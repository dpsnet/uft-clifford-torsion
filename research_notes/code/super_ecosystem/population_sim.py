"""
群体仿真实验
支持多虫子互动、繁殖、死亡等群体动态

核心功能:
- 多虫子并行仿真（向量化）
- 繁殖机制（能量达标可分裂）
- 死亡机制（能量耗尽）
- 社交互动（信息素通信）
- 行为统计和记录
"""

import numpy as np
import torch
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import time
from tqdm import tqdm

from ecosystem_env import SuperEcosystem
from super_tnn_worm import SuperTNNCore, WormState, WormMemory


@dataclass
class WormConfig:
    """虫子配置"""
    # 物理参数
    max_speed: float = 5.0
    max_turn_rate: float = np.pi / 3
    energy_consumption_rate: float = 0.05
    metabolism_base: float = 0.02
    
    # 能量参数
    initial_energy: float = 100.0
    max_energy: float = 150.0
    reproduction_threshold: float = 120.0
    reproduction_cost: float = 60.0
    starvation_threshold: float = 0.0
    
    # 健康参数
    max_health: float = 100.0
    healing_rate: float = 0.1
    damage_sensitivity: float = 1.0
    
    # 感知参数
    vision_range: float = 100.0
    chemical_range: float = 80.0
    social_range: float = 50.0
    
    # 行为参数
    exploration_prob: float = 0.1
    mating_cooldown: float = 500.0  # 交配冷却时间


