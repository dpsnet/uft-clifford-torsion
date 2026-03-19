"""
V5离身优化快速测试 - 只跑200轮验证离身准确率
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
from pathlib import Path
from typing import Dict, List
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
    def __init__(self, block_id, dim):
        super().__init__()
        self.block_id = block_id
        self.norm = nn.LayerNorm(dim)
        self.processor = nn.Sequential(nn.Linear(dim, dim), nn.Tanh(), nn.Linear(dim, dim))
        self.excitement = 0.5
        self.success_rate = 0.5
    def forward(self, x, torsion):
        h = self.norm(x)
        h = self.processor(h)
        h = h * (1 + torsion.unsqueeze(1) * 0.1)
        return x + h * 0.3
    def record_success(self, success):
        alpha = 0.1
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)

class DisembodiedBlock(nn.Module):
    def __init__(self, block_id, dim):
        super().__init__()
        self.block_id = block_id
        self.norm1 = nn.LayerNorm(dim)
        self.attn = nn.Linear(dim, dim)
        self.norm2 = nn.LayerNorm(dim)
        self.ff = nn.Sequential(nn.Linear(dim, dim * 2), nn.GELU(), nn.Linear(dim * 2, dim))
        self.excitement = 0.3
        self.success_rate = 0.3
    def forward(self, x, torsion, delayed):
        h = self.norm1(x)
        h = self.attn(h)
        if delayed is not None:
            h = h + delayed.unsqueeze(1) * 0.2
        h = h * (1 + torsion.unsqueeze(1) * 0.05)
        h = x + h * 0.5
        h2 = self.norm2(h)
        h2 = self.ff(h2)
        return h + h2 * 0.5
    def record_success(self, success):
        alpha = 0.1  # 提高学习率
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)

class DevLayer(nn.Module):
    def __init__(self, layer_id, dim, num_blocks, disembodied_unlocked):
        super().__init__()
        self.layer_id = layer_id
        self.dim = dim
        self.num_blocks = num_blocks
        
        self.embodied_blocks = {i: EmbodiedBlock(i, dim) for i in range(num_blocks)}
        self.embodied_selector = nn.Linear(dim, num_blocks)
        
        self.disembodied_blocks = {}
        self.disembodied_selector = None
        self.delay_buffer = DelayedBuffer(10)
        
        if disembodied_unlocked:
            self.disembodied_selector = nn.Linear(dim, num_blocks)
            self.disembodied_blocks = {i: DisembodiedBlock(i, dim) for i in range(num_blocks)}
    
    def __call__(self, emb_input, dis_input, torsion, dis_unlocked, delay_steps):
        # Embodied path
        scores = torch.sigmoid(self.embodied_selector(emb_input.mean(dim=1)))
        _, top = torch.topk(scores[0], 2)
        emb_h = emb_input
        for idx in top.tolist():
            emb_h = self.embodied_blocks[idx](emb_h, torsion)
            self.embodied_blocks[idx].record_success(True)
        
        # Disembodied path
        dis_h = None
        if dis_unlocked and dis_input is not None and self.disembodied_selector is not None:
            self.delay_buffer.write(dis_input.mean(dim=1))
            delayed = self.delay_buffer.read(delay_steps)
            
            scores = torch.sigmoid(self.disembodied_selector(dis_input.mean(dim=1)))
            _, top = torch.topk(scores[0], 2)
            dis_h = dis_input
            for idx in top.tolist():
                dis_h = self.disembodied_blocks[idx](dis_h, torsion, delayed)
                self.disembodied_blocks[idx].record_success(True)
        
        return emb_h, dis_h

class TestModel(nn.Module):
    def __init__(self, layers=5, dim=128):
        super().__init__()
        self.dim = dim
        self.sensory_enc = nn.Linear(32, dim)
        self.symbol_emb = nn.Embedding(10, dim)
        self.action_head = nn.Linear(dim, 2)
        self.symbol_head = nn.Linear(dim, 10)
        self.register_buffer('torsion', torch.zeros(1, dim))
        
        self.layers = nn.ModuleList()
        for i in range(layers):
            self.layers.append(DevLayer(i, dim, 4, disembodied_unlocked=True))
        
        self.stage = 'formal'  # 直接测试formal阶段
    
    def forward(self, sensory, symbol):
        emb_h = self.sensory_enc(sensory).unsqueeze(1)
        dis_h = self.symbol_emb(symbol)
        
        for layer in self.layers:
            emb_h, dis_h = layer(emb_h, dis_h, self.torsion, True, 5)
        
        return {
            'action': self.action_head(emb_h.mean(dim=1)),
            'symbol': self.symbol_head(dis_h) if dis_h is not None else None
        }

def test():
    print("🧪 V5离身优化快速测试\n")
    model = TestModel(layers=5, dim=128)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    for epoch in range(200):
        # 具身任务：二分类
        sensory = torch.randn(16, 32)
        action_target = (sensory.sum(dim=-1) > 0).long()
        
        # 离身任务：预测下一个token
        symbol = torch.randint(0, 10, (16, 8))
        symbol_target = torch.cat([symbol[:, 1:], torch.randint(0, 10, (16, 1))], dim=1)
        
        out = model(sensory, symbol)
        
        loss_action = F.cross_entropy(out['action'], action_target)
        loss_symbol = F.cross_entropy(out['symbol'].reshape(-1, 10), symbol_target.reshape(-1))
        
        # 30%具身 + 70%离身（formal阶段权重）
        loss = loss_action * 0.3 + loss_symbol * 0.7
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        with torch.no_grad():
            acc_action = (out['action'].argmax(-1) == action_target).float().mean().item()
            acc_symbol = (out['symbol'].argmax(-1) == symbol_target).float().mean().item()
        
        if (epoch + 1) % 20 == 0:
            print(f"Epoch {epoch+1}: 具身={acc_action:.1%}, 离身={acc_symbol:.1%}, 损失={loss.item():.3f}")
    
    print(f"\n✅ 最终: 具身={acc_action:.1%}, 离身={acc_symbol:.1%}")

if __name__ == "__main__":
    test()
