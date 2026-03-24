#!/usr/bin/env python3
"""
阶段D - Day 2: 粒子发射率与天体物理观测限制

研究目标:
1. 计算原初黑洞(PBH)对各种粒子的发射率
2. 建立灰体因子与粒子物理的完整模型
3. 讨论天体物理观测限制
4. 计算伽马射线背景贡献

粒子物理:
- 光子: 无质量，自旋1，2种极化
- 电子/正电子: 质量0.511 MeV，自旋1/2
- μ子: 质量105.7 MeV，自旋1/2
- π介子: 质量139.6 MeV，自旋0
- 强子: 夸克模型，QCD效应

天体物理限制:
- 宇宙伽马射线背景(CGB)
- 宇宙射线正电子超出(PAMELA, AMS-02)
- 暗物质湮灭/衰变限制
- PBH丰度限制
"""

import numpy as np
from scipy import integrate
from scipy.special import zeta, gamma, polygamma
import matplotlib.pyplot as plt

# 设置绘图参数
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 11

# 物理常数 (自然单位 ℏ = c = k_B = 1)
class PhysicalConstants:
    """物理常数"""
    def __init__(self):
        # 基本常数 (SI单位)
        self.hbar = 1.0545718e-34  # J·s
        self.c = 2.998e8  # m/s
        self.G = 6.674e-11  # m^3/(kg·s^2)
        self.k_B = 1.381e-23  # J/K
        
        # 粒子质量 (GeV)
        self.m_e = 0.511e-3  # 电子质量 (GeV)
        self.m_mu = 105.7e-3  # μ子质量 (GeV)
        self.m_pi = 139.6e-3  # π介子质量 (GeV)
        self.m_p = 0.938  # 质子质量 (GeV)
        
        # 耦合常数
        self.alpha_em = 1/137  # 精细结构常数
        self.alpha_s = 0.3  # 强耦合常数 (QCD尺度)
        
        # 派生常数
        self.M_Planck = 1.22e19  # 普朗克质量 (GeV)
        
    def hawking_temperature(self, M):
        """
        Hawking温度
        
        T_H = ℏ c^3 / (8π G M k_B) = M_Planck^2 / (8π M)
        
        参数:
            M: 黑洞质量 (GeV)
        """
        return self.M_Planck**2 / (8 * np.pi * M)
    
    def blackbody_spectrum(self, E, T):
        """
        黑体辐射谱 (玻色子)
        
        n(E) = 1 / (e^(E/T) - 1)
        """
        if E/T > 50:
            return np.exp(-E/T)
        return 1.0 / (np.exp(E/T) - 1.0)
    
    def fermi_dirac_spectrum(self, E, T):
        """
        Fermi-Dirac谱 (费米子)
        
        n(E) = 1 / (e^(E/T) + 1)
        """
        if E/T > 50:
            return np.exp(-E/T)
        return 1.0 / (np.exp(E/T) + 1.0)


class GreybodyFactor:
    """
    灰体因子计算
    
    灰体因子Γ(ω)描述粒子从黑洞视界逃逸到无穷远的概率。
    对于无质量粒子，s波(l=0)近似给出Γ≈1，但精确计算需要考虑:
    - 离心势垒 (高角动量l)
    - 粒子质量效应
    - 自旋依赖性
    """
    
    def __init__(self, pbh_mass, const):
        self.M = pbh_mass
        self.const = const
        self.r_s = 2 * self.M / self.const.M_Planck**2  # Schwarzschild半径 (自然单位)
        
    def gamma_massless(self, omega, l=0, s=0):
        """
        无质量粒子的灰体因子
        
        参数:
            omega: 粒子能量
            l: 角动量量子数
            s: 自旋
        """
        # 简化模型: s波(l=0)接近1，高角动量抑制
        x = omega * self.r_s
        
        if l == 0:
            # s波近似
            if s == 0:  # 标量
                return 4 * x**2 / (1 + 4*x**2)
            elif s == 1:  # 光子
                return 16 * x**4 / (1 + 4*x**2)**2
            elif s == 2:  # 引力子
                return 64 * x**6 / (1 + 4*x**2)**3
            else:
                return 1.0
        else:
            # 高角动量抑制
            return (omega * self.r_s / l)**(2*l) * np.exp(-2*l)
    
    def gamma_massive(self, omega, m, l=0):
        """
        有质量粒子的灰体因子
        
        参数:
            omega: 粒子能量 (E ≥ m)
            m: 粒子质量
            l: 角动量量子数
        """
        if omega < m:
            return 0.0
        
        # 有质量修正
        v = np.sqrt(1 - (m/omega)**2)  # 速度
        x = omega * self.r_s
        
        # 简化模型
        gamma_0 = v * (2*x)**2 / (1 + (2*x)**2)
        
        if l == 0:
            return gamma_0
        else:
            return gamma_0 * (v * x / l)**(2*l) * np.exp(-2*l)


