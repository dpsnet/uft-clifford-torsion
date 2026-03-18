"""
行为验证套件
验证TNN-数字果蝇的各项涌现行为

验证项目:
1. 行走行为（Locomotion）
2. 理毛行为（Grooming）
3. 觅食行为（Foraging）
4. 逃跑行为（Escape）
5. 状态切换（State Switching）
"""

import numpy as np
import torch
from typing import Dict, List, Tuple, Callable
from dataclasses import dataclass
import time

from tnn_fly_brain import TNNFlyBrain, BehaviorState, FlyInternalState
from fly_body import FlyBody, LegID
from fly_vision import FlyVision
from physics_env import FlyArena, PhysicsSimulator, ObjectType
from behaviors import (
    BehaviorController, LocomotionBehavior, GroomingBehavior,
    ForagingBehavior, EscapeBehavior, FeedingBehavior, RestingBehavior
)
from compare_with_digital_fly import DigitalFlyComparator, EonFlyReference


@dataclass
class ValidationResult:
    """验证结果"""
    test_name: str
    passed: bool
    score: float  # 0-1
    details: Dict
    error_message: str = ""


class BehaviorValidator:
    """
    行为验证器
    """
    
    # 通过阈值
    THRESHOLDS = {
        'locomotion_stability': 0.6,
        'gait_coordination': 0.7,
        'grooming_completion': 0.8,
        'foraging_success_rate': 0.5,
        'escape_latency_ms': 100,
        'state_transition_accuracy': 0.7
    }
    
    def __init__(
        self,
        brain: TNNFlyBrain,
        body: FlyBody,
        arena: FlyArena,
        device: str = 'cpu'
    ):
        self.brain = brain
        self.body = body
        self.arena = arena
        self.device = device
        
        # 初始化组件
        self.internal_state = FlyInternalState()
        self.vision = FlyVision(input_size=(32, 32), device=device)
        self.physics = PhysicsSimulator(arena)
        self.controller = BehaviorController(brain, body, self.internal_state)
        
        # 行为模块
        self.locomotion = LocomotionBehavior(body, brain)
        self.grooming = GroomingBehavior(body, self.internal_state)
        self.foraging = ForagingBehavior(body, self.internal_state, arena.size)
        self.escape = EscapeBehavior(body, self.internal_state)
        self.feeding = FeedingBehavior(body, self.internal_state)
        self.resting = RestingBehavior(body, self.internal_state)
        
        # 验证结果
        self.results: List[ValidationResult] = []
    
    def validate_all(self) -> List[ValidationResult]:
        """运行所有验证测试"""
        print("=" * 70)
        print("TNN-数字果蝇行为验证套件")
        print("=" * 70)
        
        self.results = []
        
        # 1. 行走验证
        print("\n[1/5] 验证行走行为...")
        result = self.validate_locomotion()
        self.results.append(result)
        self._print_result(result)
        
        # 2. 理毛验证
        print("\n[2/5] 验证理毛行为...")
        result = self.validate_grooming()
        self.results.append(result)
        self._print_result(result)
        
        # 3. 觅食验证
        print("\n[3/5] 验证觅食行为...")
        result = self.validate_foraging()
        self.results.append(result)
        self._print_result(result)
        
        # 4. 逃跑验证
        print("\n[4/5] 验证逃跑行为...")
        result = self.validate_escape()
        self.results.append(result)
        self._print_result(result)
        
        # 5. 状态切换验证
        print("\n[5/5] 验证状态切换...")
        result = self.validate_state_switching()
        self.results.append(result)
        self._print_result(result)
        
        # 总结
        self._print_summary()
        
        return self.results
    
    def _print_result(self, result: ValidationResult):
        """打印验证结果"""
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status}: {result.test_name} (score: {result.score:.3f})")
        if not result.passed and result.error_message:
            print(f"    错误: {result.error_message}")
    
    def _print_summary(self):
        """打印验证总结"""
        print("\n" + "=" * 70)
        print("验证总结")
        print("=" * 70)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        
        print(f"\n通过: {passed}/{total}")
        print(f"总体分数: {np.mean([r.score for r in self.results]):.3f}")
        
        if passed == total:
            print("\n✓ 所有测试通过！")
        else:
            print(f"\n△ {total - passed} 项测试未通过，需要改进")
    
    def validate_locomotion(self, n_steps: int = 200) -> ValidationResult:
        """
        验证行走行为
        
        检查:
        - 步态稳定性
        - 三脚架协调性
        - 转向能力
        """
        self._reset()
        
        # 切换到行走状态
        self.controller.transition_to(BehaviorState.WALKING)
        
        # 运行仿真
        stability_scores = []
        gait_scores = []
        
        for step in range(n_steps):
            # 获取感觉输入
            visual, olfactory, mechano, internal = self._get_sensory_input()
            
            # 大脑处理
            with torch.no_grad():
                output = self.brain(
                    visual, olfactory, mechano, internal,
                    current_behavior=BehaviorState.WALKING
                )
            
            # 执行行走
            displacement, stability = self.locomotion.execute(output, dt=0.1)
            stability_scores.append(stability)
            
            # 评估步态
            gait_quality = self.locomotion.get_gait_quality()
            if gait_quality['ideal_pattern']:
                gait_scores.append(1.0)
            else:
                gait_scores.append(0.5)
            
            # 更新物理
            self.physics.update_fly_physics(self.body, displacement, dt=0.1)
        
        # 计算分数
        avg_stability = np.mean(stability_scores)
        avg_gait = np.mean(gait_scores)
        
        # 检查移动距离
        total_distance = np.linalg.norm(self.body.position[:2])
        
        score = (avg_stability + avg_gait) / 2
        passed = score >= self.THRESHOLDS['locomotion_stability']
        
        return ValidationResult(
            test_name="Locomotion",
            passed=passed,
            score=score,
            details={
                'avg_stability': avg_stability,
                'avg_gait_quality': avg_gait,
                'total_distance_mm': total_distance
            }
        )
    
    def validate_grooming(self, n_steps: int = 300) -> ValidationResult:
        """
        验证理毛行为
        
        检查:
        - 理毛序列完成
        - 清洁度提升
        - 正确腿部使用
        """
        self._reset()
        
        # 设置低清洁度触发理毛
        self.internal_state.cleanliness = 20.0
        self.controller.transition_to(BehaviorState.GROOMING)
        
        initial_cleanliness = self.internal_state.cleanliness
        cleanliness_history = []
        
        for step in range(n_steps):
            # 获取感觉输入
            visual, olfactory, mechano, internal = self._get_sensory_input()
            
            # 大脑处理
            with torch.no_grad():
                output = self.brain(
                    visual, olfactory, mechano, internal,
                    current_behavior=BehaviorState.GROOMING
                )
            
            # 执行理毛
            completed = self.grooming.execute(output, dt=0.1)
            cleanliness_history.append(self.body.body_cleanliness)
            
            if completed:
                break
        
        # 计算分数
        cleanliness_improvement = self.body.body_cleanliness - initial_cleanliness
        
        # 清洁度提升比例
        improvement_ratio = cleanliness_improvement / (100 - initial_cleanliness)
        
        score = min(1.0, improvement_ratio)
        passed = score >= self.THRESHOLDS['grooming_completion']
        
        return ValidationResult(
            test_name="Grooming",
            passed=passed,
            score=score,
            details={
                'initial_cleanliness': initial_cleanliness,
                'final_cleanliness': self.body.body_cleanliness,
                'improvement': cleanliness_improvement,
                'steps_used': len(cleanliness_history)
            }
        )
    
    def validate_foraging(self, n_steps: int = 500) -> ValidationResult:
        """
        验证觅食行为
        
        检查:
        - 找到食物的成功率
        - 趋化性跟随
        - 效率
        """
        self._reset()
        
        # 添加食物源
        food_id = self.arena.add_object(
            ObjectType.FOOD,
            position=(80, 80, 0),
            size=3.0,
            intensity=1.5
        )
        
        # 设置饥饿状态
        self.internal_state.hunger = 80.0
        self.controller.transition_to(BehaviorState.FORAGING)
        
        food_sources = [(80, 80, 1.5)]
        distance_to_food_history = []
        food_found = False
        
        for step in range(n_steps):
            # 获取感觉输入
            visual, olfactory, mechano, internal = self._get_sensory_input()
            
            # 大脑处理
            with torch.no_grad():
                output = self.brain(
                    visual, olfactory, mechano, internal,
                    current_behavior=BehaviorState.FORAGING
                )
            
            # 执行觅食
            displacement, found_food = self.foraging.execute(
                output, olfactory, food_sources, dt=0.1
            )
            
            # 更新物理
            self.physics.update_fly_physics(self.body, displacement, dt=0.1)
            
            # 记录到食物的距离
            food_pos = np.array([80, 80])
            distance = np.linalg.norm(self.body.position[:2] - food_pos)
            distance_to_food_history.append(distance)
            
            if found_food or distance < 3.0:
                food_found = True
                break
        
        # 计算分数
        if food_found:
            # 基于找到食物的步数评分
            efficiency_score = 1.0 - min(1.0, len(distance_to_food_history) / n_steps)
            score = 0.7 + 0.3 * efficiency_score
        else:
            # 基于接近食物的程度评分
            initial_distance = distance_to_food_history[0] if distance_to_food_history else 100
            final_distance = distance_to_food_history[-1] if distance_to_food_history else 100
            progress = max(0, (initial_distance - final_distance) / initial_distance)
            score = progress * 0.5
        
        passed = score >= self.THRESHOLDS['foraging_success_rate']
        
        # 清理
        self.arena.remove_object(food_id)
        
        return ValidationResult(
            test_name="Foraging",
            passed=passed,
            score=score,
            details={
                'food_found': food_found,
                'steps_to_find': len(distance_to_food_history) if food_found else None,
                'final_distance': distance_to_food_history[-1] if distance_to_food_history else None,
                'distance_improvement': distance_to_food_history[0] - distance_to_food_history[-1] 
                                       if len(distance_to_food_history) > 1 else 0
            }
        )
    
    def validate_escape(self, n_steps: int = 100) -> ValidationResult:
        """
        验证逃跑行为
        
        检查:
        - 响应延迟
        - 逃跑速度
        - 方向正确性
        """
        self._reset()
        
        # 设置初始位置
        self.body.position = np.array([50, 50, 0])
        initial_position = self.body.position[:2].copy()
        
        # 触发逃跑
        threat_direction = np.pi / 4  # 45度
        self.escape.trigger(looming_direction=threat_direction)
        self.controller.transition_to(BehaviorState.ESCAPING, force=True)
        
        # 记录逃跑响应
        escape_start_time = None
        response_latency = None
        escape_speeds = []
        positions = []
        
        for step in range(n_steps):
            start_time = time.time()
            
            # 执行逃跑
            displacement, completed = self.escape.execute(dt=0.1)
            
            # 记录响应时间
            if escape_start_time is None and np.linalg.norm(displacement) > 0.1:
                escape_start_time = step
                response_latency = step * 10  # ms (假设每步10ms)
            
            if escape_start_time is not None:
                speed = np.linalg.norm(displacement[:2]) / 0.1  # mm/s
                escape_speeds.append(speed)
            
            # 更新物理
            self.physics.update_fly_physics(self.body, displacement, dt=0.1)
            positions.append(self.body.position[:2].copy())
            
            if completed:
                break
        
        # 计算分数
        # 1. 响应延迟分数
        if response_latency is not None:
            latency_score = max(0, 1 - response_latency / 200)  # 200ms内满分
        else:
            latency_score = 0
        
        # 2. 逃跑速度分数
        if escape_speeds:
            avg_speed = np.mean(escape_speeds)
            speed_score = min(1.0, avg_speed / 50.0)  # 50mm/s满分
        else:
            speed_score = 0
        
        # 3. 方向正确性分数
        if len(positions) > 1:
            final_position = positions[-1]
            escape_direction = np.arctan2(
                final_position[1] - initial_position[1],
                final_position[0] - initial_position[0]
            )
            
            # 期望逃跑方向（远离威胁）
            expected_direction = (threat_direction + np.pi) % (2 * np.pi)
            direction_error = abs(np.arctan2(
                np.sin(escape_direction - expected_direction),
                np.cos(escape_direction - expected_direction)
            ))
            direction_score = max(0, 1 - direction_error / (np.pi / 2))
        else:
            direction_score = 0
        
        score = (latency_score * 0.4 + speed_score * 0.4 + direction_score * 0.2)
        passed = score >= 0.5  # 逃跑行为容忍度较低
        
        return ValidationResult(
            test_name="Escape Response",
            passed=passed,
            score=score,
            details={
                'response_latency_ms': response_latency,
                'avg_escape_speed': np.mean(escape_speeds) if escape_speeds else 0,
                'max_escape_speed': np.max(escape_speeds) if escape_speeds else 0,
                'direction_accuracy': direction_score
            }
        )
    
    def validate_state_switching(self, n_steps: int = 300) -> ValidationResult:
        """
        验证状态切换
        
        检查:
        - 饥饿 -> 觅食切换
        - 应激 -> 逃跑切换
        - 清洁度 -> 理毛切换
        """
        self._reset()
        
        transition_tests = []
        
        # 测试1: 饥饿 -> 觅食
        self.internal_state.hunger = 80
        self.internal_state.current_behavior = BehaviorState.IDLE
        
        for step in range(50):
            self.controller.update(dt=0.1)
            if self.internal_state.current_behavior == BehaviorState.FORAGING:
                transition_tests.append(('hunger_to_foraging', True, step))
                break
        else:
            transition_tests.append(('hunger_to_foraging', False, None))
        
        # 测试2: 应激 -> 逃跑
        self._reset()
        self.internal_state.stress = 90
        self.internal_state.current_behavior = BehaviorState.WALKING
        
        for step in range(20):
            self.controller.update(dt=0.1)
            if self.internal_state.current_behavior == BehaviorState.ESCAPING:
                transition_tests.append(('stress_to_escaping', True, step))
                break
        else:
            transition_tests.append(('stress_to_escaping', False, None))
        
        # 测试3: 低清洁度 -> 理毛
        self._reset()
        self.internal_state.cleanliness = 20
        self.internal_state.current_behavior = BehaviorState.IDLE
        
        for step in range(50):
            self.controller.update(dt=0.1)
            if self.internal_state.current_behavior == BehaviorState.GROOMING:
                transition_tests.append(('dirty_to_grooming', True, step))
                break
        else:
            transition_tests.append(('dirty_to_grooming', False, None))
        
        # 计算分数
        passed_tests = sum(1 for _, passed, _ in transition_tests if passed)
        total_tests = len(transition_tests)
        
        score = passed_tests / total_tests if total_tests > 0 else 0
        passed = score >= self.THRESHOLDS['state_transition_accuracy']
        
        return ValidationResult(
            test_name="State Switching",
            passed=passed,
            score=score,
            details={
                'tests': transition_tests,
                'passed_count': passed_tests,
                'total_count': total_tests
            }
        )
    
    def _reset(self):
        """重置所有状态"""
        self.body.reset(position=np.array([10, 10, 0]))
        self.internal_state = FlyInternalState()
        self.controller = BehaviorController(self.brain, self.body, self.internal_state)
        self.brain.reset_stp()
        self.brain.reset_history()
        self.vision.reset()
    
    def _get_sensory_input(self) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """获取感觉输入"""
        # 视觉输入
        visual_obs = self.arena.get_visual_observation(
            self.body.position,
            self.body.orientation,
            resolution=(32, 32)
        ).astype(np.float32)  # 确保float32
        visual = self.vision(visual_obs)
        
        # 嗅觉输入
        chem_grad, concentration = self.arena.get_chemical_gradient_at(self.body.position)
        olfactory = torch.zeros(16, device=self.device)
        olfactory[:2] = torch.tensor(chem_grad, dtype=torch.float32, device=self.device)
        olfactory[2] = concentration
        
        # 机械感受器输入（仅腿部传感器18维）
        leg_sensors = self.body.get_leg_sensor_data()
        mechano = torch.tensor(
            leg_sensors,
            dtype=torch.float32,
            device=self.device
        )
        
        # 内部状态输入
        internal = torch.tensor([
            self.internal_state.hunger / 100.0,
            self.internal_state.energy / 100.0,
            self.internal_state.stress / 100.0,
            self.internal_state.cleanliness / 100.0
        ], dtype=torch.float32, device=self.device)
        
        # 添加batch维度
        visual = visual.unsqueeze(0)
        olfactory = olfactory.unsqueeze(0)
        mechano = mechano.unsqueeze(0)
        internal = internal.unsqueeze(0)
        
        return visual, olfactory, mechano, internal
    
    def generate_report(self) -> str:
        """生成验证报告"""
        lines = []
        lines.append("=" * 70)
        lines.append("TNN-数字果蝇行为验证报告")
        lines.append("=" * 70)
        
        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            lines.append(f"\n{result.test_name}: {status} (Score: {result.score:.3f})")
            lines.append(f"  Details:")
            for key, value in result.details.items():
                if isinstance(value, float):
                    lines.append(f"    {key}: {value:.3f}")
                else:
                    lines.append(f"    {key}: {value}")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)


# 主测试入口
def run_validation():
    """运行完整验证"""
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"使用设备: {device}\n")
    
    # 创建组件
    brain = TNNFlyBrain(device=device)
    body = FlyBody()
    arena = FlyArena()
    arena.create_default_environment()
    
    # 创建验证器
    validator = BehaviorValidator(brain, body, arena, device)
    
    # 运行验证
    results = validator.validate_all()
    
    # 生成报告
    report = validator.generate_report()
    print("\n" + report)
    
    return results


if __name__ == "__main__":
    run_validation()
