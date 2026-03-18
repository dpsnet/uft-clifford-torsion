"""
果蝇行为模块
实现行走、理毛、觅食、逃跑等复杂行为

行为层次结构:
1. 反射级: 快速反应（逃跑、躲避）
2. 程序级: 固定动作模式（理毛、进食）
3. 目标导向: 状态依赖行为（觅食、探索）
"""

import numpy as np
import torch
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from enum import Enum

from tnn_fly_brain import BehaviorState, TNNFlyBrain, FlyInternalState
from fly_body import FlyBody, LegID, TripodGait


class BehaviorController:
    """
    行为控制器
    管理行为状态切换和具体行为执行
    """
    
    def __init__(
        self,
        brain: TNNFlyBrain,
        body: FlyBody,
        internal_state: FlyInternalState
    ):
        self.brain = brain
        self.body = body
        self.internal = internal_state
        
        # 行为状态机
        self.state_transitions = {
            BehaviorState.IDLE: [BehaviorState.WALKING, BehaviorState.FORAGING, 
                                BehaviorState.GROOMING, BehaviorState.RESTING],
            BehaviorState.WALKING: [BehaviorState.IDLE, BehaviorState.FORAGING, 
                                   BehaviorState.ESCAPING],
            BehaviorState.FORAGING: [BehaviorState.WALKING, BehaviorState.FEEDING, 
                                    BehaviorState.IDLE],
            BehaviorState.FEEDING: [BehaviorState.IDLE, BehaviorState.WALKING],
            BehaviorState.GROOMING: [BehaviorState.IDLE],
            BehaviorState.ESCAPING: [BehaviorState.WALKING, BehaviorState.IDLE],
            BehaviorState.RESTING: [BehaviorState.IDLE, BehaviorState.WALKING]
        }
        
        # 行为持续时间限制（防止卡住）
        self.max_behavior_durations = {
            BehaviorState.IDLE: 100,
            BehaviorState.WALKING: 500,
            BehaviorState.FORAGING: 1000,
            BehaviorState.FEEDING: 200,
            BehaviorState.GROOMING: 300,
            BehaviorState.ESCAPING: 50,
            BehaviorState.RESTING: 300
        }
        
        # 行为历史
        self.behavior_history = []
        self.max_history = 100
    
    def can_transition_to(self, new_state: BehaviorState) -> bool:
        """检查是否可以从当前状态转换到新状态"""
        return new_state in self.state_transitions.get(self.internal.current_behavior, [])
    
    def transition_to(self, new_state: BehaviorState, force: bool = False) -> bool:
        """
        转换到新的行为状态
        
        Args:
            new_state: 目标行为状态
            force: 是否强制转换（忽略状态机限制）
        
        Returns:
            success: 是否成功转换
        """
        if not force and not self.can_transition_to(new_state):
            return False
        
        # 记录历史
        self.behavior_history.append({
            'from': self.internal.current_behavior,
            'to': new_state,
            'duration': self.internal.behavior_duration
        })
        
        if len(self.behavior_history) > self.max_history:
            self.behavior_history.pop(0)
        
        # 执行状态转换
        self.internal.current_behavior = new_state
        self.internal.behavior_duration = 0
        
        # 重置步态
        if new_state in [BehaviorState.WALKING, BehaviorState.FORAGING, BehaviorState.ESCAPING]:
            self.body.current_gait = 'tripod'
        
        return True
    
    def update(self, dt: float = 1.0):
        """更新行为状态"""
        # 检查是否需要强制切换（超时）
        max_duration = self.max_behavior_durations.get(self.internal.current_behavior, 100)
        
        if self.internal.behavior_duration > max_duration:
            # 超时返回IDLE
            self.transition_to(BehaviorState.IDLE, force=True)
        
        # 更新内部状态
        self.internal.update(dt)
        
        # 自动行为切换逻辑
        self._auto_behavior_switch()
    
    def _auto_behavior_switch(self):
        """基于内部状态的自动行为切换"""
        current = self.internal.current_behavior
        
        # 紧急情况：高应激 -> 逃跑
        if self.internal.stress > 70:
            if current != BehaviorState.ESCAPING:
                self.transition_to(BehaviorState.ESCAPING, force=True)
            return
        
        # 高饥饿 -> 觅食
        if self.internal.hunger > 60 and current == BehaviorState.IDLE:
            self.transition_to(BehaviorState.FORAGING)
            return
        
        # 低清洁度 -> 理毛
        if self.internal.cleanliness < 30 and current == BehaviorState.IDLE:
            self.transition_to(BehaviorState.GROOMING)
            return
        
        # 低能量 -> 休息
        if self.internal.energy < 20 and current == BehaviorState.IDLE:
            self.transition_to(BehaviorState.RESTING)
            return


