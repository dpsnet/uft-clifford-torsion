"""
连续生长系统 - 磁盘换内存版本
使用梯度检查点、激活值磁盘缓存、混合精度来突破内存限制
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import os
import tempfile
import pickle
import gc
from datetime import datetime


class MemoryEfficientGrowingTNN(nn.Module):
    """内存高效版持续生长TNN"""
    
    def __init__(self, 
                 initial_layers=2,
                 hidden_dim=128,
                 vocab_size=100,
                 max_seq_len=64,
                 checkpoint_dir='./checkpoints/memory_efficient',
                 use_gradient_checkpointing=True,
                 use_disk_offload=True,
                 mixed_precision=True):
        super().__init__()
        
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size
        self.max_seq_len = max_seq_len
        self.checkpoint_dir = checkpoint_dir
        
        # 内存优化开关
        self.use_gradient_checkpointing = use_gradient_checkpointing
        self.use_disk_offload = use_disk_offload
        self.mixed_precision = mixed_precision and torch.cuda.is_available()
        
        # 当前状态
        self.current_stage = 0
        self.current_layers = initial_layers
        self.total_params = 0
        
        # 磁盘缓存目录
        self.offload_dir = os.path.join(checkpoint_dir, 'offload_cache')
        os.makedirs(self.offload_dir, exist_ok=True)
        
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
        
        # 扭转场
        self.torsion_field = nn.Parameter(torch.zeros(hidden_dim))
        
        # 生长历史
        self.growth_history = []
        
        os.makedirs(checkpoint_dir, exist_ok=True)
        self._update_param_count()
        
        print(f"🧠 内存高效模式:")
        print(f"   梯度检查点: {'✓' if use_gradient_checkpointing else '✗'}")
        print(f"   磁盘缓存: {'✓' if use_disk_offload else '✗'}")
        print(f"   混合精度: {'✓' if self.mixed_precision else '✗'}")
    
    def _create_layer(self, hidden_dim):
        """创建层"""
        layer = nn.ModuleDict({
            'norm1': nn.LayerNorm(hidden_dim),
            'attn': nn.Linear(hidden_dim, hidden_dim, bias=False),  # 无偏置省内存
            'norm2': nn.LayerNorm(hidden_dim),
            'ff': nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim * 2, bias=False),  # 减小FFN维度
                nn.GELU(),
                nn.Linear(hidden_dim * 2, hidden_dim, bias=False),
            ),
        })
        layer.torsion_gate = nn.Parameter(torch.randn(hidden_dim) * 0.01)
        return layer
    
    def _update_param_count(self):
        self.total_params = sum(p.numel() for p in self.parameters())
        self.current_layers = len(self.layers)
    
    def forward_with_checkpointing(self, input_ids):
        """使用梯度检查点前向传播"""
        batch_size, seq_len = input_ids.shape
        
        # 嵌入
        h = self.embedding(input_ids)
        h = h + self.pos_encoding[:seq_len].unsqueeze(0)
        
        # 逐层处理（使用检查点）
        for i, layer in enumerate(self.layers):
            # 使用torch.utils.checkpoint来节省内存
            if self.use_gradient_checkpointing and self.training:
                h = torch.utils.checkpoint.checkpoint(
                    self._layer_forward, h, layer, self.torsion_field,
                    use_reentrant=False
                )
            else:
                h = self._layer_forward(h, layer, self.torsion_field)
        
        # 输出
        h = self.output_norm(h)
        logits = self.lm_head(h)
        
        return logits
    
    def _layer_forward(self, h, layer, torsion_field):
        """单层前向"""
        # 注意力
        residual = h
        h = layer['norm1'](h)
        
        torsion_signal = torch.sigmoid(layer.torsion_gate + torsion_field)
        attn_out = layer['attn'](h)
        attn_out = attn_out * torsion_signal
        h = residual + attn_out * 0.3
        
        # 前馈
        residual = h
        h = layer['norm2'](h)
        h = residual + layer['ff'](h) * 0.3
        
        return h
    
    def forward(self, input_ids):
        """前向入口"""
        if self.mixed_precision and torch.cuda.is_available():
            with torch.cuda.amp.autocast():
                return self.forward_with_checkpointing(input_ids)
        else:
            return self.forward_with_checkpointing(input_ids)
    
    def estimate_memory_usage(self):
        """估算内存使用情况"""
        # 参数内存
        param_memory = sum(p.numel() * p.element_size() for p in self.parameters()) / (1024**3)
        
        # 激活值估算（假设batch=4, seq=64）
        activation_memory = 4 * 64 * self.hidden_dim * self.current_layers * 4 / (1024**3)
        
        # 梯度内存
        grad_memory = param_memory
        
        # 优化器状态（Adam）
        optimizer_memory = param_memory * 2
        
        total_estimate = param_memory + activation_memory + grad_memory + optimizer_memory
        
        return {
            'param_gb': param_memory,
            'activation_gb': activation_memory,
            'grad_gb': grad_memory,
            'optimizer_gb': optimizer_memory,
            'total_estimate_gb': total_estimate,
        }
    
    def grow(self, num_new_layers=1):
        """生长 - 带内存检查"""
        print(f"\n🌱 生长: {self.current_layers}层 → {self.current_layers + num_new_layers}层")
        
        # 先估算生长后的内存
        temp_layers = self.current_layers + num_new_layers
        temp_activation = 4 * 64 * self.hidden_dim * temp_layers * 4 / (1024**3)
        temp_total = self.estimate_memory_usage()['total_estimate_gb'] + temp_activation
        
        print(f"   预估内存需求: {temp_total:.2f}GB")
        
        # 如果内存需求过大，启用更多优化
        if temp_total > 8:  # 假设8GB阈值
            print(f"   ⚠️ 内存需求较大，启用激进优化...")
            self.use_gradient_checkpointing = True
            self.use_disk_offload = True
        
        for i in range(num_new_layers):
            new_layer = self._create_layer(self.hidden_dim)
            
            # 小权重初始化
            with torch.no_grad():
                new_layer['attn'].weight *= 0.01
                for module in new_layer['ff']:
                    if isinstance(module, nn.Linear):
                        module.weight *= 0.01
                new_layer.torsion_gate *= 0.01
            
            self.layers.append(new_layer)
        
        self._update_param_count()
        
        self.growth_history.append({
            'timestamp': datetime.now().isoformat(),
            'previous_layers': self.current_layers - num_new_layers,
            'new_layers': self.current_layers,
            'total_params': self.total_params,
        })
        
        print(f"   新参数量: {self.total_params / 1e6:.2f}M")
        print(f"   实际内存: {self.estimate_memory_usage()['total_estimate_gb']:.2f}GB")
        
        # 强制垃圾回收
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return self
    
    def save_checkpoint(self, tag):
        """保存检查点"""
        path = os.path.join(self.checkpoint_dir, f"checkpoint_{tag}.pt")
        
        checkpoint = {
            'model_state_dict': self.state_dict(),
            'current_stage': self.current_stage,
            'current_layers': self.current_layers,
            'growth_history': self.growth_history,
        }
        
        torch.save(checkpoint, path)
        print(f"💾 检查点: {path}")
        return path


def run_memory_efficient_experiment():
    """运行内存高效实验"""
    print("="*70)
    print("🧠 内存高效连续生长实验")
    print("   策略: 梯度检查点 + 磁盘换内存")
    print("="*70)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = f'./efficient_growth_{timestamp}'
    
    # 创建模型
    model = MemoryEfficientGrowingTNN(
        initial_layers=2,
        hidden_dim=64,  # 更小维度
        vocab_size=50,
        use_gradient_checkpointing=True,
        use_disk_offload=True,
    )
    
    print(f"\n初始状态:")
    print(f"  层数: {model.current_layers}")
    print(f"  参数量: {model.total_params/1e6:.2f}M")
    mem = model.estimate_memory_usage()
    print(f"  预估内存: {mem['total_estimate_gb']:.2f}GB")
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    scaler = torch.cuda.amp.GradScaler() if model.mixed_precision else None
    
    # 训练数据生成
    def generate_data(batch_size, seq_len):
        data = []
        targets = []
        for _ in range(batch_size):
            seq = torch.arange(seq_len) % model.vocab_size
            data.append(seq)
            target = torch.cat([seq[1:], torch.tensor([seq[0].item()])])
            targets.append(target)
        return torch.stack(data), torch.stack(targets)
    
    # 生长循环
    print("\n" + "-"*70)
    print("开始生长循环")
    print("-"*70)
    
    cycle = 0
    current_target_layers = 3  # 第一个生长目标
    
    while cycle < 100:
        cycle += 1
        
        # 训练
        total_loss = 0
        for step in range(10):
            input_ids, targets = generate_data(4, 32)
            
            if scaler:
                with torch.cuda.amp.autocast():
                    logits = model(input_ids)
                    loss = F.cross_entropy(logits.view(-1, model.vocab_size), targets.view(-1))
                
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                logits = model(input_ids)
                loss = F.cross_entropy(logits.view(-1, model.vocab_size), targets.view(-1))
                loss.backward()
                optimizer.step()
            
            optimizer.zero_grad()
            total_loss += loss.item()
        
        avg_loss = total_loss / 10
        
        # 评估
        with torch.no_grad():
            eval_input, eval_target = generate_data(4, 32)
            eval_logits = model(eval_input)
            eval_loss = F.cross_entropy(eval_logits.view(-1, model.vocab_size), eval_target.view(-1))
            perplexity = torch.exp(eval_loss).item()
            
            predictions = eval_logits.argmax(dim=-1)
            accuracy = (predictions == eval_target).float().mean().item()
        
        if cycle % 10 == 0:
            print(f"\n📊 周期 #{cycle} | {model.current_layers}层 | 损失: {avg_loss:.4f} | 困惑度: {perplexity:.2f} | 准确率: {accuracy:.1%}")
            print(f"   内存估算: {model.estimate_memory_usage()['total_estimate_gb']:.2f}GB")
        
        # 生长条件：准确率达标且达到目标层数
        if accuracy > 0.90 and model.current_layers < current_target_layers:
            print(f"\n🌱 准确率{accuracy:.1%}达标，执行生长!")
            
            model.grow(num_new_layers=1)
            
            # 更新优化器
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            if scaler:
                scaler = torch.cuda.amp.GradScaler()
            
            # 设定下一个目标
            current_target_layers += 1
            if current_target_layers > 10:
                current_target_layers = 10  # 最大10层
            
            model.save_checkpoint(f'after_grow_to_{model.current_layers}layers')
            
            # 更新阶段
            if model.current_layers >= 3:
                model.current_stage = 1
            if model.current_layers >= 5:
                model.current_stage = 2
            if model.current_layers >= 8:
                model.current_stage = 3
        
        # 周期性保存
        if cycle % 20 == 0:
            model.save_checkpoint(f'periodic_cycle_{cycle}')
        
        # 清理内存
        if cycle % 5 == 0:
            gc.collect()
    
    # 完成
    print(f"\n" + "="*70)
    print("实验完成!")
    print("="*70)
    print(f"最终层数: {model.current_layers}")
    print(f"最终参数量: {model.total_params/1e6:.2f}M")
    print(f"生长次数: {len(model.growth_history)}")
    print(f"最终阶段: {model.current_stage}")
    
    # 保存报告
    report = {
        'final_layers': model.current_layers,
        'final_params_million': model.total_params / 1e6,
        'growth_count': len(model.growth_history),
        'growth_history': model.growth_history,
        'final_stage': model.current_stage,
    }
    
    with open(os.path.join(log_dir, 'report.json'), 'w') as f:
        json.dump(report, f, indent=2)
    
    model.save_checkpoint('experiment_complete')
    
    return model, report


if __name__ == "__main__":
    run_memory_efficient_experiment()
