"""
发育TNN - 资源自适应持续生长系统
无固定上限，自动检测资源，支持迁移继续
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import os
import psutil
import time
from datetime import datetime


class ResourceMonitor:
    """资源监控器 - 检测系统承载能力"""
    
    def __init__(self, warning_threshold=0.8, critical_threshold=0.95):
        self.warning_threshold = warning_threshold  # 80%警告
        self.critical_threshold = critical_threshold  # 95%临界
        self.history = []
    
    def check_resources(self):
        """检查当前系统资源"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 内存使用
        memory = psutil.virtual_memory()
        memory_percent = memory.percent / 100
        memory_available_gb = memory.available / (1024**3)
        
        # GPU显存（如果可用）
        gpu_info = {}
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                gpu_mem = torch.cuda.memory_stats(i)
                allocated = gpu_mem.get('allocated_bytes.all.current', 0) / (1024**3)
                reserved = gpu_mem.get('reserved_bytes.all.current', 0) / (1024**3)
                total = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                gpu_info[f'gpu_{i}'] = {
                    'allocated_gb': allocated,
                    'reserved_gb': reserved,
                    'total_gb': total,
                    'usage_percent': allocated / total if total > 0 else 0
                }
        
        # 磁盘空间
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024**3)
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'memory_available_gb': memory_available_gb,
            'gpu': gpu_info,
            'disk_free_gb': disk_free_gb,
        }
        
        self.history.append(status)
        
        # 判断资源状态
        alerts = []
        
        if memory_percent > self.critical_threshold:
            alerts.append(('CRITICAL', f'内存使用 {memory_percent:.1%}，即将耗尽'))
        elif memory_percent > self.warning_threshold:
            alerts.append(('WARNING', f'内存使用 {memory_percent:.1%}，建议关注'))
        
        if gpu_info:
            for gpu_name, gpu_data in gpu_info.items():
                if gpu_data['usage_percent'] > self.critical_threshold:
                    alerts.append(('CRITICAL', f'{gpu_name} 显存使用 {gpu_data["usage_percent"]:.1%}'))
                elif gpu_data['usage_percent'] > self.warning_threshold:
                    alerts.append(('WARNING', f'{gpu_name} 显存使用 {gpu_data["usage_percent"]:.1%}'))
        
        if disk_free_gb < 10:  # 少于10GB
            alerts.append(('WARNING', f'磁盘剩余空间 {disk_free_gb:.1f}GB'))
        
        status['alerts'] = alerts
        status['can_grow'] = len([a for a in alerts if a[0] == 'CRITICAL']) == 0
        
        return status
    
    def estimate_max_params(self):
        """估算当前环境能支持的最大参数量"""
        status = self.check_resources()
        
        memory_available = status['memory_available_gb']
        
        # 粗略估算：1M参数 ≈ 4MB（float32）+ 优化器状态 ≈ 12MB
        # 留50%余量用于激活值、梯度等
        safe_memory = memory_available * 0.5
        max_params_million = safe_memory / 12
        
        if status['gpu']:
            # 取最小显存的GPU作为限制
            min_gpu_mem = min(g['total_gb'] - g['allocated_gb'] for g in status['gpu'].values())
            gpu_max_params = (min_gpu_mem * 0.7) / 12
            max_params_million = min(max_params_million, gpu_max_params)
        
        return {
            'max_params_million': max_params_million,
            'memory_available_gb': memory_available,
            'safe_to_grow_to_layer': int(max_params_million * 0.8),  # 粗略估算每层1M参数
        }


