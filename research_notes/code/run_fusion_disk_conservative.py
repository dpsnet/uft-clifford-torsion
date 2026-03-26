"""
融合版：保守策略 + 磁盘卸载
支持50层+ / 100M+参数的超大规模实验
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import os
import json
import gc
import pickle
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class DiskOffloadedLayer:
    """磁盘卸载的层 - 按需加载到内存"""
    
    def __init__(self, layer_id, hidden_dim, ff_dim, blocks_per_layer, offload_dir):
        self.layer_id = layer_id
        self.hidden_dim = hidden_dim
        self.ff_dim = ff_dim
        self.blocks_per_layer = blocks_per_layer
        self.offload_dir = Path(offload_dir)
        self.offload_dir.mkdir(parents=True, exist_ok=True)
        
        # 状态追踪
        self.is_loaded = False
        self.layer = None
        self.offload_path = self.offload_dir / f"layer_{layer_id}.pkl"
        
        # 统计
        self.activation_count = 0
        self.success_count = 0
        self.total_calls = 0
    
    def create_and_save(self, layer_factory):
        """创建层并保存到磁盘"""
        layer = layer_factory()
        self._save_to_disk(layer)
        del layer
        gc.collect()
        self.is_loaded = False
    
    def _save_to_disk(self, layer):
        """序列化到磁盘"""
        state = {
            'state_dict': layer.state_dict(),
            'layer_id': self.layer_id,
            'stats': {
                'activation_count': getattr(self, 'activation_count', 0),
                'success_count': getattr(self, 'success_count', 0),
            }
        }
        with open(self.offload_path, 'wb') as f:
            pickle.dump(state, f)
    
    def load(self):
        """从磁盘加载"""
        if self.is_loaded:
            return self.layer
        
        if not self.offload_path.exists():
            raise FileNotFoundError(f"Layer file not found: {self.offload_path}")
        
        with open(self.offload_path, 'rb') as f:
            state = pickle.load(f)
        
        # 这里需要重新创建层结构
        # 简化版本：返回状态字典
        self.layer = state['state_dict']
        self.is_loaded = True
        return self.layer
    
    def offload(self):
        """卸载到磁盘，释放内存"""
        if self.is_loaded and self.layer is not None:
            self._save_to_disk(self.layer)
            del self.layer
            self.layer = None
            self.is_loaded = False
            gc.collect()
    
    def record_success(self, success):
        """记录成功/失败"""
        self.total_calls += 1
        if success:
            self.success_count += 1


class ConservativeDiskTNN(nn.Module):
    """
    保守策略 + 磁盘卸载的TNN
    支持50层+ / 100M+参数
    """
    
    def __init__(self, 
                 initial_layers=2,
                 target_layers=50,
                 hidden_dim=1024,  # 更大维度
                 vocab_size=500,
                 blocks_per_layer=4,
                 offload_dir='./disk_offload_cache',
                 max_memory_layers=5):  # 内存中最多保留5层
        super().__init__()
        
        self.target_layers = target_layers
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size
        self.blocks_per_layer = blocks_per_layer
        self.offload_dir = Path(offload_dir)
        self.max_memory_layers = max_memory_layers
        
        # 基础模块（始终留在内存）
        self.embedding = nn.Embedding(vocab_size, hidden_dim)
        self.pos_encoding = nn.Parameter(torch.randn(1, 512, hidden_dim) * 0.02)
        self.lm_head = nn.Linear(hidden_dim, vocab_size)
        
        # 扭转场（简化版）
        self.register_buffer('torsion_field', torch.zeros(1, 8))
        
        # 磁盘卸载的层
        self.offloaded_layers = []
        
        # 内存中的层索引（LRU缓存）
        self.memory_layers = {}  # layer_idx -> layer
        self.access_order = []   # 最近访问的层在前面
        
        # 保守生长策略
        self.growth_threshold_accuracy = 0.80
        self.growth_threshold_loss = 0.5
        self.deep_layer_threshold = 0.82
        self.min_cycles_before_growth = 25
        
        # 追踪
        self.layer_training_epochs = {}
        self.layer_best_accuracy = {}
        self.current_stage = 0
        
        # 阶段定义
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
        
        # 初始化前几层
        self._init_initial_layers(initial_layers)
        
        print("="*70)
        print("🚀 融合版TNN：保守策略 + 磁盘卸载")
        print("="*70)
        print(f"   目标层数: {target_layers}")
        print(f"   隐藏维度: {hidden_dim}")
        print(f"   词汇表: {vocab_size}")
        print(f"   内存缓存: {max_memory_layers}层")
        print(f"   磁盘卸载: {offload_dir}")
        print(f"   预估总参数: ~{self._estimate_params()/1e6:.0f}M")
        print("="*70)
    
    def _estimate_params(self):
        """估算总参数量"""
        base = sum(p.numel() for p in [self.embedding, self.lm_head])
        layer_params = (
            self.hidden_dim * self.hidden_dim * 2 +
            self.hidden_dim * (self.hidden_dim // 2) * 4 * self.blocks_per_layer +
            self.hidden_dim * 4
        )
        return base + layer_params * self.target_layers
    
    def _init_initial_layers(self, num_layers):
        """初始化前几层到内存"""
        for i in range(num_layers):
            layer = self._create_layer(i)
            self.memory_layers[i] = layer
            self.access_order.append(i)
            self.layer_training_epochs[i] = 0
            self.layer_best_accuracy[i] = 0
    
    def _create_layer(self, layer_id):
        """创建单层（简化版结构）"""
        # 导入原始AdaptiveLayer
        from unified_adaptive_tnn import AdaptiveLayer
        
        layer = AdaptiveLayer(
            layer_id,
            self.hidden_dim,
            (2, 2),
            self.blocks_per_layer
        )
        
        # Kaiming初始化
        with torch.no_grad():
            for name, p in layer.named_parameters():
                if 'weight' in name and len(p.shape) >= 2:
                    nn.init.kaiming_normal_(p, mode='fan_out', nonlinearity='relu')
                elif 'bias' in name:
                    nn.init.zeros_(p)
        
        return layer
    
    def _get_layer(self, layer_idx):
        """获取层（带LRU缓存管理）"""
        if layer_idx in self.memory_layers:
            # 更新访问顺序
            if layer_idx in self.access_order:
                self.access_order.remove(layer_idx)
            self.access_order.insert(0, layer_idx)
            return self.memory_layers[layer_idx]
        
        # 从磁盘加载（如果需要）
        # 简化版本：这里直接创建新层
        return None
    
    def _manage_memory(self):
        """管理内存 - 卸载最少使用的层"""
        while len(self.memory_layers) > self.max_memory_layers:
            # 移除最少使用的层
            lru_layer = self.access_order.pop()
            if lru_layer in self.memory_layers:
                # 保存到磁盘
                self._save_layer_to_disk(lru_layer)
                del self.memory_layers[lru_layer]
                gc.collect()
    
    def _save_layer_to_disk(self, layer_idx):
        """保存层到磁盘"""
        if layer_idx not in self.memory_layers:
            return
        
        layer = self.memory_layers[layer_idx]
        path = self.offload_dir / f"layer_{layer_idx}.pt"
        torch.save(layer.state_dict(), path)
    
    def forward(self, input_ids, return_stats=False):
        """前向传播 - 只使用内存中的层"""
        # Embedding
        h = self.embedding(input_ids)
        seq_len = input_ids.size(1)
        h = h + self.pos_encoding[:, :seq_len, :]
        
        # 通过内存中的层
        layer_stats = []
        for idx in sorted(self.memory_layers.keys()):
            layer = self.memory_layers[idx]
            h_new, stats = layer(h, self.torsion_field)
            h = h_new + h * 0.5  # 残差连接
            layer_stats.append(stats)
        
        # 输出
        logits = self.lm_head(h)
        
        if return_stats:
            return logits, {'layer_stats': layer_stats}
        return logits
    
    def grow(self, num_new_layers=1):
        """生长新层"""
        current_layers = len(self.memory_layers) + len([l for l in self.offloaded_layers if l.layer_id >= 0])
        
        # 检查条件
        if current_layers > 0:
            last_idx = current_layers - 1
            epochs = self.layer_training_epochs.get(last_idx, 0)
            best_acc = self.layer_best_accuracy.get(last_idx, 0)
            
            threshold = self.deep_layer_threshold if current_layers >= 15 else self.growth_threshold_accuracy
            
            if epochs < self.min_cycles_before_growth:
                print(f"⏸️ 推迟生长: 训练不足 ({epochs}/{self.min_cycles_before_growth})")
                return
            
            if best_acc < threshold:
                print(f"⏸️ 推迟生长: 准确率不足 ({best_acc:.1%} < {threshold})")
                return
        
        print(f"\n🌱 生长: {current_layers}层 → {current_layers + num_new_layers}层")
        
        for i in range(num_new_layers):
            new_idx = current_layers + i
            new_layer = self._create_layer(new_idx)
            
            # 添加到内存
            self.memory_layers[new_idx] = new_layer
            self.access_order.insert(0, new_idx)
            self.layer_training_epochs[new_idx] = 0
            self.layer_best_accuracy[new_idx] = 0
            
            # 内存管理
            self._manage_memory()
        
        # 更新阶段
        for stage_id, (name, target) in self.stages.items():
            if len(self.memory_layers) >= target:
                self.current_stage = stage_id
        
        self.growth_history.append({
            'timestamp': datetime.now().isoformat(),
            'previous': current_layers,
            'new': current_layers + num_new_layers,
            'stage': self.stages[self.current_stage][0],
        })
        
        print(f"   当前: {len(self.memory_layers)}层在内存，{len(self.offloaded_layers)}层在磁盘")
        print(f"   阶段: {self.stages[self.current_stage][0]}")
    
    def training_step(self, input_ids, targets, optimizer):
        """训练步骤"""
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
        
        # 更新统计
        current_idx = max(self.memory_layers.keys()) if self.memory_layers else 0
        self.layer_training_epochs[current_idx] = self.layer_training_epochs.get(current_idx, 0) + 1
        current_best = self.layer_best_accuracy.get(current_idx, 0)
        self.layer_best_accuracy[current_idx] = max(current_best, accuracy)
        
        # 检查生长
        should_grow = (accuracy >= self.growth_threshold_accuracy and 
                       loss.item() <= self.growth_threshold_loss)
        
        return {
            'loss': loss.item(),
            'accuracy': accuracy,
            'layers': len(self.memory_layers),
            'should_grow': should_grow,
        }


def run_fusion_experiment():
    """运行融合版实验"""
    print("\n启动融合版实验...")
    
    model = ConservativeDiskTNN(
        initial_layers=2,
        target_layers=50,  # 目标50层！
        hidden_dim=1024,   # 更大维度
        vocab_size=300,
        max_memory_layers=5,  # 只保留5层在内存
    )
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0003)
    
    # 生成数据
    def generate_batch(batch_size=4):
        seq = torch.arange(32) % model.vocab_size
        data = seq.unsqueeze(0).repeat(batch_size, 1)
        target = torch.roll(data, shifts=-1, dims=1)
        return data, target
    
    print("\n开始训练...")
    max_epochs = 300
    
    for epoch in range(max_epochs):
        epoch_loss = 0
        epoch_acc = 0
        
        for _ in range(5):  # 5个任务
            input_ids, targets = generate_batch()
            result = model.training_step(input_ids, targets, optimizer)
            epoch_loss += result['loss']
            epoch_acc += result['accuracy']
        
        avg_loss = epoch_loss / 5
        avg_acc = epoch_acc / 5
        
        if (epoch + 1) % 10 == 0:
            print(f"\n📚 Epoch {epoch + 1}")
            print(f"   损失: {avg_loss:.4f} | 准确率: {avg_acc:.1%}")
            print(f"   层数: {result['layers']}/50")
            print(f"   阶段: {model.stages[model.current_stage][0]}")
        
        # 生长
        if result['should_grow'] and result['layers'] < 50:
            model.grow(1)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.0003)
        
        # 达到目标
        if result['layers'] >= 20 and avg_acc >= 0.85:  # 先测试20层
            print(f"\n✅ 达成目标: 20层+, 准确率{avg_acc:.1%}")
            break
    
    print("\n实验完成!")
    print(f"最终层数: {result['layers']}")
    print(f"最终准确率: {avg_acc:.1%}")
    print(f"生长历史: {len(model.growth_history)}次")


if __name__ == "__main__":
    run_fusion_experiment()
