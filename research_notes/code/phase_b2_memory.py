"""
Phase B2: 记忆期解锁
目标：添加记忆模块，学会延迟反应任务

解锁条件：胚胎期准确率>90%（已满足）
新增模块：循环连接（短期记忆缓冲区）
新任务：延迟匹配（看到信号→等待→反应）
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json


class MemoryTNN(nn.Module):
    """记忆期TNN - 添加循环记忆模块"""
    
    def __init__(self, hidden=16):
        super().__init__()
        self.stage = "memory"
        
        # 感觉输入
        self.input = nn.Linear(1, hidden)
        
        # 原始2层
        self.l1 = nn.Linear(hidden, hidden)
        self.l2 = nn.Linear(hidden, hidden)
        
        # 新增：记忆模块（循环连接）
        self.memory = nn.Linear(hidden, hidden)
        self.memory_gate = nn.Parameter(torch.zeros(hidden))
        
        # 输出
        self.output = nn.Linear(hidden, 1)
    
    def forward(self, x, prev_hidden=None):
        # 输入层
        h = torch.relu(self.input(x))
        
        # 记忆融合（如果有之前的隐藏状态）
        if prev_hidden is not None:
            gate = torch.sigmoid(self.memory_gate)
            mem = torch.tanh(self.memory(prev_hidden))
            h = h * (1 - gate) + mem * gate
        
        # 处理层
        h = h + torch.tanh(self.l1(h)) * 0.3
        h = h + torch.tanh(self.l2(h)) * 0.3
        
        out = torch.tanh(self.output(h))
        return out, h  # 返回输出和隐藏状态供下次使用


def generate_delayed_task(batch_size, delay_steps=5):
    """生成延迟匹配任务"""
    # 信号（1或-1）
    signal = torch.randint(0, 2, (batch_size, 1)).float() * 2 - 1
    
    # 延迟期间的噪声输入（0）
    delay_inputs = [torch.zeros(batch_size, 1) for _ in range(delay_steps)]
    
    # 目标：延迟后输出信号
    target = signal
    
    return signal, delay_inputs, target


def train():
    print("="*60)
    print("Phase B2: 记忆期解锁 - 延迟反应任务")
    print("="*60)
    print("任务：看到信号→等待5步→输出信号")
    print("新增模块：循环记忆连接")
    print("-"*60)
    
    model = MemoryTNN(16)
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    
    print(f"参数量: {sum(p.numel() for p in model.parameters()):,}")
    print(f"解锁条件: 胚胎期准确率>90% ✅")
    print("-"*60)
    
    # 训练
    for epoch in range(50):
        total_loss = 0
        correct = 0
        total = 0
        
        for _ in range(50):  # 每轮50个样本
            signal, delay_inputs, target = generate_delayed_task(8, delay_steps=5)
            
            # 逐步处理
            hidden = None
            
            # 第1步：看到信号
            out, hidden = model(signal, hidden)
            
            # 第2-6步：延迟期
            for delay_input in delay_inputs:
                out, hidden = model(delay_input, hidden)
            
            # 计算损失（最后一步输出应该匹配信号）
            loss = (out - target).pow(2).mean()
            
            opt.zero_grad()
            loss.backward()
            opt.step()
            
            total_loss += loss.item()
            
            # 统计
            pred_match = ((out > 0) == (target > 0)).float().mean().item()
            correct += pred_match * 8
            total += 8
        
        acc = correct / total
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1:2d} | Loss: {total_loss/50:.4f} | Delay Acc: {acc:.3f}")
    
    # 测试
    test_correct = 0
    test_total = 0
    
    for _ in range(100):
        signal, delay_inputs, target = generate_delayed_task(1, delay_steps=5)
        hidden = None
        
        # 看到信号
        out, hidden = model(signal, hidden)
        
        # 延迟期
        for delay_input in delay_inputs:
            out, hidden = model(delay_input, hidden)
        
        if (out.item() > 0) == (target.item() > 0):
            test_correct += 1
        test_total += 1
    
    final_acc = test_correct / test_total
    
    print("-"*60)
    print(f"最终延迟匹配准确率: {final_acc:.3f}")
    
    if final_acc > 0.8:
        print("✅ 记忆期解锁成功！")
        print("  模型能记住信号并在延迟后正确输出")
        print("  准备解锁语言期（Phase B3）")
    else:
        print("🟡 需要更多训练")
    
    with open('phase_b2_results.json', 'w') as f:
        json.dump({
            'stage': 'memory',
            'accuracy': final_acc,
            'params': sum(p.numel() for p in model.parameters()),
            'added_module': 'recurrent_memory',
        }, f)
    
    return model


if __name__ == "__main__":
    train()
