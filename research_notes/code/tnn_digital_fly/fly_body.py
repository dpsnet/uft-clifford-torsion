"""
果蝇身体物理模型
模拟果蝇的身体结构、运动学和物理交互

果蝇身体结构:
- 身体: 椭圆体，长约2.5-3mm
- 6条腿: 每侧3条，分为前腿、中腿、后腿
- 翅膀: 2片，可展开/收起
- 触角: 2个，可运动用于触觉和理毛
- 口器: proboscis，用于进食
"""

import numpy as np
import torch
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum


class LegID(Enum):
    """腿部ID枚举"""
    FRONT_LEFT = 0
    MIDDLE_LEFT = 1
    BACK_LEFT = 2
    FRONT_RIGHT = 3
    MIDDLE_RIGHT = 4
    BACK_RIGHT = 5


@dataclass
class JointAngles:
    """关节角度"""
    coxa: float = 0.0      # 基节角度
    femur: float = 0.0     # 股节角度
    tibia: float = 0.0     # 胫节角度
    
    def to_array(self) -> np.ndarray:
        return np.array([self.coxa, self.femur, self.tibia])
    
    @classmethod
    def from_array(cls, arr: np.ndarray) -> 'JointAngles':
        return cls(coxa=arr[0], femur=arr[1], tibia=arr[2])


@dataclass
class LegKinematics:
    """腿部运动学状态"""
    angles: JointAngles = field(default_factory=JointAngles)
    foot_position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    is_stance: bool = True
    is_swing: bool = False
    touch_force: float = 0.0
    
    # 步态周期
    gait_phase: float = 0.0  # 0-1 步态相位
    
    def reset(self):
        self.angles = JointAngles()
        self.foot_position = np.zeros(3)
        self.is_stance = True
        self.is_swing = False
        self.touch_force = 0.0
        self.gait_phase = 0.0


class TripodGait:
    """
    三脚架步态控制器
    果蝇使用三脚架步态: 一组3条腿支撑时，另一组3条腿摆动
    
    步态模式:
    - 支撑组A: 前左、中右、后左
    - 支撑组B: 前右、中左、后右
    """
    
    TRIPOD_A = [LegID.FRONT_LEFT, LegID.MIDDLE_RIGHT, LegID.BACK_LEFT]
    TRIPOD_B = [LegID.FRONT_RIGHT, LegID.MIDDLE_LEFT, LegID.BACK_RIGHT]
    
    def __init__(
        self,
        stance_duration: float = 0.6,  # 支撑期占步态周期比例
        swing_duration: float = 0.4,   # 摆动期占步态周期比例
        step_frequency: float = 10.0   # 步频 (Hz)
    ):
        self.stance_duration = stance_duration
        self.swing_duration = swing_duration
        self.step_frequency = step_frequency
        self.cycle_time = 1.0 / step_frequency
        
        # 当前相位
        self.cycle_phase = 0.0
        
        # 腿状态
        self.leg_phases = {leg: 0.0 for leg in LegID}
        self.leg_in_stance = {leg: True for leg in LegID}
    
    def update(self, dt: float, speed_factor: float = 1.0):
        """
        更新步态周期
        
        Args:
            dt: 时间步长
            speed_factor: 速度因子 (0-2)，影响步频
        """
        # 更新周期相位
        effective_frequency = self.step_frequency * speed_factor
        phase_increment = effective_frequency * dt
        self.cycle_phase = (self.cycle_phase + phase_increment) % 1.0
        
        # 计算各腿相位（两组相差0.5相位）
        for leg in self.TRIPOD_A:
            self.leg_phases[leg] = self.cycle_phase
        
        for leg in self.TRIPOD_B:
            self.leg_phases[leg] = (self.cycle_phase + 0.5) % 1.0
        
        # 确定支撑/摆动状态
        for leg in LegID:
            phase = self.leg_phases[leg]
            self.leg_in_stance[leg] = phase < self.stance_duration
    
    def get_leg_trajectory(
        self,
        leg: LegID,
        base_position: np.ndarray,
        stride_length: float = 1.0,
        step_height: float = 0.5
    ) -> Tuple[np.ndarray, bool]:
        """
        获取腿的轨迹点
        
        Returns:
            (foot_position, is_stance)
        """
        phase = self.leg_phases[leg]
        is_stance = self.leg_in_stance[leg]
        
        if is_stance:
            # 支撑期: 向后拖动
            stance_phase = phase / self.stance_duration
            x_offset = stride_length * (0.5 - stance_phase)
            z_offset = 0.0  # 接触地面
        else:
            # 摆动期: 向前摆动，中间抬起
            swing_phase = (phase - self.stance_duration) / self.swing_duration
            x_offset = stride_length * (swing_phase - 0.5)
            # 抛物线轨迹
            z_offset = step_height * np.sin(swing_phase * np.pi)
        
        foot_pos = base_position.copy()
        foot_pos[0] += x_offset
        foot_pos[2] += z_offset
        
        return foot_pos, is_stance
    
    def get_gait_duty_factors(self) -> Dict[LegID, float]:
        """获取各腿的占空比（支撑时间比例）"""
        return {leg: self.stance_duration for leg in LegID}


