"""
终极融合版 V4 - 课程学习 + 自适应难度
任务难度随准确率动态调整，确保始终有可学习信号
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


class FusionBlockV4(nn.Module):
    """V4功能块 - 完整融合"""
    
    def __init__(self, block_id, dim, mode='cortical'):
        super().__init__()
        self.block_id = block_id
        self.mode = mode
        self.dim = dim
        
        self.norm1 = nn.LayerNorm(dim)
        self.attention = nn.Linear(dim, dim)
        self.norm2 = nn.LayerNorm(dim)
        
        if mode == 'cortical':
            self.ff = nn.Sequential(
                nn.Linear(dim, dim * 2),
                nn.GELU(),
                nn.Dropout(0.1),
                nn.Linear(dim * 2, dim)
            )
        else:
            self.ff = nn.Sequential(
                nn.Linear(dim, dim),
                nn.Tanh(),
                nn.Linear(dim, dim)
            )
        
        self.torsion_gate = nn.Parameter(torch.randn(dim) * 0.01)
        
        # 邻域反馈状态
        self.excitement = 0.5
        self.success_rate = 0.5
        self.activation_count = 0
        self.importance = nn.Parameter(torch.tensor(1.0))
    
    def forward(self, x, torsion_field, pathway_signal=None):
        self.activation_count += 1
        
        h = self.norm1(x)
        h = self.attention(h)
        
        torsion_effect = torch.sigmoid(self.torsion_gate) * torsion_field
        h = h * (1 + torsion_effect.unsqueeze(1))
        
        h = x + h * 0.5
        
        h2 = self.norm2(h)
        h2 = self.ff(h2)
        
        # 跨路径信号整合
        if pathway_signal is not None:
            fusion_weight = torch.sigmoid(self.torsion_gate)
            if pathway_signal.dim() == 2:
                pathway_signal = pathway_signal.unsqueeze(1)
            if pathway_signal.size(1) == 1 and h2.size(1) > 1:
                pathway_signal = pathway_signal.expand(-1, h2.size(1), -1)
            fusion_weight_expanded = fusion_weight.view(1, 1, -1)
            h2 = h2 + pathway_signal * fusion_weight_expanded
        
        out = h + h2 * 0.5
        self.excitement = min(1.0, self.excitement + 0.01)
        return out
    
    def record_success(self, success):
        alpha = 0.1
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)
        if not success:
            self.excitement = max(0.1, self.excitement - 0.05)
        with torch.no_grad():
            self.importance.data = torch.tensor(self.success_rate * 0.7 + self.excitement * 0.3)
    
    def get_load_priority(self):
        return self.success_rate * 0.6 + self.excitement * 0.4
    
    def get_state(self):
        return {
            'weights': self.state_dict(),
            'feedback': {
                'excitement': self.excitement,
                'success_rate': self.success_rate,
                'activation_count': self.activation_count,
            }
        }
    
    def set_state(self, state):
        self.load_state_dict(state['weights'])
        fb = state['feedback']
        self.excitement = fb['excitement']
        self.success_rate = fb['success_rate']
        self.activation_count = fb['activation_count']


class FusionLayerV4:
    """V4层 - 完全融合"""
    
    def __init__(self, layer_id, dim, num_blocks, max_active_blocks, offload_dir):
        self.layer_id = layer_id
        self.dim = dim
        self.num_blocks = num_blocks
        self.max_active_blocks = max_active_blocks
        self.offload_dir = Path(offload_dir)
        
        self.cortical_blocks: Dict[int, FusionBlockV4] = {}
        self.brainstem_blocks: Dict[int, FusionBlockV4] = {}
        self._create_blocks()
        
        self.cortical_selector = nn.Linear(dim, num_blocks)
        self.brainstem_selector = nn.Linear(dim, num_blocks)
        self.cross_pathway_attn = nn.Linear(dim * 2, dim)
        
        self.training_epochs = 0
        self.layer_best_accuracy = 0.0
        self.cortical_dominance = 0.5
        self.total_activations = 0
        
        self.offload_path = self.offload_dir / f"fusion_v4_layer_{layer_id}.pt"
        self.is_offloaded = False
    
    def _create_blocks(self):
        for i in range(self.num_blocks):
            self.cortical_blocks[i] = FusionBlockV4(i, self.dim, 'cortical')
            self.brainstem_blocks[i] = FusionBlockV4(i, self.dim, 'brainstem')
    
    def __call__(self, cortical_input, brainstem_input, torsion_field, fusion_strength=0.3):
        self.total_activations += 1
        
        # 皮层路径
        selector_scores = torch.sigmoid(self.cortical_selector(cortical_input.mean(dim=1)))
        adjusted_scores = selector_scores.clone()
        for i, block in self.cortical_blocks.items():
            priority = block.get_load_priority()
            adjusted_scores[:, i] = selector_scores[:, i] * 0.6 + priority * 0.4
        
        _, cortical_top = torch.topk(adjusted_scores[0], min(self.max_active_blocks, self.num_blocks))
        
        cortical_h = cortical_input
        for idx in cortical_top.tolist():
            brainstem_signal = brainstem_input.mean(dim=1, keepdim=True)
            cortical_h = self.cortical_blocks[idx](cortical_h, torsion_field, brainstem_signal * fusion_strength)
            self.cortical_blocks[idx].record_success(True)
        
        # 脑干路径
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
        
        # 丘脑融合
        if cortical_h.size(1) != brainstem_h.size(1):
            if brainstem_h.size(1) == 1:
                brainstem_h = brainstem_h.expand(-1, cortical_h.size(1), -1)
            else:
                brainstem_h = brainstem_h.mean(dim=1, keepdim=True).expand(-1, cortical_h.size(1), -1)
        
        combined = torch.cat([cortical_h, brainstem_h], dim=-1)
        fused = self.cross_pathway_attn(combined)
        
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
        if not self.offload_path.exists():
            return False
        
        state = torch.load(self.offload_path)
        
        for i, s in state['cortical_blocks'].items():
            if i in self.cortical_blocks:
                self.cortical_blocks[i].set_state(s)
        
        for i, s in state['brainstem_blocks'].items():
            if i in self.brainstem_blocks:
                self.brainstem_blocks[i].set_state(s)
        
        self.cortical_selector.load_state_dict(state['selectors']['cortical'])
        self.brainstem_selector.load_state_dict(state['selectors']['brainstem'])
        self.cross_pathway_attn.load_state_dict(state['cross_attn'])
        
        stats = state['stats']
        self.training_epochs = stats['training_epochs']
        self.layer_best_accuracy = stats['layer_best_accuracy']
        self.cortical_dominance = stats['cortical_dominance']
        self.total_activations = stats['total_activations']
        
        self.is_offloaded = False
        return True
    
    def offload(self):
        self.save_to_disk()
        del self.cortical_blocks, self.brainstem_blocks
        self.cortical_blocks, self.brainstem_blocks = {}, {}
        gc.collect()


class CurriculumScheduler:
    """课程学习调度器 - 动态调整任务难度"""
    
    def __init__(self, vocab_size_max=500, seq_len_max=32, batch_size=4):
        self.vocab_size_max = vocab_size_max
        self.seq_len_max = seq_len_max
        self.batch_size = batch_size
        
        # 难度等级
        self.level = 0
        self.levels = [
            {'vocab': 2, 'seq': 4, 'name': 'Baby'},
            {'vocab': 4, 'seq': 4, 'name': 'Toddler'},
            {'vocab': 8, 'seq': 8, 'name': 'Child'},
            {'vocab': 16, 'seq': 8, 'name': 'Student'},
            {'vocab': 32, 'seq': 16, 'name': 'Teen'},
            {'vocab': 64, 'seq': 16, 'name': 'Young'},
            {'vocab': 128, 'seq': 24, 'name': 'Adult'},
            {'vocab': 256, 'seq': 32, 'name': 'Expert'},
            {'vocab': 500, 'seq': 32, 'name': 'Master'},
        ]
        
        self.acc_history = []
        self.promotion_threshold = 0.75  # 75%准确率升级
        
    def get_current_difficulty(self):
        """获取当前难度"""
        cfg = self.levels[min(self.level, len(self.levels)-1)]
        return cfg['vocab'], cfg['seq'], cfg['name']
    
    def generate_batch(self, device='cpu'):
        """生成当前难度的训练批次"""
        vocab, seq_len, name = self.get_current_difficulty()
        
        symbol_input = torch.randint(0, vocab, (self.batch_size, seq_len), device=device)
        # 简单任务：预测下一个token
        symbol_target = torch.cat([
            symbol_input[:, 1:], 
            torch.randint(0, vocab, (self.batch_size, 1), device=device)
        ], dim=1)
        
        sensory_input = torch.randn(self.batch_size, 64, device=device)
        action_target = torch.randn(self.batch_size, 32, device=device)
        
        return symbol_input, symbol_target, sensory_input, action_target, vocab
    
    def update(self, accuracy):
        """更新难度"""
        self.acc_history.append(accuracy)
        
        # 检查是否应该升级
        if len(self.acc_history) >= 10:
            recent_acc = sum(self.acc_history[-10:]) / 10
            if recent_acc >= self.promotion_threshold and self.level < len(self.levels) - 1:
                self.level += 1
                self.acc_history = []  # 重置历史
                vocab, seq_len, name = self.get_current_difficulty()
                return True, name, vocab, seq_len
        
        return False, None, None, None
    
    def get_progress_str(self):
        """获取进度字符串"""
        _, _, name = self.get_current_difficulty()
        return f"Level {self.level} ({name})"


class UltimateFusionV4(nn.Module):
    """终极融合版 V4 - 课程学习 + 自适应难度"""
    
    def __init__(self,
                 initial_layers=2,
                 target_layers=20,
                 dim=256,
                 vocab_size_max=500,
                 sensory_dim=64,
                 action_dim=32,
                 num_blocks=4,
                 max_active_blocks=2,
                 max_memory_layers=5,
                 offload_dir='./ultimate_fusion_v4'):
        super().__init__()
        
        self.target_layers = target_layers
        self.dim = dim
        self.vocab_size_max = vocab_size_max
        self.num_blocks = num_blocks
        self.max_active_blocks = max_active_blocks
        self.max_memory_layers = max_memory_layers
        self.offload_dir = Path(offload_dir)
        self.offload_dir.mkdir(parents=True, exist_ok=True)
        
        # 嵌入层（最大词汇表）
        self.symbol_embedding = nn.Embedding(vocab_size_max, dim)
        self.cortical_pos = nn.Parameter(torch.randn(1, 128, dim) * 0.02)
        self.language_head = nn.Linear(dim, vocab_size_max)
        
        self.sensory_encoder = nn.Linear(sensory_dim, dim)
        self.brainstem_pos = nn.Parameter(torch.randn(1, 64, dim) * 0.02)
        self.action_head = nn.Linear(dim, action_dim)
        
        self.register_buffer('torsion_field', torch.zeros(1, dim))
        
        # 层管理
        self.layers: Dict[int, FusionLayerV4] = {}
        self.offloaded_layers: set = set()
        self.access_order: List[int] = []
        
        # 保守生长策略
        self.growth_threshold_accuracy = 0.70  # 70%触发（课程学习中较低）
        self.growth_threshold_loss = 0.5
        self.deep_layer_threshold = 0.75
        self.min_cycles_before_growth = 25
        
        self.current_stage = 0
        self.stages = {
            0: ("Baby", 2), 1: ("Toddler", 3), 2: ("Child", 5),
            3: ("Student", 7), 4: ("Teen", 10), 5: ("Young", 13),
            6: ("Adult", 16), 7: ("Expert", 20),
        }
        
        self.growth_history = []
        self.curriculum_promotions = []
        
        self._init_layers(initial_layers)
        self._print_info()
    
    def _print_info(self):
        print("="*70)
        print("🎓 终极融合版 V4 - 课程学习")
        print("="*70)
        print("课程策略:")
        print("  • 从2词开始，逐步增加到500词")
        print("  • 序列长度从4逐步增加到32")
        print("  • 75%准确率触发难度升级")
        print("-"*70)
        print("融合组件:")
        print("  ✅ 保守生长 (70%阈值)")
        print("  ✅ 细粒度块选择")
        print("  ✅ 双路径架构")
        print("  ✅ 磁盘卸载 + LRU")
        print("-"*70)
        print(f"   目标层数: {self.target_layers}")
        print(f"   维度: {self.dim}")
        print(f"   内存缓存: {self.max_memory_layers}层")
        print("="*70)
    
    def _init_layers(self, num_layers):
        for i in range(num_layers):
            layer = FusionLayerV4(i, self.dim, self.num_blocks, self.max_active_blocks, self.offload_dir)
            self.layers[i] = layer
            self.access_order.append(i)
    
    def _get_layer(self, idx):
        if idx in self.layers:
            if idx in self.access_order:
                self.access_order.remove(idx)
            self.access_order.insert(0, idx)
            return self.layers[idx]
        
        if idx in self.offloaded_layers:
            layer = FusionLayerV4(idx, self.dim, self.num_blocks, self.max_active_blocks, self.offload_dir)
            if layer.load_from_disk():
                self._manage_memory()
                self.layers[idx] = layer
                self.offloaded_layers.remove(idx)
                self.access_order.insert(0, idx)
                return layer
        return None
    
    def _manage_memory(self):
        while len(self.layers) > self.max_memory_layers:
            lru_idx = self.access_order.pop()
            if lru_idx in self.layers:
                self.layers[lru_idx].save_to_disk()
                self.layers[lru_idx].offload()
                del self.layers[lru_idx]
                self.offloaded_layers.add(lru_idx)
                gc.collect()
    
    def forward(self, symbol_input=None, sensory_input=None, vocab_size=None, return_stats=False):
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
                cortical_h, brainstem_h, info = layer(cortical_h, brainstem_h, self.torsion_field)
                layer_stats.append(info)
        
        # 输出（只输出当前词汇表范围的logits）
        if symbol_input is not None and vocab_size is not None:
            symbol_logits = self.language_head(cortical_h)[:, :, :vocab_size]
        else:
            symbol_logits = None
        
        outputs = {
            'symbol_logits': symbol_logits,
            'action_logits': self.action_head(brainstem_h.squeeze(1)) if sensory_input is not None else None,
            'cortical_state': cortical_h,
            'brainstem_state': brainstem_h,
        }
        
        if return_stats:
            outputs['layer_stats'] = layer_stats
        
        return outputs
    
    def grow(self, num_new_layers=1):
        current = len(self.layers) + len(self.offloaded_layers)
        
        if current > 0:
            last = self._get_layer(current - 1)
            if last:
                epochs = last.training_epochs
                best_acc = last.layer_best_accuracy
                threshold = self.deep_layer_threshold if current >= 10 else self.growth_threshold_accuracy
                
                if epochs < self.min_cycles_before_growth:
                    return False, f"训练{epochs}/{self.min_cycles_before_growth}轮"
                if best_acc < threshold:
                    return False, f"准确率{best_acc:.1%} < {threshold}"
        
        print(f"\n🌱 V4生长: {current}层 → {current + num_new_layers}层")
        
        for i in range(num_new_layers):
            new_idx = current + i
            layer = FusionLayerV4(new_idx, self.dim, self.num_blocks, self.max_active_blocks, self.offload_dir)
            
            for block in list(layer.cortical_blocks.values()) + list(layer.brainstem_blocks.values()):
                for name, p in block.named_parameters():
                    if 'weight' in name and len(p.shape) >= 2:
                        nn.init.kaiming_normal_(p, mode='fan_out', nonlinearity='relu')
                    elif 'bias' in name:
                        nn.init.zeros_(p)
            
            self.layers[new_idx] = layer
            self.access_order.insert(0, new_idx)
            self._manage_memory()
        
        for stage_id, (name, target) in self.stages.items():
            if len(self.layers) >= target:
                self.current_stage = stage_id
        
        self.growth_history.append({
            'timestamp': datetime.now().isoformat(),
            'previous': current,
            'new': current + num_new_layers,
            'stage': self.stages[self.current_stage][0],
        })
        
        return True, f"阶段: {self.stages[self.current_stage][0]}"
    
    def training_step(self, symbol_input, sensory_input, symbol_target, action_target, vocab_size, optimizer):
        self.train()
        
        outputs = self.forward(symbol_input, sensory_input, vocab_size, return_stats=True)
        
        symbol_loss = F.cross_entropy(
            outputs['symbol_logits'].view(-1, vocab_size),
            symbol_target.view(-1)
        ) if outputs['symbol_logits'] is not None else 0
        
        action_loss = F.mse_loss(
            outputs['action_logits'].mean(dim=1), action_target
        ) if outputs['action_logits'] is not None else 0
        
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
        
        with torch.no_grad():
            symbol_acc = (outputs['symbol_logits'].argmax(dim=-1) == symbol_target).float().mean().item() if outputs['symbol_logits'] is not None else 0
        
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


def run_v4_demo():
    """运行V4课程学习演示"""
    print("\n" + "="*70)
    print("🎓 终极融合版 V4 - 课程学习演示")
    print("="*70 + "\n")
    
    model = UltimateFusionV4(
        initial_layers=2,
        target_layers=20,
        dim=256,
        vocab_size_max=500,
        sensory_dim=64,
        action_dim=32,
        num_blocks=4,
        max_active_blocks=2,
        max_memory_layers=5,
    )
    
    # 课程调度器
    curriculum = CurriculumScheduler(vocab_size_max=500, seq_len_max=32, batch_size=4)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    
    print(f"\n开始课程学习...")
    print(f"初始难度: {curriculum.get_progress_str()}\n")
    
    peak_acc = 0
    total_promotions = 0
    total_growth = 0
    
    for epoch in range(800):
        # 获取当前难度的数据
        symbol_input, symbol_target, sensory_input, action_target, vocab_size = curriculum.generate_batch()
        
        result = model.training_step(symbol_input, sensory_input, symbol_target, action_target, vocab_size, optimizer)
        peak_acc = max(peak_acc, result['symbol_acc'])
        
        # 更新课程难度
        promoted, new_level, new_vocab, new_seq = curriculum.update(result['symbol_acc'])
        if promoted:
            total_promotions += 1
            print(f"\n{'='*60}")
            print(f"🎉 课程升级! 难度 → {new_level} (vocab={new_vocab}, seq={new_seq})")
            print(f"{'='*60}\n")
        
        # 尝试生长
        if result['should_grow'] and result['layers'] < 20:
            success, msg = model.grow(1)
            if success:
                total_growth += 1
                optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
                print(f"   🌱 生长成功! {msg}")
        
        # 定期报告
        if (epoch + 1) % 100 == 0 or (promoted and epoch > 0):
            vocab, seq, level_name = curriculum.get_current_difficulty()
            print(f"📚 Epoch {epoch + 1} | 难度: {level_name}(vocab={vocab}, seq={seq})")
            print(f"   损失: {result['loss']:.4f} | 准确率: {result['symbol_acc']:.1%} | 峰值: {peak_acc:.1%}")
            print(f"   层数: {result['layers']}/20 | 皮层主导: {result['dominance']:.1%}")
            
            if model.layers:
                last_layer = list(model.layers.values())[-1]
                cortical_priorities = [b.get_load_priority() for b in last_layer.cortical_blocks.values()]
                print(f"   块优先级: {[f'{p:.2f}' for p in cortical_priorities]}")
        
        # 提前结束条件
        if result['layers'] >= 15 and curriculum.level >= 7:
            print(f"\n✅ 目标达成: {result['layers']}层, 难度{curriculum.get_progress_str()}")
            break
    
    print("\n" + "="*70)
    print("📊 V4演示完成")
    print("="*70)
    print(f"最终层数: {result['layers']}")
    print(f"最终难度: {curriculum.get_progress_str()}")
    print(f"峰值准确率: {peak_acc:.1%}")
    print(f"课程升级: {total_promotions}次")
    print(f"网络生长: {total_growth}次")
    print(f"内存中: {len(model.layers)}层 | 磁盘中: {len(model.offloaded_layers)}层")


if __name__ == "__main__":
    run_v4_demo()