class SuperWormAgent:
    """
    超级虫子智能体
    包含TNN大脑、物理状态、内部状态
    """
    
    _id_counter = 0
    
    def __init__(
        self,
        x: float,
        y: float,
        heading: float = 0.0,
        config: Optional[WormConfig] = None,
        parent_id: Optional[int] = None,
        brain: Optional[SuperTNNCore] = None,
        device: str = 'cpu'
    ):
        # 分配ID
        self.id = SuperWormAgent._id_counter
        SuperWormAgent._id_counter += 1
        self.parent_id = parent_id
        
        self.config = config or WormConfig()
        self.device = device
        
        # 物理状态
        self.x = x
        self.y = y
        self.heading = heading
        self.vx = 0.0
        self.vy = 0.0
        
        # TNN大脑
        self.brain = brain or SuperTNNCore(device=device)
        self.brain.eval()  # 设置为评估模式
        
        # 内部状态
        self.state = WormState(
            energy=self.config.initial_energy,
            health=self.config.max_health,
            age=0.0,
            reproduction_drive=0.0
        )
        
        # 记忆
        self.memory = WormMemory()
        self.memory.home_location = (x, y)
        
        # 轨迹和行为记录
        self.trajectory: List[Tuple[float, float]] = [(x, y)]
        self.behavior_history: List[str] = []
        self.energy_history: List[float] = [self.config.initial_energy]
        self.health_history: List[float] = [self.config.max_health]
        self.spectral_history: List[float] = []
        self.children_ids: List[int] = []
        
        # 当前行为
        self.current_behavior = 'explore'
        self.behavior_duration = 0
        self.mating_cooldown_timer = 0.0
        
        # 统计
        self.food_consumed = 0.0
        self.distance_traveled = 0.0
        self.interactions = 0
        self.pheromones_released = 0
        
        # 存活状态
        self.is_alive = True
        self.death_cause: Optional[str] = None
    
    def sense(self, env: SuperEcosystem, other_worms: List['SuperWormAgent']) -> np.ndarray:
        """感知环境"""
        # 构建其他虫子的位置列表
        other_positions = [
            (w.id, w.x, w.y) for w in other_worms 
            if w.id != self.id and w.is_alive
        ]
        
        # 从环境获取传感器读数
        readings = env.get_sensor_readings(self.x, self.y, self.heading, other_positions)
        
        # 填充内部状态传感器[24:28]
        readings[24] = self.state.energy / self.config.max_energy
        readings[25] = self.state.health / self.config.max_health
        readings[26] = min(self.state.age / 5000.0, 1.0)  # 归一化年龄
        readings[27] = self.state.reproduction_drive
        
        return readings
    
    def think(
        self,
        sensor_readings: np.ndarray,
        context_factor: float = 1.0
    ) -> Tuple[torch.Tensor, Dict]:
        """思考决策"""
        # 转换为tensor
        x = torch.tensor(
            sensor_readings, 
            dtype=torch.float32, 
            device=self.device
        ).unsqueeze(0)
        
        # TNN前向传播
        with torch.no_grad():
            output = self.brain(x, context_factor)
            interpretation = self.brain.get_output_interpretation(output)
        
        return output, interpretation
    
    def decide_behavior(self, interpretation: Dict) -> str:
        """根据网络输出决定行为"""
        behavior_probs = interpretation['behavior_probs'][0].cpu().numpy()
        
        behaviors = ['forage', 'flee', 'mate', 'rest', 'explore', 'attack', 'communicate']
        
        # 基于概率选择行为
        # 考虑当前状态约束
        valid_behaviors = behaviors.copy()
        
        # 能量低时不能交配
        if self.state.energy < self.config.reproduction_threshold * 0.5:
            if 'mate' in valid_behaviors:
                idx = valid_behaviors.index('mate')
                behavior_probs[idx] = 0
        
        # 健康低时倾向于休息
        if self.state.health < 30:
            idx = valid_behaviors.index('rest')
            behavior_probs[idx] *= 2.0
        
        # 交配冷却中
        if self.mating_cooldown_timer > 0:
            if 'mate' in valid_behaviors:
                idx = valid_behaviors.index('mate')
                behavior_probs[idx] = 0
        
        # 归一化概率
        if behavior_probs.sum() > 0:
            behavior_probs = behavior_probs / behavior_probs.sum()
        else:
            behavior_probs = np.ones(len(behaviors)) / len(behaviors)
        
        # 选择行为
        behavior = np.random.choice(valid_behaviors, p=behavior_probs[:len(valid_behaviors)])
        
        return behavior
    
    def act(
        self,
        output: torch.Tensor,
        interpretation: Dict,
        env: SuperEcosystem,
        dt: float = 1.0
    ):
        """执行动作"""
        motor_control = interpretation['motor_control'][0].cpu().numpy()
        
        # 运动控制解码（8维 -> 速度和转向）
        # [0:4] 控制转向，[4:8] 控制速度
        turn_signal = motor_control[1] - motor_control[0] + motor_control[3] - motor_control[2]
        speed_signal = motor_control[5] - motor_control[4] + motor_control[7] - motor_control[6]
        
        # 应用sigmoid获取最终控制信号
        turn = np.tanh(turn_signal)
        speed = np.tanh(speed_signal)
        
        # 根据行为调整运动
        if self.current_behavior == 'rest':
            speed *= 0.1
        elif self.current_behavior == 'flee':
            speed *= 1.5
            # 紧急情况下降低谱维以加速决策
            context_factor = 0.7
        elif self.current_behavior == 'explore':
            turn += np.random.normal(0, 0.3)  # 添加随机性
        
        # 更新朝向
        self.heading += turn * self.config.max_turn_rate * dt
        self.heading = self.heading % (2 * np.pi)
        
        # 更新速度
        target_vx = speed * self.config.max_speed * np.cos(self.heading)
        target_vy = speed * self.config.max_speed * np.sin(self.heading)
        
        # 平滑速度变化
        self.vx = 0.8 * self.vx + 0.2 * target_vx
        self.vy = 0.8 * self.vy + 0.2 * target_vy
        
        # 应用物理
        old_x, old_y = self.x, self.y
        self.x, self.y, self.vx, self.vy = env.apply_physics(
            self.x, self.y, self.vx, self.vy, dt
        )
        
        # 记录移动距离
        self.distance_traveled += np.sqrt((self.x - old_x)**2 + (self.y - old_y)**2)
        
        # 能量消耗
        speed_mag = np.sqrt(self.vx**2 + self.vy**2)
        energy_cost = self.config.metabolism_base + speed_mag * self.config.energy_consumption_rate * dt
        self.state.energy -= energy_cost
        
        # 内部调节
        internal_reg = interpretation['internal_reg'][0].cpu().numpy()
        
        # 新陈代谢调节
        if internal_reg[0] > 0.5:
            self.state.metabolism_rate = 1.0 + 0.5 * (internal_reg[0] - 0.5)
        
        # 修复
        if internal_reg[1] > 0.5 and self.state.energy > 20:
            heal_amount = internal_reg[1] * self.config.healing_rate * dt
            self.state.health = min(self.state.health + heal_amount, self.config.max_health)
            self.state.energy -= heal_amount * 0.5  # 修复消耗能量
        
        # 释放信息素
        if internal_reg[3] > 0.7:
            self._release_pheromone(env, interpretation)
    
    def _release_pheromone(self, env: SuperEcosystem, interpretation: Dict):
        """释放信息素"""
        memory_out = interpretation['memory_out'][0].cpu().numpy()
        
        # 根据输出决定信息素类型和强度
        phero_type_idx = int(np.argmax(memory_out[:4]))
        phero_types = ['food', 'danger', 'trail', 'mate']
        phero_type = phero_types[phero_type_idx]
        
        intensity = np.tanh(memory_out[4]) * 10.0 + 5.0
        
        env.add_pheromone(
            self.x, self.y, phero_type, intensity, self.id
        )
        self.pheromones_released += 1
    
    def interact(
        self,
        env: SuperEcosystem,
        other_worms: List['SuperWormAgent']
    ):
        """与环境和其他虫子互动"""
        # 检查危险
        is_danger, danger_level = env.check_danger(self.x, self.y)
        if is_danger:
            self.state.health -= danger_level * self.config.damage_sensitivity
            self.state.stress_level = 1.0
            # 添加危险记忆
            self.memory.add_danger_memory(self.x, self.y, danger_level)
        else:
            self.state.stress_level *= 0.95  # 压力衰减
        
        # 消耗食物
        food_consumed = env.consume_food(self.x, self.y, 5.0)
        if food_consumed > 0:
            self.state.energy = min(
                self.state.energy + food_consumed,
                self.config.max_energy
            )
            self.food_consumed += food_consumed
            self.memory.add_food_memory(self.x, self.y, food_consumed)
        
        # 检查水源
        for water in env.waters:
            if water.is_inside(self.x, self.y):
                self.state.health = min(
                    self.state.health + 0.5 * water.purity,
                    self.config.max_health
                )
        
        # 与其他虫子互动
        for other in other_worms:
            if other.id == self.id or not other.is_alive:
                continue
            
            dist = np.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
            
            if dist < 10.0:  # 近距离接触
                self.interactions += 1
                
                # 更新社交记忆
                if other.id not in self.state.known_worms:
                    self.state.known_worms[other.id] = 0.0
                self.state.known_worms[other.id] += 0.01
                
                # 如果是同类且双方都想交配
                if (self.current_behavior == 'mate' and 
                    other.current_behavior == 'mate' and
                    self.mating_cooldown_timer <= 0 and
                    other.mating_cooldown_timer <= 0):
                    self.state.reproduction_drive += 0.1
                    other.state.reproduction_drive += 0.1
        
        # 更新繁殖欲望
        if self.state.energy > self.config.reproduction_threshold * 0.8:
            self.state.reproduction_drive = min(
                self.state.reproduction_drive + 0.001,
                1.0
            )
        
        # 减少交配冷却
        if self.mating_cooldown_timer > 0:
            self.mating_cooldown_timer -= 1
    
    def can_reproduce(self) -> bool:
        """检查是否可以繁殖"""
        return (
            self.state.energy > self.config.reproduction_threshold and
            self.state.health > 50 and
            self.mating_cooldown_timer <= 0 and
            self.state.age > 100  # 最小繁殖年龄
        )
    
    def reproduce(self) -> Optional['SuperWormAgent']:
        """繁殖产生后代"""
        if not self.can_reproduce():
            return None
        
        # 消耗能量
        self.state.energy -= self.config.reproduction_cost
        self.mating_cooldown_timer = self.config.mating_cooldown
        
        # 后代位置（附近）
        offset_x = np.random.normal(0, 10)
        offset_y = np.random.normal(0, 10)
        child_x = np.clip(self.x + offset_x, 0, 1000)
        child_y = np.clip(self.y + offset_y, 0, 1000)
        
        # 创建后代（继承大脑结构但略有变异）
        child_brain = SuperTNNCore(device=self.device)
        # 复制父代权重并添加小变异
        with torch.no_grad():
            for param, parent_param in zip(child_brain.parameters(), self.brain.parameters()):
                param.data = parent_param.data + torch.randn_like(param) * 0.01
        
        child = SuperWormAgent(
            x=child_x,
            y=child_y,
            heading=np.random.uniform(0, 2*np.pi),
            config=self.config,
            parent_id=self.id,
            brain=child_brain,
            device=self.device
        )
        
        self.children_ids.append(child.id)
        self.state.reproduction_drive = 0.0
        
        return child
    
    def check_death(self) -> bool:
        """检查是否死亡"""
        if self.state.energy <= self.config.starvation_threshold:
            self.is_alive = False
            self.death_cause = 'starvation'
            return True
        
        if self.state.health <= 0:
            self.is_alive = False
            self.death_cause = 'injury'
            return True
        
        # 老化死亡（可选）
        if self.state.age > 10000 and np.random.random() < 0.0001:
            self.is_alive = False
            self.death_cause = 'old_age'
            return True
        
        return False
    
    def update(self, env: SuperEcosystem, other_worms: List['SuperWormAgent'], dt: float = 1.0):
        """完整更新周期"""
        if not self.is_alive:
            return
        
        # 感知
        sensor_readings = self.sense(env, other_worms)
        
        # 上下文因子（根据压力调整）
        context_factor = 1.0 - 0.3 * self.state.stress_level
        
        # 思考
        output, interpretation = self.think(sensor_readings, context_factor)
        
        # 决定行为
        if self.behavior_duration <= 0 or np.random.random() < 0.1:
            self.current_behavior = self.decide_behavior(interpretation)
            self.behavior_duration = np.random.randint(10, 50)
        else:
            self.behavior_duration -= 1
        
        # 行动
        self.act(output, interpretation, env, dt)
        
        # 互动
        self.interact(env, other_worms)
        
        # 更新年龄
        self.state.age += dt
        
        # 记录历史
        self.trajectory.append((self.x, self.y))
        self.behavior_history.append(self.current_behavior)
        self.energy_history.append(self.state.energy)
        self.health_history.append(self.state.health)
        self.spectral_history.append(self.brain.spectral_manager.current_d_s)
        
        # 更新记忆
        self.memory.update_position_history(self.x, self.y)
        
        # 检查死亡
        self.check_death()
    
    def get_state_dict(self) -> Dict:
        """获取状态字典"""
        return {
            'id': self.id,
            'parent_id': self.parent_id,
            'x': self.x,
            'y': self.y,
            'heading': self.heading,
            'vx': self.vx,
            'vy': self.vy,
            'energy': self.state.energy,
            'health': self.state.health,
            'age': self.state.age,
            'reproduction_drive': self.state.reproduction_drive,
            'current_behavior': self.current_behavior,
            'is_alive': self.is_alive,
            'food_consumed': self.food_consumed,
            'distance_traveled': self.distance_traveled,
            'interactions': self.interactions,
            'children_count': len(self.children_ids)
        }


