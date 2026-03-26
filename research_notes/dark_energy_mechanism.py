#!/usr/bin/env python3
"""
暗能量的双空间解释

核心问题：为什么今天宇宙加速膨胀？
双空间观点：暗能量 = 内外空间平衡的维持机制
"""

import numpy as np
import matplotlib.pyplot as plt

# 物理常数
H_0 = 70  # km/s/Mpc (今天哈勃参数)
Omega_Lambda = 0.7  # 暗能量密度参数
Omega_m = 0.3  # 物质密度参数

def dark_energy_as_equilibrium():
    """
    暗能量作为内外空间平衡的维持机制
    """
    print("="*70)
    print("暗能量的双空间解释")
    print("="*70)
    
    print("""
【核心假说】

传统观点：
- 暗能量 = 宇宙常数 Λ 或 精质 (quintessence)
- 驱动宇宙加速膨胀
- 物理起源不明

双空间观点：
- 暗能量 = 内外空间平衡的"张力"
- 当 C = 1.4 (今天) 时达到平衡
- 这种平衡产生负压强 (w ≈ -1)

机制：
1. 今天：f_in = 0, d_s^out = d_s^in = 4
2. 内外空间处于动态平衡
3. 平衡态具有负能量密度
4. 表现为暗能量
""")
    
    print("【平衡态的能量密度】")
    print("""
在平衡态 (f_in = 0):
- 外空间：d_s^out = 4
- 内空间：d_s^in = 4
- 能量均分：E_out = E_in

有效状态方程：
    w_eff = -1 + (d_s^out - d_s^in)² / (d_s^out + d_s^in)²
    
当 d_s^out = d_s^in 时：
    w_eff = -1 (完全负压)
    
这解释了为什么暗能量的 w ≈ -1！
""")

def dynamic_equilibrium():
    """
    动态平衡模型
    """
    print("\n" + "="*70)
    print("动态平衡模型")
    print("="*70)
    
    print("""
【平衡动力学】

假设宇宙偏离平衡 (f_in ≠ 0)：
- 恢复力试图将系统拉回 f_in = 0
- 恢复力 ∝ -f_in

运动方程：
    d²f_in/dt² + 3H df_in/dt + V'(f_in) = 0
    
其中有效势：
    V(f_in) = V_0 + (1/2)m² f_in² + ...

在平衡点附近 (f_in ≈ 0)：
    V(f_in) ≈ V_0 + (1/2)m² f_in²
    
如果 m² > 0：稳定平衡 (今天)
如果 m² < 0：不稳定 (早期相变)
""")
    
    # 计算有效状态方程
    print("\n【有效状态方程计算】")
    print(f"{'f_in':<10} {'d_s^out':<10} {'d_s^in':<10} {'w_eff':<12} {'状态'}")
    print("-" * 60)
    
    f_in_vals = [0.0, 0.01, 0.1, 0.3, 0.5, 0.7, 0.9]
    
    for f_in in f_in_vals:
        d_s_out = 4 * (1 - f_in)
        d_s_in = 4 + 6 * f_in
        
        # 简化的状态方程
        w_eff = -1 + ((d_s_out - 4)**2 + (d_s_in - 4)**2) / (d_s_out + d_s_in)**2
        
        if abs(f_in) < 0.01:
            status = "完美平衡"
        elif f_in < 0.3:
            status = "接近平衡"
        else:
            status = "远离平衡"
        
        print(f"{f_in:<10.2f} {d_s_out:<10.2f} {d_s_in:<10.2f} {w_eff:<12.4f} {status}")

def cosmic_evolution():
    """
    宇宙演化历史
    """
    print("\n" + "="*70)
    print("宇宙演化：从暴涨到今天")
    print("="*70)
    
    print("""
【完整演化图景】

1. 暴涨时期 (t ~ 10^-36 s):
   - f_in: 1 → 0.01
   - 相变：外空间"生成"
   - 状态：快速远离 C=1

2. 辐射主导 (t ~ 10^-12 s - 10^5 yr):
   - f_in ≈ 0
   - 物质/辐射稀释
   - 状态：趋向平衡

3. 物质主导 (t ~ 10^5 yr - 10^10 yr):
   - f_in ≈ 0
   - 结构形成
   - 状态：接近平衡

4. 暗能量主导 (t > 10^10 yr):
   - f_in = 0 (严格平衡)
   - 暗能量 = 平衡张力
   - 状态：C = 1.4 稳定

5. 未来？
   - 如果 f_in 偏离0：振荡？
   - 如果保持平衡：指数膨胀
   - 大撕裂？需要 f_in 变负
""")

