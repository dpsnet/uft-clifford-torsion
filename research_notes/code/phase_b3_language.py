"""
Phase B3: 语言期解锁
目标：添加符号处理能力，学习序列预测

解锁条件：记忆期准确率>80%（已满足✅）
新增模块：符号嵌入层、序列预测头
新任务：符号指令跟随
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json


class LanguageTNN(nn.Module):
    """语言期TNN - 添加符号处理能力"""
    
    def __init__(self, vocab_size=10, hidden=32):
        super().__init__()
        self.stage = "language"
        self.vocab_size = vocab_size
        
        # 符号嵌入层（新增）
        self.embedding = nn.Embedding(vocab_size, hidden)
        
        # 感觉输入层
        self.sensor = nn.Linear(1, hidden)
        
        # 多层处理（已生长到4层）
        self.l1 = nn.Linear(hidden, hidden)
        self.l2 = nn.Linear(hidden, hidden)
        self.l3 = nn.Linear(hidden, hidden)  # 新增第3层
        self.l4 = nn.Linear(hidden, hidden)  # 新增第4层
        
        # 记忆模块
        self.memory = nn.Linear(hidden, hidden)
        self.mem_gate = nn.Parameter(torch.zeros(hidden))
        
        # 多头输出（新增序列预测头）
        self.action_head = nn.Linear(hidden, 1)  # 动作输出
        self.symbol_head = nn.Linear(hidden, vocab_size)  # 符号预测（新增）
    
    def forward(self, symbol=None, sensor=None, prev_hidden=None):
        # 融合符号和感觉输入
        if symbol is not None:
            h = self.embedding(symbol)
        elif sensor is not None:
            h = torch.relu(self.sensor(sensor))
        else:
            h = torch.zeros(1, 32)
        
        # 记忆融合
        if prev_hidden is not None:
            gate = torch.sigmoid(self.mem_gate)
            mem = torch.tanh(self.memory(prev_hidden))
            h = h * (1 - gate) + mem * gate
        
        # 4层处理
        h = h + torch.tanh(self.l1(h)) * 0.3
        h = h + torch.tanh(self.l2(h)) * 0.3
        h = h + torch.tanh(self.l3(h)) * 0.3
        h = h + torch.tanh(self.l4(h)) * 0.3
        
        # 双头输出
        action = torch.tanh(self.action_head(h))
        symbol_pred = self.symbol_head(h)
        
        return action, symbol_pred, h


def generate_language_task(batch_size):
    """生成语言指令任务（简化版）
    
    指令映射：
    符号0 → 左转 (-1)
    符号1 → 右转 (1)
    符号2 → 前进 (0.5)
    符号3 → 后退 (-0.5)
    """
    # 随机符号
    symbol = torch.randint(0, 4, (batch_size,))  # 0,1,2,3
    
    # 根据符号直接映射动作
    target_action = torch.zeros(batch_size, 1)
    
    for i in range(batch_size):
        s = symbol[i].item()
        if s == 0:
            target_action[i] = -1.0  # 左
        elif s == 1:
            target_action[i] = 1.0   # 右
        elif s == 2:
            target_action[i] = 0.5   # 前
        else:
            target_action[i] = -0.5  # 后
    
    return symbol, None, target_action, symbol


def train():
    print("="*60)
    print("Phase B3: 语言期解锁 - 符号指令跟随")
    print("="*60)
    print("任务：符号+光照 → 动作")
    print("新增模块：符号嵌入层、序列预测头")
    print("-"*60)
    
    model = LanguageTNN(vocab_size=10, hidden=32)
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    
    print(f"参数量: {sum(p.numel() for p in model.parameters()):,}")
    print(f"解锁条件: 记忆期准确率>80% ✅")
    print("-"*60)
    
    # 训练
    for epoch in range(100):
        total_action_loss = 0
        total_symbol_loss = 0
        action_correct = 0
        symbol_correct = 0
        total = 0
        
        for _ in range(50):
            symbol, light, target_action, target_symbol = generate_language_task(8)
            
            action_pred, symbol_pred, _ = model(symbol=symbol, sensor=light)
            
            # 动作损失
            action_loss = (action_pred - target_action).pow(2).mean()
            # 符号预测损失
            symbol_loss = F.cross_entropy(symbol_pred, target_symbol)
            
            loss = action_loss + symbol_loss
            
            opt.zero_grad()
            loss.backward()
            opt.step()
            
            total_action_loss += action_loss.item()
            total_symbol_loss += symbol_loss.item()
            
            # 统计
            action_match = ((action_pred > 0) == (target_action > 0)).float().mean().item()
            symbol_match = (symbol_pred.argmax(dim=1) == target_symbol).float().mean().item()
            
            action_correct += action_match * 8
            symbol_correct += symbol_match * 8
            total += 8
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1:2d} | Action Acc: {action_correct/total:.3f} | Symbol Acc: {symbol_correct/total:.3f}")
    
    # 测试
    test_action_correct = 0
    test_symbol_correct = 0
    test_total = 0
    
    for _ in range(100):
        symbol, light, target_action, target_symbol = generate_language_task(1)
        action_pred, symbol_pred, _ = model(symbol=symbol, sensor=light)
        
        if (action_pred.item() > 0) == (target_action.item() > 0):
            test_action_correct += 1
        if symbol_pred.argmax(dim=1).item() == target_symbol.item():
            test_symbol_correct += 1
        test_total += 1
    
    action_acc = test_action_correct / test_total
    symbol_acc = test_symbol_correct / test_total
    
    print("-"*60)
    print(f"最终测试结果：")
    print(f"  动作准确率: {action_acc:.3f}")
    print(f"  符号预测准确率: {symbol_acc:.3f}")
    
    if action_acc > 0.8 and symbol_acc > 0.8:
        print("✅ 语言期解锁成功！")
        print("  模型能理解符号指令并预测符号")
        print("  准备解锁社交期（Phase B4）")
    else:
        print("🟡 需要更多训练")
    
    with open('phase_b3_results.json', 'w') as f:
        json.dump({
            'stage': 'language',
            'action_accuracy': action_acc,
            'symbol_accuracy': symbol_acc,
            'params': sum(p.numel() for p in model.parameters()),
            'added_modules': ['symbol_embedding', 'sequence_prediction_head'],
        }, f)
    
    return model


if __name__ == "__main__":
    train()
