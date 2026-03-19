"""
终极融合版TNN - 整合所有优化
宏观: 保守生长策略
中观: 细粒度块选择 + 邻域反馈
微观: 动态扭转场
内存: 磁盘卸载 + LRU缓存
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import os
import json
import gc
import pickle
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class UltimateBlock(nn.Module):
    """终极功能块 - 细粒度 + 邻域反馈"""
    
    def __init__(self, block_id, hidden_dim, ff_dim):
        super().__init__()
        self.block_id = block_id
        self.hidden_dim = hidden_dim
        
        # 核心变换
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.attention = nn.Linear(hidden_dim, hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)
        self.ff = nn.Sequential(
            nn.Linear(hidden_dim, ff_dim),
            nn.GELU(),
            nn.Linear(ff_dim, hidden_dim)
        )
        
        # 扭转门
        self.torsion_gate = nn.Parameter(torch.randn(hidden_dim) * 0.01)
        
        # 邻域反馈状态
        self.excitement = 0.5
        self.success_rate = 0.5
        self.activation_count = 0
        
        # 邻域连接权重
        self.neighbor_weights = {}
    
    def forward(self, x, torsion_field, active=True):
        """前向传播 - 带邻域反馈"""
        if not active:
            return x
        
        self.activation_count += 1
        
        # 基础变换
        h = self.norm1(x)
        h = self.attention(h)
        
        # 扭转调制
        torsion_effect = torch.sigmoid(self.torsion_gate) * torsion_field
        h = h * (1 + torsion_effect.unsqueeze(1))
        
        # 残差
        h = x + h * 0.5
        
        # FFN
        h2 = self.norm2(h)
        h2 = self.ff(h2)
        out = h + h2 * 0.5
        
        # 更新兴奋度
        self.excitement = min(1.0, self.excitement + 0.01)
        
        return out
    
    def record_success(self, success):
        """记录成功/失败 - 邻域反馈"""
        # 更新成功率
        alpha = 0.1
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)
        
        # 兴奋度衰减
        if not success:
            self.excitement = max(0.1, self.excitement - 0.05)
    
    def get_load_priority(self):
        """计算加载优先级"""
        return self.success_rate * 0.6 + self.excitement * 0.4
    
    def to_state_dict(self):
        """序列化状态"""
        return {
            'weights': self.state_dict(),
            'stats': {
                'excitement': self.excitement,
                'success_rate': self.success_rate,
                'activation_count': self.activation_count,
            }
        }
    
    def from_state_dict(self, state):
        """加载状态"""
        self.load_state_dict(state['weights'])
        stats = state['stats']
        self.excitement = stats['excitement']
        self.success_rate = stats['success_rate']
        self.activation_count = stats['activation_count']


class UltimateLayer:
    """终极层 - 细粒度块管理 + 磁盘卸载"""
    
    def __init__(self, layer_id, hidden_dim, ff_dim, num_blocks, offload_dir):
        self.layer_id = layer_id
        self.hidden_dim = hidden_dim
        self.num_blocks = num_blocks
        self.offload_dir = Path(offload_dir)
        
        # 块管理
        self.blocks: Dict[int, UltimateBlock] = {}
        self.block_states: Dict[int, dict] = {}  # 块状态缓存
        
        # 块选择器
        self.block_selector = nn.Linear(hidden_dim, num_blocks)
        
        # 统计
        self.total_activations = 0
        self.layer_best_accuracy = 0.0
        self.training_epochs = 0
        
        # 磁盘路径
        self.offload_path = self.offload_dir / f"layer_{layer_id}.pt"
        
        # 初始创建所有块
        self._create_blocks()
    
    def _create_blocks(self):
        """创建所有功能块"""
        for i in range(self.num_blocks):
            block = UltimateBlock(i, self.hidden_dim, self.hidden_dim // 2)
            self.blocks[i] = block
    
    def forward(self, x, torsion_field, max_active_blocks=2):
        """前向 - 动态块选择"""
        self.total_activations += 1
        
        # 选择要激活的块
        selector_scores = torch.sigmoid(self.block_selector(x.mean(dim=1)))
        
        # 根据成功率和兴奋度调整
        adjusted_scores = selector_scores.clone()
        for i, block in self.blocks.items():
            priority = block.get_load_priority()
            adjusted_scores[0, i] = selector_scores[0, i] * 0.7 + priority * 0.3
        
        # 选择前k个块
        _, top_indices = torch.topk(adjusted_scores[0], min(max_active_blocks, self.num_blocks))
        active_blocks = top_indices.tolist()
        
        # 执行选中的块
        h = x
        for idx in active_blocks:
            block = self.blocks[idx]
            h = block(h, torsion_field, active=True)
        
        # 记录反馈
        for idx in active_blocks:
            self.blocks[idx].record_success(True)
        
        return h, {'active_blocks': active_blocks, 'scores': adjusted_scores}
    
    def save_to_disk(self):
        """保存到磁盘"""
        state = {
            'blocks': {i: b.to_state_dict() for i, b in self.blocks.items()},
            'selector': self.block_selector.state_dict(),
            'stats': {
                'total_activations': self.total_activations,
                'layer_best_accuracy': self.layer_best_accuracy,
                'training_epochs': self.training_epochs,
            }
        }
        torch.save(state, self.offload_path)
    
    def load_from_disk(self):
        """从磁盘加载"""
        if not self.offload_path.exists():
            return False
        
        state = torch.load(self.offload_path)
        
        for i, block_state in state['blocks'].items():
            if i in self.blocks:
                self.blocks[i].from_state_dict(block_state)
        
        self.block_selector.load_state_dict(state['selector'])
        
        stats = state['stats']
        self.total_activations = stats['total_activations']
        self.layer_best_accuracy = stats['layer_best_accuracy']
        self.training_epochs = stats['training_epochs']
        
        return True
    
    def offload(self):
        """卸载释放内存"""
        self.save_to_disk()
        del self.blocks
        self.blocks = {}
        gc.collect()


class UltimateTNN(nn.Module):
    """终极融合版TNN"""
    
    def __init__(self,
                 initial_layers=2,
                 target_layers=50,
                 hidden_dim=1024,
                 vocab_size=500,
                 blocks_per_layer=4,
                 max_active_blocks=2,
                 max_memory_layers=5,
                 offload_dir='./ultimate_offload'):
        super().__init__()
        
        self.target_layers = target_layers
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size
        self.blocks_per_layer = blocks_per_layer
        self.max_active_blocks = max_active_blocks
        self.max_memory_layers = max_memory_layers
        self.offload_dir = Path(offload_dir)
        self.offload_dir.mkdir(parents=True, exist_ok=True)
        
        # 基础模块
        self.embedding = nn.Embedding(vocab_size, hidden_dim)
        self.pos_encoding = nn.Parameter(torch.randn(1, 512, hidden_dim) * 0.02)
        self.lm_head = nn.Linear(hidden_dim, vocab_size)
        
        # 扭转场
        self.register_buffer('torsion_field', torch.zeros(1, hidden_dim))
        
        # 层管理
        self.layers: Dict[int, UltimateLayer] = {}
        self.offloaded_layers: set = set()
        self.access_order: List[int] = []
        
        # 保守生长策略
        self.growth_threshold_accuracy = 0.80
        self.growth_threshold_loss = 0.5
        self.deep_layer_threshold = 0.82
        self.min_cycles_before_growth = 25
        
        self.current_stage = 0
        self.stages = {
            0: ("Embryo", 3),
            1: ("Infant", 5),
            2: ("Child", 8),
            3: ("Adolescent", 12),
            4: ("Adult", 15),
            5: ("Mature", 20),
            6: ("Expert", 30),
            7: ("Master", 50),
        }
        
        self.growth_history = []
        
        # 初始化
        self._init_layers(initial_layers)
        
        # 打印信息
        self._print_info()
    
    def _print_info(self):
        """打印模型信息"""
        print("="*70)
        print("🚀 终极融合版TNN")
        print("="*70)
        print("融合优化:")
        print("  ✅ 保守生长策略 (80%阈值, 25轮/层)")
        print("  ✅ 细粒度块选择 (动态加载2/4块)")
        print("  ✅ 邻域反馈机制 (兴奋度+成功率)")
        print("  ✅ 磁盘卸载 (LRU缓存5层)")
        print("-"*70)
        print(f"   目标层数: {self.target_layers}")
        print(f"   隐藏维度: {self.hidden_dim}")
        print(f"   每层块数: {self.blocks_per_layer} (激活{self.max_active_blocks})")
        print(f"   预估参数: ~{self._estimate_params()/1e6:.0f}M")
        print("="*70)
    
    def _estimate_params(self):
        """估算参数量"""
        base = sum(p.numel() for p in [self.embedding, self.lm_head])
        # 每层: selector + blocks
        layer_params = (
            self.hidden_dim * self.blocks_per_layer +  # selector
            self.blocks_per_layer * (                  # blocks
                self.hidden_dim * self.hidden_dim * 2 +
                self.hidden_dim * (self.hidden_dim // 2) * 2 +
                self.hidden_dim
            )
        )
        return base + layer_params * self.target_layers
    
    def _init_layers(self, num_layers):
        """初始化层"""
        for i in range(num_layers):
            layer = UltimateLayer(
                i, self.hidden_dim, self.hidden_dim // 2,
                self.blocks_per_layer, self.offload_dir
            )
            self.layers[i] = layer
            self.access_order.append(i)
    
    def _get_layer(self, idx):
        """获取层（带LRU）"""
        if idx in self.layers:
            if idx in self.access_order:
                self.access_order.remove(idx)
            self.access_order.insert(0, idx)
            return self.layers[idx]
        
        # 从磁盘加载
        if idx in self.offloaded_layers:
            layer = UltimateLayer(
                idx, self.hidden_dim, self.hidden_dim // 2,
                self.blocks_per_layer, self.offload_dir
            )
            if layer.load_from_disk():
                self._manage_memory()
                self.layers[idx] = layer
                self.access_order.insert(0, idx)
                return layer
        
        return None
    
    def _manage_memory(self):
        """内存管理 - LRU卸载"""
        while len(self.layers) > self.max_memory_layers:
            lru_idx = self.access_order.pop()
            if lru_idx in self.layers:
                layer = self.layers[lru_idx]
                layer.save_to_disk()
                layer.offload()
                del self.layers[lru_idx]
                self.offloaded_layers.add(lru_idx)
                gc.collect()
    
    def forward(self, input_ids, return_stats=False):
        """前向"""
        h = self.embedding(input_ids)
        seq_len = input_ids.size(1)
        h = h + self.pos_encoding[:, :seq_len, :]
        
        # 通过所有层
        layer_stats = []
        for idx in sorted(self.layers.keys()):
            layer = self._get_layer(idx)
            if layer:
                h, stats = layer(h, self.torsion_field, self.max_active_blocks)
                h = h * 0.5 + h  # 残差
                layer_stats.append(stats)
        
        logits = self.lm_head(h)
        
        if return_stats:
            return logits, {'layer_stats': layer_stats}
        return logits
    
    def grow(self, num_new_layers=1):
        """生长"""
        current = len(self.layers) + len(self.offloaded_layers)
        
        # 检查条件
        if current > 0:
            last_layer = self._get_layer(current - 1)
            if last_layer:
                epochs = last_layer.training_epochs
                best_acc = last_layer.layer_best_accuracy
                
                threshold = self.deep_layer_threshold if current >= 15 else self.growth_threshold_accuracy
                
                if epochs < self.min_cycles_before_growth:
                    print(f"⏸️ 生长推迟: 训练不足 ({epochs}/{self.min_cycles_before_growth})")
                    return
                
                if best_acc < threshold:
                    print(f"⏸️ 生长推迟: 准确率不足 ({best_acc:.1%} < {threshold})")
                    return
        
        print(f"\n🌱 生长: {current}层 → {current + num_new_layers}层")
        
        for i in range(num_new_layers):
            new_idx = current + i
            layer = UltimateLayer(
                new_idx, self.hidden_dim, self.hidden_dim // 2,
                self.blocks_per_layer, self.offload_dir
            )
            
            # Kaiming初始化
            for block in layer.blocks.values():
                for name, p in block.named_parameters():
                    if 'weight' in name and len(p.shape) >= 2:
                        nn.init.kaiming_normal_(p, mode='fan_out', nonlinearity='relu')
                    elif 'bias' in name:
                        nn.init.zeros_(p)
            
            self.layers[new_idx] = layer
            self.access_order.insert(0, new_idx)
            self._manage_memory()
        
        # 更新阶段
        for stage_id, (name, target) in self.stages.items():
            if len(self.layers) >= target:
                self.current_stage = stage_id
        
        self.growth_history.append({
            'timestamp': datetime.now().isoformat(),
            'previous': current,
            'new': current + num_new_layers,
            'stage': self.stages[self.current_stage][0],
        })
        
        print(f"   内存中: {len(self.layers)}层 | 磁盘中: {len(self.offloaded_layers)}层")
        print(f"   阶段: {self.stages[self.current_stage][0]}")
    
    def training_step(self, input_ids, targets, optimizer):
        """训练"""
        self.train()
        
        logits, stats = self.forward(input_ids, return_stats=True)
        loss = F.cross_entropy(logits.view(-1, self.vocab_size), targets.view(-1))
        
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
        optimizer.step()
        
        with torch.no_grad():
            preds = logits.argmax(dim=-1)
            accuracy = (preds == targets).float().mean().item()
        
        # 更新层统计
        last_idx = max(self.layers.keys()) if self.layers else 0
        layer = self._get_layer(last_idx)
        if layer:
            layer.training_epochs += 1
            layer.layer_best_accuracy = max(layer.layer_best_accuracy, accuracy)
        
        should_grow = (accuracy >= self.growth_threshold_accuracy and 
                       loss.item() <= self.growth_threshold_loss)
        
        return {
            'loss': loss.item(),
            'accuracy': accuracy,
            'layers': len(self.layers) + len(self.offloaded_layers),
            'should_grow': should_grow,
        }


def run_ultimate_experiment():
    """运行终极实验"""
    print("\n🎯 启动终极融合版实验\n")
    
    model = UltimateTNN(
        initial_layers=2,
        target_layers=30,  # 目标30层
        hidden_dim=1024,
        vocab_size=300,
        blocks_per_layer=4,
        max_active_blocks=2,  # 只激活2/4块
        max_memory_layers=5,  # 内存只存5层
    )
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0003)
    
    def generate_batch(batch_size=4):
        seq = torch.arange(32) % model.vocab_size
        data = seq.unsqueeze(0).repeat(batch_size, 1)
        target = torch.roll(data, shifts=-1, dims=1)
        return data, target
    
    print("\n开始训练...\n")
    max_epochs = 400
    peak_acc = 0
    
    for epoch in range(max_epochs):
        epoch_loss = 0
        epoch_acc = 0
        
        for _ in range(5):
            input_ids, targets = generate_batch()
            result = model.training_step(input_ids, targets, optimizer)
            epoch_loss += result['loss']
            epoch_acc += result['accuracy']
        
        avg_loss = epoch_loss / 5
        avg_acc = epoch_acc / 5
        peak_acc = max(peak_acc, avg_acc)
        
        if (epoch + 1) % 10 == 0:
            print(f"📚 Epoch {epoch + 1}")
            print(f"   损失: {avg_loss:.4f} | 准确率: {avg_acc:.1%} | 峰值: {peak_acc:.1%}")
            print(f"   层数: {result['layers']}/30 | 阶段: {model.stages[model.current_stage][0]}")
        
        if result['should_grow'] and result['layers'] < 30:
            model.grow(1)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.0003)
        
        if result['layers'] >= 20 and avg_acc >= 0.85:
            print(f"\n✅ 达成目标: {result['layers']}层, 准确率{avg_acc:.1%}")
            break
    
    print("\n" + "="*70)
    print("📊 终极融合版实验完成")
    print("="*70)
    print(f"最终层数: {result['layers']}")
    print(f"最终准确率: {avg_acc:.1%}")
    print(f"峰值准确率: {peak_acc:.1%}")
    print(f"生长次数: {len(model.growth_history)}")


if __name__ == "__main__":
    run_ultimate_experiment()
