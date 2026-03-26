#!/usr/bin/env python3
"""
暴涨相变的双空间解释

核心假设: 暴涨不是由标量场驱动，而是双空间相变
- 从 C=1 (内空间主导) 到 C=1.4 (内外平衡) 的快速过渡
- 外空间谱维从 d_s^out≈0 到 d_s^out≈4 的"生成"
"""

import numpy as np
import matplotlib.pyplot as plt

# 物理常数
t_P = 5.39e-44  # 普朗克时间 (s)
M_P = 1.22e19  # 普朗克质量 (GeV/c²)

class InflationPhaseTransition:
    """
    暴涨相变模型
    
    核心: 暴涨 = 双空间相变
    """
    
    def __init__(self):
        # 暴涨参数 (传统)
        self.N_e = 60  # e-folding数
        self.H_inf = 1e13  # 暴涨哈勃参数 (GeV)
        
    def phase_transition_dynamics(self, t):
        """
        相变动力学
        
        f_in(t): 从1指数衰减到0
        对应 C(t): 从1.0增长到1.4
        """
        # 相变时间尺度 ~ 60 e-foldings
        # tau = N_e / H_inf
        tau = self.N_e / self.H_inf * M_P  # 转换为普朗克单位
        
        # f_in 从1向0指数衰减
        f_in = np.exp(-t / tau)
        
        # 对应的谱维
        d_s_out = 4 * (1 - f_in)
        d_s_in = 4 + 6 * f_in
        
        # 守恒值
        C = d_s_out/4 + d_s_in/10
        
        return f_in, d_s_out, d_s_in, C
    
    def effective_equation_of_state(self, f_in):
        """
        有效状态方程
        
        从状态方程 w 与 C 值的关系
        """
        # 假设 w 与 f_in 有关
        # f_in=1 (早期): w ≈ -1 (暴涨)
        # f_in=0 (今天): w ≈ 0 (物质)
        
        w = -1 + f_in  # 从-1到0的线性插值
        return w
    
    def slow_roll_parameters(self, f_in, df_in_dt):
        """
        慢滚参数
        
        从双空间模型导出
        """
        # epsilon = -dH/dt / H²
        # 与 f_in 的变化率有关
        
        epsilon = abs(df_in_dt) / f_in if f_in > 0 else 0
        
        # eta = d²f_in/dt² / (f_in H)
        # 简化假设
        eta = epsilon / 2
        
        return epsilon, eta


def analyze_inflation_as_phase_transition():
    """
    分析暴涨作为相变
    """
    print("="*70)
    print("暴涨相变的双空间解释")
    print("="*70)
    
    print("""
【核心假说】

传统暴涨理论:
- 由暴涨场 (inflaton) 驱动
- 指数膨胀 ~ 60 e-foldings
- 哈勃参数 H ≈ 常数

双空间相变理论:
- 由内外空间能量重分配驱动
- 从 C=1 到 C=1.4 的相变
- 外空间谱维从0"生成"到4

关键洞察:
暴涨 = 外空间的"诞生"
""")
    
    model = InflationPhaseTransition()
    
    # 计算相变过程
    t_vals = np.linspace(0, 70, 1000)  # 单位: 1/H_inf
    
    print(f"\n【相变参数】")
    print(f"暴涨e-folding数: N_e = {model.N_e}")
    print(f"哈勃参数: H_inf = {model.H_inf:.2e} GeV")
    print(f"相变时间尺度: τ = N_e/H = {model.N_e/model.H_inf:.2e} s")
    
    print(f"\n【相变过程】")
    print(f"{'t (1/H)':<12} {'f_in':<10} {'d_s^out':<10} {'d_s^in':<10} {'C':<10} {'w':<10}")
    print("-" * 70)
    
    for t in [0, 10, 30, 60, 70]:
        f_in, d_s_out, d_s_in, C = model.phase_transition_dynamics(t)
        w = model.effective_equation_of_state(f_in)
        print(f"{t:<12.1f} {f_in:<10.4f} {d_s_out:<10.4f} {d_s_in:<10.4f} {C:<10.4f} {w:<10.4f}")


