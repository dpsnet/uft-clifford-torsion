"""
终极融合版 V6 - 简化验证版
二分类任务确保生长可见，验证核心机制
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import os
import gc
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class SimpleBlock(nn.Module):
    """简化功能块"""
    
    def __init__(self, block_id, dim):
        super().__init__()
        self.block_id = block_id
        self.norm = nn.LayerNorm(dim)
        self.processor = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Linear(dim * 2, dim)
        )
        self.torsion_gate = nn.Parameter(torch.randn(dim) * 0.01)
        
        self.excitement = 0.5
        self.success_rate = 0.5
        self.activation_count = 0
    
    def forward(self, x, torsion_field):
        self.activation_count += 1
        h = self.norm(x)
        h = self.processor(h)
        torsion_effect = torch.sigmoid(self.torsion_gate) * torsion_field
        h = h * (1 + torsion_effect.unsqueeze(1))
        out = x + h * 0.5
        self.excitement = min(1.0, self.excitement + 0.01)
        return out
    
    def record_success(self, success):
        alpha = 0.1
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)
        if not success:
            self.excitement = max(0.1, self.excitement - 0.05)
    
    def get_load_priority(self):
        return self.success_rate * 0.6 + self.excitement * 0.4


class SimpleLayer:
    """简化层"""
    
    def __init__(self, layer_id, dim, num_blocks, max_active, offload_dir):
        self.layer_id = layer_id
        self.dim = dim
        self.num_blocks = num_blocks
        self.max_active = max_active
        self.offload_dir = Path(offload_dir)
        
        self.blocks: Dict[int, SimpleBlock] = {}
        for i in range(num_blocks):
            self.blocks[i] = SimpleBlock(i, dim)
        
        self.selector = nn.Linear(dim, num_blocks)
        
        self.training_epochs = 0
        self.best_accuracy = 0.0
        
        self.offload_path = self.offload_dir / f"simple_layer_{layer_id}.pt"
    
    def __call__(self, x, torsion_field):
        scores = torch.sigmoid(self.selector(x.mean(dim=1)))
        adjusted = scores.clone()
        for i, block in self.blocks.items():
            adjusted[0, i] = scores[0, i] * 0.6 + block.get_load_priority() * 0.4
        
        _, top = torch.topk(adjusted[0], min(self.max_active, self.num_blocks))
        
        h = x
        for idx in top.tolist():
            h = self.blocks[idx](h, torsion_field)
            self.blocks[idx].record_success(True)
        
        return h, {'active': top.tolist()}


class UltimateV6(nn.Module):
    """V6简化版 - 二分类任务"""
    
    def __init__(self, initial_layers=2, target_layers=10, dim=128, 
                 num_blocks=4, max_active=2, max_memory=3):
        super().__init__()
        
        self.target_layers = target_layers
        self.dim = dim
        self.num_blocks = num_blocks
        self.max_active = max_active
        self.max_memory = max_memory
        self.offload_dir = Path('./v6_offload')
        self.offload_dir.mkdir(exist_ok=True)
        
        # 输入：简单的特征
        self.input_proj = nn.Linear(32, dim)
        self.pos = nn.Parameter(torch.randn(1, 16, dim) * 0.02)
        
        # 二分类头
        self.classifier = nn.Linear(dim, 2)
        
        self.register_buffer('torsion_field', torch.zeros(1, dim))
        
        self.layers: Dict[int, SimpleLayer] = {}
        self.access_order: List[int] = []
        
        # 生长策略
        self.growth_threshold = 0.55  # 55%即可生长（随机50%）
        self.min_epochs = 10
        
        self.growth_history = []
        
        self._init_layers(initial_layers)
        self._print_info()
    
    def _print_info(self):
        print("="*60)
        print("🎯 终极融合版 V6 - 简化验证")
        print("="*60)
        print("任务: 二分类 (随机50% → 目标80%+)")
        print("生长: 55%阈值，10轮/层")
        print("="*60)
    
    def _init_layers(self, n):
        for i in range(n):
            self.layers[i] = SimpleLayer(i, self.dim, self.num_blocks, self.max_active, self.offload_dir)
            self.access_order.append(i)
    
    def forward(self, x, return_stats=False):
        h = self.input_proj(x).unsqueeze(1)
        h = h + self.pos[:, :1, :]
        
        stats = []
        for idx in sorted(self.layers.keys()):
            h, info = self.layers[idx](h, self.torsion_field)
            stats.append(info)
        
        logits = self.classifier(h.mean(dim=1))
        
        out = {'logits': logits, 'features': h}
        if return_stats:
            out['stats'] = stats
        return out
    
    def training_step(self, x, target, optimizer):
        self.train()
        out = self.forward(x, return_stats=True)
        
        loss = F.cross_entropy(out['logits'], target)
        
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
        optimizer.step()
        
        with torch.no_grad():
            acc = (out['logits'].argmax(dim=-1) == target).float().mean().item()
        
        # 更新最后一层
        last = max(self.layers.keys())
        self.layers[last].training_epochs += 1
        self.layers[last].best_accuracy = max(self.layers[last].best_accuracy, acc)
        
        epochs = self.layers[last].training_epochs
        best = self.layers[last].best_accuracy
        
        should_grow = (acc >= self.growth_threshold and 
                      epochs >= self.min_epochs and 
                      len(self.layers) < self.target_layers)
        
        return {
            'loss': loss.item(),
            'acc': acc,
            'layers': len(self.layers),
            'epochs': epochs,
            'best_acc': best,
            'should_grow': should_grow,
        }
    
    def grow(self):
        current = len(self.layers)
        if current >= self.target_layers:
            return False
        
        print(f"\n🌱 生长: {current}层 → {current+1}层")
        
        new_layer = SimpleLayer(current, self.dim, self.num_blocks, 
                                self.max_active, self.offload_dir)
        
        # Kaiming初始化
        for block in new_layer.blocks.values():
            for name, p in block.named_parameters():
                if 'weight' in name and len(p.shape) >= 2:
                    nn.init.kaiming_normal_(p, mode='fan_out', nonlinearity='relu')
        
        self.layers[current] = new_layer
        self.access_order.insert(0, current)
        
        self.growth_history.append({
            'time': datetime.now().isoformat(),
            'from': current,
            'to': current + 1,
        })
        
        return True


def run_v6():
    print("\n🚀 V6简化验证版\n")
    
    model = UltimateV6(
        initial_layers=2,
        target_layers=10,
        dim=128,
        num_blocks=4,
        max_active=2,
        max_memory=3,
    )
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    peak_acc = 0
    total_growth = 0
    
    for epoch in range(500):
        # 二分类数据：简单的线性可分任务
        x = torch.randn(32, 32)
        # 目标：根据特征和决定类别
        target = (x.sum(dim=-1) > 0).long()
        
        result = model.training_step(x, target, optimizer)
        peak_acc = max(peak_acc, result['acc'])
        
        if result['should_grow']:
            if model.grow():
                total_growth += 1
                optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        
        if (epoch + 1) % 50 == 0:
            print(f"📚 Epoch {epoch+1}: 损失={result['loss']:.3f}, "
                  f"准确率={result['acc']:.1%}(峰值={peak_acc:.1%}), "
                  f"层数={result['layers']}")
            
            if model.layers:
                last = max(model.layers.keys())
                priorities = [b.get_load_priority() for b in model.layers[last].blocks.values()]
                print(f"     块优先级: {[f'{p:.2f}' for p in priorities]}, "
                      f"训练轮数={result['epochs']}")
    
    print(f"\n✅ 完成: {result['layers']}层, 峰值准确率={peak_acc:.1%}, 生长{total_growth}次")


if __name__ == "__main__":
    run_v6()
