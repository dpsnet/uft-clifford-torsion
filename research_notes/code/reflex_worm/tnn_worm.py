"""
微型TNN"反射虫" - TNN核心实现
约2000参数，用于验证"结构即行为"假说
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple, List, Dict


class SpectralDimension:
    """
    谱维管理器（简化版）
    用于微型TNN，支持2-4维谱维
    """
    
    def __init__(
        self,
        d_s_min: float = 2.0,
        d_s_max: float = 4.0,
        device='cpu'
    ):
        self.d_s_min = d_s_min
        self.d_s_max = d_s_max
        self.device = device
        
        # 当前谱维
        self.current_d_s = 4.0
        self.d_s_history = []
        
    def update(self, input_complexity: float):
        """根据输入复杂度更新谱维"""
        # 复杂度到谱维的映射
        d_target = self.d_s_min + input_complexity * (self.d_s_max - self.d_s_min)
        # 平滑更新
        self.current_d_s = 0.9 * self.current_d_s + 0.1 * d_target
        self.current_d_s = np.clip(self.current_d_s, self.d_s_min, self.d_s_max)
        self.d_s_history.append(self.current_d_s)
        return self.current_d_s


class MiniTorsionField(nn.Module):
    """
    微型扭转场模块
    互反空间：4维
    内部空间：可配置
    扭转阶数：2-3
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        torsion_order: int = 2,
        torsion_strength: float = 0.1,
        device='cpu'
    ):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.torsion_order = torsion_order
        self.device = device
        
        # 基础权重（互反空间）
        self.weight = nn.Parameter(
            torch.randn(out_features, in_features, device=device) * 0.1
        )
        self.bias = nn.Parameter(torch.zeros(out_features, device=device))
        
        # 扭转场（内部空间耦合）
        # 形状: [torsion_order, out_features, in_features]
        self.torsion_field = nn.Parameter(
            torch.randn(
                torsion_order,
                out_features,
                in_features,
                device=device
            ) * torsion_strength
        )
        
        # 扭转耦合系数（可学习）
        self.torsion_coupling = nn.Parameter(torch.tensor(0.5, device=device))
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播，包含扭转效应"""
        # 基础线性变换
        base_output = F.linear(x, self.weight, self.bias)
        
        # 扭转修正
        torsion_correction = torch.zeros_like(base_output)
        
        for n in range(self.torsion_order):
            torsion_n = self.torsion_field[n]
            # 计算扭转相位
            linear_out = F.linear(x, torsion_n)
            phase = 2 * np.pi * (n + 1) * linear_out / (linear_out.abs().mean() + 1e-8)
            twisted = torch.sin(phase) * linear_out
            torsion_correction += twisted / (n + 1)
        
        # 组合基础流和扭转流
        coupling = torch.sigmoid(self.torsion_coupling)
        output = base_output + coupling * torsion_correction
        
        return output
    
    def get_torsion_energy(self) -> torch.Tensor:
        """计算扭转场能量（用于分析）"""
        return torch.sum(self.torsion_field ** 2)


class TNNWormCore(nn.Module):
    """
    TNN反射虫核心
    
    架构:
    - 输入层: 6个感觉神经元
      * 左/右光感受器
      * 前/后触觉
      * 亮度梯度(x, y)
    
    - 中间层: TNN核心
      * 互反空间: 4维
      * 内部空间: 16维
      * 扭转阶数: 2-3阶
    
    - 输出层: 4个运动神经元
      * 左转/右转
      * 前进/后退
      * 速度控制
    """
    
    def __init__(
        self,
        input_dim: int = 6,
        reciprocal_dim: int = 4,
        internal_dim: int = 16,
        output_dim: int = 4,
        torsion_order: int = 2,
        torsion_strength: float = 0.1,
        device='cpu'
    ):
        super().__init__()
        self.input_dim = input_dim
        self.reciprocal_dim = reciprocal_dim
        self.internal_dim = internal_dim
        self.output_dim = output_dim
        self.device = device
        
        # 谱维管理器
        self.spectral_manager = SpectralDimension(device=device)
        
        # 输入投影（到互反空间）
        self.input_projection = nn.Linear(input_dim, reciprocal_dim)
        
        # 互反-内部耦合层（2层）
        self.layer1_reciprocal = MiniTorsionField(
            reciprocal_dim, reciprocal_dim,
            torsion_order=torsion_order,
            torsion_strength=torsion_strength,
            device=device
        )
        self.layer1_internal = MiniTorsionField(
            internal_dim, internal_dim,
            torsion_order=min(torsion_order+1, 3),
            torsion_strength=torsion_strength * 0.8,
            device=device
        )
        
        # 跨空间映射
        self.reciprocal_to_internal = nn.Linear(reciprocal_dim, internal_dim)
        self.internal_to_reciprocal = nn.Linear(internal_dim, reciprocal_dim)
        
        # 流动门控
        self.flow_gate = nn.Parameter(torch.tensor(0.5, device=device))
        
        # 内部空间记忆
        self.internal_memory = nn.Parameter(
            torch.randn(1, internal_dim, device=device) * 0.01
        )
        
        # 输出投影
        self.output_projection = nn.Sequential(
            nn.Linear(reciprocal_dim, 8),
            nn.GELU(),
            nn.Linear(8, output_dim)
        )
        
        # 统计信息
        self.total_params = sum(p.numel() for p in self.parameters())
        self.torsion_energy_history = []
        self.spectral_dim_history = []
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        x: [batch, input_dim] 传感器输入
        returns: [batch, output_dim] 运动输出
        """
        batch_size = x.shape[0]
        
        # 更新谱维（基于输入复杂度）
        input_complexity = x.std(dim=1).mean().item()
        d_s = self.spectral_manager.update(input_complexity)
        self.spectral_dim_history.append(d_s)
        
        # 输入投影到互反空间
        x_reciprocal = self.input_projection(x)
        x_reciprocal = F.gelu(x_reciprocal)
        
        # 扩展内部记忆
        x_internal = self.internal_memory.expand(batch_size, -1)
        
        # 互反空间变换
        h_reciprocal = self.layer1_reciprocal(x_reciprocal)
        h_reciprocal = F.layer_norm(h_reciprocal, h_reciprocal.shape[1:])
        h_reciprocal = F.gelu(h_reciprocal)
        
        # 内部空间变换
        h_internal = self.layer1_internal(x_internal)
        h_internal = F.layer_norm(h_internal, h_internal.shape[1:])
        h_internal = F.gelu(h_internal)
        
        # 跨维流动
        gate = torch.sigmoid(self.flow_gate)
        
        flow_to_internal = self.reciprocal_to_internal(h_reciprocal)
        h_internal = h_internal + gate * flow_to_internal
        
        flow_to_reciprocal = self.internal_to_reciprocal(h_internal)
        h_reciprocal = h_reciprocal + gate * flow_to_reciprocal
        
        # 输出投影
        output = self.output_projection(h_reciprocal)
        
        # 记录扭转能量
        torsion_energy = (
            self.layer1_reciprocal.get_torsion_energy().item() +
            self.layer1_internal.get_torsion_energy().item()
        )
        self.torsion_energy_history.append(torsion_energy)
        
        return output
    
    def get_motor_commands(self, output: torch.Tensor) -> Dict[str, float]:
        """
        将网络输出转换为运动命令
        output: [batch, 4] 网络输出
        returns: 运动命令字典
        """
        # 应用激活函数
        turn_left = torch.sigmoid(output[:, 0]).item()
        turn_right = torch.sigmoid(output[:, 1]).item()
        forward = torch.sigmoid(output[:, 2]).item()
        backward = torch.sigmoid(output[:, 3]).item()
        
        # 计算净转向和速度
        turn = turn_right - turn_left  # -1 到 1，正值为右转
        speed = forward - backward     # -1 到 1，正值为前进
        
        return {
            'turn': turn,
            'speed': speed,
            'turn_left': turn_left,
            'turn_right': turn_right,
            'forward': forward,
            'backward': backward
        }
    
    def reset_internal_state(self):
        """重置内部状态"""
        nn.init.normal_(self.internal_memory, mean=0, std=0.01)
        self.spectral_manager.current_d_s = 4.0
        self.spectral_manager.d_s_history = []
        self.torsion_energy_history = []
        self.spectral_dim_history = []
    
    def get_architecture_info(self) -> Dict:
        """获取架构信息"""
        return {
            'total_params': self.total_params,
            'input_dim': self.input_dim,
            'reciprocal_dim': self.reciprocal_dim,
            'internal_dim': self.internal_dim,
            'output_dim': self.output_dim,
            'torsion_order': self.layer1_reciprocal.torsion_order,
            'target_params_range': '1000-5000'
        }


