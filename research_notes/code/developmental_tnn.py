"""
发育式TNN (GrowingTNN) - 渐进生长架构
从胚胎级开始，逐步发育到更复杂阶段

核心特性：
- 谱维随"年龄"动态解锁
- 模块化添加（条件触发）
- 突触过度生长+修剪
- 实时发育监控
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import json
import time


class DevelopmentalStage(Enum):
    """发育阶段"""
    EMBRYO = "embryo"      # 胚胎：反射级
    INFANT = "infant"      # 婴儿：感知级
    CHILD = "child"        # 儿童：序列学习
    ADOLESCENT = "adolescent"  # 青春期：抽象思维
    ADULT = "adult"        # 成人：融合级


@dataclass
class GrowthConfig:
    """生长配置"""
    # 当前阶段
    stage: DevelopmentalStage = DevelopmentalStage.EMBRYO
    
    # 年龄（训练步数）
    age: int = 0
    
    # 发育阈值
    embryo_to_infant_steps: int = 1000
    infant_to_child_steps: int = 5000
    child_to_adolescent_accuracy: float = 0.7
    adolescent_to_adult_complexity: float = 5.0
    
    # 当前架构参数（随生长动态变化）
    layers: int = 2
    internal_dim: int = 16
    spectral_dim: float = 2.5
    torsion_order: int = 1
    torsion_rank: int = 8
    
    # 可解锁能力
    has_memory: bool = False
    has_language: bool = False
    has_social: bool = False
    
    # 发育指标
    survival_rate: float = 0.0
    prediction_accuracy: float = 0.0
    memory_capacity: float = 0.0
    
    def to_dict(self):
        return {
            'stage': self.stage.value,
            'age': self.age,
            'layers': self.layers,
            'internal_dim': self.internal_dim,
            'spectral_dim': self.spectral_dim,
            'torsion_order': self.torsion_order,
            'torsion_rank': self.torsion_rank,
            'has_memory': self.has_memory,
            'has_language': self.has_language,
            'has_social': self.has_social,
            'survival_rate': self.survival_rate,
            'prediction_accuracy': self.prediction_accuracy,
            'memory_capacity': self.memory_capacity,
        }


class GrowingTorsionField(nn.Module):
    """可生长的扭转场 - 简化版"""
    
    def __init__(self, input_dim: int = 64, initial_rank: int = 8, max_rank: int = 32):
        super().__init__()
        self.input_dim = input_dim
        self.current_rank = initial_rank
        self.max_rank = max_rank
        self.torsion_order = 1
        
        # 使用简单的线性层实现扭转效果
        # A: input -> rank, B: rank -> input
        self.torsion_a = nn.Linear(input_dim, max_rank, bias=False)
        self.torsion_b = nn.Linear(max_rank, input_dim, bias=False)
        
        # 初始化时限制有效秩
        with torch.no_grad():
            self.torsion_a.weight[initial_rank:].zero_()
            self.torsion_b.weight[:, initial_rank:].zero_()
        
        self.coupling = nn.Parameter(torch.tensor(0.1))
    
    def grow(self, new_rank: int):
        """扩展扭转场秩"""
        if new_rank > self.max_rank:
            new_rank = self.max_rank
        if new_rank <= self.current_rank:
            return
        
        # 初始化新扩展的部分
        with torch.no_grad():
            # 保持已有权重，初始化新部分
            self.torsion_a.weight[self.current_rank:new_rank].normal_(0, 0.01)
            self.torsion_b.weight[:, self.current_rank:new_rank].normal_(0, 0.01)
        
        self.current_rank = new_rank
    
    def prune(self, threshold: float = 0.01):
        """修剪弱连接"""
        with torch.no_grad():
            # 减弱小权重
            weak_mask = torch.abs(self.torsion_a.weight[:self.current_rank]) < threshold
            self.torsion_a.weight[:self.current_rank][weak_mask] *= 0.5
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        # 手动实现低秩投影，只使用current_rank
        # x: [..., input_dim]
        # torsion_a.weight: [max_rank, input_dim]
        # 只取前current_rank行
        low_dim = F.linear(x, self.torsion_a.weight[:self.current_rank], 
                          self.torsion_a.bias[:self.current_rank] if self.torsion_a.bias is not None else None)
        
        # torsion_b.weight: [input_dim, max_rank]
        # 只取前current_rank列
        out = F.linear(low_dim, self.torsion_b.weight[:, :self.current_rank], self.torsion_b.bias)
        
        # 应用扭转（非线性相位）
        phase = 2 * 3.14159 * out
        twisted = torch.sin(phase) * out
        
        coupling = torch.sigmoid(self.coupling)
        return x + coupling * twisted


class GrowingInternalSpace(nn.Module):
    """可生长的内部空间"""
    
    def __init__(self, initial_dim: int = 16, max_dim: int = 128):
        super().__init__()
        self.current_dim = initial_dim
        self.max_dim = max_dim
        
        # 变换层：输入64维 -> max_dim维
        self.transform = nn.Linear(64, max_dim)
        
        # 使用GroupNorm代替LayerNorm，支持动态维度
        self.norm = nn.GroupNorm(num_groups=1, num_channels=max_dim)
        
        # 初始化时限制有效部分
        with torch.no_grad():
            self.transform.weight[initial_dim:, :].zero_()
            self.transform.bias[initial_dim:].zero_()
    
    def grow(self, new_dim: int):
        """扩展内部空间"""
        if new_dim > self.max_dim:
            new_dim = self.max_dim
        if new_dim <= self.current_dim:
            return
        
        # 初始化新维度
        with torch.no_grad():
            self.transform.weight[self.current_dim:new_dim, :].normal_(0, 0.01)
            self.transform.bias[self.current_dim:new_dim].normal_(0, 0.01)
        
        self.current_dim = new_dim
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        # x: [batch, seq, 64]
        # 变换到内部空间
        out = self.transform(x)  # [batch, seq, max_dim]
        
        # 只取当前维度并填充回
        out_current = out[..., :self.current_dim]
        if self.current_dim < self.max_dim:
            padding = torch.zeros(*out.shape[:-1], self.max_dim - self.current_dim, 
                                 device=out.device, dtype=out.dtype)
            out_padded = torch.cat([out_current, padding], dim=-1)
        else:
            out_padded = out_current
        
        # GroupNorm需要 [N, C, *] 或 [N, C]
        # 我们需要调整形状
        original_shape = out_padded.shape
        # [batch, seq, max_dim] -> [batch*seq, max_dim, 1]
        out_reshaped = out_padded.reshape(-1, self.max_dim, 1)
        out_normed = self.norm(out_reshaped)
        out_normed = out_normed.reshape(original_shape)
        
        # 返回前current_dim部分
        return out_normed[..., :self.current_dim]


class SpectralDimensionManager(nn.Module):
    """谱维管理器 - 随年龄解锁"""
    
    def __init__(self, initial_d_s: float = 2.5, max_d_s: float = 6.0):
        super().__init__()
        self.current_d_s = nn.Parameter(torch.tensor(initial_d_s))
        self.min_d_s = initial_d_s
        self.max_d_s = max_d_s
        self.unlocked_max = initial_d_s  # 当前解锁的最大值
        self.age = 0
    
    def unlock(self, new_max: float):
        """解锁更高谱维"""
        self.unlocked_max = min(new_max, self.max_d_s)
    
    def update(self, complexity: float, age: int):
        """根据复杂度和年龄更新"""
        self.age = age
        
        # 目标谱维基于输入复杂度
        target = self.min_d_s + complexity * (self.unlocked_max - self.min_d_s)
        
        # 平滑过渡
        delta = 0.01 * (target - self.current_d_s)
        self.current_d_s.data += delta
        self.current_d_s.data.clamp_(self.min_d_s, self.unlocked_max)
    
    def get_scale(self) -> float:
        """获取深度缩放因子"""
        return self.current_d_s.item() / 4.0


class GrowingTNN(nn.Module):
    """发育式TNN主模型"""
    
    def __init__(self, vocab_size: int = 100, max_seq_len: int = 64):
        super().__init__()
        self.config = GrowthConfig()
        self.vocab_size = vocab_size
        self.max_seq_len = max_seq_len
        
        # 嵌入层（固定大小）
        self.embedding = nn.Embedding(vocab_size, 64)
        self.pos_embedding = nn.Embedding(max_seq_len, 64)
        
        # 可生长组件
        self.torsion_field = GrowingTorsionField(initial_rank=8, max_rank=32)
        self.internal_space = GrowingInternalSpace(initial_dim=16, max_dim=128)
        self.spectral_manager = SpectralDimensionManager(initial_d_s=2.5, max_d_s=6.0)
        
        # 当前层（从2层开始）
        self.layers = nn.ModuleList([
            self._create_layer() for _ in range(2)
        ])
        
        # 输出头
        self.output_proj = nn.Linear(64, vocab_size)
        
        # 发育历史
        self.growth_history = []
    
    def _create_layer(self):
        """创建一个新层"""
        return nn.ModuleDict({
            'attention': nn.Linear(64, 64),
            'torsion': GrowingTorsionField(input_dim=64, initial_rank=self.config.torsion_rank),
            'internal_coupling': nn.Linear(64, self.config.internal_dim),
            'norm1': nn.LayerNorm(64),
            'norm2': nn.LayerNorm(64),
        })
    
    def check_development(self, metrics: Dict[str, float]) -> Optional[str]:
        """检查是否需要发育到下一阶段"""
        self.config.age += 1
        
        # 更新指标
        if 'accuracy' in metrics:
            self.config.prediction_accuracy = metrics['accuracy']
        if 'survival' in metrics:
            self.config.survival_rate = metrics['survival']
        
        # 检查发育条件
        if self.config.stage == DevelopmentalStage.EMBRYO:
            if self.config.age >= self.config.embryo_to_infant_steps:
                return self._grow_to_infant()
        
        elif self.config.stage == DevelopmentalStage.INFANT:
            if self.config.age >= self.config.infant_to_child_steps:
                return self._grow_to_child()
        
        elif self.config.stage == DevelopmentalStage.CHILD:
            if self.config.prediction_accuracy >= self.config.child_to_adolescent_accuracy:
                return self._grow_to_adolescent()
        
        # 谱维随年龄逐渐解锁
        self._unlock_spectral_dimension()
        
        return None
    
    def _grow_to_infant(self) -> str:
        """发育到婴儿阶段"""
        self.config.stage = DevelopmentalStage.INFANT
        self.config.layers = 3
        self.config.internal_dim = 24
        self.config.torsion_rank = 12
        self.config.torsion_order = 2
        
        # 添加新层
        self.layers.append(self._create_layer())
        
        # 扩展内部空间
        self.internal_space.grow(24)
        
        # 扩展扭转场
        self.torsion_field.grow(12)
        
        # 解锁谱维
        self.spectral_manager.unlock(3.5)
        
        msg = f"🌱 发育到婴儿阶段! 年龄:{self.config.age}, 层数:3, 内部维度:24"
        self.growth_history.append(msg)
        return msg
    
    def _grow_to_child(self) -> str:
        """发育到儿童阶段"""
        self.config.stage = DevelopmentalStage.CHILD
        self.config.layers = 4
        self.config.internal_dim = 32
        self.config.torsion_rank = 16
        self.config.has_memory = True
        
        # 添加记忆模块
        self.memory = nn.GRUCell(64, 32)
        
        # 添加新层
        self.layers.append(self._create_layer())
        
        # 扩展
        self.internal_space.grow(32)
        self.torsion_field.grow(16)
        self.spectral_manager.unlock(4.5)
        
        msg = f"🌿 发育到儿童阶段! 年龄:{self.config.age}, 层数:4, 解锁记忆模块"
        self.growth_history.append(msg)
        return msg
    
    def _grow_to_adolescent(self) -> str:
        """发育到青春期"""
        self.config.stage = DevelopmentalStage.ADOLESCENT
        self.config.layers = 6
        self.config.internal_dim = 48
        self.config.torsion_rank = 20
        self.config.torsion_order = 3
        self.config.has_language = True
        
        # 添加更多层
        for _ in range(2):
            self.layers.append(self._create_layer())
        
        # 扩展
        self.internal_space.grow(48)
        self.torsion_field.grow(20)
        self.spectral_manager.unlock(5.5)
        
        msg = f"🌳 发育到青春期! 年龄:{self.config.age}, 层数:6, 解锁语言能力"
        self.growth_history.append(msg)
        return msg
    
    def _unlock_spectral_dimension(self):
        """根据年龄逐步解锁谱维"""
        if self.config.age < 1000:
            self.spectral_manager.unlock(2.5)
        elif self.config.age < 5000:
            self.spectral_manager.unlock(3.0 + (self.config.age - 1000) / 4000 * 0.5)
        elif self.config.age < 20000:
            self.spectral_manager.unlock(3.5 + (self.config.age - 5000) / 15000 * 1.0)
        else:
            self.spectral_manager.unlock(5.5)
    
    def forward(self, input_ids: torch.Tensor, 
                labels: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        """前向传播"""
        batch_size, seq_len = input_ids.shape
        device = input_ids.device
        
        # 嵌入
        positions = torch.arange(seq_len, device=device).unsqueeze(0)
        x = self.embedding(input_ids) + self.pos_embedding(positions)
        
        # 更新谱维
        complexity = torch.rand(1).item()  # 简化：随机复杂度
        self.spectral_manager.update(complexity, self.config.age)
        depth_scale = self.spectral_manager.get_scale()
        
        # Transformer层
        for layer in self.layers:
            # 注意力 + 扭转
            residual = x
            x = layer['norm1'](x)
            attn_out = layer['attention'](x)
            
            # 应用扭转场
            twisted = layer['torsion'](x)
            
            x = residual + attn_out + twisted * depth_scale
            
            # 内部空间处理
            residual = x
            x = layer['norm2'](x)
            internal = layer['internal_coupling'](x)
            # internal: [batch, seq, internal_dim]
            # 需要处理internal_space的输入
            if internal.shape[-1] != 64:
                # 投影到64维供internal_space处理
                internal_proj = torch.zeros(*internal.shape[:-1], 64, device=internal.device)
                internal_proj[..., :min(64, internal.shape[-1])] = internal[..., :min(64, internal.shape[-1])]
            else:
                internal_proj = internal
            
            internal_processed = self.internal_space(internal_proj)
            # 投影回64维
            if internal_processed.shape[-1] != 64:
                internal_out = torch.zeros(*internal_processed.shape[:-1], 64, device=internal_processed.device)
                internal_out[..., :min(64, internal_processed.shape[-1])] = internal_processed[..., :min(64, internal_processed.shape[-1])]
            else:
                internal_out = internal_processed
            
            x = residual + internal_out
        
        # 输出
        logits = self.output_proj(x)
        
        # 计算损失
        loss = None
        if labels is not None:
            loss = F.cross_entropy(
                logits.view(-1, self.vocab_size),
                labels.view(-1)
            )
        
        return {
            'loss': loss,
            'logits': logits,
            'spectral_dim': self.spectral_manager.current_d_s.item(),
            'stage': self.config.stage.value,
            'age': self.config.age,
        }
    
    def get_info(self) -> Dict:
        """获取当前发育信息"""
        return {
            'stage': self.config.stage.value,
            'age': self.config.age,
            'layers': len(self.layers),
            'internal_dim': self.internal_space.current_dim,
            'spectral_dim': round(self.spectral_manager.current_d_s.item(), 2),
            'torsion_rank': self.torsion_field.current_rank,
            'parameters': sum(p.numel() for p in self.parameters()),
            'growth_history': self.growth_history,
        }


# =============================================================================
# 训练与发育实验
# =============================================================================

def run_developmental_experiment(num_steps: int = 10000):
    """运行发育实验"""
    print("="*60)
    print("发育式TNN实验")
    print("="*60)
    
    # 创建模型
    model = GrowingTNN(vocab_size=50, max_seq_len=32)
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # 训练历史
    history = []
    
    print(f"\n初始状态:")
    info = model.get_info()
    print(f"  阶段: {info['stage']}")
    print(f"  层数: {info['layers']}")
    print(f"  参数量: {info['parameters']:,}")
    print(f"  谱维: {info['spectral_dim']}")
    
    print(f"\n开始训练 {num_steps} 步...")
    print("-"*60)
    
    for step in range(num_steps):
        # 生成简单序列数据（递增）
        batch_size = 8
        seq_len = 16
        
        # 简单模式：重复序列
        input_ids = torch.randint(0, 50, (batch_size, seq_len))
        labels = input_ids.clone()
        
        # 前向
        outputs = model(input_ids, labels=labels)
        loss = outputs['loss']
        
        # 反向
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # 计算准确率
        with torch.no_grad():
            preds = outputs['logits'].argmax(dim=-1)
            acc = (preds == labels).float().mean().item()
        
        # 检查发育
        growth_msg = model.check_development({'accuracy': acc})
        
        # 记录
        if step % 500 == 0 or growth_msg:
            info = model.get_info()
            log = {
                'step': step,
                'loss': loss.item(),
                'accuracy': acc,
                'stage': info['stage'],
                'spectral_dim': info['spectral_dim'],
                'parameters': info['parameters'],
            }
            history.append(log)
            
            status = f"Step {step:5d} | Loss: {loss.item():.4f} | Acc: {acc:.3f} | "
            status += f"Stage: {info['stage']:12s} | d_s: {info['spectral_dim']:.2f} | "
            status += f"Params: {info['parameters']:,}"
            print(status)
            
            if growth_msg:
                print(f"  🌟 {growth_msg}")
    
    # 最终状态
    print("-"*60)
    print(f"\n最终状态:")
    info = model.get_info()
    print(f"  阶段: {info['stage']}")
    print(f"  年龄: {info['age']}")
    print(f"  层数: {info['layers']}")
    print(f"  内部维度: {info['internal_dim']}")
    print(f"  谱维: {info['spectral_dim']}")
    print(f"  参数量: {info['parameters']:,}")
    print(f"  生长历史:")
    for msg in info['growth_history']:
        print(f"    - {msg}")
    
    return model, history


if __name__ == "__main__":
    model, history = run_developmental_experiment(num_steps=8000)
    
    # 保存结果
    import json
    with open('developmental_tnn_results.json', 'w') as f:
        json.dump(history, f, indent=2)
    
    print("\n结果已保存到 developmental_tnn_results.json")
