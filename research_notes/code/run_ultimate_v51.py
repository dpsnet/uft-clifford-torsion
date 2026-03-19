"""
V5.1 增强版 - 离身智能优化
更大的网络 + 更长的训练 + 改进的离身任务
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import os
import gc
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Deque
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


class EmbodiedBlockV51(nn.Module):
    def __init__(self, block_id, dim):
        super().__init__()
        self.block_id = block_id
        self.norm = nn.LayerNorm(dim)
        self.processor = nn.Sequential(
            nn.Linear(dim, dim),
            nn.Tanh(),
            nn.Linear(dim, dim)
        )
        self.excitement = 0.5
        self.success_rate = 0.5
    
    def forward(self, x, torsion_field):
        h = self.norm(x)
        h = self.processor(h)
        h = h * (1 + torsion_field.unsqueeze(1) * 0.1)
        return x + h * 0.3
    
    def record_success(self, success):
        alpha = 0.1
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)


class DisembodiedBlockV51(nn.Module):
    def __init__(self, block_id, dim):
        super().__init__()
        self.block_id = block_id
        self.norm1 = nn.LayerNorm(dim)
        self.attention = nn.MultiheadAttention(dim, num_heads=4, batch_first=True)
        self.norm2 = nn.LayerNorm(dim)
        self.ff = nn.Sequential(
            nn.Linear(dim, dim * 4),  # 更大的FFN
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(dim * 4, dim)
        )
        self.excitement = 0.3
        self.success_rate = 0.3
    
    def forward(self, x, torsion_field, delayed_context=None):
        # 使用多头注意力替代简单线性
        h = self.norm1(x)
        h, _ = self.attention(h, h, h)
        
        if delayed_context is not None:
            h = h + delayed_context.unsqueeze(1) * 0.3
        
        h = h * (1 + torsion_field.unsqueeze(1) * 0.05)
        h = x + h * 0.5
        
        h2 = self.norm2(h)
        h2 = self.ff(h2)
        return h + h2 * 0.5
    
    def record_success(self, success):
        alpha = 0.15  # 更高的学习率
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)


class DevelopmentalLayerV51(nn.Module):
    def __init__(self, layer_id, dim, num_blocks, disembodied_unlocked):
        super().__init__()
        self.layer_id = layer_id
        self.dim = dim
        self.num_blocks = num_blocks
        
        self.embodied_blocks = nn.ModuleList([EmbodiedBlockV51(i, dim) for i in range(num_blocks)])
        self.embodied_selector = nn.Linear(dim, num_blocks)
        
        self.disembodied_blocks = nn.ModuleList()
        self.disembodied_selector = None
        self.delay_buffer = DelayedBuffer(10)
        
        if disembodied_unlocked:
            self.disembodied_selector = nn.Linear(dim, num_blocks)
            self.disembodied_blocks = nn.ModuleList([DisembodiedBlockV51(i, dim) for i in range(num_blocks)])
    
    def forward(self, embodied_input, disembodied_input, torsion_field, 
                max_active_blocks=2, disembodied_unlocked=False, delay_steps=0):
        
        # Embodied path
        scores = torch.sigmoid(self.embodied_selector(embodied_input.mean(dim=1)))
        _, top = torch.topk(scores[0], min(max_active_blocks, self.num_blocks))
        
        embodied_h = embodied_input
        for idx in top.tolist():
            embodied_h = self.embodied_blocks[idx](embodied_h, torsion_field)
            self.embodied_blocks[idx].record_success(True)
        
        # Disembodied path
        disembodied_h = None
        if disembodied_unlocked and disembodied_input is not None and self.disembodied_selector is not None:
            self.delay_buffer.write(disembodied_input.mean(dim=1))
            delayed = self.delay_buffer.read(delay_steps)
            
            scores = torch.sigmoid(self.disembodied_selector(disembodied_input.mean(dim=1)))
            _, top = torch.topk(scores[0], min(max_active_blocks, self.num_blocks))
            
            disembodied_h = disembodied_input
            for idx in top.tolist():
                disembodied_h = self.disembodied_blocks[idx](disembodied_h, torsion_field, delayed)
                self.disembodied_blocks[idx].record_success(True)
        
        return embodied_h, disembodied_h


class UltimateV51(nn.Module):
    def __init__(self, layers=2, dim=256, target_layers=20):
        super().__init__()
        self.dim = dim
        self.target_layers = target_layers
        
        self.sensory_encoder = nn.Linear(64, dim)
        self.symbol_embedding = nn.Embedding(20, dim)
        
        self.action_head = nn.Linear(dim, 2)
        self.symbol_head = nn.Linear(dim, 20)
        
        self.register_buffer('torsion_field', torch.zeros(1, dim))
        
        self.layers = nn.ModuleList()
        for i in range(layers):
            self.layers.append(DevelopmentalLayerV51(i, dim, 4, disembodied_unlocked=True))
        
        self.stage = 'formal'
        self.disembodied_ratio = 0.7  # 70%离身
    
    def forward(self, sensory_input, symbol_input):
        emb_h = self.sensory_encoder(sensory_input).unsqueeze(1)
        dis_h = self.symbol_embedding(symbol_input)
        
        for layer in self.layers:
            emb_h, dis_h = layer(emb_h, dis_h, self.torsion_field, 
                                max_active_blocks=2, 
                                disembodied_unlocked=True, 
                                delay_steps=5)
        
        return {
            'action_logits': self.action_head(emb_h.mean(dim=1)),
            'symbol_logits': self.symbol_head(dis_h) if dis_h is not None else None,
        }
    
    def grow(self):
        new_idx = len(self.layers)
        if new_idx >= self.target_layers:
            return False
        
        new_layer = DevelopmentalLayerV51(new_idx, self.dim, 4, disembodied_unlocked=True)
        
        # Kaiming初始化
        for p in new_layer.parameters():
            if len(p.shape) >= 2:
                nn.init.kaiming_normal_(p, mode='fan_out', nonlinearity='relu')
        
        self.layers.append(new_layer)
        print(f"   🌱 生长: {new_idx}层 → {new_idx+1}层")
        return True


def run_v51():
    print("\n" + "="*60)
    print("🚀 V5.1 增强版 - 离身智能优化")
    print("="*60)
    print("改进:")
    print("  • 多头注意力替换线性注意力")
    print("  • 更大FFN (4x dim)")
    print("  • 更高离身学习率 (0.15)")
    print("  • 70%离身权重")
    print("="*60 + "\n")
    
    model = UltimateV51(layers=2, dim=256, target_layers=15)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    
    peak_embodied = 0
    peak_disembodied = 0
    
    for epoch in range(1500):
        # 具身任务
        sensory = torch.randn(8, 64)
        action_target = (sensory.sum(dim=-1) > 0).long()
        
        # 离身任务：简单的分类（不是序列预测）
        symbol = torch.randint(0, 20, (8, 4))
        # 目标：根据序列中的第一个token决定类别
        symbol_target = symbol[:, 0]  # 简化：预测第一个token
        
        out = model(sensory, symbol)
        
        loss_embodied = F.cross_entropy(out['action_logits'], action_target)
        loss_disembodied = F.cross_entropy(out['symbol_logits'].mean(dim=1), symbol_target)
        
        # 30%具身 + 70%离身
        loss = loss_embodied * 0.3 + loss_disembodied * 0.7
        
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        
        with torch.no_grad():
            acc_embodied = (out['action_logits'].argmax(-1) == action_target).float().mean().item()
            acc_disembodied = (out['symbol_logits'].mean(dim=1).argmax(-1) == symbol_target).float().mean().item()
        
        peak_embodied = max(peak_embodied, acc_embodied)
        peak_disembodied = max(peak_disembodied, acc_disembodied)
        
        # 生长决策：每100轮添加一层
        if (epoch + 1) % 100 == 0 and len(model.layers) < model.target_layers:
            if acc_embodied >= 0.70 and acc_disembodied >= 0.50:  # 双路径都达标
                model.grow()
                optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
        
        if (epoch + 1) % 100 == 0:
            print(f"📚 Epoch {epoch+1}: 具身={acc_embodied:.1%}(峰值{peak_embodied:.1%}), "
                  f"离身={acc_disembodied:.1%}(峰值{peak_disembodied:.1%}), 层数={len(model.layers)}")
    
    print(f"\n✅ 完成: {len(model.layers)}层")
    print(f"   具身峰值: {peak_embodied:.1%}")
    print(f"   离身峰值: {peak_disembodied:.1%}")


if __name__ == "__main__":
    run_v51()
