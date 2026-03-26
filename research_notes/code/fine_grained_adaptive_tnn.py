"""
细粒度按需激活TNN - 块级动态加载
每层包含多个功能块，根据识别成功率决定加载哪些块
成功率低的任务方向，自动补充加载对应专家块
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


class FunctionalBlock(nn.Module):
    """功能块 - 层内的专家子模块"""
    
    def __init__(self, hidden_dim: int, block_id: int, specialization: str = "general"):
        super().__init__()
        self.block_id = block_id
        self.specialization = specialization  # 专业方向: general/pattern/memory/abstract/etc
        
        # 轻量级变换
        self.transform = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2, bias=False),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, hidden_dim, bias=False),
        )
        
        # 扭转门控（每个块独立）
        self.torsion_gate = nn.Parameter(torch.randn(hidden_dim) * 0.01)
        
        # 使用率统计
        self.usage_count = 0
        self.success_accumulator = 0.0
    
    def forward(self, h: torch.Tensor, torsion_field: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        torsion_signal = torch.sigmoid(self.torsion_gate + torsion_field)
        out = self.transform(h) * torsion_signal
        return out
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.usage_count == 0:
            return 1.0
        return self.success_accumulator / self.usage_count
    
    def update_stats(self, success: bool):
        """更新统计"""
        self.usage_count += 1
        self.success_accumulator += 1.0 if success else 0.0


class AdaptiveLayer(nn.Module):
    """自适应层 - 包含多个可按需加载的功能块"""
    
    def __init__(self, layer_id: int, hidden_dim: int, num_blocks: int = 4, 
                 offload_dir: str = './adaptive_offload'):
        super().__init__()
        self.layer_id = layer_id
        self.hidden_dim = hidden_dim
        self.num_blocks = num_blocks
        self.offload_dir = offload_dir
        
        # 归一化（始终内存）
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)
        
        # 基础连接（始终内存 - 保证基本功能）
        self.base_connection = nn.Linear(hidden_dim, hidden_dim, bias=False)
        
        # 功能块（可部分卸载到磁盘）
        self.blocks: Dict[int, FunctionalBlock] = nn.ModuleDict()
        self.block_specializations = {
            0: "pattern",      # 模式识别
            1: "memory",       # 记忆关联  
            2: "abstract",     # 抽象推理
            3: "context",      # 上下文整合
        }
        
        for i in range(num_blocks):
            spec = self.block_specializations.get(i, "general")
            self.blocks[str(i)] = FunctionalBlock(hidden_dim, i, spec)
        
        # 块选择器（学习哪个块对当前输入更重要）
        self.block_selector = nn.Linear(hidden_dim, num_blocks)
        
        # 激活状态跟踪
        self.active_blocks: set = set()  # 当前内存中的块
        self.min_active_blocks = 1  # 最少保持1个块
        self.max_active_blocks = num_blocks  # 最多全部
        
        # 性能阈值
        self.success_threshold = 0.7  # 成功率低于此值时补充加载
        
        # 磁盘缓存
        os.makedirs(offload_dir, exist_ok=True)
        self.block_cache_files = {
            i: os.path.join(offload_dir, f'layer{layer_id}_block{i}.pt')
            for i in range(num_blocks)
        }
        
        # 任务类型到块的映射
        self.task_block_mapping: Dict[str, List[int]] = defaultdict(list)
    
    def identify_task_type(self, h: torch.Tensor) -> str:
        """根据隐藏状态识别任务类型"""
        # 简单启发式：根据激活模式判断
        mean_activation = h.mean(dim=(0, 1))
        
        # 计算各维度的"活跃度"
        active_dims = (mean_activation > mean_activation.mean()).sum().item()
        total_dims = mean_activation.numel()
        activation_ratio = active_dims / total_dims
        
        if activation_ratio < 0.3:
            return "simple_pattern"  # 简单模式
        elif activation_ratio < 0.6:
            return "complex_sequence"  # 复杂序列
        else:
            return "abstract_reasoning"  # 抽象推理
    
    def select_blocks_for_task(self, task_type: str, h: torch.Tensor) -> List[int]:
        """为任务类型选择块"""
        # 基于任务类型和成功率选择
        block_scores = []
        
        for block_id in range(self.num_blocks):
            block = self.blocks[str(block_id)]
            score = 0.0
            
            # 1. 任务-块匹配度
            if task_type == "simple_pattern" and block.specialization == "pattern":
                score += 2.0
            elif task_type == "complex_sequence" and block.specialization in ["memory", "context"]:
                score += 2.0
            elif task_type == "abstract_reasoning" and block.specialization == "abstract":
                score += 2.0
            
            # 2. 历史成功率
            score += block.success_rate
            
            # 3. 选择器输出的置信度
            selector_logits = self.block_selector(h.mean(dim=1))
            selector_prob = F.softmax(selector_logits, dim=-1)[0, block_id].item()
            score += selector_prob
            
            block_scores.append((block_id, score))
        
        # 按分数排序
        block_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 选择足够的块保证成功率
        selected = []
        cumulative_confidence = 0.0
        
        for block_id, score in block_scores:
            selected.append(block_id)
            cumulative_confidence += score / (self.num_blocks * 3)  # 归一化
            
            # 如果已选块的成功率都够高，可以停止
            avg_success = sum(self.blocks[str(bid)].success_rate for bid in selected) / len(selected)
            if avg_success > self.success_threshold and len(selected) >= self.min_active_blocks:
                break
        
        return selected
    
    def to_disk(self, block_ids: List[int]):
        """将指定块卸载到磁盘"""
        for bid in block_ids:
            if bid in self.active_blocks:
                torch.save(self.blocks[str(bid)].state_dict(), self.block_cache_files[bid])
                self.active_blocks.discard(bid)
    
    def to_memory(self, block_ids: List[int]):
        """从磁盘加载指定块到内存"""
        for bid in block_ids:
            if bid not in self.active_blocks:
                if os.path.exists(self.block_cache_files[bid]):
                    self.blocks[str(bid)].load_state_dict(
                        torch.load(self.block_cache_files[bid], map_location='cpu')
                    )
                self.active_blocks.add(bid)
    
    def forward(self, h: torch.Tensor, torsion_field: torch.Tensor, 
                target_accuracy: Optional[float] = None) -> Tuple[torch.Tensor, Dict]:
        """
        前向传播，动态选择块
        返回: (输出, 统计信息)
        """
        stats = {
            'task_type': None,
            'selected_blocks': [],
            'loaded_blocks': [],
            'success_rate': 0.0,
        }
        
        batch_size, seq_len, hidden = h.shape
        
        # 识别任务类型
        task_type = self.identify_task_type(h)
        stats['task_type'] = task_type
        
        # 选择需要的块
        selected_blocks = self.select_blocks_for_task(task_type, h)
        stats['selected_blocks'] = selected_blocks
        
        # 确保选中块在内存
        need_to_load = [bid for bid in selected_blocks if bid not in self.active_blocks]
        if need_to_load:
            # 如果内存满了，先卸载一些
            if len(self.active_blocks) + len(need_to_load) > self.max_active_blocks:
                to_offload = list(self.active_blocks - set(selected_blocks))[:len(need_to_load)]
                self.to_disk(to_offload)
            
            self.to_memory(need_to_load)
            stats['loaded_blocks'] = need_to_load
        
        # 归一化
        h_norm = self.norm1(h)
        
        # 基础连接（始终使用）
        base_out = self.base_connection(h_norm)
        
        # 收集选中块的输出
        block_outputs = []
        block_weights = F.softmax(self.block_selector(h_norm.mean(dim=1)), dim=-1)
        
        for bid in selected_blocks:
            block = self.blocks[str(bid)]
            block_out = block(h_norm, torsion_field)
            weight = block_weights[:, bid:bid+1].unsqueeze(1)  # [B, 1, 1]
            block_outputs.append(block_out * weight)
            block.usage_count += 1
        
        # 合并块输出
        if block_outputs:
            combined = sum(block_outputs)
        else:
            combined = torch.zeros_like(h_norm)
        
        # 残差连接
        h = h + (base_out + combined) * 0.3
        
        # 第二次归一化
        h = self.norm2(h)
        
        # 更新成功率（如果有目标精度）
        if target_accuracy is not None:
            for bid in selected_blocks:
                self.blocks[str(bid)].update_stats(target_accuracy > self.success_threshold)
        
        # 计算平均成功率
        if selected_blocks:
            stats['success_rate'] = sum(self.blocks[str(b)].success_rate for b in selected_blocks) / len(selected_blocks)
        
        return h, stats


class FineGrainedAdaptiveTNN(nn.Module):
    """细粒度自适应TNN - 块级按需加载"""
    
    def __init__(self, 
                 num_layers: int = 4,
                 hidden_dim: int = 128,
                 vocab_size: int = 100,
                 blocks_per_layer: int = 4,
                 offload_dir: str = './fine_grained_offload'):
        super().__init__()
        
        self.num_layers = num_layers
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size
        self.blocks_per_layer = blocks_per_layer
        
        # 基础组件
        self.embedding = nn.Embedding(vocab_size, hidden_dim)
        self.pos_encoding = nn.Parameter(torch.randn(64, hidden_dim) * 0.02)
        
        # 自适应层
        self.layers = nn.ModuleList([
            AdaptiveLayer(i, hidden_dim, blocks_per_layer, offload_dir)
            for i in range(num_layers)
        ])
        
        # 输出
        self.output_norm = nn.LayerNorm(hidden_dim)
        self.lm_head = nn.Linear(hidden_dim, vocab_size, bias=False)
        
        # 全局扭转场
        self.torsion_field = nn.Parameter(torch.zeros(hidden_dim))
        
        # 统计
        self.forward_stats = []
    
    def forward(self, input_ids: torch.Tensor, 
                return_stats: bool = False) -> torch.Tensor:
        """前向传播"""
        batch_size, seq_len = input_ids.shape
        
        # 嵌入
        h = self.embedding(input_ids)
        h = h + self.pos_encoding[:seq_len].unsqueeze(0)
        
        # 逐层处理
        layer_stats = []
        for layer in self.layers:
            h, stats = layer(h, self.torsion_field)
            layer_stats.append(stats)
        
        # 输出
        h = self.output_norm(h)
        logits = self.lm_head(h)
        
        if return_stats:
            return logits, layer_stats
        return logits
    
    def print_block_status(self):
        """打印块状态"""
        print("\n📊 块级状态报告")
        print("-" * 70)
        
        for layer in self.layers:
            print(f"\n层 {layer.layer_id}:")
            for bid in range(layer.num_blocks):
                block = layer.blocks[str(bid)]
                in_mem = bid in layer.active_blocks
                status = "🧠" if in_mem else "💾"
                print(f"  块{bid} [{block.specialization:10s}] {status} "
                      f"使用{block.usage_count:4d}次 成功率{block.success_rate:.2%}")
    
    def get_memory_stats(self) -> Dict:
        """获取内存统计"""
        in_memory_blocks = 0
        total_blocks = 0
        
        for layer in self.layers:
            in_memory_blocks += len(layer.active_blocks)
            total_blocks += layer.num_blocks
        
        return {
            'in_memory_blocks': in_memory_blocks,
            'total_blocks': total_blocks,
            'memory_ratio': in_memory_blocks / total_blocks if total_blocks > 0 else 0,
            'offloaded_blocks': total_blocks - in_memory_blocks,
        }


def demo_fine_grained_adaptive():
    """演示细粒度自适应加载"""
    print("="*70)
    print("🧩 细粒度按需激活TNN")
    print("   每层4个功能块，按识别成功率动态加载")
    print("="*70)
    
    # 创建模型
    model = FineGrainedAdaptiveTNN(
        num_layers=3,
        hidden_dim=128,
        vocab_size=50,
        blocks_per_layer=4,
    )
    
    print(f"\n模型结构:")
    print(f"  层数: {model.num_layers}")
    print(f"  每层块数: {model.blocks_per_layer}")
    print(f"  总块数: {model.num_layers * model.blocks_per_layer}")
    
    # 模拟不同任务类型的输入
    task_examples = {
        "simple_pattern": torch.tensor([[0, 1, 2, 3, 4] * 6]),  # 重复模式
        "complex_sequence": torch.tensor([[0, 2, 4, 1, 3] * 6]),  # 复杂序列
        "abstract_reasoning": torch.tensor([[1, 3, 5, 7, 9] * 6]),  # 等差数列
    }
    
    print("\n" + "-"*70)
    print("测试不同任务类型的块选择")
    print("-"*70)
    
    for task_name, input_ids in task_examples.items():
        print(f"\n🔹 任务: {task_name}")
        
        # 前向传播，收集统计
        logits, stats = model(input_ids, return_stats=True)
        
        for i, layer_stat in enumerate(stats):
            print(f"   层{i}: 任务={layer_stat['task_type']}, "
                  f"选中块={layer_stat['selected_blocks']}, "
                  f"新加载={layer_stat.get('loaded_blocks', [])}")
    
    # 显示最终状态
    model.print_block_status()
    
    mem_stats = model.get_memory_stats()
    print(f"\n内存统计:")
    print(f"  内存中块数: {mem_stats['in_memory_blocks']}/{mem_stats['total_blocks']}")
    print(f"  内存比例: {mem_stats['memory_ratio']:.1%}")
    print(f"  磁盘卸载: {mem_stats['offloaded_blocks']}块")
    
    print("\n" + "="*70)
    print("演示完成!")
    print("="*70)
    
    return model


def demo_adaptive_training():
    """演示自适应训练过程"""
    print("\n" + "="*70)
    print("🎯 自适应训练演示")
    print("   根据训练成功率动态调整块加载")
    print("="*70)
    
    model = FineGrainedAdaptiveTNN(
        num_layers=2,
        hidden_dim=64,
        vocab_size=30,
        blocks_per_layer=4,
    )
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # 生成训练数据
    def generate_batch(task_type: str, batch_size: int = 4):
        if task_type == "simple":
            # 简单递增
            seq = torch.arange(20) % 30
        elif task_type == "complex":
            # 复杂模式
            seq = torch.tensor([i * 2 % 30 for i in range(20)])
        else:  # abstract
            # 抽象规律
            seq = torch.tensor([(i ** 2) % 30 for i in range(20)])
        
        data = seq.unsqueeze(0).repeat(batch_size, 1)
        target = torch.cat([data[:, 1:], data[:, :1]], dim=1)
        return data, target
    
    task_types = ["simple", "complex", "abstract"]
    
    print("\n开始训练（3轮，每轮3种任务）:")
    print("-"*70)
    
    for epoch in range(3):
        print(f"\n📚 Epoch {epoch + 1}")
        
        for task in task_types:
            input_ids, targets = generate_batch(task)
            
            # 前向
            logits = model(input_ids)
            loss = F.cross_entropy(logits.view(-1, model.vocab_size), targets.view(-1))
            
            # 计算准确率
            preds = logits.argmax(dim=-1)
            accuracy = (preds == targets).float().mean().item()
            
            # 反向
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            print(f"  {task:10s}: 损失={loss:.4f}, 准确率={accuracy:.1%}")
            
            # 更新块的成功率（用于后续块选择）
            for layer in model.layers:
                for bid in range(layer.num_blocks):
                    if bid in layer.active_blocks:
                        layer.blocks[str(bid)].update_stats(accuracy > 0.7)
        
        # 显示当前块状态
        mem_stats = model.get_memory_stats()
        print(f"   [内存块: {mem_stats['in_memory_blocks']}/{mem_stats['total_blocks']} "
              f"({mem_stats['memory_ratio']:.0%})]")
    
    print("\n" + "="*70)
    print("训练完成!")
    model.print_block_status()


if __name__ == "__main__":
    # 演示1: 基础功能
    model = demo_fine_grained_adaptive()
    
    # 演示2: 训练过程
    demo_adaptive_training()
