"""
Phase B1: 胚胎期 - 感觉-运动映射
目标：最简单的输入-输出映射（趋光性/避光性）

设计：
- 输入：光传感器（单一数值：光强度）
- 输出：运动控制（转向角度）
- 任务：趋光（向光源移动）或避光（远离光源）
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import matplotlib.pyplot as plt
import numpy as np


class EmbryoTNN(nn.Module):
    """胚胎期TNN - 最简单的2层感觉-运动映射"""
    
    def __init__(self, sensor_dim=1, motor_dim=1, hidden_dim=16):
        super().__init__()
        self.sensor_dim = sensor_dim
        self.motor_dim = motor_dim
        
        # 感觉输入层
        self.sensor_input = nn.Linear(sensor_dim, hidden_dim)
        
        # 2层内部处理（胚胎期最小结构）
        self.layer1 = nn.ModuleDict({
            'norm': nn.LayerNorm(hidden_dim),
            'process': nn.Linear(hidden_dim, hidden_dim),
        })
        
        self.layer2 = nn.ModuleDict({
            'norm': nn.LayerNorm(hidden_dim),
            'process': nn.Linear(hidden_dim, hidden_dim),
        })
        
        # 运动输出层
        self.motor_output = nn.Linear(hidden_dim, motor_dim)
        
        # 状态
        self.stage = "embryo"
        self.learning_steps = 0
    
    def forward(self, sensor_input):
        """
        输入: [batch, sensor_dim] - 光强度
        输出: [batch, motor_dim] - 转向角度
        """
        # 感觉输入
        h = self.sensor_input(sensor_input)
        h = torch.relu(h)
        
        # 第1层处理
        residual = h
        h = self.layer1['norm'](h)
        h = self.layer1['process'](h)
        h = torch.tanh(h)
        h = residual + h * 0.3
        
        # 第2层处理
        residual = h
        h = self.layer2['norm'](h)
        h = self.layer2['process'](h)
        h = torch.tanh(h)
        h = residual + h * 0.3
        
        # 运动输出
        motor_output = self.motor_output(h)
        motor_output = torch.tanh(motor_output)  # 限制在 -1 到 1
        
        return motor_output
    
    def get_info(self):
        return {
            'stage': self.stage,
            'layers': 2,
            'params': sum(p.numel() for p in self.parameters()),
            'learning_steps': self.learning_steps,
        }


class LightEnvironment:
    """简单的光照环境模拟"""
    
    def __init__(self, world_size=100):
        self.world_size = world_size
        self.light_source = np.array([world_size/2, world_size/2])  # 光源在中心
        self.light_intensity = 100.0  # 光强度
    
    def get_light_reading(self, position):
        """获取位置的光照强度（距离越近越亮）"""
        distance = np.linalg.norm(position - self.light_source)
        # 光照随距离衰减
        intensity = self.light_intensity / (1 + distance / 10)
        return intensity
    
    def generate_training_data(self, num_samples=1000):
        """生成训练数据"""
        data = []
        
        for _ in range(num_samples):
            # 随机位置
            pos = np.random.uniform(0, self.world_size, 2)
            
            # 计算光照强度（输入）
            light = self.get_light_reading(pos)
            
            # 计算最优动作（向光源移动的方向）
            direction = self.light_source - pos
            if np.linalg.norm(direction) > 0:
                direction = direction / np.linalg.norm(direction)
            
            # 转向角度（输出）：-1（左转）到 1（右转）
            # 简化：使用x方向作为转向信号
            turn = np.clip(direction[0] / 2, -1, 1)
            
            data.append({
                'position': pos,
                'light': light,
                'turn': turn,
            })
        
        return data


def train_embryo():
    """训练胚胎期模型"""
    print("="*60)
    print("Phase B1: 胚胎期 - 感觉-运动映射")
    print("="*60)
    print("\n任务：趋光性（Phototaxis）")
    print("输入：光传感器（单一数值）")
    print("输出：转向控制（-1到1）")
    print("-"*60)
    
    # 创建模型
    model = EmbryoTNN(sensor_dim=1, motor_dim=1, hidden_dim=16)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()
    
    info = model.get_info()
    print(f"\n模型信息：")
    print(f"  阶段: {info['stage']}")
    print(f"  层数: {info['layers']}")
    print(f"  参数量: {info['params']:,}")
    print(f"  隐藏维度: 16")
    
    # 创建环境
    env = LightEnvironment(world_size=100)
    training_data = env.generate_training_data(num_samples=500)  # 减少样本数
    
    print(f"\n训练数据：")
    print(f"  样本数: {len(training_data)}")
    print(f"  光照范围: {min(d['light'] for d in training_data):.1f} - {max(d['light'] for d in training_data):.1f}")
    
    # 训练
    print(f"\n开始训练...")
    print("-"*60)
    
    history = []
    
    for epoch in range(50):  # 减少 epoch
        total_loss = 0
        correct_direction = 0
        total = 0
        
        for sample in training_data:
            light = torch.tensor([[sample['light']]], dtype=torch.float32)
            target_turn = torch.tensor([[sample['turn']]], dtype=torch.float32)
            
            # 前向
            pred_turn = model(light)
            loss = criterion(pred_turn, target_turn)
            
            # 反向
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
            # 统计方向正确率
            if (pred_turn.item() > 0) == (target_turn.item() > 0):
                correct_direction += 1
            total += 1
        
        avg_loss = total_loss / len(training_data)
        accuracy = correct_direction / total
        model.learning_steps = epoch + 1
        
        if (epoch + 1) % 20 == 0:
            print(f"Epoch {epoch+1:3d} | Loss: {avg_loss:.4f} | Direction Acc: {accuracy:.3f}")
            history.append({'epoch': epoch+1, 'loss': avg_loss, 'accuracy': accuracy})
    
    # 最终评估
    print("-"*60)
    print("\n最终评估...")
    
    test_data = env.generate_training_data(num_samples=500)
    correct = 0
    total = 0
    
    model.eval()
    with torch.no_grad():
        for sample in test_data:
            light = torch.tensor([[sample['light']]], dtype=torch.float32)
            target = sample['turn']
            
            pred = model(light).item()
            
            # 判断方向是否正确
            if (pred > 0) == (target > 0):
                correct += 1
            total += 1
    
    final_accuracy = correct / total
    
    print(f"\n测试结果：")
    print(f"  方向正确率: {final_accuracy:.3f}")
    
    info = model.get_info()
    print(f"\n最终状态：")
    print(f"  阶段: {info['stage']}")
    print(f"  学习步数: {info['learning_steps']}")
    print(f"  参数量: {info['params']:,}")
    
    # 解锁条件检查
    unlock_ready = final_accuracy > 0.85
    
    print(f"\n{'='*60}")
    print("Phase B1 结论")
    print("="*60)
    
    if final_accuracy > 0.9:
        print("✅ 胚胎期训练成功！")
        print(f"   方向正确率: {final_accuracy:.1%}")
        print(f"   已准备好解锁记忆期（Phase B2）")
    elif final_accuracy > 0.7:
        print("🟡 基本合格")
        print(f"   方向正确率: {final_accuracy:.1%}")
        print(f"   建议继续训练或调整参数")
    else:
        print("❌ 训练失败")
        print(f"   方向正确率: {final_accuracy:.1%}")
        print(f"   需要重新设计模型或任务")
    
    # 可视化
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # 训练曲线
    epochs = [h['epoch'] for h in history]
    losses = [h['loss'] for h in history]
    accs = [h['accuracy'] for h in history]
    
    axes[0].plot(epochs, losses, 'o-', linewidth=2, markersize=6)
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].set_title('Training Loss')
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(epochs, accs, 's-', linewidth=2, markersize=6, color='green')
    axes[1].axhline(y=0.85, color='r', linestyle='--', alpha=0.5, label='Unlock Threshold (85%)')
    axes[1].axhline(y=0.9, color='g', linestyle='--', alpha=0.5, label='Target (90%)')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Direction Accuracy')
    axes[1].set_title('Training Accuracy')
    axes[1].set_ylim(0, 1.1)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('phase_b1_embryo_training.png', dpi=150)
    print(f"\n训练图已保存: phase_b1_embryo_training.png")
    
    # 保存结果
    result = {
        'stage': 'embryo',
        'final_accuracy': final_accuracy,
        'learning_steps': info['learning_steps'],
        'params': info['params'],
        'unlock_ready': unlock_ready,
        'history': history,
    }
    
    with open('phase_b1_results.json', 'w') as f:
        json.dump(result, f, indent=2)
    print("结果已保存: phase_b1_results.json")
    
    return model, result


if __name__ == "__main__":
    train_embryo()