class LocomotionBehavior:
    """
    行走行为
    实现稳定六足步态、转向控制、速度调节
    """
    
    def __init__(self, body: FlyBody, brain: TNNFlyBrain):
        self.body = body
        self.brain = brain
        
        # 行走参数
        self.base_speed = 1.0  # mm/s
        self.turn_rate = 0.5   # rad/s
        self.stride_length = 0.8  # mm
        
        # 当前运动状态
        self.forward_velocity = 0.0
        self.turn_velocity = 0.0
        self.speed_factor = 1.0
    
    def execute(
        self,
        brain_output: Dict[str, torch.Tensor],
        dt: float,
        target_direction: Optional[float] = None,
        target_speed: Optional[float] = None
    ) -> Tuple[np.ndarray, float]:
        """
        执行行走行为
        
        Args:
            brain_output: 大脑输出
            dt: 时间步长
            target_direction: 目标方向（可选）
            target_speed: 目标速度（可选）
        
        Returns:
            displacement: [dx, dy, dz] 位移
            stability: 身体稳定性
        """
        # 从大脑输出解析控制信号
        leg_output = brain_output['leg_output']
        
        # 提取速度控制（使用行为选择概率调制）
        behavior_probs = brain_output['behavior_probs']
        walk_prob = behavior_probs[0, 1].item()  # walking行为的概率
        
        # 确定速度因子
        if target_speed is not None:
            self.speed_factor = target_speed / self.base_speed
        else:
            self.speed_factor = 0.5 + walk_prob  # 0.5 - 1.5
        
        self.speed_factor = np.clip(self.speed_factor, 0.1, 2.0)
        
        # 更新腿部状态
        self.body.update_legs_from_brain(leg_output[0], dt, self.speed_factor)
        
        # 计算运动
        if target_direction is not None:
            self._apply_direction_control(target_direction, dt)
        
        # 计算身体位移
        displacement = self._compute_displacement(dt)
        
        # 计算稳定性
        stability = self.body.get_stability()
        
        return displacement, stability
    
    def _apply_direction_control(self, target_direction: float, dt: float):
        """应用方向控制（转向）"""
        current_heading = self.body.orientation[2]  # 偏航角
        
        # 计算角度差
        angle_diff = target_direction - current_heading
        angle_diff = (angle_diff + np.pi) % (2 * np.pi) - np.pi
        
        # 平滑转向
        turn_amount = np.clip(angle_diff, -self.turn_rate * dt, self.turn_rate * dt)
        self.body.orientation[2] += turn_amount
    
    def _compute_displacement(self, dt: float) -> np.ndarray:
        """计算身体位移"""
        # 基于支撑腿的平均运动估算
        stance_movement = []
        
        for leg in LegID:
            leg_state = self.body.legs[leg]
            if leg_state.is_stance:
                # 支撑期向后拖动产生前进
                direction = 1 if 'RIGHT' in leg.name else -1
                movement = direction * self.speed_factor * self.base_speed * dt
                stance_movement.append(movement)
        
        if len(stance_movement) >= 3:  # 至少3条腿支撑
            avg_movement = np.mean(stance_movement)
        else:
            avg_movement = 0.0
        
        # 根据朝向计算位移
        heading = self.body.orientation[2]
        dx = avg_movement * np.cos(heading)
        dy = avg_movement * np.sin(heading)
        
        return np.array([dx, dy, 0.0])
    
    def get_gait_quality(self) -> Dict:
        """评估步态质量"""
        tripod_a_stance = sum([1 for leg in TripodGait.TRIPOD_A 
                              if self.body.legs[leg].is_stance])
        tripod_b_stance = sum([1 for leg in TripodGait.TRIPOD_B 
                              if self.body.legs[leg].is_stance])
        
        # 理想三脚架步态: 一组3条支撑，另一组3条摆动
        ideal_pattern = (tripod_a_stance == 3 and tripod_b_stance == 0) or \
                       (tripod_a_stance == 0 and tripod_b_stance == 3)
        
        # 支撑腿数量
        total_stance = tripod_a_stance + tripod_b_stance
        
        # 步态协调性
        gait_coordination = abs(tripod_a_stance - tripod_b_stance)
        
        return {
            'tripod_a_stance': tripod_a_stance,
            'tripod_b_stance': tripod_b_stance,
            'total_stance': total_stance,
            'ideal_pattern': ideal_pattern,
            'gait_coordination': gait_coordination,
            'stability': self.body.get_stability()
        }


