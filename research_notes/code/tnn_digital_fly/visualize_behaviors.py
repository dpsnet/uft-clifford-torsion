"""
行为可视化工具
可视化果蝇行为、步态分析、与真实果蝇对比
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation
from typing import List, Dict, Tuple, Optional
import json


class BehaviorVisualizer:
    """
    行为可视化器
    """
    
    def __init__(self, figsize: Tuple[int, int] = (14, 10)):
        self.figsize = figsize
        self.trajectory_data = []
        self.gait_data = []
        self.behavior_data = []
        self.neural_data = []
    
    def add_timestep(
        self,
        position: np.ndarray,
        behavior: str,
        leg_states: Dict,
        neural_activity: Optional[Dict] = None
    ):
        """添加时间步数据"""
        self.trajectory_data.append(position.copy())
        self.behavior_data.append(behavior)
        self.gait_data.append(leg_states)
        if neural_activity:
            self.neural_data.append(neural_activity)
    
    def plot_trajectory(
        self,
        title: str = "Movement Trajectory",
        color_by_behavior: bool = True,
        save_path: Optional[str] = None
    ):
        """绘制运动轨迹"""
        fig, ax = plt.subplots(figsize=(10, 10))
        
        trajectory = np.array(self.trajectory_data)
        
        if len(trajectory) < 2:
            print("轨迹数据不足")
            return
        
        if color_by_behavior:
            # 按行为着色
            behavior_colors = {
                'idle': 'gray',
                'walking': 'blue',
                'foraging': 'green',
                'grooming': 'orange',
                'escaping': 'red',
                'feeding': 'purple',
                'resting': 'cyan'
            }
            
            for i in range(len(trajectory) - 1):
                behavior = self.behavior_data[i]
                color = behavior_colors.get(behavior, 'black')
                ax.plot(
                    trajectory[i:i+2, 0],
                    trajectory[i:i+2, 1],
                    color=color,
                    linewidth=2,
                    alpha=0.7
                )
            
            # 添加图例
            for behavior, color in behavior_colors.items():
                if behavior in self.behavior_data:
                    ax.plot([], [], color=color, label=behavior, linewidth=2)
            ax.legend(loc='upper right')
        else:
            ax.plot(trajectory[:, 0], trajectory[:, 1], 'b-', linewidth=2)
        
        # 标记起点和终点
        ax.plot(trajectory[0, 0], trajectory[0, 1], 'go', markersize=10, label='Start')
        ax.plot(trajectory[-1, 0], trajectory[-1, 1], 'ro', markersize=10, label='End')
        
        ax.set_xlabel('X Position (mm)')
        ax.set_ylabel('Y Position (mm)')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.axis('equal')
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"轨迹图保存到: {save_path}")
        
        plt.close()
    
    def plot_gait_analysis(
        self,
        save_path: Optional[str] = None
    ):
        """绘制步态分析图"""
        if not self.gait_data:
            print("没有步态数据")
            return
        
        fig, axes = plt.subplots(3, 2, figsize=(14, 10))
        axes = axes.flatten()
        
        leg_names = ['Front Left', 'Middle Left', 'Back Left',
                    'Front Right', 'Middle Right', 'Back Right']
        
        time = np.arange(len(self.gait_data))
        
        for i, (ax, leg_name) in enumerate(zip(axes, leg_names)):
            # 提取该腿的支撑/摆动状态
            stance_states = []
            for gait in self.gait_data:
                leg_states = gait.get('leg_states', {})
                stance = leg_states.get(i, {}).get('is_stance', True)
                stance_states.append(1 if stance else 0)
            
            # 绘制步态图
            ax.fill_between(time, 0, stance_states, alpha=0.7, label='Stance')
            ax.fill_between(time, stance_states, 1, alpha=0.7, label='Swing')
            
            ax.set_ylabel('Leg State')
            ax.set_title(leg_name)
            ax.set_ylim(-0.1, 1.1)
            ax.set_yticks([0, 1])
            ax.set_yticklabels(['Swing', 'Stance'])
            
            if i >= 4:
                ax.set_xlabel('Time Step')
        
        plt.suptitle('Gait Analysis - Tripod Coordination', fontsize=14)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"步态分析图保存到: {save_path}")
        
        plt.close()
    
    def plot_behavior_sequence(
        self,
        save_path: Optional[str] = None
    ):
        """绘制行为序列图"""
        fig, ax = plt.subplots(figsize=(14, 4))
        
        behaviors = self.behavior_data
        time = np.arange(len(behaviors))
        
        # 行为编码
        behavior_codes = {
            'idle': 0,
            'walking': 1,
            'foraging': 2,
            'grooming': 3,
            'escaping': 4,
            'feeding': 5,
            'resting': 6
        }
        
        codes = [behavior_codes.get(b, 0) for b in behaviors]
        colors = ['gray', 'blue', 'green', 'orange', 'red', 'purple', 'cyan']
        
        # 绘制行为序列
        for i in range(len(codes) - 1):
            ax.plot([time[i], time[i+1]], [codes[i], codes[i+1]], 
                   color=colors[codes[i]], linewidth=3)
        
        ax.set_yticks(range(7))
        ax.set_yticklabels(['Idle', 'Walking', 'Foraging', 'Grooming', 
                           'Escaping', 'Feeding', 'Resting'])
        ax.set_xlabel('Time Step')
        ax.set_ylabel('Behavior')
        ax.set_title('Behavior Sequence Over Time')
        ax.grid(True, alpha=0.3, axis='x')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"行为序列图保存到: {save_path}")
        
        plt.close()
    
    def plot_neural_activity(
        self,
        save_path: Optional[str] = None
    ):
        """绘制神经活动热图"""
        if not self.neural_data:
            print("没有神经活动数据")
            return
        
        # 提取互反空间和内部空间的活动
        reciprocal_activities = []
        internal_activities = []
        
        for data in self.neural_data:
            if 'reciprocal' in data:
                reciprocal_activities.append(data['reciprocal'])
            if 'internal' in data:
                internal_activities.append(data['internal'])
        
        if not reciprocal_activities:
            return
        
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        # 互反空间活动
        if reciprocal_activities:
            rec_array = np.array(reciprocal_activities)
            im1 = axes[0].imshow(rec_array.T, aspect='auto', cmap='viridis')
            axes[0].set_ylabel('Reciprocal Neuron')
            axes[0].set_title('Reciprocal Space Activity')
            plt.colorbar(im1, ax=axes[0])
        
        # 内部空间活动（降维显示）
        if internal_activities:
            int_array = np.array(internal_activities)
            # 显示前64维
            int_display = int_array[:, :64] if int_array.shape[1] > 64 else int_array
            im2 = axes[1].imshow(int_display.T, aspect='auto', cmap='plasma')
            axes[1].set_xlabel('Time Step')
            axes[1].set_ylabel('Internal Neuron (first 64)')
            axes[1].set_title('Internal Space Activity')
            plt.colorbar(im2, ax=axes[1])
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"神经活动图保存到: {save_path}")
        
        plt.close()
    
    def plot_comparison_with_real_fly(
        self,
        real_fly_data: Dict,
        save_path: Optional[str] = None
    ):
        """
        与真实果蝇数据对比
        
        Args:
            real_fly_data: 真实果蝇行为数据
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 速度对比
        if 'speed' in real_fly_data and len(self.trajectory_data) > 1:
            ax = axes[0, 0]
            
            # 计算仿真果蝇速度
            traj = np.array(self.trajectory_data)
            speeds = np.sqrt(np.sum(np.diff(traj, axis=0)**2, axis=1))
            
            real_speed = real_fly_data['speed']
            
            ax.plot(speeds, label='TNN-Fly', alpha=0.7)
            ax.axhline(y=np.mean(real_speed), color='r', linestyle='--', 
                      label='Real Fly (mean)', linewidth=2)
            ax.fill_between(range(len(speeds)), 
                          np.min(real_speed), np.max(real_speed),
                          alpha=0.2, color='r', label='Real Fly (range)')
            
            ax.set_xlabel('Time Step')
            ax.set_ylabel('Speed (mm/s)')
            ax.set_title('Speed Comparison')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # 转向速率对比
        if 'turning_rate' in real_fly_data and len(self.trajectory_data) > 2:
            ax = axes[0, 1]
            
            traj = np.array(self.trajectory_data)
            headings = np.arctan2(np.diff(traj[:, 1]), np.diff(traj[:, 0]))
            turning_rates = np.diff(headings)
            
            ax.hist(turning_rates, bins=30, alpha=0.5, label='TNN-Fly', density=True)
            ax.hist(real_fly_data['turning_rate'], bins=30, alpha=0.5, 
                   label='Real Fly', density=True)
            
            ax.set_xlabel('Turning Rate (rad/s)')
            ax.set_ylabel('Density')
            ax.set_title('Turning Rate Distribution')
            ax.legend()
        
        # 行为持续时间对比
        if 'behavior_durations' in real_fly_data:
            ax = axes[1, 0]
            
            # 计算仿真果蝇的行为持续时间
            sim_durations = self._calculate_behavior_durations()
            
            behaviors = list(set(self.behavior_data))
            x = np.arange(len(behaviors))
            width = 0.35
            
            sim_values = [sim_durations.get(b, 0) for b in behaviors]
            real_values = [real_fly_data['behavior_durations'].get(b, 0) for b in behaviors]
            
            ax.bar(x - width/2, sim_values, width, label='TNN-Fly')
            ax.bar(x + width/2, real_values, width, label='Real Fly')
            
            ax.set_ylabel('Duration (steps)')
            ax.set_title('Behavior Duration Comparison')
            ax.set_xticks(x)
            ax.set_xticklabels(behaviors, rotation=45)
            ax.legend()
        
        # 活动范围对比
        if len(self.trajectory_data) > 0:
            ax = axes[1, 1]
            
            traj = np.array(self.trajectory_data)
            
            # 活动范围（凸包面积近似）
            x_range = np.max(traj[:, 0]) - np.min(traj[:, 0])
            y_range = np.max(traj[:, 1]) - np.min(traj[:, 1])
            activity_area = x_range * y_range
            
            categories = ['TNN-Fly', 'Real Fly (ref)']
            values = [activity_area, real_fly_data.get('activity_area', 1000)]
            
            ax.bar(categories, values, color=['skyblue', 'salmon'])
            ax.set_ylabel('Activity Area (mm²)')
            ax.set_title('Activity Range Comparison')
        
        plt.suptitle('TNN-Fly vs Real Fruit Fly Comparison', fontsize=14)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"对比图保存到: {save_path}")
        
        plt.close()
    
    def _calculate_behavior_durations(self) -> Dict[str, float]:
        """计算各行为的持续时间"""
        durations = {}
        current_behavior = self.behavior_data[0]
        count = 0
        
        for behavior in self.behavior_data:
            if behavior == current_behavior:
                count += 1
            else:
                if current_behavior not in durations:
                    durations[current_behavior] = []
                durations[current_behavior].append(count)
                current_behavior = behavior
                count = 1
        
        # 计算平均持续时间
        avg_durations = {k: np.mean(v) for k, v in durations.items()}
        return avg_durations
    
    def create_animation(
        self,
        arena_size: Tuple[float, float] = (100, 100),
        save_path: Optional[str] = None,
        fps: int = 30
    ):
        """创建行为动画"""
        if len(self.trajectory_data) < 2:
            print("轨迹数据不足")
            return
        
        fig, ax = plt.subplots(figsize=(10, 10))
        
        trajectory = np.array(self.trajectory_data)
        
        # 设置坐标轴
        ax.set_xlim(0, arena_size[0])
        ax.set_ylim(0, arena_size[1])
        ax.set_xlabel('X Position (mm)')
        ax.set_ylabel('Y Position (mm)')
        ax.set_title('TNN-Fly Behavior Animation')
        ax.grid(True, alpha=0.3)
        
        # 初始化绘图元素
        line, = ax.plot([], [], 'b-', alpha=0.5, linewidth=1)
        point, = ax.plot([], [], 'ro', markersize=8)
        behavior_text = ax.text(0.02, 0.98, '', transform=ax.transAxes, 
                               fontsize=12, verticalalignment='top')
        
        def init():
            line.set_data([], [])
            point.set_data([], [])
            behavior_text.set_text('')
            return line, point, behavior_text
        
        def update(frame):
            # 显示轨迹历史
            start_idx = max(0, frame - 50)  # 显示最近50帧
            line.set_data(trajectory[start_idx:frame+1, 0], 
                         trajectory[start_idx:frame+1, 1])
            
            # 当前位置
            point.set_data([trajectory[frame, 0]], [trajectory[frame, 1]])
            
            # 当前行为
            if frame < len(self.behavior_data):
                behavior_text.set_text(f'Behavior: {self.behavior_data[frame]}')
            
            return line, point, behavior_text
        
        anim = FuncAnimation(fig, update, init_func=init,
                            frames=len(trajectory), interval=1000/fps, 
                            blit=True)
        
        if save_path:
            anim.save(save_path, writer='pillow', fps=fps)
            print(f"动画保存到: {save_path}")
        
        plt.close()
    
    def generate_summary_figure(
        self,
        save_path: Optional[str] = None
    ):
        """生成综合摘要图"""
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. 轨迹图
        ax1 = fig.add_subplot(gs[0, :2])
        if len(self.trajectory_data) > 1:
            trajectory = np.array(self.trajectory_data)
            ax1.plot(trajectory[:, 0], trajectory[:, 1], 'b-', linewidth=2)
            ax1.plot(trajectory[0, 0], trajectory[0, 1], 'go', markersize=8, label='Start')
            ax1.plot(trajectory[-1, 0], trajectory[-1, 1], 'ro', markersize=8, label='End')
            ax1.set_xlabel('X (mm)')
            ax1.set_ylabel('Y (mm)')
            ax1.set_title('Movement Trajectory')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        
        # 2. 行为分布
        ax2 = fig.add_subplot(gs[0, 2])
        if self.behavior_data:
            from collections import Counter
            behavior_counts = Counter(self.behavior_data)
            behaviors = list(behavior_counts.keys())
            counts = list(behavior_counts.values())
            ax2.pie(counts, labels=behaviors, autopct='%1.1f%%')
            ax2.set_title('Behavior Distribution')
        
        # 3. 速度曲线
        ax3 = fig.add_subplot(gs[1, :])
        if len(self.trajectory_data) > 1:
            trajectory = np.array(self.trajectory_data)
            speeds = np.sqrt(np.sum(np.diff(trajectory, axis=0)**2, axis=1))
            ax3.plot(speeds, linewidth=2)
            ax3.set_xlabel('Time Step')
            ax3.set_ylabel('Speed (mm/s)')
            ax3.set_title('Speed Over Time')
            ax3.grid(True, alpha=0.3)
        
        # 4. 步态图（简化）
        ax4 = fig.add_subplot(gs[2, 0])
        if self.gait_data:
            # 计算支撑腿数量
            stance_counts = []
            for gait in self.gait_data:
                leg_states = gait.get('leg_states', {})
                n_stance = sum(1 for ls in leg_states.values() if ls.get('is_stance', True))
                stance_counts.append(n_stance)
            
            ax4.plot(stance_counts, linewidth=2)
            ax4.axhline(y=3, color='r', linestyle='--', label='Ideal tripod')
            ax4.set_xlabel('Time Step')
            ax4.set_ylabel('Stance Legs')
            ax4.set_title('Gait Pattern')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        # 5. 行为转换图
        ax5 = fig.add_subplot(gs[2, 1:])
        if self.behavior_data:
            behaviors = self.behavior_data
            time = np.arange(len(behaviors))
            
            behavior_codes = {'idle': 0, 'walking': 1, 'foraging': 2, 
                            'grooming': 3, 'escaping': 4, 'feeding': 5, 'resting': 6}
            codes = [behavior_codes.get(b, 0) for b in behaviors]
            colors = ['gray', 'blue', 'green', 'orange', 'red', 'purple', 'cyan']
            
            for i in range(len(codes) - 1):
                ax5.plot([time[i], time[i+1]], [codes[i], codes[i+1]], 
                        color=colors[codes[i]], linewidth=3)
            
            ax5.set_yticks(range(7))
            ax5.set_yticklabels(['Idle', 'Walk', 'Forage', 'Groom', 
                               'Escape', 'Feed', 'Rest'])
            ax5.set_xlabel('Time Step')
            ax5.set_title('Behavior Sequence')
            ax5.grid(True, alpha=0.3, axis='x')
        
        plt.suptitle('TNN-Fly Behavior Summary', fontsize=16)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"综合摘要图保存到: {save_path}")
        
        plt.close()
    
    def save_data(self, filepath: str):
        """保存可视化数据"""
        data = {
            'trajectory': [t.tolist() for t in self.trajectory_data],
            'behaviors': self.behavior_data,
            'gait_data': self.gait_data
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f)
        
        print(f"数据保存到: {filepath}")
    
    def clear(self):
        """清除所有数据"""
        self.trajectory_data.clear()
        self.gait_data.clear()
        self.behavior_data.clear()
        self.neural_data.clear()


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("行为可视化工具测试")
    print("=" * 60)
    
    visualizer = BehaviorVisualizer()
    
    # 生成模拟数据
    print("\n生成模拟数据...")
    np.random.seed(42)
    
    behaviors = ['idle', 'walking', 'foraging', 'grooming', 'escaping', 'feeding', 'resting']
    
    position = np.array([50.0, 50.0, 0.0])
    current_behavior = 'idle'
    
    for t in range(200):
        # 随机行为切换
        if np.random.random() < 0.05:
            current_behavior = np.random.choice(behaviors)
        
        # 根据行为移动
        if current_behavior in ['walking', 'foraging']:
            position[:2] += np.random.randn(2) * 0.5
        elif current_behavior == 'escaping':
            position[:2] += np.random.randn(2) * 2.0
        
        # 模拟腿部状态
        leg_states = {
            'leg_states': {
                i: {'is_stance': np.random.random() > 0.5}
                for i in range(6)
            }
        }
        
        visualizer.add_timestep(position.copy(), current_behavior, leg_states)
    
    print(f"生成了 {len(visualizer.trajectory_data)} 个时间步")
    
    # 测试绘图
    print("\n测试绘图...")
    
    # 轨迹图
    visualizer.plot_trajectory(
        title="Test Trajectory",
        save_path="/tmp/test_trajectory.png"
    )
    
    # 步态分析
    visualizer.plot_gait_analysis(save_path="/tmp/test_gait.png")
    
    # 行为序列
    visualizer.plot_behavior_sequence(save_path="/tmp/test_behavior_seq.png")
    
    # 综合摘要
    visualizer.generate_summary_figure(save_path="/tmp/test_summary.png")
    
    print("\n所有图表已保存到 /tmp/")
    print("=" * 60)
    print("测试完成!")
