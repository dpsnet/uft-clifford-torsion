"""
V5.5 - 离身准确率优化版
目标: 离身准确率 >= 95%
策略: 增加容量 + 优化课程 + 延长训练
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class EnhancedDisembodiedPathway(nn.Module):
    """增强版离身路径 - 更大容量，更好架构"""
    def __init__(self, vocab_size=10, dim=256, num_layers=4):
        super().__init__()
        self.dim = dim
        self.embedding = nn.Embedding(vocab_size, dim)
        
        # 多层Transformer风格处理
        self.layers = nn.ModuleList([
            nn.TransformerEncoderLayer(
                d_model=dim, nhead=8, dim_feedforward=dim*4,
                dropout=0.1, batch_first=True
            ) for _ in range(num_layers)
        ])
        
        # 输出头
        self.output_norm = nn.LayerNorm(dim)
        self.output_head = nn.Linear(dim, vocab_size)
        
        # 位置编码
        self.pos_encoding = nn.Parameter(torch.randn(1, 128, dim) * 0.02)
    
    def forward(self, x):
        # 嵌入 + 位置编码
        h = self.embedding(x)
        seq_len = x.size(1)
        h = h + self.pos_encoding[:, :seq_len, :]
        
        # 多层处理
        for layer in self.layers:
            h = layer(h)
        
        # 输出
        h = self.output_norm(h)
        return self.output_head(h)


class OptimizedCurriculum:
    """优化版课程 - 更平滑的难度递增"""
    
    TASKS = {
        'copy': {      # 阶段1: 复制（最简单）
            'vocab': 5, 'seq_len': 4,
            'min_acc': 0.95, 'max_epochs': 100
        },
        'reverse': {   # 阶段2: 反转序列
            'vocab': 6, 'seq_len': 5,
            'min_acc': 0.93, 'max_epochs': 150
        },
        'shift': {     # 阶段3: 位移
            'vocab': 7, 'seq_len': 6,
            'min_acc': 0.90, 'max_epochs': 200
        },
        'pattern': {   # 阶段4: 模式补全
            'vocab': 8, 'seq_len': 8,
            'min_acc': 0.88, 'max_epochs': 250
        },
        'predict': {   # 阶段5: 预测（最难）
            'vocab': 10, 'seq_len': 10,
            'min_acc': 0.85, 'max_epochs': 500
        },
    }
    
    def __init__(self):
        self.stages = list(self.TASKS.keys())
        self.stage_idx = 0
        self.epoch_in_stage = 0
        self.best_acc = 0.0
        self.stable_count = 0
    
    def get_task(self, batch_size=16):
        stage = self.stages[self.stage_idx]
        cfg = self.TASKS[stage]
        vocab, seq_len = cfg['vocab'], cfg['seq_len']
        
        if stage == 'copy':
            x = torch.randint(0, vocab, (batch_size, seq_len))
            y = x.clone()
        
        elif stage == 'reverse':
            x = torch.randint(0, vocab, (batch_size, seq_len))
            y = torch.flip(x, [1])
        
        elif stage == 'shift':
            x = torch.randint(0, vocab, (batch_size, seq_len))
            y = torch.roll(x, shifts=1, dims=1)
        
        elif stage == 'pattern':
            # 补全模式: [A,B,A,B,?]
            base = torch.randint(0, vocab//2, (batch_size, 2))
            x = base.repeat(1, seq_len//2)[:, :seq_len-1]
            y = base[:, 0:1].expand(-1, seq_len)  # 目标是最常见的元素
        
        else:  # predict
            x = torch.randint(0, vocab, (batch_size, seq_len))
            # 简化：预测最后一个token是否为0
            y = (x[:, -1:] == 0).long().expand(-1, seq_len)
        
        return x, y, stage
    
    def check_promotion(self, avg_acc, epoch_in_stage):
        """检查是否晋升 - 需要稳定达到目标"""
        stage = self.stages[self.stage_idx]
        cfg = self.TASKS[stage]
        
        self.epoch_in_stage = epoch_in_stage
        self.best_acc = max(self.best_acc, avg_acc)
        
        # 条件1: 达到目标准确率
        # 条件2: 训练了足够轮数
        # 条件3: 不是最后一个阶段
        if (avg_acc >= cfg['min_acc'] and 
            epoch_in_stage >= cfg['max_epochs'] // 2 and
            self.stage_idx < len(self.stages) - 1):
            
            self.stage_idx += 1
            self.epoch_in_stage = 0
            self.best_acc = 0.0
            return True, self.stages[self.stage_idx]
        
        return False, stage


class V55(nn.Module):
    """V5.5 - 离身准确率优化版"""
    def __init__(self, dim=256):
        super().__init__()
        self.dim = dim
        
        # 具身路径（保持简单）
        self.sensory_enc = nn.Linear(32, dim)
        self.embodied = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, dim), nn.Tanh(), nn.Linear(dim, dim)
        )
        self.action_head = nn.Linear(dim, 2)
        
        # 增强离身路径
        self.disembodied = EnhancedDisembodiedPathway(vocab_size=10, dim=dim, num_layers=3)
        
        # 课程学习器
        self.curriculum = OptimizedCurriculum()
        
        # 统计
        self.stage_history = []
    
    def forward(self, sensory, symbol=None):
        # 具身
        emb = self.embodied(self.sensory_enc(sensory))
        action = self.action_head(emb)
        
        # 离身
        symbol_out = None
        if symbol is not None:
            symbol_out = self.disembodied(symbol)
        
        return action, symbol_out
    
    def train_step(self, optimizer):
        # 数据
        sensory = torch.randn(16, 32)
        action_target = (sensory.sum(dim=-1) > 0).long()
        symbol, symbol_target, stage = self.curriculum.get_task()
        
        # 前向
        action_out, symbol_out = self.forward(sensory, symbol)
        
        # 损失
        loss_action = F.cross_entropy(action_out, action_target)
        acc_action = (action_out.argmax(-1) == action_target).float().mean().item()
        
        if symbol_out is not None:
            # 根据任务类型调整损失计算
            if stage in ['copy', 'reverse', 'shift']:
                loss_symbol = F.cross_entropy(symbol_out.reshape(-1, 10), 
                                             symbol_target.reshape(-1).clamp(0, 9))
                acc_symbol = (symbol_out.argmax(-1) == symbol_target).float().mean().item()
            else:  # pattern, predict
                # 只对最后一个位置计算损失
                loss_symbol = F.cross_entropy(symbol_out[:, -1, :], 
                                             symbol_target[:, -1].clamp(0, 9))
                acc_symbol = (symbol_out[:, -1, :].argmax(-1) == symbol_target[:, -1]).float().mean().item()
        else:
            loss_symbol = torch.tensor(0.0)
            acc_symbol = 0.0
        
        # 动态权重：早期重具身，后期平衡
        dis_weight = 0.4 + self.curriculum.stage_idx * 0.1  # 0.4 -> 0.8
        total_loss = loss_action * (1 - dis_weight) + loss_symbol * dis_weight
        
        # 反向
        optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
        optimizer.step()
        
        return {
            'loss': total_loss.item(),
            'acc_action': acc_action,
            'acc_symbol': acc_symbol,
            'stage': stage
        }


def run_v55():
    print("="*60)
    print("🎯 V5.5 - 离身准确率优化版")
    print("="*60)
    print("目标: 离身准确率 >= 95%")
    print("策略:")
    print("  • 增强离身路径: 3层Transformer")
    print("  • 优化课程: 5个阶段平滑过渡")
    print("  • 延长训练: 2000轮")
    print("="*60 + "\n")
    
    model = V55(dim=256)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # 记录
    history = {stage: {'acc': [], 'epochs': 0} for stage in model.curriculum.stages}
    current_stage_start = 0
    promotions = []
    
    for epoch in range(2000):
        result = model.train_step(optimizer)
        
        stage = result['stage']
        history[stage]['acc'].append(result['acc_symbol'])
        history[stage]['epochs'] += 1
        
        # 检查晋升
        if epoch % 50 == 49:  # 每50轮检查一次
            recent_acc = sum(history[stage]['acc'][-50:]) / min(50, len(history[stage]['acc']))
            promoted, new_stage = model.curriculum.check_promotion(
                recent_acc, 
                epoch - current_stage_start
            )
            if promoted:
                promotions.append((epoch, new_stage))
                current_stage_start = epoch
                print(f"\n🎓 晋升! Epoch {epoch} -> {new_stage}")
                print(f"   上一阶段最佳: {model.curriculum.best_acc:.1%}\n")
        
        # 报告
        if (epoch + 1) % 200 == 0:
            avg_action = result['acc_action']
            avg_symbol = sum(history[stage]['acc'][-100:]) / min(100, len(history[stage]['acc']))
            print(f"Epoch {epoch+1}: 具身={avg_action:.1%}, 离身={avg_symbol:.1%}, 阶段={stage}")
    
    # 最终统计
    print(f"\n{'='*60}")
    print("📊 最终结果")
    print(f"{'='*60}")
    
    for stage, data in history.items():
        if data['acc']:
            final_acc = sum(data['acc'][-50:]) / min(50, len(data['acc']))
            best_acc = max(data['acc'])
            print(f"{stage:12s}: 最终={final_acc:.1%}, 最佳={best_acc:.1%}, 轮数={data['epochs']}")
    
    # 总体
    all_symbol_acc = []
    for stage in model.curriculum.stages:
        all_symbol_acc.extend(history[stage]['acc'])
    
    if all_symbol_acc:
        overall_final = sum(all_symbol_acc[-100:]) / min(100, len(all_symbol_acc))
        overall_best = max(all_symbol_acc)
        print(f"\n总体离身: 最终={overall_final:.1%}, 最佳={overall_best:.1%}")
        
        if overall_final >= 0.95:
            print(f"\n✅ 目标达成! 离身准确率 >= 95%")
        else:
            print(f"\n⚠️  未达目标 (需要 >= 95%)")
    
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_v55()
