"""
超级TNN生态系统实验 - 主运行脚本
整合所有模块并运行完整实验
"""

import os
import sys
import time
import argparse
import numpy as np
import torch
from datetime import datetime

# 导入自定义模块
from super_tnn_worm import SuperTNNCore
from ecosystem_env import SuperEcosystem
from population_sim import PopulationSimulation, SuperWormAgent
from emergence_analysis import EmergenceAnalyzer
from visualize_ecosystem import EcosystemVisualizer


def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def run_experiment(
    n_initial_worms: int = 20,
    n_steps: int = 1000,
    max_population: int = 50,
    env_size: float = 1000.0,
    device: str = 'cpu',
    seed: int = 42,
    output_dir: str = './results',
    save_interval: int = 100
):
    """
    运行完整实验
    
    Args:
        n_initial_worms: 初始虫子数量
        n_steps: 仿真步数
        max_population: 最大种群数量
        env_size: 环境大小
        device: 计算设备
        seed: 随机种子
        output_dir: 输出目录
        save_interval: 保存间隔
    """
    # 创建输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"{output_dir}/experiment_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/visualizations", exist_ok=True)
    
    print_section("超级TNN生态系统实验")
    print(f"实验时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"输出目录: {output_dir}")
    print(f"\n实验参数:")
    print(f"  初始虫子数: {n_initial_worms}")
    print(f"  仿真步数: {n_steps}")
    print(f"  最大种群: {max_population}")
    print(f"  环境大小: {env_size}x{env_size}")
    print(f"  计算设备: {device}")
    print(f"  随机种子: {seed}")
    
    # 设备信息
    if device == 'cuda' and torch.cuda.is_available():
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
    else:
        device = 'cpu'
        print(f"  使用CPU计算")
    
    # ===================== 阶段1: 初始化 =====================
    print_section("阶段1: 初始化生态系统")
    
    start_time = time.time()
    
    sim = PopulationSimulation(
        n_initial_worms=n_initial_worms,
        env_width=env_size,
        env_height=env_size,
        max_population=max_population,
        device=device,
        seed=seed
    )
    
    print(f"环境初始化完成")
    print(f"  食物源: {len(sim.env.foods)}")
    print(f"  水源: {len(sim.env.waters)}")
    print(f"  危险源: {len(sim.env.dangers)}")
    print(f"  初始虫子: {len(sim.worms)}")
    
    # 检查TNN参数
    sample_brain = sim.worms[0].brain
    arch_info = sample_brain.get_architecture_info()
    print(f"\nTNN架构信息:")
    print(f"  总参数量: {arch_info['total_params']:,}")
    print(f"  目标参数量: 1,360,000")
    print(f"  压缩比: {arch_info['compression_ratio']:.1f}x")
    
    # ===================== 阶段2: 运行仿真 =====================
    print_section("阶段2: 运行群体仿真")
    
    # 初始化分析器
    analyzer = EmergenceAnalyzer(sim)
    
    # 记录性能
    step_times = []
    
    print(f"\n开始仿真（{n_steps}步）...")
    print(f"进度: [0/{n_steps}] 种群: {len(sim.worms)} 出生: 0 死亡: 0")
    
    for step in range(n_steps):
        step_start = time.time()
        
        # 运行仿真步
        stats = sim.step()
        
        # 分析涌现指标
        if step % 10 == 0:  # 每10步分析一次
            analyzer.analyze_step(step)
        
        step_time = time.time() - step_start
        step_times.append(step_time)
        
        # 打印进度
        if step % save_interval == 0 or step == n_steps - 1:
            print(f"进度: [{step}/{n_steps}] "
                  f"种群: {stats['population']} "
                  f"出生: {stats['births']} "
                  f"死亡: {stats['deaths']} "
                  f"平均步时: {np.mean(step_times[-100:]):.3f}s")
            
            # 保存中间状态
            if step > 0 and step % (save_interval * 2) == 0:
                visualizer = EcosystemVisualizer(sim, output_dir=f"{output_dir}/visualizations")
                visualizer.plot_ecosystem_state()
                plt = sys.modules.get('matplotlib.pyplot')
                if plt:
                    plt.savefig(f"{output_dir}/visualizations/state_step_{step}.png", dpi=100)
                    plt.close()
    
    elapsed_time = time.time() - start_time
    
    print(f"\n仿真完成!")
    print(f"  总耗时: {elapsed_time:.2f}秒 ({elapsed_time/60:.2f}分钟)")
    print(f"  平均每步: {np.mean(step_times):.3f}秒")
    print(f"  最终种群: {len([w for w in sim.worms if w.is_alive])}")
    print(f"  总出生: {sim.birth_count}")
    print(f"  总死亡: {sim.death_count}")
    
    # ===================== 阶段3: 涌现分析 =====================
    print_section("阶段3: 涌现行为分析")
    
    # 轨迹分析
    traj_analysis = analyzer.analyze_trajectories()
    if traj_analysis:
        print(f"\n轨迹特征:")
        print(f"  平均路径长度: {traj_analysis['mean_path_length']:.1f}")
        print(f"  平均迂曲度: {traj_analysis['mean_tortuosity']:.3f}")
        print(f"  平均活动范围: {traj_analysis['mean_bbox_area']:.1f}")
    
    # 检测涌现模式
    patterns = analyzer.detect_emergent_patterns()
    print(f"\n检测到的涌现模式 ({len(patterns)}个):")
    for pattern_name, pattern_info in patterns.items():
        print(f"  - {pattern_name}: {pattern_info['description']}")
        print(f"    置信度: {pattern_info['confidence']:.3f}")
    
    # 生物对比
    comparison = analyzer.compare_to_biology()
    print(f"\n与生物群体对比:")
    if comparison['similarities']:
        print(f"  相似性:")
        for sim_item in comparison['similarities']:
            print(f"    - {sim_item['description']}")
    if comparison['differences']:
        print(f"  差异性:")
        for diff_item in comparison['differences']:
            print(f"    - {diff_item['description']}")
    
    # ===================== 阶段4: 生成可视化 =====================
    print_section("阶段4: 生成可视化")
    
    visualizer = EcosystemVisualizer(sim, output_dir=f"{output_dir}/visualizations")
    visualizer.generate_all_visualizations(analyzer, prefix="")
    
    # ===================== 阶段5: 保存结果 =====================
    print_section("阶段5: 保存实验结果")
    
    # 保存分析报告
    report = analyzer.generate_report()
    report_path = f"{output_dir}/emergence_report.txt"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"分析报告已保存: {report_path}")
    
    # 保存统计摘要
    summary = {
        'experiment_params': {
            'n_initial_worms': n_initial_worms,
            'n_steps': n_steps,
            'max_population': max_population,
            'env_size': env_size,
            'device': device,
            'seed': seed
        },
        'tnn_architecture': arch_info,
        'performance': {
            'total_time': elapsed_time,
            'avg_step_time': float(np.mean(step_times)),
            'total_steps': n_steps
        },
        'population_stats': {
            'final_population': len([w for w in sim.worms if w.is_alive]),
            'total_births': sim.birth_count,
            'total_deaths': sim.death_count,
            'population_history': sim.population_history
        },
        'emergent_patterns': patterns,
        'biological_comparison': comparison,
        'trajectory_summary': traj_analysis
    }
    
    import json
    summary_path = f"{output_dir}/experiment_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"统计摘要已保存: {summary_path}")
    
    print_section("实验完成!")
    print(f"所有结果已保存到: {output_dir}/")
    
    return {
        'simulation': sim,
        'analyzer': analyzer,
        'visualizer': visualizer,
        'summary': summary,
        'output_dir': output_dir
    }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='超级TNN生态系统实验')
    parser.add_argument('--n-worms', type=int, default=20, help='初始虫子数量')
    parser.add_argument('--n-steps', type=int, default=1000, help='仿真步数')
    parser.add_argument('--max-pop', type=int, default=50, help='最大种群数量')
    parser.add_argument('--env-size', type=float, default=1000.0, help='环境大小')
    parser.add_argument('--device', type=str, default='cpu', help='计算设备 (cpu/cuda)')
    parser.add_argument('--seed', type=int, default=42, help='随机种子')
    parser.add_argument('--output', type=str, default='./results', help='输出目录')
    parser.add_argument('--save-interval', type=int, default=100, help='保存间隔')
    
    args = parser.parse_args()
    
    # 运行实验
    results = run_experiment(
        n_initial_worms=args.n_worms,
        n_steps=args.n_steps,
        max_population=args.max_pop,
        env_size=args.env_size,
        device=args.device,
        seed=args.seed,
        output_dir=args.output,
        save_interval=args.save_interval
    )
    
    return results


if __name__ == "__main__":
    results = main()
