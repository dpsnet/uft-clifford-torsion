"""
TNN-数字果蝇核心实现
约250K参数，专注个体复杂行为涌现

架构:
- 感觉层: 模拟果蝇感觉系统
  * 复眼视觉: 32×32像素，运动检测（模仿果蝇视觉通路）
  * 触角化学: 16通道嗅觉梯度
  * 机械感受器: 身体姿态、腿部触觉
  * 内部状态: 饥饿、能量、应激

- 神经处理层（核心TNN）:
  * 互反空间: 64维（快速反射）
  * 内部空间: 256-512维（复杂决策）
  * 层数: 12-16层
  * 扭转阶数: 3-5阶
  * 短期可塑性（STP）模拟突触动态

- 运动输出层:
  * 6条腿控制（每条腿: 抬起/放下/摆动）
  * 翅膀控制（展开/收起/振动频率）
  * 触角控制（伸展/理毛动作）
  * 口器控制（proboscis伸出/收回）
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field
from enum import Enum


class BehaviorState(Enum):
    """果蝇行为状态枚举"""
    IDLE = "idle"           # 静止
    WALKING = "walking"     # 行走
    GROOMING = "grooming"   # 理毛
    FORAGING = "foraging"   # 觅食
    ESCAPING = "escaping"   # 逃跑
    FEEDING = "feeding"     # 进食
    RESTING = "resting"     # 休息


@dataclass
class FlyInternalState:
    """果蝇内部生理状态"""
    # 能量代谢
    energy: float = 100.0
    hunger: float = 0.0        # 饥饿度 (0-100)
    metabolic_rate: float = 1.0
    
    # 应激与压力
    stress: float = 0.0        # 应激水平
    arousal: float = 0.5       # 唤醒度
    
    # 健康状态
    health: float = 100.0
    cleanliness: float = 100.0  # 清洁度（影响理毛需求）
    
    # 行为状态
    current_behavior: BehaviorState = BehaviorState.IDLE
    behavior_duration: int = 0   # 当前行为持续时间
    
    # 位置记忆
    last_food_location: Optional[Tuple[float, float]] = None
    danger_memory: List[Tuple[float, float, float]] = field(default_factory=list)  # (x, y, intensity)
    
    def update(self, dt: float = 1.0):
        """更新内部状态"""
        # 基础代谢
        self.energy -= self.metabolic_rate * dt * 0.1
        self.energy = np.clip(self.energy, 0, 100)
        
        # 饥饿度更新
        self.hunger = 100 - self.energy
        
        # 应激衰减
        self.stress *= 0.95
        
        # 清洁度缓慢下降
        self.cleanliness -= 0.05 * dt
        self.cleanliness = np.clip(self.cleanliness, 0, 100)
        
        self.behavior_duration += 1
    
    def add_danger_memory(self, x: float, y: float, intensity: float, max_memories: int = 5):
        """添加危险记忆"""
        self.danger_memory.append((x, y, intensity))
        self.danger_memory.sort(key=lambda t: t[2], reverse=True)
        self.danger_memory = self.danger_memory[:max_memories]


@dataclass
class LegState:
    """单条腿的状态"""
    leg_id: int
    
    # 关节角度 (度)
    coxa_angle: float = 0.0     # 基节
    femur_angle: float = 0.0    # 股节
    tibia_angle: float = 0.0    # 胫节
    
    # 接触状态
    is_stance: bool = True      # 支撑期（着地）
    is_swing: bool = False      # 摆动期（抬起）
    is_touching: bool = False   # 是否接触地面
    
    # 触觉传感器
    touch_intensity: float = 0.0
    
    def reset(self):
        """重置腿状态"""
        self.coxa_angle = 0.0
        self.femur_angle = 0.0
        self.tibia_angle = 0.0
        self.is_stance = True
        self.is_swing = False
        self.is_touching = False
        self.touch_intensity = 0.0


class AdaptiveSpectralDimension:
    """
    自适应谱维管理器（果蝇优化版）
    支持快速响应（逃跑）vs 精细处理（理毛）的模式切换
    """
    
    def __init__(
        self,
        d_s_min: float = 2.0,
        d_s_max: float = 6.0,
        adaptation_rate: float = 0.1,  # 更快的适应
        device='cpu'
    ):
        self.d_s_min = d_s_min
        self.d_s_max = d_s_max
        self.adaptation_rate = adaptation_rate
        self.device = device
        
        self.current_d_s = 3.5
        self.d_s_history = []
        self.complexity_history = []
        
        # 行为相关的谱维偏好
        self.behavior_spectral_prefs = {
            BehaviorState.IDLE: 2.5,
            BehaviorState.WALKING: 3.0,
            BehaviorState.FORAGING: 3.5,
            BehaviorState.GROOMING: 4.5,  # 理毛需要精细处理
            BehaviorState.ESCAPING: 2.0,   # 逃跑需要快速响应
            BehaviorState.FEEDING: 3.0,
            BehaviorState.RESTING: 2.0
        }
    
    def update(self, input_complexity: float, behavior: BehaviorState, 
               threat_level: float = 0.0) -> float:
        """
        根据输入复杂度和行为状态更新谱维
        
        Args:
            input_complexity: 输入复杂度（0-1）
            behavior: 当前行为状态
            threat_level: 威胁水平（0-1），影响逃跑响应
        """
        # 基础目标谱维
        behavior_pref = self.behavior_spectral_prefs.get(behavior, 3.0)
        
        # 根据输入复杂度调整
        complexity_factor = 1.0 + input_complexity * 0.5
        
        # 威胁紧急情况降低谱维以加速响应
        threat_factor = 1.0 - threat_level * 0.5
        
        d_target = behavior_pref * complexity_factor * threat_factor
        d_target = np.clip(d_target, self.d_s_min, self.d_s_max)
        
        # 平滑更新
        self.current_d_s = (1 - self.adaptation_rate) * self.current_d_s + \
                           self.adaptation_rate * d_target
        
        self.d_s_history.append(self.current_d_s)
        self.complexity_history.append(input_complexity)
        
        return self.current_d_s


class PlasticTorsionField(nn.Module):
    """
    可塑扭转场模块（果蝇优化版）
    支持短期可塑性（STP）模拟突触动态
    
    STP机制参考果蝇神经递质动态:
    - 促进（facilitation）: 连续刺激增强响应
    - 抑制（depression）: 连续刺激减弱响应
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        torsion_order: int = 4,
        torsion_strength: float = 0.1,
        enable_stp: bool = True,
        stp_tau_fac: float = 1.5,    # 促进时间常数
        stp_tau_rec: float = 0.2,    # 恢复时间常数
        stp_U: float = 0.15,          # 基础释放概率
        device='cpu'
    ):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.torsion_order = torsion_order
        self.device = device
        self.enable_stp = enable_stp
        
        # 基础权重
        self.weight = nn.Parameter(
            torch.randn(out_features, in_features, device=device) * 0.1
        )
        self.bias = nn.Parameter(torch.zeros(out_features, device=device))
        
        # 扭转场（多阶）
        self.torsion_field = nn.Parameter(
            torch.randn(torsion_order, out_features, in_features, device=device) 
            * torsion_strength
        )
        
        # 动态扭转系数
        self.torsion_coupling = nn.Parameter(torch.tensor(0.3, device=device))
        
        # 短期可塑性参数
        if enable_stp:
            self.stp_tau_fac = stp_tau_fac
            self.stp_tau_rec = stp_tau_rec
            self.stp_U = stp_U
            
            # STP状态变量
            self.register_buffer('x', torch.ones(1, out_features, device=device))  # 可用资源
            self.register_buffer('u', torch.zeros(1, out_features, device=device))  # 促进变量
        
        # 谱维调制
        self.spectral_gate = nn.Parameter(torch.tensor(0.5, device=device))
    
    def forward(self, x_input: torch.Tensor, spectral_dim: float = 3.5) -> torch.Tensor:
        """前向传播，包含STP和扭转效应"""
        batch_size = x_input.shape[0]
        
        # 基础线性变换
        base_output = F.linear(x_input, self.weight, self.bias)
        
        # 扭转修正
        torsion_correction = torch.zeros_like(base_output)
        
        for n in range(self.torsion_order):
            torsion_n = self.torsion_field[n]
            linear_out = F.linear(x_input, torsion_n)
            
            # 谱维调制相位
            phase_factor = 2 * np.pi * (n + 1) * spectral_dim / self.torsion_order
            phase = linear_out + phase_factor
            
            # 扭转效应
            twisted = torch.sin(phase) * linear_out / (n + 1)
            torsion_correction += twisted
        
        # 谱维门控
        spectral_gate_val = torch.sigmoid(self.spectral_gate)
        gate_factor = spectral_gate_val * (spectral_dim / 3.5)
        
        # 扭转耦合
        coupling = torch.sigmoid(self.torsion_coupling)
        
        # 组合输出
        output = base_output + coupling * gate_factor * torsion_correction
        
        # 应用STP
        if self.enable_stp and self.training:
            output = self._apply_stp(output)
        
        return output
    
    def _apply_stp(self, activation: torch.Tensor) -> torch.Tensor:
        """
        应用短期可塑性（STP）
        
        基于Tsodyks-Markram模型简化版:
        - x: 可用神经递质资源 (0-1)
        - u: 促进变量 (易化)
        - 释放量 = x * u
        """
        batch_size = activation.shape[0]
        
        # 扩展状态变量
        x = self.x.expand(batch_size, -1)
        u = self.u.expand(batch_size, -1)
        
        # 计算释放概率（促进增加释放）
        u_next = self.stp_U + u * (1 - self.stp_U) * np.exp(-1.0 / self.stp_tau_fac)
        release = x * u_next
        
        # 更新资源
        x_next = x - release + (1 - x) * (1 - np.exp(-1.0 / self.stp_tau_rec))
        
        # 应用STP到输出
        stp_modulated = activation * release
        
        # 更新状态（仅在训练时）
        if self.training:
            with torch.no_grad():
                self.x = x_next[0:1].detach()
                self.u = u_next[0:1].detach()
        
        return stp_modulated
    
    def reset_stp(self):
        """重置STP状态"""
        if self.enable_stp:
            self.x.fill_(1.0)
            self.u.fill_(0.0)
    
    def get_torsion_energy(self) -> torch.Tensor:
        """计算扭转场能量"""
        return torch.sum(self.torsion_field ** 2)


