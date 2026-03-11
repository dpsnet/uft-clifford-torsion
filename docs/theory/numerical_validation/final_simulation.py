#!/usr/bin/env python3
"""
简化但正确的早期宇宙谱维演化模拟
Simplified Correct Early Universe Simulation

物理假设:
- 早期(d_s=10): 内部空间能量主导
- GUT相变: 内部空间能量快速转化为辐射
- 后期(d_s=4): 标准辐射主导宇宙
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint

# 物理常数
M_Planck = 1.22e19  # GeV
m_planck_kg = 2.18e-8  # kg (普朗克质量)
G = 6.674e-11  # m^3 kg^-1 s^-2

# 转换因子
GeV_to_K = 1.16e13
GeV_to_s = 6.58e-25

def run_simulation(tau_0=1e-5, T_GUT=1e16):
    """
    运行简化但正确的宇宙演化模拟
    """
    print("="*60)
    print("简化正确版早期宇宙模拟")
    print("="*60)
    
    # 时间网格 (对数, 从普朗克时间到10秒)
    t = np.logspace(-44, 1, 5000)  # s
    
    # 初始条件
    # 假设普朗克时期温度 ~ M_Planck, 内部空间能量密度 ~ 6 * rho_rad (因为 d_s=10 vs 4)
    T_initial = M_Planck
    rho_rad_initial = (np.pi**2 / 30) * 106.75 * T_initial**4
    rho_int_initial = 6.0 * rho_rad_initial  # d_s=10 意味着额外6维的能量
    
    # 总能量 (守恒)
    rho_total_initial = rho_rad_initial + rho_int_initial
    
    print(f"初始温度: {T_initial:.2e} GeV")
    print(f"初始辐射能量密度: {rho_rad_initial:.2e} GeV^4")
    print(f"初始内部空间能量密度: {rho_int_initial:.2e} GeV^4")
    print(f"总能量密度: {rho_total_initial:.2e} GeV^4")
    
    # 计算演化
    T = np.zeros_like(t)
    rho_rad = np.zeros_like(t)
    rho_int = np.zeros_like(t)
    d_s = np.zeros_like(t)
    
    T[0] = T_initial
    rho_rad[0] = rho_rad_initial
    rho_int[0] = rho_int_initial
    d_s[0] = 10.0
    
    for i in range(1, len(t)):
        dt = t[i] - t[i-1]
        
        # 当前温度
        T_prev = T[i-1]
        
        # 谱维 (随温度降低从10降到4)
        if T_prev > T_GUT * 10:
            d_s[i] = 10.0
        elif T_prev < T_GUT / 10:
            d_s[i] = 4.0
        else:
            x = np.log10(T_prev / T_GUT)
            d_s[i] = 4.0 + 6.0 / (1.0 + np.exp(-2.0 * x))
        
        # 能量流动: 内部空间能量转化为辐射
        # 流动率与 (d_s - 4) 成正比
        if d_s[i] > 4.01:
            Gamma = tau_0**2 * (d_s[i] - 4) / 6.0  # 归一化
            # 内部空间能量以速率 Gamma 衰减
            decay_factor = np.exp(-Gamma * dt / GeV_to_s)
            rho_int[i] = rho_int[i-1] * decay_factor
        else:
            rho_int[i] = 0.0  # 完全转化
        
        # 辐射能量密度 = 总能量 - 内部空间能量
        # 同时考虑宇宙膨胀稀释 (a^-4)
        # 从时间推算尺度因子: t ~ 1/(2H), H ~ 1/t, a ~ t^(1/2) 对于辐射主导
        a_ratio = (t[i] / t[0])**0.5
        dilution = a_ratio**(-4)
        
        rho_rad[i] = (rho_total_initial - rho_int[i]) * dilution
        
        # 温度从辐射能量密度推导
        if rho_rad[i] > 0:
            T[i] = (rho_rad[i] * 30 / (np.pi**2 * 106.75))**0.25
        else:
            T[i] = 0.0
    
    # 哈勃率
    H = 1.0 / (2.0 * t)  # 辐射主导近似
    
    results = {
        't': t,
        'T': T,
        'rho_rad': rho_rad,
        'rho_int': rho_int,
        'd_s': d_s,
        'H': H
    }
    
    return results

def analyze_results(results):
    """分析结果"""
    t = results['t']
    T = results['T']
    rho_rad = results['rho_rad']
    rho_int = results['rho_int']
    d_s = results['d_s']
    
    print("\n关键宇宙时刻:")
    print("="*70)
    print(f"{'事件':<15} {'时间(s)':<15} {'温度(GeV)':<15} {'d_s':<10} {'ratio':<12}")
    print("="*70)
    
    targets = [
        ('GUT相变', 1e16),
        ('电弱相变', 100),
        ('QCD相变', 0.2),
        ('核合成', 1e-3),
    ]
    
    bbn_check = None
    
    for name, T_target in targets:
        idx = np.argmin(np.abs(T - T_target))
        if idx < len(t):
            ratio = rho_int[idx] / (rho_rad[idx] + 1e-100)
            print(f"{name:<15} {t[idx]:<15.2e} {T[idx]:<15.2e} {d_s[idx]:<10.2f} {ratio:<12.2e}")
            
            if name == '核合成':
                bbn_check = {
                    'T': T[idx],
                    't': t[idx],
                    'd_s': d_s[idx],
                    'ratio': ratio,
                    'f_int': rho_int[idx] / (rho_rad[idx] + rho_int[idx] + 1e-100)
                }
    
    # 核合成检验
    print("\n核合成时期检查:")
    print("="*50)
    if bbn_check:
        print(f"温度: {bbn_check['T']:.2e} GeV")
        print(f"谱维: {bbn_check['d_s']:.2f}")
        print(f"内部/辐射能量比: {bbn_check['ratio']:.2e}")
        print(f"内部空间占比: {bbn_check['f_int']:.2e}")
        
        if bbn_check['ratio'] < 1e-10:
            print("✓ 内部空间能量可忽略，与观测兼容")
            status = "PASS"
        elif bbn_check['ratio'] < 1e-5:
            print("⚠ 内部空间能量较小，可能影响不大")
            status = "MARGINAL"
        else:
            print("✗ 内部空间能量过高，需要调整参数")
            status = "FAIL"
        
        bbn_check['status'] = status
    
    return bbn_check

def plot_results(results):
    """绘制结果"""
    t = results['t']
    T = results['T']
    rho_rad = results['rho_rad']
    rho_int = results['rho_int']
    d_s = results['d_s']
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    
    # 1. 温度演化
    axes[0, 0].loglog(t, T, 'b-', linewidth=2)
    axes[0, 0].axhline(1e16, color='r', linestyle='--', alpha=0.5, label='GUT')
    axes[0, 0].axhline(1e2, color='g', linestyle='--', alpha=0.5, label='EW')
    axes[0, 0].axhline(1e-3, color='m', linestyle='--', alpha=0.5, label='BBN')
    axes[0, 0].set_xlabel('Time (s)')
    axes[0, 0].set_ylabel('Temperature (GeV)')
    axes[0, 0].set_title('Temperature Evolution')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. 谱维演化
    axes[0, 1].semilogx(t, d_s, 'g-', linewidth=2)
    axes[0, 1].axhline(4, color='r', linestyle='--', alpha=0.5)
    axes[0, 1].axhline(10, color='b', linestyle='--', alpha=0.5)
    axes[0, 1].set_xlabel('Time (s)')
    axes[0, 1].set_ylabel('Spectral Dimension d_s')
    axes[0, 1].set_title('d_s: 10 → 4')
    axes[0, 1].set_ylim([3.5, 10.5])
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. 能量密度
    axes[0, 2].loglog(t, rho_rad, 'r-', linewidth=2, label='Radiation')
    axes[0, 2].loglog(t, rho_int, 'b-', linewidth=2, label='Internal Space')
    axes[0, 2].set_xlabel('Time (s)')
    axes[0, 2].set_ylabel('Energy Density (GeV^4)')
    axes[0, 2].set_title('Energy Components')
    axes[0, 2].legend()
    axes[0, 2].grid(True, alpha=0.3)
    
    # 4. 内部空间占比
    f_int = rho_int / (rho_rad + rho_int + 1e-100)
    axes[1, 0].semilogx(t, f_int, 'm-', linewidth=2)
    axes[1, 0].set_xlabel('Time (s)')
    axes[1, 0].set_ylabel('f_int')
    axes[1, 0].set_title('Internal Space Fraction')
    axes[1, 0].grid(True, alpha=0.3)
    
    # 5. 哈勃率
    H = results['H']
    axes[1, 1].loglog(t, H, 'c-', linewidth=2)
    axes[1, 1].set_xlabel('Time (s)')
    axes[1, 1].set_ylabel('H (GeV)')
    axes[1, 1].set_title('Hubble Rate')
    axes[1, 1].grid(True, alpha=0.3)
    
    # 6. 能量密度比
    ratio = rho_int / (rho_rad + 1e-100)
    axes[1, 2].loglog(t, ratio, 'orange', linewidth=2)
    axes[1, 2].set_xlabel('Time (s)')
    axes[1, 2].set_ylabel('rho_int / rho_rad')
    axes[1, 2].set_title('Internal/Radiation Ratio')
    axes[1, 2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('final_early_universe.png', dpi=150, bbox_inches='tight')
    print("\n图像已保存: final_early_universe.png")

def parameter_scan():
    """参数扫描: 找到使核合成检验通过的 tau_0"""
    print("\n" + "="*60)
    print("参数扫描: 寻找合适的 tau_0")
    print("="*60)
    
    tau_values = [1e-5, 1e-4, 1e-3, 1e-2, 0.1, 1.0]
    
    print(f"{'tau_0':<12} {'BBN ratio':<15} {'Status':<10}")
    print("-"*40)
    
    for tau in tau_values:
        results = run_simulation(tau_0=tau, T_GUT=1e16)
        
        # 找到核合成时期
        T = results['T']
        rho_rad = results['rho_rad']
        rho_int = results['rho_int']
        
        idx_bbn = np.argmin(np.abs(T - 1e-3))
        ratio = rho_int[idx_bbn] / (rho_rad[idx_bbn] + 1e-100)
        
        if ratio < 1e-10:
            status = "PASS"
        elif ratio < 1e-5:
            status = "MARGINAL"
        else:
            status = "FAIL"
        
        print(f"{tau:<12.0e} {ratio:<15.2e} {status:<10}")

def main():
    # 主模拟
    results = run_simulation(tau_0=1e-5, T_GUT=1e16)
    
    # 分析
    bbn_check = analyze_results(results)
    
    # 绘图
    plot_results(results)
    
    print("\n模拟完成!")
    print("="*60)
    
    if bbn_check and bbn_check['status'] == "PASS":
        print("✓ 核合成检验通过!")
    else:
        print("正在运行参数扫描以找到合适的 tau_0...")
        parameter_scan()

if __name__ == "__main__":
    main()
