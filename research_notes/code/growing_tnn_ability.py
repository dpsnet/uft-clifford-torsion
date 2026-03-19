"""
发育式TNN - 能力驱动生长版
生长由学习进度触发，而非固定时间
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import sys
from collections import deque

# 强制立即输出
class FlushPrint:
    def __init__(self):
        self.stdout = sys.stdout
    def write(self, s):
        self.stdout.write(s)
        self.stdout.flush()
    def flush(self):
        self.stdout.flush()

sys.stdout = FlushPrint()


class GrowingTNN(nn.Module):
    """能力驱动的可生长TNN"""
    
    def __init__(self, vocab_size=50, max_seq_len=32):
        super().__init__()
        self.vocab_size = vocab_size
        self.max_seq_len = max_seq_len
        
        # 嵌入
        self.embedding = nn.Embedding(vocab_size, 64)
        self.pos_embed = nn.Embedding(max_seq_len, 64)
        
        # 初始为embryo（胚胎）- 最简单结构
        self.stage = "embryo"
        self.age = 0
        
        # 起始：2层，最小谱维
        self.layers = nn.ModuleList([self._make_layer() for _ in range(2)])
        self.spectral_dim = 2.5
        self.spectral_max = 2.5
        
        self.output = nn.Linear(64, vocab_size)
        
        # 生长历史
        self.growth_log = []
        
        # 性能滑动窗口（检测稳定性）
        self.acc_window = deque(maxlen=100)  # 最近100步准确率
        self.loss_window = deque(maxlen=100)  # 最近100步损失
        
        # 生长条件配置
        self.growth_conditions = {
            'embryo_to_infant': {
                'min_steps': 200,  # 至少训练200步
                'target_acc': 0.95,  # 准确率>95%
                'stable_steps': 50,  # 连续50步达标
                'max_loss': 0.5,  # 损失<0.5
            },
            'infant_to_child': {
                'min_steps': 500,
                'target_acc': 0.98,
                'stable_steps': 100,
                'max_loss': 0.1,
            },
            'child_to_adolescent': {
                'min_steps': 1000,
                'target_acc': 0.99,
                'stable_steps': 200,
                'max_loss': 0.05,
            }
        }
        
        # 当前阶段的达标计数
        self.stable_count = 0
        self.stage_start_step = 0
    
    def _make_layer(self):
        return nn.ModuleDict({
            'attn': nn.Linear(64, 64),
            'torsion_a': nn.Linear(64, 16, bias=False),
            'torsion_b': nn.Linear(16, 64, bias=False),
            'norm': nn.LayerNorm(64),
        })
    
    def check_growth(self, step, loss, acc):
        """基于能力达标检查生长"""
        self.age = step
        self.acc_window.append(acc)
        self.loss_window.append(loss)
        
        # 计算当前性能统计
        if len(self.acc_window) < 50:
            return None  # 数据不足
        
        avg_acc = sum(self.acc_window) / len(self.acc_window)
        avg_loss = sum(self.loss_window) / len(self.loss_window)
        recent_acc = sum(list(self.acc_window)[-20:]) / 20  # 最近20步
        recent_loss = sum(list(self.loss_window)[-20:]) / 20
        
        # 检查是否满足当前阶段的生长条件
        stage_age = step - self.stage_start_step
        
        if self.stage == "embryo":
            cond = self.growth_conditions['embryo_to_infant']
            if self._check_conditions(stage_age, recent_acc, recent_loss, cond):
                self._grow_to_infant(step, avg_acc, avg_loss)
                return f"🌱 embryo→infant (acc={recent_acc:.3f}, loss={recent_loss:.4f})"
        
        elif self.stage == "infant":
            cond = self.growth_conditions['infant_to_child']
            if self._check_conditions(stage_age, recent_acc, recent_loss, cond):
                self._grow_to_child(step, avg_acc, avg_loss)
                return f"🌿 infant→child (acc={recent_acc:.3f}, loss={recent_loss:.4f})"
        
        elif self.stage == "child":
            cond = self.growth_conditions['child_to_adolescent']
            if self._check_conditions(stage_age, recent_acc, recent_loss, cond):
                self._grow_to_adolescent(step, avg_acc, avg_loss)
                return f"🌳 child→adolescent (acc={recent_acc:.3f}, loss={recent_loss:.4f})"
        
        # 谱维解锁（平滑）
        self._unlock_spectral(avg_acc)
        
        return None
    
    def _check_conditions(self, stage_age, acc, loss, cond):
        """检查是否满足生长条件"""
        if stage_age < cond['min_steps']:
            return False
        if acc < cond['target_acc']:
            self.stable_count = 0
            return False
        if loss > cond['max_loss']:
            self.stable_count = 0
            return False
        
        self.stable_count += 1
        return self.stable_count >= cond['stable_steps']
    
    def _unlock_spectral(self, avg_acc):
        """基于准确率解锁谱维"""
        # 准确率越高，解锁的谱维越高
        if avg_acc > 0.99:
            target = 5.5
        elif avg_acc > 0.95:
            target = 4.5
        elif avg_acc > 0.90:
            target = 3.5
        else:
            target = 2.5
        
        # 平滑过渡
        self.spectral_max += 0.01 * (target - self.spectral_max)
    
    def _grow_to_infant(self, step, acc, loss):
        """生长到infant阶段"""
        self.stage = "infant"
        self.layers.append(self._make_layer())  # 添加第3层
        self.stage_start_step = step
        self.stable_count = 0
        
        msg = f"Step {step}: embryo→infant | 当前能力 acc={acc:.3f}, loss={loss:.4f}"
        self.growth_log.append(msg)
        print(f"  🌱 {msg}")
    
    def _grow_to_child(self, step, acc, loss):
        """生长到child阶段"""
        self.stage = "child"
        self.layers.append(self._make_layer())  # 添加第4层
        self.stage_start_step = step
        self.stable_count = 0
        
        msg = f"Step {step}: infant→child | 当前能力 acc={acc:.3f}, loss={loss:.4f}"
        self.growth_log.append(msg)
        print(f"  🌿 {msg}")
    
    def _grow_to_adolescent(self, step, acc, loss):
        """生长到adolescent阶段"""
        self.stage = "adolescent"
        self.layers.append(self._make_layer())  # 添加第5层
        self.layers.append(self._make_layer())  # 添加第6层
        self.stage_start_step = step
        self.stable_count = 0
        
        msg = f"Step {step}: child→adolescent | 当前能力 acc={acc:.3f}, loss={loss:.4f}"
        self.growth_log.append(msg)
        print(f"  🌳 {msg}")
    
    def forward(self, x, labels=None):
        batch, seq = x.shape
        device = x.device
        
        pos = torch.arange(seq, device=device).unsqueeze(0)
        h = self.embedding(x) + self.pos_embed(pos)
        
        for layer in self.layers:
            residual = h
            h = layer['norm'](h)
            attn = layer['attn'](h)
            
            low = layer['torsion_a'](h)
            twist = layer['torsion_b'](low)
            twist = torch.sin(twist) * 0.1
            
            h = residual + attn + twist
        
        logits = self.output(h)
        
        loss = None
        if labels is not None:
            loss = F.cross_entropy(logits.view(-1, self.vocab_size), labels.view(-1))
        
        return {
            'loss': loss,
            'logits': logits,
            'stage': self.stage,
            'spectral': self.spectral_max,
        }
    
    def get_info(self):
        return {
            'stage': self.stage,
            'age': self.age,
            'layers': len(self.layers),
            'params': sum(p.numel() for p in self.parameters()),
            'spectral': round(self.spectral_max, 2),
            'stable_count': self.stable_count,
            'log': self.growth_log,
        }


def run_experiment():
    print("="*70)
    print("发育式TNN - 能力驱动生长版")
    print("="*70)
    print("\n生长触发条件:")
    print("  embryo→infant: 训练≥200步, 准确率≥95%, 连续50步达标, 损失<0.5")
    print("  infant→child: 训练≥500步, 准确率≥98%, 连续100步达标, 损失<0.1")
    print("  child→adolescent: 训练≥1000步, 准确率≥99%, 连续200步达标, 损失<0.05")
    print("="*70)
    
    model = GrowingTNN()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    info = model.get_info()
    print(f"\n初始状态:")
    print(f"  阶段: {info['stage']}")
    print(f"  层数: {info['layers']}")
    print(f"  参数量: {info['params']:,}")
    
    print(f"\n开始训练...")
    print("-"*70)
    
    history = []
    
    for step in range(8000):
        # 生成数据
        x = torch.randint(0, 50, (8, 16))
        labels = x.clone()
        
        # 前向
        out = model(x, labels)
        loss = out['loss']
        
        # 反向
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # 计算准确率
        with torch.no_grad():
            preds = out['logits'].argmax(dim=-1)
            acc = (preds == labels).float().mean().item()
        
        # 检查生长（基于能力）
        growth_msg = model.check_growth(step, loss.item(), acc)
        
        # 记录和显示
        if step % 500 == 0 or growth_msg:
            info = model.get_info()
            status = f"Step {step:5d} | Loss: {loss.item():.4f} | Acc: {acc:.3f} | "
            status += f"Stage: {info['stage']:12s} | Layers: {info['layers']} | "
            status += f"Spectral: {info['spectral']:.2f} | Stable: {info['stable_count']:3d}"
            print(status)
    
    print("-"*70)
    info = model.get_info()
    print(f"\n最终状态:")
    print(f"  阶段: {info['stage']}")
    print(f"  年龄: {info['age']}")
    print(f"  层数: {info['layers']}")
    print(f"  参数量: {info['params']:,}")
    print(f"  谱维: {info['spectral']}")
    print(f"\n生长历史:")
    for entry in info['log']:
        print(f"  {entry}")
    
    # 保存
    with open('growing_tnn_ability_driven.json', 'w') as f:
        json.dump(history, f, indent=2)
    print("\n结果已保存到 growing_tnn_ability_driven.json")
    
    return model, history


if __name__ == "__main__":
    run_experiment()