class GroomingBehavior:
    """
    理毛行为
    实现触角理毛、头部理毛、身体理毛
    
    果蝇理毛序列:
    1. 前腿刷触角
    2. 前腿清理头部
    3. 中后腿清理身体
    """
    
    GROOMING_SEQUENCE = ['antenna', 'head', 'body']
    
    def __init__(self, body: FlyBody, internal_state: FlyInternalState):
        self.body = body
        self.internal = internal_state
        
        # 理毛状态
        self.current_stage = 0
        self.stage_timer = 0
        self.stage_durations = {
            'antenna': 50,  # 步骤
            'head': 40,
            'body': 60
        }
    
    def execute(self, brain_output: Dict[str, torch.Tensor], dt: float) -> bool:
        """
        执行理毛行为
        
        Returns:
            completed: 是否完成整个理毛序列
        """
        # 获取当前阶段
        if self.current_stage >= len(self.GROOMING_SEQUENCE):
            self.reset()
            return True
        
        current_part = self.GROOMING_SEQUENCE[self.current_stage]
        
        # 执行当前阶段的理毛动作
        cleaning_progress = self.body.perform_grooming(current_part, dt)
        
        # 更新计时器
        self.stage_timer += 1
        
        # 检查是否进入下一阶段
        if self.stage_timer >= self.stage_durations[current_part]:
            self.current_stage += 1
            self.stage_timer = 0
        
        return False
    
    def reset(self):
        """重置理毛状态"""
        self.current_stage = 0
        self.stage_timer = 0


class ForagingBehavior:
    """
    觅食行为
    实现随机探索、化学梯度跟随、食物识别
    """
    
    def __init__(
        self,
        body: FlyBody,
        internal_state: FlyInternalState,
        arena_size: Tuple[float, float] = (100, 100)
    ):
        self.body = body
        self.internal = internal_state
        self.arena_size = arena_size
        
        # 探索参数
        self.exploration_rate = 0.3  # 随机探索概率
        self.chemotaxis_strength = 1.0  # 趋化强度
        
        # 内部状态
        self.target_food_location: Optional[Tuple[float, float]] = None
        self.search_direction = np.random.uniform(0, 2 * np.pi)
        self.search_timer = 0
        self.search_duration = 100
        
        # 记忆
        self.visited_locations: List[Tuple[float, float]] = []
        self.max_memory = 20
    
    def execute(
        self,
        brain_output: Dict[str, torch.Tensor],
        olfactory_input: torch.Tensor,
        food_sources: List[Tuple[float, float, float]],  # (x, y, intensity)
        dt: float
    ) -> Tuple[np.ndarray, bool]:
        """
        执行觅食行为
        
        Args:
            brain_output: 大脑输出
            olfactory_input: 嗅觉输入
            food_sources: 食物源列表
            dt: 时间步长
        
        Returns:
            displacement: 位移
            food_detected: 是否检测到食物
        """
        current_pos = self.body.position[:2]
        
        # 记录访问位置
        self.visited_locations.append(tuple(current_pos))
        if len(self.visited_locations) > self.max_memory:
            self.visited_locations.pop(0)
        
        # 1. 检查附近是否有食物
        nearest_food, food_distance = self._find_nearest_food(food_sources)
        
        if nearest_food is not None and food_distance < 2.0:
            # 到达食物
            return np.array([0.0, 0.0, 0.0]), True
        
        # 2. 化学梯度跟随或随机探索
        if nearest_food is not None:
            # 朝着食物方向移动（趋化性）
            target_direction = np.arctan2(
                nearest_food[1] - current_pos[1],
                nearest_food[0] - current_pos[0]
            )
            
            # 更新搜索方向
            self.search_direction = target_direction
            self.search_timer = 0
        else:
            # 随机探索
            self.search_timer += 1
            if self.search_timer >= self.search_duration:
                # 随机改变方向
                self.search_direction += np.random.uniform(-np.pi/2, np.pi/2)
                self.search_timer = 0
                self.search_duration = np.random.randint(50, 150)
        
        # 3. 计算位移
        speed = 1.0  # mm/s
        dx = speed * dt * np.cos(self.search_direction)
        dy = speed * dt * np.sin(self.search_direction)
        
        displacement = np.array([dx, dy, 0.0])
        
        return displacement, False
    
    def _find_nearest_food(
        self,
        food_sources: List[Tuple[float, float, float]]
    ) -> Tuple[Optional[Tuple[float, float]], float]:
        """找到最近的食物源"""
        current_pos = self.body.position[:2]
        
        nearest = None
        min_distance = float('inf')
        
        for food in food_sources:
            food_pos = np.array(food[:2])
            distance = np.linalg.norm(food_pos - current_pos)
            
            if distance < min_distance:
                min_distance = distance
                nearest = food[:2]
        
        return nearest, min_distance


