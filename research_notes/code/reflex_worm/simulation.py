"""
微型TNN"反射虫" - 主仿真脚本
运行实验验证"结构即行为"假说
"""

import numpy as np
import torch
import json
import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import matplotlib.pyplot as plt

try:
    from .environment import Environment2D
    from .tnn_worm import TNNWorm
    from .behaviors import (
        create_worm_by_behavior, 
        get_behavior_info, 
        compare_torsion_fields,
        BEHAVIOR_PRESETS
    )
except ImportError:
    from environment import Environment2D
    from tnn_worm import TNNWorm
    from behaviors import (
        create_worm_by_behavior, 
        get_behavior_info, 
        compare_torsion_fields,
        BEHAVIOR_PRESETS
    )


class ExperimentConfig:
    """实验配置"""
    def __init__(
        self,
        environment_type: str = 'simple',
        environment_size: Tuple[int, int] = (100, 100),
        simulation_steps: int = 500,
        dt: float = 0.1,
        num_trials: int = 10,
        random_seed: int = 42
    ):
        self.environment_type = environment_type
        self.environment_size = environment_size
        self.simulation_steps = simulation_steps
        self.dt = dt
        self.num_trials = num_trials
        self.random_seed = random_seed


class ReflexWormExperiment:
    """
    TNN反射虫实验
    
    验证:
    1. 零训练：所有行为 purely from structure
    2. 结构-行为映射：改变扭转场 → 观察行为变化
    3. 鲁棒性测试：环境扰动下的行为稳定性
    4. 谱维演化：观察不同刺激下的谱维变化
    """
    
    def __init__(self, config: ExperimentConfig, output_dir: str = './results'):
        self.config = config
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 设置随机种子
        np.random.seed(config.random_seed)
        torch.manual_seed(config.random_seed)
        
        # 设备
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"使用设备: {self.device}")
        
        # 结果存储
        self.results = {}
        
    def run_single_simulation(
        self,
        behavior_type: str,
        trial: int = 0,
        initial_position: Optional[Tuple[float, float]] = None,
        initial_heading: Optional[float] = None
    ) -> Dict:
        """
        运行单次仿真实验
        
        Returns:
            包含轨迹、传感器历史、运动历史的字典
        """
        # 创建环境
        env = Environment2D(
            width=self.config.environment_size[0],
            height=self.config.environment_size[1]
        )
        env.create_default_environment(self.config.environment_type)
        
        # 初始位置
        if initial_position is None:
            # 随机位置，但不要太靠近边界
            margin = 10
            x = np.random.uniform(margin, env.width - margin)
            y = np.random.uniform(margin, env.height - margin)
        else:
            x, y = initial_position
            
        if initial_heading is None:
            heading = np.random.uniform(0, 2 * np.pi)
        else:
            heading = initial_heading
        
        # 创建虫子
        worm = create_worm_by_behavior(behavior_type, x, y, heading, self.device)
        
        # 运行仿真
        for step in range(self.config.simulation_steps):
            worm.update(env, self.config.dt)
            
            # 检查能量耗尽
            if worm.energy <= 0:
                break
        
        # 收集结果
        return {
            'behavior_type': behavior_type,
            'trial': trial,
            'trajectory': np.array(worm.trajectory),
            'sensor_history': np.array(worm.sensor_history),
            'motor_history': worm.motor_history,
            'spectral_history': worm.spectral_history,
            'final_position': (worm.x, worm.y),
            'final_energy': worm.energy,
            'total_steps': len(worm.trajectory),
            'worm_params': worm.brain.get_architecture_info()
        }
    
    def run_behavior_experiment(self, behavior_type: str) -> Dict:
        """
        运行单个行为类型的多试验实验
        """
        print(f"\n运行 {behavior_type} 实验...")
        
        trials = []
        for i in range(self.config.num_trials):
            result = self.run_single_simulation(behavior_type, trial=i)
            trials.append(result)
            print(f"  试验 {i+1}/{self.config.num_trials} 完成，步数: {result['total_steps']}")
        
        # 分析结果
        analysis = self._analyze_trials(trials)
        
        return {
            'behavior_type': behavior_type,
            'trials': trials,
            'analysis': analysis,
            'behavior_info': get_behavior_info()[behavior_type]
        }
    
    def _analyze_trials(self, trials: List[Dict]) -> Dict:
        """分析多次试验的结果"""
        trajectories = [t['trajectory'] for t in trials]
        
        # 计算平均路径长度
        path_lengths = []
        for traj in trajectories:
            if len(traj) > 1:
                diffs = np.diff(traj, axis=0)
                length = np.sum(np.sqrt(np.sum(diffs**2, axis=1)))
                path_lengths.append(length)
        
        # 计算终点分布
        final_positions = np.array([t['final_position'] for t in trials])
        
        # 谱维统计
        spectral_histories = [t['spectral_history'] for t in trials]
        avg_spectral_dims = [np.mean(h) if h else 4.0 for h in spectral_histories]
        
        return {
            'mean_path_length': float(np.mean(path_lengths)) if path_lengths else 0,
            'std_path_length': float(np.std(path_lengths)) if path_lengths else 0,
            'final_position_mean': final_positions.mean(axis=0).tolist(),
            'final_position_std': final_positions.std(axis=0).tolist(),
            'mean_spectral_dim': float(np.mean(avg_spectral_dims)),
            'std_spectral_dim': float(np.std(avg_spectral_dims)),
            'mean_energy': float(np.mean([t['final_energy'] for t in trials]))
        }
    
    def run_all_experiments(self) -> Dict:
        """运行所有行为类型的实验"""
        print("=" * 60)
        print("TNN反射虫实验 - 验证'结构即行为'假说")
        print("=" * 60)
        print(f"配置: {self.config.environment_size[0]}x{self.config.environment_size[1]} 环境")
        print(f"      {self.config.simulation_steps} 步/试验, {self.config.num_trials} 次试验/行为")
        
        behavior_types = list(BEHAVIOR_PRESETS.keys())
        
        for behavior_type in behavior_types:
            result = self.run_behavior_experiment(behavior_type)
            self.results[behavior_type] = result
        
        # 跨行为比较
        print("\n进行跨行为比较...")
        self.cross_behavior_analysis()
        
        return self.results
    
    def cross_behavior_analysis(self):
        """比较不同行为模式的差异"""
        print("\n" + "=" * 60)
        print("跨行为比较分析")
        print("=" * 60)
        
        for behavior_type, result in self.results.items():
            analysis = result['analysis']
            print(f"\n{behavior_type}:")
            print(f"  平均路径长度: {analysis['mean_path_length']:.2f} ± {analysis['std_path_length']:.2f}")
            print(f"  平均谱维: {analysis['mean_spectral_dim']:.3f} ± {analysis['std_spectral_dim']:.3f}")
            print(f"  终点位置: ({analysis['final_position_mean'][0]:.1f}, {analysis['final_position_mean'][1]:.1f})")
    
    def run_robustness_test(self) -> Dict:
        """
        鲁棒性测试：在不同环境配置下测试行为稳定性
        """
        print("\n" + "=" * 60)
        print("鲁棒性测试")
        print("=" * 60)
        
        robustness_results = {}
        behavior_type = 'phototaxis'  # 以趋光虫为例
        
        environment_configs = [
            ('simple', '简单环境'),
            ('two_lights', '双光源'),
            ('obstacle_course', '障碍物'),
            ('gradient', '梯度亮度')
        ]
        
        for env_type, env_desc in environment_configs:
            print(f"\n  测试环境: {env_desc}")
            
            # 临时更改环境配置
            original_env_type = self.config.environment_type
            self.config.environment_type = env_type
            
            # 运行少量试验
            original_num_trials = self.config.num_trials
            self.config.num_trials = 3
            
            result = self.run_behavior_experiment(behavior_type)
            robustness_results[env_type] = result
            
            # 恢复配置
            self.config.environment_type = original_env_type
            self.config.num_trials = original_num_trials
        
        return robustness_results
    
    def save_results(self, filename: str = 'experiment_results.json'):
        """保存实验结果到JSON"""
        filepath = os.path.join(self.output_dir, filename)
        
        # 转换numpy数组为列表以便JSON序列化
        serializable_results = {}
        for behavior, result in self.results.items():
            serializable_results[behavior] = {
                'behavior_info': result['behavior_info'],
                'analysis': result['analysis'],
                'trial_summaries': [
                    {
                        'trial': t['trial'],
                        'total_steps': t['total_steps'],
                        'final_position': t['final_position'],
                        'final_energy': t['final_energy'],
                        'path_length': float(np.sum(np.sqrt(np.sum(np.diff(np.array(t['trajectory']), axis=0)**2, axis=1))))
                    }
                    for t in result['trials']
                ]
            }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n结果已保存到: {filepath}")