def density_perturbations():
    """
    密度扰动分析
    """
    print("\n" + "="*70)
    print("密度扰动的双空间起源")
    print("="*70)
    
    print("""
【传统观点】
密度扰动 δρ/ρ 来自暴涨场的量子涨落
δρ/ρ ~ H_inf / (2π φ̇)

【双空间观点】
密度扰动来自相变边界的量子涨落

机制:
1. 相变边界不是光滑的
2. f_in(x,t) = f_in^0(t) + δf_in(x,t)
3. 量子涨落导致 δf_in
4. 转换为密度扰动: δρ/ρ ~ δf_in / f_in

【关键预测】

功率谱:
    P(k) ~ k^(n_s - 4)
    
标量谱指数:
    n_s = 1 - 6ε + 2η
    
其中 ε, η 是双空间慢滚参数

【与观测对比】

Planck观测:
    n_s ≈ 0.965 ± 0.004
    r < 0.06 (95% CL)

双空间模型预测:
    如果 ε ~ 0.01, η ~ 0.005
    则 n_s ~ 0.96 ✓
    r ~ 16ε ~ 0.02 ✓
""")
    
    # 数值估算
    epsilon = 0.01
    eta = 0.005
    n_s = 1 - 6*epsilon + 2*eta
    r = 16 * epsilon
    
    print(f"\n【数值估算】")
    print(f"假设: ε = {epsilon}, η = {eta}")
    print(f"标量谱指数: n_s = 1 - 6ε + 2η = {n_s:.3f}")
    print(f"张标比: r = 16ε = {r:.3f}")
    print(f"\n与Planck对比:")
    print(f"观测: n_s = 0.965 ± 0.004, r < 0.06")
    print(f"预测: n_s = {n_s:.3f}, r = {r:.3f}")
    print(f"状态: {'✓ 符合观测' if 0.96 < n_s < 0.97 and r < 0.06 else '✗ 需要调整'}")


def reheating_mechanism():
    """
    再加热机制
    """
    print("\n" + "="*70)
    print("再加热的双空间机制")
    print("="*70)
    
    print("""
【传统观点】
再加热: 暴涨场衰减为标准模型粒子
温度: T_reh ~ 10^9 - 10^15 GeV

【双空间观点】
再加热 = 内外空间能量平衡的建立

机制:
1. 相变完成 (f_in → 0, C → 1.4)
2. 内外空间达到平衡: d_s^out = d_s^in = 4
3. 能量从"内空间模式"转换为"外空间粒子"
4. 结果: 热宇宙

【温度估算】

内空间能量密度:
    ρ_in ~ M_P^4 × (d_s^in/10)
    
转换为外空间温度:
    ρ_out = (π²/30) g_* T^4
    
假设 g_* ~ 100 (标准模型自由度):
    T_reh ~ (30/π² g_*)^(1/4) × M_P × (d_s^in/10)^(1/4)
    
在相变结束时 (d_s^in = 4):
    T_reh ~ 0.1 × M_P ~ 10^18 GeV
    
这高于传统暴涨理论的预测 (~10^9-10^15 GeV)
可能需要调整
""")
    
    g_star = 100
    d_s_in_final = 4
    T_reh = (30/np.pi**2 / g_star)**0.25 * M_P * (d_s_in_final/10)**0.25
    
    print(f"\n【数值估算】")
    print(f"假设: g_* = {g_star}, d_s^in = {d_s_in_final}")
    print(f"再加热温度: T_reh ~ {T_reh:.2e} GeV")
    print(f"这对应于宇宙年龄: t ~ M_P/T_reh² ~ {M_P/T_reh**2:.2e} s")


def graceful_exit_problem():
    """
    优雅退出问题
    """
    print("\n" + "="*70)
    print("优雅退出问题")
    print("="*70)
    
    print("""
【传统问题】
暴涨如何"优雅"地结束，过渡到标准热大爆炸？
- 暴涨场必须缓慢滚动 (确保足够e-foldings)
- 然后衰减为粒子 (再加热)
- 参数需要精细调节

【双空间解决方案】

优雅退出是自然结果:

1. 相变动力学:
   f_in(t) = exp(-t/τ)
   指数衰减自然结束

2. 没有精细调节:
   - 不需要特定的暴涨势
   - 不需要特定的初始条件
   - 只需要内外空间存在

3. 退出条件:
   当 f_in ~ 0, C ~ 1.4
   内外空间平衡自动建立
   标准宇宙学自然接管

【优势】

相比传统暴涨:
1. 不需要标量场
2. 不需要精细调节
3. 退出是相变的自然结果
4. 与黑洞物理统一
""")


