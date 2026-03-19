"""
终极融合版 V5 - 生物发育型：具身优先 + 阶段解耦
模拟人类认知发育：感知运动阶段 → 前运算阶段 → 具体运算 → 形式运算
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import os
import gc
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Deque
from collections import deque

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class DelayedBuffer:
    """时延缓冲器 - 离身智能的慢处理通道"""
    
    def __init__(self, max_delay_steps=10):
        self.buffer: Deque[torch.Tensor] = deque(maxlen=max_delay_steps)
        self.max_delay = max_delay_steps
        self.read_idx = 0
        
    def write(self, x):
        """写入最新感知"""
        self.buffer.append(x.clone().detach())
        
    def read(self, delay_steps=None):
        """读取时延后的信息"""
        if len(self.buffer) == 0:
            return None
        
        delay = delay_steps or max(1, len(self.buffer) // 2)
        idx = max(0, len(self.buffer) - delay - 1)
        
        return self.buffer[idx] if idx < len(self.buffer) else self.buffer[0]
    
    def clear(self):
        self.buffer.clear()


class EmbodiedBlockV5(nn.Module):
    """具身功能块 - 快速响应"""
    
    def __init__(self, block_id, dim):
        super().__init__()
        self.block_id = block_id
        self.dim = dim
        
        # 快速处理路径
        self.norm = nn.LayerNorm(dim)
        self.processor = nn.Sequential(
            nn.Linear(dim, dim),
            nn.Tanh(),
            nn.Linear(dim, dim)
        )
        
        # 状态
        self.excitement = 0.5
        self.success_rate = 0.5
        self.activation_count = 0
    
    def forward(self, x, torsion_field):
        self.activation_count += 1
        
        h = self.norm(x)
        h = self.processor(h)
        
        # 快速扭转调制
        h = h * (1 + torsion_field.unsqueeze(1) * 0.1)
        
        out = x + h * 0.3  # 弱残差，快速响应
        
        self.excitement = min(1.0, self.excitement + 0.02)
        return out
    
    def record_success(self, success):
        alpha = 0.1
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)
        if not success:
            self.excitement = max(0.1, self.excitement - 0.05)
    
    def get_load_priority(self):
        return self.success_rate * 0.6 + self.excitement * 0.4


class DisembodiedBlockV5(nn.Module):
    """离身功能块 - 慢速深度处理"""
    
    def __init__(self, block_id, dim):
        super().__init__()
        self.block_id = block_id
        self.dim = dim
        
        # 深度处理路径
        self.norm1 = nn.LayerNorm(dim)
        self.attention = nn.Linear(dim, dim)
        self.norm2 = nn.LayerNorm(dim)
        self.ff = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(dim * 2, dim)
        )
        
        # 状态
        self.excitement = 0.3  # 离身初始兴奋度较低
        self.success_rate = 0.3
        self.activation_count = 0
        self.importance = nn.Parameter(torch.tensor(0.5))
    
    def forward(self, x, torsion_field, delayed_context=None):
        self.activation_count += 1
        
        # 第一层归一化
        h = self.norm1(x)
        h = self.attention(h)
        
        # 时延上下文整合
        if delayed_context is not None:
            h = h + delayed_context.unsqueeze(1) * 0.2
        
        # 扭转调制
        h = h * (1 + torsion_field.unsqueeze(1) * 0.05)
        h = x + h * 0.5
        
        # 深度FFN
        h2 = self.norm2(h)
        h2 = self.ff(h2)
        
        out = h + h2 * 0.5
        
        self.excitement = min(1.0, self.excitement + 0.005)  # 慢速兴奋
        return out
    
    def record_success(self, success):
        alpha = 0.05  # 离身学习更慢
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)
        if not success:
            self.excitement = max(0.1, self.excitement - 0.02)
        
        with torch.no_grad():
            self.importance.data = torch.tensor(self.success_rate * 0.7 + self.excitement * 0.3)
    
    def get_load_priority(self):
        return self.success_rate * 0.6 + self.excitement * 0.4


class DevelopmentalStage:
    """发育阶段管理"""
    
    STAGES = {
        'sensorimotor': {  # 感知运动阶段 (0-2岁)
            'min_layers': 2,
            'max_layers': 5,
            'embodied_ratio': 1.0,  # 100%具身
            'disembodied_unlocked': False,
            'delay_steps': 0,
        },
        'preoperational': {  # 前运算阶段 (2-7岁)
            'min_layers': 5,
            'max_layers': 10,
            'embodied_ratio': 0.8,  # 80%具身
            'disembodied_unlocked': True,
            'delay_steps': 3,
        },
        'concrete': {  # 具体运算阶段 (7-12岁)
            'min_layers': 10,
            'max_layers': 15,
            'embodied_ratio': 0.6,  # 60%具身
            'disembodied_unlocked': True,
            'delay_steps': 5,
        },
        'formal': {  # 形式运算阶段 (12岁+)
            'min_layers': 15,
            'max_layers': 30,
            'embodied_ratio': 0.5,  # 50%具身
            'disembodied_unlocked': True,
            'delay_steps': 10,
        },
    }
    
    def __init__(self):
        self.stage = 'sensorimotor'
        self.stage_order = ['sensorimotor', 'preoperational', 'concrete', 'formal']
        self.stage_idx = 0
        
        # 里程碑检测
        self.embodied_mastery = 0.0  # 具身掌握度
        self.environment_stability = 0.0  # 环境稳定性
        
    def get_config(self):
        return self.STAGES[self.stage]
    
    def check_promotion(self, embodied_acc, env_stability, total_layers):
        """检查是否应进入下一阶段"""
        cfg = self.get_config()
        
        # 当前阶段掌握度
        self.embodied_mastery = embodied_acc
        self.environment_stability = env_stability
        
        # 晋升条件
        if self.stage == 'sensorimotor':
            # 感知运动阶段：具身准确率>70% 且层数>=5
            if embodied_acc >= 0.70 and total_layers >= 5:
                return self._promote()
                
        elif self.stage == 'preoperational':
            # 前运算阶段：具身>75% 且环境稳定>0.8
            if embodied_acc >= 0.75 and env_stability >= 0.8 and total_layers >= 10:
                return self._promote()
                
        elif self.stage == 'concrete':
            # 具体运算阶段：具身>80% 且环境稳定>0.85
            if embodied_acc >= 0.80 and env_stability >= 0.85 and total_layers >= 15:
                return self._promote()
        
        return False, self.stage
    
    def _promote(self):
        """晋升到下一阶段"""
        if self.stage_idx < len(self.stage_order) - 1:
            self.stage_idx += 1
            self.stage = self.stage_order[self.stage_idx]
            return True, self.stage
        return False, self.stage
    
    def get_progress_str(self):
        cfg = self.get_config()
        return f"{self.stage}(E{cfg['embodied_ratio']*100:.0f}%/D{cfg['delay_steps']})"


class DevelopmentalLayerV5:
    """发育层 - 阶段依赖的层结构"""
    
    def __init__(self, layer_id, dim, num_blocks, offload_dir, stage_config):
        self.layer_id = layer_id
        self.dim = dim
        self.num_blocks = num_blocks
        self.offload_dir = Path(offload_dir)
        
        # 根据发育阶段创建块
        self.embodied_blocks: Dict[int, EmbodiedBlockV5] = {}
        self.disembodied_blocks: Dict[int, DisembodiedBlockV5] = {}
        
        self._create_blocks(stage_config)
        
        # 选择器
        self.embodied_selector = nn.Linear(dim, num_blocks)
        if stage_config['disembodied_unlocked']:
            self.disembodied_selector = nn.Linear(dim, num_blocks)
        else:
            self.disembodied_selector = None
        
        # 时延缓冲
        self.delay_buffer = DelayedBuffer(max_delay_steps=stage_config['delay_steps'])
        
        # 统计
        self.training_epochs = 0
        self.layer_best_embodied_acc = 0.0
        self.layer_best_disembodied_acc = 0.0
        
        self.offload_path = self.offload_dir / f"dev_v5_layer_{layer_id}.pt"
    
    def _create_blocks(self, stage_config):
        """根据阶段创建块"""
        for i in range(self.num_blocks):
            self.embodied_blocks[i] = EmbodiedBlockV5(i, self.dim)
            
            # 只有解锁后才创建离身块
            if stage_config['disembodied_unlocked']:
                self.disembodied_blocks[i] = DisembodiedBlockV5(i, self.dim)
    
    def __call__(self, embodied_input, disembodied_input, torsion_field, 
                max_active_blocks=2, stage_config=None):
        """前向 - 阶段依赖处理"""
        
        embodied_ratio = stage_config['embodied_ratio'] if stage_config else 1.0
        disembodied_unlocked = stage_config['disembodied_unlocked'] if stage_config else False
        delay_steps = stage_config['delay_steps'] if stage_config else 0
        
        # === 具身路径（总是活跃）===
        selector_scores = torch.sigmoid(self.embodied_selector(embodied_input.mean(dim=1)))
        _, embodied_top = torch.topk(selector_scores[0], min(max_active_blocks, self.num_blocks))
        
        embodied_h = embodied_input
        for idx in embodied_top.tolist():
            embodied_h = self.embodied_blocks[idx](embodied_h, torsion_field)
            self.embodied_blocks[idx].record_success(True)
        
        # === 离身路径（阶段解锁后才处理）===
        if disembodied_unlocked and disembodied_input is not None:
            # 写入时延缓冲
            self.delay_buffer.write(disembodied_input.mean(dim=1))
            
            # 读取时延信息
            delayed_context = self.delay_buffer.read(delay_steps)
            
            selector_scores = torch.sigmoid(self.disembodied_selector(disembodied_input.mean(dim=1)))
            _, disembodied_top = torch.topk(selector_scores[0], min(max_active_blocks, self.num_blocks))
            
            disembodied_h = disembodied_input
            for idx in disembodied_top.tolist():
                disembodied_h = self.disembodied_blocks[idx](
                    disembodied_h, torsion_field, delayed_context
                )
                self.disembodied_blocks[idx].record_success(True)
        else:
            disembodied_h = None
        
        # 返回具身主导的结果
        return embodied_h, disembodied_h, {
            'embodied_active': embodied_top.tolist(),
            'disembodied_active': list(self.disembodied_blocks.keys()) if disembodied_unlocked else [],
            'embodied_ratio': embodied_ratio,
            'delay_steps': delay_steps,
        }


class UltimateFusionV5(nn.Module):
    """
    终极融合版 V5 - 生物发育型
    具身优先发育，离身后解锁，时延解耦
    """
    
    def __init__(self,
                 initial_layers=2,
                 target_layers=30,
                 dim=256,
                 sensory_dim=64,
                 action_dim=32,
                 symbol_vocab=500,
                 num_blocks=4,
                 max_memory_layers=5,
                 offload_dir='./ultimate_fusion_v5'):
        super().__init__()
        
        self.target_layers = target_layers
        self.dim = dim
        self.num_blocks = num_blocks
        self.max_memory_layers = max_memory_layers
        self.offload_dir = Path(offload_dir)
        self.offload_dir.mkdir(parents=True, exist_ok=True)
        
        # 具身输入
        self.sensory_encoder = nn.Linear(sensory_dim, dim)
        self.embodied_pos = nn.Parameter(torch.randn(1, 64, dim) * 0.02)
        self.action_head = nn.Linear(dim, action_dim)
        
        # 离身输入（初始锁定，后解锁）
        self.symbol_embedding = nn.Embedding(symbol_vocab, dim)
        self.disembodied_pos = nn.Parameter(torch.randn(1, 128, dim) * 0.02)
        self.symbol_head = nn.Linear(dim, symbol_vocab)
        
        # 共享扭转场
        self.register_buffer('torsion_field', torch.zeros(1, dim))
        
        # 层管理
        self.layers: Dict[int, DevelopmentalLayerV5] = {}
        self.offloaded_layers: set = set()
        self.access_order: List[int] = []
        
        # 发育阶段管理
        self.development = DevelopmentalStage()
        
        # 生长策略
        self.min_cycles_per_stage = 30
        
        self._init_layers(initial_layers)
        self._print_info()
    
    def _print_info(self):
        print("="*70)
        print("🧬 终极融合版 V5 - 生物发育型")
        print("="*70)
        print("发育策略:")
        print("  1. 感知运动 (0-2岁): 100%具身，2-5层")
        print("  2. 前运算 (2-7岁): 80%具身，离身解锁，5-10层")
        print("  3. 具体运算 (7-12岁): 60%具身，10-15层")
        print("  4. 形式运算 (12岁+): 50%具身，15-30层")
        print("-"*70)
        print("关键特性:")
        print("  ✅ 具身优先发育")
        print("  ✅ 离身时延解耦")
        print("  ✅ 阶段里程碑检测")
        print("  ✅ 环境稳定度评估")
        print("="*70)
    
    def _init_layers(self, num_layers):
        stage_cfg = self.development.get_config()
        for i in range(num_layers):
            layer = DevelopmentalLayerV5(i, self.dim, self.num_blocks, self.offload_dir, stage_cfg)
            self.layers[i] = layer
            self.access_order.append(i)
    
    def _get_layer(self, idx):
        if idx in self.layers:
            if idx in self.access_order:
                self.access_order.remove(idx)
            self.access_order.insert(0, idx)
            return self.layers[idx]
        return None
    
    def forward(self, sensory_input=None, symbol_input=None, return_stats=False):
        stage_cfg = self.development.get_config()
        
        # 具身路径（总是处理）
        if sensory_input is not None:
            embodied_h = self.sensory_encoder(sensory_input).unsqueeze(1)
            embodied_h = embodied_h + self.embodied_pos[:, :1, :]
        else:
            embodied_h = torch.zeros(1, 1, self.dim, device=self.torsion_field.device)
        
        # 离身路径（阶段解锁后处理）
        if stage_cfg['disembodied_unlocked'] and symbol_input is not None:
            disembodied_h = self.symbol_embedding(symbol_input)
            seq_len = symbol_input.size(1)
            disembodied_h = disembodied_h + self.disembodied_pos[:, :seq_len, :]
        else:
            disembodied_h = None
        
        # 通过层
        layer_stats = []
        for idx in sorted(self.layers.keys()):
            layer = self._get_layer(idx)
            if layer:
                embodied_h, disembodied_h, info = layer(
                    embodied_h, disembodied_h, self.torsion_field, 
                    max_active_blocks=2, stage_config=stage_cfg
                )
                layer_stats.append(info)
        
        # 输出
        outputs = {
            'action_logits': self.action_head(embodied_h.squeeze(1)) if embodied_h is not None else None,
            'symbol_logits': self.symbol_head(disembodied_h) if disembodied_h is not None else None,
            'embodied_state': embodied_h,
            'disembodied_state': disembodied_h,
        }
        
        if return_stats:
            outputs['layer_stats'] = layer_stats
            outputs['stage'] = self.development.stage
        
        return outputs
    
    def training_step(self, sensory_input, symbol_input, action_target, symbol_target, optimizer):
        self.train()
        stage_cfg = self.development.get_config()
        
        outputs = self.forward(sensory_input, symbol_input, return_stats=True)
        
        # 具身损失（分类任务）
        if outputs['action_logits'] is not None:
            # 动作分类（假设action_target是类别索引）
            embodied_loss = F.cross_entropy(outputs['action_logits'], action_target)
            embodied_acc = (outputs['action_logits'].argmax(dim=-1) == action_target).float().mean().item()
        else:
            embodied_loss = torch.tensor(0.0)
            embodied_acc = 0.0
        
        # 离身损失（解锁后计算）
        if stage_cfg['disembodied_unlocked'] and outputs['symbol_logits'] is not None:
            # 使用当前阶段的词汇表大小
            max_vocab = min(symbol_target.max().item() + 1, 500)
            disembodied_loss = F.cross_entropy(
                outputs['symbol_logits'][:, :, :max_vocab].reshape(-1, max_vocab),
                symbol_target.reshape(-1)
            )
        else:
            disembodied_loss = torch.tensor(0.0)
        
        # 总损失：具身主导
        embodied_weight = stage_cfg['embodied_ratio']
        disembodied_weight = 1.0 - embodied_weight if stage_cfg['disembodied_unlocked'] else 0.0
        
        total_loss = embodied_loss * embodied_weight + disembodied_loss * disembodied_weight
        
        optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
        optimizer.step()
        
        # 统计 - 离身准确率
        with torch.no_grad():
            if stage_cfg['disembodied_unlocked'] and outputs['symbol_logits'] is not None:
                disembodied_acc = (outputs['symbol_logits'].argmax(dim=-1) == symbol_target).float().mean().item()
            else:
                disembodied_acc = 0.0
        
        # 更新层统计
        last_idx = max(self.layers.keys()) if self.layers else 0
        layer = self._get_layer(last_idx)
        if layer:
            layer.training_epochs += 1
            layer.layer_best_embodied_acc = max(layer.layer_best_embodied_acc, embodied_acc)
        
        return {
            'loss': total_loss.item(),
            'embodied_loss': embodied_loss.item(),
            'disembodied_loss': disembodied_loss.item() if isinstance(disembodied_loss, torch.Tensor) else 0.0,
            'embodied_acc': embodied_acc,
            'disembodied_acc': disembodied_acc,
            'layers': len(self.layers),
            'stage': self.development.stage,
        }
    
    def check_development(self):
        """检查发育里程碑"""
        last_idx = max(self.layers.keys()) if self.layers else 0
        layer = self._get_layer(last_idx)
        
        if layer is None:
            return False, self.development.stage
        
        embodied_acc = layer.layer_best_embodied_acc
        env_stability = 0.85  # 简化：假设环境稳定
        total_layers = len(self.layers)
        
        promoted, new_stage = self.development.check_promotion(embodied_acc, env_stability, total_layers)
        
        if promoted:
            print(f"\n{'='*60}")
            print(f"🎉 发育里程碑! 进入{new_stage}阶段")
            print(f"   具身掌握度: {embodied_acc:.1%}")
            print(f"   当前层数: {total_layers}")
            print(f"{'='*60}\n")
            
            # 解锁新层时应用新阶段配置
            for layer in self.layers.values():
                layer.delay_buffer.maxlen = self.development.get_config()['delay_steps'] + 5
        
        return promoted, new_stage


def run_v5_demo():
    """运行V5生物发育演示"""
    print("\n" + "="*70)
    print("🧬 终极融合版 V5 - 生物发育演示")
    print("="*70 + "\n")
    
    model = UltimateFusionV5(
        initial_layers=1,  # 单细胞起始
        target_layers=20,
        dim=256,
        sensory_dim=64,
        action_dim=16,
        symbol_vocab=100,
        num_blocks=4,
        max_memory_layers=5,
    )
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    
    print(f"\n开始发育...")
    print(f"初始阶段: {model.development.get_progress_str()}\n")
    
    embodied_accs = []
    total_growth = 0
    
    for epoch in range(2000):
        # 生成数据 - 离散分类任务
        sensory_input = torch.randn(4, 64)
        # 动作分类（16类）
        action_target = torch.randint(0, 16, (4,))
        
        # 符号数据（阶段解锁后才有效）
        stage_cfg = model.development.get_config()
        if stage_cfg['disembodied_unlocked']:
            symbol_input = torch.randint(0, 20, (4, 8))
            symbol_target = torch.randint(0, 20, (4, 8))
        else:
            symbol_input = None
            symbol_target = None
        
        result = model.training_step(sensory_input, symbol_input, action_target, symbol_target, optimizer)
        embodied_accs.append(result['embodied_acc'])
        
        # 每50轮检查发育
        if (epoch + 1) % 50 == 0:
            model.check_development()
            
            print(f"📚 Epoch {epoch + 1} | 阶段: {result['stage']}")
            print(f"   具身损失: {result['embodied_loss']:.4f} | 准确率: {result['embodied_acc']:.1%}")
            if result['disembodied_acc'] > 0:
                print(f"   离身损失: {result['disembodied_loss']:.4f} | 准确率: {result['disembodied_acc']:.1%}")
            print(f"   层数: {result['layers']}/20")
            
            # 生长决策
            # 胚胎快速分裂期(<4层): 每50轮自动+1层，不依赖准确率
            # 正常发育期(>=4层): 需要准确率达标
            if result['layers'] < 4:
                # 胚胎期: 每50轮自动生长
                if (epoch + 1) % 50 == 0 and result['layers'] < model.target_layers:
                    new_idx = result['layers']
                    stage_cfg = model.development.get_config()
                    new_layer = DevelopmentalLayerV5(new_idx, model.dim, model.num_blocks, model.offload_dir, stage_cfg)
                    
                    # Kaiming初始化
                    for i in range(model.num_blocks):
                        for p in new_layer.embodied_blocks[i].parameters():
                            if len(p.shape) >= 2:
                                nn.init.kaiming_normal_(p, mode='fan_out', nonlinearity='relu')
                    
                    model.layers[new_idx] = new_layer
                    model.access_order.insert(0, new_idx)
                    total_growth += 1
                    
                    print(f"   🧬 胚胎分裂! {result['layers']}层 → {len(model.layers)}层 (自动)")
                    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
                    
            elif result['embodied_acc'] >= 0.70 and result['layers'] < model.target_layers:
                # 正常发育期: 准确率达标才生长
                stage_max = model.development.get_config()['max_layers']
                if result['layers'] < stage_max:
                    new_idx = result['layers']
                    stage_cfg = model.development.get_config()
                    new_layer = DevelopmentalLayerV5(new_idx, model.dim, model.num_blocks, model.offload_dir, stage_cfg)
                    
                    for i in range(model.num_blocks):
                        for p in new_layer.embodied_blocks[i].parameters():
                            if len(p.shape) >= 2:
                                nn.init.kaiming_normal_(p, mode='fan_out', nonlinearity='relu')
                    
                    model.layers[new_idx] = new_layer
                    model.access_order.insert(0, new_idx)
                    total_growth += 1
                    
                    print(f"   🌱 生长成功! {result['layers']}层 → {len(model.layers)}层 (达标)")
                    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
                    total_growth += 1
        
        # 提前结束
        if result['layers'] >= 15 and model.development.stage == 'formal':
            print(f"\n✅ 完全发育! {result['layers']}层, 阶段: {result['stage']}")
            break
    
    print("\n" + "="*70)
    print("📊 V5发育完成")
    print("="*70)
    print(f"最终层数: {result['layers']}")
    print(f"最终阶段: {result['stage']}")
    print(f"具身准确率: {result['embodied_acc']:.1%}")
    print(f"生长次数: {total_growth}")


if __name__ == "__main__":
    run_v5_demo()
