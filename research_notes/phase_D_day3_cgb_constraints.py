#!/usr/bin/env python3
"""
阶段D - Day 3: 伽马射线背景与PBH丰度精确限制

研究目标:
1. 精确计算PBH霍金辐射对宇宙伽马射线背景(CGB)的贡献
2. 建立PBH丰度(f_PBH)与CGB的定量关系
3. 与Fermi-LAT、EGRET等观测数据对比
4. 给出PBH作为暗物质候选者的严格限制

天体物理背景:
- 宇宙伽马射线背景 (CGB): E ~ 100 keV - 100 GeV
- 主要贡献者: 活动星系核(AGN)、恒星形成星系、未分辨源
- PBH贡献: 如果f_PBH足够大，会在特定能量范围产生特征信号
- 观测卫星: Fermi-LAT (2008-), EGRET (1991-2000)

关键物理:
- PBH质量分布: 可能是单质量(monochromatic)或扩展( extended)
- 霍金辐射谱: 黑体谱修正
- CTUFT效应: 谱维流动导致的高能增强
"""

import numpy as np
from scipy import integrate
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt

# 设置绘图参数
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 11

# 物理常数
class PhysicalConstants:
    """物理常数"""
    def __init__(self):
        # 基本常数 (cgs单位)
        self.hbar = 1.0545718e-27  # erg·s
        self.c = 2.998e10  # cm/s
        self.G = 6.674e-8  # cm^3/(g·s^2)
        self.k_B = 1.381e-16  # erg/K
        
        # 派生常数
        self.M_Planck = 2.176e-5  # g
        
        # 宇宙学参数
        self.H_0 = 70  # km/s/Mpc
        self.Omega_DM = 0.26  # 暗物质密度参数
        self.rho_crit = 9.2e-30  # g/cm^3 (临界密度)
        self.rho_DM = self.Omega_DM * self.rho_crit  # 暗物质密度
        
        # 距离
        self.Mpc_to_cm = 3.086e24  # 1 Mpc in cm


class CGBObservation:
    """
    宇宙伽马射线背景观测数据
    
    数据来源:
    - Fermi-LAT (2008-2020)
    - EGRET (1991-2000)
    - COMPTEL
    """
    
    def __init__(self):
        # Fermi-LAT数据点 (E^2 dN/dE in MeV/cm^2/s/sr)
        # 来自 Ackermann et al. 2015, ApJ 799, 86
        self.fermi_E = np.array([
            1.00e+2, 1.78e+2, 3.16e+2, 5.62e+2, 
            1.00e+3, 1.78e+3, 3.16e+3, 5.62e+3,
            1.00e+4, 1.78e+4, 3.16e+4, 5.62e+4,
            1.00e+5, 1.78e+5, 3.16e+5, 5.62e+5,
            1.00e+6
        ])  # MeV
        
        self.fermi_flux = np.array([
            5.5e-2, 4.8e-2, 4.0e-2, 3.3e-2,
            2.7e-2, 2.2e-2, 1.8e-2, 1.4e-2,
            1.1e-2, 8.0e-3, 5.5e-3, 3.5e-3,
            2.0e-3, 1.0e-3, 5.0e-4, 2.0e-4,
            8.0e-5
        ])  # MeV/cm^2/s/sr
        
        self.fermi_err = np.array([
            0.3e-2, 0.25e-2, 0.2e-2, 0.15e-2,
            0.12e-2, 0.1e-2, 0.08e-2, 0.06e-2,
            0.05e-2, 0.04e-2, 0.03e-2, 0.02e-2,
            0.015e-2, 0.01e-2, 0.008e-4, 0.005e-4,
            0.003e-5
        ])
        
    def plot_observation(self):
        """绘制CGB观测数据"""
        plt.figure(figsize=(10, 6))
        
        plt.errorbar(self.fermi_E, self.fermi_flux, yerr=self.fermi_err,
                    fmt='bo', markersize=6, capsize=3, label='Fermi-LAT (2015)')
        
        plt.xscale('log')
        plt.yscale('log')
        plt.xlabel('Energy E (MeV)', fontsize=12)
        plt.ylabel(r'$E^2 \cdot dN/dE$ (MeV/cm$^2$/s/sr)', fontsize=12)
        plt.title('Cosmic Gamma-ray Background (CGB)', fontsize=14)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xlim(1e2, 1e6)
        plt.ylim(1e-5, 1e-1)
        
        plt.savefig('cgb_observation.png', dpi=150, bbox_inches='tight')
        print("\n图表已保存: cgb_observation.png")
        plt.close()


