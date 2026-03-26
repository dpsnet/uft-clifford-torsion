"""
终极融合版V2 - 具身智能 + 离身智能 + 生长 + 磁盘卸载
真正的双路径统一架构
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import os
import json
import gc
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class DualPathBlock(nn.Module):
    """双路径功能块 - 支持符号和感知两种模式"""
    
    def __init__(self, block_id, dim, mode='cortical'):
        super().__init__()
        self.block_id = block_id
        self.mode = mode  # 'cortical' 或 'brainstem'
        self.dim = dim
        
        # 共享结构
        self.norm = nn.LayerNorm(dim)
        
        if mode == 'cortical':
            # 离身智能：符号处理
            self.processor = nn.Sequential(
                nn.Linear(dim, dim * 2),
                nn.GELU(),
                nn.Linear(dim * 2, dim)
            )
        else:
            # 具身智能：感知-动作
            self.processor = nn.Sequential(
                nn.Linear(dim, dim),
                nn.Tanh(),  # 动作空间有界
                nn.Linear(dim, dim)
            )
        
        # 扭转门 - 跨路径通信
        self.torsion_gate = nn.Parameter(torch.randn(dim) * 0.01)
        
        # 状态追踪
        self.excitement = 0.5
        self.success_rate = 0.5
        self.activation_count = 0
    
    def forward(self, x, torsion_field, pathway_signal=None):
        """
        前向传播
        x: 输入
        torsion_field: 共享扭转场
        pathway_signal: 来自另一路径的信号（跨路径通信）
        """
        self.activation_count += 1
        
        # 归一化
        h = self.norm(x)
        
        # 核心处理
        h = self.processor(h)
        
        # 扭转调制
        torsion_effect = torch.sigmoid(self.torsion_gate) * torsion_field
        h = h * (1 + torsion_effect.unsqueeze(1))
        
        # 跨路径信号整合
        if pathway_signal is not None:
            # 融合另一路径的信息
            fusion_weight = torch.sigmoid(self.torsion_gate)
            h = h + pathway_signal * fusion_weight.unsqueeze(1)
        
        # 残差
        out = x + h * 0.5
        
        # 更新兴奋度
        self.excitement = min(1.0, self.excitement + 0.01)
        
        return out
    
    def record_success(self, success):
        """记录成功/失败"""
        alpha = 0.1
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)
        if not success:
            self.excitement = max(0.1, self.excitement - 0.05)
    
    def get_priority(self):
        """获取加载优先级"""
        return self.success_rate * 0.6 + self.excitement * 0.4


class DualPathLayer:
    """双路径层 - 皮层 + 脑干"""
    
    def __init__(self, layer_id, dim, num_blocks, offload_dir):
        self.layer_id = layer_id
        self.dim = dim
        self.num_blocks = num_blocks
        self.offload_dir = Path(offload_dir)
        
        # 双路径块
        self.cortical_blocks: Dict[int, DualPathBlock] = {}
        self.brainstem_blocks: Dict[int, DualPathBlock] = {}
        
        # 块选择器
        self.cortical_selector = nn.Linear(dim, num_blocks)
        self.brainstem_selector = nn.Linear(dim, num_blocks)
        
        # 跨路径注意力（丘脑模拟）
        self.cross_pathway_attn = nn.Linear(dim * 2, dim)
        
        # 统计
        self.training_epochs = 0
        self.layer_best_accuracy = 0.0
        self.cortical_dominance = 0.5  # 皮层主导程度
        
        # 磁盘路径
        self.offload_path = self.offload_dir / f"dual_layer_{layer_id}.pt"
        
        self._create_blocks()
    
    def _create_blocks(self):
        """创建双路径块"""
        for i in range(self.num_blocks):
            self.cortical_blocks[i] = DualPathBlock(i, self.dim, 'cortical')
            self.brainstem_blocks[i] = DualPathBlock(i, self.dim, 'brainstem')
    
    def forward(self, cortical_input, brainstem_input, torsion_field, 
                max_active_blocks=2, fusion_strength=0.3):
        """
        双路径前向
        返回: (cortical_output, brainstem_output, fusion_info)
        """
        # 1. 皮层路径处理
        cortical_scores = torch.sigmoid(self.cortical_selector(cortical_input.mean(dim=1)))
        cortical_adjusted = cortical_scores.clone()
        
        for i, block in self.cortical_blocks.items():
            cortical_adjusted[0, i] = cortical_scores[0, i] * 0.7 + block.get_priority() * 0.3
        
        _, cortical_top = torch.topk(cortical_adjusted[0], min(max_active_blocks, self.num_blocks))
        
        cortical_h = cortical_input
        for idx in cortical_top.tolist():
            # 脑干信号作为pathway_signal传入
            brainstem_signal = brainstem_input.mean(dim=1, keepdim=True)
            cortical_h = self.cortical_blocks[idx](cortical_h, torsion_field, brainstem_signal * fusion_strength)
            self.cortical_blocks[idx].record_success(True)
        
        # 2. 脑干路径处理
        brainstem_scores = torch.sigmoid(self.brainstem_selector(brainstem_input.mean(dim=1)))
        brainstem_adjusted = brainstem_scores.clone()
        
        for i, block in self.brainstem_blocks.items():
            brainstem_adjusted[0, i] = brainstem_scores[0, i] * 0.7 + block.get_priority() * 0.3
        
        _, brainstem_top = torch.topk(brainstem_adjusted[0], min(max_active_blocks, self.num_blocks))
        
        brainstem_h = brainstem_input
        for idx in brainstem_top.tolist():
            # 皮层信号作为pathway_signal传入
            cortical_signal = cortical_input.mean(dim=1, keepdim=True)
            brainstem_h = self.brainstem_blocks[idx](brainstem_h, torsion_field, cortical_signal * fusion_strength)
            self.brainstem_blocks[idx].record_success(True)
        
        # 3. 丘脑融合（跨路径信息整合）
        combined = torch.cat([cortical_h, brainstem_h], dim=-1)
        fused = self.cross_pathway_attn(combined)
        
        # 更新主导程度
        cortical_activity = cortical_h.abs().mean().item()
        brainstem_activity = brainstem_h.abs().mean().item()
        total = cortical_activity + brainstem_activity + 1e-8
        self.cortical_dominance = cortical_activity / total
        
        return cortical_h, brainstem_h, {
            'cortical_blocks': cortical_top.tolist(),
            'brainstem_blocks': brainstem_top.tolist(),
            'dominance': self.cortical_dominance,
            'fusion': fused,
        }
    
    def save_to_disk(self):
        """保存到磁盘"""
        state = {
            'cortical_blocks': {i: b.state_dict() for i, b in self.cortical_blocks.items()},
            'brainstem_blocks': {i: b.state_dict() for i, b in self.brainstem_blocks.items()},
            'selectors': {
                'cortical': self.cortical_selector.state_dict(),
                'brainstem': self.brainstem_selector.state_dict(),
            },
            'cross_attn': self.cross_pathway_attn.state_dict(),
            'stats': {
                'training_epochs': self.training_epochs,
                'layer_best_accuracy': self.layer_best_accuracy,
                'cortical_dominance': self.cortical_dominance,
            }
        }
        torch.save(state, self.offload_path)
    
    def load_from_disk(self):
        """从磁盘加载"""
        if not self.offload_path.exists():
            return False
        
        state = torch.load(self.offload_path)
        
        for i, s in state['cortical_blocks'].items():
            if i in self.cortical_blocks:
                self.cortical_blocks[i].load_state_dict(s)
        
        for i, s in state['brainstem_blocks'].items():
            if i in self.brainstem_blocks:
                self.brainstem_blocks[i].load_state_dict(s)
        
        self.cortical_selector.load_state_dict(state['selectors']['cortical'])
        self.brainstem_selector.load_state_dict(state['selectors']['brainstem'])
        self.cross_pathway_attn.load_state_dict(state['cross_attn'])
        
        stats = state['stats']
        self.training_epochs = stats['training_epochs']
        self.layer_best_accuracy = stats['layer_best_accuracy']
        self.cortical_dominance = stats['cortical_dominance']
        
        return True
    
    def offload(self):
        """卸载"""
        self.save_to_disk()
        del self.cortical_blocks, self.brainstem_blocks
        self.cortical_blocks, self.brainstem_blocks = {}, {}
        gc.collect()


class UltimateDualPathTNN(nn.Module):
    """
    终极双路径融合TNN
    具身智能 + 离身智能 + 生长 + 磁盘卸载
    """
    
    def __init__(self,
                 initial_layers=2,
                 target_layers=50,
                 dim=512,
                 vocab_size=1000,
                 sensory_dim=128,
                 action_dim=64,
                 num_blocks=4,
                 max_memory_layers=5,
                 offload_dir='./dual_path_offload'):
        super().__init__()
        
        self.target_layers = target_layers
        self.dim = dim
        self.vocab_size = vocab_size
        self.num_blocks = num_blocks
        self.max_memory_layers = max_memory_layers
        self.offload_dir = Path(offload_dir)
        self.offload_dir.mkdir(parents=True, exist_ok=True)
        
        # === 皮层路径（离身智能）===
        self.symbol_embedding = nn.Embedding(vocab_size, dim)
        self.cortical_pos_enc = nn.Parameter(torch.randn(1, 512, dim) * 0.02)
        self.language_head = nn.Linear(dim, vocab_size)
        
        # === 脑干路径（具身智能）===
        self.sensory_encoder = nn.Linear(sensory_dim, dim)
        self.brainstem_pos_enc = nn.Parameter(torch.randn(1, 128, dim) * 0.02)
        self.action_head = nn.Linear(dim, action_dim)
        
        # === 共享扭转场（融合接口）===
        self.register_buffer('torsion_field', torch.zeros(1, dim))
        
        # === 双路径层管理 ===
        self.layers: Dict[int, DualPathLayer] = {}
        self.offloaded_layers: set = set()
        self.access_order: List[int] = []
        
        # === 保守生长策略 ===
        self.growth_threshold_accuracy = 0.80
        self.growth_threshold_loss = 0.5
        self.deep_layer_threshold = 0.82
        self.min_cycles_before_growth = 25
        
        self.current_stage = 0
        self.stages = {
            0: ("Embryo", 3), 1: ("Infant", 5), 2: ("Child", 8),
            3: ("Adolescent", 12), 4: ("Adult", 15), 5: ("Mature", 20),
            6: ("Expert", 30), 7: ("Master", 50),
        }
        
        self.growth_history = []
        
        # 初始化
        self._init_layers(initial_layers)
        
        self._print_info()
    
    def _print_info(self):
        """打印信息"""
        print("="*70)
        print("🧠 终极双路径融合TNN V2")
        print("="*70)
        print("架构:")
        print("  📝 皮层路径（离身智能）- 符号/语言/推理")
        print("  🎯 脑干路径（具身智能）- 感知/动作/反射")
        print("  🔗 扭转场 - 跨路径融合接口")
        print("-"*70)
        print("优化:")
        print("  ✅ 保守生长策略")
        print("  ✅ 细粒度双路径块选择")
        print("  ✅ 丘脑跨路径注意力")
        print("  ✅ 磁盘卸载 + LRU缓存")
        print("-"*70)
        print(f"   目标层数: {self.target_layers}")
        print(f"   维度: {self.dim}")
        print(f"   每层块数: {self.num_blocks}×2 (双路径)")
        print(f"   预估参数: ~{self._estimate_params()/1e6:.0f}M")
        print("="*70)
    
    def _estimate_params(self):
        """估算参数"""
        base = sum(p.numel() for p in [
            self.symbol_embedding, self.language_head,
            self.sensory_encoder, self.action_head
        ])
        # 每层双路径
        layer_params = self.num_blocks * 2 * (self.dim * self.dim * 3)
        return base + layer_params * self.target_layers
    
    def _init_layers(self, num_layers):
        """初始化层"""
        for i in range(num_layers):
            layer = DualPathLayer(i, self.dim, self.num_blocks, self.offload_dir)
            self.layers[i] = layer
            self.access_order.append(i)
    
    def _get_layer(self, idx):
        """获取层（LRU）"""
        if idx in self.layers:
            if idx in self.access_order:
                self.access_order.remove(idx)
            self.access_order.insert(0, idx)
            return self.layers[idx]
        
        if idx in self.offloaded_layers:
            layer = DualPathLayer(idx, self.dim, self.num_blocks, self.offload_dir)
            if layer.load_from_disk():
                self._manage_memory()
                self.layers[idx] = layer
                self.access_order.insert(0, idx)
                return layer
        return None
    
    def _manage_memory(self):
        """内存管理"""
        while len(self.layers) > self.max_memory_layers:
            lru = self.access_order.pop()
            if lru in self.layers:
                self.layers[lru].save_to_disk()
                self.layers[lru].offload()
                del self.layers[lru]
                self.offloaded_layers.add(lru)
                gc.collect()
    
    def forward(self, symbol_input=None, sensory_input=None, return_stats=False):
        """
        双路径前向
        symbol_input: [batch, seq] 符号序列（离身）
        sensory_input: [batch, sensory_dim] 感知输入（具身）
        """
        # 皮层路径
        if symbol_input is not None:
            cortical_h = self.symbol_embedding(symbol_input)
            seq_len = symbol_input.size(1)
            cortical_h = cortical_h + self.cortical_pos_enc[:, :seq_len, :]
        else:
            cortical_h = torch.zeros(1, 1, self.dim)
        
        # 脑干路径
        if sensory_input is not None:
            brainstem_h = self.sensory_encoder(sensory_input).unsqueeze(1)
            brainstem_h = brainstem_h + self.brainstem_pos_enc[:, :1, :]
        else:
            brainstem_h = torch.zeros(1, 1, self.dim)
        
        # 通过所有层
        layer_stats = []
        for idx in sorted(self.layers.keys()):
            layer = self._get_layer(idx)
            if layer:
                cortical_h, brainstem_h, info = layer(
                    cortical_h, brainstem_h, self.torsion_field
                )
                layer_stats.append(info)
        
        # 输出
        symbol_logits = self.language_head(cortical_h) if symbol_input is not None else None
        action_logits = self.action_head(brainstem_h.squeeze(1)) if sensory_input is not None else None
        
        outputs = {
            'symbol_logits': symbol_logits,
            'action_logits': action_logits,
            'cortical_state': cortical_h,
            'brainstem_state': brainstem_h,
        }
        
        if return_stats:
            outputs['layer_stats'] = layer_stats
        
        return outputs
    
    def grow(self, num_new_layers=1):
        """生长"""
        current = len(self.layers) + len(self.offloaded_layers)
        
        # 检查条件
        if current > 0:
            last = self._get_layer(current - 1)
            if last:
                epochs = last.training_epochs
                best_acc = last.layer_best_accuracy
                threshold = self.deep_layer_threshold if current >= 15 else self.growth_threshold_accuracy
                
                if epochs < self.min_cycles_before_growth:
                    print(f"⏸️ 生长推迟: 训练不足 ({epochs}/{self.min_cycles_before_growth})")
                    return
                if best_acc < threshold:
                    print(f"⏸️ 生长推迟: 准确率不足 ({best_acc:.1%} < {threshold})")
                    return
        
        print(f"\n🌱 双路径生长: {current}层 → {current + num_new_layers}层")
        
        for i in range(num_new_layers):
            new_idx = current + i
            layer = DualPathLayer(new_idx, self.dim, self.num_blocks, self.offload_dir)
            
            # Kaiming初始化
            for block in list(layer.cortical_blocks.values()) + list(layer.brainstem_blocks.values()):
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
    
    def training_step(self, symbol_input, sensory_input, symbol_target, action_target, optimizer):
        """训练步骤"""
        self.train()
        
        outputs = self.forward(symbol_input, sensory_input, return_stats=True)
        
        # 双路径损失
        symbol_loss = F.cross_entropy(
            outputs['symbol_logits'].view(-1, self.vocab_size),
            symbol_target.view(-1)
        ) if outputs['symbol_logits'] is not None else 0
        
        action_loss = F.mse_loss(
            outputs['action_logits'],
            action_target
        ) if outputs['action_logits'] is not None else 0
        
        # 融合损失
        fusion_loss = -torch.cosine_similarity(
            outputs['cortical_state'].mean(dim=1),
            outputs['brainstem_state'].mean(dim=1),
            dim=-1
        ).mean() * 0.1  # 鼓励两路径对齐
        
        total_loss = symbol_loss + action_loss + fusion_loss
        
        optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
        optimizer.step()
        
        # 统计
        with torch.no_grad():
            symbol_acc = (outputs['symbol_logits'].argmax(dim=-1) == symbol_target).float().mean().item() if outputs['symbol_logits'] is not None else 0
        
        # 更新层
        last_idx = max(self.layers.keys()) if self.layers else 0
        layer = self._get_layer(last_idx)
        if layer:
            layer.training_epochs += 1
            layer.layer_best_accuracy = max(layer.layer_best_accuracy, symbol_acc)
        
        should_grow = symbol_acc >= self.growth_threshold_accuracy and total_loss.item() <= self.growth_threshold_loss
        
        return {
            'loss': total_loss.item(),
            'symbol_acc': symbol_acc,
            'layers': len(self.layers) + len(self.offloaded_layers),
            'should_grow': should_grow,
            'dominance': layer.cortical_dominance if layer else 0.5,
        }


def run_dual_path_demo():
    """运行双路径演示"""
    print("\n🚀 启动终极双路径融合TNN演示\n")
    
    model = UltimateDualPathTNN(
        initial_layers=2,
        target_layers=20,
        dim=256,
        vocab_size=100,
        sensory_dim=64,
        action_dim=32,
        num_blocks=4,
        max_memory_layers=5,
    )
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    print("\n开始训练...\n")
    
    for epoch in range(100):
        # 双输入
        symbol_input = torch.randint(0, 100, (4, 16))
        sensory_input = torch.randn(4, 64)
        symbol_target = torch.randint(0, 100, (4, 16))
        action_target = torch.randn(4, 32)
        
        result = model.training_step(symbol_input, sensory_input, symbol_target, action_target, optimizer)
        
        if (epoch + 1) % 10 == 0:
            print(f"📚 Epoch {epoch + 1}")
            print(f"   损失: {result['loss']:.4f} | 符号准确率: {result['symbol_acc']:.1%}")
            print(f"   层数: {result['layers']}/20 | 皮层主导: {result['dominance']:.1%}")
        
        if result['should_grow'] and result['layers'] < 20:
            model.grow(1)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    print("\n✅ 双路径演示完成!")


if __name__ == "__main__":
    run_dual_path_demo()