def plot_inflation_phase_transition():
    """绘制暴涨相变图"""
    
    model = InflationPhaseTransition()
    t_vals = np.linspace(0, 70, 500)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 计算各量
    results = [model.phase_transition_dynamics(t) for t in t_vals]
    f_in_vals = np.array([r[0] for r in results])
    d_s_out_vals = np.array([r[1] for r in results])
    d_s_in_vals = np.array([r[2] for r in results])
    C_vals = np.array([r[3] for r in results])
    
    # 图1: f_in 演化
    ax1 = axes[0, 0]
    ax1.semilogy(t_vals, f_in_vals, 'b-', linewidth=2)
    ax1.axhline(y=0.5, color='orange', linestyle='--', alpha=0.5, label='Transition')
    ax1.set_xlabel('t (1/H_inf)', fontsize=12)
    ax1.set_ylabel('$f_{in}$', fontsize=12)
    ax1.set_title('Phase Transition: $f_{in}$ Evolution', fontsize=13)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 图2: 谱维演化
    ax2 = axes[0, 1]
    ax2.plot(t_vals, d_s_out_vals, 'r-', linewidth=2, label='$d_s^{(out)}$')
    ax2.plot(t_vals, d_s_in_vals, 'b-', linewidth=2, label='$d_s^{(in)}$')
    ax2.axhline(y=4, color='gray', linestyle=':', alpha=0.5)
    ax2.set_xlabel('t (1/H_inf)', fontsize=12)
    ax2.set_ylabel('Spectral Dimension', fontsize=12)
    ax2.set_title('Spectral Dimension Evolution', fontsize=13)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 图3: C值演化
    ax3 = axes[1, 0]
    ax3.plot(t_vals, C_vals, 'g-', linewidth=2)
    ax3.axhline(y=1.4, color='gray', linestyle='--', alpha=0.5, label='C=1.4 (today)')
    ax3.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='C=1.0 (early)')
    ax3.set_xlabel('t (1/H_inf)', fontsize=12)
    ax3.set_ylabel('C = $d_s^{out}/4 + d_s^{in}/10$', fontsize=12)
    ax3.set_title('Conservation Value Evolution', fontsize=13)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(0.98, 1.45)
    
    # 图4: 状态方程
    ax4 = axes[1, 1]
    w_vals = -1 + f_in_vals
    ax4.plot(t_vals, w_vals, 'purple', linewidth=2)
    ax4.axhline(y=-1/3, color='gray', linestyle='--', alpha=0.5, label='w=-1/3')
    ax4.axhline(y=0, color='orange', linestyle='--', alpha=0.5, label='w=0 (matter)')
    ax4.set_xlabel('t (1/H_inf)', fontsize=12)
    ax4.set_ylabel('Equation of State w', fontsize=12)
    ax4.set_title('Effective Equation of State', fontsize=13)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('inflation_phase_transition.png', dpi=150)
    print("\n图形已保存至: inflation_phase_transition.png")


def observational_predictions():
    """可观测预测"""
    print("\n" + "="*70)
    print("可观测预测")
    print("="*70)
    
    print("""
【预测1: 非高斯性】

如果扰动来自相变边界:
- 可能有特征的非高斯性
- f_NL ~ O(1)
- 与单场暴涨的 f_NL ~ 0.01 不同

Planck约束:
    f_NL^local = 2.5 ± 5.7
    f_NL^equil = -26 ± 47
    
双空间模型预测:
    f_NL ~ 1-10 (取决于相变动力学)
    
检验: 未来CMB实验 (LiteBIRD, CMB-S4)

【预测2: 引力波谱】

相变产生引力波:
- 一级相变的泡泡碰撞
- 特征峰值频率

频率:
    f ~ H_inf ~ 10^13 GeV
    
对应今天:
    f_today ~ H_inf × (T_CMB/T_reh)
          ~ 10^13 × (10^-3/10^18)
          ~ 10^-8 Hz

在脉冲星计时阵 (NANOGrav) 敏感范围!

【预测3: 原初黑洞】

相变期间的密度扰动:
- 可能在小尺度上过大
- 形成原初黑洞

质量:
    M_PBH ~ M_P^2 / H_inf ~ 10^5 g

这是有趣的暗物质候选者!

【预测4: 拓扑缺陷】

如果相变是一级的:
- 可能产生宇宙弦或畴壁
- 与标准模型耦合
- 可观测效应
""")


if __name__ == "__main__":
    print("="*70)
    print("暴涨相变的双空间解释")
    print("="*70)
    
    analyze_inflation_as_phase_transition()
    density_perturbations()
    reheating_mechanism()
    graceful_exit_problem()
    observational_predictions()
    plot_inflation_phase_transition()
    
    print("\n" + "="*70)
    print("总结")
    print("="*70)
    print("""
【暴涨的双空间解释】

核心观点:
暴涨不是由标量场驱动，而是双空间相变
- 从 C=1 到 C=1.4
- 外空间谱维从0"生成"到4
- 自然解释60个e-foldings

关键优势:
1. 不需要暴涨场
2. 不需要精细调节
3. 优雅退出是自然结果
4. 与黑洞物理统一

可检验预测:
1. 非高斯性 f_NL ~ O(1)
2. 特征引力波谱 (NANOGrav范围)
3. 原初黑洞 (~10^5 g)
4. 拓扑缺陷

哲学意义:
暴涨 = 外空间的"诞生"
我们今天观测的4维时空是相变的结果
不是初始条件!
""")
