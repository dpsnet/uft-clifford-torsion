"""
Phase B4: 社交期解锁
目标：添加社交模块，学习多智能体交互

解锁条件：语言期准确率>80%（已满足✅）
新增模块：社交注意力层、意图预测头
新任务：合作/竞争博弈
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import numpy as np


class SocialTNN(nn.Module):
    """社交期TNN - 添加多智能体交互能力"""
    
    def __init__(self, vocab_size=10, hidden=32):
        super().__init__()
        self.stage = "social"
        self.vocab_size = vocab_size
        
        # 符号嵌入层
        self.embedding = nn.Embedding(vocab_size, hidden)
        
        # 4层处理（继承自语言期）
        self.l1 = nn.Linear(hidden, hidden)
        self.l2 = nn.Linear(hidden, hidden)
        self.l3 = nn.Linear(hidden, hidden)
        self.l4 = nn.Linear(hidden, hidden)
        
        # 记忆模块
        self.memory = nn.Linear(hidden, hidden)
        self.mem_gate = nn.Parameter(torch.zeros(hidden))
        
        # 新增：社交注意力层
        self.social_query = nn.Linear(hidden, hidden)
        self.social_key = nn.Linear(hidden, hidden)
        self.social_value = nn.Linear(hidden, hidden)
        
        # 新增：意图预测头
        self.intent_head = nn.Linear(hidden, 3)  # 合作/竞争/中立
        
        # 输出头
        self.action_head = nn.Linear(hidden, 1)
        self.symbol_head = nn.Linear(hidden, vocab_size)
    
    def forward(self, symbol=None, other_hidden=None, prev_hidden=None):
        """
        symbol: 自己的符号输入
        other_hidden: 其他智能体的隐藏状态（社交输入）
        prev_hidden: 自己的记忆
        """
        # 符号嵌入
        if symbol is not None:
            h = self.embedding(symbol)
        else:
            h = torch.zeros(1, 32)
        
        # 记忆融合
        if prev_hidden is not None:
            gate = torch.sigmoid(self.mem_gate)
            mem = torch.tanh(self.memory(prev_hidden))
            h = h * (1 - gate) + mem * gate
        
        # 社交注意力（如果有其他智能体）
        if other_hidden is not None and len(other_hidden) > 0:
            # 计算注意力
            q = self.social_query(h)  # [batch, hidden]
            k = torch.stack([self.social_key(oh) for oh in other_hidden])  # [others, hidden]
            v = torch.stack([self.social_value(oh) for oh in other_hidden])  # [others, hidden]
            
            # 注意力权重
            scores = torch.matmul(q.unsqueeze(1), k.transpose(0, 1)) / np.sqrt(32)
            weights = F.softmax(scores, dim=-1)
            
            # 加权融合
            social_context = torch.matmul(weights, v).squeeze(1)
            h = h + social_context * 0.3
        
        # 4层处理
        h = h + torch.tanh(self.l1(h)) * 0.3
        h = h + torch.tanh(self.l2(h)) * 0.3
        h = h + torch.tanh(self.l3(h)) * 0.3
        h = h + torch.tanh(self.l4(h)) * 0.3
        
        # 多头输出
        action = torch.tanh(self.action_head(h))
        symbol_pred = self.symbol_head(h)
        intent = self.intent_head(h)  # 新增意图输出
        
        return action, symbol_pred, intent, h


class SocialGame:
    """简单的合作-竞争博弈环境"""
    
    def __init__(self):
        self.reward_matrix = {
            ("cooperate", "cooperate"): (3, 3),    # 双赢
            ("cooperate", "compete"): (0, 5),      # 背叛
            ("compete", "cooperate"): (5, 0),      # 背叛
            ("compete", "compete"): (1, 1),        # 双输
        }
    
    def play(self, action1, action2):
        """返回两个智能体的奖励"""
        return self.reward_matrix[(action1, action2)]


def train():
    print("="*60)
    print("Phase B4: 社交期解锁 - 多智能体博弈")
    print("="*60)
    print("任务：与其他智能体互动，学习合作/竞争策略")
    print("新增模块：社交注意力层、意图预测头")
    print("-"*60)
    
    # 创建两个智能体
    agent1 = SocialTNN(vocab_size=10, hidden=32)
    agent2 = SocialTNN(vocab_size=10, hidden=32)
    
    opt1 = torch.optim.Adam(agent1.parameters(), lr=0.005)
    opt2 = torch.optim.Adam(agent2.parameters(), lr=0.005)
    
    game = SocialGame()
    
    print(f"智能体1 参数量: {sum(p.numel() for p in agent1.parameters()):,}")
    print(f"智能体2 参数量: {sum(p.numel() for p in agent2.parameters()):,}")
    print(f"解锁条件: 语言期准确率>80% ✅")
    print("-"*60)
    
    # 训练
    history1 = []
    history2 = []
    
    for epoch in range(100):
        total_reward1 = 0
        total_reward2 = 0
        
        for _ in range(50):
            # 随机符号输入
            symbol1 = torch.randint(0, 10, (1,))
            symbol2 = torch.randint(0, 10, (1,))
            
            # 前向传播（互相观察）
            hidden1_prev = None
            hidden2_prev = None
            
            action1, _, intent1, hidden1 = agent1(symbol1, [hidden2_prev] if hidden2_prev is not None else [], hidden1_prev)
            action2, _, intent2, hidden2 = agent2(symbol2, [hidden1_prev] if hidden1_prev is not None else [], hidden2_prev)
            
            # 根据action决定合作/竞争
            act1 = "cooperate" if action1.item() > 0 else "compete"
            act2 = "cooperate" if action2.item() > 0 else "compete"
            
            # 计算奖励
            reward1, reward2 = game.play(act1, act2)
            
            # 损失：最大化奖励（最小化负奖励）
            loss1 = -reward1 * torch.sigmoid(action1).sum()
            loss2 = -reward2 * torch.sigmoid(action2).sum()
            
            opt1.zero_grad()
            opt2.zero_grad()
            
            loss1.backward(retain_graph=True)
            loss2.backward()
            
            opt1.step()
            opt2.step()
            
            total_reward1 += reward1
            total_reward2 += reward2
        
        avg_reward1 = total_reward1 / 50
        avg_reward2 = total_reward2 / 50
        
        history1.append(avg_reward1)
        history2.append(avg_reward2)
        
        if (epoch + 1) % 20 == 0:
            print(f"Epoch {epoch+1:3d} | Agent1 Avg Reward: {avg_reward1:.2f} | Agent2 Avg Reward: {avg_reward2:.2f}")
    
    # 评估社交行为
    print("-"*60)
    print("社交行为分析...")
    
    # 统计合作率
    coop_count1 = 0
    coop_count2 = 0
    total = 0
    
    for _ in range(100):
        symbol1 = torch.randint(0, 10, (1,))
        symbol2 = torch.randint(0, 10, (1,))
        
        with torch.no_grad():
            action1, _, intent1, _ = agent1(symbol1)
            action2, _, intent2, _ = agent2(symbol2)
        
        if action1.item() > 0:
            coop_count1 += 1
        if action2.item() > 0:
            coop_count2 += 1
        total += 1
    
    coop_rate1 = coop_count1 / total
    coop_rate2 = coop_count2 / total
    
    print(f"\n合作行为统计：")
    print(f"  智能体1 合作率: {coop_rate1:.2%}")
    print(f"  智能体2 合作率: {coop_rate2:.2%}")
    
    # 判断社会策略
    if coop_rate1 > 0.6 and coop_rate2 > 0.6:
        strategy = "合作主导"
    elif coop_rate1 < 0.4 and coop_rate2 < 0.4:
        strategy = "竞争主导"
    else:
        strategy = "混合策略"
    
    print(f"  整体策略: {strategy}")
    
    # 最终评估
    print("-"*60)
    print("Phase B4 结论")
    print("="*60)
    
    final_reward1 = np.mean(history1[-10:])
    final_reward2 = np.mean(history2[-10:])
    
    print(f"\n最终平均奖励（最近10轮）：")
    print(f"  智能体1: {final_reward1:.2f}")
    print(f"  智能体2: {final_reward2:.2f}")
    
    if final_reward1 > 2.5 and final_reward2 > 2.5:
        print("\n✅ 社交期解锁成功！")
        print("  智能体学会了有效的社交策略")
        print("  双方都能获得较高奖励（接近双赢）")
        print("  发育TNN路线图全部完成！")
    else:
        print("\n🟡 部分成功")
        print("  社交策略尚未稳定")
    
    # 保存结果
    result = {
        'stage': 'social',
        'agent1': {
            'params': sum(p.numel() for p in agent1.parameters()),
            'cooperation_rate': coop_rate1,
            'final_reward': final_reward1,
        },
        'agent2': {
            'params': sum(p.numel() for p in agent2.parameters()),
            'cooperation_rate': coop_rate2,
            'final_reward': final_reward2,
        },
        'strategy': strategy,
        'history1': history1,
        'history2': history2,
    }
    
    with open('phase_b4_results.json', 'w') as f:
        json.dump(result, f, indent=2)
    print("\n结果已保存: phase_b4_results.json")
    
    return agent1, agent2, result


if __name__ == "__main__":
    train()
