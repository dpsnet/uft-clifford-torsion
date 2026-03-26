"""
超级TNN虫子核心实现
约136万参数的大规模TNN生态系统

架构:
- 感觉层: 32个传感器
  * 8个光感受器（360度视觉）
  * 8个化学感受器（嗅觉梯度）
  * 8个触觉传感器（全身触觉）
  * 4个内部状态（能量、健康、年龄、繁殖欲）
  * 4个社交传感器（探测其他虫子）

- 中间层:
  * 互反空间: 16维
  * 内部空间: 512维
  * 层数: 8-12层
  * 扭转阶数: 4-5阶
  * 可塑扭转场（简单学习机制）

- 运动/行为层: 32个输出
  * 运动控制（8维）
  * 行为选择（觅食、逃跑、交配、休息、探索、攻击、交流）
  * 内部调节（新陈代谢、修复）
  * 记忆输出（信息素标记）
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple, List, Dict, Set
from dataclasses import dataclass, field


@dataclass
class WormState:
    """虫子内部状态"""
    energy: float = 100.0
    health: float = 100.0
    age: float = 0.0
    reproduction_drive: float = 0.0
    metabolism_rate: float = 1.0
    stress_level: float = 0.0
    
    # 行为状态标志
    is_mating: bool = False
    is_resting: bool = False
    is_exploring: bool = False
    is_fleeing: bool = False
    
    # 社交记忆
    known_worms: Dict[int, float] = field(default_factory=dict)  # worm_id -> 好感度
    territory_center: Optional[Tuple[float, float]] = None
    home_location: Optional[Tuple[float, float]] = None


@dataclass  
class WormMemory:
    """虫子长期记忆结构"""
    food_locations: List[Tuple[float, float, float]] = field(default_factory=list)  # (x, y, quality)
    danger_locations: List[Tuple[float, float, float]] = field(default_factory=list)  # (x, y, intensity)
    mate_encounters: List[Tuple[int, float]] = field(default_factory=list)  # (worm_id, quality)
    last_positions: List[Tuple[float, float]] = field(default_factory=list)  # 最近位置历史
    
    def add_food_memory(self, x: float, y: float, quality: float, max_memories: int = 10):
        """添加食物位置记忆"""
        self.food_locations.append((x, y, quality))
        # 按质量排序，保留最好的
        self.food_locations.sort(key=lambda t: t[2], reverse=True)
        self.food_locations = self.food_locations[:max_memories]
    
    def add_danger_memory(self, x: float, y: float, intensity: float, max_memories: int = 10):
        """添加危险位置记忆"""
        self.danger_locations.append((x, y, intensity))
        self.danger_locations.sort(key=lambda t: t[2], reverse=True)
        self.danger_locations = self.danger_locations[:max_memories]
    
    def update_position_history(self, x: float, y: float, max_history: int = 50):
        """更新位置历史"""
        self.last_positions.append((x, y))
        if len(self.last_positions) > max_history:
            self.last_positions.pop(0)


class AdaptiveSpectralDimension:
    """
    自适应谱维管理器
    支持动态范围2.0-8.0，根据输入复杂度自动调整
    """
    
    def __init__(
        self,
        d_s_min: float = 2.0,
        d_s_max: float = 8.0,
        adaptation_rate: float = 0.05,
        device='cpu'
    ):
        self.d_s_min = d_s_min
        self.d_s_max = d_s_max
        self.adaptation_rate = adaptation_rate
        self.device = device
        
        # 当前谱维
        self.current_d_s = 4.0
        self.d_s_history = []
        self.complexity_history = []
        
        # 自适应参数
        self.base_complexity = 0.1
        self.complexity_threshold = 0.5
        
    def update(self, input_complexity: float, context_factor: float = 1.0):
        """
        根据输入复杂度和上下文更新谱维
        
        Args:
            input_complexity: 输入复杂度（0-1）
            context_factor: 上下文因子（如紧急情况下降低维度以加速决策）
        """
        # 计算目标谱维
        normalized_complexity = min(input_complexity / (self.base_complexity + 1e-8), 2.0)
        d_target = self.d_s_min + normalized_complexity * (self.d_s_max - self.d_s_min)
        
        # 应用上下文因子
        d_target = d_target * context_factor
        
        # 平滑更新
        self.current_d_s = (1 - self.adaptation_rate) * self.current_d_s + \
                           self.adaptation_rate * d_target
        self.current_d_s = np.clip(self.current_d_s, self.d_s_min, self.d_s_max)
        
        self.d_s_history.append(self.current_d_s)
        self.complexity_history.append(input_complexity)
        
        return self.current_d_s
    
    def get_spectral_phase(self) -> float:
        """获取谱相位（用于调制网络行为）"""
        return np.sin(2 * np.pi * self.current_d_s / self.d_s_max)


class PlasticTorsionField(nn.Module):
    """
    可塑扭转场模块
    支持短期可塑性（类似突触可塑性）
    
    总参数量: out_features * in_features * (1 + torsion_order + 1) + out_features
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        torsion_order: int = 4,
        torsion_strength: float = 0.1,
        enable_plasticity: bool = True,
        plasticity_rate: float = 0.001,
        device='cpu'
    ):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.torsion_order = torsion_order
        self.device = device
        self.enable_plasticity = enable_plasticity
        self.plasticity_rate = plasticity_rate
        
        # 基础权重
        self.weight = nn.Parameter(
            torch.randn(out_features, in_features, device=device) * 0.1
        )
        self.bias = nn.Parameter(torch.zeros(out_features, device=device))
        
        # 扭转场（多阶）
        self.torsion_field = nn.Parameter(
            torch.randn(
                torsion_order,
                out_features,
                in_features,
                device=device
            ) * torsion_strength
        )
        
        # 动态扭转系数（可学习）
        self.torsion_coupling = nn.Parameter(torch.tensor(0.5, device=device))
        
        # 可塑状态（短期记忆）
        if enable_plasticity:
            self.register_buffer(
                'plastic_weights',
                torch.zeros(out_features, in_features, device=device)
            )
            self.register_buffer(
                'activation_history',
                torch.zeros(100, out_features, device=device)
            )
            self.history_ptr = 0
        
        # 谱维调制参数
        self.spectral_gate = nn.Parameter(torch.tensor(0.5, device=device))
        
    def forward(self, x: torch.Tensor, spectral_dim: float = 4.0) -> torch.Tensor:
        """
        前向传播，包含扭转效应和谱维调制
        
        Args:
            x: 输入 [batch, in_features]
            spectral_dim: 当前谱维
        """
        batch_size = x.shape[0]
        
        # 基础线性变换
        if self.enable_plasticity and hasattr(self, 'plastic_weights'):
            effective_weight = self.weight + self.plasticity_rate * self.plastic_weights
        else:
            effective_weight = self.weight
            
        base_output = F.linear(x, effective_weight, self.bias)
        
        # 扭转修正（多阶叠加）
        torsion_correction = torch.zeros_like(base_output)
        
        for n in range(self.torsion_order):
            torsion_n = self.torsion_field[n]
            linear_out = F.linear(x, torsion_n)
            
            # 谱维调制相位
            phase_factor = 2 * np.pi * (n + 1) * spectral_dim / self.torsion_order
            phase = linear_out + phase_factor
            
            # 扭转效应
            twisted = torch.sin(phase) * linear_out / (n + 1)
            torsion_correction += twisted
        
        # 谱维门控
        spectral_gate_value = torch.sigmoid(self.spectral_gate)
        gate_factor = spectral_gate_value * (spectral_dim / 4.0)
        
        # 扭转耦合
        coupling = torch.sigmoid(self.torsion_coupling)
        
        # 组合输出
        output = base_output + coupling * gate_factor * torsion_correction
        
        # 更新可塑状态
        if self.enable_plasticity and self.training:
            self._update_plasticity(output.detach())
        
        return output
    
    def _update_plasticity(self, activation: torch.Tensor):
        """更新可塑权重（Hebbian-like learning）"""
        if not hasattr(self, 'activation_history'):
            return
            
        # 记录激活历史
        batch_mean = activation.mean(dim=0)
        self.activation_history[self.history_ptr] = batch_mean
        self.history_ptr = (self.history_ptr + 1) % 100
        
        # 计算协方差并更新可塑权重
        if self.history_ptr % 10 == 0:
            recent = self.activation_history[max(0, self.history_ptr-10):self.history_ptr]
            if len(recent) > 1:
                cov = torch.cov(recent.T)
                if cov.shape[0] == self.out_features:
                    # 简化的Hebbian更新
                    self.plastic_weights += self.plasticity_rate * cov[:self.out_features, :self.in_features] \
                                           if cov.shape[1] >= self.in_features else 0
    
    def get_torsion_energy(self) -> torch.Tensor:
        """计算扭转场能量"""
        return torch.sum(self.torsion_field ** 2)
    
    def get_param_count(self) -> int:
        """获取参数数量"""
        return sum(p.numel() for p in self.parameters())


