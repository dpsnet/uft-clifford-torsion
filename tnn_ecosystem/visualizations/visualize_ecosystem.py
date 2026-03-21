"""
生态系统可视化工具
生成群体演化动画、行为统计、涌现指标等可视化
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation, FFMpegWriter
from matplotlib.collections import LineCollection
from typing import List, Dict, Tuple, Optional
import os
from tqdm import tqdm

from population_sim import SuperWormAgent, PopulationSimulation
from ecosystem_env import SuperEcosystem
from emergence_analysis import EmergenceAnalyzer, EmergenceMetrics


class EcosystemVisualizer:
    """生态系统可视化器"""
    
    def __init__(self, simulation: PopulationSimulation, output_dir: str = './visualizations'):
        self.sim = simulation
        self.env = simulation.env
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 颜色映射
        self.behavior_colors = {
            'forage': '#2ecc71',    # 绿色 - 觅食
            'flee': '#e74c3c',      # 红色 - 逃跑
            'mate': '#e91e63',      # 粉色 - 交配
            'rest': '#3498db',      # 蓝色 - 休息
            'explore': '#f39c12',   # 橙色 - 探索
            'attack': '#9b59b6',    # 紫色 - 攻击
            'communicate': '#1abc9c' # 青色 - 交流
        }
        
        self.pheromone_colors = {
            'food': '#2ecc71',
            'danger': '#e74c3c',
            'trail': '#f39c12',
            'mate': '#e91e63'
        }
        
    def plot_ecosystem_state(
        self,
        step: Optional[int] = None,
        show_trajectories: bool = True,
        show_pheromones: bool = True,
        show_food: bool = True,
        ax=None,
        figsize=(12, 12)
    ):
        """绘制生态系统当前状态"""
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.figure
        
        # 设置背景
        ax.set_facecolor('#f8f9fa')
        
        # 绘制边界
        ax.plot([0, self.env.width, self.env.width, 0, 0],
                [0, 0, self.env.height, self.env.height, 0],
                'k-', linewidth=2)
        
        # 绘制食物
        if show_food:
            for food in self.env.foods:
                circle = plt.Circle(
                    (food.x, food.y), food.radius,
                    color='#2ecc71', alpha=0.6, zorder=1
                )
                ax.add_patch(circle)
                ax.text(food.x, food.y, f'{food.energy:.0f}', 
                       ha='center', va='center', fontsize=8, zorder=2)
        
        # 绘制水源
        for water in self.env.waters:
            circle = plt.Circle(
                (water.x, water.y), water.radius,
                color='#3498db', alpha=0.3, zorder=1
            )
            ax.add_patch(circle)
        
        # 绘制危险源
        for danger in self.env.dangers:
            circle = plt.Circle(
                (danger.x, danger.y), danger.radius,
                color='#e74c3c', alpha=0.5, zorder=1
            )
            ax.add_patch(circle)
        
        # 绘制信息素
        if show_pheromones:
            for phero in self.env.pheromones:
                if phero.is_active(self.env.step_count):
                    intensity = phero.get_current_intensity(self.env.step_count)
                    ax.scatter(
                        phero.x, phero.y,
                        c=self.pheromone_colors.get(phero.type, '#95a5a6'),
                        s=intensity * 20,
                        alpha=min(intensity / 10, 0.6),
                        zorder=1
                    )
        
        # 绘制虫子和轨迹
        alive_worms = [w for w in self.sim.worms if w.is_alive]
        
        for worm in alive_worms:
            # 绘制轨迹
            if show_trajectories and len(worm.trajectory) > 1:
                traj = np.array(worm.trajectory[-50:])  # 最近50个点
                color = self.behavior_colors.get(worm.current_behavior, '#95a5a6')
                ax.plot(traj[:, 0], traj[:, 1], color=color, alpha=0.3, linewidth=1, zorder=2)
            
            # 绘制虫子
            color = self.behavior_colors.get(worm.current_behavior, '#95a5a6')
            
            # 身体
            circle = plt.Circle(
                (worm.x, worm.y), 3,
                color=color, alpha=0.8, zorder=3
            )
            ax.add_patch(circle)
            
            # 朝向指示
            dx = 6 * np.cos(worm.heading)
            dy = 6 * np.sin(worm.heading)
            ax.arrow(worm.x, worm.y, dx, dy, head_width=2, head_length=2,
                    fc=color, ec=color, zorder=4)
            
            # 能量指示（圆圈大小）
            energy_ratio = worm.state.energy / worm.config.max_energy
            ring = plt.Circle(
                (worm.x, worm.y), 3 + energy_ratio * 2,
                fill=False, color='black', linewidth=1, alpha=0.5, zorder=3
            )
            ax.add_patch(ring)
        
        # 设置坐标轴
        ax.set_xlim(-10, self.env.width + 10)
        ax.set_ylim(-10, self.env.height + 10)
        ax.set_aspect('equal')
        ax.set_xlabel('X Position')
        ax.set_ylabel('Y Position')
        
        # 标题
        time_of_day = self.env.day_night.get_time_of_day()
        light_level = self.env.day_night.get_light_level()
        title = f'Step: {self.env.step_count} | Time: {time_of_day} | Light: {light_level:.1f} | Population: {len(alive_worms)}'
        ax.set_title(title, fontsize=12, fontweight='bold')
        
        # 图例
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color, 
                      markersize=8, label=behavior)
            for behavior, color in self.behavior_colors.items()
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=8)
        
        return fig, ax
    
    def create_animation(
        self,
        n_frames: int = 1000,
        fps: int = 10,
        save_path: Optional[str] = None,
        show_progress: bool = True
    ):
        """创建群体演化动画"""
        fig, ax = plt.subplots(figsize=(12, 12))
        
        def init():
            ax.clear()
            return []
        
        def update(frame):
            # 运行仿真步
            if frame > 0:
                self.sim.step()
            
            ax.clear()
            self.plot_ecosystem_state(ax=ax)
            return []
        
        if show_progress:
            print(f"创建动画: {n_frames}帧, {fps}fps...")
        
        anim = FuncAnimation(
            fig, update, frames=n_frames,
            init_func=init, blit=False
        )
        
        if save_path:
            writer = FFMpegWriter(fps=fps, metadata=dict(artist='SuperEcosystem'))
            anim.save(save_path, writer=writer)
            if show_progress:
                print(f"动画已保存: {save_path}")
        
        plt.close(fig)
        return anim
    
    def plot_population_dynamics(self, save_path: Optional[str] = None):
        """绘制种群动态图"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 种群数量变化
        ax1 = axes[0, 0]
        ax1.plot(self.sim.population_history, 'b-', linewidth=2)
        ax1.axhline(y=self.sim.max_population, color='r', linestyle='--', label='Max Capacity')
        ax1.set_xlabel('Step')
        ax1.set_ylabel('Population')
        ax1.set_title('Population Dynamics')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 出生和死亡统计
        ax2 = axes[0, 1]
        categories = ['Births', 'Deaths']
        values = [self.sim.birth_count, self.sim.death_count]
        colors = ['#2ecc71', '#e74c3c']
        ax2.bar(categories, values, color=colors, alpha=0.7)
        ax2.set_ylabel('Count')
        ax2.set_title('Reproduction & Mortality')
        
        # 3. 行为分布
        ax3 = axes[1, 0]
        alive_worms = [w for w in self.sim.worms if w.is_alive]
        behavior_counts = {}
        for w in alive_worms:
            behavior_counts[w.current_behavior] = behavior_counts.get(w.current_behavior, 0) + 1
        
        if behavior_counts:
            behaviors = list(behavior_counts.keys())
            counts = list(behavior_counts.values())
            colors = [self.behavior_colors.get(b, '#95a5a6') for b in behaviors]
            ax3.pie(counts, labels=behaviors, colors=colors, autopct='%1.1f%%')
            ax3.set_title('Current Behavior Distribution')
        
        # 4. 能量分布
        ax4 = axes[1, 1]
        if alive_worms:
            energies = [w.state.energy for w in alive_worms]
            ax4.hist(energies, bins=20, color='#3498db', alpha=0.7, edgecolor='black')
            ax4.axvline(x=np.mean(energies), color='r', linestyle='--', 
                       label=f'Mean: {np.mean(energies):.1f}')
            ax4.set_xlabel('Energy')
            ax4.set_ylabel('Count')
            ax4.set_title('Energy Distribution')
            ax4.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"种群动态图已保存: {save_path}")
        
        return fig
    
    def plot_emergence_metrics(
        self,
        analyzer: EmergenceAnalyzer,
        save_path: Optional[str] = None
    ):
        """绘制涌现指标"""
        if not analyzer.metrics_history:
            print("没有可绘制的涌现指标数据")
            return None
        
        fig, axes = plt.subplots(3, 2, figsize=(14, 12))
        
        metrics = analyzer.metrics_history
        steps = range(len(metrics))
        
        # 1. 聚类指标
        ax1 = axes[0, 0]
        clustering = [m.clustering_coefficient for m in metrics]
        n_clusters = [m.n_clusters for m in metrics]
        ax1.plot(steps, clustering, 'b-', label='Clustering Coefficient')
        ax1_twin = ax1.twinx()
        ax1_twin.plot(steps, n_clusters, 'r--', label='N Clusters', alpha=0.7)
        ax1.set_xlabel('Step')
        ax1.set_ylabel('Clustering', color='b')
        ax1_twin.set_ylabel('N Clusters', color='r')
        ax1.set_title('Clustering Dynamics')
        ax1.grid(True, alpha=0.3)
        
        # 2. 空间分布
        ax2 = axes[0, 1]
        spatial_entropy = [m.spatial_entropy for m in metrics]
        uniformity = [m.spatial_uniformity for m in metrics]
        ax2.plot(steps, spatial_entropy, 'g-', label='Spatial Entropy')
        ax2.plot(steps, uniformity, 'orange', label='Uniformity')
        ax2.set_xlabel('Step')
        ax2.set_ylabel('Metric Value')
        ax2.set_title('Spatial Distribution')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 行为同步性
        ax3 = axes[1, 0]
        sync_index = [m.behavior_sync_index for m in metrics]
        behavior_entropy = [m.behavior_entropy for m in metrics]
        ax3.plot(steps, sync_index, 'purple', label='Sync Index')
        ax3.plot(steps, behavior_entropy, 'cyan', label='Behavior Entropy', alpha=0.7)
        ax3.set_xlabel('Step')
        ax3.set_ylabel('Value')
        ax3.set_title('Behavior Synchronization')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 社交网络
        ax4 = axes[1, 1]
        network_density = [m.network_density for m in metrics]
        avg_degree = [m.avg_degree for m in metrics]
        ax4.plot(steps, network_density, 'brown', label='Network Density')
        ax4.plot(steps, avg_degree, 'pink', label='Avg Degree', alpha=0.7)
        ax4.set_xlabel('Step')
        ax4.set_ylabel('Value')
        ax4.set_title('Social Network Metrics')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # 5. 信息素指标
        ax5 = axes[2, 0]
        phero_conc = [m.pheromone_concentration for m in metrics]
        trail_strength = [m.trail_strength for m in metrics]
        ax5.plot(steps, phero_conc, 'green', label='Concentration')
        ax5.plot(steps, trail_strength, 'orange', label='Trail Strength')
        ax5.set_xlabel('Step')
        ax5.set_ylabel('Value')
        ax5.set_title('Pheromone Metrics')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # 6. 演化指标
        ax6 = axes[2, 1]
        growth_rate = [m.population_growth_rate for m in metrics]
        survival_rate = [m.survival_rate for m in metrics]
        ax6.plot(steps, growth_rate, 'blue', label='Growth Rate')
        ax6.plot(steps, survival_rate, 'red', label='Survival Rate', alpha=0.7)
        ax6.axhline(y=0, color='k', linestyle='--', alpha=0.3)
        ax6.set_xlabel('Step')
        ax6.set_ylabel('Rate')
        ax6.set_title('Evolution Metrics')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"涌现指标图已保存: {save_path}")
        
        return fig
    
    def plot_trajectory_analysis(
        self,
        analyzer: EmergenceAnalyzer,
        save_path: Optional[str] = None
    ):
        """绘制轨迹分析"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        alive_worms = [w for w in self.sim.worms if w.is_alive]
        if not alive_worms:
            print("没有存活的虫子用于轨迹分析")
            return None
        
        # 1. 所有轨迹叠加
        ax1 = axes[0, 0]
        for worm in alive_worms[:20]:  # 只显示前20个
            if len(worm.trajectory) > 1:
                traj = np.array(worm.trajectory)
                ax1.plot(traj[:, 0], traj[:, 1], alpha=0.3, linewidth=0.5)
        ax1.set_xlim(0, self.env.width)
        ax1.set_ylim(0, self.env.height)
        ax1.set_aspect('equal')
        ax1.set_title('Trajectory Overlay (First 20 Worms)')
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        
        # 2. 空间密度热图
        ax2 = axes[0, 1]
        all_positions = []
        for worm in alive_worms:
            all_positions.extend(worm.trajectory)
        
        if all_positions:
            positions = np.array(all_positions)
            heatmap, xedges, yedges = np.histogram2d(
                positions[:, 0], positions[:, 1],
                bins=50, range=[[0, self.env.width], [0, self.env.height]]
            )
            extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
            ax2.imshow(heatmap.T, extent=extent, origin='lower', cmap='hot', aspect='auto')
            ax2.set_title('Position Density Heatmap')
            ax2.set_xlabel('X')
            ax2.set_ylabel('Y')
        
        # 3. 轨迹迂曲度分布
        ax3 = axes[1, 0]
        traj_analysis = analyzer.analyze_trajectories()
        if traj_analysis and 'trajectory_metrics' in traj_analysis:
            tortuosities = [m['tortuosity'] for m in traj_analysis['trajectory_metrics']]
            ax3.hist(tortuosities, bins=20, color='#9b59b6', alpha=0.7, edgecolor='black')
            ax3.axvline(x=np.mean(tortuosities), color='r', linestyle='--',
                       label=f'Mean: {np.mean(tortuosities):.2f}')
            ax3.set_xlabel('Tortuosity')
            ax3.set_ylabel('Count')
            ax3.set_title('Tortuosity Distribution')
            ax3.legend()
        
        # 4. 活动范围分布
        ax4 = axes[1, 1]
        if traj_analysis and 'trajectory_metrics' in traj_analysis:
            bbox_areas = [m['bbox_area'] for m in traj_analysis['trajectory_metrics']]
            ax4.hist(bbox_areas, bins=20, color='#1abc9c', alpha=0.7, edgecolor='black')
            ax4.axvline(x=np.mean(bbox_areas), color='r', linestyle='--',
                       label=f'Mean: {np.mean(bbox_areas):.1f}')
            ax4.set_xlabel('Activity Range (BBox Area)')
            ax4.set_ylabel('Count')
            ax4.set_title('Activity Range Distribution')
            ax4.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"轨迹分析图已保存: {save_path}")
        
        return fig
    
    def plot_social_network(
        self,
        connection_threshold: float = 30.0,
        save_path: Optional[str] = None
    ):
        """绘制社交网络图"""
        fig, ax = plt.subplots(figsize=(12, 12))
        
        alive_worms = [w for w in self.sim.worms if w.is_alive]
        if len(alive_worms) < 2:
            print("虫子数量不足，无法绘制社交网络")
            return None
        
        # 获取位置
        positions = {w.id: (w.x, w.y) for w in alive_worms}
        
        # 绘制连接
        for i, w1 in enumerate(alive_worms):
            for w2 in alive_worms[i+1:]:
                dist = np.sqrt((w1.x - w2.x)**2 + (w1.y - w2.y)**2)
                if dist < connection_threshold:
                    ax.plot([w1.x, w2.x], [w1.y, w2.y], 'gray', alpha=0.3, linewidth=0.5)
        
        # 绘制节点
        for worm in alive_worms:
            x, y = positions[worm.id]
            color = self.behavior_colors.get(worm.current_behavior, '#95a5a6')
            size = 50 + worm.state.energy / 2
            ax.scatter(x, y, c=color, s=size, alpha=0.8, edgecolors='black', linewidth=1)
            
            # 显示ID
            ax.text(x, y+5, str(worm.id), ha='center', va='bottom', fontsize=8)
        
        ax.set_xlim(0, self.env.width)
        ax.set_ylim(0, self.env.height)
        ax.set_aspect('equal')
        ax.set_title('Social Network (Proximity Connections)')
        ax.set_xlabel('X Position')
        ax.set_ylabel('Y Position')
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"社交网络图已保存: {save_path}")
        
        return fig
    
    def generate_all_visualizations(
        self,
        analyzer: Optional[EmergenceAnalyzer] = None,
        prefix: str = ''
    ):
        """生成所有可视化"""
        print("=" * 60)
        print("生成所有可视化...")
        print("=" * 60)
        
        # 1. 生态系统状态图
        print("\n1. 绘制生态系统状态...")
        fig, _ = self.plot_ecosystem_state()
        fig.savefig(f'{self.output_dir}/{prefix}ecosystem_state.png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        # 2. 种群动态
        print("2. 绘制种群动态...")
        fig = self.plot_population_dynamics()
        if fig:
            fig.savefig(f'{self.output_dir}/{prefix}population_dynamics.png', dpi=150, bbox_inches='tight')
            plt.close(fig)
        
        # 3. 涌现指标
        if analyzer:
            print("3. 绘制涌现指标...")
            fig = self.plot_emergence_metrics(analyzer)
            if fig:
                fig.savefig(f'{self.output_dir}/{prefix}emergence_metrics.png', dpi=150, bbox_inches='tight')
                plt.close(fig)
            
            # 4. 轨迹分析
            print("4. 绘制轨迹分析...")
            fig = self.plot_trajectory_analysis(analyzer)
            if fig:
                fig.savefig(f'{self.output_dir}/{prefix}trajectory_analysis.png', dpi=150, bbox_inches='tight')
                plt.close(fig)
        
        # 5. 社交网络
        print("5. 绘制社交网络...")
        fig = self.plot_social_network()
        if fig:
            fig.savefig(f'{self.output_dir}/{prefix}social_network.png', dpi=150, bbox_inches='tight')
            plt.close(fig)
        
        print(f"\n所有可视化已保存到: {self.output_dir}/")


# 测试代码
if __name__ == "__main__":
    print("=" * 70)
    print("生态系统可视化测试")
    print("=" * 70)
    
    print("\n此模块需要在群体仿真完成后进行可视化")
    print("请运行 population_sim.py 生成仿真数据")
    print("\n使用示例:")
    print("  from population_sim import PopulationSimulation")
    print("  from emergence_analysis import EmergenceAnalyzer")
    print("  from visualize_ecosystem import EcosystemVisualizer")
    print("  ")
    print("  sim = PopulationSimulation(n_initial_worms=10)")
    print("  results = sim.run(n_steps=500)")
    print("  ")
    print("  # 分析")
    print("  analyzer = EmergenceAnalyzer(sim)")
    print("  for step in range(500):")
    print("      analyzer.analyze_step(step)")
    print("  ")
    print("  # 可视化")
    print("  visualizer = EcosystemVisualizer(sim)")
    print("  visualizer.generate_all_visualizations(analyzer)")
