"""
复杂生态环境系统
2D连续世界，支持多虫子互动

环境特性:
- 2D连续世界（1000×1000）
- 动态资源分布（食物、水源）
- 昼夜循环（光照变化）
- 信息素系统（虫子间间接通信）
- 简单物理（速度、动量、摩擦）
"""

import numpy as np
import torch
from typing import Tuple, List, Dict, Optional, Set
from dataclasses import dataclass, field
from scipy.spatial import KDTree
import warnings
warnings.filterwarnings('ignore')


@dataclass
class FoodSource:
    """食物源"""
    x: float
    y: float
    energy: float  # 剩余能量
    max_energy: float
    radius: float = 5.0
    regen_rate: float = 0.0  # 再生速率
    
    def consume(self, amount: float) -> float:
        """消耗食物，返回实际获得的能量"""
        actual = min(amount, self.energy)
        self.energy -= actual
        return actual
    
    def update(self, dt: float = 1.0):
        """更新（再生）"""
        self.energy = min(self.energy + self.regen_rate * dt, self.max_energy)
    
    def is_depleted(self) -> bool:
        """是否耗尽"""
        return self.energy < 0.1


@dataclass
class WaterSource:
    """水源"""
    x: float
    y: float
    radius: float
    purity: float = 1.0  # 水质（影响健康恢复）
    
    def is_inside(self, x: float, y: float) -> bool:
        """检查点是否在水源内"""
        dist = np.sqrt((x - self.x)**2 + (y - self.y)**2)
        return dist < self.radius


@dataclass
class Pheromone:
    """信息素标记"""
    x: float
    y: float
    type: str  # 'food', 'danger', 'trail', 'mate'
    intensity: float
    creator_id: int
    created_time: float
    decay_rate: float = 0.05
    
    def get_current_intensity(self, current_time: float) -> float:
        """获取当前强度（考虑衰减）"""
        age = current_time - self.created_time
        return self.intensity * np.exp(-self.decay_rate * age)
    
    def is_active(self, current_time: float, threshold: float = 0.01) -> bool:
        """是否仍然活跃"""
        return self.get_current_intensity(current_time) > threshold


@dataclass
class DangerSource:
    """危险源（捕食者、毒素等）"""
    x: float
    y: float
    radius: float
    damage_rate: float
    type: str = 'predator'  # 'predator', 'toxin', 'radiation'
    mobile: bool = False
    vx: float = 0.0
    vy: float = 0.0
    
    def update(self, dt: float = 1.0):
        """更新位置（如果是移动的）"""
        if self.mobile:
            self.x += self.vx * dt
            self.y += self.vy * dt


class DayNightCycle:
    """昼夜循环系统"""
    
    def __init__(
        self,
        day_length: float = 1000.0,  # 一天的长度（步数）
        max_light: float = 100.0,
        min_light: float = 5.0
    ):
        self.day_length = day_length
        self.max_light = max_light
        self.min_light = min_light
        self.time = 0.0
        
    def step(self, dt: float = 1.0):
        """推进时间"""
        self.time += dt
        
    def get_light_level(self) -> float:
        """获取当前光照水平"""
        # 正弦变化模拟昼夜
        phase = 2 * np.pi * self.time / self.day_length
        light = self.min_light + (self.max_light - self.min_light) * (0.5 + 0.5 * np.sin(phase - np.pi/2))
        return light
    
    def is_daytime(self) -> bool:
        """是否是白天"""
        phase = (self.time % self.day_length) / self.day_length
        return 0.25 < phase < 0.75
    
    def get_time_of_day(self) -> str:
        """获取时段描述"""
        phase = (self.time % self.day_length) / self.day_length
        if 0.2 < phase < 0.3:
            return 'dawn'
        elif 0.3 <= phase < 0.7:
            return 'day'
        elif 0.7 <= phase < 0.8:
            return 'dusk'
        else:
            return 'night'


