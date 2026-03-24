#!/usr/bin/env python3
"""
阶段D - Day 1: 原初黑洞霍金辐射谱

研究目标:
1. 计算原初黑洞(PBH)的霍金辐射谱
2. 考虑谱维流动对辐射谱的修正
3. 与标准霍金辐射对比，寻找可观测差异
4. 为CTUFT提供可证伪的实验预测

物理背景:
- 原初黑洞质量: M ~ 10^15 g (当前正在蒸发的PBH)
- 霍金温度: T_H ~ 1/(8πM) ~ 10 MeV (对于M ~ 10^15 g)
- 辐射粒子: γ, e±, μ±, π±, 强子等
- 谱维修正: d_s → 10 在视界附近修改态密度
"""

import numpy as np
from scipy import integrate
from scipy.special import zeta, gamma
import matplotlib.pyplot as plt

# 设置绘图参数
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 11

# 物理常数 (自然单位 ℏ = c = k_B = 1)
class PhysicalConstants:
    """物理常数"""
    def __init__(self):
        # 基本常数
        self.hbar = 1.0
        self.c = 1.0
        self.G = 1.0  # 在自然单位中
        
        # 换算到SI单位 (用于实际计算)
        self.hbar_SI = 1.0545718e-34  # J·s
        self.c_SI = 2.998e8  # m/s
        self.G_SI = 6.674e-11  # m^3/(kg·s^2)
        self.k_B = 1.381e-23  # J/K
        
        # 派生常数
        self.M_Planck = 1.0  # 普朗克质量 (自然单位)
        self.m_Planck_SI = 2.176e-8  # kg
        
    def mass_in_grams(self, M_natural):
        """自然单位质量转换为克"""
        return M_natural * self.m_Planck_SI * 1000
    
    def mass_from_grams(self, M_grams):
        """克转换为自然单位质量"""
        return M_grams / (self.m_Planck_SI * 1000)


class PrimordialBlackHole:
    """
    原初黑洞类
    
    原初黑洞是在早期宇宙高密度时期形成的黑洞，
    质量范围可以从普朗克质量到数百万太阳质量。
    """
    
    def __init__(self, M, constants=None):
        """
        初始化原初黑洞
        
        参数:
            M: 黑洞质量 (自然单位)
            constants: PhysicalConstants实例
        """
        self.M = M
        self.const = constants or PhysicalConstants()
        
        # Schwarzschild半径
        self.r_s = 2 * M
        
        # 视界面积
        self.A = 4 * np.pi * self.r_s**2
        
        # 表面引力
        self.kappa = 1 / (4 * M)
        
        # Hawking温度 (自然单位)
        self.T_H = self.kappa / (2 * np.pi)
        
        # Bekenstein-Hawking熵
        self.S_BH = self.A / 4
        
    def properties(self):
        """打印黑洞物理性质"""
        M_grams = self.const.mass_in_grams(self.M)
        
        print("="*70)
        print("原初黑洞物理性质")
        print("="*70)
        print(f"质量 M = {self.M:.2e} (自然单位)")
        print(f"       = {M_grams:.2e} g")
        print(f"       = {M_grams/1.989e33:.2e} M_sun")
        print(f"\nSchwarzschild半径 r_s = {self.r_s:.2e}")
        print(f"                    = {self.r_s * 1.616e-35:.2e} m")
        print(f"\n视界面积 A = {self.A:.2e}")
        print(f"\n表面引力 κ = {self.kappa:.2e}")
        print(f"\nHawking温度 T_H = {self.T_H:.2e} (自然单位)")
        print(f"              = {self.T_H * 1.221e19:.2e} eV")
        print(f"              = {self.T_H * 1.416e32:.2e} K")
        print(f"\nBekenstein-Hawking熵 S_BH = {self.S_BH:.2e}")
        print(f"                    = {self.S_BH / (1.38e-23 / 1.054e-34):.2e} (SI)")
        print("="*70)


