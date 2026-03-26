"""
优化版20层实验 - 更高生长阈值，更多训练轮数
解决生长过快导致的准确率下降问题
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import os
import json
import gc
from datetime import datetime

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')
from unified_adaptive_tnn import UnifiedAdaptiveTNN, AdaptiveLayer


class OptimizedUltraScaleTNN(UnifiedAdaptiveTNN):
    """优化版 - 更保守的生长策略"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 优化配置 - 更保守
        self.gradient_clip_val = 1.0
        self.residual_scale = 0.5
        
        # 关键改进：更高的生长阈值
        self.growth_threshold_accuracy = 0.80  # 从70%提高到80%
        self.growth_threshold_loss = 0.6       # 从1.0收紧到0.6
        self.min_cycles_before_growth = 25     # 从15增加到25
        
        # 记录每层的训练情况
        self.layer_training_epochs = {}
        
        print("✅ 优化版配置:")
        print(f"   生长阈值: 准确率>{self.growth_threshold_accuracy}, 损失<{self.growth_threshold_loss}")
        print(f"   最小训练轮数: {self.min_cycles_before_growth}")
        print(f"   梯度裁剪: {self.gradient_clip_val}")
    
    def grow(self, num_new_layers=1):
        """优化版生长 - 确保充分训练"""
        current_layer_count = len(self.layers)
        
        # 检查当前层是否充分训练
        if current_layer_count > 0:
            current_epochs = self.layer_training_epochs.get(current_layer_count - 1, 0)
            if current_epochs < self.min_cycles_before_growth:
                print(f"\n⏸️ 推迟生长: 当前层仅训练{current_epochs}轮，需{self.min_cycles_before_growth}轮")
                return self
        
        print(f"\n🌱 优化版生长: {current_layer_count}层 → {current_layer_count + num_new_layers}层")
        
        for i in range(num_new_layers):
            new_layer = AdaptiveLayer(
                current_layer_count + i,
                self.hidden_dim,
                (2, 2),
                self.blocks_per_layer
            )
            
            # Kaiming初始化
            with torch.no_grad():
                for name, p in new_layer.named_parameters():
                    if 'weight' in name and len(p.shape) >= 2:
                        nn.init.kaiming_normal_(p, mode='fan_out', nonlinearity='relu')
                    elif 'bias' in name:
                        nn.init.zeros_(p)
                    elif 'norm' in name.lower() and 'weight' in name:
                        nn.init.ones_(p)
                
                for block in new_layer.blocks:
                    nn.init.normal_(block.torsion_gate, mean=0, std=0.001)
            
            self.layers.append(new_layer)
            # 记录新层训练轮数
            self.layer_training_epochs[len(self.layers) - 1] = 0
        
        # 更新阶段
        for stage_id, (name, target_layers) in self.stages.items():
            if len(self.layers) >= target_layers:
                self.current_stage = stage_id
        
        self.growth_history.append({
            'timestamp': datetime.now().isoformat(),
            'previous_layers': current_layer_count,
            'new_layers': len(self.layers),
            'stage': self.stages[self.current_stage][0],
            'note': 'optimized_growth',
        })
        
        print(f"   新层数: {len(self.layers)}")
        print(f"   新阶段: {self.stages[self.current_stage][0]}")
        
        gc.collect()
        return self
    
    def training_step(self, input_ids, targets, optimizer):
        """优化版训练步骤"""
        self.train()
        
        # 前向
        logits, stats = self.forward(input_ids, return_stats=True)
        
        # 损失
        loss = F.cross_entropy(logits.view(-1, self.vocab_size), targets.view(-1))
        
        # 反向
        optimizer.zero_grad()
        loss.backward()
        
        # 梯度裁剪
        if self.gradient_clip_val > 0:
            torch.nn.utils.clip_grad_norm_(self.parameters(), self.gradient_clip_val)
        
        optimizer.step()
        
        # 统计
        with torch.no_grad():
            preds = logits.argmax(dim=-1)
            accuracy = (preds == targets).float().mean().item()
        
        # 反馈
        for layer in self.layers:
            layer.record_success(accuracy > 0.8)  # 提高成功阈值
        
        # 记录训练轮数
        for i in range(len(self.layers)):
            self.layer_training_epochs[i] = self.layer_training_epochs.get(i, 0) + 1
        
        # 检查生长
        should_grow = self.check_growth_condition(accuracy, loss.item())
        
        return {
            'loss': loss.item(),
            'accuracy': accuracy,
            'layers': len(self.layers),
            'stage': self.stages[self.current_stage][0],
            'should_grow': should_grow,
            'layer_stats': stats,
        }


