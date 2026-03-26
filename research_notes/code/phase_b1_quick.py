"""
Phase B1: 胚胎期 - 简化版
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json


class EmbryoTNN(nn.Module):
    def __init__(self, hidden=16):
        super().__init__()
        self.input = nn.Linear(1, hidden)
        self.l1 = nn.Linear(hidden, hidden)
        self.l2 = nn.Linear(hidden, hidden)
        self.output = nn.Linear(hidden, 1)
    
    def forward(self, x):
        h = torch.relu(self.input(x))
        h = h + torch.tanh(self.l1(h)) * 0.3
        h = h + torch.tanh(self.l2(h)) * 0.3
        return torch.tanh(self.output(h))


def train():
    print("="*50)
    print("Phase B1: 胚胎期 - 趋光性学习")
    print("="*50)
    
    model = EmbryoTNN(16)
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    
    print(f"参数量: {sum(p.numel() for p in model.parameters()):,}")
    print("-"*50)
    
    # 生成数据：光强度 -> 转向
    data = []
    for _ in range(500):
        light = torch.rand(1) * 10  # 0-10
        target = (light - 5) / 5  # -1 到 1
        data.append((light, target))
    
    # 训练
    for epoch in range(30):
        total_loss = 0
        correct = 0
        
        for light, target in data:
            pred = model(light.unsqueeze(0))
            loss = (pred - target).pow(2).mean()
            
            opt.zero_grad()
            loss.backward()
            opt.step()
            
            total_loss += loss.item()
            if (pred.item() > 0) == (target.item() > 0):
                correct += 1
        
        acc = correct / len(data)
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1:2d} | Loss: {total_loss/len(data):.4f} | Acc: {acc:.3f}")
    
    # 测试
    test_correct = 0
    for light, target in data[:100]:
        pred = model(light.unsqueeze(0))
        if (pred.item() > 0) == (target.item() > 0):
            test_correct += 1
    
    final_acc = test_correct / 100
    print("-"*50)
    print(f"最终准确率: {final_acc:.3f}")
    
    if final_acc > 0.85:
        print("✅ 胚胎期训练成功！准备解锁记忆期")
    else:
        print("🟡 需要更多训练")
    
    with open('phase_b1_quick.json', 'w') as f:
        json.dump({'accuracy': final_acc, 'params': sum(p.numel() for p in model.parameters())}, f)
    
    return model

if __name__ == "__main__":
    train()
