"""
统一自适应TNN - 三层嵌套控制架构
层生长(宏观) + 块选择(中观) + 邻域反馈(微观)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import os
import math
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import gc


# ============================================================================
# Level 3: 微观 - 邻域反馈块
# ============================================================================

class NeuroBlock(nn.Module):
    """神经块 - 带邻域关系的可学习单元"""
    
    def __init__(self, block_id: int, hidden_dim: int, grid_pos: Tuple[int, int]):
        super().__init__()
        self.block_id = block_id
        self.hidden_dim = hidden_dim
        self.grid_pos = grid_pos
        
        # 核心变换
        self.transform = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2, bias=False),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, hidden_dim, bias=False),
        )
        
        # 扭转门控
        self.torsion_gate = nn.Parameter(torch.randn(hidden_dim) * 0.01)
        
        # 邻居连接权重
        self.neighbor_weights = nn.Parameter(torch.ones(4) * 0.5)
        
        # 功能特化类型（训练后确定）
        self.specialization = None
        
        # 统计
        self.activation_count = 0
        self.success_history = []
        self.excitement = 0.0
    
    def forward(self, h: torch.Tensor, torsion_field: torch.Tensor) -> torch.Tensor:
        torsion_signal = torch.sigmoid(self.torsion_gate + torsion_field)
        return self.transform(h) * torsion_signal
    
    def record_result(self, success: bool):
        self.activation_count += 1
        self.success_history.append(1.0 if success else 0.0)
        if len(self.success_history) > 50:
            self.success_history.pop(0)
    
    @property
    def success_rate(self) -> float:
        if not self.success_history:
            return 0.5
        return sum(self.success_history) / len(self.success_history)
    
    def distance_to(self, other_pos: Tuple[int, int]) -> float:
        dx = self.grid_pos[0] - other_pos[0]
        dy = self.grid_pos[1] - other_pos[1]
        return math.sqrt(dx*dx + dy*dy)


# ============================================================================
# Level 2: 中观 - 自适应层（含块选择）
# ============================================================================

class AdaptiveLayer(nn.Module):
    """自适应层 - 动态块管理 + 邻域反馈"""
    
    def __init__(self, layer_id: int, hidden_dim: int, 
                 grid_size: Tuple[int, int] = (2, 2),
                 min_blocks: int = 1, max_blocks: int = 4):
        super().__init__()
        self.layer_id = layer_id
        self.hidden_dim = hidden_dim
        self.grid_size = grid_size
        self.num_blocks = grid_size[0] * grid_size[1]
        self.min_blocks = min_blocks
        self.max_blocks = max_blocks
        
        # 基础组件
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)
        self.base_connection = nn.Linear(hidden_dim, hidden_dim, bias=False)
        
        # 神经块网格
        self.blocks = nn.ModuleList()
        for i in range(grid_size[0]):
            for j in range(grid_size[1]):
                block_id = i * grid_size[1] + j
                self.blocks.append(NeuroBlock(block_id, hidden_dim, (i, j)))
        
        # 块选择器
        self.block_selector = nn.Linear(hidden_dim, self.num_blocks)
        
        # 信号传播网络
        self.signal_propagator = nn.Sequential(
            nn.Linear(self.num_blocks, self.num_blocks),
            nn.Sigmoid(),
        )
        
        # 当前加载状态
        self.loaded_blocks: Set[int] = set(range(self.num_blocks))  # 默认全加载
        self.load_threshold = 0.3
        
        # 统计
        self.layer_stats = {
            'activations': 0,
            'block_loads': 0,
            'block_unloads': 0,
        }
    
    def propagate_signals(self) -> torch.Tensor:
        """传播成功信号，计算各块兴奋度"""
        success_vector = torch.tensor([
            self.blocks[i].success_rate for i in range(self.num_blocks)
        ])
        
        # 神经网络传播
        excitement = self.signal_propagator(success_vector)
        
        # 显式邻域影响
        for i, block_i in enumerate(self.blocks):
            neighbor_influence = 0.0
            for j, block_j in enumerate(self.blocks):
                if i != j:
                    dist = block_i.distance_to(block_j.grid_pos)
                    influence = block_j.success_rate / (1.0 + dist)
                    neighbor_influence += influence
            
            excitement[i] = 0.6 * excitement[i] + 0.4 * torch.sigmoid(torch.tensor(neighbor_influence))
            self.blocks[i].excitement = excitement[i].item()
        
        return excitement
    
    def select_blocks(self, excitement: torch.Tensor, 
                      force_min: bool = True) -> Set[int]:
        """根据兴奋度选择加载哪些块"""
        excitement_np = excitement.detach().cpu().numpy()
        
        # 按兴奋度排序
        ranked = sorted(range(self.num_blocks), 
                       key=lambda i: excitement_np[i], reverse=True)
        
        selected = set()
        for i in ranked:
            if excitement_np[i] > self.load_threshold:
                selected.add(i)
            elif len(selected) < self.min_blocks and force_min:
                selected.add(i)
        
        # 限制最大数量
        while len(selected) > self.max_blocks:
            min_block = min(selected, key=lambda i: excitement_np[i])
            selected.remove(min_block)
        
        return selected
    
    def forward(self, h: torch.Tensor, torsion_field: torch.Tensor,
                update_blocks: bool = True) -> Tuple[torch.Tensor, Dict]:
        """前向传播"""
        batch_size, seq_len, hidden = h.shape
        
        # 传播信号，更新兴奋度
        excitement = self.propagate_signals()
        
        # 动态选择块（每10次激活更新一次，避免频繁切换）
        if update_blocks and self.layer_stats['activations'] % 10 == 0:
            new_selection = self.select_blocks(excitement)
            
            loaded_now = new_selection - self.loaded_blocks
            unloaded_now = self.loaded_blocks - new_selection
            
            self.loaded_blocks = new_selection
            self.layer_stats['block_loads'] += len(loaded_now)
            self.layer_stats['block_unloads'] += len(unloaded_now)
        
        # 归一化
        h_norm = self.norm1(h)
        
        # 基础连接
        base_out = self.base_connection(h_norm)
        
        # 收集加载块的输出
        block_outputs = []
        total_weight = 0.0
        
        for bid in self.loaded_blocks:
            block = self.blocks[bid]
            weight = excitement[bid].item()
            block_out = block(h_norm, torsion_field) * weight
            block_outputs.append(block_out)
            total_weight += weight
            block.activation_count += 1
        
        # 合并
        if block_outputs and total_weight > 0:
            combined = sum(block_outputs) / total_weight
        else:
            combined = torch.zeros_like(h_norm)
        
        h = h + (base_out + combined) * 0.3
        h = self.norm2(h)
        
        self.layer_stats['activations'] += 1
        
        # 统计
        stats = {
            'loaded_blocks': sorted(list(self.loaded_blocks)),
            'block_count': len(self.loaded_blocks),
            'avg_excitement': excitement.mean().item(),
            'success_rates': [self.blocks[i].success_rate for i in range(self.num_blocks)],
        }
        
        return h, stats
    
    def record_success(self, success: bool):
        """记录成功/失败，更新所有加载块"""
        for bid in self.loaded_blocks:
            self.blocks[bid].record_result(success)


# ============================================================================
# Level 1: 宏观 - 统一自适应TNN（层生长）
# ============================================================================

class UnifiedAdaptiveTNN(nn.Module):
    """
    统一自适应TNN
    三层控制：层生长 -> 块选择 -> 邻域反馈
    """
    
    def __init__(self,
                 initial_layers: int = 2,
                 hidden_dim: int = 128,
                 vocab_size: int = 100,
                 max_seq_len: int = 64,
                 blocks_per_layer: int = 4,
                 checkpoint_dir: str = './unified_adaptive'):
        super().__init__()
        
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size
        self.max_seq_len = max_seq_len
        self.blocks_per_layer = blocks_per_layer
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # 基础组件
        self.embedding = nn.Embedding(vocab_size, hidden_dim)
        self.pos_encoding = nn.Parameter(torch.randn(max_seq_len, hidden_dim) * 0.02)
        
        # 自适应层列表（动态可生长）
        self.layers: List[AdaptiveLayer] = nn.ModuleList()
        for i in range(initial_layers):
            self.layers.append(AdaptiveLayer(i, hidden_dim, (2, 2), blocks_per_layer))
        
        # 输出
        self.output_norm = nn.LayerNorm(hidden_dim)
        self.lm_head = nn.Linear(hidden_dim, vocab_size, bias=False)
        
        # 全局扭转场
        self.torsion_field = nn.Parameter(torch.zeros(hidden_dim))
        
        # 生长控制
        self.growth_threshold_accuracy = 0.85
        self.growth_threshold_loss = 0.1
        self.min_cycles_before_growth = 20
        self.cycle_count = 0
        
        # 阶段定义
        self.stages = {
            0: ("Embryo", 2),
            1: ("Infant", 4),
            2: ("Child", 6),
            3: ("Adolescent", 8),
            4: ("Adult", 10),
        }
        self.current_stage = 0
        
        # 历史
        self.growth_history = []
        self.training_history = []
    
    @property
    def num_layers(self) -> int:
        return len(self.layers)
    
    def get_total_params(self) -> int:
        """估计总参数量"""
        # 基础组件
        base = 0
        for module in [self.embedding, self.lm_head]:
            for p in module.parameters():
                base += p.numel()
        
        # 层参数（估算）
        if len(self.layers) > 0:
            layer_params = 0
            for p in self.layers[0].parameters():
                layer_params += p.numel()
            return base + layer_params * len(self.layers)
        return base
    
    def forward(self, input_ids: torch.Tensor, 
                return_stats: bool = False) -> torch.Tensor:
        """前向传播"""
        batch_size, seq_len = input_ids.shape
        
        h = self.embedding(input_ids)
        h = h + self.pos_encoding[:seq_len].unsqueeze(0)
        
        # 逐层处理
        all_stats = []
        for layer in self.layers:
            h, stats = layer(h, self.torsion_field)
            all_stats.append(stats)
        
        h = self.output_norm(h)
        logits = self.lm_head(h)
        
        if return_stats:
            return logits, all_stats
        return logits
    
    def check_growth_condition(self, accuracy: float, loss: float) -> bool:
        """检查是否应该生长新层"""
        self.cycle_count += 1
        
        if self.cycle_count < self.min_cycles_before_growth:
            return False
        
        # 性能达标
        performance_ok = accuracy > self.growth_threshold_accuracy and loss < self.growth_threshold_loss
        
        # 达到下一阶段目标
        target_layers = self.stages.get(self.current_stage + 1, (None, 100))[1]
        
        return performance_ok and len(self.layers) < target_layers
    
    def grow(self, num_new_layers: int = 1):
        """生长新层"""
        print(f"\n🌱 层生长: {len(self.layers)}层 → {len(self.layers) + num_new_layers}层")
        
        start_id = len(self.layers)
        
        for i in range(num_new_layers):
            new_layer = AdaptiveLayer(start_id + i, self.hidden_dim, (2, 2), self.blocks_per_layer)
            
            # 小权重初始化
            with torch.no_grad():
                for p in new_layer.parameters():
                    p *= 0.01
            
            self.layers.append(new_layer)
        
        # 更新阶段
        for stage_id, (name, target_layers) in self.stages.items():
            if len(self.layers) >= target_layers:
                self.current_stage = stage_id
        
        self.growth_history.append({
            'timestamp': datetime.now().isoformat(),
            'previous_layers': start_id,
            'new_layers': len(self.layers),
            'stage': self.stages[self.current_stage][0],
        })
        
        print(f"   新层数: {len(self.layers)}")
        print(f"   新阶段: {self.stages[self.current_stage][0]}")
        print(f"   估计参数量: {self.get_total_params() / 1e6:.2f}M")
        
        return self
    
    def training_step(self, input_ids: torch.Tensor, targets: torch.Tensor,
                     optimizer: torch.optim.Optimizer) -> Dict:
        """训练一步"""
        self.train()
        
        # 前向
        logits, stats = self.forward(input_ids, return_stats=True)
        
        # 计算损失
        loss = F.cross_entropy(logits.view(-1, self.vocab_size), targets.view(-1))
        
        # 反向
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # 计算准确率
        with torch.no_grad():
            preds = logits.argmax(dim=-1)
            accuracy = (preds == targets).float().mean().item()
            perplexity = torch.exp(loss).item()
        
        # 反馈给各层
        for layer in self.layers:
            layer.record_success(accuracy > 0.7)
        
        # 检查生长
        should_grow = self.check_growth_condition(accuracy, loss.item())
        
        result = {
            'loss': loss.item(),
            'accuracy': accuracy,
            'perplexity': perplexity,
            'layers': len(self.layers),
            'stage': self.stages[self.current_stage][0],
            'should_grow': should_grow,
            'layer_stats': stats,
        }
        
        self.training_history.append(result)
        
        return result
    
    def print_unified_status(self):
        """打印统一状态"""
        print("\n" + "="*70)
        print("🧠 统一自适应TNN状态")
        print("="*70)
        
        print(f"\n📊 宏观（层）:")
        print(f"   当前层数: {len(self.layers)}")
        print(f"   当前阶段: {self.stages[self.current_stage][0]}")
        print(f"   生长次数: {len(self.growth_history)}")
        print(f"   估计参数: {self.get_total_params() / 1e6:.2f}M")
        
        print(f"\n🔍 中观（层内块）:")
        for layer in self.layers:
            print(f"   层{layer.layer_id}: 加载{len(layer.loaded_blocks)}/{layer.num_blocks}块 "
                  f"激活{layer.layer_stats['activations']}次")
        
        print(f"\n🔗 微观（块状态）:")
        for layer in self.layers[:2]:  # 只显示前两层
            print(f"\n   层{layer.layer_id}:")
            for block in layer.blocks:
                status = "🟢" if block.block_id in layer.loaded_blocks else "⚪"
                print(f"     块{block.block_id} {status} "
                      f"成功率{block.success_rate:.1%} "
                      f"兴奋度{block.excitement:.2f} "
                      f"激活{block.activation_count}次")


def demo_unified_adaptive():
    """演示统一自适应TNN"""
    print("="*70)
    print("🧠 统一自适应TNN - 三层嵌套控制")
    print("="*70)
    print("架构: 层生长(宏观) + 块选择(中观) + 邻域反馈(微观)")
    print("="*70)
    
    # 创建模型（2层胚胎期）
    model = UnifiedAdaptiveTNN(
        initial_layers=2,
        hidden_dim=64,
        vocab_size=30,
        blocks_per_layer=4,
    )
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    print(f"\n初始状态:")
    print(f"  层数: {model.num_layers}")
    print(f"  每层层数: 4块 (2x2网格)")
    print(f"  阶段: {model.stages[model.current_stage][0]}")
    
    # 生成训练数据
    def generate_batch(task_type: str, batch_size: int = 4):
        if task_type == "simple":
            seq = torch.arange(20) % 30
        elif task_type == "pattern":
            seq = torch.tensor([i * 2 % 30 for i in range(20)])
        else:  # complex
            seq = torch.tensor([(i ** 2) % 30 for i in range(20)])
        
        data = seq.unsqueeze(0).repeat(batch_size, 1)
        target = torch.roll(data, shifts=-1, dims=1)
        return data, target
    
    tasks = ["simple", "pattern", "complex"]
    
    print("\n" + "-"*70)
    print("开始训练（动态生长演示）")
    print("-"*70)
    
    for epoch in range(50):
        epoch_loss = 0
        epoch_acc = 0
        
        for task in tasks:
            input_ids, targets = generate_batch(task)
            result = model.training_step(input_ids, targets, optimizer)
            
            epoch_loss += result['loss']
            epoch_acc += result['accuracy']
        
        avg_loss = epoch_loss / len(tasks)
        avg_acc = epoch_acc / len(tasks)
        
        # 每10轮显示状态
        if (epoch + 1) % 10 == 0:
            print(f"\n📚 Epoch {epoch + 1}")
            print(f"   损失: {avg_loss:.4f} | 准确率: {avg_acc:.1%}")
            print(f"   层数: {result['layers']} | 阶段: {result['stage']}")
            
            # 显示块加载情况
            for li, ls in enumerate(result['layer_stats']):
                print(f"   层{li}: 加载{ls['block_count']}块 "
                      f"(块{ls['loaded_blocks']}) "
                      f"兴奋度{ls['avg_excitement']:.2f}")
        
        # 检查生长
        if result['should_grow'] and len(model.layers) < 6:
            model.grow(num_new_layers=1)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # 最终状态
    model.print_unified_status()
    
    print("\n" + "="*70)
    print("演示完成!")
    print("="*70)
    
    return model


if __name__ == "__main__":
    demo_unified_adaptive()