def run_optimized_experiment():
    """运行优化版实验"""
    print("="*70)
    print("🚀 优化版20层实验 - 保守生长策略")
    print("="*70)
    print("改进:")
    print("  • 生长阈值: 70% → 80%")
    print("  • 损失阈值: 1.0 → 0.6")
    print("  • 最小训练: 15轮 → 25轮")
    print("="*70)
    
    # 创建模型
    model = OptimizedUltraScaleTNN(
        initial_layers=2,
        hidden_dim=512,
        vocab_size=200,
        blocks_per_layer=4,
    )
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)
    
    # 数据生成
    def generate_batch(task_type, batch_size=6):
        seq_len = 32
        vocab_size = model.vocab_size
        
        if task_type == "sequence":
            seq = torch.arange(seq_len) % vocab_size
        elif task_type == "arithmetic":
            seq = torch.tensor([(i * 3 + 2) % vocab_size for i in range(seq_len)])
        elif task_type == "geometric":
            seq = torch.tensor([(2 ** (i % 8)) % vocab_size for i in range(seq_len)])
        elif task_type == "fibonacci":
            fib = [1, 1]
            for i in range(2, seq_len):
                fib.append((fib[-1] + fib[-2]) % vocab_size)
            seq = torch.tensor(fib)
        else:
            primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
            seq = torch.tensor([primes[i % len(primes)] % vocab_size for i in range(seq_len)])
        
        data = seq.unsqueeze(0).repeat(batch_size, 1)
        target = torch.roll(data, shifts=-1, dims=1)
        return data, target
    
    tasks = ["sequence", "arithmetic", "geometric", "fibonacci", "prime"]
    
    print(f"\n初始状态: {model.num_layers}层")
    print(f"目标: 15层（20层中途中止，验证效果）")
    
    max_epochs = 400
    history = []
    target_layers = 15  # 先测试15层
    
    print("\n开始训练...")
    
    for epoch in range(max_epochs):
        epoch_loss = 0
        epoch_acc = 0
        
        for task in tasks:
            input_ids, targets = generate_batch(task)
            result = model.training_step(input_ids, targets, optimizer)
            
            epoch_loss += result['loss']
            epoch_acc += result['accuracy']
        
        avg_loss = epoch_loss / len(tasks)
        avg_acc = epoch_acc / len(tasks)
        
        history.append({
            'epoch': epoch + 1,
            'loss': avg_loss,
            'accuracy': avg_acc,
            'layers': result['layers'],
        })
        
        # 显示
        if (epoch + 1) % 10 == 0:
            print(f"\n📚 Epoch {epoch + 1}")
            print(f"   损失: {avg_loss:.4f} | 准确率: {avg_acc:.1%}")
            print(f"   层数: {result['layers']}/{target_layers} | 阶段: {result['stage']}")
            
            # 显示每层训练轮数
            layer_epochs = [model.layer_training_epochs.get(i, 0) for i in range(len(model.layers))]
            print(f"   层训练轮数: {layer_epochs[-3:]}")  # 显示最后3层
        
        # 生长
        if result['should_grow'] and result['layers'] < target_layers:
            print(f"\n🌱 触发优化生长!")
            model.grow(num_new_layers=1)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)
        
        # 达到目标
        if result['layers'] >= target_layers and avg_acc > 0.85:
            print(f"\n✅ 达到目标{target_layers}层，准确率{avg_acc:.1%}")
            break
    
    # 结果
    print("\n" + "="*70)
    print("📊 优化版实验结果")
    print("="*70)
    
    print(f"\n最终层数: {model.num_layers}")
    print(f"最终准确率: {avg_acc:.1%}")
    print(f"最终损失: {avg_loss:.4f}")
    
    print(f"\n🌱 生长历史:")
    for event in model.growth_history:
        print(f"   {event['previous_layers']}层 → {event['new_layers']}层 ({event['stage']})")
    
    # 与原版对比
    print("\n" + "="*70)
    print("📈 版本对比")
    print("="*70)
    print("""
┌────────────────┬─────────────┬─────────────┬─────────────┐
│     指标       │  原版20层   │  改进版20层 │  优化版15层 │
├────────────────┼─────────────┼─────────────┼─────────────┤
│ 最终准确率      │    76.9%    │    71.9%    │   {:.1f}%    │
│ 峰值准确率      │    86.0%    │    89.4%    │   {:.1f}%    │
│ 最终损失       │    0.56     │    0.88     │   {:.4f}   │
│ 生长策略       │   激进      │   标准      │   保守     │
└────────────────┴─────────────┴─────────────┴─────────────┘
    """.format(avg_acc * 100, max([h['accuracy'] for h in history]) * 100, avg_loss))
    
    return model, history


if __name__ == "__main__":
    run_optimized_experiment()
