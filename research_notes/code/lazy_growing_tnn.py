"""
按需激活TNN - Lazy Loading层管理
只有当前需要的层在内存，其他层保存在磁盘
用磁盘空间换内存，支持超大规模模型
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import os
import pickle
import tempfile
import gc
from pathlib import Path
from datetime import datetime
from typing import Optional, List


class LazyLayer:
    """懒加载层 - 按需从磁盘加载到内存"""
    
    def __init__(self, layer_id: int, hidden_dim: int, offload_dir: str):
        self.layer_id = layer_id
        self.hidden_dim = hidden_dim
        self.offload_dir = offload_dir
        self.cache_file = os.path.join(offload_dir, f'layer_{layer_id}.pt')
        
        # 内存中的实际层（可能为None）
        self._layer: Optional[nn.Module] = None
        self._in_memory = False
        self._access_count = 0
        self._last_access = 0
    
    def _create_layer(self):
        """创建层结构"""
        layer = nn.ModuleDict({
            'norm1': nn.LayerNorm(self.hidden_dim),
            'attn': nn.Linear(self.hidden_dim, self.hidden_dim, bias=False),
            'norm2': nn.LayerNorm(self.hidden_dim),
            'ff': nn.Sequential(
                nn.Linear(self.hidden_dim, self.hidden_dim * 2, bias=False),
                nn.GELU(),
                nn.Linear(self.hidden_dim * 2, self.hidden_dim, bias=False),
            ),
        })
        layer.torsion_gate = nn.Parameter(torch.randn(self.hidden_dim) * 0.01)
        return layer
    
    def to_disk(self):
        """将层保存到磁盘"""
        if self._layer is not None and self._in_memory:
            torch.save(self._layer.state_dict(), self.cache_file)
            self._in_memory = False
            self._layer = None
            gc.collect()
    
    def to_memory(self):
        """从磁盘加载到内存"""
        if not self._in_memory:
            self._layer = self._create_layer()
            if os.path.exists(self.cache_file):
                self._layer.load_state_dict(torch.load(self.cache_file, map_location='cpu'))
            self._in_memory = True
            self._access_count += 1
            self._last_access = datetime.now().timestamp()
    
    def get(self) -> nn.Module:
        """获取层（自动加载）"""
        if not self._in_memory:
            self.to_memory()
        return self._layer
    
    def forward(self, h, torsion_field):
        """前向传播"""
        layer = self.get()
        
        # 注意力
        residual = h
        h = layer['norm1'](h)
        
        torsion_signal = torch.sigmoid(layer.torsion_gate + torsion_field)
        attn_out = layer['attn'](h)
        attn_out = attn_out * torsion_signal
        h = residual + attn_out * 0.3
        
        # 前馈
        residual = h
        h = layer['norm2'](h)
        h = residual + layer['ff'](h) * 0.3
        
        return h
    
    @property
    def in_memory(self) -> bool:
        return self._in_memory
    
    @property
    def memory_size(self) -> int:
        """估算内存占用（字节）"""
        if self._in_memory and self._layer is not None:
            return sum(p.numel() * p.element_size() for p in self._layer.parameters())
        return 0
    
    @property
    def disk_size(self) -> int:
        """磁盘占用（字节）"""
        if os.path.exists(self.cache_file):
            return os.path.getsize(self.cache_file)
        return 0


class LazyGrowingTNN(nn.Module):
    """按需加载的持续生长TNN"""
    
    def __init__(self,
                 initial_layers=2,
                 hidden_dim=128,
                 vocab_size=100,
                 max_seq_len=64,
                 max_memory_layers=4,  # 内存中最多同时保持4层
                 offload_dir='./lazy_offload'):
        super().__init__()
        
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size
        self.max_seq_len = max_seq_len
        self.max_memory_layers = max_memory_layers
        
        # 磁盘缓存目录
        self.offload_dir = offload_dir
        os.makedirs(offload_dir, exist_ok=True)
        
        # 基础组件（始终内存驻留）
        self.embedding = nn.Embedding(vocab_size, hidden_dim)
        self.pos_encoding = nn.Parameter(torch.randn(max_seq_len, hidden_dim) * 0.02)
        self.output_norm = nn.LayerNorm(hidden_dim)
        self.lm_head = nn.Linear(hidden_dim, vocab_size, bias=False)
        
        # 扭转场
        self.torsion_field = nn.Parameter(torch.zeros(hidden_dim))
        
        # 懒加载层列表
        self.lazy_layers: List[LazyLayer] = []
        self.current_stage = 0
        
        # 初始化层
        for i in range(initial_layers):
            lazy_layer = LazyLayer(i, hidden_dim, offload_dir)
            # 创建并保存到磁盘
            layer = lazy_layer._create_layer()
            torch.save(layer.state_dict(), lazy_layer.cache_file)
            self.lazy_layers.append(lazy_layer)
        
        # 预加载前max_memory_layers层到内存
        for i in range(min(max_memory_layers, len(self.lazy_layers))):
            self.lazy_layers[i].to_memory()
        
        # 统计
        self._access_stats = {'disk_reads': 0, 'memory_hits': 0}
        self.growth_history = []
    
    @property
    def current_layers(self) -> int:
        return len(self.lazy_layers)
    
    def get_total_params(self) -> int:
        """估算总参数（包括磁盘上的）"""
        if not self.lazy_layers:
            return 0
        # 临时加载一层来统计参数
        self.lazy_layers[0].to_memory()
        per_layer = sum(p.numel() for p in self.lazy_layers[0].get().parameters())
        base_params = sum(sum(p.numel() for p in module.parameters()) 
                         for module in [self.embedding, self.lm_head, self.output_norm])
        return base_params + per_layer * len(self.lazy_layers)
    
    def _manage_memory(self, active_layer_ids: List[int]):
        """管理内存 - 只保持活跃层在内存"""
        # 当前在内存中的层
        in_memory = [(i, layer) for i, layer in enumerate(self.lazy_layers) if layer.in_memory]
        
        # 需要加载的层
        to_load = set(active_layer_ids) - set(i for i, _ in in_memory)
        # 可以卸载的层
        to_offload = set(i for i, _ in in_memory) - set(active_layer_ids)
        
        # 优先卸载最久未访问的
        if len(in_memory) + len(to_load) > self.max_memory_layers:
            # 按最后访问时间排序
            in_memory_sorted = sorted(in_memory, key=lambda x: x[1]._last_access)
            need_to_free = len(in_memory) + len(to_load) - self.max_memory_layers
            for i, layer in in_memory_sorted[:need_to_free]:
                if i not in active_layer_ids:
                    layer.to_disk()
                    to_offload.discard(i)
        
        # 加载需要的层
        for i in to_load:
            self.lazy_layers[i].to_memory()
            self._access_stats['disk_reads'] += 1
    
    def forward(self, input_ids, layer_range: Optional[tuple] = None):
        """
        前向传播
        layer_range: (start_layer, end_layer) - 只使用部分层（用于逐层训练）
        """
        batch_size, seq_len = input_ids.shape
        
        # 嵌入（始终内存）
        h = self.embedding(input_ids)
        h = h + self.pos_encoding[:seq_len].unsqueeze(0)
        
        # 确定使用的层范围
        start = layer_range[0] if layer_range else 0
        end = layer_range[1] if layer_range else len(self.lazy_layers)
        active_layers = list(range(start, end))
        
        # 管理内存
        self._manage_memory(active_layers)
        
        # 逐层处理
        for i in active_layers:
            h = self.lazy_layers[i].forward(h, self.torsion_field)
            self._access_stats['memory_hits'] += 1
        
        # 输出（始终内存）
        h = self.output_norm(h)
        logits = self.lm_head(h)
        
        return logits
    
    def sequential_forward(self, input_ids):
        """顺序前向 - 一次只加载一层，极致省内存"""
        batch_size, seq_len = input_ids.shape
        
        h = self.embedding(input_ids)
        h = h + self.pos_encoding[:seq_len].unsqueeze(0)
        
        # 逐层处理，每次只保留当前层在内存
        for i, lazy_layer in enumerate(self.lazy_layers):
            # 加载当前层
            lazy_layer.to_memory()
            
            # 前向
            h = lazy_layer.forward(h, self.torsion_field)
            
            # 如果不是最后几层，卸载到磁盘
            if i < len(self.lazy_layers) - self.max_memory_layers:
                lazy_layer.to_disk()
        
        # 确保最后几层在内存
        self._manage_memory(list(range(len(self.lazy_layers) - self.max_memory_layers, len(self.lazy_layers))))
        
        h = self.output_norm(h)
        logits = self.lm_head(h)
        
        return logits
    
    def grow(self, num_new_layers=1):
        """生长 - 新层直接创建在磁盘"""
        print(f"\n🌱 生长: {self.current_layers}层 → {self.current_layers + num_new_layers}层")
        
        start_id = len(self.lazy_layers)
        
        for i in range(num_new_layers):
            layer_id = start_id + i
            lazy_layer = LazyLayer(layer_id, self.hidden_dim, self.offload_dir)
            
            # 创建层
            layer = lazy_layer._create_layer()
            
            # 小权重初始化
            with torch.no_grad():
                layer['attn'].weight *= 0.01
                for module in layer['ff']:
                    if isinstance(module, nn.Linear):
                        module.weight *= 0.01
                layer.torsion_gate *= 0.01
            
            # 直接保存到磁盘，不加载到内存
            torch.save(layer.state_dict(), lazy_layer.cache_file)
            
            self.lazy_layers.append(lazy_layer)
        
        # 如果内存还有空间，预加载一些新层
        current_in_memory = sum(1 for l in self.lazy_layers if l.in_memory)
        can_load = self.max_memory_layers - current_in_memory
        
        for i in range(max(0, len(self.lazy_layers) - can_load), len(self.lazy_layers)):
            if can_load > 0:
                self.lazy_layers[i].to_memory()
                can_load -= 1
        
        self.growth_history.append({
            'timestamp': datetime.now().isoformat(),
            'new_total_layers': len(self.lazy_layers),
        })
        
        print(f"   新层数: {len(self.lazy_layers)}")
        print(f"   预估总参数: {self.get_total_params() / 1e6:.2f}M")
        self.print_memory_status()
        
        return self
    
    def print_memory_status(self):
        """打印内存状态"""
        in_memory = sum(1 for l in self.lazy_layers if l.in_memory)
        memory_size = sum(l.memory_size for l in self.lazy_layers) / (1024**2)
        disk_size = sum(l.disk_size for l in self.lazy_layers) / (1024**2)
        
        print(f"   内存层数: {in_memory}/{len(self.lazy_layers)} (最大{self.max_memory_layers})")
        print(f"   内存占用: {memory_size:.2f}MB")
        print(f"   磁盘占用: {disk_size:.2f}MB")
        print(f"   磁盘读取: {self._access_stats['disk_reads']}次")
    
    def save_checkpoint(self, tag):
        """保存检查点 - 确保所有层都在磁盘"""
        # 先把所有层刷到磁盘
        for layer in self.lazy_layers:
            layer.to_disk()
        
        checkpoint_file = os.path.join(self.offload_dir, f'checkpoint_{tag}.pt')
        
        # 保存元数据和基础组件
        checkpoint = {
            'num_layers': len(self.lazy_layers),
            'hidden_dim': self.hidden_dim,
            'vocab_size': self.vocab_size,
            'base_state': {
                'embedding': self.embedding.state_dict(),
                'pos_encoding': self.pos_encoding,
                'output_norm': self.output_norm.state_dict(),
                'lm_head': self.lm_head.state_dict(),
                'torsion_field': self.torsion_field,
            },
            'current_stage': self.current_stage,
            'growth_history': self.growth_history,
        }
        
        torch.save(checkpoint, checkpoint_file)
        print(f"💾 检查点: {checkpoint_file}")
        return checkpoint_file
    
    @classmethod
    def load_checkpoint(cls, checkpoint_file, max_memory_layers=4):
        """加载检查点"""
        checkpoint = torch.load(checkpoint_file, map_location='cpu')
        
        # 创建模型
        model = cls(
            initial_layers=0,  # 稍后手动创建层
            hidden_dim=checkpoint['hidden_dim'],
            vocab_size=checkpoint['vocab_size'],
            max_memory_layers=max_memory_layers,
            offload_dir=os.path.dirname(checkpoint_file),
        )
        
        # 加载基础组件
        model.embedding.load_state_dict(checkpoint['base_state']['embedding'])
        model.pos_encoding = checkpoint['base_state']['pos_encoding']
        model.output_norm.load_state_dict(checkpoint['base_state']['output_norm'])
        model.lm_head.load_state_dict(checkpoint['base_state']['lm_head'])
        model.torsion_field = checkpoint['base_state']['torsion_field']
        
        # 重建懒加载层
        offload_dir = os.path.dirname(checkpoint_file)
        for i in range(checkpoint['num_layers']):
            lazy_layer = LazyLayer(i, checkpoint['hidden_dim'], offload_dir)
            lazy_layer.cache_file = os.path.join(offload_dir, f'layer_{i}.pt')
            model.lazy_layers.append(lazy_layer)
        
        # 预加载部分层
        for i in range(min(max_memory_layers, len(model.lazy_layers))):
            model.lazy_layers[i].to_memory()
        
        model.current_stage = checkpoint.get('current_stage', 0)
        model.growth_history = checkpoint.get('growth_history', [])
        
        print(f"📂 加载完成: {len(model.lazy_layers)}层")
        return model


def demo_lazy_growth():
    """演示按需加载生长"""
    print("="*70)
    print("🧠 按需激活TNN演示")
    print("   策略: 只有活跃层在内存，其他层在磁盘")
    print("="*70)
    
    # 创建模型，内存只保持2层
    model = LazyGrowingTNN(
        initial_layers=2,
        hidden_dim=128,
        vocab_size=100,
        max_memory_layers=2,  # 只保持2层在内存
        offload_dir='./lazy_demo_offload',
    )
    
    print(f"\n初始状态:")
    model.print_memory_status()
    
    # 测试生长到10层
    print("\n" + "-"*70)
    print("测试: 生长到10层（内存只保持2层）")
    print("-"*70)
    
    for i in range(8):
        model.grow(num_new_layers=1)
        
        # 测试前向（应该只加载需要的层）
        test_input = torch.randint(0, 100, (2, 32))
        output = model.sequential_forward(test_input)
        
        print(f"   输出形状: {output.shape}")
        model.print_memory_status()
        print()
    
    print("="*70)
    print("演示完成!")
    print(f"总层数: {model.current_layers}")
    print(f"理论总参数: {model.get_total_params() / 1e6:.2f}M")
    model.print_memory_status()
    
    # 保存检查点
    model.save_checkpoint('demo_complete')
    
    return model


if __name__ == "__main__":
    demo_lazy_growth()
