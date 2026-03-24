#!/usr/bin/env python3
"""
黑洞熵阶段C - Day 2: 弯曲时空中的量子场论

研究目标: Hartle-Hawking真空、模式展开与Hawking辐射
"""

import numpy as np
import sympy as sp
from sympy import symbols, Function, sqrt, exp, simplify, diff, integrate, oo, I, pi, cos, sin

# 设置符号计算
sp.init_printing()

class QFTinCurvedSpacetime:
    """
    弯曲时空中的量子场论
    
    为扭转场在黑洞背景中的量子化建立框架
    """
    
    def __init__(self, M=1):
        """
        初始化
        
        参数:
            M: 黑洞质量
        """
        self.M = M
        self.r_s = 2 * M
        self.kappa = 1 / (4 * M)  # 表面引力
        
    def free_field_flat_spacetime(self):
        """
        平直时空中的自由标量场 (回顾)
        """
        print("="*70)
        print("平直时空中的自由标量场 (回顾)")
        print("="*70)
        
        print("""
作用量:
    S = ∫ d⁴x √(-g) [-(1/2)g^μν ∂_μφ ∂_νφ - (1/2)m²φ²]
    
在平直时空 (g_μν = η_μν):
    S = ∫ d⁴x [-(1/2)∂_μφ ∂^μφ - (1/2)m²φ²]

运动方程 (Klein-Gordon):
    (□ + m²)φ = 0
    
其中 □ = ∂_μ∂^μ = -∂_t² + ∇² 是达朗贝尔算符。

模式展开:
    φ(t,x) = ∫ d³k/(2π)³ (1/√(2ω_k)) [a_k e^(-iω_kt+ik·x) + a_k† e^(iω_kt-ik·x)]
    
其中 ω_k = √(k² + m²) 是能量。

产生湮灭算符:
    [a_k, a_k'†] = (2π)³ δ³(k - k')
    
真空态 |0⟩ 定义为:
    a_k |0⟩ = 0 对所有 k

粒子解释:
    a_k† |0⟩ = |1_k⟩ 产生一个动量为 k 的粒子
        """)
        
    def free_field_curved_spacetime(self):
        """
        弯曲时空中的自由标量场
        """
        print("\n" + "="*70)
        print("弯曲时空中的自由标量场")
        print("="*70)
        
        print("""
在弯曲时空中，度规 g_μν(x) 依赖于位置。

作用量:
    S = ∫ d⁴x √(-g) [-(1/2)g^μν ∂_μφ ∂_νφ - (1/2)m²φ² - (1/2)ξRφ²]
    
其中:
- √(-g) 是体积元
- R 是Ricci标量
- ξ 是耦合常数 (ξ = 0: 最小耦合, ξ = 1/6: 共形耦合)

运动方程:
    (□ + m² + ξR)φ = 0
    
其中 □ = (1/√(-g)) ∂_μ(√(-g) g^μν ∂_ν) 是弯曲时空中的达朗贝尔算符。

关键问题: 没有全局的类时Killing矢量!

在平直时空中:
- ∂_t 是类时Killing矢量
- ω = -p_μ ξ^μ 定义了正频率
- 所有惯性观测者都同意正频率的定义

在弯曲时空中:
- 一般不存在全局类时Killing矢量
- 不同的观测者可能有不同的"正频率"定义
- 粒子数不是普适的!

这导致了:
1. 粒子产生 (Bogoliubov变换)
2. 霍金辐射
3. Unruh效应
        """)
        
    def hartle_hawking_vacuum(self):
        """
        Hartle-Hawking真空
        """
        print("\n" + "="*70)
        print("Hartle-Hawking真空")
        print("="*70)
        
        print(f"""
定义:
Hartle-Hawking真空 |HH⟩ 是Schwarzschild黑洞背景中，在视界上和无穷远处都是正则的量子态。

关键性质:
1. 在视界 (r → r_s) 处正则
2. 在无穷远 (r → ∞) 处正则
3. 对应于热平衡态，温度 T_H = ℏκ/(2π) = {self.kappa/(2*np.pi):.6f} (当 M = {self.M})

物理解释:
- Hartle-Hawking真空描述了与热浴平衡的黑洞
- 一个包裹黑洞的盒子，内壁温度 T_H
- 与奇点处方 (singularity regularization) 相关

与Boulware真空 |B⟩ 的区别:
- Boulware真空: 在无穷远处是"空"的 (类似平直时空真空)
- 但在视界处发散!
- 不是物理态 (能量密度在视界处发散)

与Unruh真空 |U⟩ 的区别:
- Unruh真空: 在视界处正则，在无穷远处描述出射粒子
- 描述坍缩黑洞晚期 (蒸发阶段)

HH真空的特殊性:
HH真空是唯一的、在最大延拓上处处正则的态。

数学构造:
在Kruskal坐标 (覆盖整个最大延拓) 中:
    ds² = -(32M³/r) e^(-r/2M) dU dV + r²dΩ²
    
其中:
    U = -e^(-u/4M) (入射 null 坐标)
    V = e^(v/4M)  (出射 null 坐标)
    u = t - r_*
    v = t + r_*

在Kruskal坐标中，视界 U=0 或 V=0 是正则的。
Hartle-Hawking模式是 U 和 V 的函数 (而非 u 和 v)。
        """)
        
    def mode_expansion_schwarzschild(self):
        """
        Schwarzschild时空中的模式展开
        """
        print("\n" + "="*70)
        print("Schwarzschild时空中的模式展开")
        print("="*70)
        
        print("""
球对称简化:
利用球对称性，可以分离变量:
    φ(t,r,θ,φ) = Σ_{l,m} (1/r) ψ_{ωlm}(r) Y_{lm}(θ,φ) e^(-iωt)

径向方程 (Klein-Gordon方程的径向部分):
    d²ψ/dr_*² + [ω² - V_l(r)]ψ = 0
    
其中 r_* 是乌龟坐标。

有效势 V_l(r):
    V_l(r) = f(r)[l(l+1)/r² + (2M/r³) + m²]
    
其中 f(r) = 1 - 2M/r。

有效势的性质:
1. 在视界 (r → r_s): V_l(r) → 0
2. 在无穷远 (r → ∞): V_l(r) → m² (质量项)
3. 在中间: 势垒

模式分类:
1. 传播模式 (ω² > V_max): 可以穿透势垒
2. 束缚模式 (ω² < V_max): 在势垒附近振荡

边界条件:
在视界附近 (r_* → -∞):
    ψ ~ e^(-iωt) [A_in e^(-iωr_*) + A_out e^(iωr_*)]
    
物理意义:
- e^(-iωr_*): 入射波 (向视界传播)
- e^(iωr_*): 出射波 (从视界发出)

在无穷远处 (r_* → +∞):
    ψ ~ e^(-iωt) [B_in e^(-iω_∞r_*) + B_out e^(iω_∞r_*)]
    
其中 ω_∞ = √(ω² - m²)。

物理意义:
- 对于m=0: ω_∞ = ω
- 入射波来自无穷远
- 出射波去向无穷远
        """)
        
    def bogoliubov_transformations(self):
        """
        Bogoliubov变换与粒子产生
        """
        print("\n" + "="*70)
        print("Bogoliubov变换与粒子产生")
        print("="*70)
        
        print("""
问题设定:
假设有两个不同的模式展开:

展开1 (例如, 晚期观测者):
    φ = ∫ d³k [a_k u_k + a_k† u_k*]

展开2 (例如, 早期观测者):
    φ = ∫ d³k' [b_k' v_k' + b_k'† v_k'*]

其中 u_k 和 v_k' 都是Klein-Gordon方程的解，但对应不同的"正频率"定义。

Bogoliubov变换:
由于两组模式都完备，可以相互展开:
    u_k = ∫ d³k' [α_kk' v_k' + β_kk' v_k'*]
    
其中 α_kk' 和 β_kk' 是Bogoliubov系数。

逆变换:
    v_k' = ∫ d³k [α_kk'* u_k - β_kk' u_k*]

产生湮灭算符的关系:
    b_k' = ∫ d³k [α_kk'* a_k + β_kk' a_k†]
    
这就是Bogoliubov变换!

粒子数期望:
如果早期真空 |0⟩_a 定义为 a_k |0⟩_a = 0，
那么在晚期观测者看来，粒子数是:
    ⟨n_k'⟩ = ⟨0|_a b_k'† b_k' |0⟩_a = ∫ d³k |β_kk'|²

物理意义:
如果 β ≠ 0，早期真空在晚期看来是"有粒子"的!
这就是粒子产生。

霍金辐射的来源:
- 早期 (坍缩前): Boulware真空 (类平直)
- 晚期 (视界形成后): Unruh/Hartle-Hawking模式
- Bogoliubov变换给出 β ≠ 0
- 因此黑洞辐射粒子!
        """)
        
    def hawking_radiation_derivation(self):
        """
        Hawking辐射的推导
        """
        print("\n" + "="*70)
        print("Hawking辐射的推导")
        print("="*70)
        
        print(f"""
Hawking原始推导 (1974):

考虑坍缩恒星形成黑洞的过程:

1. 早期 (t → -∞):
   - 空间渐近平直
   - 场处于真空态 (Boulware-like)
   - 没有粒子

2. 坍缩过程中:
   - 恒星表面收缩
   - 光锥倾斜
   - 最后出射的射线在视界处"冻结"

3. 晚期 (t → +∞):
   - 黑洞形成
   - 视界处的模式高度红移
   - Bogoliubov变换给出 β ≠ 0

关键计算:
追踪从视界附近逃逸到无穷远的模式。

在视界附近 (r_* → -∞):
    模式频率 (局域): ω_loc ~ ω e^(κr_*)
    
其中 κ = {self.kappa:.4f} 是表面引力。

当模式向外传播:
- 引力红移
- 频率降低: ω_∞ = ω_loc f(r)^(1/2) ≈ ω_loc e^(κr_*)

因此:
    ω_∞ ~ ω e^(κr_*) e^(κr_*) = ω e^(2κr_*)
    
等等...让我们更仔细。

正确的分析:
模式在视界附近的Kruskal坐标中展开:
    出射模式 ~ e^(-iωU)
    
其中 U = -e^(-κu) 是Kruskal入射坐标。

在晚期 (u → ∞):
    U ~ -e^(-κu) → 0^-
    
模式高度振荡。

Bogoliubov系数:
通过匹配视界模式和无穷远模式，Hawking发现:
    |β|² = 1/(e^(2πω/κ) - 1) = 1/(e^(ω/T_H) - 1)
    
其中 T_H = κ/(2π) = {self.kappa/(2*np.pi):.6f}!

这正是普朗克分布!

霍金温度:
    T_H = ℏκ/(2π) = ℏ/(8πM)

物理意义:
黑洞辐射热谱，温度 T_H。
这是量子效应在弯曲时空中的体现。
        """)
        
    def stress_tensor_and_back_reaction(self):
        """
        应力张量与反作用
        """
        print("\n" + "="*70)
        print("应力张量与反作用")
        print("="*70)
        
        print("""
量子场的应力张量:

正则化方法 (Point-splitting, Adiabatic regularization等):
    ⟨T_μν⟩ = lim_{x'→x} D_μν(x,x') [G(x,x') - G_sing(x,x')]
    
其中 G(x,x') 是Green函数，G_sing 是发散部分。

在Hartle-Hawking真空中:
    ⟨T_μν⟩_HH = diag(-ρ, p_r, p_θ, p_φ)
    
能量密度 ρ:
    ρ = (π²/30) T_H⁴ × (修正项)
    
类似于黑体辐射!

反作用问题:
量子场的能量动量影响背景几何:
    G_μν = 8πG ⟨T_μν⟩

这导致:
1. 黑洞蒸发 (质量减小)
2. 视界收缩
3. 温度升高 (T_H ∝ 1/M)
4. 正反馈: 蒸发加速

蒸发时间:
    τ_evap ~ M³/(ℏc⁴/G²) ~ (M/M_Planck)³ t_Planck
    
对于恒星质量黑洞:
    τ_evap ~ 10⁶⁷ 年 >> 宇宙年龄

对于原初黑洞 (M ~ 10¹² kg):
    τ_evap ~ 10¹⁰ 年 (可能正在蒸发!)

信息悖论:
如果黑洞完全蒸发，纯态 → 混合态?
这违反了量子力学的幺正性!

CTUFT的解决方案:
- 扭转场模式存储信息
- 蒸发过程中信息逐渐释放
- 信息通过霍金辐射编码
- 非局域效应 (ER=EPR?)
        """)
        
    def mode_expansion_torsion_field(self):
        """
        扭转场的模式展开
        """
        print("\n" + "="*70)
        print("扭转场在黑洞背景中的模式展开")
        print("="*70)
        
        print("""
扭转场的运动方程:

在弯曲时空中，扭转场满足推广的场方程:
    D^μ D_μ T^α_{νρ} - R^α_{μνρ} T^μ + ... = 0
    
其中 D_μ 是协变导数，R^α_{μνρ} 是Riemann张量。

模式展开:
类似于标量场，可以展开为:
    T^α_{μν}(t,r,θ,φ) = Σ_{ω,l,m,λ} N_ω [a_{ωlλ} u_{ωlλ} + a_{ωlλ}† u_{ωlλ}*]

其中 λ 标记极化态。

边界条件:
1. 视界处: 正则性条件 (类似于HH真空)
2. 无穷远处: 出射波条件

谱维的影响:
在视界附近，高能模式感受到的"有效维度"是 d_s → 10。
这增加了:
1. 态密度
2. 模式数
3. 熵

关键洞见:
扭转场的谱维流动 d_s = 4 → 10 提供了正确的态密度标度，
导致熵 S ~ A (面积律) 而非 S ~ V (体积律)。

与熵计算的联系:
熵 S = -Tr(ρ ln ρ) 依赖于态密度 ρ(E)。
谱维 d_s(E) 修正了 ρ(E) 的标度行为:
    ρ(E) ~ E^{d_s(E)/2 - 1}
    
在高能区 (E → E_Planck), d_s → 10:
    ρ(E) ~ E⁴ (而非 E¹)
    
这增加了视界附近的状态数，导致面积律!
        """)
        
    def summary(self):
        """
        总结
        """
        print("\n" + "="*70)
        print("Day 2 总结")
        print("="*70)
        
        print("""
今日完成:

1. ✅ 弯曲时空中的自由场论
   - 弯曲时空Klein-Gordon方程
   - 没有全局类时Killing矢量
   - 粒子定义的观测者依赖性

2. ✅ Hartle-Hawking真空
   - 定义: 视界和无穷远都正则的态
   - 对应热平衡态，温度 T_H
   - 与Boulware、Unruh真空的区别

3. ✅ 模式展开
   - 球对称简化
   - 径向方程与有效势
   - 边界条件 (视界和无穷远)

4. ✅ Bogoliubov变换
   - 不同模式展开之间的关系
   - 粒子产生的数学机制
   - β系数与粒子数

5. ✅ Hawking辐射
   - 原始推导思路
   - 普朗克谱的出现
   - 温度 T_H = ℏκ/(2π)

6. ✅ 扭转场应用
   - 运动方程
   - 谱维对态密度的影响
   - 与面积律的联系

关键公式:
┌────────────────────┬────────────────────────────┐
│ 概念               │ 公式                       │
├────────────────────┼────────────────────────────┤
│ Hawking温度        │ T_H = ℏκ/(2π) = ℏ/(8πM)   │
│ Bogoliubov系数     │ |β|² = 1/(e^(ω/T_H) - 1)  │
│ 普朗克分布         │ n(ω) = 1/(e^(ω/T) - 1)    │
│ 态密度 (d维)       │ ρ(E) ~ E^{d/2-1}          │
│ 谱维修正           │ d_s(E) = 4 + 6/(1+(E/E_c)²)│
└────────────────────┴────────────────────────────┘

下一步:
态密度计算与熵公式推导
- 相空间体积
- 模式求和
- 熵的显式计算
        """)


def main():
    """主程序"""
    print("="*70)
    print("黑洞熵阶段C - Day 2: 弯曲时空中的量子场论")
    print("="*70)
    print()
    
    # 创建QFT实例 (M = 1)
    qft = QFTinCurvedSpacetime(M=1)
    
    # 运行所有分析
    qft.free_field_flat_spacetime()
    qft.free_field_curved_spacetime()
    qft.hartle_hawking_vacuum()
    qft.mode_expansion_schwarzschild()
    qft.bogoliubov_transformations()
    qft.hawking_radiation_derivation()
    qft.stress_tensor_and_back_reaction()
    qft.mode_expansion_torsion_field()
    qft.summary()
    
    print("\n" + "="*70)
    print("Day 2 完成！准备进入态密度计算与熵推导")
    print("="*70)


if __name__ == "__main__":
    main()