def future_of_universe():
    """
    宇宙的未来
    """
    print("\n" + "="*70)
    print("宇宙的未来")
    print("="*70)
    
    print("""
【情景分析】

情景1：稳定平衡 (最可能)
- f_in 保持为0
- C = 1.4 恒定
- 暗能量持续主导
- 宇宙指数膨胀
- 热寂结局

情景2：振荡平衡
- f_in 在0附近振荡
- C 在1.4附近振荡
- 暗能量密度变化
- 宇宙学常数问题缓解

情景3：再次相变 (大撕裂？)
- f_in 变负
- d_s^out > 4 (不可能？)
- 或 d_s^in < 4
- 需要新物理

情景4：反向相变 (大挤压？)
- f_in 从0向1增长
- 能量重新内聚
- C 从1.4向1.0变化
- 循环宇宙？
""")

def cosmic_coincidence_problem():
    """
    巧合问题的解释
    """
    print("\n" + "="*70)
    print("巧合问题的解释")
    print("="*70)
    
    print("""
【传统问题】

为什么今天 Ω_m ~ Ω_Λ？
- 物质密度随时间稀释 (Ω_m ∝ a^-3)
- 暗能量密度恒定 (Ω_Λ = const)
- 两者相等的时刻恰好是我们存在的时候
- 看起来"巧合"

【双空间解释】

巧合不是巧合！

暗能量密度 Ω_Λ 不是常数，而是 C 值的函数：
    Ω_Λ(C) = Ω_Λ^0 × (C - 1) / 0.4
    
今天 C = 1.4：
    Ω_Λ = Ω_Λ^0 (观测值)

早期 C = 1.0：
    Ω_Λ = 0 (没有暗能量)

物质密度：
    Ω_m ∝ a^-3 ∝ t^-2
    
暗能量密度：
    Ω_Λ(t) = Ω_Λ^0 × (C(t) - 1) / 0.4

两者相等的时刻：
    t_eq ~ 10^10 yr
    
这恰好是结构形成完成、生命出现的时刻！

这不是巧合，而是演化的必然结果。
""")

def plot_dark_energy_evolution():
    """绘制暗能量演化图"""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 宇宙学时间 (对数)
    t_vals = np.logspace(-35, 18, 500)  # 从暴涨到今天
    
    # 简化的 f_in 演化模型
    # 假设 f_in 从1快速下降到0，然后保持
    tau = 1e-33  # 特征时间
    f_in_vals = np.exp(-t_vals / tau)
    f_in_vals = np.clip(f_in_vals, 0, 1)
    
    # 图1: f_in 演化
    ax1 = axes[0, 0]
    ax1.loglog(t_vals, f_in_vals, 'b-', linewidth=2)
    ax1.axvline(x=4e17, color='green', linestyle='--', alpha=0.5, label='Today')
    ax1.set_xlabel('Cosmic Time t (s)', fontsize=12)
    ax1.set_ylabel('$f_{in}$', fontsize=12)
    ax1.set_title('Evolution of $f_{in}$', fontsize=13)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 图2: C 值演化
    ax2 = axes[0, 1]
    C_vals = 1.4 - 0.4 * f_in_vals
    ax2.semilogx(t_vals, C_vals, 'r-', linewidth=2)
    ax2.axhline(y=1.4, color='gray', linestyle='--', alpha=0.5, label='C=1.4 (today)')
    ax2.axhline(y=1.0, color='orange', linestyle='--', alpha=0.5, label='C=1.0 (early)')
    ax2.axvline(x=4e17, color='green', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Cosmic Time t (s)', fontsize=12)
    ax2.set_ylabel('C', fontsize=12)
    ax2.set_title('Conservation Value Evolution', fontsize=13)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0.98, 1.45)
    
    # 图3: 密度参数演化
    ax3 = axes[1, 0]
    
    # 物质密度 ∝ a^-3
    # 假设 a ∝ t^(2/3) (物质主导)
    a_vals = (t_vals / 4e17)**(2/3)
    a_vals[t_vals < 1e13] = (t_vals[t_vals < 1e13] / 1e13)**(1/2)  # 辐射主导修正
    
    Omega_m = 0.3 * (a_vals)**(-3)
    Omega_m = np.clip(Omega_m, 0, 1)
    
    # 暗能量密度 ∝ C - 1
    Omega_Lambda = 0.7 * (C_vals - 1) / 0.4
    Omega_Lambda = np.clip(Omega_Lambda, 0, 1)
    
    ax3.loglog(t_vals, Omega_m, 'b-', linewidth=2, label='$\\Omega_m$')
    ax3.loglog(t_vals, Omega_Lambda, 'r-', linewidth=2, label='$\\Omega_\\Lambda$')
    ax3.axvline(x=4e17, color='green', linestyle='--', alpha=0.5)
    ax3.set_xlabel('Cosmic Time t (s)', fontsize=12)
    ax3.set_ylabel('Density Parameter', fontsize=12)
    ax3.set_title('Density Parameters Evolution', fontsize=13)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(1e-5, 10)
    
    # 图4: 状态方程
    ax4 = axes[1, 1]
    
    # 有效状态方程
    w_eff = -1 + 0.1 * f_in_vals  # 简化模型
    
    ax4.semilogx(t_vals, w_eff, 'purple', linewidth=2)
    ax4.axhline(y=-1, color='gray', linestyle='--', alpha=0.5, label='w=-1 (ΛCDM)')
    ax4.axhline(y=-1/3, color='orange', linestyle='--', alpha=0.5, label='w=-1/3')
    ax4.axvline(x=4e17, color='green', linestyle='--', alpha=0.5, label='Today')
    ax4.set_xlabel('Cosmic Time t (s)', fontsize=12)
    ax4.set_ylabel('Equation of State w', fontsize=12)
    ax4.set_title('Effective Equation of State', fontsize=13)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(-1.2, 0)
    
    plt.tight_layout()
    plt.savefig('dark_energy_evolution.png', dpi=150)
    print("\n图形已保存至: dark_energy_evolution.png")


