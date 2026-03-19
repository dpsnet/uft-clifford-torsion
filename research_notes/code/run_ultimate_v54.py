"""
V5.4 - 完全整合版
网络生长 + 具身发育 + 离身渐进学习
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
from typing import Dict, List, Tuple
from collections import deque

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class DelayedBuffer:
    def __init__(self, max_delay=10):
        self.buffer = deque(maxlen=max_delay)
    def write(self, x):
        self.buffer.append(x.clone().detach())
    def read(self, delay=None):
        if len(self.buffer) == 0:
            return None
        delay = delay or max(1, len(self.buffer) // 2)
        idx = max(0, len(self.buffer) - delay - 1)
        return self.buffer[idx] if idx < len(self.buffer) else self.buffer[0]


class EmbodiedBlock(nn.Module):
    """具身块 - 快速响应"""
    def __init__(self, dim):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.processor = nn.Sequential(
            nn.Linear(dim, dim), nn.Tanh(), nn.Linear(dim, dim)
        )
    def forward(self, x, torsion):
        h = self.norm(x)
        h = self.processor(h)
        return x + h * 0.3


class DisembodiedBlock(nn.Module):
    """离身块 - 深度处理"""
    def __init__(self, dim):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn = nn.Linear(dim, dim)
        self.norm2 = nn.LayerNorm(dim)
        self.ff = nn.Sequential(nn.Linear(dim, dim*2), nn.GELU(), nn.Linear(dim*2, dim))
    def forward(self, x, torsion, delayed):
        h = self.norm1(x)
        h = self.attn(h)
        if delayed is not None:
            h = h + delayed.unsqueeze(1) * 0.2
        h = x + h * 0.5
        h2 = self.norm2(h)
        h2 = self.ff(h2)
        return h + h2 * 0.5


class DevelopmentalLayer(nn.Module):
    """发育层 - 包含具身和离身组件"""
    def __init__(self, layer_id, dim, disembodied_unlocked=False):
        super().__init__()
        self.layer_id = layer_id
        self.dim = dim
        
        # 具身组件（始终存在）
        self.embodied_blocks = nn.ModuleList([EmbodiedBlock(dim) for _ in range(2)])
        self.embodied_selector = nn.Linear(dim, 2)
        
        # 离身组件（阶段解锁后创建）
        self.disembodied_blocks = nn.ModuleList()
        self.disembodied_selector = None
        self.delay_buffer = DelayedBuffer(10)
        
        if disembodied_unlocked:
            self._unlock_disembodied()
    
    def _unlock_disembodied(self):
        """解锁离身组件"""
        if self.disembodied_selector is None:
            self.disembodied_selector = nn.Linear(self.dim, 2)
            self.disembodied_blocks = nn.ModuleList([DisembodiedBlock(self.dim) for _ in range(2)])
    
    def forward(self, emb_input, dis_input, torsion, disembodied_unlocked=False, delay_steps=0):
        # 具身路径
        scores = torch.sigmoid(self.embodied_selector(emb_input.mean(dim=1)))
        _, top = torch.topk(scores[0], 2)
        emb_h = emb_input
        for idx in top.tolist():
            emb_h = self.embodied_blocks[idx](emb_h, torsion)
        
        # 离身路径
        dis_h = None
        if disembodied_unlocked and dis_input is not None and self.disembodied_selector is not None:
            self.delay_buffer.write(dis_input.mean(dim=1))
            delayed = self.delay_buffer.read(delay_steps)
            
            scores = torch.sigmoid(self.disembodied_selector(dis_input.mean(dim=1)))
            _, top = torch.topk(scores[0], 2)
            dis_h = dis_input
            for idx in top.tolist():
                dis_h = self.disembodied_blocks[idx](dis_h, torsion, delayed)
        
        return emb_h, dis_h


class DisembodiedCurriculum:
    """离身渐进学习课程"""
    STAGES = ['copy', 'pattern', 'classify', 'predict']
    
    def __init__(self):
        self.stage_idx = 0
        self.success_history = deque(maxlen=10)
    
    def get_task(self, batch_size=8):
        """获取当前阶段的任务"""
        stage = self.STAGES[self.stage_idx]
        
        if stage == 'copy':
            x = torch.randint(0, 5, (batch_size, 4))
            y = x.clone()
        elif stage == 'pattern':
            x = torch.tensor([[0,1,0,1], [1,0,1,0]] * (batch_size//2))
            y = x.clone()
        elif stage == 'classify':
            # 简单二分类：全0或全1
            if torch.rand(1) > 0.5:
                x = torch.zeros(batch_size, 4, dtype=torch.long)
                y = torch.zeros(batch_size, 4, dtype=torch.long)
            else:
                x = torch.ones(batch_size, 4, dtype=torch.long)
                y = torch.ones(batch_size, 4, dtype=torch.long)
        else:  # predict
            # 简化预测：只预测下一个是不是0
            x = torch.randint(0, 4, (batch_size, 6))
            y = (x[:, -1] == 0).long().unsqueeze(1).expand(-1, 6)  # 最后一个是否为0
        
        return x, y, stage
    
    def record(self, acc):
        self.success_history.append(acc)
    
    def check_promotion(self):
        if len(self.success_history) < 10:
            return False
        avg = sum(self.success_history) / len(self.success_history)
        if avg >= 0.85 and self.stage_idx < len(self.STAGES) - 1:
            self.stage_idx += 1
            self.success_history.clear()
            return True
        return False


class UltimateV54(nn.Module):
    """V5.4 - 完全整合版"""
    
    def __init__(self, initial_layers=1, target_layers=15, dim=256):
        super().__init__()
        self.dim = dim
        self.target_layers = target_layers
        
        # 编码器
        self.sensory_enc = nn.Linear(64, dim)
        self.symbol_emb = nn.Embedding(10, dim)
        
        # 输出头
        self.action_head = nn.Linear(dim, 2)
        self.symbol_head = nn.Linear(dim, 10)
        
        self.register_buffer('torsion', torch.zeros(1, dim))
        
        # 发育系统
        self.layers = nn.ModuleList()
        for i in range(initial_layers):
            self.layers.append(DevelopmentalLayer(i, dim, disembodied_unlocked=False))
        
        # 离身课程
        self.curriculum = DisembodiedCurriculum()
        
        # 阶段状态
        self.disembodied_unlocked = False
        self.current_stage = 'sensorimotor'
        self.epochs_since_growth = 0
    
    def unlock_disembodied(self):
        """解锁所有层的离身组件"""
        self.disembodied_unlocked = True
        for layer in self.layers:
            layer._unlock_disembodied()
        print("   🔓 离身智能解锁!")
    
    def add_layer(self):
        """添加新层"""
        if len(self.layers) >= self.target_layers:
            return False
        new_idx = len(self.layers)
        new_layer = DevelopmentalLayer(new_idx, self.dim, self.disembodied_unlocked)
        
        # Kaiming初始化
        for p in new_layer.parameters():
            if len(p.shape) >= 2:
                nn.init.kaiming_normal_(p, mode='fan_out', nonlinearity='relu')
        
        self.layers.append(new_layer)
        self.epochs_since_growth = 0
        print(f"   🌱 生长: {new_idx}层 → {new_idx+1}层")
        return True
    
    def forward(self, sensory, symbol=None):
        emb_h = self.sensory_enc(sensory).unsqueeze(1)
        dis_h = self.symbol_emb(symbol) if symbol is not None else None
        
        for layer in self.layers:
            emb_h, dis_h = layer(emb_h, dis_h, self.torsion, 
                                self.disembodied_unlocked, delay_steps=3)
        
        return {
            'action': self.action_head(emb_h.mean(dim=1)),
            'symbol': self.symbol_head(dis_h) if dis_h is not None else None
        }
    
    def training_step(self, optimizer):
        # === 具身任务 ===
        sensory = torch.randn(8, 64)
        action_target = (sensory.sum(dim=-1) > 0).long()
        
        # === 离身任务 ===
        symbol, symbol_target, dis_stage = self.curriculum.get_task()
        
        # 前向
        out = self.forward(sensory, symbol if self.disembodied_unlocked else None)
        
        # 具身损失
        loss_action = F.cross_entropy(out['action'], action_target)
        acc_action = (out['action'].argmax(-1) == action_target).float().mean().item()
        
        # 离身损失（解锁后）
        if self.disembodied_unlocked and out['symbol'] is not None:
            loss_symbol = F.cross_entropy(out['symbol'].reshape(-1, 10), 
                                         symbol_target.reshape(-1).clamp(0, 9))
            acc_symbol = (out['symbol'].argmax(-1) == symbol_target).float().mean().item()
            self.curriculum.record(acc_symbol)
        else:
            loss_symbol = torch.tensor(0.0)
            acc_symbol = 0.0
        
        # 动态权重
        if self.disembodied_unlocked:
            dis_weight = 0.3 + self.curriculum.stage_idx * 0.15
        else:
            dis_weight = 0.0
        
        total_loss = loss_action * (1 - dis_weight) + loss_symbol * dis_weight
        
        # 反向
        optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
        optimizer.step()
        
        self.epochs_since_growth += 1
        
        return {
            'loss': total_loss.item(),
            'acc_action': acc_action,
            'acc_symbol': acc_symbol,
            'layers': len(self.layers),
            'stage': dis_stage if self.disembodied_unlocked else 'locked',
        }


def run_v54():
    print("\n" + "="*60)
    print("🚀 V5.4B - 延长训练版")
    print("="*60)
    print("改进:")
    print("  • 总轮数: 1200 → 2000")
    print("  • 每阶段200轮评估（原为100轮）")
    print("  • predict阶段延长训练")
    print("="*60 + "\n")
    
    model = UltimateV54(initial_layers=1, target_layers=15, dim=256)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    
    stats = {'action': [], 'symbol': [], 'promotions': []}
    
    for epoch in range(2000):
        result = model.training_step(optimizer)
        stats['action'].append(result['acc_action'])
        stats['symbol'].append(result['acc_symbol'])
        
        # 离身晋升检查
        if model.disembodied_unlocked:
            promoted = model.curriculum.check_promotion()
            if promoted:
                new_stage = model.curriculum.STAGES[model.curriculum.stage_idx]
                stats['promotions'].append((epoch, new_stage))
                print(f"\n🎓 离身晋升! 进入 {new_stage} 阶段\n")
        
        # 每200轮报告（延长训练）
        if (epoch + 1) % 200 == 0:
            avg_action = sum(stats['action'][-100:]) / 100
            avg_symbol = sum(stats['symbol'][-100:]) / 100 if model.disembodied_unlocked else 0
            
            print(f"📚 Epoch {epoch+1}: 具身={avg_action:.1%}, "
                  f"离身={avg_symbol:.1%}, 层数={result['layers']}, "
                  f"阶段={result['stage']}")
            
            # === 发育决策 ===
            
            # 1. 胚胎期: 每100轮自动生长（1→4层）
            if result['layers'] < 4 and model.epochs_since_growth >= 100:
                model.add_layer()
                optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
            
            # 2. 解锁离身: 具身掌握后（5层以上，准确率>80%）
            elif result['layers'] >= 4 and not model.disembodied_unlocked and avg_action >= 0.80:
                model.unlock_disembodied()
                print(f"   📚 Epoch {epoch+1}: 具身={avg_action:.1%}, "
                      f"离身={avg_symbol:.1%}, 层数={result['layers']}, "
                      f"阶段={result['stage']}")
            
            # 3. 正常生长期: 双路径都达标（延长到100轮）
            elif (model.disembodied_unlocked and 
                  avg_action >= 0.75 and 
                  avg_symbol >= 0.50 and  # 降低离身要求到50%
                  model.epochs_since_growth >= 100 and
                  result['layers'] < model.target_layers):
                model.add_layer()
                optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    
    print(f"\n{'='*60}")
    print("✅ V5.4 发育完成!")
    print(f"   最终层数: {len(model.layers)}")
    print(f"   离身阶段: {model.curriculum.STAGES[model.curriculum.stage_idx]}")
    print(f"   离身晋升: {len(stats['promotions'])}次")
    for ep, st in stats['promotions']:
        print(f"      Epoch {ep}: {st}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_v54()
