"""
V5.6 - 渐进难度增强版
设计平滑的10阶段课程，逐步增加难度，最终挑战predict任务
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class ProgressiveV56(nn.Module):
    def __init__(self, dim=256):
        super().__init__()
        self.dim = dim
        
        # 具身路径
        self.sensory_enc = nn.Linear(32, dim)
        self.embodied = nn.Sequential(
            nn.LayerNorm(dim), nn.Linear(dim, dim), nn.ReLU(), nn.Linear(dim, dim)
        )
        self.action_head = nn.Linear(dim, 2)
        
        # 离身路径 - 4层GRU
        self.symbol_emb = nn.Embedding(20, dim)
        self.disembodied = nn.GRU(dim, dim, num_layers=4, batch_first=True, dropout=0.1)
        self.symbol_norm = nn.LayerNorm(dim)
        self.symbol_head = nn.Linear(dim, 20)
        
        # 10阶段渐进课程（难度平滑递增）
        self.stages = [
            'copy_1',      # 1. 复制1个token
            'copy_2',      # 2. 复制2个token
            'copy_4',      # 3. 复制4个token
            'pattern_ab',  # 4. ABAB模式
            'pattern_abc', # 5. ABCABC模式
            'classify_2',  # 6. 二分类（全0/全1）
            'classify_4',  # 7. 四分类
            'predict_1',   # 8. 预测1个token
            'predict_2',   # 9. 预测2个token
            'predict_4',   # 10. 预测4个token序列
        ]
        self.stage_idx = 0
        self.history = []
        self.min_acc_threshold = 0.92  # 每阶段最低92%才能晋升
    
    def get_task(self, batch_size=16):
        """根据当前阶段生成任务"""
        stage = self.stages[self.stage_idx]
        
        if stage == 'copy_1':
            x = torch.randint(0, 3, (batch_size, 1))
            y = x.clone()
            
        elif stage == 'copy_2':
            x = torch.randint(0, 4, (batch_size, 2))
            y = x.clone()
            
        elif stage == 'copy_4':
            x = torch.randint(0, 5, (batch_size, 4))
            y = x.clone()
            
        elif stage == 'pattern_ab':
            # ABAB模式
            base = torch.tensor([[0, 1]]).repeat(batch_size, 1)
            x = base.repeat(1, 2)[:, :4]
            y = x.clone()
            
        elif stage == 'pattern_abc':
            # ABCABC模式
            base = torch.tensor([[0, 1, 2]]).repeat(batch_size, 1)
            x = base.repeat(1, 2)[:, :6]
            y = x.clone()
            
        elif stage == 'classify_2':
            # 二分类：前一半是0类，后一半是1类
            half = batch_size // 2
            x = torch.cat([
                torch.zeros(half, 4, dtype=torch.long),
                torch.ones(batch_size - half, 4, dtype=torch.long)
            ], dim=0)
            y = x.clone()
            
        elif stage == 'classify_4':
            # 四分类：根据第一个token分类
            x = torch.randint(0, 4, (batch_size, 4))
            y = x[:, 0:1].expand(-1, 4)  # 目标是类别标签
            
        elif stage == 'predict_1':
            # 预测最后一个token（二分类：是否为0）
            x = torch.randint(0, 4, (batch_size, 4))
            y = (x[:, -1:] < 2).long().expand(-1, 4)  # 0或1为类0，否则类1
            
        elif stage == 'predict_2':
            # 预测最后2个token的和的奇偶
            x = torch.randint(0, 5, (batch_size, 6))
            parity = (x[:, -2:].sum(dim=1) % 2).long()
            y = parity.unsqueeze(1).expand(-1, 6)
            
        else:  # predict_4
            # 预测下一个4-token序列
            x = torch.randint(0, 6, (batch_size, 8))
            y = torch.cat([x[:, 4:], torch.randint(0, 6, (batch_size, 4))], dim=1)
        
        return x, y, stage
    
    def forward(self, sensory, symbol):
        # 具身
        emb = self.embodied(self.sensory_enc(sensory))
        action = self.action_head(emb)
        
        # 离身
        dis = self.symbol_emb(symbol)
        dis, _ = self.disembodied(dis)
        dis = self.symbol_norm(dis)
        symbol_out = self.symbol_head(dis)
        
        return action, symbol_out
    
    def compute_loss_and_acc(self, symbol_out, symbol_target, stage):
        """根据阶段类型计算损失和准确率"""
        if 'predict' in stage:
            # 预测任务：只看最后一个位置
            pred = symbol_out[:, -1, :]
            target = symbol_target[:, -1]
            loss = F.cross_entropy(pred, target)
            acc = (pred.argmax(-1) == target).float().mean().item()
        else:
            # 其他任务：全序列
            loss = F.cross_entropy(symbol_out.reshape(-1, 20), symbol_target.reshape(-1))
            acc = (symbol_out.argmax(-1) == symbol_target).float().mean().item()
        
        return loss, acc
    
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
        
        loss_symbol, acc_symbol = self.compute_loss_and_acc(symbol_out, symbol_target, stage)
        
        # 动态权重：早期重具身，后期平衡
        dis_weight = 0.4 + (self.stage_idx / len(self.stages)) * 0.4  # 0.4 -> 0.8
        
        total = loss_action * (1 - dis_weight) + loss_symbol * dis_weight
        
        optimizer.zero_grad()
        total.backward()
        torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
        optimizer.step()
        
        self.history.append(acc_symbol)
        return acc_action, acc_symbol, stage
    
    def check_promotion(self, epoch_in_stage):
        """检查是否晋升 - 需要稳定达到阈值"""
        if len(self.history) < 50:
            return False
        
        recent_acc = sum(self.history[-50:]) / 50
        
        # 条件1: 达到目标准确率
        # 条件2: 至少训练了一定轮数
        # 条件3: 不是最后一个阶段
        min_epochs = 50 + self.stage_idx * 20  # 越往后需要越多轮数
        
        if (recent_acc >= self.min_acc_threshold and 
            epoch_in_stage >= min_epochs and
            self.stage_idx < len(self.stages) - 1):
            
            self.stage_idx += 1
            self.history.clear()
            return True, self.stages[self.stage_idx]
        
        return False, self.stages[self.stage_idx]


def run_v56():
    print("="*65)
    print("🎯 V5.6 - 渐进难度增强版")
    print("="*65)
    print("目标: 通过10阶段平滑课程，最终挑战predict任务")
    print("策略:")
    print("  • 10阶段渐进课程（难度平滑递增）")
    print("  • 每阶段92%准确率才能晋升")
    print("  • 越往后训练轮数要求越多")
    print("="*65 + "\n")
    
    model = ProgressiveV56(dim=256)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    
    # 统计
    stage_accs = {s: [] for s in model.stages}
    promotions = []
    epoch_in_stage = 0
    
    for epoch in range(2000):
        acc_a, acc_s, stage = model.train_step(optimizer)
        stage_accs[stage].append(acc_s)
        epoch_in_stage += 1
        
        # 检查晋升
        if epoch % 50 == 49:
            promoted, new_stage = model.check_promotion(epoch_in_stage)
            if promoted:
                promotions.append((epoch, new_stage))
                print(f"\n🎓 晋升! Epoch {epoch:4d} -> {new_stage}")
                print(f"   上一阶段训练轮数: {epoch_in_stage}")
                epoch_in_stage = 0
        
        # 报告
        if (epoch + 1) % 200 == 0:
            recent = sum(stage_accs[stage][-100:]) / min(100, len(stage_accs[stage]))
            print(f"Epoch {epoch+1:4d}: 具身={acc_a:.1%}, 离身={recent:.1%}, 阶段={stage}")
    
    # 最终统计
    print(f"\n{'='*65}")
    print("📊 完整课程统计")
    print(f"{'='*65}")
    
    reached_stage = model.stages[model.stage_idx]
    print(f"最终到达阶段: {reached_stage} (共{len(model.stages)}阶段)\n")
    
    for i, (s, accs) in enumerate(stage_accs.items()):
        if accs:
            final = sum(accs[-50:]) / min(50, len(accs))
            best = max(accs)
            count = len(accs)
            status = "✅" if final >= 0.92 else "⚠️"
            print(f"{status} Stage {i+1:2d} {s:12s}: 最终={final:.1%}, 最佳={best:.1%}, 轮数={count:4d}")
    
    # 总体
    all_acc = [a for accs in stage_accs.values() for a in accs]
    if all_acc:
        overall = sum(all_acc[-100:]) / min(100, len(all_acc))
        print(f"\n总体离身准确率: {overall:.1%}")
        
        if reached_stage == model.stages[-1] and overall >= 0.90:
            print("🎉 完成全部10阶段课程！")
        elif reached_stage in ['predict_1', 'predict_2', 'predict_4']:
            print(f"✅ 成功挑战predict任务（到达{reached_stage}）")
        else:
            print(f"⚠️  未完成全部课程（卡在{reached_stage}）")
    
    print(f"{'='*65}\n")


if __name__ == "__main__":
    run_v56()
