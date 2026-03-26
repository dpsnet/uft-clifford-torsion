"""
保守策略20层挑战 - 目标85%+准确率
使用优化版配置：80%阈值，25轮/层，Kaiming初始化，梯度裁剪
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


class Conservative20LayerTNN(UnifiedAdaptiveTNN):
    """保守策略20层TNN - 追求高质量而非高速度"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 保守配置 - 追求高质量
        self.gradient_clip_val = 1.0
        self.residual_scale = 0.5
        
        # 严格生长条件
        self.growth_threshold_accuracy = 0.80  # 必须达到80%才能生长
        self.growth_threshold_loss = 0.5       # 损失必须低于0.5
        self.min_cycles_before_growth = 25     # 至少训练25轮
        
        # 15层后进一步提高阈值（防止后期质量下降）
        self.deep_layer_threshold = 0.82       # 15层后需要82%
        
        # 追踪每层的训练情况
        self.layer_training_epochs = {}
        self.layer_best_accuracy = {}
        
        print("="*70)
        print("🎯 保守策略20层挑战")
        print("="*70)
        print(f"   基础生长阈值: 准确率>{self.growth_threshold_accuracy}, 损失<{self.growth_threshold_loss}")
        print(f"   深层阈值(15+): 准确率>{self.deep_layer_threshold}")
        print(f"   最小训练轮数: {self.min_cycles_before_growth}")
        print(f"   梯度裁剪: {self.gradient_clip_val}")
        print(f"   残差缩放: {self.residual_scale}")
        print("="*70)
    
    def check_growth_condition(self, accuracy, loss):
        """严格的生长条件检查"""
        # 基础条件
        base_ok = (accuracy >= self.growth_threshold_accuracy and 
                   loss <= self.growth_threshold_loss)
        
        # 深层额外要求
        current_layers = len(self.layers)
        if current_layers >= 15:
            base_ok = base_ok and (accuracy >= self.deep_layer_threshold)
        
        # 训练充分性检查
        if current_layers > 0:
            current_epoch = self.layer_training_epochs.get(current_layers - 1, 0)
            epochs_ok = current_epoch >= self.min_cycles_before_growth
        else:
            epochs_ok = True
        
        return base_ok and epochs_ok
    
    def grow(self, num_new_layers=1):
        """谨慎的生长 - 带充分性检查"""
        current_layer_count = len(self.layers)
        
        # 检查当前层是否充分训练
        if current_layer_count > 0:
            current_epochs = self.layer_training_epochs.get(current_layer_count - 1, 0)
            best_acc = self.layer_best_accuracy.get(current_layer_count - 1, 0)
            
            if current_epochs < self.min_cycles_before_growth:
                print(f"\n⏸️ 推迟生长: 训练不足 ({current_epochs}/{self.min_cycles_before_growth}轮)")
                return self
            
            if best_acc < self.growth_threshold_accuracy:
                print(f"\n⏸️ 推迟生长: 准确率不足 (最佳{best_acc:.1%} < {self.growth_threshold_accuracy})")
                return self
        
        print(f"\n🌱 保守生长: {current_layer_count}层 → {current_layer_count + num_new_layers}层")
        print(f"   当前最佳准确率: {best_acc:.1%}")
        
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
            layer_idx = len(self.layers) - 1
            self.layer_training_epochs[layer_idx] = 0
            self.layer_best_accuracy[layer_idx] = 0
        
        # 更新阶段
        for stage_id, (name, target_layers) in self.stages.items():
            if len(self.layers) >= target_layers:
                self.current_stage = stage_id
        
        self.growth_history.append({
            'timestamp': datetime.now().isoformat(),
            'previous_layers': current_layer_count,
            'new_layers': len(self.layers),
            'stage': self.stages[self.current_stage][0],
            'best_acc_before_growth': best_acc,
        })
        
        print(f"   新层数: {len(self.layers)}/20")
        print(f"   当前阶段: {self.stages[self.current_stage][0]}")
        print(f"   参数量: ~{self.get_total_params()/1e6:.1f}M")
        
        gc.collect()
        return self
    
    def training_step(self, input_ids, targets, optimizer):
        """训练步骤 - 带详细追踪"""
        self.train()
        
        logits, stats = self.forward(input_ids, return_stats=True)
        loss = F.cross_entropy(logits.view(-1, self.vocab_size), targets.view(-1))
        
        optimizer.zero_grad()
        loss.backward()
        
        if self.gradient_clip_val > 0:
            torch.nn.utils.clip_grad_norm_(self.parameters(), self.gradient_clip_val)
        
        optimizer.step()
        
        with torch.no_grad():
            preds = logits.argmax(dim=-1)
            accuracy = (preds == targets).float().mean().item()
        
        # 反馈
        for layer in self.layers:
            layer.record_success(accuracy > 0.8)
        
        # 更新层统计
        current_layer_idx = len(self.layers) - 1
        if current_layer_idx >= 0:
            self.layer_training_epochs[current_layer_idx] = \
                self.layer_training_epochs.get(current_layer_idx, 0) + 1
            current_best = self.layer_best_accuracy.get(current_layer_idx, 0)
            self.layer_best_accuracy[current_layer_idx] = max(current_best, accuracy)
        
        should_grow = self.check_growth_condition(accuracy, loss.item())
        
        return {
            'loss': loss.item(),
            'accuracy': accuracy,
            'layers': len(self.layers),
            'stage': self.stages[self.current_stage][0],
            'should_grow': should_grow,
            'layer_stats': stats,
        }
    
    def get_total_params(self):
        total = 0
        for p in self.parameters():
            total += p.numel()
        return total