class EscapeBehavior:
    """
    逃跑行为
    实现looming刺激检测、快速逃跑反应、恢复探索
    """
    
    def __init__(self, body: FlyBody, internal_state: FlyInternalState):
        self.body = body
        self.internal = internal_state
        
        # 逃跑参数
        self.escape_speed = 3.0  # mm/s (正常速度的3倍)
        self.escape_direction: Optional[float] = None
        self.escape_timer = 0
        self.escape_duration = 30  # 步骤
        
        # 恢复参数
        self.recovery_timer = 0
        self.recovery_duration = 50
    
    def trigger(self, looming_direction: Optional[float] = None):
        """触发逃跑反应"""
        self.internal.stress = 100.0
        self.internal.arousal = 1.0
        
        # 逃跑方向：与looming方向相反
        if looming_direction is not None:
            self.escape_direction = (looming_direction + np.pi) % (2 * np.pi)
        else:
            # 随机逃跑方向
            self.escape_direction = np.random.uniform(0, 2 * np.pi)
        
        self.escape_timer = 0
        self.recovery_timer = 0
    
    def execute(self, dt: float) -> Tuple[np.ndarray, bool]:
        """
        执行逃跑行为
        
        Returns:
            displacement: 位移
            completed: 是否完成逃跑并可以恢复
        """
        if self.escape_timer < self.escape_duration:
            # 逃跑阶段
            self.escape_timer += 1
            
            # 高速移动
            dx = self.escape_speed * dt * np.cos(self.escape_direction)
            dy = self.escape_speed * dt * np.sin(self.escape_direction)
            
            displacement = np.array([dx, dy, 0.0])
            
            return displacement, False
        
        elif self.recovery_timer < self.recovery_duration:
            # 恢复阶段
            self.recovery_timer += 1
            
            # 应激逐渐衰减
            self.internal.stress *= 0.9
            self.internal.arousal *= 0.95
            
            # 慢速移动
            slow_direction = self.escape_direction + np.random.uniform(-0.5, 0.5)
            dx = 0.5 * dt * np.cos(slow_direction)
            dy = 0.5 * dt * np.sin(slow_direction)
            
            displacement = np.array([dx, dy, 0.0])
            
            return displacement, False
        
        else:
            # 逃跑完成
            return np.array([0.0, 0.0, 0.0]), True
    
    def reset(self):
        """重置逃跑状态"""
        self.escape_direction = None
        self.escape_timer = 0
        self.recovery_timer = 0


