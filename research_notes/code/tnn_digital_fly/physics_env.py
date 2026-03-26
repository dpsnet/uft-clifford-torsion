"""
3D物理环境
简化版MuJoCo-like物理引擎，用于果蝇仿真

环境特性:
- 2D平面arena，支持高度变化
- 重力、摩擦、碰撞
- 食物源、障碍物
- 化学梯度扩散
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum


class ObjectType(Enum):
    """环境物体类型"""
    FOOD = "food"
    OBSTACLE = "obstacle"
    DANGER = "danger"
    WATER = "water"


@dataclass
class EnvironmentObject:
    """环境中的物体"""
    obj_id: int
    obj_type: ObjectType
    position: np.ndarray  # [x, y, z]
    size: float
    intensity: float = 1.0  # 食物质量/危险程度等
    active: bool = True
    
    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取边界框 (min, max)"""
        half_size = self.size / 2
        min_bound = self.position - half_size
        max_bound = self.position + half_size
        return min_bound, max_bound


@dataclass
class ChemicalGradient:
    """化学梯度场"""
    center: np.ndarray
    concentration: float
    decay_rate: float = 0.1
    diffusion_rate: float = 0.5
    
    def get_concentration_at(self, position: np.ndarray) -> float:
        """获取某位置的化学浓度"""
        distance = np.linalg.norm(position[:2] - self.center[:2])
        concentration = self.concentration * np.exp(-self.decay_rate * distance)
        return max(0, concentration)


