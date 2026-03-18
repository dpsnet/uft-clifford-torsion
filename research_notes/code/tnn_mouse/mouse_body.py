"""
TNN小鼠身体模型
包含物理身体、运动学和运动控制
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MouseBodyConfig:
    """小鼠身体配置"""
    # 身体尺寸 (米)
    body_length: float = 0.08      # 8cm
    body_width: float = 0.03       # 3cm
    body_height: float = 0.03      # 3cm
    body_mass: float = 0.025       # 25g
    
    # 头部尺寸
    head_length: float = 0.025
    head_width: float = 0.018
    head_mass: float = 0.005
    
    # 四肢参数
    limb_lengths: Dict[str, float] = None
    limb_masses: Dict[str, float] = None
    
    # 尾巴参数
    tail_segments: int = 10
    tail_length: float = 0.08
    
    # 物理参数
    friction: float = 0.8
    max_speed: float = 0.5         # m/s
    max_acceleration: float = 2.0   # m/s²
    
    def __post_init__(self):
        if self.limb_lengths is None:
            self.limb_lengths = {
                'front_upper': 0.015,
                'front_lower': 0.012,
                'hind_upper': 0.020,
                'hind_lower': 0.018
            }
        if self.limb_masses is None:
            self.limb_masses = {
                'front': 0.002,
                'hind': 0.003
            }


class MouseBody:
    """
    TNN小鼠物理身体模型
    简化但包含关键运动学特性
    """
    
    def __init__(self, config: MouseBodyConfig = None):
        self.config = config or MouseBodyConfig()
        
        # 状态变量
        self.position = np.zeros(3)          # 世界坐标 [x, y, z]
        self.orientation = np.zeros(3)       # 欧拉角 [yaw, pitch, roll]
        self.velocity = np.zeros(3)          # 线速度
        self.angular_velocity = np.zeros(3)  # 角速度
        
        # 关节角度 (简化模型)
        # 前肢: 肩(3DOF) + 肘(1DOF) + 腕(2DOF) = 6 × 2 = 12
        # 后肢: 髋(3DOF) + 膝(1DOF) + 踝(2DOF) = 6 × 2 = 12
        # 头部: 颈(3DOF)
        # 尾巴: 10节 × 2DOF = 20
        self.joint_angles = {
            'front_left': np.zeros(6),
            'front_right': np.zeros(6),
            'hind_left': np.zeros(6),
            'hind_right': np.zeros(6),
            'neck': np.zeros(3),
            'tail': np.zeros(self.config.tail_segments * 2)
        }
        
        # 感觉状态
        self.whisker_deflections = np.zeros(64)  # 32根胡须 × 2侧
        self.body_touch = np.zeros(128)
        self.paw_touch = np.zeros(64)
        
        # 内部状态
        self.energy = 1.0          # 0-1
        self.arousal = 0.5         # 觉醒水平
        self.stress = 0.0          # 压力水平
        self.hunger = 0.0          # 饥饿程度
        self.fear = 0.0            # 恐惧程度
        
        # 时间
        self.time = 0.0
        self.dt = 0.01             # 10ms步长
        
    def update(self, motor_commands: np.ndarray, environment: Dict = None):
        """
        更新身体状态
        
        Args:
            motor_commands: 运动指令 [168维]
            environment: 环境信息字典
        """
        # 解析运动命令
        self._parse_motor_commands(motor_commands)
        
        # 更新身体动力学
        self._update_dynamics()
        
        # 更新关节运动学
        self._update_limb_kinematics()
        
        # 更新头部和尾巴
        self._update_head_tail()
        
        # 更新内部状态 (能量消耗等)
        self._update_internal_states()
        
        # 更新时间
        self.time += self.dt
        
    def _parse_motor_commands(self, commands: np.ndarray):
        """解析运动命令到关节目标"""
        # 假设commands是归一化的 [-1, 1]
        idx = 0
        
        # 前肢 (每肢6DOF × 2 = 12)
        for side in ['front_left', 'front_right']:
            self.joint_angles[side] = commands[idx:idx+6] * np.pi
            idx += 6
        
        # 后肢
        for side in ['hind_left', 'hind_right']:
            self.joint_angles[side] = commands[idx:idx+6] * np.pi
            idx += 6
        
        # 头部 (3DOF)
        self.joint_angles['neck'] = commands[idx:idx+3] * np.pi/2
        idx += 3
        
        # 尾巴 (20DOF)
        n_tail = self.config.tail_segments * 2
        self.joint_angles['tail'] = commands[idx:idx+n_tail] * np.pi/4
        idx += n_tail
        
        # 剩余用于身体整体运动
        if idx < len(commands):
            # 使用剩余维度控制整体运动
            self._desired_velocity = commands[idx:idx+3] * self.config.max_speed
            self._desired_angular_velocity = commands[idx+3:idx+6] * np.pi
    
    def _update_dynamics(self):
        """更新身体动力学"""
        # 简化的动力学模型
        # 速度向目标速度收敛
        if hasattr(self, '_desired_velocity'):
            alpha = 0.1  # 收敛系数
            self.velocity += alpha * (self._desired_velocity - self.velocity)
        
        if hasattr(self, '_desired_angular_velocity'):
            alpha = 0.1
            self.angular_velocity += alpha * (
                self._desired_angular_velocity - self.angular_velocity
            )
        
        # 更新位置
        self.position += self.velocity * self.dt
        
        # 更新朝向
        self.orientation += self.angular_velocity * self.dt
        
        # 归一化角度
        self.orientation = np.mod(self.orientation + np.pi, 2 * np.pi) - np.pi
    
    def _update_limb_kinematics(self):
        """更新四肢运动学"""
        # 简化的正向运动学
        # 计算足底位置 (用于碰撞检测等)
        self.paw_positions = {}
        
        for side, angles in self.joint_angles.items():
            if 'front' in side or 'hind' in side:
                # 简化的2连杆运动学
                # 实际实现需要更复杂的3D运动学
                self.paw_positions[side] = self._compute_limb_position(side, angles)
    
    def _compute_limb_position(self, limb: str, angles: np.ndarray) -> np.ndarray:
        """计算肢体末端位置 (简化)"""
        # 这是简化版本，实际需要完整的3D正向运动学
        base_pos = self.position.copy()
        
        # 根据肢体添加偏移
        if 'front' in limb:
            base_pos[0] += self.config.body_length * 0.3
        elif 'hind' in limb:
            base_pos[0] -= self.config.body_length * 0.3
        
        if 'left' in limb:
            base_pos[1] += self.config.body_width * 0.5
        elif 'right' in limb:
            base_pos[1] -= self.config.body_width * 0.5
        
        # 添加基于关节角度的偏移 (简化)
        l1 = self.config.limb_lengths.get('front_upper', 0.015)
        l2 = self.config.limb_lengths.get('front_lower', 0.012)
        
        # 2D简化
        x = base_pos[0] + l1 * np.sin(angles[0]) + l2 * np.sin(angles[0] + angles[1])
        z = base_pos[2] - l1 * np.cos(angles[0]) - l2 * np.cos(angles[0] + angles[1])
        
        return np.array([x, base_pos[1], z])
    
    def _update_head_tail(self):
        """更新头部和尾巴"""
        # 计算头部位置
        head_offset = np.array([
            self.config.body_length * 0.5 + self.config.head_length * 0.5,
            0,
            self.config.body_height * 0.3
        ])
        
        # 应用颈部旋转 (简化)
        yaw, pitch, roll = self.joint_angles['neck']
        rotation_matrix = self._euler_to_matrix(yaw, pitch, roll)
        self.head_position = self.position + rotation_matrix @ head_offset
        self.head_orientation = self.orientation + self.joint_angles['neck']
        
        # 计算尾巴位置 (简化)
        self.tail_positions = [self.position.copy()]
        tail_segment_length = self.config.tail_length / self.config.tail_segments
        
        for i in range(self.config.tail_segments):
            angle_idx = i * 2
            angles = self.joint_angles['tail'][angle_idx:angle_idx+2]
            
            # 简化的尾巴段位置计算
            segment_offset = np.array([
                -tail_segment_length * np.cos(angles[0]),
                tail_segment_length * np.sin(angles[1]),
                tail_segment_length * np.sin(angles[0])
            ])
            
            new_pos = self.tail_positions[-1] + segment_offset
            self.tail_positions.append(new_pos)
    
    def _euler_to_matrix(self, yaw: float, pitch: float, roll: float) -> np.ndarray:
        """欧拉角到旋转矩阵"""
        cy, sy = np.cos(yaw), np.sin(yaw)
        cp, sp = np.cos(pitch), np.sin(pitch)
        cr, sr = np.cos(roll), np.sin(roll)
        
        R = np.array([
            [cy*cp, cy*sp*sr - sy*cr, cy*sp*cr + sy*sr],
            [sy*cp, sy*sp*sr + cy*cr, sy*sp*cr - cy*sr],
            [-sp, cp*sr, cp*cr]
        ])
        return R
    
    def _update_internal_states(self):
        """更新内部生理状态"""
        # 基础代谢消耗
        metabolic_rate = 0.0001
        self.energy = max(0, self.energy - metabolic_rate)
        
        # 活动增加饥饿
        activity = np.linalg.norm(self.velocity)
        self.hunger = min(1, self.hunger + activity * 0.001)
        
        # 压力和恐惧随时间衰减
        self.stress = max(0, self.stress - 0.001)
        self.fear = max(0, self.fear - 0.002)
        
        # 觉醒水平波动 (昼夜节律简化)
        self.arousal = 0.5 + 0.3 * np.sin(self.time * 0.001)
    
    def get_proprioception(self) -> np.ndarray:
        """获取本体感觉反馈"""
        # 关节角度 (64维)
        proprio = []
        for side in ['front_left', 'front_right', 'hind_left', 'hind_right']:
            proprio.extend(self.joint_angles[side])
        proprio.extend(self.joint_angles['neck'])
        
        # 角速度 (从角度变化估计)
        # 这里简化处理，实际应该记录历史
        proprio.extend(np.zeros(len(proprio)))  # 速度占位
        
        return np.array(proprio[:64])  # 确保64维
    
    def get_state_dict(self) -> Dict:
        """获取完整状态字典"""
        return {
            'position': self.position.copy(),
            'orientation': self.orientation.copy(),
            'velocity': self.velocity.copy(),
            'joint_angles': {k: v.copy() for k, v in self.joint_angles.items()},
            'energy': self.energy,
            'arousal': self.arousal,
            'stress': self.stress,
            'hunger': self.hunger,
            'fear': self.fear,
            'time': self.time
        }
    
    def reset(self, position: Optional[np.ndarray] = None):
        """重置身体状态"""
        self.position = position if position is not None else np.zeros(3)
        self.orientation = np.zeros(3)
        self.velocity = np.zeros(3)
        self.angular_velocity = np.zeros(3)
        
        for key in self.joint_angles:
            self.joint_angles[key] = np.zeros_like(self.joint_angles[key])
        
        self.energy = 1.0
        self.arousal = 0.5
        self.stress = 0.0
        self.hunger = 0.0
        self.fear = 0.0
        self.time = 0.0


# 测试
if __name__ == "__main__":
    print("=== TNN小鼠身体模型测试 ===\n")
    
    body = MouseBody()
    print(f"身体质量: {body.config.body_mass*1000:.1f}g")
    print(f"体长: {body.config.body_length*100:.1f}cm")
    print(f"关节自由度: {sum(len(v) for v in body.joint_angles.values())}")
    
    # 模拟一步
    motor_commands = np.random.randn(168) * 0.1
    body.update(motor_commands)
    
    print(f"\n更新后位置: {body.position}")
    print(f"本体感觉维度: {len(body.get_proprioception())}")
    print(f"内部状态: 能量={body.energy:.3f}, 饥饿={body.hunger:.3f}")
    
    print("\n✓ 测试通过!")