class SuperTNNCore(nn.Module):
    """
    超级TNN核心（约136万参数）
    
    架构分层:
    1. 输入投影层: 32 -> 16
    2. 互反空间处理: 16维，4-6层
    3. 内部空间处理: 256维，6-8层
    4. 跨空间耦合: 16 <-> 256
    5. 输出投影: 16 -> 32
    """
    
    def __init__(
        self,
        input_dim: int = 32,
        reciprocal_dim: int = 16,
        internal_dim: int = 192,
        output_dim: int = 32,
        n_reciprocal_layers: int = 5,
        n_internal_layers: int = 8,
        torsion_order: int = 4,
        torsion_strength: float = 0.15,
        enable_plasticity: bool = True,
        device='cpu'
    ):
        super().__init__()
        self.input_dim = input_dim
        self.reciprocal_dim = reciprocal_dim
        self.internal_dim = internal_dim
        self.output_dim = output_dim
        self.n_reciprocal_layers = n_reciprocal_layers
        self.n_internal_layers = n_internal_layers
        self.device = device
        
        # 谱维管理器
        self.spectral_manager = AdaptiveSpectralDimension(device=device)
        
        # === 输入投影层 ===
        self.input_projection = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Linear(64, reciprocal_dim),
            nn.LayerNorm(reciprocal_dim)
        )
        
        # === 互反空间处理层 ===
        self.reciprocal_layers = nn.ModuleList()
        for i in range(n_reciprocal_layers):
            self.reciprocal_layers.append(
                PlasticTorsionField(
                    reciprocal_dim, reciprocal_dim,
                    torsion_order=max(2, torsion_order - i//2),  # 高层降低阶数
                    torsion_strength=torsion_strength * (1.0 - 0.1*i),
                    enable_plasticity=enable_plasticity,
                    device=device
                )
            )
        
        # 互反空间层间归一化
        self.reciprocal_norms = nn.ModuleList([
            nn.LayerNorm(reciprocal_dim) for _ in range(n_reciprocal_layers)
        ])
        
        # === 内部空间处理层 ===
        self.internal_layers = nn.ModuleList()
        for i in range(n_internal_layers):
            layer_torsion = torsion_order if i < n_internal_layers // 2 else max(2, torsion_order - 1)
            self.internal_layers.append(
                PlasticTorsionField(
                    internal_dim, internal_dim,
                    torsion_order=layer_torsion,
                    torsion_strength=torsion_strength * 0.8,
                    enable_plasticity=enable_plasticity,
                    device=device
                )
            )
        
        # 内部空间层间归一化
        self.internal_norms = nn.ModuleList([
            nn.LayerNorm(internal_dim) for _ in range(n_internal_layers)
        ])
        
        # === 跨空间耦合 ===
        # 互反 -> 内部
        self.reciprocal_to_internal = nn.Sequential(
            nn.Linear(reciprocal_dim, 128),
            nn.GELU(),
            nn.Linear(128, internal_dim)
        )
        
        # 内部 -> 互反
        self.internal_to_reciprocal = nn.Sequential(
            nn.Linear(internal_dim, 128),
            nn.GELU(),
            nn.Linear(128, reciprocal_dim)
        )
        
        # 流动门控（可学习）
        self.flow_gates = nn.Parameter(torch.ones(n_reciprocal_layers) * 0.5)
        
        # === 内部记忆状态 ===
        self.register_buffer(
            'internal_memory',
            torch.randn(1, internal_dim, device=device) * 0.01
        )
        
        # === 输出投影层 ===
        self.output_projection = nn.Sequential(
            nn.Linear(reciprocal_dim, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Linear(64, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Linear(64, output_dim)
        )
        
        # 输出门控
        self.output_gate = nn.Parameter(torch.tensor(0.5, device=device))
        
        # 统计信息
        self._count_parameters()
        
        # 历史记录
        self.torsion_energy_history = []
        self.spectral_dim_history = []
        self.flow_gate_history = []
        
    def _count_parameters(self):
        """统计参数数量"""
        self.total_params = sum(p.numel() for p in self.parameters())
        
        # 分层统计
        self.param_breakdown = {
            'input_projection': sum(p.numel() for p in self.input_projection.parameters()),
            'reciprocal_layers': sum(p.numel() for p in self.reciprocal_layers.parameters()),
            'internal_layers': sum(p.numel() for p in self.internal_layers.parameters()),
            'cross_space': sum(p.numel() for p in self.reciprocal_to_internal.parameters()) + \
                          sum(p.numel() for p in self.internal_to_reciprocal.parameters()),
            'output_projection': sum(p.numel() for p in self.output_projection.parameters()),
            'other': self.total_params - (
                sum(p.numel() for p in self.input_projection.parameters()) +
                sum(p.numel() for p in self.reciprocal_layers.parameters()) +
                sum(p.numel() for p in self.internal_layers.parameters()) +
                sum(p.numel() for p in self.reciprocal_to_internal.parameters()) +
                sum(p.numel() for p in self.internal_to_reciprocal.parameters()) +
                sum(p.numel() for p in self.output_projection.parameters())
            )
        }
    
    def forward(self, x: torch.Tensor, context_factor: float = 1.0) -> torch.Tensor:
        """
        前向传播
        
        Args:
            x: [batch, input_dim] 传感器输入
            context_factor: 上下文因子（紧急情况下降低）
        """
        batch_size = x.shape[0]
        
        # 更新谱维
        input_complexity = x.std(dim=1).mean().item()
        d_s = self.spectral_manager.update(input_complexity, context_factor)
        self.spectral_dim_history.append(d_s)
        
        # 输入投影
        x_reciprocal = self.input_projection(x)
        x_reciprocal = F.gelu(x_reciprocal)
        
        # 扩展内部记忆
        x_internal = self.internal_memory.expand(batch_size, -1)
        
        # 互反-内部耦合循环
        for i, (rec_layer, rec_norm) in enumerate(zip(self.reciprocal_layers, self.reciprocal_norms)):
            # 互反空间处理
            h_reciprocal = rec_layer(x_reciprocal, d_s)
            h_reciprocal = rec_norm(h_reciprocal)
            h_reciprocal = F.gelu(h_reciprocal)
            
            # 残差连接
            x_reciprocal = x_reciprocal + 0.1 * h_reciprocal
            
            # 跨空间流动（每隔一层）
            if i % 2 == 0 and i < len(self.reciprocal_layers) - 1:
                flow_gate = torch.sigmoid(self.flow_gates[i // 2])
                
                # 互反 -> 内部
                flow_to_internal = self.reciprocal_to_internal(x_reciprocal)
                
                # 内部空间处理
                if i // 2 < len(self.internal_layers):
                    int_layer = self.internal_layers[i // 2]
                    int_norm = self.internal_norms[i // 2]
                    
                    h_internal = int_layer(x_internal, d_s)
                    h_internal = int_norm(h_internal)
                    h_internal = F.gelu(h_internal)
                    
                    x_internal = x_internal + 0.1 * h_internal + flow_gate * flow_to_internal
                
                # 内部 -> 互反
                flow_to_reciprocal = self.internal_to_reciprocal(x_internal)
                x_reciprocal = x_reciprocal + flow_gate * flow_to_reciprocal
        
        # 输出投影
        output = self.output_projection(x_reciprocal)
        
        # 输出门控
        gate = torch.sigmoid(self.output_gate)
        output = output * gate
        
        # 记录历史
        total_energy = sum(layer.get_torsion_energy().item() for layer in 
                          list(self.reciprocal_layers) + list(self.internal_layers))
        self.torsion_energy_history.append(total_energy)
        self.flow_gate_history.append(torch.sigmoid(self.flow_gates).mean().item())
        
        return output
    
    def get_output_interpretation(self, output: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        解释输出向量的含义
        
        输出结构:
        - [0:8]: 运动控制
        - [8:15]: 行为选择
        - [15:20]: 内部调节
        - [20:32]: 记忆/信息素输出
        """
        # 运动控制（8维）
        motor_control = output[:, 0:8]
        
        # 行为选择（7维 - 对应7种行为）
        behavior_logits = output[:, 8:15]
        behavior_probs = F.softmax(behavior_logits, dim=-1)
        
        # 内部调节（5维）
        internal_reg = torch.sigmoid(output[:, 15:20])
        
        # 记忆输出（12维 - 信息素标记等）
        memory_out = output[:, 20:32]
        
        return {
            'motor_control': motor_control,
            'behavior_logits': behavior_logits,
            'behavior_probs': behavior_probs,
            'internal_reg': internal_reg,
            'memory_out': memory_out
        }
    
    def reset_internal_state(self):
        """重置内部状态"""
        nn.init.normal_(self.internal_memory, mean=0, std=0.01)
        self.spectral_manager.current_d_s = 4.0
        self.spectral_manager.d_s_history = []
        self.spectral_manager.complexity_history = []
        self.torsion_energy_history = []
        self.spectral_dim_history = []
        self.flow_gate_history = []
    
    def get_architecture_info(self) -> Dict:
        """获取架构信息"""
        return {
            'total_params': self.total_params,
            'target_params': 1360000,
            'param_breakdown': self.param_breakdown,
            'input_dim': self.input_dim,
            'reciprocal_dim': self.reciprocal_dim,
            'internal_dim': self.internal_dim,
            'output_dim': self.output_dim,
            'n_reciprocal_layers': self.n_reciprocal_layers,
            'n_internal_layers': self.n_internal_layers,
            'compression_ratio': self.total_params / 1363  # 相对于原始反射虫的压缩比
        }


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("超级TNN核心测试")
    print("=" * 60)
    
    # 创建核心
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"使用设备: {device}")
    
    brain = SuperTNNCore(device=device)
    info = brain.get_architecture_info()
    
    print("\n架构信息:")
    for key, value in info.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v:,}")
        else:
            print(f"  {key}: {value:,}" if isinstance(value, int) else f"  {key}: {value}")
    
    # 测试前向传播
    print("\n" + "=" * 60)
    print("前向传播测试")
    test_input = torch.randn(2, 32, device=device)
    output = brain(test_input)
    
    print(f"输入形状: {test_input.shape}")
    print(f"输出形状: {output.shape}")
    
    # 输出解释
    interpretation = brain.get_output_interpretation(output)
    print("\n输出解释:")
    for key, value in interpretation.items():
        print(f"  {key}: {value.shape}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
