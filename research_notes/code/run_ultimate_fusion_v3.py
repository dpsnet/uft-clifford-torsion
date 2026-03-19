"""
终极融合版 V3 - 完全整合
UltimateTNN的所有优化 + 双路径架构
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import os
import gc
import copy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class FusionBlockV3(nn.Module):
    """
    V3功能块 - 完整融合版
    包含：细粒度处理 + 邻域反馈 + 兴奋度追踪
    """
    
    def __init__(self, block_id, dim, mode='cortical'):
        super().__init__()
        self.block_id = block_id
        self.mode = mode
        self.dim = dim
        
        # 核心变换（细粒度）
        self.norm1 = nn.LayerNorm(dim)
        self.attention = nn.Linear(dim, dim)
        self.norm2 = nn.LayerNorm(dim)
        
        if mode == 'cortical':
            # 离身：更深的FFN
            self.ff = nn.Sequential(
                nn.Linear(dim, dim * 2),
                nn.GELU(),
                nn.Dropout(0.1),
                nn.Linear(dim * 2, dim)
            )
        else:
            # 具身：动作友好
            self.ff = nn.Sequential(
                nn.Linear(dim, dim),
                nn.Tanh(),
                nn.Linear(dim, dim)
            )
        
        # 扭转门 - 跨路径通信
        self.torsion_gate = nn.Parameter(torch.randn(dim) * 0.01)
        
        # === 邻域反馈状态（来自UltimateTNN）===
        self.excitement = 0.5          # 兴奋度
        self.success_rate = 0.5        # 成功率
        self.activation_count = 0      # 激活计数
        self.neighbor_weights = {}     # 邻域权重
        
        # 可学习的重要性权重
        self.importance = nn.Parameter(torch.tensor(1.0))
    
    def forward(self, x, torsion_field, pathway_signal=None):
        """
        完整前向
        x: 输入
        torsion_field: 扭转场
        pathway_signal: 另一路径信号
        """
        self.activation_count += 1
        
        # 归一化 + 注意力
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
        
        # 跨路径信号整合
        if pathway_signal is not None:
            fusion_weight = torch.sigmoid(self.torsion_gate)
            h2 = h2 + pathway_signal * fusion_weight.unsqueeze(1)
        
        out = h + h2 * 0.5
        
        # 更新兴奋度（邻域反馈）
        self.excitement = min(1.0, self.excitement + 0.01)
        
        return out
    
    def record_success(self, success):
        """记录成功 - 邻域反馈更新"""
        alpha = 0.1
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)
        
        if not success:
            self.excitement = max(0.1, self.excitement - 0.05)
        
        # 更新重要性
        with torch.no_grad():
            self.importance.data = torch.tensor(self.success_rate * 0.7 + self.excitement * 0.3)
    
    def get_load_priority(self):
        """
        计算加载优先级（UltimateTNN公式）
        优先级 = 0.6×成功率 + 0.4×兴奋度
        """
        return self.success_rate * 0.6 + self.excitement * 0.4
    
    def get_state(self):
        """获取完整状态（用于磁盘保存）"""
        return {
            'weights': self.state_dict(),
            'feedback': {
                'excitement': self.excitement,
                'success_rate': self.success_rate,
                'activation_count': self.activation_count,
            }
        }
    
    def set_state(self, state):
        """恢复完整状态"""
        self.load_state_dict(state['weights'])
        fb = state['feedback']
        self.excitement = fb['excitement']
        self.success_rate = fb['success_rate']
        self.activation_count = fb['activation_count']


class FusionLayerV3:
    """
    V3层 - 完全融合
    双路径 + 细粒度块选择 + 磁盘卸载
    """
    
    def __init__(self, layer_id, dim, num_blocks, max_active_blocks, offload_dir):
        self.layer_id = layer_id
        self.dim = dim
        self.num_blocks = num_blocks
        self.max_active_blocks = max_active_blocks
        self.offload_dir = Path(offload_dir)
        
        # 双路径块（各num_blocks个）
        self.cortical_blocks: Dict[int, FusionBlockV3] = {}
        self.brainstem_blocks: Dict[int, FusionBlockV3] = {}
        self._create_blocks()
        
        # 细粒度块选择器（来自UltimateTNN）
        self.cortical_selector = nn.Linear(dim, num_blocks)
        self.brainstem_selector = nn.Linear(dim, num_blocks)
        
        # 跨路径注意力（丘脑）
        self.cross_pathway_attn = nn.Linear(dim * 2, dim)
        
        # 统计
        self.training_epochs = 0
        self.layer_best_accuracy = 0.0
        self.cortical_dominance = 0.5
        self.total_activations = 0
        
        # 磁盘路径
        self.offload_path = self.offload_dir / f"fusion_v3_layer_{layer_id}.pt"
        self.is_offloaded = False
    
    def _create_blocks(self):
        """创建所有块"""
        for i in range(self.num_blocks):
            self.cortical_blocks[i] = FusionBlockV3(i, self.dim, 'cortical')
            self.brainstem_blocks[i] = FusionBlockV3(i, self.dim, 'brainstem')
    
    def forward(self, cortical_input, brainstem_input, torsion_field, fusion_strength=0.3):
        """
        完整双路径前向（细粒度块选择）
        """
        self.total_activations += 1
        batch_size = cortical_input.size(0)
        
        # === 皮层路径：细粒度块选择 ===
        # 选择器得分
        selector_scores = torch.sigmoid(self.cortical_selector(cortical_input.mean(dim=1)))
        
        # 根据优先级调整（UltimateTNN策略）
        adjusted_scores = selector_scores.clone()
        for i, block in self.cortical_blocks.items():
            priority = block.get_load_priority()
            adjusted_scores[:, i] = selector_scores[:, i] * 0.6 + priority * 0.4
        
        # 动态选择最活跃的块
        _, cortical_top = torch.topk(adjusted_scores[0], min(self.max_active_blocks, self.num_blocks))
        
        # 执行选中的块
        cortical_h = cortical_input
        for idx in cortical_top.tolist():
            brainstem_signal = brainstem_input.mean(dim=1, keepdim=True)
            cortical_h = self.cortical_blocks[idx](cortical_h, torsion_field, brainstem_signal * fusion_strength)
            self.cortical_blocks[idx].record_success(True)
        
        # === 脑干路径：细粒度块选择 ===
        selector_scores = torch.sigmoid(self.brainstem_selector(brainstem_input.mean(dim=1)))
        adjusted_scores = selector_scores.clone()
        
        for i, block in self.brainstem_blocks.items():
            priority = block.get_load_priority()
            adjusted_scores[:, i] = selector_scores[:, i] * 0.6 + priority * 0.4
        
        _, brainstem_top = torch.topk(adjusted_scores[0], min(self.max_active_blocks, self.num_blocks))
        
        brainstem_h = brainstem_input
        for idx in brainstem_top.tolist():
            cortical_signal = cortical_input.mean(dim=1, keepdim=True)
            brainstem_h = self.brainstem_blocks[idx](brainstem_h, torsion_field, cortical_signal * fusion_strength)
            self.brainstem_blocks[idx].record_success(True)
        
        # === 丘脑融合 ===
        combined = torch.cat([cortical_h, brainstem_h], dim=-1)
        fused = self.cross_pathway_attn(combined)
        
        # 更新主导度
        cortical_act = cortical_h.abs().mean().item()
        brainstem_act = brainstem_h.abs().mean().item()
        total = cortical_act + brainstem_act + 1e-8
        self.cortical_dominance = cortical_act / total
        
        return cortical_h, brainstem_h, {
            'cortical_active': cortical_top.tolist(),
            'brainstem_active': brainstem_top.tolist(),
            'cortical_dominance': self.cortical_dominance,
            'fusion': fused,
        }
    
    def save_to_disk(self):
        """完整保存到磁盘（包括反馈状态）"""
        state = {
            'cortical_blocks': {i: b.get_state() for i, b in self.cortical_blocks.items()},
            'brainstem_blocks': {i: b.get_state() for i, b in self.brainstem_blocks.items()},
            'selectors': {
                'cortical': self.cortical_selector.state_dict(),
                'brainstem': self.brainstem_selector.state_dict(),
            },
            'cross_attn': self.cross_pathway_attn.state_dict(),
            'stats': {
                'training_epochs': self.training_epochs,
                'layer_best_accuracy': self.layer_best_accuracy,
                'cortical_dominance': self.cortical_dominance,
                'total_activations': self.total_activations,
            }
        }
        torch.save(state, self.offload_path)
        self.is_offloaded = True
    
    def load_from_disk(self):
        """完整从磁盘加载（包括反馈状态）"""
        if not self.offload_path.exists():
            return False
        
        state = torch.load(self.offload_path)
        
        # 恢复块状态和反馈
        for i, s in state['cortical_blocks'].items():
            if i in self.cortical_blocks:
                self.cortical_blocks[i].set_state(s)
        
        for i, s in state['brainstem_blocks'].items():
            if i in self.brainstem_blocks:
                self.brainstem_blocks[i].set_state(s)
        
        # 恢复网络参数
        self.cortical_selector.load_state_dict(state['selectors']['cortical'])
        self.brainstem_selector.load_state_dict(state['selectors']['brainstem'])
        self.cross_pathway_attn.load_state_dict(state['cross_attn'])
        
        # 恢复统计
        stats = state['stats']
        self.training_epochs = stats['training_epochs']
        self.layer_best_accuracy = stats['layer_best_accuracy']
        self.cortical_dominance = stats['cortical_dominance']
        self.total_activations = stats['total_activations']
        
        self.is_offloaded = False
        return True
    
    def offload(self):
        """卸载释放内存"""
        self.save_to_disk()
        del self.cortical_blocks, self.brainstem_blocks
        self.cortical_blocks, self.brainstem_blocks = {}, {}
        gc.collect()


class UltimateFusionV3(nn.Module):
    """
    终极融合版 V3 - 完全整合
    UltimateTNN + 双路径 + 所有优化
    """
    
    def __init__(self,
                 initial_layers=2,
                 target_layers=30,
                 dim=512,
                 vocab_size=500,
                 sensory_dim=128,
                 action_dim=64,
                 num_blocks=4,
                 max_active_blocks=2,
                 max_memory_layers=5,
                 offload_dir='./ultimate_fusion_v3'):
        super().__init__()
        
        self.target_layers = target_layers
        self.dim = dim
        self.vocab_size = vocab_size
        self.num_blocks = num_blocks
        self.max_active_blocks = max_active_blocks
        self.max_memory_layers = max_memory_layers
        self.offload_dir = Path(offload_dir)
        self.offload_dir.mkdir(parents=True, exist_ok=True)
        
        # === 双路径输入 ===
        # 皮层（离身）
        self.symbol_embedding = nn.Embedding(vocab_size, dim)
        self.cortical_pos = nn.Parameter(torch.randn(1, 256, dim) * 0.02)
        self.language_head = nn.Linear(dim, vocab_size)
        
        # 脑干（具身）
        self.sensory_encoder = nn.Linear(sensory_dim, dim)
        self.brainstem_pos = nn.Parameter(torch.randn(1, 64, dim) * 0.02)
        self.action_head = nn.Linear(dim, action_dim)
        
        # 共享扭转场
        self.register_buffer('torsion_field', torch.zeros(1, dim))
        
        # === 层管理（LRU缓存）===
        self.layers: Dict[int, FusionLayerV3] = {}
        self.offloaded_layers: set = set()
        self.access_order: List[int] = []
        
        # === 保守生长策略（UltimateTNN）===
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
        """打印架构信息"""
        print("="*70)
        print("🧠 终极融合版 V3 - 完全整合")
        print("="*70)
        print("融合组件:")
        print("  ✅ UltimateTNN优化:")
        print("     • 保守生长策略 (80%阈值)")
        print("     • 细粒度块选择 (动态2/4块)")
        print("     • 邻域反馈 (兴奋度+成功率)")
        print("     • 磁盘卸载 + LRU缓存")
        print("  ✅ 双路径架构:")
        print("     • 皮层路径 (离身智能)")
        print("     • 脑干路径 (具身智能)")
        print("     • 丘脑融合 (跨路径注意力)")
        print("-"*70)
        print(f"   目标层数: {self.target_layers}")
        print(f"   维度: {self.dim}")
        print(f"   每层: {self.num_blocks}块×2路径，激活{self.max_active_blocks}块")
        print(f"   内存缓存: {self.max_memory_layers}层")
        print(f"   预估参数: ~{self._estimate_params()/1e6:.0f}M")
        print("="*70)
    
    def _estimate_params(self):
        """估算参数"""
        base = sum(p.numel() for p in [
            self.symbol_embedding, self.language_head,
            self.sensory_encoder, self.action_head
        ])
        # 每层: 双路径块 + 选择器 + 融合
        layer_params = (
            self.num_blocks * 2 * (self.dim * self.dim * 4) +  # 块
            self.dim * self.num_blocks * 2 +                    # 选择器
            self.dim * 2 * self.dim                             # 融合
        )
        return base + layer_params * self.target_layers
    
    def _init_layers(self, num_layers):
        """初始化层"""
        for i in range(num_layers):
            layer = FusionLayerV3(
                i, self.dim, self.num_blocks,
                self.max_active_blocks, self.offload_dir
            )
            self.layers[i] = layer
            self.access_order.append(i)
    
    def _get_layer(self, idx):
        """获取层（LRU缓存管理）"""
        if idx in self.layers:
            # 更新访问顺序
            if idx in self.access_order:
                self.access_order.remove(idx)
            self.access_order.insert(0, idx)
            return self.layers[idx]
        
        # 从磁盘加载
        if idx in self.offloaded_layers:
            layer = FusionLayerV3(
                idx, self.dim, self.num_blocks,
                self.max_active_blocks, self.offload_dir
            )
            if layer.load_from_disk():
                self._manage_memory()
                self.layers[idx] = layer
                self.offloaded_layers.remove(idx)
                self.access_order.insert(0, idx)
                return layer
        return None
    
    def _manage_memory(self):
        """LRU内存管理（UltimateTNN策略）"""
        while len(self.layers) > self.max_memory_layers:
            lru_idx = self.access_order.pop()
            if lru_idx in self.layers:
                layer = self.layers[lru_idx]
                layer.save_to_disk()
                layer.offload()
                del self.layers[lru_idx]
                self.offloaded_layers.add(lru_idx)
                gc.collect()
    
    def forward(self, symbol_input=None, sensory_input=None, return_stats=False):
        """双路径前向"""
        # 皮层路径
        if symbol_input is not None:
            cortical_h = self.symbol_embedding(symbol_input)
            seq_len = symbol_input.size(1)
            cortical_h = cortical_h + self.cortical_pos[:, :seq_len, :]
        else:
            cortical_h = torch.zeros(1, 1, self.dim, device=self.torsion_field.device)
        
        # 脑干路径
        if sensory_input is not None:
            brainstem_h = self.sensory_encoder(sensory_input).unsqueeze(1)
            brainstem_h = brainstem_h + self.brainstem_pos[:, :1, :]
        else:
            brainstem_h = torch.zeros(1, 1, self.dim, device=self.torsion_field.device)
        
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
        outputs = {
            'symbol_logits': self.language_head(cortical_h) if symbol_input is not None else None,
            'action_logits': self.action_head(brainstem_h.squeeze(1)) if sensory_input is not None else None,
            'cortical_state': cortical_h,
            'brainstem_state': brainstem_h,
        }
        
        if return_stats:
            outputs['layer_stats'] = layer_stats
        
        return outputs
    
    def grow(self, num_new_layers=1):
        """保守生长"""
        current = len(self.layers) + len(self.offloaded_layers)
        
        # 检查充分性
        if current > 0:
            last = self._get_layer(current - 1)
            if last:
                epochs = last.training_epochs
                best_acc = last.layer_best_accuracy
                threshold = self.deep_layer_threshold if current >= 15 else self.growth_threshold_accuracy
                
                if epochs < self.min_cycles_before_growth:
                    print(f"⏸️ 推迟生长: 训练{epochs}/{self.min_cycles_before_growth}轮")
                    return
                if best_acc < threshold:
                    print(f"⏸️ 推迟生长: 准确率{best_acc:.1%} < {threshold}")
                    return
        
        print(f"\n🌱 V3生长: {current}层 → {current + num_new_layers}层")
        
        for i in range(num_new_layers):
            new_idx = current + i
            layer = FusionLayerV3(
                new_idx, self.dim, self.num_blocks,
                self.max_active_blocks, self.offload_dir
            )
            
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
        
        print(f"   内存:{len(self.layers)}层 | 磁盘:{len(self.offloaded_layers)}层")
        print(f"   阶段:{self.stages[self.current_stage][0]}")
    
    def training_step(self, symbol_input, sensory_input, symbol_target, action_target, optimizer):
        """训练"""
        self.train()
        
        outputs = self.forward(symbol_input, sensory_input, return_stats=True)
        
        # 双路径损失
        symbol_loss = F.cross_entropy(
            outputs['symbol_logits'].view(-1, self.vocab_size),
            symbol_target.view(-1)
        ) if outputs['symbol_logits'] is not None else 0
        
        action_loss = F.mse_loss(
            outputs['action_logits'], action_target
        ) if outputs['action_logits'] is not None else 0
        
        # 融合对齐损失
        fusion_loss = -torch.cosine_similarity(
            outputs['cortical_state'].mean(dim=1),
            outputs['brainstem_state'].mean(dim=1),
            dim=-1
        ).mean() * 0.1
        
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


def run_v3_demo():
    """运行V3演示"""
    print("\n" + "="*70)
    print("🚀 终极融合版 V3 演示")
    print("="*70 + "\n")
    
    model = UltimateFusionV3(
        initial_layers=2,
        target_layers=15,
        dim=256,
        vocab_size=100,
        sensory_dim=64,
        action_dim=32,
        num_blocks=4,
        max_active_blocks=2,
        max_memory_layers=5,
    )
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    print("\n开始训练...\n")
    peak_acc = 0
    
    for epoch in range(150):
        symbol_input = torch.randint(0, 100, (4, 16))
        sensory_input = torch.randn(4, 64)
        symbol_target = torch.randint(0, 100, (4, 16))
        action_target = torch.randn(4, 32)
        
        result = model.training_step(symbol_input, sensory_input, symbol_target, action_target, optimizer)
        peak_acc = max(peak_acc, result['symbol_acc'])
        
        if (epoch + 1) % 10 == 0:
            print(f"📚 Epoch {epoch + 1}")
            print(f"   损失: {result['loss']:.4f} | 符号准确率: {result['symbol_acc']:.1%} | 峰值: {peak_acc:.1%}")
            print(f"   层数: {result['layers']}/15 | 皮层主导: {result['dominance']:.1%}")
            
            # 显示块状态
            if model.layers:
                last_layer = list(model.layers.values())[-1]
                cortical_priorities = [b.get_load_priority() for b in last_layer.cortical_blocks.values()]
                print(f"   皮层块优先级: {[f'{p:.2f}' for p in cortical_priorities]}")
        
        if result['should_grow'] and result['layers'] < 15:
            model.grow(1)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        
        if result['layers'] >= 10 and result['symbol_acc'] >= 0.85:
            print(f"\n✅ 提前达成: {result['layers']}层, 准确率{result['symbol_acc']:.1%}")
            break
    
    print("\n" + "="*70)
    print("📊 V3演示完成")
    print("="*70)
    print(f"最终层数: {result['layers']}")
    print(f"最终准确率: {result['symbol_acc']:.1%}")
    print(f"峰值准确率: {peak_acc:.1%}")
    print(f"生长次数: {len(model.growth_history)}")
    print(f"内存中: {len(model.layers)}层 | 磁盘中: {len(model.offloaded_layers)}层")


if __name__ == "__main__":
    run_v3_demo()
