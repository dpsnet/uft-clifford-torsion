#!/usr/bin/env python3
"""
TNN互补性能量谱维流分析

核心假设:
- 外空间能量 E_out 和内空间能量 E_in 互补
- E_out + E_in = E_total (常数)
- 能量在内外空间之间转移，而非增减
- 系统总能量由外部参数决定

这对应物理直觉:
- 引力势能降低 = 能量向内空间泄露
- 外空间谱维降低, 内空间谱维升高
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple
import json


def compute_spectral_flow_complementary(
    f_in: np.ndarray,  # 内空间能量比例 (0-1)
    E_total: float = 100.0  # 总能量常数
):
    """
    基于互补性能量假设计算谱维流
    
    f_in = 0: 所有能量在外空间 → d_s_out=4, d_s_in=4 (基态)
    f_in = 1: 所有能量在内空间 → d_s_out=0 (黑洞), d_s_in=10
    
    参数:
        f_in: 内空间能量比例数组 [0, 1]
        E_total: 总能量常数
    """
    E_out = E_total * (1 - f_in)  # 外空间能量
    E_in = E_total * f_in  # 内空间能量
    
    # 外空间谱维:
    # f_in = 0 (E在外): d_s = 4 (正常观测)
    # f_in = 1 (E在内): d_s = 0 (信息不可达)
    # 使用平滑过渡函数
    d_s_out = 4.0 * (1 - f_in)**2
    
    # 内空间谱维:
    # f_in = 0: d_s = 4 (内空间关闭)
    # f_in = 1: d_s = 10 (内空间完全开放)
    # 使用与原始公式类似的S型曲线
    d_s_in = 4.0 + 6.0 * f_in**2 / (0.1 + f_in**2)
    
    return d_s_out, d_s_in, E_out, E_in


def analyze_conservation_laws(f_in: np.ndarray, d_s_out: np.ndarray, d_s_in: np.ndarray):
    """分析各种守恒律候选"""
    
    results = {}
    
    # 1. 简单维度相加
    sum_dims = d_s_out + d_s_in
    results['sum'] = {
        'value_at_0': sum_dims[0],
        'value_at_half': sum_dims[len(f_in)//2],
        'value_at_1': sum_dims[-1],
        'std': np.std(sum_dims)
    }
    
    # 2. 归一化比例
    norm_sum = d_s_out / 4 + d_s_in / 10
    results['normalized'] = {
        'value_at_0': norm_sum[0],
        'value_at_half': norm_sum[len(f_in)//2],
        'value_at_1': norm_sum[-1],
        'std': np.std(norm_sum)
    }
    
    # 3. 维度乘积
    product = d_s_out * d_s_in
    results['product'] = {
        'value_at_0': product[0],
        'value_at_half': product[len(f_in)//2],
        'value_at_1': product[-1],
        'std': np.std(product)
    }
    
    # 4. 信息论形式: 1/d_s_out + 1/d_s_in ?
    inv_sum = 1/np.maximum(d_s_out, 0.01) + 1/np.maximum(d_s_in, 0.01)
    results['inverse'] = {
        'value_at_0': inv_sum[0],
        'value_at_half': inv_sum[len(f_in)//2],
        'value_at_1': inv_sum[-1],
        'std': np.std(inv_sum)
    }
    
    return results


def plot_complementary_flow():
    """可视化互补性能量谱维流"""
    
    f_in = np.linspace(0, 1, 500)
    
    # 计算不同总能量下的谱维流
    E_total_values = [1.0, 10.0, 100.0]
    colors = ['blue', 'green', 'red']
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    for E_total, color in zip(E_total_values, colors):
        d_s_out, d_s_in, E_out, E_in = compute_spectral_flow_complementary(f_in, E_total)
        
        # 1. 外空间谱维
        axes[0, 0].plot(f_in, d_s_out, color=color, linewidth=2, 
                       label=f'E_total={E_total}')
        
        # 2. 内空间谱维
        axes[0, 1].plot(f_in, d_s_in, color=color, linewidth=2,
                       label=f'E_total={E_total}')
        
        # 3. 维度之和
        sum_dims = d_s_out + d_s_in
        axes[0, 2].plot(f_in, sum_dims, color=color, linewidth=2,
                       label=f'E_total={E_total}')
        
        # 4. 归一化比例
        norm_sum = d_s_out / 4 + d_s_in / 10
        axes[1, 0].plot(f_in, norm_sum, color=color, linewidth=2,
                       label=f'E_total={E_total}')
        
        # 5. 维度乘积
        product = d_s_out * d_s_in
        axes[1, 1].plot(f_in, product, color=color, linewidth=2,
                       label=f'E_total={E_total}')
        
        # 6. 能量分布
        axes[1, 2].plot(f_in, E_out, '--', color=color, linewidth=1.5,
                       label=f'E_out (E_total={E_total})')
        axes[1, 2].plot(f_in, E_in, '-', color=color, linewidth=2,
                       label=f'E_in (E_total={E_total})')
    
    # 设置标签和参考线
    axes[0, 0].set_ylabel('d_s (external)', fontsize=12)
    axes[0, 0].set_xlabel('f_in (energy fraction in internal)', fontsize=11)
    axes[0, 0].set_title('External Spectral Dimension', fontsize=13)
    axes[0, 0].axhline(y=4, color='gray', linestyle=':', alpha=0.5)
    axes[0, 0].axhline(y=0, color='gray', linestyle=':', alpha=0.5)
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    axes[0, 1].set_ylabel('d_s (internal)', fontsize=12)
    axes[0, 1].set_xlabel('f_in', fontsize=11)
    axes[0, 1].set_title('Internal Spectral Dimension', fontsize=13)
    axes[0, 1].axhline(y=4, color='gray', linestyle=':', alpha=0.5)
    axes[0, 1].axhline(y=10, color='gray', linestyle=':', alpha=0.5)
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    axes[0, 2].set_ylabel('d_s_out + d_s_in', fontsize=12)
    axes[0, 2].set_xlabel('f_in', fontsize=11)
    axes[0, 2].set_title('Sum of Dimensions', fontsize=13)
    axes[0, 2].axhline(y=8, color='orange', linestyle=':', alpha=0.5, label='today universe')
    axes[0, 2].axhline(y=10, color='gray', linestyle=':', alpha=0.5, label='black hole')
    axes[0, 2].axhline(y=14, color='red', linestyle=':', alpha=0.5, label='constant 14')
    axes[0, 2].legend()
    axes[0, 2].grid(True, alpha=0.3)
    
    axes[1, 0].set_ylabel('d_s_out/4 + d_s_in/10', fontsize=12)
    axes[1, 0].set_xlabel('f_in', fontsize=11)
    axes[1, 0].set_title('Normalized Conservation', fontsize=13)
    axes[1, 0].axhline(y=1.0, color='gray', linestyle=':', alpha=0.5)
    axes[1, 0].axhline(y=2.0, color='red', linestyle=':', alpha=0.5)
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    axes[1, 1].set_ylabel('d_s_out × d_s_in', fontsize=12)
    axes[1, 1].set_xlabel('f_in', fontsize=11)
    axes[1, 1].set_title('Product of Dimensions', fontsize=13)
    axes[1, 1].axhline(y=40, color='gray', linestyle=':', alpha=0.5, label='4×10=40')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    axes[1, 2].set_ylabel('Energy', fontsize=12)
    axes[1, 2].set_xlabel('f_in', fontsize=11)
    axes[1, 2].set_title('Energy Distribution (Complementary)', fontsize=13)
    axes[1, 2].legend(fontsize=8)
    axes[1, 2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('complementary_energy_analysis.png', dpi=150)
    print("图形已保存至: complementary_energy_analysis.png")


def test_physical_scenarios():
    """测试物理场景对应的参数范围"""
    
    print("\n" + "="*60)
    print("物理场景对应的谱维状态")
    print("="*60)
    
    scenarios = [
        ("今天宇宙 (低能平衡)", 0.0),
        ("过渡状态 (弱耦合)", 0.1),
        ("中等耦合", 0.5),
        ("强耦合 (接近黑洞)", 0.9),
        ("黑洞视界 (完全转移)", 1.0),
    ]
    
    print(f"{'场景':<25} {'f_in':<8} {'d_s_out':<10} {'d_s_in':<10} {'和':<8} {'归一化':<10}")
    print("-" * 75)
    
    for name, f in scenarios:
        d_s_out, d_s_in, _, _ = compute_spectral_flow_complementary(np.array([f]))
        d_s_out = d_s_out[0]
        d_s_in = d_s_in[0]
        sum_val = d_s_out + d_s_in
        norm_val = d_s_out/4 + d_s_in/10
        print(f"{name:<25} {f:<8.2f} {d_s_out:<10.2f} {d_s_in:<10.2f} {sum_val:<8.2f} {norm_val:<10.3f}")


def derive_conservation_formula():
    """
    尝试从数值结果反推守恒律公式
    """
    print("\n" + "="*60)
    print("守恒律公式推导")
    print("="*60)
    
    f_in = np.linspace(0.01, 0.99, 100)
    d_s_out, d_s_in, _, _ = compute_spectral_flow_complementary(f_in)
    
    # 测试各种形式的守恒律
    candidates = {
        'd_s_out + d_s_in': d_s_out + d_s_in,
        'd_s_out/4 + d_s_in/10': d_s_out/4 + d_s_in/10,
        'd_s_out × d_s_in': d_s_out * d_s_in,
        '(d_s_out-4)² + (d_s_in-4)²': (d_s_out-4)**2 + (d_s_in-4)**2,
        '(4-d_s_out)/4 + (d_s_in-4)/6': (4-d_s_out)/4 + (d_s_in-4)/6,
    }
    
    print(f"{'守恒律候选':<40} {'标准差':<12} {'是否接近常数'}")
    print("-" * 70)
    
    for name, values in candidates.items():
        std = np.std(values)
        is_constant = "是" if std < 0.5 else "否"
        print(f"{name:<40} {std:<12.4f} {is_constant}")
    
    # 找出最接近常数的
    best = min(candidates.items(), key=lambda x: np.std(x[1]))
    print(f"\n最接近守恒的候选: {best[0]}")
    print(f"标准差: {np.std(best[1]):.6f}")
    print(f"值域: [{np.min(best[1]):.3f}, {np.max(best[1]):.3f}]")


if __name__ == "__main__":
    print("="*60)
    print("互补性能量谱维流分析")
    print("="*60)
    
    # 1. 绘制谱维流图
    plot_complementary_flow()
    
    # 2. 测试物理场景
    test_physical_scenarios()
    
    # 3. 推导守恒律
    derive_conservation_formula()
    
    print("\n" + "="*60)
    print("分析完成!")
    print("="*60)
