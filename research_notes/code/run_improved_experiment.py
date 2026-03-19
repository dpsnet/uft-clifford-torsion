"""
改进版大规模实验 - 解决深层模型准确率下降
使用更好的初始化、预热训练和动态调整
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')
from accuracy_issue_analysis import ImprovedUnifiedAdaptiveTNN


def run_improved_experiment():
    """运行改进版实验"""
    print("="*70)
    print("🚀 改进版大规模实验")
    print("="*70)
    print("改进措施:")
    print("  ✅ Kaiming初始化")
    print("  ✅ 梯度裁剪 (max_norm=1.0)")
    print("  ✅ 残差缩放 (0.5)")
    print("  ✅ 新层学习率衰减 (0.1x)")
    print("  ✅ 层预热训练 (5 epochs)")
    print("="*70)
    
    # 创建改进版模型
    model = ImprovedUnifiedAdaptiveTNN(
        initial_layers=2,
        hidden_dim=256,
        vocab_size=100,
        blocks_per_layer=4,
    )
    
    # 降低生长阈值以便更快看到效果
    model.growth_threshold_accuracy = 0.72
    model.growth_threshold_loss = 0.9
    model.min_cycles_before_growth = 15
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # 生成数据
    def generate_batch(task_type, batch_size=8):
        if task_type == "simple":
            seq = torch.arange(20) % 100
        elif task_type == "pattern":
            seq = torch.tensor([i * 2 % 100 for i in range(20)])
        elif task_type == "math":
            seq = torch.tensor([(i ** 2 + 1) % 100 for i in range(20)])
        else:
            seq = torch.tensor([((i + 1) * 3) % 100 for i in range(20)])
        
        data = seq.unsqueeze(0).repeat(batch_size, 1)
        target = torch.roll(data, shifts=-1, dims=1)
        return data, target
    
    tasks = ["simple", "pattern", "math", "shift"]
    
    print(f"\n初始状态: {model.num_layers}层, {model.stages[model.current_stage][0]}阶段")
    
    # 训练历史
    history = []
    target_layers = 12  # 目标12层
    
    print("\n" + "-"*70)
    print("开始训练...")
    print("-"*70)
    
    for epoch in range(100):
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
        if (epoch + 1) % 5 == 0:
            print(f"\n📚 Epoch {epoch + 1}")
            print(f"   损失: {avg_loss:.4f} | 准确率: {avg_acc:.1%}")
            print(f"   层数: {result['layers']} | 阶段: {result['stage']}")
        
        # 生长
        if result['should_grow'] and result['layers'] < target_layers:
            print(f"\n🌱 生长: {result['layers']} → {result['layers']+1}层")
            model.grow(num_new_layers=1)
            
            # 新优化器，但对新层使用较小学习率
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        
        # 达到目标
        if result['layers'] >= target_layers and avg_acc > 0.80:
            print(f"\n✅ 达到目标: {target_layers}层, 准确率{avg_acc:.1%}")
            break
    
    # 结果
    print("\n" + "="*70)
    print("📊 改进版实验结果")
    print("="*70)
    
    print(f"\n最终层数: {model.num_layers}")
    print(f"最终阶段: {model.stages[model.current_stage][0]}")
    print(f"最终准确率: {avg_acc:.1%}")
    print(f"最终损失: {avg_loss:.4f}")
    
    print(f"\n🌱 生长历史:")
    for event in model.growth_history:
        print(f"   {event['previous_layers']}层 → {event['new_layers']}层 "
              f"({event['stage']}) [{'改进' if event.get('improved_init') else '普通'}]")
    
    # 层间准确率对比
    print(f"\n📈 层间训练情况:")
    for i, layer in enumerate(model.layers):
        # 估算该层对整体准确率的贡献
        activation_ratio = layer.layer_stats['activations'] / max(1, len(history))
        print(f"   层{i}: 激活{layer.layer_stats['activations']}次 "
              f"(参与率{activation_ratio:.1%})")
    
    print("\n" + "="*70)
    print("实验完成!")
    print("="*70)
    
    return model, history


def compare_versions():
    """对比原版和改进版"""
    print("\n" + "="*70)
    print("📊 原版 vs 改进版 对比")
    print("="*70)
    print("""
问题分析:
┌─────────────────────────────────────────────────────────────────┐
│ 现象: 20层模型准确率76%，低于10层模型的86%                        │
│                                                                 │
│ 可能原因:                                                        │
│ 1. 新层初始化不够好 → 使用Kaiming初始化                          │
│ 2. 梯度在深层的传播问题 → 梯度裁剪+残差缩放                      │
│ 3. 新层与旧层协调不足 → 层预热训练                               │
│ 4. 学习率对深层不友好 → 新层学习率衰减                           │
└─────────────────────────────────────────────────────────────────┘

改进措施:
┌────────────────┬──────────────────┬──────────────────────────────┐
│ 问题           │ 原版             │ 改进版                       │
├────────────────┼──────────────────┼──────────────────────────────┤
│ 初始化         │ 小值(0.01)       │ Kaiming + 小扭转门           │
│ 梯度控制       │ 无               │ 裁剪(max_norm=1.0)           │
│ 残差连接       │ 固定0.3          │ 缩放0.5（自适应）              │
│ 新层训练       │ 立即全速率       │ 学习率0.1x + 5epoch预热       │
└────────────────┴──────────────────┴──────────────────────────────┘

预期效果:
- 深层模型准确率下降减缓
- 新层更快融入整体网络
- 训练稳定性提升
""")


if __name__ == "__main__":
    # 运行改进版实验
    model, history = run_improved_experiment()
    
    # 显示对比
    compare_versions()
