"""
TNN Digital Fly - 果蝇个体涌现行为验证实验

本模块包含TNN-数字果蝇的完整实现：
- tnn_fly_brain: 250K参数TNN大脑
- fly_body: 物理身体模型
- fly_vision: 视觉处理系统
- behaviors: 行为模块
- physics_env: 3D物理环境
- compare_with_digital_fly: 与Eon对比分析
- visualize_behaviors: 行为可视化
- validate_behaviors: 行为验证套件
"""

__version__ = "1.0.0"
__author__ = "TNN Research Team"

# 主要类导出
from .tnn_fly_brain import TNNFlyBrain, BehaviorState, FlyInternalState
from .fly_body import FlyBody, LegID, TripodGait
from .fly_vision import FlyVision
from .physics_env import FlyArena, PhysicsSimulator
from .behaviors import (
    BehaviorController,
    LocomotionBehavior,
    GroomingBehavior,
    ForagingBehavior,
    EscapeBehavior
)
from .compare_with_digital_fly import DigitalFlyComparator
from .visualize_behaviors import BehaviorVisualizer
from .validate_behaviors import BehaviorValidator

__all__ = [
    'TNNFlyBrain',
    'BehaviorState',
    'FlyInternalState',
    'FlyBody',
    'LegID',
    'TripodGait',
    'FlyVision',
    'FlyArena',
    'PhysicsSimulator',
    'BehaviorController',
    'LocomotionBehavior',
    'GroomingBehavior',
    'ForagingBehavior',
    'EscapeBehavior',
    'DigitalFlyComparator',
    'BehaviorVisualizer',
    'BehaviorValidator'
]