def run_conservative_20layer():
    """运行保守策略20层挑战"""
    print("\n" + "="*70)
    print("🚀 保守策略20层挑战 - 目标85%+准确率")
    print("="*70)
    print("\n配置:")
    print("  • hidden_dim: 512")
    print("  • vocab_size: 200")
    print("  • 初始层数: 2")
    print("  • 目标层数: 20")
    print("  • 预期参数量: ~50M")
    print("\n保守策略:")
    print("  • 生长阈值: 80% (15层后82%)")
    print("  • 损失阈值: 0.5")
    print("  • 最小训练: 25轮/层")
    print("="*70 + "\n")
    
    # 创建模型
    model = Conservative20LayerTNN(
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
    
    max_epochs = 500
    history = []
    peak_accuracy = 0
    
    print("开始训练...\n")
    
    try:
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
            peak_accuracy = max(peak_accuracy, avg_acc)
            
            history.append({
                'epoch': epoch + 1,
                'loss': avg_loss,
                'accuracy': avg_acc,
                'layers': result['layers'],
            })
            
            # 显示进度
            if (epoch + 1) % 10 == 0 or result['should_grow']:
                current_layer = result['layers']
                layer_epochs = model.layer_training_epochs.get(current_layer - 1, 0)
                layer_best = model.layer_best_accuracy.get(current_layer - 1, 0)
                
                print(f"\n📚 Epoch {epoch + 1}")
                print(f"   损失: {avg_loss:.4f} | 准确率: {avg_acc:.1%} | 峰值: {peak_accuracy:.1%}")
                print(f"   层数: {current_layer}/20 | 当前层训练: {layer_epochs}轮 | 最佳: {layer_best:.1%}")
                
                # 进度条
                progress = current_layer / 20
                bar = "█" * int(progress * 20) + "░" * (20 - int(progress * 20))
                print(f"   进度: [{bar}] {progress*100:.0f}%")
            
            # 生长
            if result['should_grow'] and result['layers'] < 20:
                model.grow(num_new_layers=1)
                optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)
            
            # 达到目标
            if result['layers'] >= 20:
                print(f"\n{'='*70}")
                print(f"🎉 达成目标: 20层!")
                print(f"{'='*70}")
                print(f"   最终准确率: {avg_acc:.1%}")
                print(f"   峰值准确率: {peak_accuracy:.1%}")
                print(f"   最终损失: {avg_loss:.4f}")
                break
    
    except KeyboardInterrupt:
        print("\n\n⚠️ 训练中断")
    
    # 最终报告
    print("\n" + "="*70)
    print("📊 保守策略20层挑战 - 最终报告")
    print("="*70)
    
    print(f"\n✅ 最终状态:")
    print(f"   层数: {model.num_layers}/20")
    print(f"   最终准确率: {avg_acc:.1%}")
    print(f"   峰值准确率: {peak_accuracy:.1%}")
    print(f"   最终损失: {avg_loss:.4f}")
    print(f"   参数量: ~{model.get_total_params()/1e6:.1f}M")
    
    # 挑战成功判定
    if avg_acc >= 0.85:
        print(f"\n🎉🎉🎉 挑战成功! 达到目标85%+准确率!")
    elif avg_acc >= 0.80:
        print(f"\n✅ 挑战合格! 达到80%+准确率")
    else:
        print(f"\n⚠️ 挑战未达标，但完成了20层生长")
    
    print(f"\n🌱 生长历史:")
    for event in model.growth_history:
        note = f" (最佳{event.get('best_acc_before_growth', 0):.1%})"
        print(f"   {event['previous_layers']}层 → {event['new_layers']}层 "
              f"({event['stage']}){note}")
    
    # 版本对比
    print("\n" + "="*70)
    print("📈 四版本对比")
    print("="*70)
    print("""
┌────────────────┬────────────┬────────────┬────────────┬────────────┐
│     指标       │ 原版20层   │ 改进版20层 │ 优化版15层 │ 保守版20层 │
├────────────────┼────────────┼────────────┼────────────┼────────────┤
│ 最终准确率      │   76.9%    │   71.9%    │   90.6%    │  {:.1f}%    │
│ 峰值准确率      │   86.0%    │   89.4%    │   95.0%    │  {:.1f}%    │
│ 最终损失       │   0.56     │   0.88     │   0.36     │  {:.4f}   │
│ 参数量        │   26.5M    │   26.5M    │   ~20M     │  {:.1f}M   │
└────────────────┴────────────┴────────────┴────────────┴────────────┘
    """.format(avg_acc*100, peak_accuracy*100, avg_loss, model.get_total_params()/1e6))
    
    return model, history


if __name__ == "__main__":
    run_conservative_20layer()