class SuperEcosystem:
    """
    超级生态系统环境
    支持50+虫子同时仿真
    """
    
    def __init__(
        self,
        width: float = 1000.0,
        height: float = 1000.0,
        friction: float = 0.05,
        boundary_type: str = 'reflective',
        day_length: float = 1000.0,
        use_spatial_index: bool = True
    ):
        self.width = width
        self.height = height
        self.friction = friction
        self.boundary_type = boundary_type
        self.use_spatial_index = use_spatial_index
        
        # 环境元素
        self.foods: List[FoodSource] = []
        self.waters: List[WaterSource] = []
        self.dangers: List[DangerSource] = []
        self.pheromones: List[Pheromone] = []
        
        # 昼夜循环
        self.day_night = DayNightCycle(day_length=day_length)
        
        # 空间索引
        self._food_tree: Optional[KDTree] = None
        self._water_tree: Optional[KDTree] = None
        self._pheromone_tree: Optional[KDTree] = None
        self._spatial_index_valid = False
        
        # 统计信息
        self.step_count = 0
        self.total_food_consumed = 0.0
        self.pheromone_count = 0
        
        # 环境参数
        self.global_temperature = 20.0  # 摄氏度
        self.global_humidity = 0.5  # 湿度
        
    def add_food(
        self,
        x: float,
        y: float,
        energy: float = 50.0,
        radius: float = 5.0,
        regen_rate: float = 0.0
    ):
        """添加食物源"""
        self.foods.append(FoodSource(x, y, energy, energy, radius, regen_rate))
        self._spatial_index_valid = False
        
    def add_water(
        self,
        x: float,
        y: float,
        radius: float = 20.0,
        purity: float = 1.0
    ):
        """添加水源"""
        self.waters.append(WaterSource(x, y, radius, purity))
        self._spatial_index_valid = False
        
    def add_danger(
        self,
        x: float,
        y: float,
        radius: float = 10.0,
        damage_rate: float = 5.0,
        danger_type: str = 'predator',
        mobile: bool = False
    ):
        """添加危险源"""
        self.dangers.append(DangerSource(x, y, radius, damage_rate, danger_type, mobile))
        
    def add_pheromone(
        self,
        x: float,
        y: float,
        pheromone_type: str,
        intensity: float,
        creator_id: int,
        decay_rate: float = 0.05
    ):
        """添加信息素"""
        self.pheromones.append(Pheromone(
            x, y, pheromone_type, intensity, creator_id,
            self.step_count, decay_rate
        ))
        self.pheromone_count += 1
        self._spatial_index_valid = False
        
    def _update_spatial_index(self):
        """更新空间索引"""
        if not self.use_spatial_index:
            return
            
        # 食物索引
        if self.foods:
            food_points = np.array([[f.x, f.y] for f in self.foods])
            self._food_tree = KDTree(food_points)
        
        # 水源索引
        if self.waters:
            water_points = np.array([[w.x, w.y] for w in self.waters])
            self._water_tree = KDTree(water_points)
        
        # 信息素索引
        active_pheromones = [p for p in self.pheromones if p.is_active(self.step_count)]
        if active_pheromones:
            phero_points = np.array([[p.x, p.y] for p in active_pheromones])
            self._pheromone_tree = KDTree(phero_points)
        
        self._spatial_index_valid = True
    
    def get_nearby_food(self, x: float, y: float, radius: float = 50.0) -> List[FoodSource]:
        """获取附近的食物源"""
        if self.use_spatial_index and self._food_tree is not None:
            indices = self._food_tree.query_ball_point([x, y], radius)
            return [self.foods[i] for i in indices]
        else:
            return [f for f in self.foods 
                   if np.sqrt((f.x-x)**2 + (f.y-y)**2) < radius]
    
    def get_nearby_water(self, x: float, y: float, radius: float = 50.0) -> List[WaterSource]:
        """获取附近的水源"""
        if self.use_spatial_index and self._water_tree is not None:
            indices = self._water_tree.query_ball_point([x, y], radius)
            return [self.waters[i] for i in indices]
        else:
            return [w for w in self.waters 
                   if np.sqrt((w.x-x)**2 + (w.y-y)**2) < radius]
    
    def get_pheromone_gradient(
        self,
        x: float,
        y: float,
        pheromone_type: Optional[str] = None,
        radius: float = 30.0
    ) -> Tuple[float, float, float]:
        """
        获取信息素梯度
        返回: (梯度_x, 梯度_y, 总强度)
        """
        active_pheromones = [
            p for p in self.pheromones 
            if p.is_active(self.step_count) and 
            (pheromone_type is None or p.type == pheromone_type)
        ]
        
        if not active_pheromones:
            return 0.0, 0.0, 0.0
        
        total_grad_x = 0.0
        total_grad_y = 0.0
        total_intensity = 0.0
        
        for p in active_pheromones:
            dx = p.x - x
            dy = p.y - y
            dist = np.sqrt(dx**2 + dy**2)
            
            if dist < radius and dist > 0.1:
                intensity = p.get_current_intensity(self.step_count)
                # 梯度方向指向信息素源
                total_grad_x += intensity * dx / dist / (dist + 1)
                total_grad_y += intensity * dy / dist / (dist + 1)
                total_intensity += intensity
        
        return total_grad_x, total_grad_y, total_intensity
    
    def get_light_at(self, x: float, y: float) -> float:
        """获取某位置的光照强度"""
        base_light = self.day_night.get_light_level()
        # 简化的光照模型：假设有一个主光源在天空
        return base_light
    
    def get_light_gradient(self, x: float, y: float, delta: float = 5.0) -> Tuple[float, float]:
        """获取光照梯度"""
        center = self.get_light_at(x, y)
        right = self.get_light_at(x + delta, y)
        left = self.get_light_at(x - delta, y)
        up = self.get_light_at(x, y + delta)
        down = self.get_light_at(x, y - delta)
        
        grad_x = (right - left) / (2 * delta)
        grad_y = (up - down) / (2 * delta)
        
        return grad_x, grad_y
    
    def get_chemical_gradient(
        self,
        x: float,
        y: float,
        delta: float = 5.0
    ) -> Tuple[float, float, float]:
        """
        获取化学梯度（食物+水+信息素）
        返回: (grad_x, grad_y, total_chemical)
        """
        center = self._get_chemical_concentration(x, y)
        right = self._get_chemical_concentration(x + delta, y)
        left = self._get_chemical_concentration(x - delta, y)
        up = self._get_chemical_concentration(x, y + delta)
        down = self._get_chemical_concentration(x, y - delta)
        
        grad_x = (right - left) / (2 * delta)
        grad_y = (up - down) / (2 * delta)
        
        return grad_x, grad_y, center
    
    def _get_chemical_concentration(self, x: float, y: float) -> float:
        """获取某位置的化学浓度"""
        concentration = 0.0
        
        # 食物化学信号
        for food in self.foods:
            dist = np.sqrt((food.x - x)**2 + (food.y - y)**2)
            if dist < food.radius * 3:
                concentration += food.energy / (1 + dist)
        
        # 水源化学信号
        for water in self.waters:
            if water.is_inside(x, y):
                concentration += 10.0 * water.purity
        
        # 信息素信号
        _, _, phero_intensity = self.get_pheromone_gradient(x, y, radius=50.0)
        concentration += phero_intensity
        
        return concentration
    
    def get_obstacle_distance(self, x: float, y: float, angle: float, max_dist: float = 50.0) -> float:
        """沿某方向测量到障碍物的距离"""
        step = 1.0
        for d in np.arange(0, max_dist, step):
            check_x = x + d * np.cos(angle)
            check_y = y + d * np.sin(angle)
            
            if not self._is_valid_position(check_x, check_y):
                return d
            
            # 检查危险源
            for danger in self.dangers:
                dist = np.sqrt((check_x - danger.x)**2 + (check_y - danger.y)**2)
                if dist < danger.radius:
                    return d
        
        return max_dist
    
    def _is_valid_position(self, x: float, y: float, margin: float = 0.0) -> bool:
        """检查位置是否有效（在边界内）"""
        return margin <= x <= self.width - margin and margin <= y <= self.height - margin
    
    def apply_physics(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        dt: float = 0.1
    ) -> Tuple[float, float, float, float]:
        """
        应用物理规则
        返回新的位置和速度
        """
        # 应用摩擦
        vx *= (1 - self.friction * dt)
        vy *= (1 - self.friction * dt)
        
        # 更新位置
        new_x = x + vx * dt
        new_y = y + vy * dt
        
        # 边界处理
        if self.boundary_type == 'reflective':
            if new_x < 0:
                new_x = 0
                vx = -vx * 0.5
            elif new_x > self.width:
                new_x = self.width
                vx = -vx * 0.5
                
            if new_y < 0:
                new_y = 0
                vy = -vy * 0.5
            elif new_y > self.height:
                new_y = self.height
                vy = -vy * 0.5
                
        elif self.boundary_type == 'toroidal':
            new_x = new_x % self.width
            new_y = new_y % self.height
        
        return new_x, new_y, vx, vy
    
    def check_danger(self, x: float, y: float, safety_radius: float = 5.0) -> Tuple[bool, float]:
        """
        检查是否在危险区域内
        返回: (是否危险, 危险强度)
        """
        max_danger = 0.0
        for danger in self.dangers:
            dist = np.sqrt((x - danger.x)**2 + (y - danger.y)**2)
            if dist < danger.radius + safety_radius:
                intensity = danger.damage_rate * (1 - dist / (danger.radius + safety_radius))
                max_danger = max(max_danger, intensity)
        
        return max_danger > 0, max_danger
    
    def consume_food(self, x: float, y: float, amount: float, radius: float = 5.0) -> float:
        """消耗附近的食物"""
        total_consumed = 0.0
        nearby_food = self.get_nearby_food(x, y, radius)
        
        for food in nearby_food:
            dist = np.sqrt((food.x - x)**2 + (food.y - y)**2)
            if dist < radius:
                consumed = food.consume(amount)
                total_consumed += consumed
                self.total_food_consumed += consumed
        
        # 移除耗尽的食物
        self.foods = [f for f in self.foods if not f.is_depleted()]
        if nearby_food:
            self._spatial_index_valid = False
        
        return total_consumed
    
    def step(self, dt: float = 1.0):
        """
        环境步进
        """
        self.step_count += 1
        
        # 更新昼夜
        self.day_night.step(dt)
        
        # 更新食物再生
        for food in self.foods:
            food.update(dt)
        
        # 更新危险源
        for danger in self.dangers:
            danger.update(dt)
            # 保持危险源在边界内
            danger.x = np.clip(danger.x, 0, self.width)
            danger.y = np.clip(danger.y, 0, self.height)
        
        # 清理过期信息素
        self.pheromones = [p for p in self.pheromones if p.is_active(self.step_count)]
        
        # 更新空间索引
        if not self._spatial_index_valid:
            self._update_spatial_index()
    
    def get_sensor_readings(
        self,
        x: float,
        y: float,
        heading: float,
        other_worms: Optional[List[Tuple[int, float, float]]] = None
    ) -> np.ndarray:
        """
        获取完整的传感器读数（32维）
        
        传感器布局:
        - [0:8]: 光感受器（360度，每45度一个）
        - [8:16]: 化学感受器（360度）
        - [16:24]: 触觉传感器（360度）
        - [24:28]: 内部状态（能量、健康、年龄、繁殖欲）
        - [28:32]: 社交传感器（探测其他虫子）
        """
        readings = np.zeros(32, dtype=np.float32)
        
        # 光照水平
        light_level = self.get_light_at(x, y)
        
        # === 光感受器（8个，360度）===
        for i in range(8):
            angle = heading + i * np.pi / 4
            # 方向上的光照变化
            lx = x + np.cos(angle) * 10
            ly = y + np.sin(angle) * 10
            local_light = self.get_light_at(lx, ly)
            # 归一化到[-1, 1]
            readings[i] = (local_light - 50) / 50
        
        # === 化学感受器（8个，360度）===
        chem_x, chem_y, chem_total = self.get_chemical_gradient(x, y)
        for i in range(8):
            angle = heading + i * np.pi / 4
            # 化学梯度投影到该方向
            proj = chem_x * np.cos(angle) + chem_y * np.sin(angle)
            readings[8 + i] = np.tanh(proj / 10)
        
        # === 触觉传感器（8个，360度）===
        for i in range(8):
            angle = heading + i * np.pi / 4
            dist = self.get_obstacle_distance(x, y, angle, max_dist=50.0)
            readings[16 + i] = 1.0 - dist / 50.0  # 越近值越大
        
        # === 社交传感器（4个）===
        if other_worms:
            # 计算最近虫子的相对位置和距离
            nearest_dist = float('inf')
            nearest_angle = 0.0
            avg_distance = 0.0
            count = 0
            
            for worm_id, wx, wy in other_worms:
                dx = wx - x
                dy = wy - y
                dist = np.sqrt(dx**2 + dy**2)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_angle = np.arctan2(dy, dx) - heading
                avg_distance += dist
                count += 1
            
            if count > 0:
                avg_distance /= count
                readings[28] = np.tanh(nearest_dist / 50)  # 最近虫子距离
                readings[29] = np.sin(nearest_angle)  # 最近虫子方向sin
                readings[30] = np.cos(nearest_angle)  # 最近虫子方向cos
                readings[31] = min(count / 10, 1.0)  # 周围虫子密度
        
        return readings
    
    def create_random_environment(
        self,
        n_food: int = 20,
        n_water: int = 5,
        n_dangers: int = 3
    ):
        """创建随机环境"""
        # 随机食物分布（聚集分布）
        n_clusters = max(1, n_food // 5)
        for _ in range(n_clusters):
            cx = np.random.uniform(100, self.width - 100)
            cy = np.random.uniform(100, self.height - 100)
            for _ in range(n_food // n_clusters):
                x = cx + np.random.normal(0, 50)
                y = cy + np.random.normal(0, 50)
                x = np.clip(x, 10, self.width - 10)
                y = np.clip(y, 10, self.height - 10)
                self.add_food(x, y, energy=np.random.uniform(30, 100))
        
        # 随机水源
        for _ in range(n_water):
            x = np.random.uniform(100, self.width - 100)
            y = np.random.uniform(100, self.height - 100)
            self.add_water(x, y, radius=np.random.uniform(15, 40))
        
        # 随机危险源
        for _ in range(n_dangers):
            x = np.random.uniform(100, self.width - 100)
            y = np.random.uniform(100, self.height - 100)
            self.add_danger(x, y, radius=np.random.uniform(5, 15))
    
    def get_statistics(self) -> Dict:
        """获取环境统计信息"""
        return {
            'step_count': self.step_count,
            'time_of_day': self.day_night.get_time_of_day(),
            'light_level': self.day_night.get_light_level(),
            'n_food': len(self.foods),
            'n_water': len(self.waters),
            'n_dangers': len(self.dangers),
            'n_pheromones': len(self.pheromones),
            'total_food_consumed': self.total_food_consumed
        }


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("复杂生态系统测试")
    print("=" * 60)
    
    # 创建环境
    env = SuperEcosystem(width=1000, height=1000)
    env.create_random_environment(n_food=20, n_water=5, n_dangers=2)
    
    print("\n初始环境状态:")
    stats = env.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 测试传感器
    print("\n传感器测试（位置: 500, 500）:")
    readings = env.get_sensor_readings(500, 500, 0.0)
    print(f"  光感受器[0:8]: {readings[0:8]}")
    print(f"  化学感受器[8:16]: {readings[8:16]}")
    print(f"  触觉传感器[16:24]: {readings[16:24]}")
    print(f"  社交传感器[28:32]: {readings[28:32]}")
    
    # 模拟几步
    print("\n模拟100步...")
    for _ in range(100):
        env.step()
    
    print("\n100步后环境状态:")
    stats = env.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
