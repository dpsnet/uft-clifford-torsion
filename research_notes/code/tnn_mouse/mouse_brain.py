"""
TNN小鼠大脑核心实现
目标: 30M参数级哺乳动物脑模拟

基于TNN数字果蝇实验扩展
作者: AI Research Assistant
日期: 2026-03-18
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TNNMouseConfig:
    """TNN小鼠大脑配置"""
    # 感觉输入维度
    vision_input_dim: int = 49152      # 128×128 RGB
    audition_input_dim: int = 1024     # 频谱特征
    olfaction_input_dim: int = 400     # 嗅觉受体
    touch_input_dim: int = 256         # 触觉传感器
    proprio_input_dim: int = 64        # 本体感觉
    internal_state_dim: int = 32       # 内部状态
    
    # 互反空间 (处理流)
    reciprocal_dims: List[int] = None  # [1024, 1024, 1024, 1024, 2048, 2048, 2048, 2048, 2048, 2048, 1024, 1024, 1024, 1024]
    
    # 内部空间 (高级表征)
    internal_dims: List[int] = None    # [4096, 4096, 8192, 8192, 8192, 4096, 4096, 2048]
    
    # 输出维度
    motor_output_dim: int = 168        # 运动控制
    behavior_output_dim: int = 16      # 行为选择
    
    # TNN特定参数
    torsion_order: int = 3
    spectral_dim_min: float = 2.5
    spectral_dim_max: float = 8.0
    adaptation_rate: float = 0.01
    
    def __post_init__(self):
        if self.reciprocal_dims is None:
            # 初级感觉皮层(4层) + 联想皮层(6层) + 运动皮层(4层) + 海马体(3层，其中1层在internal)
            self.reciprocal_dims = [1024] * 4 + [2048] * 6 + [1024] * 4 + [512] * 2
        if self.internal_dims is None:
            # 高级视觉(2) + 多模态整合(3) + 决策(2) + 工作记忆(1)
            self.internal_dims = [4096, 4096, 8192, 8192, 8192, 4096, 4096, 2048]


class SpectralAdaptiveLinear(nn.Module):
    """谱维自适应线性层"""
    def __init__(self, in_dim: int, out_dim: int, spectral_dim_init: float = 4.0):
        super().__init__()
        self.in_dim = in_dim
        self.out_dim = out_dim
        
        # 标准权重
        self.weight = nn.Parameter(torch.randn(out_dim, in_dim) * 0.02)
        self.bias = nn.Parameter(torch.zeros(out_dim))
        
        # 谱维参数
        self.spectral_dim = nn.Parameter(torch.tensor(spectral_dim_init))
        self.spectral_scale = nn.Parameter(torch.ones(out_dim))
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # 谱维缩放
        d_s = torch.clamp(self.spectral_dim, 2.0, 8.0)
        scale = torch.abs(self.spectral_scale) ** (4.0 / d_s)
        
        # 应用变换
        out = torch.nn.functional.linear(x, self.weight * scale.unsqueeze(1), self.bias)
        
        return out, d_s


class TorsionAttention(nn.Module):
    """扭转注意力机制 - TNN核心"""
    def __init__(self, dim: int, num_heads: int = 8, torsion_order: int = 3):
        super().__init__()
        self.dim = dim
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.torsion_order = torsion_order
        
        # Q, K, V投影
        self.q_proj = nn.Linear(dim, dim)
        self.k_proj = nn.Linear(dim, dim)
        self.v_proj = nn.Linear(dim, dim)
        self.o_proj = nn.Linear(dim, dim)
        
        # 扭转场参数
        self.torsion_field = nn.Parameter(torch.zeros(torsion_order, dim))
        self.torsion_strength = nn.Parameter(torch.ones(torsion_order) * 0.1)
        
    def forward(self, x: torch.Tensor, 
                return_torsion: bool = False) -> Dict[str, torch.Tensor]:
        B, L, D = x.shape
        
        # 标准QKV
        q = self.q_proj(x).view(B, L, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, L, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, L, self.num_heads, self.head_dim).transpose(1, 2)
        
        # 计算注意力分数
        scores = torch.matmul(q, k.transpose(-2, -1)) / np.sqrt(self.head_dim)
        
        # 应用扭转场调制
        torsion_energy = 0.0
        for i in range(self.torsion_order):
            torsion_phase = torch.sigmoid(self.torsion_field[i])
            torsion_mod = self.torsion_strength[i] * torch.sin(
                torch.arange(L, device=x.device).float() * (i + 1) * np.pi / L
            )
            scores = scores + torsion_mod.view(1, 1, 1, -1) * torsion_phase.view(1, 1, 1, -1)
            torsion_energy += torch.sum(self.torsion_strength[i] ** 2)
        
        # 注意力计算
        attn = torch.softmax(scores, dim=-1)
        out = torch.matmul(attn, v)
        
        # 重塑输出
        out = out.transpose(1, 2).contiguous().view(B, L, D)
        out = self.o_proj(out)
        
        result = {
            'output': out,
            'attention': attn,
            'torsion_energy': torsion_energy / self.torsion_order
        }
        
        return result


class TNNMouseBrain(nn.Module):
    """
    TNN小鼠大脑主网络
    架构: 感觉输入 → 互反空间 → 内部空间 → 输出
    """
    def __init__(self, config: TNNMouseConfig):
        super().__init__()
        self.config = config
        
        # 计算总输入维度
        self.total_input_dim = (
            config.vision_input_dim +
            config.audition_input_dim +
            config.olfaction_input_dim +
            config.touch_input_dim +
            config.proprio_input_dim +
            config.internal_state_dim
        )
        
        # 感觉编码器
        self.sensory_encoder = nn.Sequential(
            nn.Linear(self.total_input_dim, 2048),
            nn.LayerNorm(2048),
            nn.GELU(),
            nn.Linear(2048, config.reciprocal_dims[0])
        )
        
        # 互反空间层 (处理流)
        self.reciprocal_layers = nn.ModuleList()
        for i in range(len(config.reciprocal_dims) - 1):
            self.reciprocal_layers.append(nn.Sequential(
                SpectralAdaptiveLinear(
                    config.reciprocal_dims[i], 
                    config.reciprocal_dims[i + 1]
                ),
                nn.LayerNorm(config.reciprocal_dims[i + 1]),
                nn.GELU()
            ))
        
        # 互反→内部投影
        self.reciprocal_to_internal = nn.Linear(
            config.reciprocal_dims[-1],
            config.internal_dims[0]
        )
        
        # 内部空间层 (高级表征)
        self.internal_layers = nn.ModuleList()
        self.internal_attentions = nn.ModuleList()
        
        for i in range(len(config.internal_dims) - 1):
            self.internal_layers.append(nn.Sequential(
                nn.Linear(config.internal_dims[i], config.internal_dims[i + 1]),
                nn.LayerNorm(config.internal_dims[i + 1]),
                nn.GELU()
            ))
            # 每两层添加注意力
            if i % 2 == 0:
                self.internal_attentions.append(
                    TorsionAttention(config.internal_dims[i + 1])
                )
        
        # 工作记忆 (可循环连接)
        self.working_memory = nn.Linear(
            config.internal_dims[-1],
            config.internal_dims[-1]
        )
        self.memory_gate = nn.Linear(config.internal_dims[-1] * 2, config.internal_dims[-1])
        
        # 输出头
        # 运动控制
        self.motor_head = nn.Sequential(
            nn.Linear(config.internal_dims[-1], 512),
            nn.GELU(),
            nn.Linear(512, config.motor_output_dim),
            nn.Tanh()  # 归一化输出
        )
        
        # 行为选择 (策略输出)
        self.behavior_head = nn.Sequential(
            nn.Linear(config.internal_dims[-1], 256),
            nn.GELU(),
            nn.Linear(256, config.behavior_output_dim)
        )
        
        # 状态评估 (价值输出)
        self.value_head = nn.Sequential(
            nn.Linear(config.internal_dims[-1], 256),
            nn.GELU(),
            nn.Linear(256, 1)
        )
        
        # 谱维记录
        self.spectral_dims_history = []
        self.torsion_energies_history = []
        
    def encode_sensory(self, sensory_input: Dict[str, torch.Tensor]) -> torch.Tensor:
        """编码感觉输入"""
        # 拼接所有感觉模态
        inputs = []
        for key in ['vision', 'audition', 'olfaction', 'touch', 'proprioception', 'internal']:
            if key in sensory_input:
                inputs.append(sensory_input[key].flatten(1))
            else:
                # 使用零填充
                dim = getattr(self.config, f'{key}_input_dim' if key != 'internal' else 'internal_state_dim')
                inputs.append(torch.zeros(sensory_input[list(sensory_input.keys())[0]].size(0), dim, 
                                        device=sensory_input[list(sensory_input.keys())[0]].device))
        
        concatenated = torch.cat(inputs, dim=-1)
        return self.sensory_encoder(concatenated)
    
    def forward(self, sensory_input: Dict[str, torch.Tensor],
                memory_state: Optional[torch.Tensor] = None,
                return_details: bool = False) -> Dict[str, torch.Tensor]:
        """
        前向传播
        
        Args:
            sensory_input: 感觉输入字典
            memory_state: 上一时刻的记忆状态
            return_details: 是否返回详细信息
        
        Returns:
            包含输出和内部状态的字典
        """
        batch_size = sensory_input[list(sensory_input.keys())[0]].size(0)
        
        # 感觉编码
        x = self.encode_sensory(sensory_input)
        
        # 互反空间处理
        spectral_dims = []
        torsion_energies = []
        
        for layer in self.reciprocal_layers:
            if isinstance(layer[0], SpectralAdaptiveLinear):
                x, d_s = layer[0](x)
                spectral_dims.append(d_s.item())
                x = layer[1:](x)  # 应用LayerNorm和激活
            else:
                x = layer(x)
        
        # 投影到内部空间
        x = self.reciprocal_to_internal(x)
        
        # 内部空间处理
        for i, layer in enumerate(self.internal_layers):
            x = layer(x)
            
            # 应用注意力 (每两层)
            if i < len(self.internal_attentions):
                attn_out = self.internal_attentions[i](x.unsqueeze(1))
                x = x + attn_out['output'].squeeze(1)
                torsion_energies.append(attn_out['torsion_energy'].item())
        
        # 工作记忆整合
        if memory_state is None:
            memory_state = torch.zeros(batch_size, self.config.internal_dims[-1], device=x.device)
        
        # 门控记忆更新
        memory_input = torch.cat([x, memory_state], dim=-1)
        gate = torch.sigmoid(self.memory_gate(memory_input))
        new_memory = gate * torch.tanh(self.working_memory(x)) + (1 - gate) * memory_state
        
        # 记忆影响当前状态
        x = x + 0.1 * new_memory
        
        # 输出计算
        motor_output = self.motor_head(x)
        behavior_logits = self.behavior_head(x)
        value = self.value_head(x)
        
        # 记录历史
        if spectral_dims:
            self.spectral_dims_history.append(np.mean(spectral_dims))
        if torsion_energies:
            self.torsion_energies_history.append(np.mean(torsion_energies))
        
        result = {
            'motor_output': motor_output,
            'behavior_logits': behavior_logits,
            'value': value,
            'memory_state': new_memory,
            'spectral_dim': np.mean(spectral_dims) if spectral_dims else 4.0,
            'torsion_energy': np.mean(torsion_energies) if torsion_energies else 0.0
        }
        
        if return_details:
            result['internal_representation'] = x
            result['spectral_dims'] = spectral_dims
            result['torsion_energies'] = torsion_energies
        
        return result
    
    def count_parameters(self) -> int:
        """计算总参数量"""
        return sum(p.numel() for p in self.parameters())
    
    def reset_memory(self):
        """重置记忆历史"""
        self.spectral_dims_history = []
        self.torsion_energies_history = []


def create_tnn_mouse_brain(config: Optional[TNNMouseConfig] = None) -> TNNMouseBrain:
    """创建TNN小鼠大脑实例"""
    if config is None:
        config = TNNMouseConfig()
    
    model = TNNMouseBrain(config)
    n_params = model.count_parameters()
    print(f"TNN小鼠大脑创建完成")
    print(f"  总参数量: {n_params/1e6:.2f}M")
    print(f"  互反空间维度: {sum(config.reciprocal_dims):,}")
    print(f"  内部空间维度: {sum(config.internal_dims):,}")
    
    return model


# 测试
if __name__ == "__main__":
    print("=== TNN小鼠大脑测试 ===\n")
    
    # 创建模型
    config = TNNMouseConfig()
    brain = create_tnn_mouse_brain(config)
    
    # 创建模拟输入
    batch_size = 2
    sensory_input = {
        'vision': torch.randn(batch_size, 3, 128, 128),
        'audition': torch.randn(batch_size, 1024),
        'olfaction': torch.randn(batch_size, 400),
        'touch': torch.randn(batch_size, 256),
        'proprioception': torch.randn(batch_size, 64),
        'internal': torch.randn(batch_size, 32)
    }
    
    # 前向传播
    print("\n运行前向传播...")
    with torch.no_grad():
        outputs = brain(sensory_input, return_details=True)
    
    print(f"\n输出形状:")
    print(f"  运动输出: {outputs['motor_output'].shape}")
    print(f"  行为logits: {outputs['behavior_logits'].shape}")
    print(f"  价值: {outputs['value'].shape}")
    print(f"  记忆状态: {outputs['memory_state'].shape}")
    
    print(f"\n内部状态:")
    print(f"  平均谱维: {outputs['spectral_dim']:.2f}")
    print(f"  扭转场能量: {outputs['torsion_energy']:.4f}")
    
    print("\n✓ 测试通过!")