def run_quick_demo():
    """快速演示"""
    print("=" * 60)
    print("TNN反射虫快速演示")
    print("=" * 60)
    
    # 简单配置
    config = ExperimentConfig(
        environment_type='simple',
        environment_size=(100, 100),
        simulation_steps=200,
        num_trials=1
    )
    
    experiment = ReflexWormExperiment(config, output_dir='./demo_results')
    
    # 运行几个行为的演示
    demo_behaviors = ['phototaxis', 'photophobia', 'exploration']
    
    for behavior in demo_behaviors:
        print(f"\n运行 {behavior} 演示...")
        result = experiment.run_single_simulation(behavior)
        
        trajectory = result['trajectory']
        print(f"  初始位置: ({trajectory[0][0]:.1f}, {trajectory[0][1]:.1f})")
        print(f"  终点位置: ({trajectory[-1][0]:.1f}, {trajectory[-1][1]:.1f})")
        print(f"  路径长度: {len(trajectory)} 步")
        print(f"  谱维范围: {min(result['spectral_history']):.2f} - {max(result['spectral_history']):.2f}")
    
    print("\n演示完成!")
    return experiment


def run_full_experiment():
    """运行完整实验"""
    config = ExperimentConfig(
        environment_type='simple',
        environment_size=(100, 100),
        simulation_steps=500,
        num_trials=10,
        random_seed=42
    )
    
    experiment = ReflexWormExperiment(config, output_dir='./experiment_results')
    
    # 运行所有实验
    results = experiment.run_all_experiments()
    
    # 鲁棒性测试
    robustness = experiment.run_robustness_test()
    
    # 保存结果
    experiment.save_results()
    
    print("\n" + "=" * 60)
    print("实验完成！")
    print("=" * 60)
    
    return experiment, results


# 主函数
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        # 快速演示模式
        experiment = run_quick_demo()
    else:
        # 完整实验模式
        experiment, results = run_full_experiment()
