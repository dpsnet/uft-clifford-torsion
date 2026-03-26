"""
微型TNN"反射虫" - 可视化工具
生成轨迹图、行为统计、对比分析
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.collections import LineCollection
from typing import Dict, List, Tuple, Optional
import os
import json

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def plot_single_trajectory(
    trajectory: np.ndarray,
    environment,
    title: str = "反射虫轨迹",
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 10)
):
    """
    绘制单个反射虫的运动轨迹
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # 绘制环境
    # 亮度热图
    brightness_grid = np.zeros((environment.height, environment.width))
    for i in range(environment.height):
        for j in range(environment.width):
            brightness_grid[i, j] = environment.get_total_brightness(j, i)
    
    im = ax.imshow(
        brightness_grid,
        extent=[0, environment.width, 0, environment.height],
        origin='lower',
        cmap='YlOrRd',
        alpha=0.5
    )
    plt.colorbar(im, ax=ax, label='亮度')
    
    # 绘制障碍物
    for obs in environment.obstacles:
        circle = plt.Circle(
            (obs.x, obs.y),
            obs.radius,
            color='gray',
            alpha=0.7,
            label='障碍物'
        )
        ax.add_patch(circle)
    
    # 绘制轨迹（带颜色渐变表示时间）
    if len(trajectory) > 1:
        points = trajectory.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        
        # 根据时间设置颜色
        norm = plt.Normalize(0, len(trajectory))
        lc = LineCollection(
            segments,
            cmap='viridis',
            norm=norm,
            linewidths=2,
            alpha=0.8
        )
        lc.set_array(np.arange(len(trajectory)))
        ax.add_collection(lc)
        
        # 起点和终点标记
        ax.scatter(*trajectory[0], color='green', s=200, marker='o', 
                  edgecolors='black', linewidth=2, label='起点', zorder=5)
        ax.scatter(*trajectory[-1], color='red', s=200, marker='s',
                  edgecolors='black', linewidth=2, label='终点', zorder=5)
    
    ax.set_xlim(0, environment.width)
    ax.set_ylim(0, environment.height)
    ax.set_xlabel('X 位置')
    ax.set_ylabel('Y 位置')
    ax.set_title(title)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"轨迹图已保存: {save_path}")
    
    return fig, ax


def plot_multiple_trajectories(
    results: Dict[str, Dict],
    environment,
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (15, 12)
):
    """
    绘制多种行为模式的轨迹对比
    """
    behavior_names = {
        'phototaxis': '趋光虫',
        'photophobia': '避光虫',
        'thigmotaxis': '壁虎虫',
        'exploration': '探索虫',
        'homeostasis': '平衡虫'
    }
    
    behaviors = list(results.keys())
    n_behaviors = len(behaviors)
    
    # 创建子图
    n_cols = 3
    n_rows = (n_behaviors + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    if n_behaviors == 1:
        axes = np.array([axes])
    axes = axes.flatten()
    
    for idx, behavior in enumerate(behaviors):
        ax = axes[idx]
        
        # 绘制环境背景
        brightness_grid = np.zeros((environment.height, environment.width))
        for i in range(environment.height):
            for j in range(environment.width):
                brightness_grid[i, j] = environment.get_total_brightness(j, i)
        
        im = ax.imshow(
            brightness_grid,
            extent=[0, environment.width, 0, environment.height],
            origin='lower',
            cmap='YlOrRd',
            alpha=0.4
        )
        
        # 绘制障碍物
        for obs in environment.obstacles:
            circle = plt.Circle((obs.x, obs.y), obs.radius, color='gray', alpha=0.6)
            ax.add_patch(circle)
        
        # 绘制所有试验的轨迹
        trials = results[behavior]['trials']
        colors = plt.cm.tab10(np.linspace(0, 1, len(trials)))
        
        for trial_idx, trial in enumerate(trials[:5]):  # 最多显示5条轨迹
            trajectory = trial['trajectory']
            if len(trajectory) > 1:
                ax.plot(trajectory[:, 0], trajectory[:, 1], 
                       color=colors[trial_idx], alpha=0.6, linewidth=1.5)
                ax.scatter(*trajectory[0], color='green', s=50, marker='o', zorder=5)
                ax.scatter(*trajectory[-1], color='red', s=50, marker='s', zorder=5)
        
        name = behavior_names.get(behavior, behavior)
        ax.set_title(f'{name}\n({len(trials)} 次试验)', fontsize=12)
        ax.set_xlim(0, environment.width)
        ax.set_ylim(0, environment.height)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
    
    # 隐藏多余的子图
    for idx in range(n_behaviors, len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"多轨迹对比图已保存: {save_path}")
    
    return fig, axes


def plot_behavior_statistics(results: Dict[str, Dict], save_path: Optional[str] = None):
    """
    绘制行为统计对比图
    """
    behavior_names = {
        'phototaxis': '趋光虫',
        'photophobia': '避光虫',
        'thigmotaxis': '壁虎虫',
        'exploration': '探索虫',
        'homeostasis': '平衡虫'
    }
    
    behaviors = list(results.keys())
    names = [behavior_names.get(b, b) for b in behaviors]
    
    # 提取统计数据
    path_lengths = [results[b]['analysis']['mean_path_length'] for b in behaviors]
    path_stds = [results[b]['analysis']['std_path_length'] for b in behaviors]
    spectral_dims = [results[b]['analysis']['mean_spectral_dim'] for b in behaviors]
    spectral_stds = [results[b]['analysis']['std_spectral_dim'] for b in behaviors]
    energies = [results[b]['analysis']['mean_energy'] for b in behaviors]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. 路径长度
    ax = axes[0, 0]
    bars = ax.bar(names, path_lengths, yerr=path_stds, capsize=5, 
                  color='steelblue', alpha=0.8, edgecolor='black')
    ax.set_ylabel('平均路径长度')
    ax.set_title('不同行为的路径长度对比')
    ax.grid(True, alpha=0.3, axis='y')
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right')
    
    # 2. 谱维
    ax = axes[0, 1]
    bars = ax.bar(names, spectral_dims, yerr=spectral_stds, capsize=5,
                  color='coral', alpha=0.8, edgecolor='black')
    ax.axhline(y=4.0, color='gray', linestyle='--', label='d_s = 4 (基准)')
    ax.set_ylabel('平均谱维')
    ax.set_title('不同行为的谱维对比')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right')
    
    # 3. 终点位置分布
    ax = axes[1, 0]
    for behavior in behaviors:
        trials = results[behavior]['trials']
        final_positions = np.array([t['final_position'] for t in trials])
        ax.scatter(final_positions[:, 0], final_positions[:, 1], 
                  label=behavior_names.get(behavior, behavior), alpha=0.6, s=50)
    ax.set_xlabel('X 位置')
    ax.set_ylabel('Y 位置')
    ax.set_title('终点位置分布')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    
    # 4. 能量消耗
    ax = axes[1, 1]
    bars = ax.bar(names, energies, color='seagreen', alpha=0.8, edgecolor='black')
    ax.set_ylabel('剩余能量')
    ax.set_title('最终能量水平')
    ax.grid(True, alpha=0.3, axis='y')
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"行为统计图已保存: {save_path}")
    
    return fig, axes