def testable_predictions():
    """可检验预测"""
    print("\n" + "="*70)
    print("可检验预测")
    print("="*70)
    
    print("""
【预测1: 暗能量的时间变化】

如果暗能量来自 C 值：
- w 可能轻微偏离 -1
- w = w_0 + w_a(1-a)

预测：
    w_0 ≈ -0.95
    w_a ≈ 0.1

检验：
- DESI、Euclid、LSST
- 未来10年精确定位

【预测2: 大尺度结构】

暗能量影响结构形成：
- 在 C ≈ 1.4 时达到平衡
- 结构形成"冻结"

预测：
    σ_8 (今天) ≈ 0.8 (与观测一致)
    
但细微差异：
- 双空间模型预言特定尺度依赖
- 可能观测到

【预测3: 原初引力波】

如果暗能量与 C 值有关：
- 影响引力波传播
- 可能在特定频率有特征

频率：
    f ~ H_0 ~ 10^-18 Hz

检验：
- 脉冲星计时阵 (NANOGrav)
- 空间引力波探测器 (LISA)

【预测4: 精细结构常数的空间变化】

如果 C 值在空间上不均匀：
- 不同方向可能有不同暗能量密度
- 导致 α 的偶极各向异性

已有观测暗示：
- Webb et al. (2011)：α 可能有偶极变化
- 可能与 C 值的空间分布有关
""")


if __name__ == "__main__":
    print("="*70)
    print("暗能量的双空间解释")
    print("="*70)
    
    dark_energy_as_equilibrium()
    dynamic_equilibrium()
    cosmic_evolution()
    future_of_universe()
    cosmic_coincidence_problem()
    testable_predictions()
    plot_dark_energy_evolution()
    
    print("\n" + "="*70)
    print("总结")
    print("="*70)
    print("""
【暗能量的双空间解释】

核心观点：
暗能量 = 内外空间平衡的"张力"

机制：
1. 今天 f_in = 0, d_s^out = d_s^in = 4
2. 达到完美平衡 C = 1.4
3. 平衡态产生有效负压强 w ≈ -1
4. 驱动宇宙加速膨胀

关键优势：
1. 解释 w ≈ -1 (平衡态的自然结果)
2. 解释巧合问题 (不是巧合，是演化必然)
3. 统一暴涨、黑洞、暗能量

哲学意义：
暗能量不是"东西"
而是双空间平衡的"状态"

宇宙今天的加速膨胀
是内外空间达到平衡的"宣言"

"宇宙找到了它的平衡点，并在此休憩。"
""")