class PopulationSimulation:
    """
    群体仿真实验
    管理多个虫子和环境交互
    """
    
    def __init__(
        self,
        n_initial_worms: int = 10,
        env_width: float = 1000.0,
        env_height: float = 1000.0,
        max_population: int = 100,
        device: str = 'cpu',
        seed: int = 42
    ):
        self.n_initial = n_initial_worms
        self.max_population = max_population
        self.device = device
        self.seed = seed
        
        np.random.seed(seed)
        torch.manual_seed(seed)
        
        # 创建环境
        self.env = SuperEcosystem(width=env_width, height=env_height)
        self.env.create_random_environment()
        
        # 初始化虫子群体
        self.worms: List[SuperWormAgent] = []
        self.dead_worms: List[SuperWormAgent] = []
        self._initialize_population()
        
        # 统计记录
        self.population_history: List[int] = [len(self.worms)]
        self.birth_count = 0
        self.death_count = 0
        self.step_count = 0
        self.start_time = time.time()
        
    def _initialize_population(self):
        """初始化虫子群体"""
        for i in range(self.n_initial):
            x = np.random.uniform(100, self.env.width - 100)
            y = np.random.uniform(100, self.env.height - 100)
            heading = np.random.uniform(0, 2 * np.pi)
            
            worm = SuperWormAgent(x, y, heading, device=self.device)
            self.worms.append(worm)
    
    def step(self, dt: float = 1.0) -> Dict:
        """仿真步进"""
        self.step_count += 1
        
        # 更新环境
        self.env.step(dt)
        
        # 获取当前存活虫子列表
        alive_worms = [w for w in self.worms if w.is_alive]
        
        # 并行更新所有虫子
        for worm in alive_worms:
            worm.update(self.env, alive_worms, dt)
        
        # 处理繁殖
        new_worms = []
        for worm in alive_worms:
            if worm.can_reproduce() and len(alive_worms) + len(new_worms) < self.max_population:
                child = worm.reproduce()
                if child:
                    new_worms.append(child)
                    self.birth_count += 1
        
        self.worms.extend(new_worms)
        
        # 处理死亡
        newly_dead = [w for w in self.worms if not w.is_alive and w not in self.dead_worms]
        self.dead_worms.extend(newly_dead)
        self.death_count += len(newly_dead)
        
        # 记录种群历史
        current_alive = len([w for w in self.worms if w.is_alive])
        self.population_history.append(current_alive)
        
        return self.get_statistics()
    
    def run(
        self,
        n_steps: int = 1000,
        dt: float = 1.0,
        verbose: bool = True
    ) -> Dict:
        """
        运行完整仿真
        
        Returns:
            仿真结果字典
        """
        if verbose:
            pbar = tqdm(total=n_steps, desc="Simulation")
        
        for step in range(n_steps):
            stats = self.step(dt)
            
            if verbose and step % 100 == 0:
                pbar.set_postfix(stats)
            
            if verbose:
                pbar.update(1)
            
            # 提前终止条件
            alive_count = len([w for w in self.worms if w.is_alive])
            if alive_count == 0:
                if verbose:
                    print(f"\n所有虫子在步骤 {step} 死亡，仿真终止")
                break
        
        if verbose:
            pbar.close()
        
        return self.get_results()
    
    def get_statistics(self) -> Dict:
        """获取当前统计"""
        alive_worms = [w for w in self.worms if w.is_alive]
        
        if not alive_worms:
            return {
                'population': 0,
                'step': self.step_count,
                'avg_energy': 0,
                'avg_health': 0,
                'avg_age': 0
            }
        
        return {
            'population': len(alive_worms),
            'step': self.step_count,
            'avg_energy': np.mean([w.state.energy for w in alive_worms]),
            'avg_health': np.mean([w.state.health for w in alive_worms]),
            'avg_age': np.mean([w.state.age for w in alive_worms]),
            'births': self.birth_count,
            'deaths': self.death_count
        }
    
    def get_results(self) -> Dict:
        """获取完整结果"""
        elapsed = time.time() - self.start_time
        alive_worms = [w for w in self.worms if w.is_alive]
        
        return {
            'n_steps': self.step_count,
            'elapsed_time': elapsed,
            'final_population': len(alive_worms),
            'total_births': self.birth_count,
            'total_deaths': self.death_count,
            'population_history': self.population_history,
            'worms': self.worms,
            'dead_worms': self.dead_worms,
            'environment': self.env,
            'statistics': self.get_statistics()
        }