class FlyArena:
    """
    果蝇竞技场环境
    
    物理参数:
    - 尺寸: 100mm × 100mm 平面
    - 重力: 9.8 m/s² (向下)
    - 摩擦系数: 0.5
    """
    
    def __init__(
        self,
        size: Tuple[float, float] = (100.0, 100.0),
        gravity: float = 9.8,
        friction_coefficient: float = 0.5,
        dt: float = 0.01
    ):
        self.size = size
        self.gravity = gravity
        self.friction_coefficient = friction_coefficient
        self.dt = dt
        
        # 环境中的物体
        self.objects: Dict[int, EnvironmentObject] = {}
        self.next_obj_id = 0
        
        # 化学梯度
        self.chemical_gradients: List[ChemicalGradient] = []
        
        # 时间
        self.time = 0.0
        
        # 环境状态
        self.ambient_light = 100.0
        self.temperature = 25.0  # °C
        self.humidity = 50.0     # %
    
    def add_object(
        self,
        obj_type: ObjectType,
        position: Tuple[float, float, float],
        size: float,
        intensity: float = 1.0
    ) -> int:
        """
        添加物体到环境
        
        Returns:
            obj_id: 物体ID
        """
        obj_id = self.next_obj_id
        self.next_obj_id += 1
        
        obj = EnvironmentObject(
            obj_id=obj_id,
            obj_type=obj_type,
            position=np.array(position),
            size=size,
            intensity=intensity
        )
        
        self.objects[obj_id] = obj
        
        # 如果是食物，添加化学梯度
        if obj_type == ObjectType.FOOD:
            gradient = ChemicalGradient(
                center=np.array(position),
                concentration=intensity * 10.0,
                decay_rate=0.05
            )
            self.chemical_gradients.append(gradient)
        
        return obj_id
    
    def remove_object(self, obj_id: int) -> bool:
        """移除物体"""
        if obj_id in self.objects:
            obj = self.objects.pop(obj_id)
            
            # 移除对应的化学梯度
            self.chemical_gradients = [
                g for g in self.chemical_gradients 
                if not np.allclose(g.center, obj.position)
            ]
            return True
        return False
    
    def get_objects_by_type(self, obj_type: ObjectType) -> List[EnvironmentObject]:
        """获取特定类型的物体列表"""
        return [obj for obj in self.objects.values() if obj.obj_type == obj_type]
    
    def get_chemical_gradient_at(self, position: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        获取某位置的化学梯度
        
        Returns:
            gradient_vector: 梯度方向
            total_concentration: 总浓度
        """
        if not self.chemical_gradients:
            return np.zeros(2), 0.0
        
        total_concentration = 0.0
        gradient_vector = np.zeros(2)
        
        for chem in self.chemical_gradients:
            conc = chem.get_concentration_at(position)
            total_concentration += conc
            
            # 计算梯度方向（指向浓度增加的方向）
            direction = chem.center[:2] - position[:2]
            distance = np.linalg.norm(direction)
            
            if distance > 0.001:
                direction = direction / distance
                gradient_vector += direction * conc
        
        if np.linalg.norm(gradient_vector) > 0:
            gradient_vector = gradient_vector / np.linalg.norm(gradient_vector)
        
        return gradient_vector, total_concentration
    
    def check_collision(
        self,
        position: np.ndarray,
        radius: float = 0.5
    ) -> Tuple[bool, Optional[EnvironmentObject]]:
        """
        检查与环境中物体的碰撞
        
        Returns:
            collided: 是否碰撞
            collided_object: 碰撞的物体（如果有）
        """
        for obj in self.objects.values():
            if not obj.active:
                continue
            
            distance = np.linalg.norm(position[:2] - obj.position[:2])
            if distance < (radius + obj.size / 2):
                return True, obj
        
        return False, None
    
    def check_boundaries(self, position: np.ndarray) -> Tuple[bool, np.ndarray]:
        """
        检查是否超出边界
        
        Returns:
            out_of_bounds: 是否越界
            corrected_position: 修正后的位置
        """
        x, y, z = position
        corrected = position.copy()
        out_of_bounds = False
        
        # x边界
        if x < 0:
            corrected[0] = 0
            out_of_bounds = True
        elif x > self.size[0]:
            corrected[0] = self.size[0]
            out_of_bounds = True
        
        # y边界
        if y < 0:
            corrected[1] = 0
            out_of_bounds = True
        elif y > self.size[1]:
            corrected[1] = self.size[1]
            out_of_bounds = True
        
        # z边界（地面）
        if z < 0:
            corrected[2] = 0
            out_of_bounds = True
        
        return out_of_bounds, corrected
    
    def get_visual_observation(
        self,
        position: np.ndarray,
        orientation: np.ndarray,
        resolution: Tuple[int, int] = (32, 32),
        fov: float = np.pi / 2  # 90度视野
    ) -> np.ndarray:
        """
        获取某位置的视觉观察
        
        简化版：返回灰度图像，亮度表示物体
        
        Returns:
            observation: [H, W] 灰度图像
        """
        h, w = resolution
        observation = np.zeros((h, w))
        
        # 视野范围
        heading = orientation[2]  # 偏航角
        fov_half = fov / 2
        
        # 对每个像素计算对应的世界方向
        for i in range(h):
            for j in range(w):
                # 归一化角度
                angle_norm = (j / (w - 1)) * 2 - 1  # -1 到 1
                angle = heading + angle_norm * fov_half
                
                # 射线方向
                ray_dir = np.array([np.cos(angle), np.sin(angle)])
                
                # 检查与物体的交点
                max_brightness = 0.0
                
                for obj in self.objects.values():
                    if not obj.active:
                        continue
                    
                    # 简化：点光源模型
                    to_obj = obj.position[:2] - position[:2]
                    distance = np.linalg.norm(to_obj)
                    
                    if distance < 0.001:
                        continue
                    
                    # 检查是否在视野内
                    angle_to_obj = np.arctan2(to_obj[1], to_obj[0])
                    angle_diff = np.abs(np.arctan2(
                        np.sin(angle_to_obj - angle),
                        np.cos(angle_to_obj - angle)
                    ))
                    
                    if angle_diff < fov_half / w * 2:  # 近似
                        # 亮度随距离衰减
                        brightness = obj.intensity / (1 + distance * 0.1)
                        
                        if obj.obj_type == ObjectType.FOOD:
                            brightness *= 1.5  # 食物更亮
                        elif obj.obj_type == ObjectType.DANGER:
                            brightness *= 0.5  # 危险物较暗
                        
                        max_brightness = max(max_brightness, min(1.0, brightness))
                
                observation[i, j] = max_brightness
        
        # 添加环境光照
        observation += self.ambient_light / 1000.0
        observation = np.clip(observation, 0, 1)
        
        return observation
    
    def update(self, dt: Optional[float] = None):
        """更新环境状态"""
        if dt is None:
            dt = self.dt
        
        self.time += dt
        
        # 更新化学梯度（扩散和衰减）
        for chem in self.chemical_gradients:
            chem.concentration *= (1 - chem.decay_rate * dt)
        
        # 移除浓度太低的梯度
        self.chemical_gradients = [
            chem for chem in self.chemical_gradients 
            if chem.concentration > 0.1
        ]
    
    def get_state_summary(self) -> Dict:
        """获取环境状态摘要"""
        return {
            'time': self.time,
            'n_objects': len(self.objects),
            'n_food': len(self.get_objects_by_type(ObjectType.FOOD)),
            'n_obstacles': len(self.get_objects_by_type(ObjectType.OBSTACLE)),
            'n_dangers': len(self.get_objects_by_type(ObjectType.DANGER)),
            'n_chemical_gradients': len(self.chemical_gradients),
            'ambient_light': self.ambient_light,
            'temperature': self.temperature,
            'humidity': self.humidity
        }
    
    def reset(self):
        """重置环境"""
        self.objects.clear()
        self.chemical_gradients.clear()
        self.next_obj_id = 0
        self.time = 0.0
    
    def create_default_environment(self):
        """创建默认测试环境"""
        self.reset()
        
        # 添加食物源
        self.add_object(
            ObjectType.FOOD,
            position=(20, 20, 0),
            size=2.0,
            intensity=1.0
        )
        self.add_object(
            ObjectType.FOOD,
            position=(80, 80, 0),
            size=3.0,
            intensity=1.5
        )
        
        # 添加障碍物
        self.add_object(
            ObjectType.OBSTACLE,
            position=(50, 30, 0),
            size=5.0,
            intensity=1.0
        )
        
        # 添加危险源
        self.add_object(
            ObjectType.DANGER,
            position=(70, 20, 0),
            size=3.0,
            intensity=0.8
        )


class PhysicsSimulator:
    """
    简化物理仿真器
    处理果蝇与环境的物理交互
    """
    
    def __init__(self, arena: FlyArena):
        self.arena = arena
        
        # 物理参数
        self.air_resistance = 0.1
        self.ground_friction = 0.5
        self.restitution = 0.3  # 弹性系数
    
    def update_fly_physics(
        self,
        body,
        intended_displacement: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, Dict]:
        """
        更新果蝇物理状态
        
        Args:
            body: FlyBody对象
            intended_displacement: 意图位移
            dt: 时间步长
        
        Returns:
            actual_displacement: 实际位移
            physics_info: 物理信息字典
        """
        current_pos = body.position.copy()
        
        # 应用意图位移
        new_pos = current_pos + intended_displacement
        
        # 边界检查
        out_of_bounds, new_pos = self.arena.check_boundaries(new_pos)
        
        # 碰撞检测
        collided, collided_obj = self.arena.check_collision(new_pos)
        
        if collided:
            # 简单的反弹处理
            if collided_obj is not None:
                # 计算碰撞法线
                collision_normal = new_pos[:2] - collided_obj.position[:2]
                collision_normal = collision_normal / (np.linalg.norm(collision_normal) + 1e-6)
                
                # 反向位移
                new_pos[:2] = current_pos[:2] - collision_normal * 0.1
        
        # 地面接触
        on_ground = new_pos[2] <= 0.01
        
        if on_ground:
            new_pos[2] = 0.0
            # 应用地面摩擦
            if np.linalg.norm(intended_displacement[:2]) > 0:
                friction_force = -self.ground_friction * intended_displacement[:2]
                new_pos[:2] += friction_force * dt
        
        # 计算实际位移
        actual_displacement = new_pos - current_pos
        body.position = new_pos
        
        # 更新速度
        body.velocity = actual_displacement / dt
        
        # 物理信息
        physics_info = {
            'collided': collided,
            'collided_with': collided_obj.obj_type if collided_obj else None,
            'out_of_bounds': out_of_bounds,
            'on_ground': on_ground,
            'actual_displacement': actual_displacement,
            'speed': np.linalg.norm(body.velocity)
        }
        
        return actual_displacement, physics_info
    
    def apply_external_force(
        self,
        body,
        force: np.ndarray,
        dt: float
    ):
        """应用外力"""
        acceleration = force / body.mass
        body.velocity += acceleration * dt


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("物理环境测试")
    print("=" * 60)
    
    # 创建环境
    arena = FlyArena(size=(100, 100))
    arena.create_default_environment()
    
    print("\n环境参数:")
    print(f"  尺寸: {arena.size}")
    print(f"  重力: {arena.gravity}")
    print(f"  摩擦系数: {arena.friction_coefficient}")
    
    summary = arena.get_state_summary()
    print("\n环境状态:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # 测试化学梯度
    print("\n化学梯度测试:")
    test_positions = [
        np.array([20, 20, 0]),
        np.array([30, 30, 0]),
        np.array([50, 50, 0])
    ]
    
    for pos in test_positions:
        gradient, concentration = arena.get_chemical_gradient_at(pos)
        print(f"  位置 ({pos[0]:.0f}, {pos[1]:.0f}): 浓度={concentration:.3f}, 梯度=[{gradient[0]:.3f}, {gradient[1]:.3f}]")
    
    # 测试视觉观察
    print("\n视觉观察测试:")
    obs = arena.get_visual_observation(
        position=np.array([50, 50, 0]),
        orientation=np.array([0, 0, 0]),
        resolution=(16, 16)
    )
    print(f"  观察形状: {obs.shape}")
    print(f"  亮度范围: [{obs.min():.3f}, {obs.max():.3f}]")
    
    # 测试碰撞检测
    print("\n碰撞检测测试:")
    test_positions = [
        np.array([20, 20, 0]),  # 食物位置
        np.array([50, 30, 0]),  # 障碍物位置
        np.array([50, 50, 0])   # 空位置
    ]
    
    for pos in test_positions:
        collided, obj = arena.check_collision(pos)
        if collided and obj:
            print(f"  位置 ({pos[0]:.0f}, {pos[1]:.0f}): 碰撞 {obj.obj_type.value}")
        else:
            print(f"  位置 ({pos[0]:.0f}, {pos[1]:.0f}): 无碰撞")
    
    print("\n" + "=" * 60)
    print("测试完成!")