class WaveGait:
    """
    波动步态控制器（用于慢速精细运动）
    每条腿依次摆动，类似毛毛虫
    """
    
    LEG_ORDER = [
        LegID.BACK_LEFT, LegID.MIDDLE_LEFT, LegID.FRONT_LEFT,
        LegID.BACK_RIGHT, LegID.MIDDLE_RIGHT, LegID.FRONT_RIGHT
    ]
    
    def __init__(self, step_frequency: float = 5.0):
        self.step_frequency = step_frequency
        self.cycle_phase = 0.0
        self.leg_in_stance = {leg: True for leg in LegID}
        self.leg_phases = {leg: 0.0 for leg in LegID}
    
    def update(self, dt: float, speed_factor: float = 1.0):
        """更新波动步态"""
        effective_frequency = self.step_frequency * speed_factor
        self.cycle_phase = (self.cycle_phase + effective_frequency * dt) % 1.0
        
        # 每条腿在周期中均匀分布
        for i, leg in enumerate(self.LEG_ORDER):
            leg_phase_offset = i / 6.0
            self.leg_phases[leg] = (self.cycle_phase + leg_phase_offset) % 1.0
            # 摆动期占1/6周期
            self.leg_in_stance[leg] = self.leg_phases[leg] > (1.0 / 6.0)