def plot_spectral_evolution(results: Dict[str, Dict], save_path: Optional[str] = None):
    """
    绘制谱维演化图
    """
    behavior_names = {
        'phototaxis': '趋光虫',
        'photophobia': '避光虫',
        'thigmotaxis': '壁虎虫',
        'exploration': '探索虫',
        'homeostasis': '平衡虫'
    }
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    
    for idx, (behavior, result) in enumerate(results.items()):
        if idx >= 6:
            break
            
        ax = axes[idx]
        trials = result['trials']
        
        # 绘制每个试验的谱维演化
        for trial in trials[:5]:  # 最多5条
            spectral_history = trial['spectral_history']
            if spectral_history:
                ax.plot(spectral_history, alpha=0.6, linewidth=1)
        
        # 绘制平均值
        max_len = max(len(t['spectral_history']) for t in trials if t['spectral_history'])
        if max_len > 0:
            padded = []
            for t in trials:
                hist = t['spectral_history']
                if hist:
                    padded.append(hist + [hist[-1]] * (max_len - len(hist)))
            if padded:
                mean_spectral = np.mean(padded, axis=0)
                ax.plot(mean_spectral, color='red', linewidth=2, label='平均值')
        
        ax.axhline(y=4.0, color='gray', linestyle='--', alpha=0.5, label='d_s = 4')
        ax.axhline(y=2.0, color='gray', linestyle=':', alpha=0.5, label='d_s = 2')
        
        name = behavior_names.get(behavior, behavior)
        ax.set_title(f'{name}')
        ax.set_xlabel('时间步')
        ax.set_ylabel('谱维 d_s')
        ax.set_ylim(1.5, 4.5)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    # 隐藏多余的子图
    for idx in range(len(results), len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"谱维演化图已保存: {save_path}")
    
    return fig, axes


def plot_torsion_energy(results: Dict[str, Dict], save_path: Optional[str] = None):
    """
    绘制扭转场能量演化图
    """
    behavior_names = {
        'phototaxis': '趋光虫',
        'photophobia': '避光虫',
        'thigmotaxis': '壁虎虫',
        'exploration': '探索虫',
        'homeostasis': '平衡虫'
    }
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    
    for idx, (behavior, result) in enumerate(results.items()):
        if idx >= 6:
            break
            
        ax = axes[idx]
        trials = result['trials']
        
        # 绘制每个试验的扭转能量演化
        for trial in trials[:5]:
            worm = trial.get('worm', None)
            if worm and hasattr(worm, 'brain'):
                energy_history = worm.brain.torsion_energy_history
                if energy_history:
                    ax.plot(energy_history, alpha=0.6, linewidth=1)
        
        name = behavior_names.get(behavior, behavior)
        ax.set_title(f'{name}')
        ax.set_xlabel('时间步')
        ax.set_ylabel('扭转场能量')
        ax.grid(True, alpha=0.3)
    
    # 隐藏多余的子图
    for idx in range(len(results), len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"扭转能量图已保存: {save_path}")
    
    return fig, axes