class ContinuousGrowingTNN(nn.Module):
    """持续生长TNN - 无固定上限"""
    
    def __init__(self, 
                 initial_layers=2,
                 hidden_dim=256,
                 vocab_size=10000,
                 max_seq_len=512,
                 checkpoint_dir='./checkpoints/continuous_growth'):
        super().__init__()
        
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size
        self.max_seq_len = max_seq_len
        self.checkpoint_dir = checkpoint_dir
        
        # 当前状态
        self.current_stage = 0
        self.current_layers = initial_layers
        self.total_params = 0
        
        # 发育里程碑
        self.milestones = {
            0: {'name': 'embryo', 'min_layers': 2, 'task': 'phototaxis'},
            1: {'name': 'memory', 'min_layers': 3, 'task': 'delayed_response'},
            2: {'name': 'spatial', 'min_layers': 4, 'task': 'navigation'},
            3: {'name': 'long_range', 'min_layers': 5, 'task': 'long_range_copy'},
            4: {'name': 'symbolic', 'min_layers': 6, 'task': 'instruction_following'},
            5: {'name': 'social', 'min_layers': 7, 'task': 'multi_agent_cooperation'},
            6: {'name': 'language', 'min_layers': 8, 'task': 'language_modeling'},
            7: {'name': 'reasoning', 'min_layers': 12, 'task': 'complex_reasoning'},
            8: {'name': 'multimodal', 'min_layers': 16, 'task': 'vision_language'},
            9: {'name': 'embodied_ai', 'min_layers': 24, 'task': 'robotic_control'},
            # 可以继续添加更多阶段...
        }
        
        # 基础组件
        self.embedding = nn.Embedding(vocab_size, hidden_dim)
        self.pos_encoding = nn.Parameter(torch.randn(max_seq_len, hidden_dim) * 0.02)
        
        # 动态层列表
        self.layers = nn.ModuleList([
            self._create_layer(hidden_dim) for _ in range(initial_layers)
        ])
        
        # 输出头
        self.output_norm = nn.LayerNorm(hidden_dim)
        self.lm_head = nn.Linear(hidden_dim, vocab_size, bias=False)
        
        # 扭转场（跨层共享）
        self.torsion_field = nn.Parameter(torch.zeros(hidden_dim))
        
        # 资源监控
        self.monitor = ResourceMonitor()
        
        # 生长历史
        self.growth_history = []
        
        # 确保检查点目录存在
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        self._update_param_count()
    
    def _create_layer(self, hidden_dim):
        """创建一个TNN层"""
        layer = nn.ModuleDict({
            'norm1': nn.LayerNorm(hidden_dim),
            'attn': nn.Linear(hidden_dim, hidden_dim),
            'norm2': nn.LayerNorm(hidden_dim),
            'ff': nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim * 4),
                nn.GELU(),
                nn.Linear(hidden_dim * 4, hidden_dim),
            ),
        })
        # torsion_gate作为单独的Parameter
        layer.torsion_gate = nn.Parameter(torch.randn(hidden_dim) * 0.01)
        return layer
    
    def _update_param_count(self):
        """更新参数计数"""
        self.total_params = sum(p.numel() for p in self.parameters())
        self.current_layers = len(self.layers)
    
    def forward(self, input_ids, attention_mask=None):
        """前向传播"""
        batch_size, seq_len = input_ids.shape
        
        # 嵌入
        h = self.embedding(input_ids)
        h = h + self.pos_encoding[:seq_len].unsqueeze(0)
        
        # 逐层处理
        for layer in self.layers:
            # 注意力
            residual = h
            h = layer['norm1'](h)
            
            # 扭转场调制
            torsion_signal = torch.sigmoid(layer.torsion_gate + self.torsion_field)
            
            attn_out = layer['attn'](h)
            attn_out = attn_out * torsion_signal
            h = residual + attn_out * 0.3
            
            # 前馈
            residual = h
            h = layer['norm2'](h)
            h = residual + layer['ff'](h) * 0.3
        
        # 输出
        h = self.output_norm(h)
        logits = self.lm_head(h)
        
        return logits
    
    def check_and_grow(self, performance_metric=None):
        """检查是否需要生长，返回生长建议"""
        status = self.monitor.check_resources()
        estimates = self.monitor.estimate_max_params()
        
        result = {
            'can_grow': status['can_grow'],
            'alerts': status['alerts'],
            'current_layers': self.current_layers,
            'current_params_million': self.total_params / 1e6,
            'max_params_million': estimates['max_params_million'],
            'safe_max_layers': estimates['safe_to_grow_to_layer'],
            'should_grow': False,
            'reason': '',
        }
        
        # 检查是否有严重资源警告
        critical_alerts = [a for a in status['alerts'] if a[0] == 'CRITICAL']
        if critical_alerts:
            result['should_grow'] = False
            result['reason'] = '资源临界，建议迁移到更强环境'
            result['migration_needed'] = True
            return result
        
        # 检查性能是否触发生长条件
        if performance_metric is not None:
            # 如果性能达标且资源允许，建议生长
            current_stage_info = self.milestones.get(self.current_stage, {})
            next_stage = self.current_stage + 1
            
            if next_stage in self.milestones:
                next_stage_info = self.milestones[next_stage]
                
                if performance_metric > 0.85:  # 性能阈值
                    if self.current_layers >= current_stage_info.get('min_layers', 2):
                        if self.current_layers < estimates['safe_to_grow_to_layer']:
                            result['should_grow'] = True
                            result['reason'] = f'性能达标({performance_metric:.2f})，资源充足，建议生长到阶段{next_stage}'
                            result['next_stage'] = next_stage
                            result['next_stage_name'] = next_stage_info['name']
                        else:
                            result['reason'] = f'性能达标但资源接近上限，建议迁移后继续生长'
                            result['migration_recommended'] = True
                    else:
                        result['should_grow'] = True
                        result['reason'] = f'需要更多层数达到阶段{self.current_stage}要求'
                        result['next_stage'] = self.current_stage
        
        return result
    
    def grow(self, num_new_layers=1, init_strategy='identity'):
        """添加新层"""
        print(f"\n🌱 生长: {self.current_layers}层 → {self.current_layers + num_new_layers}层")
        
        for i in range(num_new_layers):
            new_layer = self._create_layer(self.hidden_dim)
            
            # 权重初始化策略
            if init_strategy == 'identity':
                # 近似恒等映射初始化
                with torch.no_grad():
                    # 注意力层初始化为小权重
                    new_layer['attn'].weight *= 0.01
                    # 前馈层也小权重
                    for module in new_layer['ff']:
                        if isinstance(module, nn.Linear):
                            module.weight *= 0.01
                    # torsion_gate小值
                    new_layer.torsion_gate *= 0.01
            
            elif init_strategy == 'copy_last':
                # 复制最后一层的权重
                if len(self.layers) > 0:
                    last_layer = self.layers[-1]
                    new_layer.load_state_dict(last_layer.state_dict())
                    new_layer.torsion_gate.data = last_layer.torsion_gate.data.clone()
            
            self.layers.append(new_layer)
        
        self._update_param_count()
        
        # 记录生长历史
        self.growth_history.append({
            'timestamp': datetime.now().isoformat(),
            'previous_layers': self.current_layers - num_new_layers,
            'new_layers': self.current_layers,
            'total_params': self.total_params,
            'init_strategy': init_strategy,
        })
        
        print(f"   新参数量: {self.total_params / 1e6:.2f}M")
        
        return self
    
    def save_checkpoint(self, tag=None):
        """保存检查点"""
        if tag is None:
            tag = f"stage{self.current_stage}_L{self.current_layers}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        path = os.path.join(self.checkpoint_dir, f"checkpoint_{tag}.pt")
        
        checkpoint = {
            'model_state_dict': self.state_dict(),
            'current_stage': self.current_stage,
            'current_layers': self.current_layers,
            'total_params': self.total_params,
            'growth_history': self.growth_history,
            'milestones': self.milestones,
        }
        
        torch.save(checkpoint, path)
        print(f"💾 检查点已保存: {path}")
        
        # 同时保存元数据JSON
        meta_path = os.path.join(self.checkpoint_dir, f"metadata_{tag}.json")
        with open(meta_path, 'w') as f:
            json.dump({
                'current_stage': self.current_stage,
                'current_layers': self.current_layers,
                'total_params': self.total_params,
                'growth_history': self.growth_history,
            }, f, indent=2)
        
        return path
    
    @classmethod
    def load_checkpoint(cls, path, new_device=None):
        """加载检查点，支持迁移到新设备"""
        checkpoint = torch.load(path, map_location='cpu')
        
        # 获取模型配置
        hidden_dim = checkpoint['model_state_dict']['embedding.weight'].shape[1]
        vocab_size = checkpoint['model_state_dict']['embedding.weight'].shape[0]
        initial_layers = checkpoint['current_layers']
        
        # 创建模型
        model = cls(
            initial_layers=initial_layers,
            hidden_dim=hidden_dim,
            vocab_size=vocab_size,
        )
        
        # 加载状态
        model.load_state_dict(checkpoint['model_state_dict'])
        model.current_stage = checkpoint['current_stage']
        model.growth_history = checkpoint.get('growth_history', [])
        
        if new_device:
            model = model.to(new_device)
            print(f"🚀 模型已迁移到: {new_device}")
        
        model._update_param_count()
        print(f"📂 检查点已加载: {path}")
        print(f"   当前层数: {model.current_layers}")
        print(f"   当前阶段: {model.current_stage}")
        print(f"   参数量: {model.total_params / 1e6:.2f}M")
        
        return model
    
    def get_status_report(self):
        """获取完整状态报告"""
        status = self.monitor.check_resources()
        estimates = self.monitor.estimate_max_params()
        
        # 当前阶段信息
        current_stage_info = self.milestones.get(self.current_stage, {})
        next_stage_info = self.milestones.get(self.current_stage + 1, {})
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'model': {
                'current_stage': self.current_stage,
                'current_stage_name': current_stage_info.get('name', 'unknown'),
                'current_layers': self.current_layers,
                'total_params_million': self.total_params / 1e6,
                'growth_history_count': len(self.growth_history),
            },
            'resources': status,
            'estimates': estimates,
            'next_milestone': {
                'stage': self.current_stage + 1,
                'name': next_stage_info.get('name', 'unknown'),
                'min_layers_required': next_stage_info.get('min_layers', 'unknown'),
                'task': next_stage_info.get('task', 'unknown'),
            },
            'can_grow_on_current_device': estimates['max_params_million'] > (self.total_params / 1e6) * 1.2,
        }
        
        return report


