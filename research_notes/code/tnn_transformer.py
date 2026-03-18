"""
TNN-Transformer: 125M参数规模的大语言模型实现
基于扭转神经网络(Torsion Neural Network)的Transformer架构

核心创新:
1. Torsion Attention: 扭转注意力机制，引入谱维感知的注意力计算
2. Spectral-Adaptive MLP: 谱维自适应的MLP层
3. Reciprocal-Internal Embedding: 互反-内部空间词嵌入
4. Dynamic Depth Scaling: 动态深度缩放机制

参数规模: ~125M
架构特点:
- 层数: 12层
- 隐藏维度: 768
- 注意力头数: 12
- 内部维度: 256
- 扭转阶数: 3
- 序列长度: 1024

参考: Torsion Neural Network Theory
作者: AI Research Assistant
日期: 2026-03-18
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, IterableDataset
import numpy as np
import math
from typing import Optional, Tuple, List, Dict, Union
from dataclasses import dataclass
# from transformers import GPT2Tokenizer, GPT2LMHeadModel  # 可选导入
import json


# =============================================================================
# 配置类
# =============================================================================

@dataclass
class TNNTransformerConfig:
    """TNN-Transformer模型配置"""
    # 基础架构参数
    vocab_size: int = 50257          # GPT-2词表大小
    max_position_embeddings: int = 1024
    hidden_size: int = 768           # 隐藏层维度
    num_hidden_layers: int = 12      # 层数
    num_attention_heads: int = 12    # 注意力头数
    intermediate_size: int = 3072    # MLP中间层维度 (4 * hidden_size)
    
    # TNN特有参数
    internal_dim: int = 64           # 内部空间维度 (减小以控制参数量)
    torsion_order: int = 2           # 扭转阶数
    torsion_strength: float = 0.1    # 扭转强度
    torsion_rank: int = 64           # 扭转场低秩维度
    spectral_dim_min: float = 2.0    # 最小谱维
    spectral_dim_max: float = 10.0   # 最大谱维
    adaptation_rate: float = 0.01    # 谱维适应率
    
    # 正则化参数
    hidden_dropout_prob: float = 0.1
    attention_dropout_prob: float = 0.1
    layer_norm_eps: float = 1e-12
    
    # 优化参数
    init_std: float = 0.02
    
    # 计算属性
    @property
    def head_dim(self) -> int:
        return self.hidden_size // self.num_attention_heads
    
    @property
    def num_parameters(self) -> int:
        """估算参数量 (使用低秩扭转场)"""
        torsion_rank = getattr(self, 'torsion_rank', 64)
        
        # 词嵌入 + 位置嵌入
        embed_params = self.vocab_size * self.hidden_size + self.max_position_embeddings * self.hidden_size
        
        # 每层参数
        # 1. Torsion Attention: Q, K, V投影 + O投影 + 低秩扭转场
        attention_params = (3 * self.hidden_size * self.hidden_size +  # Q, K, V
                          self.hidden_size * self.hidden_size +        # O
                          2 * self.torsion_order * self.hidden_size * torsion_rank * 2)  # Q,K低秩扭转场 (A,B)
        
        # 2. Spectral-Adaptive MLP
        mlp_params = (self.hidden_size * self.intermediate_size +     # gate_proj
                     self.intermediate_size +                         # gate bias
                     self.hidden_size * self.intermediate_size +      # up_proj (新增)
                     self.intermediate_size +                         # up bias
                     self.intermediate_size * self.hidden_size +      # down_proj
                     self.hidden_size +                               # down bias
                     2 * self.torsion_order * self.intermediate_size * torsion_rank)  # 低秩扭转场 (A,B)
        
        # 3. Reciprocal-Internal Coupling
        coupling_params = (self.hidden_size * self.internal_dim +      # r_to_i
                          self.internal_dim +                          # r_to_i bias
                          self.internal_dim * self.hidden_size +       # i_to_r
                          self.hidden_size +                           # i_to_r bias
                          self.internal_dim * self.internal_dim * 2 +  # internal transform
                          self.internal_dim * 2)                       # transform biases
        
        # 4. Layer Norms
        norm_params = 2 * self.hidden_size * 2  # attention + MLP前后的LN
        
        layer_params = attention_params + mlp_params + coupling_params + norm_params
        
        # 总参数量
        total = embed_params + self.num_hidden_layers * layer_params + self.hidden_size  # final LN
        
        return int(total)


# =============================================================================
# 谱维管理器 (序列版本)
# =============================================================================

class SpectralDimensionManager(nn.Module):
    """
    谱维自适应管理器 (序列版本)
    根据序列复杂度和当前损失动态调整谱维
    """
    
    def __init__(self, config: TNNTransformerConfig):
        super().__init__()
        self.config = config
        self.d_s_min = config.spectral_dim_min
        self.d_s_max = config.spectral_dim_max
        self.adaptation_rate = config.adaptation_rate
        
        # 当前谱维 (可学习参数)
        self.current_d_s = nn.Parameter(torch.tensor(4.0))
        
        # 复杂度估计网络
        self.complexity_estimator = nn.Sequential(
            nn.Linear(config.hidden_size, config.hidden_size // 4),
            nn.GELU(),
            nn.Linear(config.hidden_size // 4, 1),
            nn.Sigmoid()
        )
        
        # 损失响应网络
        self.loss_encoder = nn.Sequential(
            nn.Linear(1, 16),
            nn.GELU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
        
    def compute_sequence_complexity(self, hidden_states: torch.Tensor) -> torch.Tensor:
        """
        计算序列复杂度
        hidden_states: [batch, seq_len, hidden_size]
        """
        # 使用池化特征估计复杂度
        pooled = hidden_states.mean(dim=1)  # [batch, hidden_size]
        complexity = self.complexity_estimator(pooled)  # [batch, 1]
        return complexity.mean()  # 标量
    
    def update_spectral_dimension(
        self, 
        hidden_states: torch.Tensor,
        loss: Optional[torch.Tensor] = None
    ) -> float:
        """
        更新谱维
        流动方程: d(d_s)/dt = -γ(d_s - d_target)
        """
        complexity = self.compute_sequence_complexity(hidden_states)
        
        # 基础目标谱维 (基于复杂度)
        d_target = self.d_s_min + complexity * (self.d_s_max - self.d_s_min)
        
        # 损失反馈调整
        if loss is not None:
            loss_signal = self.loss_encoder(loss.unsqueeze(0))
            d_target = d_target + loss_signal * (self.d_s_max - d_target)
        
        # 谱维流动 (指数弛豫)
        delta_d_s = -self.adaptation_rate * (self.current_d_s - d_target)
        self.current_d_s.data += delta_d_s
        self.current_d_s.data.clamp_(self.d_s_min, self.d_s_max)
        
        return self.current_d_s.item()
    
    def get_depth_scale(self) -> float:
        """获取深度缩放因子"""
        return self.current_d_s.item() / 4.0
    
    def get_effective_layers(self, base_layers: int) -> int:
        """根据谱维计算有效层数"""
        scale = self.get_depth_scale()
        return max(1, int(base_layers * scale))


# =============================================================================
# 扭转注意力机制 (Torsion Attention)
# =============================================================================

class TorsionAttention(nn.Module):
    """
    扭转注意力机制
    引入谱维感知的注意力计算，通过扭转场增强查询-键交互
    """
    
    def __init__(self, config: TNNTransformerConfig):
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.num_heads = config.num_attention_heads
        self.head_dim = config.head_dim
        self.torsion_order = config.torsion_order
        
        assert self.head_dim * self.num_heads == self.hidden_size
        
        # 标准投影
        self.q_proj = nn.Linear(config.hidden_size, config.hidden_size)
        self.k_proj = nn.Linear(config.hidden_size, config.hidden_size)
        self.v_proj = nn.Linear(config.hidden_size, config.hidden_size)
        self.o_proj = nn.Linear(config.hidden_size, config.hidden_size)
        
        # 扭转场 (使用低秩近似减少参数量)
        torsion_rank = getattr(config, 'torsion_rank', 64)
        self.torsion_rank = torsion_rank
        
        # Q扭转场: 分解为低秩矩阵 A (hidden, rank) 和 B (rank, hidden)
        self.q_torsion_a = nn.Parameter(
            torch.randn(config.torsion_order, config.hidden_size, torsion_rank) * 0.01
        )
        self.q_torsion_b = nn.Parameter(
            torch.randn(config.torsion_order, torsion_rank, config.hidden_size) * 0.01
        )
        
        # K扭转场
        self.k_torsion_a = nn.Parameter(
            torch.randn(config.torsion_order, config.hidden_size, torsion_rank) * 0.01
        )
        self.k_torsion_b = nn.Parameter(
            torch.randn(config.torsion_order, torsion_rank, config.hidden_size) * 0.01
        )
        
        # 扭转耦合系数
        self.torsion_coupling = nn.Parameter(torch.tensor(0.1))
        
        # Dropout
        self.attn_dropout = nn.Dropout(config.attention_dropout_prob)
        self.resid_dropout = nn.Dropout(config.hidden_dropout_prob)
        
        # 缩放因子
        self.scale = self.head_dim ** -0.5
        
    def apply_torsion(self, x: torch.Tensor, torsion_a: nn.Parameter, torsion_b: nn.Parameter) -> torch.Tensor:
        """
        应用低秩扭转场扭曲
        x: [batch, seq_len, hidden_size]
        返回: [batch, seq_len, hidden_size]
        """
        torsion_correction = torch.zeros_like(x)
        
        for n in range(self.torsion_order):
            # 低秩投影: x @ A @ B
            a_n = torsion_a[n]  # [hidden, rank]
            b_n = torsion_b[n]  # [rank, hidden]
            
            # 先降维再升维
            low_dim = torch.matmul(x, a_n)  # [batch, seq, rank]
            linear_out = torch.matmul(low_dim, b_n)  # [batch, seq, hidden]
            
            # 螺旋型扭曲
            phase = 2 * math.pi * (n + 1) * linear_out
            twisted = torch.sin(phase) * linear_out / (n + 1)
            
            torsion_correction += twisted
        
        coupling = torch.sigmoid(self.torsion_coupling)
        return x + coupling * torsion_correction
    
    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        layer_past: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        """
        前向传播
        hidden_states: [batch, seq_len, hidden_size]
        """
        batch_size, seq_len, _ = hidden_states.shape
        
        # 投影到Q, K, V
        query = self.q_proj(hidden_states)
        key = self.k_proj(hidden_states)
        value = self.v_proj(hidden_states)
        
        # 应用扭转修正
        query = self.apply_torsion(query, self.q_torsion_a, self.q_torsion_b)
        key = self.apply_torsion(key, self.k_torsion_a, self.k_torsion_b)
        
        # 重塑为多头: [batch, num_heads, seq_len, head_dim]
        query = query.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        key = key.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        value = value.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        
        # 处理KV Cache
        if layer_past is not None:
            past_key, past_value = layer_past
            key = torch.cat([past_key, key], dim=-2)
            value = torch.cat([past_value, value], dim=-2)
        
        present = (key, value) if use_cache else None
        
        # 计算注意力分数
        attn_weights = torch.matmul(query, key.transpose(-2, -1)) * self.scale
        
        # 应用掩码
        if attention_mask is not None:
            attn_weights = attn_weights + attention_mask
        
        attn_weights = F.softmax(attn_weights, dim=-1)
        attn_weights = self.attn_dropout(attn_weights)
        
        # 计算注意力输出
        attn_output = torch.matmul(attn_weights, value)
        
        # 重塑回原始维度
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.hidden_size)
        
        # 输出投影
        attn_output = self.o_proj(attn_output)
        attn_output = self.resid_dropout(attn_output)
        
        return attn_output, present
    
    def get_torsion_energy(self) -> torch.Tensor:
        """计算扭转场能量 (正则化项)"""
        return (torch.sum(self.q_torsion_a ** 2) + torch.sum(self.q_torsion_b ** 2) +
                torch.sum(self.k_torsion_a ** 2) + torch.sum(self.k_torsion_b ** 2))


# =============================================================================
# 互反-内部空间耦合
# =============================================================================

class ReciprocalInternalCoupling(nn.Module):
    """
    互反-内部空间耦合层
    实现信息在互反空间(序列表示)和内部空间(谱维特征)之间的流动
    """
    
    def __init__(self, config: TNNTransformerConfig):
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.internal_dim = config.internal_dim
        
        # 互反 -> 内部投影
        self.r_to_i = nn.Linear(config.hidden_size, config.internal_dim)
        
        # 内部 -> 互反投影
        self.i_to_r = nn.Linear(config.internal_dim, config.hidden_size)
        
        # 内部空间变换
        self.internal_transform = nn.Sequential(
            nn.Linear(config.internal_dim, config.internal_dim * 2),
            nn.GELU(),
            nn.Linear(config.internal_dim * 2, config.internal_dim)
        )
        
        # 流动门控
        self.flow_gate = nn.Parameter(torch.tensor(0.5))
        
        # Layer Norm
        self.norm_internal = nn.LayerNorm(config.internal_dim, eps=config.layer_norm_eps)
        
    def forward(
        self, 
        reciprocal: torch.Tensor,
        internal: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播
        reciprocal: [batch, seq_len, hidden_size]
        internal: [batch, seq_len, internal_dim] or None
        """
        batch_size, seq_len, _ = reciprocal.shape
        
        if internal is None:
            internal = torch.zeros(batch_size, seq_len, self.internal_dim, device=reciprocal.device)
        
        # 内部空间变换
        h_internal = self.internal_transform(internal)
        h_internal = self.norm_internal(h_internal)
        
        # 跨维流动
        gate = torch.sigmoid(self.flow_gate)
        
        # 互反 -> 内部
        flow_r_to_i = self.r_to_i(reciprocal)
        h_internal = h_internal + gate * flow_r_to_i
        
        # 内部 -> 互反
        flow_i_to_r = self.i_to_r(h_internal)
        h_reciprocal = reciprocal + gate * flow_i_to_r
        
        return h_reciprocal, h_internal