class FlyBody:
    """
    果蝇身体模型
    
    物理参数（基于真实果蝇Drosophila melanogaster）:
    - 体长: 约2.5-3mm
    - 体重: 约1mg
    - 翅膀展开宽度: 约4-5mm
    """
    
    # 身体尺寸参数 (mm)
    BODY_LENGTH = 2.8
    BODY_WIDTH = 1.0
    BODY_HEIGHT = 0.8
    
    # 腿部参数 (mm)
    LEG_LENGTHS = {
        LegID.FRONT_LEFT: {'coxa': 0.3, 'femur': 0.8, 'tibia': 1.2},
        LegID.MIDDLE_LEFT: {'coxa': 0.3, 'femur': 0.9, 'tibia': 1.3},
        LegID.BACK_LEFT: {'coxa': 0.3, 'femur': 1.0, 'tibia': 1.5},
        LegID.FRONT_RIGHT: {'coxa': 0.3, 'femur': 0.8, 'tibia': 1.2},
        LegID.MIDDLE_RIGHT: {'coxa': 0.3, 'femur': 0.9, 'tibia': 1.3},
        LegID.BACK_RIGHT: {'coxa': 0.3, 'femur': 1.0, 'tibia': 1.5}
    }
    
    # 腿部附着点（身体坐标系，相对于中心）
    LEG_ATTACHMENTS = {
        LegID.FRONT_LEFT: np.array([1.0, 0.4, 0.0]),
        LegID.MIDDLE_LEFT: np.array([0.0, 0.4, 0.0]),
        LegID.BACK_LEFT: np.array([-1.0, 0.4, 0.0]),
        LegID.FRONT_RIGHT: np.array([1.0, -0.4, 0.0]),
        LegID.MIDDLE_RIGHT: np.array([0.0, -0.4, 0.0]),
        LegID.BACK_RIGHT: np.array([-1.0, -0.4, 0.0])
    }
    
    def __init__(self, position: Optional[np.ndarray] = None):
        """
        初始化果蝇身体
        
        Args:
            position: 初始位置 [x, y, z] (mm)
        """
        # 位置与朝向
        if position is not None:
            self.position = position.astype(float)
        else:
            self.position = np.zeros(3, dtype=float)
        self.orientation = np.zeros(3, dtype=float)  # 俯仰、偏航、翻滚角
        self.velocity = np.zeros(3, dtype=float)
        self.angular_velocity = np.zeros(3, dtype=float)
        
        # 身体物理属性
        self.mass = 1.0  # mg
        self.inertia = np.array([0.1, 0.1, 0.1])  # 转动惯量
        
        # 腿部状态
        self.legs = {leg: LegKinematics() for leg in LegID}
        
        # 翅膀状态
        self.wing_spread = 0.0  # 展开程度 0-1
        self.wing_angle = 0.0   # 翅膀角度
        self.wing_vibration = 0.0  # 振动频率
        self.is_flying = False
        
        # 触角状态
        self.antenna_angles = np.zeros(2)  # 左右触角角度
        self.antenna_extension = 0.5  # 伸展程度
        
        # 口器状态
        self.proboscis_extension = 0.0  # 伸出程度
        
        # 步态控制器
        self.tripod_gait = TripodGait()
        self.wave_gait = WaveGait()
        self.current_gait = 'tripod'  # 'tripod' 或 'wave'
        
        # 身体清洁状态
        self.body_cleanliness = 100.0
        
        # 传感器状态
        self.touch_sensors = {leg: 0.0 for leg in LegID}
        self.body_touch = 0.0
    
    def update_physics(self, dt: float, forces: Optional[np.ndarray] = None):
        """
        更新物理状态
        
        Args:
            dt: 时间步长
            forces: 外力 [fx, fy, fz]
        """
        # 重力
        gravity = np.array([0, 0, -9.8]) * self.mass
        
        # 应用力
        if forces is not None:
            total_force = forces + gravity
        else:
            total_force = gravity
        
        # 简化的物理更新（欧拉积分）
        acceleration = total_force / self.mass
        self.velocity += acceleration * dt
        
        # 阻尼
        self.velocity *= 0.95
        
        # 更新位置
        self.position += self.velocity * dt
        
        # 地面碰撞检测
        if self.position[2] < 0:
            self.position[2] = 0
            self.velocity[2] = max(0, self.velocity[2])
        
        # 更新角速度
        self.angular_velocity *= 0.95
        self.orientation += self.angular_velocity * dt
    
    def update_legs_from_brain(
        self,
        leg_output: torch.Tensor,
        dt: float,
        speed_factor: float = 1.0
    ):
        """
        根据大脑输出更新腿部状态
        
        Args:
            leg_output: [18] 6条腿 × 3关节控制信号
            dt: 时间步长
            speed_factor: 速度因子
        """
        # 解析大脑输出
        leg_controls = leg_output.detach().cpu().numpy()
        
        # 更新步态
        if self.current_gait == 'tripod':
            self.tripod_gait.update(dt, speed_factor)
        else:
            self.wave_gait.update(dt, speed_factor)
        
        # 更新每条腿
        for i, leg in enumerate(LegID):
            start_idx = i * 3
            
            # 目标关节角度（归一化到 [-1, 1]）
            target_coxa = np.clip(leg_controls[start_idx], -1, 1)
            target_femur = np.clip(leg_controls[start_idx + 1], -1, 1)
            target_tibia = np.clip(leg_controls[start_idx + 2], -1, 1)
            
            # 映射到实际角度范围
            leg_state = self.legs[leg]
            leg_state.angles.coxa = target_coxa * 45.0  # ±45度
            leg_state.angles.femur = target_femur * 60.0  # ±60度
            leg_state.angles.tibia = target_tibia * 90.0  # ±90度
            
            # 步态相位
            if self.current_gait == 'tripod':
                leg_state.gait_phase = self.tripod_gait.leg_phases[leg]
                leg_state.is_stance = self.tripod_gait.leg_in_stance[leg]
            else:
                leg_state.gait_phase = self.wave_gait.leg_phases[leg]
                leg_state.is_stance = self.wave_gait.leg_in_stance[leg]
            
            leg_state.is_swing = not leg_state.is_stance
            
            # 计算足端位置
            leg_state.foot_position = self._compute_foot_position(leg)
    
    def _compute_foot_position(self, leg: LegID) -> np.ndarray:
        """
        计算腿末端位置（正向运动学）
        """
        # 腿部附着点（世界坐标）
        attachment = self.LEG_ATTACHMENTS[leg] + self.position
        
        # 腿部参数
        lengths = self.LEG_LENGTHS[leg]
        angles = self.legs[leg].angles
        
        # 简化的正向运动学（假设腿在身体侧面平面运动）
        coxa_len = lengths['coxa']
        femur_len = lengths['femur']
        tibia_len = lengths['tibia']
        
        # 基节旋转
        coxa_rad = np.deg2rad(angles.coxa)
        femur_rad = np.deg2rad(angles.femur)
        tibia_rad = np.deg2rad(angles.tibia)
        
        # 计算足端位置（简化模型）
        x = coxa_len * np.cos(coxa_rad) + \
            femur_len * np.cos(coxa_rad + femur_rad) + \
            tibia_len * np.cos(coxa_rad + femur_rad + tibia_rad)
        
        z = coxa_len * np.sin(coxa_rad) + \
            femur_len * np.sin(coxa_rad + femur_rad) + \
            tibia_len * np.sin(coxa_rad + femur_rad + tibia_rad)
        
        # 根据左右调整y坐标
        y_offset = 0.4 if 'LEFT' in leg.name else -0.4
        
        foot_pos = attachment + np.array([x, y_offset, z])
        
        return foot_pos
    
    def update_wings(self, wing_output: torch.Tensor):
        """更新翅膀状态"""
        wing_vals = wing_output.detach().cpu().numpy()
        
        self.wing_spread = np.clip(wing_vals[0], 0, 1)
        self.wing_angle = np.clip(wing_vals[1], 0, 1)
        self.wing_vibration = np.clip(wing_vals[2], 0, 1)
        
        # 判断是否飞行
        self.is_flying = self.wing_spread > 0.7 and self.wing_vibration > 0.5
    
    def update_antennae(self, antenna_output: torch.Tensor):
        """更新触角状态"""
        antenna_vals = antenna_output.detach().cpu().numpy()
        
        self.antenna_extension = np.clip(antenna_vals[0], 0, 1)
        self.antenna_angles = np.array([
            antenna_vals[1] * 45.0,  # 左触角
            antenna_vals[1] * 45.0   # 右触角
        ])
    
    def update_proboscis(self, proboscis_output: torch.Tensor):
        """更新口器状态"""
        self.proboscis_extension = np.clip(proboscis_output.item(), 0, 1)
    
    def get_body_state_vector(self) -> np.ndarray:
        """获取身体状态向量用于传感器反馈"""
        return np.array([
            self.position[0], self.position[1], self.position[2],
            self.orientation[0], self.orientation[1], self.orientation[2],
            self.velocity[0], self.velocity[1], self.velocity[2],
            self.body_cleanliness
        ])
    
    def get_leg_sensor_data(self) -> np.ndarray:
        """获取腿部传感器数据"""
        sensor_data = []
        for leg in LegID:
            leg_state = self.legs[leg]
            sensor_data.extend([
                float(leg_state.is_stance),
                float(leg_state.is_swing),
                leg_state.touch_force
            ])
        return np.array(sensor_data)
    
    def perform_grooming(self, grooming_type: str, dt: float) -> float:
        """
        执行理毛动作
        
        Args:
            grooming_type: 'antenna', 'head', 'body'
            dt: 时间步长
        
        Returns:
            cleaning_progress: 清洁进度
        """
        cleaning_rate = 0.0
        
        if grooming_type == 'antenna':
            # 前腿刷触角
            cleaning_rate = 5.0 * dt
            # 特定腿部动作
            self.legs[LegID.FRONT_LEFT].angles.femur = 60.0
            self.legs[LegID.FRONT_RIGHT].angles.femur = 60.0
            self.antenna_extension = 1.0  # 触角完全伸展
            
        elif grooming_type == 'head':
            # 前腿清理头部
            cleaning_rate = 3.0 * dt
            self.legs[LegID.FRONT_LEFT].angles.coxa = -30.0
            self.legs[LegID.FRONT_RIGHT].angles.coxa = 30.0
            
        elif grooming_type == 'body':
            # 中后腿清理身体
            cleaning_rate = 2.0 * dt
            self.legs[LegID.MIDDLE_LEFT].angles.femur = 70.0
            self.legs[LegID.MIDDLE_RIGHT].angles.femur = 70.0
        
        self.body_cleanliness = min(100.0, self.body_cleanliness + cleaning_rate)
        
        return cleaning_rate
    
    def get_stability(self) -> float:
        """计算身体稳定性（支撑多边形面积）"""
        stance_feet = []
        for leg in LegID:
            if self.legs[leg].is_stance:
                stance_feet.append(self.legs[leg].foot_position[:2])  # x, y位置
        
        if len(stance_feet) < 3:
            return 0.0
        
        # 计算凸包面积（简化计算）
        stance_feet = np.array(stance_feet)
        center = np.mean(stance_feet, axis=0)
        
        # 计算到中心的平均距离（近似稳定性度量）
        distances = np.linalg.norm(stance_feet - center, axis=1)
        avg_distance = np.mean(distances)
        
        # 归一化稳定性
        stability = min(1.0, avg_distance / 2.0)
        
        return stability
    
    def reset(self, position: Optional[np.ndarray] = None):
        """重置身体状态"""
        self.position = position if position is not None else np.zeros(3)
        self.orientation = np.zeros(3)
        self.velocity = np.zeros(3)
        self.angular_velocity = np.zeros(3)
        
        for leg in LegID:
            self.legs[leg].reset()
        
        self.wing_spread = 0.0
        self.wing_angle = 0.0
        self.wing_vibration = 0.0
        self.is_flying = False
        
        self.antenna_angles = np.zeros(2)
        self.antenna_extension = 0.5
        
        self.proboscis_extension = 0.0
        self.body_cleanliness = 100.0


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("果蝇身体模型测试")
    print("=" * 60)
    
    # 创建身体
    body = FlyBody(position=np.array([0, 0, 1]))
    
    print("\n身体参数:")
    print(f"  体长: {FlyBody.BODY_LENGTH} mm")
    print(f"  体宽: {FlyBody.BODY_WIDTH} mm")
    print(f"  体重: {body.mass} mg")
    
    print("\n腿部参数:")
    for leg in LegID:
        lengths = FlyBody.LEG_LENGTHS[leg]
        print(f"  {leg.name}: coxa={lengths['coxa']}, femur={lengths['femur']}, tibia={lengths['tibia']} mm")
    
    # 测试步态
    print("\n" + "=" * 60)
    print("三脚架步态测试")
    
    dt = 0.01
    for step in range(10):
        body.tripod_gait.update(dt)
        
        if step % 2 == 0:
            stance_a = sum([1 for leg in TripodGait.TRIPOD_A if body.tripod_gait.leg_in_stance[leg]])
            stance_b = sum([1 for leg in TripodGait.TRIPOD_B if body.tripod_gait.leg_in_stance[leg]])
            print(f"  步数 {step}: Tripod A 支撑={stance_a}, Tripod B 支撑={stance_b}")
    
    # 测试物理更新
    print("\n物理模拟测试:")
    body.reset(position=np.array([0.0, 0.0, 5.0]))
    
    for i in range(5):
        body.update_physics(dt=0.1)
        print(f"  t={i*0.1:.1f}s: position=[{body.position[0]:.2f}, {body.position[1]:.2f}, {body.position[2]:.2f}]")
    
    print("\n" + "=" * 60)
    print("测试完成!")