def demo_continuous_growth():
    """演示持续生长系统"""
    print("="*70)
    print("发育TNN - 资源自适应持续生长系统")
    print("="*70)
    
    # 初始化模型（2层，胚胎期）
    model = ContinuousGrowingTNN(
        initial_layers=2,
        hidden_dim=256,
        vocab_size=1000,  # 小词汇表用于演示
    )
    
    print(f"\n初始状态:")
    print(f"  层数: {model.current_layers}")
    print(f"  参数量: {model.total_params / 1e6:.2f}M")
    print(f"  阶段: {model.milestones[0]['name']}")
    
    # 检查资源状态
    print("\n资源检查:")
    status = model.get_status_report()
    print(f"  内存可用: {status['resources']['memory_available_gb']:.1f}GB")
    print(f"  估算最大支持: {status['estimates']['max_params_million']:.1f}M参数")
    print(f"  安全生长到: {status['estimates']['safe_to_grow_to_layer']}层")
    
    # 模拟生长决策
    print("\n生长决策模拟:")
    
    # 场景1：性能达标，资源充足
    result = model.check_and_grow(performance_metric=0.90)
    print(f"\n场景1: 性能90%，检查生长条件")
    print(f"  建议生长: {result['should_grow']}")
    print(f"  原因: {result['reason']}")
    
    if result['should_grow']:
        # 执行生长
        model.grow(num_new_layers=1)
        model.current_stage = result.get('next_stage', model.current_stage)
        
        # 保存检查点
        model.save_checkpoint(tag=f"after_grow_to_{model.current_layers}layers")
    
    # 场景2：资源接近上限
    print("\n场景2: 模拟资源紧张情况")
    # 人为制造一个大的模型来测试资源检测
    while model.current_layers < 50:  # 快速生长到较大规模
        if model.total_params > 500e6:  # 超过500M停止
            break
        model.grow(num_new_layers=5)
    
    result = model.check_and_grow(performance_metric=0.90)
    print(f"  当前层数: {model.current_layers}")
    print(f"  当前参数: {model.total_params / 1e6:.1f}M")
    print(f"  建议生长: {result['should_grow']}")
    print(f"  原因: {result['reason']}")
    
    if result.get('migration_needed') or result.get('migration_recommended'):
        print(f"\n⚠️ 迁移建议:")
        print(f"  当前环境资源接近上限")
        print(f"  建议:")
        print(f"    1. 保存当前检查点: {model.save_checkpoint('pre_migration')}")
        print(f"    2. 迁移到更强设备（更多GPU/内存）")
        print(f"    3. 使用 model.load_checkpoint(path, new_device='cuda') 继续")
    
    # 最终状态报告
    print("\n" + "="*70)
    print("最终状态报告")
    print("="*70)
    
    final_report = model.get_status_report()
    print(json.dumps(final_report, indent=2, default=str))
    
    return model


if __name__ == "__main__":
    demo_continuous_growth()