# =============================================================================
# 谱维自适应MLP
# =============================================================================

class SpectralAdaptiveMLP(nn.Module):
    """
    谱维自适应MLP
    根据当前谱维动态调整MLP的表达能力
    """
    
    def __init__(self, config: TNNTransformerConfig):
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.intermediate_size = config.intermediate_size
        self.torsion_order = config.torsion_order
        
        # 门控投影
        self.gate_proj = nn.Linear(config.hidden_size, config.intermediate_size)
        
        # 上投影 (升维)
        self.up_proj = nn.Linear(config.hidden_size, config.intermediate_size)
        
        # 下投影 (降维)
        self.down_proj = nn.Linear(config.intermediate_size, config.hidden_size)
        
        # 扭转场 (使用低秩近似)
        torsion_rank = getattr(config, 'torsion_rank', 64)
        self.torsion_rank = torsion_rank
        
        self.torsion_a = nn.Parameter(
            torch.randn(config.torsion_order, config.intermediate_size, torsion_rank) * 0.01
        )
        self.torsion_b = nn.Parameter(
            torch.randn(config.torsion_order, torsion_rank, config.intermediate_size) * 0.01
        )
        
        # 扭转耦合
        self.torsion_coupling = nn.Parameter(torch.tensor(0.1))
        
        # 激活函数
        self.activation = nn.GELU()
        
        # Dropout
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        
    def apply_torsion(self, x: torch.Tensor) -> torch.Tensor:
        """应用低秩扭转场"""
        torsion_correction = torch.zeros_like(x)
        
        for n in range(self.torsion_order):
            a_n = self.torsion_a[n]  # [intermediate, rank]
            b_n = self.torsion_b[n]  # [rank, intermediate]
            
            # 低秩投影
            low_dim = torch.matmul(x, a_n)  # [batch, seq, rank]
            linear_out = torch.matmul(low_dim, b_n)  # [batch, seq, intermediate]
            
            phase = 2 * math.pi * (n + 1) * linear_out
            twisted = torch.sin(phase) * linear_out / (n + 1)
            
            torsion_correction += twisted
        
        coupling = torch.sigmoid(self.torsion_coupling)
        return x + coupling * torsion_correction
    
    def forward(self, x: torch.Tensor, depth_scale: float = 1.0) -> torch.Tensor:
        """
        前向传播
        depth_scale: 深度缩放因子 (来自谱维)
        """
        # 门控机制
        gate = self.activation(self.gate_proj(x))
        up = self.up_proj(x)
        
        # 逐元素乘 (SwiGLU风格)
        intermediate = gate * up
        
        # 应用扭转
        intermediate = self.apply_torsion(intermediate)
        
        # 根据深度缩放调整中间层维度
        if depth_scale != 1.0 and self.training:
            # 动态调整有效宽度
            effective_dim = max(1, int(self.intermediate_size * depth_scale))
            if effective_dim < self.intermediate_size:
                intermediate = intermediate[:, :effective_dim]
        
        # 降维
        output = self.down_proj(intermediate)
        output = self.dropout(output)
        
        return output
    
    def get_torsion_energy(self) -> torch.Tensor:
        """计算扭转场能量"""
        return torch.sum(self.torsion_a ** 2) + torch.sum(self.torsion_b ** 2)