class FeedingBehavior:
    """
    进食行为
    实现口器控制、进食动作、饱腹感更新
    """
    
    def __init__(self, body: FlyBody, internal_state: FlyInternalState):
        self.body = body
        self.internal = internal_state
        
        # 进食参数
        self.feeding_rate = 2.0  # 能量/步
        self.max_feeding_duration = 200
        
        # 状态
        self.feeding_timer = 0
        self.proboscis_extended = False
    
    def execute(
        self,
        brain_output: Dict[str, torch.Tensor],
        food_quality: float = 1.0,
        dt: float = 1.0
    ) -> bool:
        """
        执行进食行为
        
        Args:
            brain_output: 大脑输出
            food_quality: 食物质量 (0-1)
            dt: 时间步长
        
        Returns:
            completed: 是否完成进食
        """
        # 从口器输出判断是否需要伸出
        proboscis_output = brain_output['proboscis_output']
        extend_proboscis = proboscis_output.item() > 0.5
        
        if extend_proboscis and not self.proboscis_extended:
            # 伸出口器
            self.proboscis_extended = True
            self.body.proboscis_extension = 1.0
        
        if self.proboscis_extended:
            # 进食中
            self.feeding_timer += 1
            
            # 增加能量，减少饥饿
            energy_gain = self.feeding_rate * food_quality * dt
            self.internal.energy = min(100.0, self.internal.energy + energy_gain)
            self.internal.hunger = max(0.0, self.internal.hunger - energy_gain)
            
            # 检查是否吃饱或超时
            if self.internal.hunger < 10 or self.feeding_timer >= self.max_feeding_duration:
                # 收回口器，完成进食
                self.proboscis_extended = False
                self.body.proboscis_extension = 0.0
                return True
        
        return False
    
    def reset(self):
        """重置进食状态"""
        self.feeding_timer = 0
        self.proboscis_extended = False
        self.body.proboscis_extension = 0.0


class RestingBehavior:
    """
    休息行为
    实现低代谢、恢复、静止
    """
    
    def __init__(self, body: FlyBody, internal_state: FlyInternalState):
        self.body = body
        self.internal = internal_state
        
        # 休息参数
        self.rest_recovery_rate = 0.5  # 能量恢复速率
        self.min_rest_duration = 50
        
        # 状态
        self.rest_timer = 0
    
    def execute(self, dt: float = 1.0) -> bool:
        """
        执行休息行为
        
        Returns:
            completed: 是否完成休息（能量恢复到一定程度）
        """
        self.rest_timer += 1
        
        # 降低代谢率
        self.internal.metabolic_rate = 0.3
        
        # 缓慢恢复能量
        self.internal.energy = min(100.0, self.internal.energy + self.rest_recovery_rate * dt)
        
        # 应激衰减
        self.internal.stress *= 0.95
        self.internal.arousal = max(0.2, self.internal.arousal * 0.95)
        
        # 身体静止
        for leg in LegID:
            self.body.legs[leg].reset()
        
        self.body.wing_spread = 0.0
        self.body.wing_vibration = 0.0
        
        # 检查是否完成休息
        if self.rest_timer >= self.min_rest_duration and self.internal.energy > 50:
            self.internal.metabolic_rate = 1.0  # 恢复正常代谢
            return True
        
        return False
    
    def reset(self):
        """重置休息状态"""
        self.rest_timer = 0
        self.internal.metabolic_rate = 1.0


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("果蝇行为模块测试")
    print("=" * 60)
    
    # 创建模拟组件
    device = 'cpu'
    brain = TNNFlyBrain(device=device)
    body = FlyBody()
    internal = FlyInternalState()
    
    # 创建行为控制器
    controller = BehaviorController(brain, body, internal)
    
    print("\n行为状态机:")
    for state, transitions in controller.state_transitions.items():
        print(f"  {state.value}: -> {[s.value for s in transitions]}")
    
    # 测试状态转换
    print("\n状态转换测试:")
    print(f"  初始状态: {internal.current_behavior.value}")
    
    controller.transition_to(BehaviorState.WALKING)
    print(f"  转换到 WALKING: {internal.current_behavior.value}")
    
    controller.transition_to(BehaviorState.FORAGING)
    print(f"  转换到 FORAGING: {internal.current_behavior.value}")
    
    # 测试行走行为
    print("\n行走行为测试:")
    locomotion = LocomotionBehavior(body, brain)
    
    # 模拟大脑输出
    test_output = {
        'leg_output': torch.randn(1, 18),
        'behavior_probs': torch.tensor([[0.1, 0.7, 0.05, 0.1, 0.0, 0.03, 0.02]])
    }
    
    for i in range(5):
        displacement, stability = locomotion.execute(test_output, dt=0.1)
        print(f"  步数 {i}: 位移=[{displacement[0]:.3f}, {displacement[1]:.3f}], 稳定性={stability:.3f}")
    
    # 评估步态质量
    gait_quality = locomotion.get_gait_quality()
    print(f"\n步态质量:")
    for key, value in gait_quality.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
