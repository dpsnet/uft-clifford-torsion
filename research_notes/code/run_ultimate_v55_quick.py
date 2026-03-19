"""
V5.5-Quick - 离身准确率快速验证
目标: 验证优化策略能否达到95%
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class QuickV55(nn.Module):
    def __init__(self, dim=128):
        super().__init__()
        self.dim = dim
        
        # 具身路径
        self.sensory_enc = nn.Linear(32, dim)
        self.embodied = nn.Sequential(
            nn.LayerNorm(dim), nn.Linear(dim, dim), nn.Tanh(), nn.Linear(dim, dim)
        )
        self.action_head = nn.Linear(dim, 2)
        
        # 增强离身路径（2层LSTM风格）
        self.symbol_emb = nn.Embedding(10, dim)
        self.disembodied = nn.LSTM(dim, dim, num_layers=2, batch_first=True)
        self.symbol_head = nn.Linear(dim, 10)
        
        # 当前阶段
        self.stage_idx = 0
        self.stages = ['copy', 'reverse', 'predict']
        self.history = []
    
    def get_task(self):
        stage = self.stages[self.stage_idx]
        batch = 16
        
        if stage == 'copy':
            x = torch.randint(0, 5, (batch, 4))
            y = x.clone()
        elif stage == 'reverse':
            x = torch.randint(0, 6, (batch, 5))
            y = torch.flip(x, [1])
        else:  # predict - 简化为二分类
            x = torch.randint(0, 8, (batch, 6))
            y = (x[:, -1] == 0).long().unsqueeze(1).expand(-1, 6)
        
        return x, y, stage
    
    def forward(self, sensory, symbol):
        # 具身
        emb = self.embodied(self.sensory_enc(sensory))
        action = self.action_head(emb)
        
        # 离身
        dis = self.symbol_emb(symbol)
        dis, _ = self.disembodied(dis)
        symbol_out = self.symbol_head(dis)
        
        return action, symbol_out
    
    def train_step(self, optimizer):
        sensory = torch.randn(16, 32)
        action_target = (sensory.sum(dim=-1) > 0).long()
        symbol, symbol_target, stage = self.get_task()
        
        action_out, symbol_out = self.forward(sensory, symbol)
        
        loss_action = F.cross_entropy(action_out, action_target)
        acc_action = (action_out.argmax(-1) == action_target).float().mean().item()
        
        if stage == 'predict':
            loss_symbol = F.cross_entropy(symbol_out[:, -1, :], symbol_target[:, -1])
            acc_symbol = (symbol_out[:, -1, :].argmax(-1) == symbol_target[:, -1]).float().mean().item()
        else:
            loss_symbol = F.cross_entropy(symbol_out.reshape(-1, 10), symbol_target.reshape(-1))
            acc_symbol = (symbol_out.argmax(-1) == symbol_target).float().mean().item()
        
        dis_weight = 0.5 + self.stage_idx * 0.15
        total = loss_action * (1 - dis_weight) + loss_symbol * dis_weight
        
        optimizer.zero_grad()
        total.backward()
        optimizer.step()
        
        self.history.append(acc_symbol)
        return acc_action, acc_symbol, stage
    
    def check_promotion(self):
        if len(self.history) >= 30 and self.stage_idx < 2:
            recent = sum(self.history[-30:]) / 30
            if recent >= 0.90:
                self.stage_idx += 1
                self.history.clear()
                return True
        return False


def main():
    print("🎯 V5.5-Quick: 离身准确率目标95%\n")
    
    model = QuickV55(dim=128)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
    
    stage_accs = {s: [] for s in model.stages}
    promotions = []
    
    for epoch in range(1000):
        acc_a, acc_s, stage = model.train_step(optimizer)
        stage_accs[stage].append(acc_s)
        
        if model.check_promotion():
            promotions.append((epoch, model.stages[model.stage_idx]))
            print(f"\n🎓 晋升! Epoch {epoch} -> {model.stages[model.stage_idx]}\n")
        
        if (epoch + 1) % 100 == 0:
            recent = sum(stage_accs[stage][-50:]) / min(50, len(stage_accs[stage]))
            print(f"Epoch {epoch+1}: 具身={acc_a:.1%}, 离身={recent:.1%}, 阶段={stage}")
    
    # 统计
    print(f"\n{'='*50}")
    for s, accs in stage_accs.items():
        if accs:
            final = sum(accs[-50:]) / min(50, len(accs))
            best = max(accs)
            print(f"{s:10s}: 最终={final:.1%}, 最佳={best:.1%}")
    
    all_acc = [a for accs in stage_accs.values() for a in accs]
    if all_acc:
        overall = sum(all_acc[-100:]) / min(100, len(all_acc))
        print(f"\n总体离身: {overall:.1%}")
        if overall >= 0.95:
            print("✅ 目标达成!")
        else:
            print(f"⚠️  未达95%目标")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
