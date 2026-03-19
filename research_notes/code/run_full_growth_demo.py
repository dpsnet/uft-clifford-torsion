"""
运行完整生长演示 - 展示从2层到6层的完整生长过程
降低阈值，加速展示效果
"""

import torch
import torch.nn.functional as F
import sys
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')
from unified_adaptive_tnn import UnifiedAdaptiveTNN
import json
from datetime import datetime


def run_full_growth_demo():
    """运行完整生长演示"""
    print("="*70)
    print("🌱 完整生长演示 - 2层 → 6层")
    print("="*70)
    print("降低生长阈值，加速展示层生长过程")
    print("="*70)
    
    # 创建模型
    model = UnifiedAdaptiveTNN(
        initial_layers=2,
        hidden_dim=64,
        vocab_size=30,
        blocks_per_layer=4,
    )
    
    # 降低生长阈值以便更快展示
    model.growth_threshold_accuracy = 0.70  # 降低到70%
    model.growth_threshold_loss = 0.5       # 放宽到0.5
    model.min_cycles_before_growth = 10     # 减少到10轮
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)  # 稍大学习率
    
    # 生成训练数据
    def generate_batch(task_type: str, batch_size: int = 8):
        if task_type == "simple":
            seq = torch.arange(20) % 30
        elif task_type == "pattern":
            seq = torch.tensor([i * 2 % 30 for i in range(20)])
        else:  # complex
            seq = torch.tensor([(i * 3 + 1) % 30 for i in range(20)])
        
        data = seq.unsqueeze(0).repeat(batch_size, 1)
        target = torch.roll(data, shifts=-1, dims=1)
        return data, target
    
    tasks = ["simple", "pattern", "complex"]
    
    # 记录
    history = {
        'start_time': datetime.now().isoformat(),
        'epochs': [],
        'growth_events': [],
    }
    
    print(f"\n初始状态:")
    print(f"  层数: {model.num_layers}")
    print(f"  阶段: {model.stages[model.current_stage][0]}")
    print(f"  生长阈值: 准确率>{model.growth_threshold_accuracy:.0%}, 损失<{model.growth_threshold_loss}")
    
    print("\n" + "-"*70)
    print("开始训练...")
    print("-"*70)
    
    growth_count = 0
    max_epochs = 100
    
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
        
        # 记录
        history['epochs'].append({
            'epoch': epoch + 1,
            'loss': avg_loss,
            'accuracy': avg_acc,
            'layers': result['layers'],
            'stage': result['stage'],
        })
        
        # 每5轮显示状态
        if (epoch + 1) % 5 == 0:
            print(f"\n📚 Epoch {epoch + 1}/{max_epochs}")
            print(f"   损失: {avg_loss:.4f} | 准确率: {avg_acc:.1%}")
            print(f"   层数: {result['layers']} | 阶段: {result['stage']}")
            
            # 显示每层块加载情况
            for li, ls in enumerate(result['layer_stats']):
                print(f"   层{li}: {ls['block_count']}块加载 "
                      f"兴奋度={ls['avg_excitement']:.2f}")
        
        # 检查并执行生长
        if result['should_grow'] and result['layers'] < 6:
            growth_count += 1
            print(f"\n" + "="*70)
            print(f"🌱🌱🌱 触发第{growth_count}次生长! 🌱🌱🌱")
            print(f"="*70)
            print(f"条件满足: 准确率{avg_acc:.1%} > {model.growth_threshold_accuracy:.0%}")
            print(f"          损失{avg_loss:.4f} < {model.growth_threshold_loss}")
            
            model.grow(num_new_layers=1)
            
            history['growth_events'].append({
                'epoch': epoch + 1,
                'previous_layers': result['layers'],
                'new_layers': model.num_layers,
                'new_stage': model.stages[model.current_stage][0],
            })
            
            # 更新优化器
            optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
            
            print(f"="*70)
        
        # 达到6层停止
        if model.num_layers >= 6:
            print(f"\n✅ 达到目标层数(6层)，停止训练")
            break
    
    # 最终状态
    print("\n" + "="*70)
    print("📊 最终状态")
    print("="*70)
    
    model.print_unified_status()
    
    # 生长历史
    print(f"\n🌱 生长历史:")
    for event in history['growth_events']:
        print(f"   Epoch {event['epoch']}: {event['previous_layers']}层 → {event['new_layers']}层 "
              f"(进入{event['new_stage']}阶段)")
    
    # 保存结果
    history['end_time'] = datetime.now().isoformat()
    history['final_layers'] = model.num_layers
    history['final_stage'] = model.stages[model.current_stage][0]
    
    with open('./growth_demo_result.json', 'w') as f:
        json.dump(history, f, indent=2)
    
    print(f"\n💾 结果已保存: growth_demo_result.json")
    
    print("\n" + "="*70)
    print("演示完成!")
    print("="*70)
    
    return model, history


if __name__ == "__main__":
    run_full_growth_demo()