# 测试代码
if __name__ == "__main__":
    print("=" * 70)
    print("群体仿真实验测试")
    print("=" * 70)
    
    # 创建仿真
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\n使用设备: {device}")
    
    sim = PopulationSimulation(
        n_initial_worms=5,
        max_population=20,
        device=device,
        seed=42
    )
    
    print(f"\n初始虫子数量: {len(sim.worms)}")
    print(f"环境大小: {sim.env.width} x {sim.env.height}")
    
    # 运行短仿真测试
    print("\n运行100步测试仿真...")
    results = sim.run(n_steps=100, verbose=True)
    
    print("\n" + "=" * 70)
    print("仿真结果:")
    print(f"  最终种群: {results['final_population']}")
    print(f"  总出生数: {results['total_births']}")
    print(f"  总死亡数: {results['total_deaths']}")
    print(f"  耗时: {results['elapsed_time']:.2f}秒")
    
    # 检查虫子状态
    if results['worms']:
        sample_worm = results['worms'][0]
        print(f"\n样本虫子 (ID: {sample_worm.id}):")
        print(f"  能量: {sample_worm.state.energy:.2f}")
        print(f"  健康: {sample_worm.state.health:.2f}")
        print(f"  年龄: {sample_worm.state.age:.2f}")
        print(f"  轨迹长度: {len(sample_worm.trajectory)}")
    
    print("\n" + "=" * 70)
    print("测试完成!")