def create_behavior_metrics_table(results: Dict[str, Dict]) -> str:
    """
    创建行为指标对比表（Markdown格式）
    """
    behavior_names = {
        'phototaxis': '趋光虫',
        'photophobia': '避光虫',
        'thigmotaxis': '壁虎虫',
        'exploration': '探索虫',
        'homeostasis': '平衡虫'
    }
    
    lines = []
    lines.append("## 行为指标对比表")
    lines.append("")
    lines.append("| 行为 | 平均路径长度 | 谱维(d_s) | 剩余能量 | 描述 |")
    lines.append("|------|-------------|----------|---------|------|")
    
    for behavior, result in results.items():
        name = behavior_names.get(behavior, behavior)
        analysis = result['analysis']
        
        path_len = f"{analysis['mean_path_length']:.1f}±{analysis['std_path_length']:.1f}"
        spectral = f"{analysis['mean_spectral_dim']:.2f}±{analysis['std_spectral_dim']:.2f}"
        energy = f"{analysis['mean_energy']:.1f}"
        desc = result['behavior_info']['description']
        
        lines.append(f"| {name} | {path_len} | {spectral} | {energy} | {desc} |")
    
    return "\n".join(lines)


def generate_all_visualizations(
    results: Dict[str, Dict],
    environment,
    output_dir: str = './visualizations'
):
    """
    生成所有可视化图表
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n生成可视化图表...")
    print("=" * 60)
    
    # 1. 多轨迹对比
    print("1. 多轨迹对比图...")
    plot_multiple_trajectories(
        results, environment,
        save_path=os.path.join(output_dir, 'trajectories_comparison.png')
    )
    plt.close()
    
    # 2. 行为统计
    print("2. 行为统计对比图...")
    plot_behavior_statistics(
        results,
        save_path=os.path.join(output_dir, 'behavior_statistics.png')
    )
    plt.close()
    
    # 3. 谱维演化
    print("3. 谱维演化图...")
    plot_spectral_evolution(
        results,
        save_path=os.path.join(output_dir, 'spectral_evolution.png')
    )
    plt.close()
    
    # 4. 为每个行为生成单独轨迹图
    print("4. 单独轨迹图...")
    for behavior, result in results.items():
        if result['trials']:
            trial = result['trials'][0]  # 使用第一次试验
            plot_single_trajectory(
                trial['trajectory'],
                environment,
                title=f"{result['behavior_info']['name']} 轨迹",
                save_path=os.path.join(output_dir, f'trajectory_{behavior}.png')
            )
            plt.close()
    
    # 5. 生成指标表格
    print("5. 行为指标表格...")
    table = create_behavior_metrics_table(results)
    with open(os.path.join(output_dir, 'metrics_table.md'), 'w', encoding='utf-8') as f:
        f.write(table)
    
    print(f"\n所有可视化已保存到: {output_dir}")
    print("=" * 60)


# 加载和可视化已有结果
def load_and_visualize(results_dir: str, output_dir: str = './visualizations'):
    """
    从JSON加载结果并生成可视化
    """
    results_path = os.path.join(results_dir, 'experiment_results.json')
    
    if not os.path.exists(results_path):
        print(f"结果文件不存在: {results_path}")
        return
    
    with open(results_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 重建结果结构（简化版，不含完整轨迹）
    results = {}
    for behavior, info in data.items():
        results[behavior] = {
            'behavior_info': info['behavior_info'],
            'analysis': info['analysis'],
            'trials': []  # 简化，不重建完整轨迹
        }
    
    # 创建虚拟环境用于可视化
    from environment import Environment2D
    env = Environment2D(100, 100)
    env.create_default_environment('simple')
    
    # 生成统计可视化
    plot_behavior_statistics(results, save_path=os.path.join(output_dir, 'behavior_statistics.png'))
    plt.close()
    
    print(f"可视化已生成: {output_dir}")


# 测试代码
if __name__ == "__main__":
    print("TNN反射虫可视化工具测试")
    print("=" * 60)
    
    # 创建测试数据
    from environment import Environment2D
    
    env = Environment2D(100, 100)
    env.create_default_environment('simple')
    
    # 生成测试轨迹
    t = np.linspace(0, 4*np.pi, 200)
    trajectory = np.column_stack([
        50 + 20 * np.cos(t) * np.exp(-t/10),
        50 + 20 * np.sin(t) * np.exp(-t/10)
    ])
    
    # 绘制测试轨迹
    fig, ax = plot_single_trajectory(
        trajectory, env,
        title="测试轨迹 - 趋光虫",
        save_path='./test_trajectory.png'
    )
    plt.close()
    
    print("测试完成!")