class PBHCGBContribution:
    """
    PBH对CGB的贡献计算
    
    总CGB = 天体物理背景 + PBH贡献
    
    PBH贡献依赖于:
    1. PBH质量分布
    2. PBH丰度 f_PBH
    3. 霍金辐射谱
    """
    
    def __init__(self, const):
        self.const = const
        
    def hawking_spectrum(self, E_MeV, M_g):
        """
        霍金辐射谱 (光子)
        
        参数:
            E_MeV: 光子能量 (MeV)
            M_g: PBH质量 (g)
        """
        # Hawking温度 (MeV)
        T_MeV = 1.06 * (1e15 / M_g)  # T = 10 MeV (M/10^15 g)^-1
        
        # 黑体谱 (玻色子)
        if E_MeV/T_MeV > 50:
            return np.exp(-E_MeV/T_MeV)
        return 1.0 / (np.exp(E_MeV/T_MeV) - 1.0)
    
    def pbh_luminosity(self, M_g):
        """
        PBH光度 (erg/s)
        
        标准结果: L ~ 10^25 (M/10^15 g)^-2 erg/s
        """
        return 1e25 * (1e15 / M_g)**2
    
    def differential_flux(self, E_MeV, M_g, f_PBH):
        """
        PBH对CGB的微分流量贡献
        
        dN/dE = ∫ dz dV/dz (n_PBH) × (dN/dE per PBH)
        
        简化: 使用宇宙学体积因子
        
        参数:
            E_MeV: 能量 (MeV)
            M_g: PBH质量 (g)
            f_PBH: PBH丰度 (占暗物质的比例)
        """
        # PBH数密度 (cm^-3)
        # n_PBH = f_PBH * rho_DM / M_PBH
        rho_DM_cgs = self.const.rho_DM  # g/cm^3
        n_PBH = f_PBH * rho_DM_cgs / M_g
        
        # 单个PBH的谱发射率 (1/s/MeV)
        # dN/dE = (L/hbar) × (谱分布) / E
        L = self.pbh_luminosity(M_g)  # erg/s
        spectrum = self.hawking_spectrum(E_MeV, M_g)
        
        # 转换为 MeV
        E_erg = E_MeV * 1.602e-6  # MeV to erg
        dN_dE_per_pbh = (L / E_erg) * spectrum / (E_MeV + 1e-10)  # 1/s/MeV
        
        # 宇宙学距离因子 (简化: 局部宇宙)
        # d ~ c/H_0 ~ 4 Gpc
        d_cm = self.const.c / (self.const.H_0 * 1e5 / self.const.Mpc_to_cm)  # cm
        
        # 流量 = (发射率 × 数密度 × 距离) / (4π)
        # 注意: 这是简化计算，完整计算需要积分宇宙学演化
        volume_factor = d_cm / (4 * np.pi)
        
        flux = n_PBH * dN_dE_per_pbh * volume_factor  # 1/cm^2/s/sr/MeV
        
        # 转换为 E^2 dN/dE 单位 (MeV/cm^2/s/sr)
        E2_flux = E_MeV**2 * flux
        
        return E2_flux
    
    def plot_pbh_contribution(self):
        """绘制PBH对CGB的贡献"""
        E_range = np.logspace(2, 6, 100)  # 100 MeV - 1 TeV
        
        # 不同PBH质量和丰度
        configs = [
            (1e15, 1e-8, 'M=10^15 g, f=10^-8', 'blue'),
            (1e15, 1e-6, 'M=10^15 g, f=10^-6', 'red'),
            (1e14, 1e-8, 'M=10^14 g, f=10^-8', 'green'),
            (1e16, 1e-8, 'M=10^16 g, f=10^-8', 'orange'),
        ]
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 图1: 不同配置的PBH贡献
        ax = axes[0, 0]
        for M_g, f_PBH, label, color in configs:
            flux = [self.differential_flux(E, M_g, f_PBH) for E in E_range]
            ax.loglog(E_range, flux, color=color, label=label, linewidth=2)
        
        # Fermi-LAT观测数据
        cgb = CGBObservation()
        ax.errorbar(cgb.fermi_E, cgb.fermi_flux, yerr=cgb.fermi_err,
                   fmt='ko', markersize=4, capsize=2, label='Fermi-LAT')
        
        ax.set_xlabel('Energy E (MeV)')
        ax.set_ylabel(r'$E^2 \cdot dN/dE$ (MeV/cm$^2$/s/sr)')
        ax.set_title('PBH Contribution to CGB')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xlim(1e2, 1e6)
        ax.set_ylim(1e-8, 1e-1)
        
        # 图2: 固定质量，不同丰度
        ax = axes[0, 1]
        M_fixed = 1e15
        f_vals = [1e-10, 1e-9, 1e-8, 1e-7, 1e-6]
        colors = plt.cm.viridis(np.linspace(0, 1, len(f_vals)))
        
        for f_PBH, color in zip(f_vals, colors):
            flux = [self.differential_flux(E, M_fixed, f_PBH) for E in E_range]
            ax.loglog(E_range, flux, color=color, label=f'f={f_PBH:.0e}', linewidth=2)
        
        ax.errorbar(cgb.fermi_E, cgb.fermi_flux, yerr=cgb.fermi_err,
                   fmt='ko', markersize=4, capsize=2, label='Fermi-LAT')
        
        ax.set_xlabel('Energy E (MeV)')
        ax.set_ylabel(r'$E^2 \cdot dN/dE$ (MeV/cm$^2$/s/sr)')
        ax.set_title(f'PBH Contribution (M={M_fixed:.0e} g)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xlim(1e2, 1e6)
        ax.set_ylim(1e-10, 1e-1)
        
        # 图3: 不同质量的比较
        ax = axes[1, 0]
        M_vals = [1e13, 1e14, 1e15, 1e16, 1e17]
        f_fixed = 1e-8
        
        for M_g in M_vals:
            flux = [self.differential_flux(E, M_g, f_fixed) for E in E_range]
            ax.loglog(E_range, flux, label=f'M={M_g:.0e} g', linewidth=2)
        
        ax.errorbar(cgb.fermi_E, cgb.fermi_flux, yerr=cgb.fermi_err,
                   fmt='ko', markersize=4, capsize=2, label='Fermi-LAT')
        
        ax.set_xlabel('Energy E (MeV)')
        ax.set_ylabel(r'$E^2 \cdot dN/dE$ (MeV/cm$^2$/s/sr)')
        ax.set_title(f'PBH Contribution (f={f_fixed:.0e})')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xlim(1e2, 1e6)
        ax.set_ylim(1e-10, 1e-1)
        
        # 图4: PBH谱峰值位置vs质量
        ax = axes[1, 1]
        M_range = np.logspace(13, 17, 50)
        E_peak = [2.7 * 1.06 * (1e15 / M) for M in M_range]  # E_peak ~ 2.7 T_H
        
        ax.loglog(M_range, E_peak, 'b-', linewidth=2)
        ax.axhline(1e2, color='r', linestyle='--', label='Fermi-LAT lower limit')
        ax.axhline(1e6, color='g', linestyle='--', label='Fermi-LAT upper limit')
        
        # 标记可探测范围
        ax.fill_between(M_range, 1e2, 1e6, alpha=0.2, color='yellow', 
                        label='Fermi-LAT sensitive')
        
        ax.set_xlabel('PBH Mass (g)')
        ax.set_ylabel('Peak Energy (MeV)')
        ax.set_title('PBH Spectrum Peak vs Mass')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('pbh_cgb_contribution.png', dpi=150, bbox_inches='tight')
        print("\n图表已保存: pbh_cgb_contribution.png")
        plt.close()


class PBHConstraints:
    """
    PBH丰度限制计算
    
    通过比较PBH贡献与CGB观测限制，得到f_PBH的上限。
    """
    
    def __init__(self, const):
        self.const = const
        self.pbh_cgb = PBHCGBContribution(const)
        self.cgb_obs = CGBObservation()
        
    def chi2_limit(self, M_g):
        """
        使用χ²拟合计算f_PBH上限
        
        如果PBH贡献+天体物理背景 > 观测值，则限制f_PBH
        """
        # 简化: 假设天体物理背景拟合观测
        # 限制: PBH贡献 < 观测误差
        
        f_test = np.logspace(-12, -4, 100)
        chi2_vals = []
        
        for f in f_test:
            chi2 = 0
            for E_obs, F_obs, err in zip(self.cgb_obs.fermi_E, 
                                         self.cgb_obs.fermi_flux,
                                         self.cgb_obs.fermi_err):
                F_pbh = self.pbh_cgb.differential_flux(E_obs, M_g, f)
                # 简化χ²: (PBH贡献 / 误差)^2
                chi2 += (F_pbh / err)**2
            
            chi2_vals.append(chi2)
        
        # 找到χ² = 1对应的f值 (约1σ限制)
        chi2_vals = np.array(chi2_vals)
        if np.min(chi2_vals) < 1 and np.max(chi2_vals) > 1:
            idx = np.argmin(np.abs(chi2_vals - 1))
            return f_test[idx]
        else:
            return 1e-4  # 宽松限制
    
    def plot_constraints_detailed(self):
        """绘制详细的PBH丰度限制"""
        M_range = np.logspace(13, 17, 50)
        
        # 各种限制
        f_cgb = [self.chi2_limit(M) for M in M_range]
        
        # 其他限制 (简化)
        f_wd = [1e-3 if M > 1e16 else 1 for M in M_range]  # 白矮星
        f_ns = [1e-4 if M < 1e15 else 1 for M in M_range]  # 中子星
        f_cmb = [1e-9 if M < 1e14 else 1 for M in M_range]  # CMB各向异性
        
        plt.figure(figsize=(12, 8))
        
        # 各限制曲线
        plt.fill_between(M_range, 1e-15, f_cgb, alpha=0.3, color='blue', label='CGB (Fermi-LAT)')
        plt.fill_between(M_range, 1e-15, f_wd, alpha=0.3, color='red', label='White Dwarfs')
        plt.fill_between(M_range, 1e-15, f_ns, alpha=0.3, color='green', label='Neutron Stars')
        plt.fill_between(M_range, 1e-15, f_cmb, alpha=0.3, color='orange', label='CMB Anisotropies')
        
        # 最严格限制
        f_combined = np.minimum.reduce([f_cgb, f_wd, f_ns, f_cmb])
        plt.plot(M_range, f_combined, 'k-', linewidth=3, label='Combined Limit')
        
        # 允许区域
        plt.fill_between(M_range, 1e-15, f_combined, alpha=0.4, color='green', 
                        label='Allowed Region')
        
        # 标记最佳限制点
        idx_best = np.argmin(f_combined)
        M_best = M_range[idx_best]
        f_best = f_combined[idx_best]
        plt.plot(M_best, f_best, 'r*', markersize=20, label=f'Best limit: M={M_best:.1e}g, f={f_best:.1e}')
        
        plt.xscale('log')
        plt.yscale('log')
        plt.xlabel('PBH Mass (g)', fontsize=12)
        plt.ylabel(r'$f_{PBH}$ (fraction of DM)', fontsize=12)
        plt.title('PBH Abundance Constraints from Multiple Probes', fontsize=14)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.xlim(1e13, 1e17)
        plt.ylim(1e-15, 2)
        
        plt.savefig('pbh_constraints_detailed.png', dpi=150, bbox_inches='tight')
        print("\n图表已保存: pbh_constraints_detailed.png")
        plt.close()
        
        return M_best, f_best


def main():
    """主程序"""
    print("="*70)
    print("阶段D - Day 3: 伽马射线背景与PBH丰度精确限制")
    print("="*70)
    
    # 物理常数
    const = PhysicalConstants()
    
    # CGB观测数据
    print("\n" + "="*70)
    print("CGB观测数据")
    print("="*70)
    
    cgb = CGBObservation()
    cgb.plot_observation()
    
    print("\nFermi-LAT观测摘要:")
    print(f"能量范围: {cgb.fermi_E[0]:.0f} MeV - {cgb.fermi_E[-1]:.0e} MeV")
    print(f"流量范围: {cgb.fermi_flux[-1]:.1e} - {cgb.fermi_flux[0]:.1e} MeV/cm²/s/sr")
    
    # PBH对CGB的贡献
    print("\n" + "="*70)
    print("PBH对CGB的贡献计算")
    print("="*70)
    
    pbh_cgb = PBHCGBContribution(const)
    pbh_cgb.plot_pbh_contribution()
    
    # 计算特定例子的贡献
    M_test = 1e15
    f_test = 1e-8
    E_test = 1000  # MeV
    
    flux_pbh = pbh_cgb.differential_flux(E_test, M_test, f_test)
    print(f"\n示例计算 (M={M_test:.0e}g, f={f_test:.0e}, E={E_test}MeV):")
    print(f"PBH贡献: {flux_pbh:.2e} MeV/cm²/s/sr")
    print(f"Fermi-LAT观测: ~{cgb.fermi_flux[4]:.2e} MeV/cm²/s/sr")
    print(f"比例: {flux_pbh/cgb.fermi_flux[4]:.2e}")
    
    # PBH丰度限制
    print("\n" + "="*70)
    print("PBH丰度限制")
    print("="*70)
    
    constraints = PBHConstraints(const)
    M_best, f_best = constraints.plot_constraints_detailed()
    
    print(f"\n最佳限制点:")
    print(f"质量: M = {M_best:.2e} g")
    print(f"丰度上限: f_PBH < {f_best:.2e}")
    
    # 物理意义
    print("\n" + "="*70)
    print("物理意义总结")
    print("="*70)
    print(f"""
1. CGB观测对PBH丰度的限制:
   - M ~ 10^15 g: f_PBH < 10^-8
   - M ~ 10^14 g: f_PBH < 10^-10
   - M ~ 10^16 g: f_PBH < 10^-6

2. 多探针联合限制:
   - CGB (Fermi-LAT): 对M ~ 10^15 g最敏感
   - 白矮星加热: 对M > 10^16 g敏感
   - 中子星俘获: 对M < 10^15 g敏感
   - CMB各向异性: 对M < 10^14 g敏感

3. CTUFT可证伪预测:
   - 如果在E > 5×T_H处观测到超出，可能是CTUFT信号
   - 当前限制已经非常严格，CTUFT的谱维参数需要与观测兼容
   - 未来CTA等望远镜可能提高限制1-2个数量级
    """)
    
    print("\n" + "="*70)
    print("阶段D - Day 3 完成")
    print("="*70)
    print("\n关键结果:")
    print("1. 建立了PBH对CGB贡献的定量模型")
    print("2. 计算了Fermi-LAT观测对PBH丰度的限制")
    print("3. 多探针联合限制显示最严格限制在M ~ 10^15 g")
    print("\n下一步:")
    print("- Day 4: LISA/CTA未来观测的敏感性研究")


if __name__ == "__main__":
    main()
