"""
V5.3 - 极简有效的双路径渐进学习
离身从最简单的任务开始，逐步增加难度
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class V53(nn.Module):
    def __init__(self, dim=128):
        super().__init__()
        self.dim = dim
        
        # 具身路径
        self.sensory_enc = nn.Linear(32, dim)
        self.embodied = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, dim), nn.Tanh(), nn.Linear(dim, dim)
        )
        self.action_head = nn.Linear(dim, 2)
        
        # 离身路径 - 更简单的结构
        self.symbol_emb = nn.Embedding(10, dim)
        self.disembodied = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, dim), nn.ReLU(), nn.Linear(dim, dim)
        )
        self.symbol_head = nn.Linear(dim, 10)
        
        # 离身课程阶段
        self.disembodied_stage = 0  # 0=copy, 1=pattern, 2=classify
        self.stage_names = ['copy', 'pattern', 'classify']
        self.stage_threshold = 0.85  # 85%准确率晋升
        
    def forward(self, sensory, symbol=None):
        # 具身
        emb = self.sensory_enc(sensory)
        emb = self.embodied(emb)
        action = self.action_head(emb)
        
        # 离身
        symbol_out = None
        if symbol is not None:
            dis = self.symbol_emb(symbol)
            dis = self.disembodied(dis)
            symbol_out = self.symbol_head(dis)
        
        return action, symbol_out
    
    def get_disembodied_task(self):
        """获取当前阶段的离身任务"""
        batch_size = 8
        
        if self.disembodied_stage == 0:  # copy
            # 复制：输入什么输出什么
            x = torch.randint(0, 5, (batch_size, 4))
            y = x.clone()
            
        elif self.disembodied_stage == 1:  # pattern
            # 模式识别：识别ABAB模式
            x = torch.tensor([[0,1,0,1], [1,0,1,0], [0,1,0,1], [1,0,1,0]] * 2)
            y = x.clone()
            
        else:  # classify
            # 分类：更简单——识别固定类别模式
            # 类别0: 全0序列, 类别1: 全1序列
            if torch.rand(1) > 0.5:
                x = torch.zeros(batch_size, 4, dtype=torch.long)
                y = torch.zeros(batch_size, 4, dtype=torch.long)
            else:
                x = torch.ones(batch_size, 4, dtype=torch.long)
                y = torch.ones(batch_size, 4, dtype=torch.long)
        
        return x, y
    
    def train_step(self, optimizer):
        # 具身数据
        sensory = torch.randn(16, 32)
        action_target = (sensory.sum(dim=-1) > 0).long()
        
        # 离身数据
        symbol, symbol_target = self.get_disembodied_task()
        
        # 前向
        action_out, symbol_out = self.forward(sensory, symbol)
        
        # 损失
        loss_action = F.cross_entropy(action_out, action_target)
        acc_action = (action_out.argmax(-1) == action_target).float().mean().item()
        
        loss_symbol = F.cross_entropy(symbol_out.reshape(-1, 10), symbol_target.reshape(-1))
        acc_symbol = (symbol_out.argmax(-1) == symbol_target).float().mean().item()
        
        # 动态权重
        dis_weight = 0.3 + self.disembodied_stage * 0.15  # 0.3 -> 0.6
        total_loss = loss_action * (1 - dis_weight) + loss_symbol * dis_weight
        
        # 反向
        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()
        
        return {
            'loss': total_loss.item(),
            'action_acc': acc_action,
            'symbol_acc': acc_symbol,
            'stage': self.stage_names[self.disembodied_stage]
        }
    
    def check_promotion(self):
        """检查离身晋升"""
        if self.disembodied_stage < len(self.stage_names) - 1:
            self.disembodied_stage += 1
            print(f"\n🎓 离身晋升! {self.stage_names[self.disembodied_stage-1]} -> {self.stage_names[self.disembodied_stage]}\n")
            return True
        return False


def main():
    print("🚀 V5.3 - 极简双路径渐进学习\n")
    
    model = V53(dim=128)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    # 记录最近准确率用于晋升判断
    recent_symbol_accs = []
    
    for epoch in range(500):
        result = model.train_step(optimizer)
        recent_symbol_accs.append(result['symbol_acc'])
        
        if len(recent_symbol_accs) > 20:
            recent_symbol_accs.pop(0)
        
        # 每50轮检查
        if (epoch + 1) % 50 == 0:
            avg_action = result['action_acc']
            avg_symbol = sum(recent_symbol_accs) / len(recent_symbol_accs)
            
            print(f"Epoch {epoch+1}: 具身={avg_action:.1%}, 离身={avg_symbol:.1%}, 阶段={result['stage']}")
            
            # 晋升判断
            if len(recent_symbol_accs) >= 10 and avg_symbol >= model.stage_threshold:
                model.check_promotion()
                recent_symbol_accs.clear()
    
    print(f"\n✅ 完成!")
    print(f"   离身最终阶段: {model.stage_names[model.disembodied_stage]}")


if __name__ == "__main__":
    main()
