"""
V5.4B-Quick - 延长训练快速验证版
减小模型尺寸，专注验证延长训练对离身准确率的影响
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class QuickV54B(nn.Module):
    def __init__(self, dim=128):
        super().__init__()
        self.dim = dim
        
        # 简化编码器
        self.sensory_enc = nn.Linear(32, dim)
        self.symbol_emb = nn.Embedding(10, dim)
        
        # 具身路径
        self.embodied = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, dim), nn.Tanh(), nn.Linear(dim, dim)
        )
        self.action_head = nn.Linear(dim, 2)
        
        # 离身路径（增加容量）
        self.disembodied = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, dim), nn.ReLU(),
            nn.Linear(dim, dim), nn.ReLU(),  # 加一层
            nn.Linear(dim, dim)
        )
        self.symbol_head = nn.Linear(dim, 10)
        
        # 课程学习状态
        self.stage_idx = 0
        self.stages = ['copy', 'pattern', 'classify', 'predict']
        self.history = []
    
    def get_task(self):
        stage = self.stages[self.stage_idx]
        batch = 16
        
        if stage == 'copy':
            x = torch.randint(0, 5, (batch, 4))
            y = x.clone()
        elif stage == 'pattern':
            x = torch.tensor([[0,1,0,1], [1,0,1,0]] * 8)
            y = x.clone()
        elif stage == 'classify':
            if torch.rand(1) > 0.5:
                x, y = torch.zeros(batch, 4, dtype=torch.long), torch.zeros(batch, 4, dtype=torch.long)
            else:
                x, y = torch.ones(batch, 4, dtype=torch.long), torch.ones(batch, 4, dtype=torch.long)
        else:  # predict
            x = torch.randint(0, 4, (batch, 6))
            y = (x[:, -1] == 0).long().unsqueeze(1).expand(-1, 6)
        
        return x, y, stage
    
    def forward(self, sensory, symbol):
        # 具身
        emb = self.embodied(self.sensory_enc(sensory))
        action = self.action_head(emb)
        
        # 离身
        dis = self.disembodied(self.symbol_emb(symbol))
        symbol_out = self.symbol_head(dis)
        
        return action, symbol_out
    
    def train_step(self, optimizer):
        # 数据
        sensory = torch.randn(16, 32)
        action_target = (sensory.sum(dim=-1) > 0).long()
        symbol, symbol_target, stage = self.get_task()
        
        # 前向
        action_out, symbol_out = self.forward(sensory, symbol)
        
        # 损失
        loss_action = F.cross_entropy(action_out, action_target)
        acc_action = (action_out.argmax(-1) == action_target).float().mean().item()
        
        loss_symbol = F.cross_entropy(symbol_out.reshape(-1, 10), symbol_target.reshape(-1))
        acc_symbol = (symbol_out.argmax(-1) == symbol_target).float().mean().item()
        
        # 动态权重
        dis_weight = 0.3 + self.stage_idx * 0.15
        total = loss_action * (1 - dis_weight) + loss_symbol * dis_weight
        
        optimizer.zero_grad()
        total.backward()
        optimizer.step()
        
        self.history.append(acc_symbol)
        if len(self.history) > 50:
            self.history.pop(0)
        
        return acc_action, acc_symbol, stage
    
    def check_promotion(self):
        if len(self.history) < 30:
            return False
        if sum(self.history) / len(self.history) >= 0.85 and self.stage_idx < 3:
            self.stage_idx += 1
            self.history.clear()
            return True
        return False


def main():
    print("🚀 V5.4B-Quick - 延长训练验证 (1500轮)\n")
    
    model = QuickV54B(dim=128)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    results = []
    promotions = []
    
    for epoch in range(1500):
        acc_a, acc_s, stage = model.train_step(optimizer)
        
        if model.check_promotion():
            new_stage = model.stages[model.stage_idx]
            promotions.append((epoch, new_stage))
            print(f"\n🎓 晋升! Epoch {epoch} -> {new_stage}\n")
        
        if (epoch + 1) % 150 == 0:  # 每150轮报告
            avg_a = sum([r[0] for r in results[-150:]]) / 150 if results else acc_a
            avg_s = sum([r[1] for r in results[-150:]]) / 150 if results else acc_s
            print(f"Epoch {epoch+1}: 具身={avg_a:.1%}, 离身={avg_s:.1%}, 阶段={stage}")
        
        results.append((acc_a, acc_s))
    
    # 最终统计
    final_a = sum([r[0] for r in results[-100:]]) / 100
    final_s = sum([r[1] for r in results[-100:]]) / 100
    
    print(f"\n{'='*50}")
    print(f"✅ 完成! 最终150轮平均:")
    print(f"   具身: {final_a:.1%}")
    print(f"   离身: {final_s:.1%}")
    print(f"   离身阶段: {model.stages[model.stage_idx]}")
    print(f"   晋升: {len(promotions)}次")
    for ep, st in promotions:
        print(f"      Epoch {ep}: {st}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