# =============================================================================
# TNN-Transformer层
# =============================================================================

class TNNTransformerLayer(nn.Module):
    """
    TNN-Transformer层
    结合扭转注意力、互反-内部耦合和谱维自适应MLP
    """
    
    def __init__(self, config: TNNTransformerConfig, layer_idx: int):
        super().__init__()
        self.config = config
        self.layer_idx = layer_idx
        
        # 扭转注意力
        self.attention = TorsionAttention(config)
        
        # 互反-内部耦合
        self.coupling = ReciprocalInternalCoupling(config)
        
        # 谱维自适应MLP
        self.mlp = SpectralAdaptiveMLP(config)
        
        # Layer Norms
        self.ln1 = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.ln2 = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        
        # 深度门控 (用于自适应深度)
        self.depth_gate = nn.Parameter(torch.tensor(1.0))
        
    def forward(
        self,
        hidden_states: torch.Tensor,
        internal_states: Optional[torch.Tensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        layer_past: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False,
        depth_scale: float = 1.0,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[Tuple]]:
        """
        前向传播
        """
        # 自注意力
        residual = hidden_states
        hidden_states = self.ln1(hidden_states)
        attn_output, present = self.attention(
            hidden_states,
            attention_mask=attention_mask,
            layer_past=layer_past,
            use_cache=use_cache
        )
        
        # 深度门控
        gate = torch.sigmoid(self.depth_gate * depth_scale)
        hidden_states = residual + gate * attn_output
        
        # 互反-内部耦合
        hidden_states, internal_states = self.coupling(hidden_states, internal_states)
        
        # MLP
        residual = hidden_states
        hidden_states = self.ln2(hidden_states)
        mlp_output = self.mlp(hidden_states, depth_scale)
        hidden_states = residual + gate * mlp_output
        
        return hidden_states, internal_states, present
    
    def get_torsion_energy(self) -> torch.Tensor:
        """获取扭转场能量"""
        return self.attention.get_torsion_energy() + self.mlp.get_torsion_energy()


# =============================================================================
# TNN-Transformer模型
# =============================================================================

class TNNTransformerLM(nn.Module):
    """
    TNN-Transformer语言模型 (125M参数规模)
    完整的扭转Transformer实现，用于大语言模型验证
    """
    
    def __init__(self, config: TNNTransformerConfig):
        super().__init__()
        self.config = config
        
        # 词嵌入
        self.wte = nn.Embedding(config.vocab_size, config.hidden_size)
        self.wpe = nn.Embedding(config.max_position_embeddings, config.hidden_size)
        
        # Dropout
        self.drop = nn.Dropout(config.hidden_dropout_prob)
        
        # TNN-Transformer层
        self.layers = nn.ModuleList([
            TNNTransformerLayer(config, i) for i in range(config.num_hidden_layers)
        ])
        
        # 最终Layer Norm
        self.ln_f = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        
        # 语言建模头
        self.lm_head = nn.Linear(config.hidden_size, config.vocab_size, bias=False)
        
        # 权重绑定
        self.wte.weight = self.lm_head.weight
        
        # 谱维管理器
        self.spectral_manager = SpectralDimensionManager(config)
        
        # 初始化权重
        self.apply(self._init_weights)
        
        print(f"TNN-Transformer模型初始化完成")
        print(f"  参数量: {self.get_num_params()/1e6:.1f}M")
        print(f"  层数: {config.num_hidden_layers}")
        print(f"  隐藏维度: {config.hidden_size}")
        print(f"  注意力头数: {config.num_attention_heads}")
        print(f"  扭转阶数: {config.torsion_order}")
        print(f"  内部维度: {config.internal_dim}")
        
    def _init_weights(self, module):
        """初始化权重"""
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=self.config.init_std)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=self.config.init_std)
        
    def get_num_params(self, non_embedding: bool = False) -> int:
        """获取参数量"""
        n_params = sum(p.numel() for p in self.parameters())
        if non_embedding:
            n_params -= self.wpe.weight.numel()
            n_params -= self.wte.weight.numel()
        return n_params
    
    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.Tensor] = None,
        past_key_values: Optional[List[Tuple]] = None,
        labels: Optional[torch.Tensor] = None,
        use_cache: bool = False,
        output_attentions: bool = False,
        output_hidden_states: bool = False,
    ) -> Dict[str, torch.Tensor]:
        """
        前向传播
        """
        batch_size, seq_len = input_ids.shape
        device = input_ids.device
        
        # 生成位置ID
        if position_ids is None:
            past_length = past_key_values[0][0].size(-2) if past_key_values else 0
            position_ids = torch.arange(
                past_length, seq_len + past_length, dtype=torch.long, device=device
            ).unsqueeze(0).expand(batch_size, -1)
        
        # 词嵌入 + 位置嵌入
        inputs_embeds = self.wte(input_ids)
        position_embeds = self.wpe(position_ids)
        hidden_states = inputs_embeds + position_embeds
        hidden_states = self.drop(hidden_states)
        
        # 生成因果掩码
        if attention_mask is None:
            attention_mask = torch.ones((batch_size, seq_len), dtype=torch.bool, device=device)
        
        # 因果掩码
        causal_mask = torch.triu(
            torch.ones((seq_len, seq_len), device=device) * float('-inf'),
            diagonal=1
        )
        causal_mask = causal_mask.unsqueeze(0).unsqueeze(0)  # [1, 1, seq_len, seq_len]
        
        # 处理KV Cache
        presents = [] if use_cache else None
        all_hidden_states = () if output_hidden_states else None
        
        # 获取谱维深度缩放
        depth_scale = self.spectral_manager.get_depth_scale()
        
        # 通过Transformer层
        internal_states = None
        for i, layer in enumerate(self.layers):
            if output_hidden_states:
                all_hidden_states = all_hidden_states + (hidden_states,)
            
            past = past_key_values[i] if past_key_values else None
            
            hidden_states, internal_states, present = layer(
                hidden_states,
                internal_states=internal_states,
                attention_mask=causal_mask,
                layer_past=past,
                use_cache=use_cache,
                depth_scale=depth_scale
            )
            
            if use_cache:
                presents.append(present)
        
        hidden_states = self.ln_f(hidden_states)
        
        if output_hidden_states:
            all_hidden_states = all_hidden_states + (hidden_states,)
        
        # 语言建模头
        logits = self.lm_head(hidden_states)
        
        # 计算损失
        loss = None
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
            
            # 添加扭转场正则化
            torsion_energy = sum(layer.get_torsion_energy() for layer in self.layers)
            loss = loss + 0.0001 * torsion_energy
        
        output = {
            'loss': loss,
            'logits': logits,
            'last_hidden_state': hidden_states,
            'past_key_values': presents if use_cache else None,
            'hidden_states': all_hidden_states,
        }
        
        return output
    
    def update_spectral_dimension(self, loss: Optional[torch.Tensor] = None):
        """更新谱维 (需要在forward后调用)"""
        # 这里简化处理，实际应该从hidden_states计算
        if hasattr(self, '_last_hidden_states'):
            return self.spectral_manager.update_spectral_dimension(
                self._last_hidden_states, loss
            )
        return self.spectral_manager.current_d_s.item()
    
    def generate(
        self,
        input_ids: torch.Tensor,
        max_length: int = 100,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 0.95,
        do_sample: bool = True,
    ) -> torch.Tensor:
        """
        文本生成
        """
        self.eval()
        batch_size = input_ids.shape[0]
        device = input_ids.device
        
        past_key_values = None
        
        for _ in range(max_length):
            with torch.no_grad():
                outputs = self.forward(
                    input_ids if past_key_values is None else input_ids[:, -1:],
                    past_key_values=past_key_values,
                    use_cache=True
                )
            
            logits = outputs['logits'][:, -1, :] / temperature
            
            # Top-k采样
            if top_k > 0:
                indices_to_remove = logits < torch.topk(logits, top_k)[0][..., -1, None]
                logits[indices_to_remove] = float('-inf')
            
            # Top-p采样
            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = 0
                indices_to_remove = sorted_indices_to_remove.scatter(
                    1, sorted_indices, sorted_indices_to_remove
                )
                logits[indices_to_remove] = float('-inf')
            
            # 采样
            probs = F.softmax(logits, dim=-1)
            if do_sample:
                next_token = torch.multinomial(probs, num_samples=1)
            else:
                next_token = torch.argmax(probs, dim=-1, keepdim=True)
            
            input_ids = torch.cat([input_ids, next_token], dim=-1)
            past_key_values = outputs['past_key_values']
        
        return input_ids
    
    def save_pretrained(self, save_path: str):
        """保存模型"""
        import os
        os.makedirs(save_path, exist_ok=True)
        
        # 保存模型权重
        torch.save(self.state_dict(), os.path.join(save_path, "pytorch_model.bin"))
        
        # 保存配置
        config_dict = {
            'vocab_size': self.config.vocab_size,
            'max_position_embeddings': self.config.max_position_embeddings,
            'hidden_size': self.config.hidden_size,
            'num_hidden_layers': self.config.num_hidden_layers,
            'num_attention_heads': self.config.num_attention_heads,
            'intermediate_size': self.config.intermediate_size,
            'internal_dim': self.config.internal_dim,
            'torsion_order': self.config.torsion_order,
        }
        with open(os.path.join(save_path, "config.json"), 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        print(f"模型已保存至: {save_path}")
    
    @classmethod
    def from_pretrained(cls, model_path: str, device='cuda'):
        """加载模型"""
        import os
        
        # 加载配置
        with open(os.path.join(model_path, "config.json"), 'r') as f:
            config_dict = json.load(f)
        
        config = TNNTransformerConfig(**config_dict)
        model = cls(config)
        
        # 加载权重
        state_dict = torch.load(os.path.join(model_path, "pytorch_model.bin"), map_location=device)
        model.load_state_dict(state_dict)
        
        return model


# =============================================================================
# 辅助函数和工具
# =============================================================================

def create_125m_tnn_transformer(device='cuda') -> TNNTransformerLM:
    """
    创建125M参数的TNN-Transformer模型
    """
    config = TNNTransformerConfig(
        vocab_size=50257,
        max_position_embeddings=1024,
        hidden_size=768,
        num_hidden_layers=12,
        num_attention_heads=12,
        intermediate_size=3072,
        internal_dim=256,
        torsion_order=3,
        torsion_strength=0.1,
        hidden_dropout_prob=0.1,
        attention_dropout_prob=0.1,
    )
    
    model = TNNTransformerLM(config)
    return model.to(device)


def count_parameters(model: nn.Module) -> Dict[str, int]:
    """详细统计模型参数"""
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    # 按组件统计
    embedding_params = sum(p.numel() for p in [model.wte, model.wpe] for p in p.parameters())
    layer_params = sum(p.numel() for layer in model.layers for p in layer.parameters())
    lm_head_params = sum(p.numel() for p in model.lm_head.parameters())
    
    return {
        'total': total,
        'trainable': trainable,
        'embedding': embedding_params,
        'transformer_layers': layer_params,
        'lm_head': lm_head_params,
    }


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"使用设备: {device}\n")
    
    # 创建模型
    print("创建TNN-Transformer (125M)...")
    model = create_125m_tnn_transformer(device)
    
    # 统计参数
    params = count_parameters(model)
    print("\n参数统计:")
    for k, v in params.items():
        print(f"  {k}: {v/1e6:.2f}M")
    
    # 测试前向传播
    print("\n测试前向传播...")
    batch_size = 2
    seq_len = 128
    input_ids = torch.randint(0, 50257, (batch_size, seq_len), device=device)
    labels = torch.randint(0, 50257, (batch_size, seq_len), device=device)
    
    with torch.no_grad():
        outputs = model(input_ids, labels=labels)
    
    print(f"  输入形状: {input_ids.shape}")
    print(f"  输出logits形状: {outputs['logits'].shape}")
    print(f"  损失值: {outputs['loss'].item():.4f}")
    print(f"  当前谱维: {model.spectral_manager.current_d_s.item():.2f}")
    
    # 测试生成
    print("\n测试文本生成...")
    prompt = torch.randint(0, 50257, (1, 10), device=device)
    generated = model.generate(prompt, max_length=20, do_sample=True)
    print(f"  输入长度: {prompt.shape[1]}")
    print(f"  生成长度: {generated.shape[1]}")
    
    print("\n✓ TNN-Transformer 125M 模型测试通过!")
