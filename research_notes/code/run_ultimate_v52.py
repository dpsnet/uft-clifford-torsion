"""
V5.2 - 离身智能渐进式学习
具身和离身都有自己的发育阶段，从简单到复杂
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import os
from pathlib import Path
from typing import Dict, List, Deque, Tuple
from collections import deque

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class DisembodiedCurriculum:
    """离身智能课程学习 - 像婴儿一样从简单到复杂"""
    
    TASKS = {
        'copy': {           # 阶段1: 复制任务（最简单）
            'vocab': 5,
            'seq_len': 4,
            'difficulty': 1,
        },
        'pattern': {        # 阶段2: 固定模式识别
            'vocab': 8,
            'seq_len': 6,
            'difficulty': 2,
        },
        'classification': { # 阶段3: 序列分类
            'vocab': 10,
            'seq_len': 8,
            'difficulty': 3,
        },
        'prediction': {     # 阶段4: 预测下一个token（最难）
            'vocab': 15,
            'seq_len': 10,
            'difficulty': 4,
        },
    }
    
    def __init__(self):
        self.stage = 'copy'  # 从最简单的复制开始
        self.stage_order = ['copy', 'pattern', 'classification', 'prediction']
        self.stage_idx = 0
        self.success_history = deque(maxlen=10)
    
    def get_task(self) -> Tuple[torch.Tensor, torch.Tensor, str]:
        """生成当前阶段的任务数据"""
        cfg = self.TASKS[self.stage]
        vocab, seq_len = cfg['vocab'], cfg['seq_len']
        
        batch_size = 4
        
        if self.stage == 'copy':
            # 复制任务：输入=输出
            x = torch.randint(0, vocab, (batch_size, seq_len))
            y = x.clone()
            
        elif self.stage == 'pattern':
            # 固定模式：ABAB...
            x = torch.zeros(batch_size, seq_len, dtype=torch.long)
            for i in range(seq_len):
                x[:, i] = i % 2  # 0,1,0,1,...
            y = x.clone()
            
        elif self.stage == 'classification':
            # 序列分类：根据前3个token决定类别
            x = torch.randint(0, vocab, (batch_size, seq_len))
            # 目标是前3个token的和的类别
            y = (x[:, :3].sum(dim=1) % vocab).unsqueeze(1).expand(-1, seq_len)
            
        else:  # prediction
            # 预测下一个token
            x = torch.randint(0, vocab, (batch_size, seq_len))
            y = torch.cat([x[:, 1:], torch.randint(0, vocab, (batch_size, 1))], dim=1)
        
        return x, y, self.stage
    
    def record_success(self, accuracy: float):
        """记录学习成功率"""
        self.success_history.append(accuracy)
    
    def check_promotion(self) -> bool:
        """检查是否应进入下一阶段"""
        if len(self.success_history) < 5:
            return False
        
        avg_success = sum(self.success_history) / len(self.success_history)
        
        # 当前阶段掌握度>80%，晋升
        if avg_success >= 0.80 and self.stage_idx < len(self.stage_order) - 1:
            self.stage_idx += 1
            self.stage = self.stage_order[self.stage_idx]
            self.success_history.clear()
            print(f"\n🎓 离身智能晋升! 进入 {self.stage} 阶段\n")
            return True
        
        return False


class UltimateV52(nn.Module):
    """V5.2 - 双路径都有自己的课程学习"""
    
    def __init__(self, dim=256):
        super().__init__()
        self.dim = dim
        
        # 编码器
        self.sensory_enc = nn.Linear(64, dim)
        self.symbol_emb = nn.Embedding(20, dim)
        
        # 具身路径（简单快速）
        self.embodied_norm = nn.LayerNorm(dim)
        self.embodied_processor = nn.Sequential(
            nn.Linear(dim, dim), nn.Tanh(), nn.Linear(dim, dim)
        )
        self.action_head = nn.Linear(dim, 2)
        
        # 离身路径（复杂深层）
        self.disembodied_layers = nn.ModuleList([
            nn.TransformerEncoderLayer(d_model=dim, nhead=4, dim_feedforward=dim*2, batch_first=True)
            for _ in range(2)
        ])
        self.symbol_head = nn.Linear(dim, 20)
        
        self.register_buffer('torsion', torch.zeros(1, dim))
        
        # 离身课程学习器
        self.disembodied_curriculum = DisembodiedCurriculum()
        
        # 发育状态
        self.layers = 1
        self.target_layers = 20
        
    def forward(self, sensory, symbol=None):
        # 具身路径
        emb_h = self.sensory_enc(sensory).unsqueeze(1)
        emb_h = self.embodied_norm(emb_h)
        emb_h = self.embodied_processor(emb_h)
        emb_out = self.action_head(emb_h.mean(dim=1))
        
        # 离身路径
        dis_out = None
        if symbol is not None:
            dis_h = self.symbol_emb(symbol)
            for layer in self.disembodied_layers:
                dis_h = layer(dis_h)
            dis_out = self.symbol_head(dis_h)
        
        return {'action': emb_out, 'symbol': dis_out}
    
    def training_step(self, optimizer):
        """单步训练 - 双路径分别学习"""
        
        # === 具身任务 ===
        sensory = torch.randn(8, 64)
        action_target = (sensory.sum(dim=-1) > 0).long()
        
        # === 离身任务（课程学习）===
        symbol_input, symbol_target, task_stage = self.disembodied_curriculum.get_task()
        
        # 前向
        out = self.forward(sensory, symbol_input)
        
        # 具身损失
        loss_embodied = F.cross_entropy(out['action'], action_target)
        acc_embodied = (out['action'].argmax(-1) == action_target).float().mean().item()
        
        # 离身损失
        if out['symbol'] is not None:
            # 根据任务类型调整目标维度
            if task_stage in ['copy', 'pattern', 'prediction']:
                loss_disembodied = F.cross_entropy(
                    out['symbol'].reshape(-1, 20),
                    symbol_target.reshape(-1).clamp(0, 19)
                )
                acc_disembodied = (out['symbol'].argmax(-1) == symbol_target).float().mean().item()
            else:  # classification
                loss_disembodied = F.cross_entropy(
                    out['symbol'].mean(dim=1),
                    symbol_target[:, 0].clamp(0, 19)
                )
                acc_disembodied = (out['symbol'].mean(dim=1).argmax(-1) == symbol_target[:, 0]).float().mean().item()
        else:
            loss_disembodied = torch.tensor(0.0)
            acc_disembodied = 0.0
        
        # 动态权重：离身随着阶段提升权重增加
        disembodied_weight = 0.2 + self.disembodied_curriculum.stage_idx * 0.2  # 0.2 -> 0.8
        total_loss = loss_embodied * (1 - disembodied_weight) + loss_disembodied * disembodied_weight
        
        # 反向
        optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
        optimizer.step()
        
        # 记录离身学习进度
        self.disembodied_curriculum.record_success(acc_disembodied)
        
        return {
            'loss': total_loss.item(),
            'embodied_acc': acc_embodied,
            'disembodied_acc': acc_disembodied,
            'disembodied_stage': task_stage,
            'layers': self.layers,
        }
    
    def grow(self):
        """网络生长"""
        if self.layers >= self.target_layers:
            return False
        
        # 添加新的离身层
        new_layer = nn.TransformerEncoderLayer(
            d_model=self.dim, nhead=4, dim_feedforward=self.dim*2, batch_first=True
        )
        self.disembodied_layers.append(new_layer)
        self.layers += 1
        print(f"   🌱 生长: {self.layers-1}层 → {self.layers}层")
        return True


def run_v52():
    print("\n" + "="*60)
    print("🚀 V5.2 - 离身智能渐进式学习")
    print("="*60)
    print("离身发育阶段:")
    print("  1. copy         - 复制任务（最简单）")
    print("  2. pattern      - 固定模式识别")
    print("  3. classification - 序列分类")
    print("  4. prediction   - 预测下一个token")
    print("="*60 + "\n")
    
    model = UltimateV52(dim=256)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    
    stats = {'embodied': [], 'disembodied': [], 'stage_changes': []}
    
    for epoch in range(1000):
        result = model.training_step(optimizer)
        
        stats['embodied'].append(result['embodied_acc'])
        stats['disembodied'].append(result['disembodied_acc'])
        
        # 检查离身晋升
        promoted = model.disembodied_curriculum.check_promotion()
        if promoted:
            stats['stage_changes'].append((epoch, model.disembodied_curriculum.stage))
        
        # 每100轮报告
        if (epoch + 1) % 100 == 0:
            avg_emb = sum(stats['embodied'][-100:]) / 100
            avg_dis = sum(stats['disembodied'][-100:]) / 100
            print(f"📚 Epoch {epoch+1}: 具身={avg_emb:.1%}, 离身={avg_dis:.1%}, "
                  f"任务={result['disembodied_stage']}, 层数={result['layers']}")
            
            # 生长决策
            if avg_emb >= 0.80 and avg_dis >= 0.70:
                model.grow()
                optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    
    print(f"\n✅ 完成!")
    print(f"   最终层数: {model.layers}")
    print(f"   离身最终阶段: {model.disembodied_curriculum.stage}")
    print(f"   离身晋升次数: {len(stats['stage_changes'])}")
    if stats['stage_changes']:
        for ep, st in stats['stage_changes']:
            print(f"      Epoch {ep}: {st}")


if __name__ == "__main__":
    run_v52()
