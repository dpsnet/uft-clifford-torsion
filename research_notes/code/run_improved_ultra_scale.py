"""
改进版超大规模实验 - 20层目标
使用所有改进措施：Kaiming初始化、梯度裁剪、残差缩放
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


class ImprovedUltraScaleTNN(UnifiedAdaptiveTNN):
    """改进版超大规模TNN - 解决深层准确率下降"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 改进配置
        self.gradient_clip_val = 1.0
        self.residual_scale = 0.5
        self.use_improved_init = True
        
        print("✅ 改进版配置已启用:")
        print(f"   梯度裁剪: {self.gradient_clip_val}")
        print(f"   残差缩放: {self.residual_scale}")
        print(f"   改进初始化: Kaiming")
    
    def grow(self, num_new_layers=1):
        """改进的生长 - 更好的初始化"""
        print(f"\n🌱 改进版生长: {len(self.layers)}层 → {len(self.layers) + num_new_layers}层")
        
        for i in range(num_new_layers):
            new_layer = AdaptiveLayer(
                len(self.layers) + i,
                self.hidden_dim,
                (2, 2),
                self.blocks_per_layer
            )
            
            # 改进初始化
            with torch.no_grad():
                for name, p in new_layer.named_parameters():
                    if 'weight' in name and len(p.shape) >= 2:
                        nn.init.kaiming_normal_(p, mode='fan_out', nonlinearity='relu')
                    elif 'bias' in name:
                        nn.init.zeros_(p)
                    elif 'norm' in name.lower() and 'weight' in name:
                        nn.init.ones_(p)
                
                # 扭转门小值
                for block in new_layer.blocks:
                    nn.init.normal_(block.torsion_gate, mean=0, std=0.001)
            
            self.layers.append(new_layer)
        
        # 更新阶段
        for stage_id, (name, target_layers) in self.stages.items():
            if len(self.layers) >= target_layers:
                self.current_stage = stage_id
        
        self.growth_history.append({
            'timestamp': datetime.now().isoformat(),
            'previous_layers': len(self.layers) - num_new_layers,
            'new_layers': len(self.layers),
            'stage': self.stages[self.current_stage][0],
        })
        
        print(f"   新层数: {len(self.layers)}")
        print(f"   新阶段: {self.stages[self.current_stage][0]}")
        print(f"   估计参数量: ~{self.get_total_params() / 1e6:.1f}M")
        
        # 内存清理
        gc.collect()
        
        return self
    
    def training_step(self, input_ids, targets, optimizer):
        """改进的训练步骤 - 添加梯度裁剪"""
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
            layer.record_success(accuracy > 0.7)
        
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
    
    def get_total_params(self):
        base = 0
        for module in [self.embedding, self.lm_head]:
            for p in module.parameters():
                base += p.numel()
        
        if len(self.layers) > 0:
            layer_params = 0
            for p in self.layers[0].parameters():
                layer_params += p.numel()
            return base + layer_params * len(self.layers)
        return base


def run_improved_ultra_scale():
    """运行改进版超大规模实验"""
    print("="*70)
    print("🚀 改进版超大规模实验 - 目标20层")
    print("="*70)
    print("配置: hidden_dim=512, vocab_size=200")
    print("改进: Kaiming初始化 + 梯度裁剪 + 残差缩放")
    print("="*70)
    
    # 创建模型
    model = ImprovedUltraScaleTNN(
        initial_layers=2,
        hidden_dim=512,
        vocab_size=200,
        blocks_per_layer=4,
    )
    
    # 调整阈值
    model.growth_threshold_accuracy = 0.70
    model.growth_threshold_loss = 1.0
    model.min_cycles_before_growth = 15
    
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
    print(f"生长阈值: 准确率>70%, 损失<1.0")
    
    # 训练
    max_epochs = 300
    history = []
    
    print("\n" + "-"*70)
    print("开始训练...")
    print("-"*70)
    
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
            
            history.append({
                'epoch': epoch + 1,
                'loss': avg_loss,
                'accuracy': avg_acc,
                'layers': result['layers'],
            })
            
            # 显示
            if (epoch + 1) % 10 == 0:
                current_params = model.get_total_params()
                print(f"\n📚 Epoch {epoch + 1}/{max_epochs}")
                print(f"   损失: {avg_loss:.4f} | 准确率: {avg_acc:.1%}")
                print(f"   层数: {result['layers']}/20 | 参数量: ~{current_params/1e6:.1f}M")
                print(f"   阶段: {result['stage']}")
            
            # 生长
            if result['should_grow'] and result['layers'] < 20:
                print(f"\n🌱 触发生长! {result['layers']} → {result['layers']+1}层")
                model.grow(num_new_layers=1)
                optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)
            
            # 达到目标
            if result['layers'] >= 20:
                print(f"\n✅ 达到目标20层!")
                break
    
    except KeyboardInterrupt:
        print(f"\n\n⚠️ 训练中断")
        return model, history
    
    # 结果
    print("\n" + "="*70)
    print("📊 改进版超大规模实验结果")
    print("="*70)
    
    print(f"\n最终层数: {model.num_layers}")
    print(f"最终阶段: {model.stages[model.current_stage][0]}")
    print(f"最终准确率: {avg_acc:.1%}")
    print(f"最终损失: {avg_loss:.4f}")
    print(f"估计参数量: ~{model.get_total_params()/1e6:.1f}M")
    
    print(f"\n🌱 生长历史:")
    for event in model.growth_history:
        print(f"   {event['previous_layers']}层 → {event['new_layers']}层 ({event['stage']})")
    
    # 层间对比
    print(f"\n📈 层间训练情况:")
    for i, layer in enumerate(model.layers):
        print(f"   层{i}: 激活{layer.layer_stats['activations']}次")
    
    print("\n" + "="*70)
    print("实验完成!")
    print("="*70)
    
    return model, history


if __name__ == "__main__":
    run_improved_ultra_scale()