class TNNWorm:
    """
    TNN反射虫完整实现
    包含TNN核心和物理状态
    """
    
    def __init__(
        self,
        x: float = 50.0,
        y: float = 50.0,
        heading: float = 0.0,
        torsion_config: Optional[Dict] = None,
        device='cpu'
    ):
        self.device = device
        
        # 物理状态
        self.x = x
        self.y = y
        self.heading = heading  # 弧度，0表示+x方向
        self.vx = 0.0
        self.vy = 0.0
        self.energy = 100.0
        
        # TNN核心
        torsion_order = torsion_config.get('torsion_order', 2) if torsion_config else 2
        torsion_strength = torsion_config.get('torsion_strength', 0.1) if torsion_config else 0.1
        
        self.brain = TNNWormCore(
            input_dim=6,
            reciprocal_dim=4,
            internal_dim=16,
            output_dim=4,
            torsion_order=torsion_order,
            torsion_strength=torsion_strength,
            device=device
        )
        
        # 运动历史（用于分析行为）
        self.trajectory = [(x, y)]
        self.sensor_history = []
        self.motor_history = []
        self.spectral_history = []
        
    def sense(self, environment) -> np.ndarray:
        """从环境获取感觉输入"""
        sensors = environment.get_sensor_readings(self.x, self.y, self.heading)
        self.sensor_history.append(sensors.copy())
        return sensors
    
    def think(self, sensor_input: np.ndarray) -> Dict[str, float]:
        """TNN处理感觉输入"""
        # 转换为tensor
        x = torch.tensor(sensor_input, dtype=torch.float32, device=self.device).unsqueeze(0)
        
        # TNN前向传播
        with torch.no_grad():
            output = self.brain(x)
            motor_commands = self.brain.get_motor_commands(output)
        
        self.motor_history.append(motor_commands)
        self.spectral_history.append(self.brain.spectral_manager.current_d_s)
        
        return motor_commands
    
    def act(self, motor_commands: Dict[str, float], dt: float = 0.1):
        """执行运动命令"""
        turn = motor_commands['turn']
        speed = motor_commands['speed']
        
        # 更新朝向（转向）
        max_turn_rate = np.pi / 4  # 最大转向速率
        self.heading += turn * max_turn_rate * dt * 10
        self.heading = self.heading % (2 * np.pi)
        
        # 更新速度
        max_speed = 2.0
        target_vx = speed * max_speed * np.cos(self.heading)
        target_vy = speed * max_speed * np.sin(self.heading)
        
        # 平滑速度变化
        self.vx = 0.8 * self.vx + 0.2 * target_vx
        self.vy = 0.8 * self.vy + 0.2 * target_vy
        
        # 能量消耗
        self.energy -= abs(speed) * 0.1
        self.energy = max(0, self.energy)
    
    def update(self, environment, dt: float = 0.1):
        """完整的感知-思考-行动循环"""
        # 感知
        sensors = self.sense(environment)
        
        # 思考
        motor_commands = self.think(sensors)
        
        # 行动
        self.act(motor_commands, dt)
        
        # 应用物理
        self.x, self.y, self.vx, self.vy = environment.apply_physics(
            self.x, self.y, self.vx, self.vy, dt
        )
        
        # 记录轨迹
        self.trajectory.append((self.x, self.y))
    
    def get_state(self) -> Dict:
        """获取当前状态"""
        return {
            'x': self.x,
            'y': self.y,
            'heading': self.heading,
            'vx': self.vx,
            'vy': self.vy,
            'energy': self.energy,
            'spectral_dim': self.brain.spectral_manager.current_d_s
        }
    
    def reset(self, x: float = 50.0, y: float = 50.0, heading: float = 0.0):
        """重置虫子状态"""
        self.x = x
        self.y = y
        self.heading = heading
        self.vx = 0.0
        self.vy = 0.0
        self.energy = 100.0
        self.trajectory = [(x, y)]
        self.sensor_history = []
        self.motor_history = []
        self.spectral_history = []
        self.brain.reset_internal_state()


# 测试代码
if __name__ == "__main__":
    print("TNN反射虫核心测试")
    print("=" * 50)
    
    # 创建TNN核心
    brain = TNNWormCore(device='cpu')
    info = brain.get_architecture_info()
    print(f"架构信息:")
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # 测试前向传播
    test_input = torch.randn(1, 6)
    output = brain(test_input)
    print(f"\n输入: {test_input.shape}")
    print(f"输出: {output.shape}")
    
    motor_commands = brain.get_motor_commands(output)
    print(f"\n运动命令:")
    for key, value in motor_commands.items():
        print(f"  {key}: {value:.3f}")
    
    # 创建完整虫子
    print("\n" + "=" * 50)
    print("完整虫子测试")
    worm = TNNWorm(device='cpu')
    print(f"虫子位置: ({worm.x:.1f}, {worm.y:.1f})")
    print(f"虫子朝向: {worm.heading:.2f} rad")