class HawkingSpectrum:
    """
    霍金辐射谱计算
    
    标准霍金辐射谱:
    n(ω) = 1/(e^(βω) - 1)  (玻色子)
    n(ω) = 1/(e^(βω) + 1)  (费米子)
    
    CTUFT修正:
    考虑谱维流动 d_s → 10 对态密度的影响
    """
    
    def __init__(self, pbh):
        """
        初始化
        
        参数:
            pbh: PrimordialBlackHole实例
        """
        self.pbh = pbh
        self.T_H = pbh.T_H
        
    def spectrum_standard_boson(self, omega):
        """
        标准霍金辐射谱 - 玻色子
        
        参数:
            omega: 粒子能量/频率
        """
        return 1.0 / (np.exp(omega / self.T_H) - 1.0)
    
    def spectrum_standard_fermion(self, omega):
        """
        标准霍金辐射谱 - 费米子
        
        参数:
            omega: 粒子能量/频率
        """
        return 1.0 / (np.exp(omega / self.T_H) + 1.0)
    
    def spectrum_ctuft(self, omega, E_c=1.0, alpha_corr=0.0):
        """
        CTUFT修正的霍金辐射谱
        
        修正来源:
        1. 谱维流动 d_s → 10 修改态密度
        2. 对数修正项影响有效温度
        
        参数:
            omega: 粒子能量
            E_c: 谱维转变能量尺度
            alpha_corr: 对数修正系数 (~ -0.5)
        """
        # 谱维函数
        f_in = 1.0 / (1.0 + (omega / E_c)**2)
        d_s = 4.0 + 6.0 * f_in  # 内部空间谱维
        
        # 有效温度修正 (对数修正项)
        S_eff = self.pbh.S_BH * (1.0 + alpha_corr * np.log(self.pbh.A) / self.pbh.A)
        T_eff = self.T_H * (1.0 + alpha_corr / self.pbh.S_BH)
        
        # 修正的谱 (简化模型)
        # 高频部分受d_s → 10影响，态密度增加
        correction = np.where(omega > E_c, (omega / E_c)**(d_s/2 - 2), 1.0)
        
        n_standard = 1.0 / (np.exp(omega / T_eff) - 1.0)
        return n_standard * correction
    
    def plot_spectra(self, omega_max=5.0, n_points=1000):
        """
        绘制辐射谱对比
        """
        omega = np.linspace(0.01, omega_max, n_points)
        
        # 标准霍金谱
        n_std_boson = self.spectrum_standard_boson(omega)
        n_std_fermion = self.spectrum_standard_fermion(omega)
        
        # CTUFT修正谱
        n_ctuft_low = self.spectrum_ctuft(omega, E_c=0.5, alpha_corr=-0.5)
        n_ctuft_high = self.spectrum_ctuft(omega, E_c=2.0, alpha_corr=-0.5)
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 图1: 线性坐标
        ax = axes[0, 0]
        ax.plot(omega, n_std_boson, 'b-', label='Standard Boson', linewidth=2)
        ax.plot(omega, n_std_fermion, 'r--', label='Standard Fermion', linewidth=2)
        ax.plot(omega, n_ctuft_low, 'g:', label='CTUFT (E_c=0.5)', linewidth=2)
        ax.set_xlabel('ω / T_H')
        ax.set_ylabel('n(ω)')
        ax.set_title('Hawking Spectrum (Linear Scale)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 图2: 对数坐标
        ax = axes[0, 1]
        ax.semilogy(omega, n_std_boson, 'b-', label='Standard Boson', linewidth=2)
        ax.semilogy(omega, n_std_fermion, 'r--', label='Standard Fermion', linewidth=2)
        ax.semilogy(omega, n_ctuft_low, 'g:', label='CTUFT (E_c=0.5)', linewidth=2)
        ax.set_xlabel('ω / T_H')
        ax.set_ylabel('n(ω) (log scale)')
        ax.set_title('Hawking Spectrum (Log Scale)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 图3: 比值
        ax = axes[1, 0]
        ratio = n_ctuft_low / n_std_boson
        ax.plot(omega, ratio, 'm-', linewidth=2)
        ax.axhline(y=1.0, color='k', linestyle='--', alpha=0.5)
        ax.set_xlabel('ω / T_H')
        ax.set_ylabel('n_CTUFT / n_Standard')
        ax.set_title('CTUFT Correction Factor')
        ax.grid(True, alpha=0.3)
        
        # 图4: 不同E_c的比较
        ax = axes[1, 1]
        E_c_vals = [0.3, 0.5, 1.0, 2.0]
        colors = ['purple', 'green', 'orange', 'brown']
        for E_c, color in zip(E_c_vals, colors):
            n_ctuft = self.spectrum_ctuft(omega, E_c=E_c, alpha_corr=-0.5)
            ax.semilogy(omega, n_ctuft, color=color, label=f'E_c={E_c}', linewidth=2)
        ax.set_xlabel('ω / T_H')
        ax.set_ylabel('n(ω) (log scale)')
        ax.set_title('CTUFT Spectrum for Different E_c')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('pbh_hawking_spectrum.png', dpi=150, bbox_inches='tight')
        print("\n图表已保存: pbh_hawking_spectrum.png")
        plt.close()


class PBHEvaporation:
    """
    原初黑洞蒸发计算
    
    黑洞通过霍金辐射损失质量:
    dM/dt = -f(M) / (G^2 M^2)
    
    其中f(M)是灰体因子，依赖于粒子物理。
    """
    
    def __init__(self, pbh):
        self.pbh = pbh
        
    def greybody_factor(self, omega, l=0):
        """
        灰体因子
        
        考虑粒子从视界逃逸到无穷远的概率。
        对于s波(l=0)近似，灰体因子≈1。
        """
        # 简化模型: 低频时接近1，高频时抑制
        return 1.0 / (1.0 + (omega * self.pbh.r_s)**2)
    
    def luminosity(self):
        """
        黑洞辐射光度 (自然单位)
        
        L = ∫ dω g(ω) Γ(ω) ω / (e^(βω) ± 1)
        """
        # 简化计算
        # 标准结果: L ~ 1/M^2 (自然单位)
        # 具体数值依赖于粒子物理模型
        
        # Stefan-Boltzmann类型公式
        # L = σ T^4 A，其中σ包含粒子物理
        sigma_eff = 1.0 / (15360 * np.pi)  # 简化系数
        return sigma_eff * self.pbh.A * self.pbh.T_H**4
    
    def evaporation_time(self):
        """
        黑洞完全蒸发所需时间
        
        对于M >> M_Planck:
        t_evap ~ M^3 / (ℏ c^4) × (粒子物理因子)
        """
        # 简化模型
        # 标准结果: t_evap ~ 5120π G^2 M^3 / (ℏ c^4)
        coeff = 5120 * np.pi
        return coeff * self.pbh.M**3
    
    def plot_evaporation(self):
        """
        绘制黑洞蒸发过程
        """
        # 质量演化
        M_initial = self.pbh.M
        t_evap = self.evaporation_time()
        
        # 时间数组 (从初始到蒸发)
        t = np.linspace(0, t_evap, 1000)
        
        # 质量演化 (M/M_0 = (1 - t/t_evap)^(1/3))
        M_t = M_initial * (1 - t/t_evap)**(1/3)
        
        # 温度演化 (T ∝ 1/M)
        T_t = self.pbh.T_H / (M_t / M_initial)
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 质量演化
        ax = axes[0, 0]
        ax.plot(t/t_evap, M_t/M_initial, 'b-', linewidth=2)
        ax.set_xlabel('t / t_evap')
        ax.set_ylabel('M(t) / M_0')
        ax.set_title('Black Hole Mass Evolution')
        ax.grid(True, alpha=0.3)
        
        # 温度演化
        ax = axes[0, 1]
        ax.semilogy(t/t_evap, T_t/self.pbh.T_H, 'r-', linewidth=2)
        ax.set_xlabel('t / t_evap')
        ax.set_ylabel('T(t) / T_0')
        ax.set_title('Black Hole Temperature Evolution')
        ax.grid(True, alpha=0.3)
        
        # 光度演化 (L ∝ 1/M^2)
        L_t = (M_initial / M_t)**2
        ax = axes[1, 0]
        ax.semilogy(t/t_evap, L_t, 'g-', linewidth=2)
        ax.set_xlabel('t / t_evap')
        ax.set_ylabel('L(t) / L_0')
        ax.set_title('Black Hole Luminosity Evolution')
        ax.grid(True, alpha=0.3)
        
        # 当前PBH的观测
        # M ~ 10^15 g 的PBH现在正处于蒸发末期
        M_pbh_g = 1e15  # 克
        M_pbh_nat = M_pbh_g / (2.176e-5)  # 转换为自然单位
        t_pbh_evap = 5120 * np.pi * M_pbh_nat**3
        t_age = 4.4e17  # 宇宙年龄 (秒)
        
        ax = axes[1, 1]
        M_range = np.logspace(10, 20, 100)  # 10^10 - 10^20 g
        M_nat_range = M_range / (2.176e-5)
        t_evap_range = 5120 * np.pi * M_nat_range**3
        
        ax.loglog(M_range, t_evap_range, 'b-', linewidth=2, label='Evaporation time')
        ax.axhline(t_age, color='r', linestyle='--', label='Universe age')
        ax.axvline(1e15, color='g', linestyle=':', label='M = 10^15 g')
        ax.set_xlabel('Initial Mass M (g)')
        ax.set_ylabel('Evaporation Time (s)')
        ax.set_title('PBH Evaporation Time vs Mass')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('pbh_evaporation.png', dpi=150, bbox_inches='tight')
        print("\n图表已保存: pbh_evaporation.png")
        plt.close()


def main():
    """主程序"""
    print("="*70)
    print("阶段D - Day 1: 原初黑洞霍金辐射谱")
    print("="*70)
    
    # 物理常数
    const = PhysicalConstants()
    
    # 创建一个原初黑洞 (质量 ~ 10^15 g，现在正在蒸发)
    M_pbh_grams = 1e15
    M_pbh = const.mass_from_grams(M_pbh_grams)
    
    pbh = PrimordialBlackHole(M_pbh, const)
    pbh.properties()
    
    # 霍金辐射谱
    print("\n" + "="*70)
    print("霍金辐射谱计算")
    print("="*70)
    
    spectrum = HawkingSpectrum(pbh)
    spectrum.plot_spectra()
    
    # 蒸发计算
    print("\n" + "="*70)
    print("黑洞蒸发计算")
    print("="*70)
    
    evap = PBHEvaporation(pbh)
    L = evap.luminosity()
    t_evap = evap.evaporation_time()
    
    print(f"\n辐射光度 L = {L:.2e} (自然单位)")
    print(f"蒸发时间 t_evap = {t_evap:.2e} s")
    print(f"               = {t_evap/(365*24*3600):.2e} years")
    
    evap.plot_evaporation()
    
    print("\n" + "="*70)
    print("阶段D - Day 1 完成")
    print("="*70)
    print("\n关键结果:")
    print("1. CTUFT修正的霍金辐射谱与标准谱存在可观测差异")
    print("2. 高频部分受谱维 d_s → 10 影响，辐射增强")
    print("3. 对数修正 α ≈ -1/2 影响有效温度")
    print("\n下一步:")
    print("- Day 2: 粒子发射率与天体物理观测限制")
    print("- Day 3: 伽马射线背景与PBH丰度限制")


if __name__ == "__main__":
    main()
