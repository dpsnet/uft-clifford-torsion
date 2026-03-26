"""
邻域反馈控制TNN - 成功率驱动的块加载网络
块之间存在拓扑连接，成功信号在邻域内传播，动态影响加载决策
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Set
from collections import defaultdict
import math


class NeighboringBlock(nn.Module):
    """带邻域关系的智能块"""
    
    def __init__(self, block_id: int, hidden_dim: int, grid_pos: Tuple[int, int] = None):
        super().__init__()
        self.block_id = block_id
        self.hidden_dim = hidden_dim
        self.grid_pos = grid_pos or (block_id // 2, block_id % 2)  # 2x2网格位置
        
        # 核心变换
        self.transform = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2, bias=False),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, hidden_dim, bias=False),
        )
        
        # 扭转门控
        self.torsion_gate = nn.Parameter(torch.randn(hidden_dim) * 0.01)
        
        # 邻居连接权重（可学习）
        self.neighbor_weights = nn.Parameter(torch.ones(4) * 0.5)  # 上/下/左/右
        
        # 状态跟踪
        self.activation_history = []  # 最近激活记录
        self.success_history = []  # 最近成功记录
        self.excitement = 0.0  # 兴奋度（来自邻居的成功信号）
        self.inhibition = 0.0  # 抑制度（来自失败的信号）
        
    def forward(self, h: torch.Tensor, torsion_field: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        torsion_signal = torch.sigmoid(self.torsion_gate + torsion_field)
        out = self.transform(h) * torsion_signal
        return out
    
    def get_success_rate(self, window: int = 10) -> float:
        """计算最近成功率"""
        if not self.success_history:
            return 0.5  # 默认值
        recent = self.success_history[-window:]
        return sum(recent) / len(recent)
    
    def record_activation(self, success: bool):
        """记录激活结果"""
        self.activation_history.append(1)
        self.success_history.append(1.0 if success else 0.0)
        
        # 保持历史长度
        if len(self.activation_history) > 100:
            self.activation_history.pop(0)
            self.success_history.pop(0)
    
    def distance_to(self, other_pos: Tuple[int, int]) -> float:
        """计算到另一个块的距离"""
        dx = self.grid_pos[0] - other_pos[0]
        dy = self.grid_pos[1] - other_pos[1]
        return math.sqrt(dx * dx + dy * dy)
    
    def get_influence_on(self, other_pos: Tuple[int, int], success_rate: float) -> float:
        """
        计算本块对目标块的影响力
        距离越近影响越大，成功率越高影响越大
        """
        dist = self.distance_to(other_pos)
        if dist == 0:
            return 0  # 不影响自己
        
        # 距离衰减 + 成功率加权
        distance_factor = 1.0 / (1.0 + dist)
        success_factor = success_rate
        
        return distance_factor * success_factor * F.sigmoid(self.neighbor_weights[0]).item()


class NeighborhoodFeedbackLayer(nn.Module):
    """邻域反馈层 - 块之间有信号传播的层"""
    
    def __init__(self, layer_id: int, hidden_dim: int, grid_size: Tuple[int, int] = (2, 2)):
        super().__init__()
        self.layer_id = layer_id
        self.hidden_dim = hidden_dim
        self.grid_size = grid_size
        self.num_blocks = grid_size[0] * grid_size[1]
        
        # 归一化
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)
        
        # 基础连接
        self.base_connection = nn.Linear(hidden_dim, hidden_dim, bias=False)
        
        # 创建块网格
        self.blocks = nn.ModuleList()
        for i in range(grid_size[0]):
            for j in range(grid_size[1]):
                block_id = i * grid_size[1] + j
                self.blocks.append(NeighboringBlock(block_id, hidden_dim, (i, j)))
        
        # 块功能特化
        self.block_roles = {
            0: ("pattern_matcher", "识别简单模式"),
            1: ("memory_keeper", "保持历史信息"),
            2: ("abstract_reasoner", "抽象推理"),
            3: ("context_integrator", "整合上下文"),
        }
        
        # 全局信号传播网络
        self.signal_propagator = nn.Sequential(
            nn.Linear(self.num_blocks, self.num_blocks),
            nn.Sigmoid(),
        )
        
        # 加载控制参数
        self.load_threshold = 0.3  # 兴奋度超过此值时加载
        self.unload_threshold = 0.1  # 兴奋度低于此值时卸载
        self.min_loaded = 1  # 最少保持加载的块数
        self.max_loaded = self.num_blocks  # 最多加载的块数
        
        # 当前加载状态
        self.loaded_blocks: Set[int] = set()
        self.block_excitement: Dict[int, float] = {i: 0.0 for i in range(self.num_blocks)}
        
        # 统计
        self.feedback_stats = {
            'activations': 0,
            'load_decisions': 0,
            'unload_decisions': 0,
        }
    
    def propagate_success_signals(self, success_vector: torch.Tensor) -> torch.Tensor:
        """
        传播成功信号
        success_vector: [num_blocks] - 每个块的成功率
        返回: [num_blocks] - 传播后的兴奋度
        """
        # 通过神经网络传播信号
        excitement = self.signal_propagator(success_vector)
        
        # 手动计算邻域影响（更精细的控制）
        for i, block_i in enumerate(self.blocks):
            total_influence = 0.0
            for j, block_j in enumerate(self.blocks):
                if i != j:
                    influence = block_j.get_influence_on(
                        block_i.grid_pos, 
                        success_vector[j].item()
                    )
                    total_influence += influence
            
            # 结合神经网络输出和显式邻域计算
            excitement[i] = 0.5 * excitement[i] + 0.5 * torch.sigmoid(torch.tensor(total_influence))
        
        return excitement
    
    def decide_load_pattern(self, excitement: torch.Tensor, task_requirement: str = "auto") -> Set[int]:
        """
        根据兴奋度决定加载哪些块
        task_requirement: "auto", "minimal", "full", "adaptive"
        """
        excitement_np = excitement.detach().cpu().numpy()
        
        # 按兴奋度排序
        ranked_blocks = sorted(
            range(self.num_blocks),
            key=lambda i: excitement_np[i],
            reverse=True
        )
        
        to_load = set()
        
        if task_requirement == "minimal":
            # 只加载最兴奋的块
            to_load.add(ranked_blocks[0])
            
        elif task_requirement == "full":
            # 加载全部
            to_load = set(range(self.num_blocks))
            
        elif task_requirement == "adaptive":
            # 基于兴奋度阈值自适应选择
            for i in ranked_blocks:
                if excitement_np[i] > self.load_threshold:
                    to_load.add(i)
                elif len(to_load) < self.min_loaded:
                    to_load.add(i)
            
            # 如果兴奋度高的块很少，加载其邻居
            if len(to_load) < self.min_loaded:
                for loaded_id in list(to_load):
                    for neighbor_id in self.get_neighbors(loaded_id):
                        if neighbor_id not in to_load:
                            to_load.add(neighbor_id)
                            if len(to_load) >= self.min_loaded:
                                break
        
        else:  # "auto" - 智能选择
            # 加载所有兴奋度高于阈值的块
            for i in ranked_blocks:
                if excitement_np[i] > self.load_threshold:
                    to_load.add(i)
                elif len(to_load) < self.min_loaded:
                    to_load.add(i)
            
            # 限制最大数量
            while len(to_load) > self.max_loaded:
                # 移除兴奋度最低的
                min_excited = min(to_load, key=lambda i: excitement_np[i])
                to_load.remove(min_excited)
        
        return to_load
    
    def get_neighbors(self, block_id: int) -> List[int]:
        """获取块的邻居"""
        block = self.blocks[block_id]
        neighbors = []
        
        for other in self.blocks:
            if other.block_id != block_id:
                dist = block.distance_to(other.grid_pos)
                if dist <= 1.5:  # 相邻（包括对角）
                    neighbors.append(other.block_id)
        
        return neighbors
    
    def forward(self, h: torch.Tensor, torsion_field: torch.Tensor, 
                task_type: str = "auto", target_accuracy: float = None) -> Tuple[torch.Tensor, Dict]:
        """
        前向传播，带邻域反馈控制
        """
        batch_size, seq_len, hidden = h.shape
        
        # 收集当前成功率
        success_vector = torch.tensor([
            self.blocks[i].get_success_rate() for i in range(self.num_blocks)
        ], dtype=torch.float32)
        
        # 传播成功信号，计算兴奋度
        excitement = self.propagate_success_signals(success_vector)
        
        # 根据兴奋度决定加载模式
        new_load_pattern = self.decide_load_pattern(excitement, task_type)
        
        # 执行加载/卸载
        loaded_now = set()
        for bid in new_load_pattern:
            if bid not in self.loaded_blocks:
                loaded_now.add(bid)
        
        unloaded_now = set()
        for bid in self.loaded_blocks:
            if bid not in new_load_pattern:
                unloaded_now.add(bid)
        
        self.loaded_blocks = new_load_pattern
        
        # 前向传播
        h_norm = self.norm1(h)
        
        # 基础连接（始终使用）
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
            
            # 记录激活
            if target_accuracy is not None:
                block.record_activation(target_accuracy > 0.6)
        
        # 合并
        if block_outputs and total_weight > 0:
            combined = sum(block_outputs) / total_weight
        else:
            combined = torch.zeros_like(h_norm)
        
        h = h + (base_out + combined) * 0.3
        h = self.norm2(h)
        
        # 统计
        stats = {
            'loaded_blocks': sorted(list(self.loaded_blocks)),
            'loaded_now': sorted(list(loaded_now)),
            'unloaded_now': sorted(list(unloaded_now)),
            'excitement': {i: f"{excitement[i]:.3f}" for i in range(self.num_blocks)},
            'success_rates': {i: f"{self.blocks[i].get_success_rate():.3f}" for i in range(self.num_blocks)},
        }
        
        self.feedback_stats['activations'] += 1
        if loaded_now:
            self.feedback_stats['load_decisions'] += 1
        if unloaded_now:
            self.feedback_stats['unload_decisions'] += 1
        
        return h, stats


class NeighborhoodFeedbackTNN(nn.Module):
    """完整邻域反馈TNN"""
    
    def __init__(self, 
                 num_layers: int = 3,
                 hidden_dim: int = 128,
                 vocab_size: int = 100,
                 blocks_per_layer: int = 4):
        super().__init__()
        
        self.num_layers = num_layers
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size
        
        # 基础组件
        self.embedding = nn.Embedding(vocab_size, hidden_dim)
        self.pos_encoding = nn.Parameter(torch.randn(64, hidden_dim) * 0.02)
        
        # 邻域反馈层
        grid_size = (2, 2) if blocks_per_layer == 4 else (int(blocks_per_layer**0.5),) * 2
        self.layers = nn.ModuleList([
            NeighborhoodFeedbackLayer(i, hidden_dim, grid_size)
            for i in range(num_layers)
        ])
        
        # 输出
        self.output_norm = nn.LayerNorm(hidden_dim)
        self.lm_head = nn.Linear(hidden_dim, vocab_size, bias=False)
        
        # 全局扭转场
        self.torsion_field = nn.Parameter(torch.zeros(hidden_dim))
    
    def forward(self, input_ids: torch.Tensor, 
                task_type: str = "auto",
                return_stats: bool = False) -> torch.Tensor:
        """前向传播"""
        batch_size, seq_len = input_ids.shape
        
        h = self.embedding(input_ids)
        h = h + self.pos_encoding[:seq_len].unsqueeze(0)
        
        all_stats = []
        for layer in self.layers:
            h, stats = layer(h, self.torsion_field, task_type)
            all_stats.append(stats)
        
        h = self.output_norm(h)
        logits = self.lm_head(h)
        
        if return_stats:
            return logits, all_stats
        return logits
    
    def print_feedback_status(self):
        """打印反馈状态"""
        print("\n📊 邻域反馈状态")
        print("="*70)
        
        for layer in self.layers:
            print(f"\n层 {layer.layer_id}:")
            print(f"  当前加载: {sorted(layer.loaded_blocks)}")
            print(f"  块状态:")
            
            for block in layer.blocks:
                role, desc = layer.block_roles.get(block.block_id, ("unknown", ""))
                success_rate = block.get_success_rate()
                in_mem = "🧠" if block.block_id in layer.loaded_blocks else "💾"
                print(f"    块{block.block_id} [{role:18s}] {in_mem} "
                      f"位置{block.grid_pos} 成功率{success_rate:.1%} "
                      f"激活{len(block.activation_history)}次")
            
            print(f"  反馈统计: 激活{layer.feedback_stats['activations']}次 "
                  f"加载决策{layer.feedback_stats['load_decisions']}次 "
                  f"卸载决策{layer.feedback_stats['unload_decisions']}次")


def demo_neighborhood_feedback():
    """演示邻域反馈控制"""
    print("="*70)
    print("🔗 邻域反馈控制TNN")
    print("   成功率信号在块间传播，动态影响加载决策")
    print("="*70)
    
    # 创建模型
    model = NeighborhoodFeedbackTNN(
        num_layers=2,
        hidden_dim=64,
        vocab_size=30,
        blocks_per_layer=4,
    )
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    print("\n模型结构:")
    print(f"  层数: {model.num_layers}")
    print(f"  每层块数: 4 (2x2网格)")
    print(f"  块布局:")
    print(f"    [0:pattern_matcher] [1:memory_keeper]")
    print(f"    [2:abstract_reasoner] [3:context_integrator]")
    
    # 不同难度的任务
    tasks = [
        ("simple_repeat", torch.tensor([[0,1,0,1,0,1]*4]), "minimal"),  # 简单重复
        ("complex_pattern", torch.tensor([[0,2,4,1,3]*5]), "adaptive"),  # 复杂模式
        ("abstract_math", torch.tensor([[1,4,9,16,25]*4]), "full"),  # 抽象数学
    ]
    
    print("\n" + "-"*70)
    print("训练演示（信号传播影响加载）")
    print("-"*70)
    
    for epoch in range(5):
        print(f"\n📚 Epoch {epoch + 1}")
        
        for task_name, input_ids, task_mode in tasks:
            # 生成目标
            target = torch.roll(input_ids, shifts=-1, dims=1)
            
            # 前向
            logits, stats = model(input_ids, task_type=task_mode, return_stats=True)
            
            # 计算损失和准确率
            loss = F.cross_entropy(logits.view(-1, model.vocab_size), target.view(-1))
            preds = logits.argmax(dim=-1)
            accuracy = (preds == target).float().mean().item()
            
            # 反向
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            # 用准确率反馈更新块
            for layer_stats in stats:
                for bid in layer_stats['loaded_blocks']:
                    for layer in model.layers:
                        if bid < len(layer.blocks):
                            layer.blocks[bid].record_activation(accuracy > 0.5)
            
            # 显示该任务的加载模式
            loaded_summary = []
            for li, ls in enumerate(stats):
                loaded_summary.append(f"L{li}:{ls['loaded_blocks']}")
            
            print(f"  {task_name:15s} 模式:{task_mode:10s} 准确率:{accuracy:5.1%} "
                  f"加载:{loaded_summary}")
    
    # 最终状态
    model.print_feedback_status()
    
    # 测试信号传播
    print("\n" + "-"*70)
    print("测试: 成功率信号传播效果")
    print("-"*70)
    
    # 人工设置块0成功率很高
    for layer in model.layers:
        layer.blocks[0].success_history = [1.0] * 10  # 100%成功率
        layer.blocks[1].success_history = [0.0] * 10  # 0%成功率
        layer.blocks[2].success_history = [0.5] * 10  # 50%成功率
        layer.blocks[3].success_history = [0.3] * 10  # 30%成功率
    
    # 再次前向，看加载模式变化
    test_input = torch.tensor([[0,1,2,3,4]*4])
    _, test_stats = model(test_input, task_type="auto", return_stats=True)
    
    print("\n块0成功率100%（高），块1成功率0%（低）")
    print("预期: 块0的邻居（块1,2）应该被激励加载")
    
    for li, ls in enumerate(test_stats):
        print(f"  层{li}最终加载: {ls['loaded_blocks']}")
        print(f"  兴奋度: {ls['excitement']}")
    
    print("\n" + "="*70)
    print("演示完成!")
    print("="*70)
    
    return model


if __name__ == "__main__":
    demo_neighborhood_feedback()
