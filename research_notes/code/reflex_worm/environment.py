"""
微型TNN"反射虫"实验 - 2D环境
基于统一场理论的神经网络几何化实现

研究目标：在简单2D环境中验证"结构即行为"假说
"""

import numpy as np
import torch
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass


@dataclass
class LightSource:
    """光源"""
    x: float
    y: float
    intensity: float  # 亮度强度
    radius: float     # 有效半径
    
    def get_brightness_at(self, x: float, y: float) -> float:
        """计算某位置的亮度（平方反比衰减）"""
        dist = np.sqrt((x - self.x)**2 + (y - self.y)**2)
        if dist < 1.0:
            dist = 1.0
        brightness = self.intensity / (1 + (dist / self.radius)**2)
        return min(brightness, self.intensity)


@dataclass  
class Obstacle:
    """障碍物"""
    x: float
    y: float
    radius: float
    
    def contains(self, x: float, y: float) -> bool:
        """检查点是否在障碍物内"""
        dist = np.sqrt((x - self.x)**2 + (y - self.y)**2)
        return dist < self.radius


class Environment2D:
    """
    2D网格世界环境
    包含光源、障碍物、边界
    """
    
    def __init__(
        self,
        width: int = 100,
        height: int = 100,
        friction: float = 0.1,
        boundary_type: str = 'reflective'  # 'reflective', 'toroidal', 'absorbing'
    ):
        self.width = width
        self.height = height
        self.friction = friction
        self.boundary_type = boundary_type
        
        # 环境元素
        self.lights: List[LightSource] = []
        self.obstacles: List[Obstacle] = []
        
        # 亮度缓存（用于优化）
        self._brightness_cache = None
        self._cache_valid = False
        
    def add_light(self, x: float, y: float, intensity: float = 100.0, radius: float = 50.0):
        """添加光源"""
        self.lights.append(LightSource(x, y, intensity, radius))
        self._cache_valid = False
        
    def add_obstacle(self, x: float, y: float, radius: float = 5.0):
        """添加障碍物"""
        self.obstacles.append(Obstacle(x, y, radius))
        
    def get_total_brightness(self, x: float, y: float) -> float:
        """获取某位置的总亮度"""
        total = 0.0
        for light in self.lights:
            total += light.get_brightness_at(x, y)
        return total
    
    def get_brightness_gradient(self, x: float, y: float, delta: float = 1.0) -> Tuple[float, float]:
        """
        计算亮度梯度（用于光感受器）
        返回 (dx, dy) 方向的亮度变化率
        """
        center = self.get_total_brightness(x, y)
        right = self.get_total_brightness(x + delta, y)
        left = self.get_total_brightness(x - delta, y)
        up = self.get_total_brightness(x, y + delta)
        down = self.get_total_brightness(x, y - delta)
        
        grad_x = (right - left) / (2 * delta)
        grad_y = (up - down) / (2 * delta)
        
        return grad_x, grad_y
    
    def check_collision(self, x: float, y: float, radius: float = 0.5) -> Tuple[bool, Optional[Obstacle]]:
        """
        检查是否与障碍物碰撞
        返回 (是否碰撞, 碰撞的障碍物)
        """
        # 检查边界碰撞
        if self.boundary_type == 'reflective':
            if x < radius or x > self.width - radius or \
               y < radius or y > self.height - radius:
                return True, None
        
        # 检查障碍物碰撞
        for obs in self.obstacles:
            dist = np.sqrt((x - obs.x)**2 + (y - obs.y)**2)
            if dist < (obs.radius + radius):
                return True, obs
                
        return False, None
    
    def get_distance_to_obstacle(self, x: float, y: float, angle: float, max_dist: float = 20.0) -> float:
        """
        沿某方向测量到障碍物的距离（用于触觉传感器）
        angle: 弧度，0表示+x方向
        """
        step = 0.5
        for d in np.arange(0, max_dist, step):
            check_x = x + d * np.cos(angle)
            check_y = y + d * np.sin(angle)
            
            collision, _ = self.check_collision(check_x, check_y, radius=0.1)
            if collision:
                return d
                
        return max_dist
    
    def apply_physics(self, x: float, y: float, vx: float, vy: float, dt: float = 0.1) -> Tuple[float, float, float, float]:
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
            if new_x < 0 or new_x > self.width:
                vx = -vx * 0.5  # 弹性碰撞，有能量损失
                new_x = np.clip(new_x, 0, self.width)
            if new_y < 0 or new_y > self.height:
                vy = -vy * 0.5
                new_y = np.clip(new_y, 0, self.height)
                
        elif self.boundary_type == 'toroidal':
            new_x = new_x % self.width
            new_y = new_y % self.height
            
        # 障碍物碰撞响应
        collision, obs = self.check_collision(new_x, new_y)
        if collision and obs is not None:
            # 计算碰撞法线
            dx = new_x - obs.x
            dy = new_y - obs.y
            dist = np.sqrt(dx**2 + dy**2)
            if dist > 0:
                nx, ny = dx/dist, dy/dist
                # 反射速度
                dot = vx * nx + vy * ny
                vx = vx - 2 * dot * nx * 0.5
                vy = vy - 2 * dot * ny * 0.5
                # 推开
                new_x = obs.x + nx * (obs.radius + 0.6)
                new_y = obs.y + ny * (obs.radius + 0.6)
        
        return new_x, new_y, vx, vy
    
    def create_default_environment(self, config: str = 'simple'):
        """创建预设环境"""
        if config == 'simple':
            # 简单环境：中央光源，四周无边界
            self.add_light(self.width/2, self.height/2, intensity=100.0, radius=40.0)
            
        elif config == 'two_lights':
            # 双光源环境
            self.add_light(self.width/3, self.height/2, intensity=80.0, radius=30.0)
            self.add_light(2*self.width/3, self.height/2, intensity=80.0, radius=30.0)
            
        elif config == 'obstacle_course':
            # 障碍物课程
            self.add_light(self.width/2, self.height/2, intensity=150.0, radius=50.0)
            # 添加环形障碍物
            for angle in np.linspace(0, 2*np.pi, 8, endpoint=False):
                ox = self.width/2 + 25 * np.cos(angle)
                oy = self.height/2 + 25 * np.sin(angle)
                self.add_obstacle(ox, oy, radius=3.0)
                
        elif config == 'maze':
            # 简单迷宫
            self.add_light(self.width - 10, self.height - 10, intensity=100.0, radius=30.0)
            # 墙壁
            for i in range(0, self.width, 10):
                if i < self.width/2 - 10 or i > self.width/2 + 10:
                    self.add_obstacle(i, self.height/2, radius=2.0)
            for j in range(0, self.height, 10):
                if j < self.height/2 - 10 or j > self.height/2 + 10:
                    self.add_obstacle(self.width/2, j, radius=2.0)
                    
        elif config == 'gradient':
            # 梯度亮度环境（用于测试趋光/避光）
            for i in range(5):
                x = (i + 0.5) * self.width / 5
                intensity = 20 + i * 20
                self.add_light(x, self.height/2, intensity=intensity, radius=25.0)
    
    def get_environment_state(self, x: float, y: float, heading: float) -> Dict:
        """
        获取环境状态（用于可视化）
        """
        return {
            'brightness': self.get_total_brightness(x, y),
            'brightness_gradient': self.get_brightness_gradient(x, y),
            'front_distance': self.get_distance_to_obstacle(x, y, heading),
            'back_distance': self.get_distance_to_obstacle(x, y, heading + np.pi),
        }
    
    def get_sensor_readings(self, x: float, y: float, heading: float) -> np.ndarray:
        """
        获取完整的传感器读数
        用于反射虫的感觉输入
        """
        # 计算传感器位置（相对于heading）
        left_angle = heading + np.pi/4  # 左前方45度
        right_angle = heading - np.pi/4  # 右前方45度
        
        # 光感受器
        left_sensor_x = x + 0.5 * np.cos(left_angle)
        left_sensor_y = y + 0.5 * np.sin(left_angle)
        right_sensor_x = x + 0.5 * np.cos(right_angle)
        right_sensor_y = y + 0.5 * np.sin(right_angle)
        
        left_brightness = self.get_total_brightness(left_sensor_x, left_sensor_y)
        right_brightness = self.get_total_brightness(right_sensor_x, right_sensor_y)
        
        # 触觉传感器
        front_distance = self.get_distance_to_obstacle(x, y, heading)
        back_distance = self.get_distance_to_obstacle(x, y, heading + np.pi)
        
        # 亮度梯度
        grad_x, grad_y = self.get_brightness_gradient(x, y)
        
        return np.array([
            left_brightness / 100.0,   # 归一化
            right_brightness / 100.0,
            front_distance / 20.0,      # 归一化到0-1
            back_distance / 20.0,
            grad_x / 10.0,              # 归一化
            grad_y / 10.0,
        ], dtype=np.float32)


# 测试代码
if __name__ == "__main__":
    env = Environment2D(100, 100)
    env.create_default_environment('simple')
    
    print("环境测试:")
    print(f"中心亮度: {env.get_total_brightness(50, 50):.2f}")
    print(f"角落亮度: {env.get_total_brightness(10, 10):.2f}")
    
    gradient = env.get_brightness_gradient(50, 50)
    print(f"中心梯度: {gradient}")
    
    sensors = env.get_sensor_readings(50, 50, 0)
    print(f"传感器读数: {sensors}")
