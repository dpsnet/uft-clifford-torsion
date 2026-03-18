"""
TNN-Transformer Tiny: 1M参数微型模型
基于扭转神经网络(Torsion Neural Network)的轻量级Transformer架构

核心特性:
- 隐藏维度: 128 (vs 原版768)
- 层数: 4层 (vs 原版12层)
- 内部维度: 32 (vs 原版256)
- 参数量: ~1M (便于CPU快速验证)

作者: AI Research Assistant
日期: 2026-03-18
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
import math
import json


# =============================================================================
# 配置类
# =============================================================================

@dataclass
class TNNTransformerTinyConfig:
    """TNN-Transformer微型模型配置 - 1M参数"""
    # 基础架构参数 (大幅缩减)
    vocab_size: int = 10000          # 使用较小的词表
    max_position_embeddings: int = 512  # 缩短序列长度
    hidden_size: int = 128           # 隐藏层维度 (原版768→128)
    num_hidden_layers: int = 4       # 层数 (原版12→4)
    num_attention_heads: int = 4     # 注意力头数 (原版12→4)
    intermediate_size: int = 512     # MLP中间层 (4 * hidden_size)
    
    # TNN特有参数 (适当缩减)
    internal_dim: int = 32           # 内部空间维度 (原版256→32)
    torsion_order: int = 2           # 扭转阶数 (原版3→2)
    torsion_strength: float = 0.1    # 扭转强度
    torsion_rank: int = 16           # 扭转场低秩维度 (原版64→16)
    
    # 谱维自适应参数
    spectral_dim_min: float = 2.0    # 最小谱维
    spectral_dim_max: float = 8.0    # 最大谱维 (降低范围)
    adaptation_rate: float = 0.02    # 谱维适应率 (加快适应)
    
    # 正则化参数
    hidden_dropout_prob: float = 0.05  # 降低dropout
    attention_dropout_prob: float = 0.05
    layer_norm_eps: float = 1e-12
    
    # 优化参数
    init_std: float = 0.02
    
    @property
    def head_dim(self) -> int:
        return self.hidden_size // self.num_attention_heads
    
    @property
    def num_parameters(self) -> int:
        """估算参数量"""
        # 词嵌入 + 位置嵌入
        embed_params = (self.vocab_size + self.max_position_embeddings) * self.hidden_size
        
        # 每层参数简化计算
        # Attention: QKV + O + 扭转场
        attn_params = (4 * self.hidden_size * self.hidden_size + 
                      4 * self.torsion_order * self.hidden_size * self.torsion_rank)
        
        # MLP: gate + up + down + 扭转场
        mlp_params = (3 * self.hidden_size * self.intermediate_size + 
                     2 * self.torsion_order * self.intermediate_size * self.torsion_rank)
        
        # 耦合层
        coupling_params = 2 * (self.hidden_size * self.internal_dim + self.internal_dim * self.hidden_size)
        
        # LayerNorms
        norm_params = 4 * self.hidden_size + 2 * self.internal_dim
        
        layer_params = attn_params + mlp_params + coupling_params + norm_params
        total = embed_params + self.num_hidden_layers * layer_params + self.hidden_size
        
        return int(total)


# =============================================================================
# 谱维管理器
# =============================================================================

class SpectralDimensionManager(nn.Module):
    """谱维自适应管理器 (轻量版)"""
    
    def __init__(self, config: TNNTransformerTinyConfig):
        super().__init__()
        self.config = config
        self.d_s_min = config.spectral_dim_min
        self.d_s_max = config.spectral_dim_max
        self.adaptation_rate = config.adaptation_rate
        
        # 当前谱维 (可学习)
        self.current_d_s = nn.Parameter(torch.tensor(4.0))
        
        # 简化复杂度估计
        self.complexity_estimator = nn.Sequential(
            nn.Linear(config.hidden_size, config.hidden_size // 2),
            nn.GELU(),
            nn.Linear(config.hidden_size // 2, 1),
            nn.Sigmoid()
        )
        
    def compute_sequence_complexity(self, hidden_states: torch.Tensor) -> torch.Tensor:
        """计算序列复杂度"""
        pooled = hidden_states.mean(dim=1)
        complexity = self.complexity_estimator(pooled)
        return complexity.mean()
    
    def update_spectral_dimension(self, hidden_states: torch.Tensor, 
                                   loss: Optional[torch.Tensor] = None) -> float:
        """更新谱维"""
        complexity = self.compute_sequence_complexity(hidden_states)
        d_target = self.d_s_min + complexity * (self.d_s_max - self.d_s_min)
        
        if loss is not None:
            loss_factor = torch.sigmoid(loss / 5.0)  # 简化损失响应
            d_target = d_target + loss_factor * (self.d_s_max - d_target) * 0.5
        
        # 谱维流动
        delta_d_s = -self.adaptation_rate * (self.current_d_s - d_target)
        self.current_d_s.data += delta_d_s
        self.current_d_s.data.clamp_(self.d_s_min, self.d_s_max)
        
        return self.current_d_s.item()
    
    def get_depth_scale(self) -> float:
        """获取深度缩放因子"""
        return self.current_d_s.item() / 4.0


# =============================================================================
# 扭转注意力机制
# =============================================================================

class TorsionAttention(nn.Module):
    """扭转注意力机制 (轻量版)"""
    
    def __init__(self, config: TNNTransformerTinyConfig):
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.num_heads = config.num_attention_heads
        self.head_dim = config.head_dim
        self.torsion_order = config.torsion_order
        self.torsion_rank = config.torsion_rank
        
        assert self.head_dim * self.num_heads == self.hidden_size
        
        # 标准投影
        self.q_proj = nn.Linear(config.hidden_size, config.hidden_size, bias=False)
        self.k_proj = nn.Linear(config.hidden_size, config.hidden_size, bias=False)
        self.v_proj = nn.Linear(config.hidden_size, config.hidden_size, bias=False)
        self.o_proj = nn.Linear(config.hidden_size, config.hidden_size, bias=False)
        
        # 低秩扭转场
        self.q_torsion_a = nn.Parameter(
            torch.randn(config.torsion_order, config.hidden_size, config.torsion_rank) * 0.01
        )
        self.q_torsion_b = nn.Parameter(
            torch.randn(config.torsion_order, config.torsion_rank, config.hidden_size) * 0.01
        )
        self.k_torsion_a = nn.Parameter(
            torch.randn(config.torsion_order, config.hidden_size, config.torsion_rank) * 0.01
        )
        self.k_torsion_b = nn.Parameter(
            torch.randn(config.torsion_order, config.torsion_rank, config.hidden_size) * 0.01
        )
        
        self.torsion_coupling = nn.Parameter(torch.tensor(0.1))
        self.attn_dropout = nn.Dropout(config.attention_dropout_prob)
        self.resid_dropout = nn.Dropout(config.hidden_dropout_prob)
        self.scale = self.head_dim ** -0.5
        
    def apply_torsion(self, x: torch.Tensor, torsion_a: nn.Parameter, 
                      torsion_b: nn.Parameter) -> torch.Tensor:
        """应用低秩扭转场"""
        torsion_correction = torch.zeros_like(x)
        
        for n in range(self.torsion_order):
            a_n = torsion_a[n]
            b_n = torsion_b[n]
            
            # 低秩投影
            low_dim = torch.matmul(x, a_n)
            linear_out = torch.matmul(low_dim, b_n)
            
            # 螺旋型扭曲
            phase = 2 * math.pi * (n + 1) * linear_out
            twisted = torch.sin(phase) * linear_out / (n + 1)
            torsion_correction += twisted
        
        coupling = torch.sigmoid(self.torsion_coupling)
        return x + coupling * torsion_correction
    
    def forward(self, hidden_states: torch.Tensor, 
                attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """前向传播"""
        batch_size, seq_len, _ = hidden_states.shape
        
        # 投影
        query = self.q_proj(hidden_states)
        key = self.k_proj(hidden_states)
        value = self.v_proj(hidden_states)
        
        # 应用扭转
        query = self.apply_torsion(query, self.q_torsion_a, self.q_torsion_b)
        key = self.apply_torsion(key, self.k_torsion_a, self.k_torsion_b)
        
        # 多头重塑
        query = query.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        key = key.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        value = value.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        
        # 注意力计算
        attn_weights = torch.matmul(query, key.transpose(-2, -1)) * self.scale
        
        if attention_mask is not None:
            attn_weights = attn_weights + attention_mask
        
        attn_weights = F.softmax(attn_weights, dim=-1)
        attn_weights = self.attn_dropout(attn_weights)
        
        attn_output = torch.matmul(attn_weights, value)
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.hidden_size)
        attn_output = self.o_proj(attn_output)
        attn_output = self.resid_dropout(attn_output)
        
        return attn_output
    
    def get_torsion_energy(self) -> torch.Tensor:
        """计算扭转场能量"""
        return (torch.sum(self.q_torsion_a ** 2) + torch.sum(self.q_torsion_b ** 2) +
                torch.sum(self.k_torsion_a ** 2) + torch.sum(self.k_torsion_b ** 2))


# =============================================================================
# 互反-内部空间耦合
# =============================================================================

class ReciprocalInternalCoupling(nn.Module):
    """互反-内部空间耦合层 (轻量版)"""
    
    def __init__(self, config: TNNTransformerTinyConfig):
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.internal_dim = config.internal_dim
        
        self.r_to_i = nn.Linear(config.hidden_size, config.internal_dim, bias=True)
        self.i_to_r = nn.Linear(config.internal_dim, config.hidden_size, bias=True)
        
        # 简化内部变换
        self.internal_transform = nn.Sequential(
            nn.Linear(config.internal_dim, config.internal_dim),
            nn.GELU(),
            nn.Linear(config.internal_dim, config.internal_dim)
        )
        
        self.flow_gate = nn.Parameter(torch.tensor(0.5))
        self.norm_internal = nn.LayerNorm(config.internal_dim, eps=config.layer_norm_eps)
        
    def forward(self, reciprocal: torch.Tensor, 
                internal: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        """前向传播"""
        batch_size, seq_len, _ = reciprocal.shape
        
        if internal is None:
            internal = torch.zeros(batch_size, seq_len, self.internal_dim, device=reciprocal.device)
        
        # 内部变换
        h_internal = self.internal_transform(internal)
        h_internal = self.norm_internal(h_internal)
        
        # 跨维流动
        gate = torch.sigmoid(self.flow_gate)
        
        flow_r_to_i = self.r_to_i(reciprocal)
        h_internal = h_internal + gate * flow_r_to_i
        
        flow_i_to_r = self.i_to_r(h_internal)
        h_reciprocal = reciprocal + gate * flow_i_to_r
        
        return h_reciprocal, h_internal


# =============================================================================
# 谱维自适应MLP
# =============================================================================

class SpectralAdaptiveMLP(nn.Module):
    """谱维自适应MLP (轻量版)"""
    
    def __init__(self, config: TNNTransformerTinyConfig):
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.intermediate_size = config.intermediate_size
        self.torsion_order = config.torsion_order
        self.torsion_rank = config.torsion_rank
        
        self.gate_proj = nn.Linear(config.hidden_size, config.intermediate_size, bias=True)
        self.up_proj = nn.Linear(config.hidden_size, config.intermediate_size, bias=True)
        self.down_proj = nn.Linear(config.intermediate_size, config.hidden_size, bias=True)
        
        # 低秩扭转场
        self.torsion_a = nn.Parameter(
            torch.randn(config.torsion_order, config.intermediate_size, config.torsion_rank) * 0.01
        )
        self.torsion_b = nn.Parameter(
            torch.randn(config.torsion_order, config.torsion_rank, config.intermediate_size) * 0.01
        )
        
        self.torsion_coupling = nn.Parameter(torch.tensor(0.1))
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        
    def apply_torsion(self, x: torch.Tensor) -> torch.Tensor:
        """应用低秩扭转场"""
        torsion_correction = torch.zeros_like(x)
        
        for n in range(self.torsion_order):
            a_n = self.torsion_a[n]
            b_n = self.torsion_b[n]
            
            low_dim = torch.matmul(x, a_n)
            linear_out = torch.matmul(low_dim, b_n)
            
            phase = 2 * math.pi * (n + 1) * linear_out
            twisted = torch.sin(phase) * linear_out / (n + 1)
            torsion_correction += twisted
        
        coupling = torch.sigmoid(self.torsion_coupling)
        return x + coupling * torsion_correction
    
    def forward(self, x: torch.Tensor, depth_scale: float = 1.0) -> torch.Tensor:
        """前向传播"""
        gate = self.activation(self.gate_proj(x))
        up = self.up_proj(x)
        intermediate = gate * up
        
        intermediate = self.apply_torsion(intermediate)
        
        # 深度缩放 (简化)
        if depth_scale != 1.0 and self.training:
            effective_dim = max(1, int(self.intermediate_size * depth_scale))
            if effective_dim < self.intermediate_size:
                intermediate = intermediate[:, :effective_dim].contiguous()
                # 调整down_proj
                output = torch.matmul(intermediate, self.down_proj.weight[:effective_dim, :].t())
                if self.down_proj.bias is not None:
                    output = output + self.down_proj.bias
            else:
                output = self.down_proj(intermediate)
        else:
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
    """TNN-Transformer层 (轻量版)"""
    
    def __init__(self, config: TNNTransformerTinyConfig, layer_idx: int):
        super().__init__()
        self.config = config
        self.layer_idx = layer_idx
        
        self.attention = TorsionAttention(config)
        self.coupling = ReciprocalInternalCoupling(config)
        self.mlp = SpectralAdaptiveMLP(config)
        
        self.ln1 = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.ln2 = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        
        self.depth_gate = nn.Parameter(torch.tensor(1.0))
        
    def forward(self, hidden_states: torch.Tensor, 
                internal_states: Optional[torch.Tensor] = None,
                attention_mask: Optional[torch.Tensor] = None,
                depth_scale: float = 1.0) -> Tuple[torch.Tensor, torch.Tensor]:
        """前向传播"""
        # 自注意力
        residual = hidden_states
        hidden_states = self.ln1(hidden_states)
        attn_output = self.attention(hidden_states, attention_mask)
        
        gate = torch.sigmoid(self.depth_gate * depth_scale)
        hidden_states = residual + gate * attn_output
        
        # 互反-内部耦合
        hidden_states, internal_states = self.coupling(hidden_states, internal_states)
        
        # MLP
        residual = hidden_states
        hidden_states = self.ln2(hidden_states)
        mlp_output = self.mlp(hidden_states, depth_scale)
        hidden_states = residual + gate * mlp_output
        
        return hidden_states, internal_states
    
    def get_torsion_energy(self) -> torch.Tensor:
        """获取扭转场能量"""
        return self.attention.get_torsion_energy() + self.mlp.get_torsion_energy()


# =============================================================================
# TNN-Transformer微型模型
# =============================================================================

class TNNTransformerTinyLM(nn.Module):
    """TNN-Transformer微型语言模型 (1M参数)"""
    
    def __init__(self, config: TNNTransformerTinyConfig):
        super().__init__()
        self.config = config
        
        # 词嵌入
        self.wte = nn.Embedding(config.vocab_size, config.hidden_size)
        self.wpe = nn.Embedding(config.max_position_embeddings, config.hidden_size)
        
        self.drop = nn.Dropout(config.hidden_dropout_prob)
        
        # TNN-Transformer层
        self.layers = nn.ModuleList([
            TNNTransformerLayer(config, i) for i in range(config.num_hidden_layers)
        ])
        
        self.ln_f = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.lm_head = nn.Linear(config.hidden_size, config.vocab_size, bias=False)
        
        # 权重绑定
        self.wte.weight = self.lm_head.weight
        
        # 谱维管理器
        self.spectral_manager = SpectralDimensionManager(config)
        
        # 初始化
        self.apply(self._init_weights)
        
        # 统计参数量
        n_params = sum(p.numel() for p in self.parameters())
        print(f"TNN-Transformer Tiny初始化完成")
        print(f"  参数量: {n_params/1e6:.2f}M")
        print(f"  层数: {config.num_hidden_layers}")
        print(f"  隐藏维度: {config.hidden_size}")
        print(f"  注意力头数: {config.num_attention_heads}")
        print(f"  词表大小: {config.vocab_size}")
        
    def _init_weights(self, module):
        """初始化权重"""
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=self.config.init_std)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=self.config.init_std)
    
    def get_num_params(self) -> int:
        """获取参数量"""
        return sum(p.numel() for p in self.parameters())
    
    def forward(self, input_ids: torch.Tensor,
                attention_mask: Optional[torch.Tensor] = None,
                labels: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        """前向传播"""
        batch_size, seq_len = input_ids.shape
        device = input_ids.device
        
        # 位置ID
        position_ids = torch.arange(0, seq_len, dtype=torch.long, device=device).unsqueeze(0)
        
        # 嵌入
        inputs_embeds = self.wte(input_ids)
        position_embeds = self.wpe(position_ids)
        hidden_states = inputs_embeds + position_embeds
        hidden_states = self.drop(hidden_states)
        
        # 因果掩码
        causal_mask = torch.triu(
            torch.ones((seq_len, seq_len), device=device) * float('-inf'), diagonal=1
        )
        causal_mask = causal_mask.unsqueeze(0).unsqueeze(0)
        
        # 深度缩放
        depth_scale = self.spectral_manager.get_depth_scale()
        
        # Transformer层
        internal_states = None
        all_torsion_energies = []
        
        for layer in self.layers:
            hidden_states, internal_states = layer(
                hidden_states, internal_states, causal_mask, depth_scale
            )
            all_torsion_energies.append(layer.get_torsion_energy())
        
        hidden_states = self.ln_f(hidden_states)
        
        # 语言建模头
        logits = self.lm_head(hidden_states)
        
        # 计算损失
        loss = None
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
            
            # 扭转场正则化
            total_torsion_energy = sum(all_torsion_energies)
            loss = loss + 0.0001 * total_torsion_energy
        
        # 更新谱维
        current_d_s = self.spectral_manager.update_spectral_dimension(hidden_states, loss)
        
        # 计算平均扭转场能量
        avg_torsion_energy = (sum(all_torsion_energies) / len(all_torsion_energies)).item()
        
        return {
            'loss': loss,
            'logits': logits,
            'last_hidden_state': hidden_states,
            'spectral_dimension': current_d_s,
            'torsion_energy': avg_torsion_energy,
            'depth_scale': depth_scale,
        }
    
    @torch.no_grad()
    def generate(self, input_ids: torch.Tensor, max_length: int = 50,
                 temperature: float = 1.0, top_k: int = 20, 
                 top_p: float = 0.95) -> torch.Tensor:
        """文本生成"""
        self.eval()
        device = input_ids.device
        
        for _ in range(max_length):
            outputs = self.forward(input_ids)
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
                indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
                logits[indices_to_remove] = float('-inf')
            
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            input_ids = torch.cat([input_ids, next_token], dim=-1)
        
        return input_ids
    
    def save_pretrained(self, save_path: str):
        """保存模型"""
        import os
        os.makedirs(save_path, exist_ok=True)
        
        torch.save(self.state_dict(), os.path.join(save_path, "pytorch_model.bin"))
        
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
    def from_pretrained(cls, model_path: str, device='cpu'):
        """加载模型"""
        import os
        
        with open(os.path.join(model_path, "config.json"), 'r') as f:
            config_dict = json.load(f)
        
        config = TNNTransformerTinyConfig(**config_dict)
        model = cls(config)
        
        state_dict = torch.load(os.path.join(model_path, "pytorch_model.bin"), map_location=device)
        model.load_state_dict(state_dict)
        
        return model


# =============================================================================
# 工厂函数
# =============================================================================

def create_tiny_tnn_transformer(vocab_size: int = 5000, device: str = 'cpu') -> TNNTransformerTinyLM:
    """创建1M参数的TNN-Transformer微型模型"""
    config = TNNTransformerTinyConfig(
        vocab_size=vocab_size,
        max_position_embeddings=256,    # 减少位置嵌入
        hidden_size=128,
        num_hidden_layers=4,
        num_attention_heads=4,
        intermediate_size=256,          # 减少MLP维度
        internal_dim=16,                # 减少内部维度
        torsion_order=2,
        torsion_rank=8,                 # 减少扭转场秩
        hidden_dropout_prob=0.05,
        attention_dropout_prob=0.05,
    )
    
    model = TNNTransformerTinyLM(config)
    return model.to(device)


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print(f"使用设备: cpu\n")
    
    # 创建模型
    print("创建TNN-Transformer Tiny (1M)...")
    model = create_tiny_tnn_transformer(vocab_size=10000, device='cpu')
    
    n_params = model.get_num_params()
    print(f"\n实际参数量: {n_params/1e6:.2f}M")
    
    # 测试前向传播
    print("\n测试前向传播...")
    batch_size = 2
    seq_len = 64
    input_ids = torch.randint(0, 10000, (batch_size, seq_len))
    labels = torch.randint(0, 10000, (batch_size, seq_len))
    
    outputs = model(input_ids, labels=labels)
    
    print(f"  输入形状: {input_ids.shape}")
    print(f"  输出logits形状: {outputs['logits'].shape}")
    print(f"  损失值: {outputs['loss'].item():.4f}")
    print(f"  当前谱维: {outputs['spectral_dimension']:.2f}")
    print(f"  扭转场能量: {outputs['torsion_energy']:.4f}")
    
    # 测试生成
    print("\n测试文本生成...")
    prompt = torch.randint(0, 10000, (1, 10))
    generated = model.generate(prompt, max_length=20)
    print(f"  输入长度: {prompt.shape[1]}")
    print(f"  生成长度: {generated.shape[1]}")
    
    print("\n✓ TNN-Transformer Tiny (1M) 模型测试通过!")