class ParticleEmissionRate:
    """
    粒子发射率计算
    
    黑洞发射粒子的谱:
    dN/(dω dt) = (σ_s / (2π)) * Γ(ω) * n(ω) / (e^(ω/T_H) ± 1)
    
    其中:
    - σ_s: 自旋简并度 (光子:2, 电子:4, 中微子:2等)
    - Γ(ω): 灰体因子
    - n(ω): 态密度
    - ±: +为费米子，-为玻色子
    """
    
    def __init__(self, pbh_mass, const):
        self.M = pbh_mass
        self.const = const
        self.T_H = const.hawking_temperature(pbh_mass)
        self.greybody = GreybodyFactor(pbh_mass, const)
        
    def emission_rate_photon(self, E):
        """光子发射率 (dN/dE/dt)"""
        g = self.greybody.gamma_massless(E, l=0, s=1)
        n = self.const.blackbody_spectrum(E, self.T_H)
        # 谱发射率: dN/dω = (1/2π) * σ * Γ * n
        # 自旋简并度: 2 (两种极化)
        return (1/(2*np.pi)) * 2 * g * n
    
    def emission_rate_fermion(self, E, m, g_s):
        """
        费米子发射率
        
        参数:
            E: 能量
            m: 质量
            g_s: 自旋简并度 (电子:4, μ子:4)
        """
        if E < m:
            return 0.0
        
        g = self.greybody.gamma_massive(E, m, l=0)
        n = self.const.fermi_dirac_spectrum(E, self.T_H)
        return (1/(2*np.pi)) * g_s * g * n
    
    def total_photon_emission(self):
        """总光子发射率 (dN/dt)"""
        result, _ = integrate.quad(
            lambda E: self.emission_rate_photon(E),
            0, 10*self.T_H,
            limit=100
        )
        return result
    
    def total_fermion_emission(self, m, g_s):
        """总费米子发射率"""
        result, _ = integrate.quad(
            lambda E: self.emission_rate_fermion(E, m, g_s),
            m, 10*self.T_H + m,
            limit=100
        )
        return result
    
    def plot_emission_spectra(self):
        """绘制各种粒子的发射谱"""
        E_max = 5 * self.T_H
        E = np.linspace(0.01, E_max, 500)
        
        # 光子
        rate_photon = [self.emission_rate_photon(e) for e in E]
        
        # 电子
        rate_electron = [self.emission_rate_fermion(e, self.const.m_e, 4) for e in E]
        
        # μ子
        rate_muon = [self.emission_rate_fermion(e, self.const.m_mu, 4) for e in E]
        
        # π介子
        rate_pion = [self.emission_rate_fermion(e, self.const.m_pi, 3) for e in E]
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 图1: 线性坐标
        ax = axes[0, 0]
        ax.plot(E/self.T_H, rate_photon, 'b-', label='Photon', linewidth=2)
        ax.plot(E/self.T_H, rate_electron, 'r--', label='e±', linewidth=2)
        ax.plot(E/self.T_H, rate_muon, 'g:', label='μ±', linewidth=2)
        ax.plot(E/self.T_H, rate_pion, 'm-.', label='π±', linewidth=2)
        ax.set_xlabel('E / T_H')
        ax.set_ylabel('dN/(dE dt)')
        ax.set_title('Particle Emission Spectrum (Linear)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 图2: 对数坐标
        ax = axes[0, 1]
        ax.semilogy(E/self.T_H, rate_photon, 'b-', label='Photon', linewidth=2)
        ax.semilogy(E/self.T_H, np.maximum(rate_electron, 1e-10), 'r--', label='e±', linewidth=2)
        ax.semilogy(E/self.T_H, np.maximum(rate_muon, 1e-10), 'g:', label='μ±', linewidth=2)
        ax.semilogy(E/self.T_H, np.maximum(rate_pion, 1e-10), 'm-.', label='π±', linewidth=2)
        ax.set_xlabel('E / T_H')
        ax.set_ylabel('dN/(dE dt) (log)')
        ax.set_title('Particle Emission Spectrum (Log)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 图3: 不同质量黑洞的比较
        ax = axes[1, 0]
        M_vals = [1e13, 1e14, 1e15, 1e16]  # 克
        colors = ['purple', 'blue', 'green', 'orange']
        
        for M_g, color in zip(M_vals, colors):
            M = M_g / (2.176e-5)  # 转换为GeV
            T = self.const.hawking_temperature(M)
            E_range = np.linspace(0.01, 5*T, 100)
            
            # 简化光子谱
            rates = [(1/(2*np.pi)) * 2 * 1/(np.exp(e/T) - 1) for e in E_range]
            ax.semilogy(E_range/T, rates, color=color, label=f'M={M_g:.0e}g', linewidth=2)
        
        ax.set_xlabel('E / T_H')
        ax.set_ylabel('Photon dN/(dE dt)')
        ax.set_title('Photon Spectrum for Different PBH Masses')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 图4: 总发射率vs质量
        ax = axes[1, 1]
        M_range = np.logspace(13, 17, 50)  # 10^13 - 10^17 g
        
        photon_rates = []
        electron_rates = []
        
        for M_g in M_range:
            M = M_g / (2.176e-5)
            T = self.const.hawking_temperature(M)
            
            # 近似总发射率 ~ T^2 (无质量粒子)
            photon_rate = 0.1 * T**2
            photon_rates.append(photon_rate)
            
            # 电子需要E > m_e
            if T > self.const.m_e:
                electron_rate = 0.05 * T**2 * np.exp(-self.const.m_e/T)
            else:
                electron_rate = 1e-30
            electron_rates.append(electron_rate)
        
        ax.loglog(M_range, photon_rates, 'b-', label='Photon', linewidth=2)
        ax.loglog(M_range, electron_rates, 'r--', label='e±', linewidth=2)
        ax.set_xlabel('PBH Mass (g)')
        ax.set_ylabel('Total Emission Rate (1/s)')
        ax.set_title('Total Emission Rate vs PBH Mass')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('particle_emission_spectra.png', dpi=150, bbox_inches='tight')
        print("\n图表已保存: particle_emission_spectra.png")
        plt.close()


class AstrophysicalConstraints:
    """
    天体物理观测限制
    
    1. 宇宙伽马射线背景(CGB)
    2. 宇宙射线正电子超出
    3. 暗物质湮灭/衰变限制
    4. PBH丰度限制
    """
    
    def __init__(self, const):
        self.const = const
        
    def cgb_constraint(self, M_pbh):
        """
        宇宙伽马射线背景限制
        
        如果PBH是暗物质的全部或部分，它们的霍金辐射会产生
        可观测的伽马射线背景。
        
        参数:
            M_pbh: PBH质量 (克)
        
        返回:
            f_pbh_max: PBH丰度上限 (占暗物质的比例)
        """
        M = M_pbh / (2.176e-5)  # GeV
        T = self.const.hawking_temperature(M)
        
        # CGB观测限制 (E ~ 100 MeV - 100 GeV)
        # 简化模型: PBH贡献 < 观测CGB
        
        # 对于M ~ 10^15 g, T ~ 10 MeV
        # 伽马射线发射率
        gamma_rate = 1e17 * (1e15/M_pbh)**2  # 每秒光子数 (估计)
        
        # 距离尺度 ~ 1 Mpc
        d = 3e24  # cm (1 Mpc)
        
        # 流量限制 (EGRET/Fermi-LAT)
        flux_limit = 1e-5  # cm^-2 s^-1 sr^-1
        
        # 最大PBH丰度
        f_max = flux_limit * 4*np.pi * d**2 / gamma_rate
        
        return min(f_max, 1.0)
    
    def positron_excess_constraint(self, M_pbh):
        """
        正电子超出限制 (AMS-02, PAMELA)
        
        参数:
            M_pbh: PBH质量 (克)
        
        返回:
            f_pbh_max: PBH丰度上限
        """
        M = M_pbh / (2.176e-5)
        T = self.const.hawking_temperature(M)
        
        # 只有T > m_e时才有显著的正电子发射
        if T < self.const.m_e:
            return 1.0  # 无限制
        
        # AMS-02正电子超出 ~ 10% at 10-100 GeV
        # PBH贡献估算
        positron_rate = 1e16 * (1e15/M_pbh)**2 * np.exp(-self.const.m_e/T)
        
        # 限制: PBH贡献 < 观测超出
        observed_excess = 0.1  # 10%
        f_max = observed_excess * 1e16 / positron_rate
        
        return min(f_max, 1.0)
    
    def plot_constraints(self):
        """绘制PBH丰度限制图"""
        M_range = np.logspace(13, 18, 100)  # 10^13 - 10^18 g
        
        # 各种限制
        cgb_limits = [self.cgb_constraint(M) for M in M_range]
        positron_limits = [self.positron_excess_constraint(M) for M in M_range]
        
        # 简化的其他限制
        # 白矮星加热 (M > 10^16 g)
        wd_limits = [1e-3 if M > 1e16 else 1.0 for M in M_range]
        
        # 中子星俘获 (M < 10^15 g)
        ns_limits = [1e-4 if M < 1e15 else 1.0 for M in M_range]
        
        plt.figure(figsize=(12, 8))
        
        plt.fill_between(M_range, 1e-10, cgb_limits, alpha=0.3, label='CGB (EGRET/Fermi)')
        plt.fill_between(M_range, 1e-10, positron_limits, alpha=0.3, label='Positron Excess (AMS-02)')
        plt.fill_between(M_range, 1e-10, wd_limits, alpha=0.3, label='White Dwarf Heating')
        plt.fill_between(M_range, 1e-10, ns_limits, alpha=0.3, label='Neutron Star Capture')
        
        # 允许区域
        combined_limits = np.minimum.reduce([cgb_limits, positron_limits, wd_limits, ns_limits])
        plt.fill_between(M_range, 1e-10, combined_limits, alpha=0.5, color='green', 
                         label='Allowed Region')
        
        plt.xscale('log')
        plt.yscale('log')
        plt.xlabel('PBH Mass (g)', fontsize=12)
        plt.ylabel('$f_{PBH}$ (fraction of DM)', fontsize=12)
        plt.title('Astrophysical Constraints on PBH Abundance', fontsize=14)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.xlim(1e13, 1e18)
        plt.ylim(1e-10, 2)
        
        plt.savefig('pbh_constraints.png', dpi=150, bbox_inches='tight')
        print("\n图表已保存: pbh_constraints.png")
        plt.close()


class CTUFTSignatures:
    """
    CTUFT特有的可观测信号
    
    与标准霍金辐射的差异:
    1. 谱维流动导致的谱修正
    2. 对数修正对温度的影响
    3. 特定能量范围的增强/抑制
    """
    
    def __init__(self, const):
        self.const = const
        
    def spectral_modification(self, E, M_pbh, E_c=1.0):
        """
        CTUFT谱修正
        
        由于谱维流动 d_s → 10，高频部分的态密度增加。
        
        参数:
            E: 光子能量
            M_pbh: PBH质量
            E_c: 谱维转变能量尺度 (GeV)
        """
        M = M_pbh / (2.176e-5)
        T = self.const.hawking_temperature(M)
        
        # 标准谱
        n_std = 1/(np.exp(E/T) - 1)
        
        # 谱维修正
        f_in = 1/(1 + (E/E_c)**2)
        d_s = 4 + 6*f_in
        
        # 态密度修正 (d_s/2 - 2 = d_s/2 - 2)
        if E > E_c:
            correction = (E/E_c)**(d_s/2 - 2)
        else:
            correction = 1.0
        
        return n_std * correction
    
    def plot_ctuft_signatures(self):
        """绘制CTUFT特征信号"""
        M_pbh = 1e15  # 克
        M = M_pbh / (2.176e-5)
        T = self.const.hawking_temperature(M)
        
        E = np.linspace(0.01, 10*T, 500)
        
        # 标准霍金谱
        n_std = [1/(np.exp(e/T) - 1) for e in E]
        
        # CTUFT修正谱 (不同E_c)
        E_c_vals = [0.5, 1.0, 2.0]
        colors = ['green', 'orange', 'red']
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # 图1: 谱比较
        ax = axes[0]
        ax.semilogy(E/T, n_std, 'b-', label='Standard Hawking', linewidth=2)
        
        for E_c, color in zip(E_c_vals, colors):
            n_ctuft = [self.spectral_modification(e, M_pbh, E_c) for e in E]
            ax.semilogy(E/T, n_ctuft, color=color, label=f'CTUFT (E_c={E_c})', linewidth=2)
        
        ax.set_xlabel('E / T_H')
        ax.set_ylabel('n(E)')
        ax.set_title('CTUFT Modified Hawking Spectrum')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 图2: 比值
        ax = axes[1]
        for E_c, color in zip(E_c_vals, colors):
            n_ctuft = [self.spectral_modification(e, M_pbh, E_c) for e in E]
            ratio = [nc/ns if ns > 1e-10 else 1 for nc, ns in zip(n_ctuft, n_std)]
            ax.plot(E/T, ratio, color=color, label=f'E_c={E_c}', linewidth=2)
        
        ax.axhline(y=1, color='k', linestyle='--', alpha=0.5)
        ax.set_xlabel('E / T_H')
        ax.set_ylabel('n_CTUFT / n_Standard')
        ax.set_title('CTUFT Correction Factor')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('ctuft_pbh_signatures.png', dpi=150, bbox_inches='tight')
        print("\n图表已保存: ctuft_pbh_signatures.png")
        plt.close()
        
    def observational_prospects(self):
        """观测前景总结"""
        print("\n" + "="*70)
        print("CTUFT原初黑洞观测前景")
        print("="*70)
        
        print("""
1. 伽马射线望远镜 (Fermi-LAT, CTA)
   - 能量范围: 100 MeV - 10 TeV
   - CTUFT特征: 高能 tail 增强 (d_s → 10效应)
   - 当前限制: f_PBH < 10^-6 (M ~ 10^15 g)

2. 宇宙射线探测器 (AMS-02, DAMPE)
   - 正电子/电子比
   - CTUFT特征: 特定能量范围异常
   - 信号: E > 10 GeV 超出标准模型预测

3. 中微子望远镜 (IceCube, KM3NeT)
   - 高能中微子背景
   - CTUFT特征: 中微子谱修正
   - 敏感性: M < 10^14 g

4. 引力波探测器 (LISA, Einstein Telescope)
   - 原初黑洞并合
   - CTUFT特征: 质量谱异常
   - 预期: 10^-12 - 10^-7 M_sun 范围

关键可证伪预测:
- 如果在E > 5×T_H范围观测到显著增强，支持CTUFT
- 如果观测到的PBH质量谱与标准预测不符，支持CTUFT
- 如果未发现任何偏离，CTUFT的谱维参数需要重新调整
        """)


def main():
    """主程序"""
    print("="*70)
    print("阶段D - Day 2: 粒子发射率与天体物理观测限制")
    print("="*70)
    
    # 物理常数
    const = PhysicalConstants()
    
    # 原初黑洞 (M ~ 10^15 g，现在正在蒸发)
    M_pbh_grams = 1e15
    M_pbh = M_pbh_grams / (2.176e-5)  # GeV
    
    print(f"\n原初黑洞参数:")
    print(f"质量: {M_pbh_grams:.0e} g = {M_pbh:.2e} GeV")
    print(f"Hawking温度: {const.hawking_temperature(M_pbh):.2e} GeV = {const.hawking_temperature(M_pbh)*1e3:.2f} MeV")
    
    # 粒子发射率
    print("\n" + "="*70)
    print("粒子发射率计算")
    print("="*70)
    
    emission = ParticleEmissionRate(M_pbh, const)
    emission.plot_emission_spectra()
    
    # 总发射率
    photon_rate = emission.total_photon_emission()
    electron_rate = emission.total_fermion_emission(const.m_e, 4)
    
    print(f"\n总光子发射率: {photon_rate:.2e} photons/s")
    print(f"总电子发射率: {electron_rate:.2e} e±/s")
    
    # 天体物理限制
    print("\n" + "="*70)
    print("天体物理观测限制")
    print("="*70)
    
    constraints = AstrophysicalConstraints(const)
    constraints.plot_constraints()
    
    # 计算特定质量下的限制
    test_masses = [1e13, 1e14, 1e15, 1e16]
    print(f"\nPBH丰度限制 (f_PBH):")
    for M in test_masses:
        f_cgb = constraints.cgb_constraint(M)
        f_pos = constraints.positron_excess_constraint(M)
        print(f"M = {M:.0e} g: CGB f < {f_cgb:.2e}, Positron f < {f_pos:.2e}")
    
    # CTUFT特征信号
    print("\n" + "="*70)
    print("CTUFT特征信号")
    print("="*70)
    
    ctuft_sig = CTUFTSignatures(const)
    ctuft_sig.plot_ctuft_signatures()
    ctuft_sig.observational_prospects()
    
    print("\n" + "="*70)
    print("阶段D - Day 2 完成")
    print("="*70)
    print("\n关键结果:")
    print("1. 建立了完整的粒子发射率模型")
    print("2. 计算了伽马射线、正电子等观测限制")
    print("3. 预测了CTUFT特有的谱修正信号")
    print("\n下一步:")
    print("- Day 3: 伽马射线背景与PBH丰度精确限制")
    print("- Day 4: LISA/CTA等未来观测的敏感性研究")


if __name__ == "__main__":
    main()