class TNNFlyBrain(nn.Module):
    """
    TNN-果蝇大脑（约250K参数）
    
    架构:
    1. 输入投影层: 感觉输入 -> 互反空间
    2. 互反空间处理: 64维，快速反射（6-8层）
    3. 内部空间处理: 128维，复杂决策（6-8层）
    4. 跨空间耦合: 互反 <-> 内部
    5. 运动输出层: 控制6条腿 + 翅膀 + 触角 + 口器
    """
    
    def __init__(
        self,
        # 感觉输入维度
        visual_dim: int = 1024,      # 32×32 复眼视觉
        olfactory_dim: int = 16,     # 16通道嗅觉
        mechano_dim: int = 18,       # 6条腿 × 3触觉 + 身体姿态
        internal_dim_input: int = 4, # 饥饿、能量、应激、清洁度
        
        # 网络架构
        reciprocal_dim: int = 64,
        internal_dim: int = 128,
        n_reciprocal_layers: int = 4,
        n_internal_layers: int = 6,
        torsion_order: int = 3,
        torsion_strength: float = 0.1,
        
        # 输出维度
        leg_output_dim: int = 18,     # 6条腿 × 3控制
        wing_output_dim: int = 3,     # 展开/收起/振动频率
        antenna_output_dim: int = 2,  # 伸展/理毛
        proboscis_dim: int = 1,       # 口器伸出/收回
        behavior_dim: int = 7,        # 7种行为状态
        
        device='cpu'
    ):
        super().__init__()
        
        self.visual_dim = visual_dim
        self.olfactory_dim = olfactory_dim
        self.mechano_dim = mechano_dim
        self.internal_dim_input = internal_dim_input
        
        self.reciprocal_dim = reciprocal_dim
        self.internal_dim = internal_dim
        self.n_reciprocal_layers = n_reciprocal_layers
        self.n_internal_layers = n_internal_layers
        self.device = device
        
        # 总输入维度
        total_input_dim = visual_dim + olfactory_dim + mechano_dim + internal_dim_input
        
        # 总输出维度
        total_output_dim = leg_output_dim + wing_output_dim + antenna_output_dim + \
                          proboscis_dim + behavior_dim
        
        # 谱维管理器
        self.spectral_manager = AdaptiveSpectralDimension(device=device)
        
        # === 输入投影层 ===
        # 视觉特征提取（简化）
        self.visual_encoder = nn.Sequential(
            nn.Linear(visual_dim, 64),
            nn.LayerNorm(64),
            nn.GELU()
        )
        
        # 嗅觉特征提取
        self.olfactory_encoder = nn.Sequential(
            nn.Linear(olfactory_dim, 32),
            nn.LayerNorm(32),
            nn.GELU()
        )
        
        # 机械感受器处理
        self.mechano_encoder = nn.Sequential(
            nn.Linear(mechano_dim, 32),
            nn.LayerNorm(32),
            nn.GELU()
        )
        
        # 内部状态处理
        self.internal_encoder = nn.Sequential(
            nn.Linear(internal_dim_input, 16),
            nn.LayerNorm(16),
            nn.GELU()
        )
        
        # 融合层 -> 互反空间
        self.input_fusion = nn.Sequential(
            nn.Linear(64 + 32 + 32 + 16, reciprocal_dim),
            nn.LayerNorm(reciprocal_dim)
        )
        
        # === 互反空间处理层（快速反射）===
        self.reciprocal_layers = nn.ModuleList()
        self.reciprocal_norms = nn.ModuleList()
        
        for i in range(n_reciprocal_layers):
            # 逐层降低扭转阶数以提高效率
            layer_order = max(2, torsion_order - i // 3)
            layer_strength = torsion_strength * (1.0 - 0.05 * i)
            
            self.reciprocal_layers.append(
                PlasticTorsionField(
                    reciprocal_dim, reciprocal_dim,
                    torsion_order=layer_order,
                    torsion_strength=layer_strength,
                    enable_stp=True,
                    device=device
                )
            )
            self.reciprocal_norms.append(nn.LayerNorm(reciprocal_dim))
        
        # === 内部空间处理层（复杂决策）===
        self.internal_layers = nn.ModuleList()
        self.internal_norms = nn.ModuleList()
        
        for i in range(n_internal_layers):
            layer_order = torsion_order if i < n_internal_layers // 2 else max(2, torsion_order - 1)
            
            self.internal_layers.append(
                PlasticTorsionField(
                    internal_dim, internal_dim,
                    torsion_order=layer_order,
                    torsion_strength=torsion_strength * 0.8,
                    enable_stp=True,
                    device=device
                )
            )
            self.internal_norms.append(nn.LayerNorm(internal_dim))
        
        # === 跨空间耦合 ===
        self.reciprocal_to_internal = nn.Sequential(
            nn.Linear(reciprocal_dim, 128),
            nn.GELU(),
            nn.Linear(128, internal_dim)
        )
        
        self.internal_to_reciprocal = nn.Sequential(
            nn.Linear(internal_dim, 128),
            nn.GELU(),
            nn.Linear(128, reciprocal_dim)
        )
        
        # 流动门控
        self.flow_gates = nn.Parameter(torch.ones(n_reciprocal_layers // 2) * 0.5)
        
        # === 内部记忆状态 ===
        self.register_buffer(
            'internal_memory',
            torch.randn(1, internal_dim, device=device) * 0.01
        )
        
        # === 运动输出层 ===
        # 腿部控制（从互反空间）
        self.leg_controller = nn.Sequential(
            nn.Linear(reciprocal_dim, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Linear(64, leg_output_dim)
        )
        
        # 翅膀控制
        self.wing_controller = nn.Sequential(
            nn.Linear(reciprocal_dim + internal_dim, 32),
            nn.LayerNorm(32),
            nn.GELU(),
            nn.Linear(32, wing_output_dim)
        )
        
        # 触角控制（理毛等精细动作需要内部空间参与）
        self.antenna_controller = nn.Sequential(
            nn.Linear(reciprocal_dim + internal_dim, 32),
            nn.LayerNorm(32),
            nn.GELU(),
            nn.Linear(32, antenna_output_dim)
        )
        
        # 口器控制
        self.proboscis_controller = nn.Sequential(
            nn.Linear(internal_dim, 16),
            nn.LayerNorm(16),
            nn.GELU(),
            nn.Linear(16, proboscis_dim)
        )
        
        # 行为选择（从内部空间）
        self.behavior_selector = nn.Sequential(
            nn.Linear(internal_dim, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Linear(64, behavior_dim)
        )
        
        # 输出门控
        self.output_gate = nn.Parameter(torch.tensor(0.5, device=device))
        
        # 统计信息
        self._count_parameters()
        
        # 历史记录
        self.reset_history()
    
    def _count_parameters(self):
        """统计参数数量"""
        self.total_params = sum(p.numel() for p in self.parameters())
        
        # 分层统计
        self.param_breakdown = {
            'visual_encoder': sum(p.numel() for p in self.visual_encoder.parameters()),
            'olfactory_encoder': sum(p.numel() for p in self.olfactory_encoder.parameters()),
            'mechano_encoder': sum(p.numel() for p in self.mechano_encoder.parameters()),
            'internal_encoder': sum(p.numel() for p in self.internal_encoder.parameters()),
            'input_fusion': sum(p.numel() for p in self.input_fusion.parameters()),
            'reciprocal_layers': sum(p.numel() for p in self.reciprocal_layers.parameters()),
            'internal_layers': sum(p.numel() for p in self.internal_layers.parameters()),
            'cross_space': sum(p.numel() for p in self.reciprocal_to_internal.parameters()) + \
                          sum(p.numel() for p in self.internal_to_reciprocal.parameters()),
            'leg_controller': sum(p.numel() for p in self.leg_controller.parameters()),
            'wing_controller': sum(p.numel() for p in self.wing_controller.parameters()),
            'antenna_controller': sum(p.numel() for p in self.antenna_controller.parameters()),
            'proboscis_controller': sum(p.numel() for p in self.proboscis_controller.parameters()),
            'behavior_selector': sum(p.numel() for p in self.behavior_selector.parameters()),
        }
    
    def forward(
        self, 
        visual_input: torch.Tensor,
        olfactory_input: torch.Tensor,
        mechano_input: torch.Tensor,
        internal_input: torch.Tensor,
        current_behavior: BehaviorState = BehaviorState.IDLE,
        threat_level: float = 0.0
    ) -> Dict[str, torch.Tensor]:
        """
        前向传播
        
        Args:
            visual_input: [batch, 1024] 32×32视觉输入
            olfactory_input: [batch, 16] 嗅觉输入
            mechano_input: [batch, 18] 机械感受器输入
            internal_input: [batch, 4] 内部状态
            current_behavior: 当前行为状态
            threat_level: 威胁水平
        """
        batch_size = visual_input.shape[0]
        
        # 更新谱维
        input_complexity = torch.cat([
            visual_input.std(dim=1),
            olfactory_input.std(dim=1),
            mechano_input.std(dim=1)
        ]).mean().item()
        
        d_s = self.spectral_manager.update(input_complexity, current_behavior, threat_level)
        self.spectral_dim_history.append(d_s)
        
        # === 编码感觉输入 ===
        visual_feat = self.visual_encoder(visual_input)
        olfactory_feat = self.olfactory_encoder(olfactory_input)
        mechano_feat = self.mechano_encoder(mechano_input)
        internal_feat = self.internal_encoder(internal_input)
        
        # 融合到互反空间
        fused_input = torch.cat([visual_feat, olfactory_feat, mechano_feat, internal_feat], dim=-1)
        x_reciprocal = self.input_fusion(fused_input)
        x_reciprocal = F.gelu(x_reciprocal)
        
        # 扩展内部记忆
        x_internal = self.internal_memory.expand(batch_size, -1)
        
        # === 互反-内部耦合循环 ===
        for i, (rec_layer, rec_norm) in enumerate(zip(self.reciprocal_layers, self.reciprocal_norms)):
            # 互反空间处理
            h_reciprocal = rec_layer(x_reciprocal, d_s)
            h_reciprocal = rec_norm(h_reciprocal)
            h_reciprocal = F.gelu(h_reciprocal)
            
            # 残差连接
            x_reciprocal = x_reciprocal + 0.1 * h_reciprocal
            
            # 跨空间流动（每隔一层）
            if i % 2 == 0 and i // 2 < len(self.internal_layers):
                flow_gate = torch.sigmoid(self.flow_gates[i // 2])
                
                # 互反 -> 内部
                flow_to_internal = self.reciprocal_to_internal(x_reciprocal)
                
                # 内部空间处理
                int_layer = self.internal_layers[i // 2]
                int_norm = self.internal_norms[i // 2]
                
                h_internal = int_layer(x_internal, d_s)
                h_internal = int_norm(h_internal)
                h_internal = F.gelu(h_internal)
                
                # 更新内部记忆
                x_internal = x_internal + 0.1 * h_internal + flow_gate * flow_to_internal
                
                # 内部 -> 互反
                flow_to_reciprocal = self.internal_to_reciprocal(x_internal)
                x_reciprocal = x_reciprocal + flow_gate * flow_to_reciprocal
        
        # === 生成输出 ===
        # 腿部控制
        leg_output = self.leg_controller(x_reciprocal)
        
        # 合并互反和内部空间用于高级控制
        combined_state = torch.cat([x_reciprocal, x_internal], dim=-1)
        
        # 翅膀控制
        wing_output = self.wing_controller(combined_state)
        
        # 触角控制
        antenna_output = self.antenna_controller(combined_state)
        
        # 口器控制（仅从内部空间）
        proboscis_output = self.proboscis_controller(x_internal)
        
        # 行为选择
        behavior_logits = self.behavior_selector(x_internal)
        behavior_probs = F.softmax(behavior_logits, dim=-1)
        
        # 输出门控
        gate = torch.sigmoid(self.output_gate)
        
        # 记录历史
        total_energy = sum(layer.get_torsion_energy().item() for layer in 
                          list(self.reciprocal_layers) + list(self.internal_layers))
        self.torsion_energy_history.append(total_energy)
        self.flow_gate_history.append(torch.sigmoid(self.flow_gates).mean().item())
        
        return {
            'leg_output': leg_output * gate,
            'wing_output': wing_output * gate,
            'antenna_output': antenna_output * gate,
            'proboscis_output': torch.sigmoid(proboscis_output) * gate,
            'behavior_logits': behavior_logits,
            'behavior_probs': behavior_probs,
            'reciprocal_state': x_reciprocal,
            'internal_state': x_internal,
            'spectral_dim': d_s
        }
    
    def reset_history(self):
        """重置历史记录"""
        self.torsion_energy_history = []
        self.spectral_dim_history = []
        self.flow_gate_history = []
        self.spectral_manager.d_s_history = []
        self.spectral_manager.complexity_history = []
    
    def reset_stp(self):
        """重置所有STP状态"""
        for layer in self.reciprocal_layers:
            layer.reset_stp()
        for layer in self.internal_layers:
            layer.reset_stp()
    
    def get_architecture_info(self) -> Dict:
        """获取架构信息"""
        return {
            'total_params': self.total_params,
            'target_params': 250000,
            'param_breakdown': self.param_breakdown,
            'reciprocal_dim': self.reciprocal_dim,
            'internal_dim': self.internal_dim,
            'n_reciprocal_layers': self.n_reciprocal_layers,
            'n_internal_layers': self.n_internal_layers,
            'compression_ratio': self.total_params / 250000
        }
    
    def interpret_output(self, output: Dict[str, torch.Tensor]) -> Dict:
        """
        解释输出含义
        
        输出结构:
        - leg_output: [batch, 18] - 6条腿 × 3关节控制
        - wing_output: [batch, 3] - 展开/收起/振动频率
        - antenna_output: [batch, 2] - 触角伸展/理毛动作
        - proboscis_output: [batch, 1] - 口器伸出程度
        - behavior_probs: [batch, 7] - 7种行为概率
        """
        leg_output = output['leg_output']
        wing_output = output['wing_output']
        antenna_output = output['antenna_output']
        proboscis_output = output['proboscis_output']
        behavior_probs = output['behavior_probs']
        
        batch_size = leg_output.shape[0]
        
        # 解析腿部控制
        leg_controls = []
        for i in range(6):
            start_idx = i * 3
            leg_controls.append({
                'coxa': leg_output[:, start_idx],
                'femur': leg_output[:, start_idx + 1],
                'tibia': leg_output[:, start_idx + 2]
            })
        
        # 解析翅膀控制
        wing_control = {
            'spread': torch.sigmoid(wing_output[:, 0]),
            'tuck': torch.sigmoid(wing_output[:, 1]),
            'vibration_freq': torch.sigmoid(wing_output[:, 2])
        }
        
        # 解析触角控制
        antenna_control = {
            'extension': torch.sigmoid(antenna_output[:, 0]),
            'grooming_motion': torch.tanh(antenna_output[:, 1])
        }
        
        # 解析行为选择
        behavior_names = ['idle', 'walking', 'grooming', 'foraging', 'escaping', 'feeding', 'resting']
        behavior_selection = {
            name: behavior_probs[:, i] for i, name in enumerate(behavior_names)
        }
        selected_indices = torch.argmax(behavior_probs, dim=-1)
        selected_behavior = [behavior_names[i] for i in selected_indices.tolist()]
        
        return {
            'leg_controls': leg_controls,
            'wing_control': wing_control,
            'antenna_control': antenna_control,
            'proboscis_extension': proboscis_output,
            'behavior_selection': behavior_selection,
            'selected_behavior': selected_behavior,
            'behavior_confidence': torch.max(behavior_probs, dim=-1).values
        }


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("TNN-数字果蝇大脑测试")
    print("=" * 60)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"使用设备: {device}")
    
    # 创建大脑
    brain = TNNFlyBrain(device=device)
    info = brain.get_architecture_info()
    
    print("\n架构信息:")
    print(f"  总参数: {info['total_params']:,}")
    print(f"  目标参数: {info['target_params']:,}")
    print(f"  参数比: {info['compression_ratio']:.2%}")
    print(f"  互反空间维度: {info['reciprocal_dim']}")
    print(f"  内部空间维度: {info['internal_dim']}")
    print(f"  互反层数: {info['n_reciprocal_layers']}")
    print(f"  内部层数: {info['n_internal_layers']}")
    
    print("\n参数分布:")
    for key, value in info['param_breakdown'].items():
        percentage = value / info['total_params'] * 100
        print(f"  {key}: {value:,} ({percentage:.1f}%)")
    
    # 测试前向传播
    print("\n" + "=" * 60)
    print("前向传播测试")
    
    batch_size = 2
    visual_input = torch.randn(batch_size, 1024, device=device)
    olfactory_input = torch.randn(batch_size, 16, device=device)
    mechano_input = torch.randn(batch_size, 18, device=device)
    internal_input = torch.randn(batch_size, 4, device=device)
    
    output = brain(
        visual_input, olfactory_input, mechano_input, internal_input,
        current_behavior=BehaviorState.WALKING
    )
    
    print(f"\n输入:")
    print(f"  视觉: {visual_input.shape}")
    print(f"  嗅觉: {olfactory_input.shape}")
    print(f"  机械: {mechano_input.shape}")
    print(f"  内部: {internal_input.shape}")
    
    print(f"\n输出:")
    for key, value in output.items():
        if isinstance(value, torch.Tensor):
            print(f"  {key}: {value.shape}")
    
    # 输出解释
    interpretation = brain.interpret_output(output)
    print(f"\n行为选择: {interpretation['selected_behavior']}")
    print(f"行为置信度: {interpretation['behavior_confidence'].tolist()}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
