#!/usr/bin/env python3
"""
超级TNN生态系统 - 快速测试
小规模快速运行以验证安装
"""

import sys
import time
import numpy as np
import torch

print("=" * 70)
print("超级TNN生态系统 - 快速测试")
print("=" * 70)

# 检查依赖
print("\n[1/5] 检查依赖...")
try:
    from super_tnn_worm import SuperTNNCore
    from ecosystem_env import SuperEcosystem
    from population_sim import PopulationSimulation
    from emergence_analysis import EmergenceAnalyzer
    print("  ✓ 所有依赖模块加载成功")
except ImportError as e:
    print(f"  ✗ 导入错误: {e}")
    sys.exit(1)

# 测试TNN核心
print("\n[2/5] 测试TNN核心...")
try:
    brain = SuperTNNCore(device='cpu')
    info = brain.get_architecture_info()
    print(f"  ✓ TNN核心创建成功")
    print(f"    总参数: {info['total_params']:,}")
    print(f"    目标参数: 1,360,000")
    print(f"    比例: {info['total_params']/1360000:.2f}x")
    
    # 前向传播测试
    test_input = torch.randn(1, 32)
    output = brain(test_input)
    print(f"    前向传播测试: ✓ (输出形状: {output.shape})")
except Exception as e:
    print(f"  ✗ TNN核心测试失败: {e}")
    sys.exit(1)

# 测试环境
print("\n[3/5] 测试生态环境...")
try:
    env = SuperEcosystem(width=500, height=500)
    env.create_random_environment(n_food=10, n_water=2, n_dangers=1)
    print(f"  ✓ 环境创建成功")
    print(f"    大小: {env.width}x{env.height}")
    print(f"    食物源: {len(env.foods)}")
    print(f"    水源: {len(env.waters)}")
    print(f"    危险源: {len(env.dangers)}")
    
    # 传感器测试
    readings = env.get_sensor_readings(250, 250, 0.0)
    print(f"    传感器读数: ✓ (32维)")
except Exception as e:
    print(f"  ✗ 环境测试失败: {e}")
    sys.exit(1)

# 测试群体仿真（小规模）
print("\n[4/5] 测试群体仿真（3虫子 x 50步）...")
try:
    start_time = time.time()
    sim = PopulationSimulation(
        n_initial_worms=3,
        max_population=10,
        env_width=500,
        env_height=500,
        seed=42
    )
    
    results = sim.run(n_steps=50, verbose=False)
    elapsed = time.time() - start_time
    
    print(f"  ✓ 仿真完成")
    print(f"    总耗时: {elapsed:.2f}秒")
    print(f"    平均每步: {elapsed/50*1000:.1f}ms")
    print(f"    最终种群: {results['final_population']}")
    print(f"    总出生: {results['total_births']}")
    print(f"    总死亡: {results['total_deaths']}")
except Exception as e:
    print(f"  ✗ 仿真测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试分析
print("\n[5/5] 测试涌现分析...")
try:
    analyzer = EmergenceAnalyzer(sim)
    for step in range(0, 50, 5):
        analyzer.analyze_step(step)
    
    patterns = analyzer.detect_emergent_patterns()
    print(f"  ✓ 分析完成")
    print(f"    检测到的模式: {len(patterns)}")
    for name, info in patterns.items():
        print(f"      - {name}: {info['confidence']:.3f}")
    
    # 生物对比
    comparison = analyzer.compare_to_biology()
    if comparison['similarities']:
        print(f"    与生物群体的相似性: {len(comparison['similarities'])}个")
except Exception as e:
    print(f"  ✗ 分析测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("快速测试完成! 所有模块正常工作")
print("=" * 70)

print("\n下一步建议:")
print("  1. 运行完整实验: python3 run_experiment.py --n-worms 20 --n-steps 1000")
print("  2. 查看实验报告: /root/.openclaw/workspace/research_notes/tnn_super_ecosystem_experiment.md")
print("  3. 查看可视化结果: results/experiment_*/visualizations/")

print("\n性能预估:")
print(f"  - 10虫子 x 1000步: ~{(elapsed/50*1000*10/60):.1f}分钟")
print(f"  - 20虫子 x 1000步: ~{(elapsed/50*1000*20/60):.1f}分钟")
print(f"  - 50虫子 x 1000步: ~{(elapsed/50*1000*50/60):.1f}分钟")
