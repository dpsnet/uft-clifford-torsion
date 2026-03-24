#!/usr/bin/env python3
"""
原初引力波谱修正计算
Primordial Gravitational Wave Spectrum Modification

计算谱维演化对原初引力波谱的影响
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

# 物理常数
M_Planck = 1.22e19  # GeV
m_planck_kg = 2.18e-8  # kg
hbar = 1.055e-34  # J·s
c = 3e8  # m/s
G = 6.674e-11  # m^3 kg^-1 s^-2

# 转换因子
GeV_to_J = 1.602e-10
GeV_to_m = 1.97e-16  # 1 GeV^-1
GeV_to_s = 6.58e-25  # 1 GeV^-1
GeV_to_Hz = 1 / GeV_to_s

class GWSpectrumCalculator:
    """原初引力波谱计算器"""
    
    def __init__(self, tau_0=1e-4, r=0.01):
        """
        参数:
            tau_0: 扭转参数
            r: 张量-标量比 (r = P_t / P_s), 当前观测限制 r < 0.036
        """
        self.tau_0 = tau_0
        self.r = r
        self.H_inf = 1e13  # GeV, 暴胀时期的哈勃参数 (示例值)
        
    def spectral_dimension(self, f):
        """
        与频率相关的有效谱维
        
        物理图像:
        - 高频 (f > f_GUT): 对应早期宇宙高谱维时期, d_s ≈ 10
        - 低频 (f < f_GUT): 对应后期低谱维时期, d_s ≈ 4
        """
        # GUT能标对应的频率
        T_GUT = 1e16  # GeV
        f_GUT = T_GUT * GeV_to_Hz / (2 * np.pi)  # Hz
        
        if np.isscalar(f):
            if f > f_GUT * 10:
                return 10.0
            elif f < f_GUT / 10:
                return 4.0
            else:
                x = np.log10(f / f_GUT)
                return 4.0 + 6.0 / (1.0 + np.exp(-2.0 * x))
        else:
            d_s = np.ones_like(f) * 4.0
            mask_high = f > f_GUT * 10
            mask_low = f < f_GUT / 10
            mask_trans = ~mask_high & ~mask_low
            
            d_s[mask_high] = 10.0
            d_s[mask_trans] = 4.0 + 6.0 / (1.0 + np.exp(-2.0 * np.log10(f[mask_trans] / f_GUT)))
            return d_s
    
    def omega_gw_standard(self, f, H_inf=None):
        """
        标准暴胀预言的原初引力波谱
        
        对于慢滚暴胀:
        Ω_GW(f) ≈ (r × Ω_γ / 24) × (f/f_eq)^2  (f < f_eq)
        Ω_GW(f) ≈ (r × Ω_γ / 24)              (f > f_eq)
        
        其中:
        - Ω_γ ≈ 5.4e-5 (今天辐射能量密度参数)
        - f_eq ≈ 1e-16 Hz (物质-辐射平衡频率)
        """
        if H_inf is None:
            H_inf = self.H_inf
            
        Omega_gamma = 5.4e-5  # 今天辐射能量密度参数
        f_eq = 1e-16  # Hz, 物质-辐射平衡频率
        
        # 计算引力波能量密度
        # 简化模型: 暴胀产生的引力波在今天的能量密度
        omega = (self.r * Omega_gamma / 24) * np.ones_like(f)
        
        # 低频修正 (f < f_eq)
        mask_low = f < f_eq
        omega[mask_low] *= (f[mask_low] / f_eq)**2
        
        # 高频截断 (f > f_reheat, 再加热频率)
        f_reheat = H_inf * GeV_to_Hz / (2 * np.pi)
        mask_high = f > f_reheat
        omega[mask_high] *= np.exp(-(f[mask_high] / f_reheat))
        
        return omega
    
    def omega_gw_modified(self, f, H_inf=None):
        """
        修正的原初引力波谱 (包含谱维效应)
        
        修正公式:
        Ω_GW^mod(f) = Ω_GW^std(f) × [1 + τ_0^2 × (f/f_Planck)^(d_s(f)-4)]
        
        物理意义:
        - 高频部分受到谱维影响更大 (d_s > 4)
        - 产生特征性的"隆起"或"截断"
        """
        omega_std = self.omega_gw_standard(f, H_inf)
        d_s = self.spectral_dimension(f)
        
        # 普朗克频率
        f_Planck = M_Planck * GeV_to_Hz / (2 * np.pi)
        
        # 修正因子
        correction = 1.0 + self.tau_0**2 * (f / f_Planck)**(d_s - 4)
        
        return omega_std * correction
    
    def calculate_spectrum(self, f_min=1e-20, f_max=1e10, n_points=1000):
        """计算完整频谱"""
        f = np.logspace(np.log10(f_min), np.log10(f_max), n_points)
        
        omega_std = self.omega_gw_standard(f)
        omega_mod = self.omega_gw_modified(f)
        d_s = self.spectral_dimension(f)
        
        return {
            'f': f,
            'omega_std': omega_std,
            'omega_mod': omega_mod,
            'd_s': d_s,
            'ratio': omega_mod / omega_std
        }
    
    def plot_spectrum(self):
        """绘制引力波谱对比"""
        results = self.calculate_spectrum()
        f = results['f']
        omega_std = results['omega_std']
        omega_mod = results['omega_mod']
        d_s = results['d_s']
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 引力波能量密度谱
        axes[0, 0].loglog(f, omega_std, 'b-', linewidth=2, label='Standard Inflation')
        axes[0, 0].loglog(f, omega_mod, 'r--', linewidth=2, label='Modified (This Theory)')
        
        # 添加探测器灵敏度曲线 (近似)
        # LISA灵敏度 (近似)
        f_LISA = np.logspace(-4, 0, 100)
        Omega_LISA = 1e-11 * (f_LISA / 1e-3)**2  # 简化模型
        axes[0, 0].loglog(f_LISA, Omega_LISA, 'g:', alpha=0.5, label='LISA (sens.)')
        
        # PTA灵敏度 (近似)
        f_PTA = np.logspace(-9, -7, 100)
        Omega_PTA = 1e-9 * np.ones_like(f_PTA)
        axes[0, 0].loglog(f_PTA, Omega_PTA, 'm:', alpha=0.5, label='PTA (sens.)')
        
        axes[0, 0].set_xlabel('Frequency (Hz)')
        axes[0, 0].set_ylabel('Ω_GW(f)')
        axes[0, 0].set_title('Primordial Gravitational Wave Spectrum')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].set_ylim([1e-20, 1e-4])
        
        # 2. 修正因子
        ratio = omega_mod / omega_std
        axes[0, 1].semilogx(f, ratio, 'purple', linewidth=2)
        axes[0, 1].axhline(1.0, color='k', linestyle='--', alpha=0.5)
        axes[0, 1].set_xlabel('Frequency (Hz)')
        axes[0, 1].set_ylabel('Ω_GW^mod / Ω_GW^std')
        axes[0, 1].set_title('Modification Factor')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 谱维随频率变化
        axes[1, 0].semilogx(f, d_s, 'orange', linewidth=2)
        axes[1, 0].axhline(4, color='r', linestyle='--', alpha=0.5)
        axes[1, 0].axhline(10, color='b', linestyle='--', alpha=0.5)
        axes[1, 0].set_xlabel('Frequency (Hz)')
        axes[1, 0].set_ylabel('Spectral Dimension d_s')
        axes[1, 0].set_title('d_s vs Frequency')
        axes[1, 0].set_ylim([3.5, 10.5])
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 差异幅度 (Ω_mod - Ω_std)
        diff = omega_mod - omega_std
        axes[1, 1].loglog(f, np.abs(diff), 'brown', linewidth=2)
        axes[1, 1].set_xlabel('Frequency (Hz)')
        axes[1, 1].set_ylabel('|ΔΩ_GW|')
        axes[1, 1].set_title('Absolute Difference')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('gw_spectrum_comparison.png', dpi=150, bbox_inches='tight')
        print("图像已保存: gw_spectrum_comparison.png")
        
        return results
    
    def check_detectability(self):
        """检查修正是否可被当前或未来探测器探测到"""
        results = self.calculate_spectrum()
        f = results['f']
        omega_std = results['omega_std']
        omega_mod = results['omega_mod']
        
        print("\n探测器可及性分析:")
        print("="*70)
        
        # 定义探测器频段和灵敏度 (简化)
        detectors = [
            ('LISA', 1e-4, 1e0, 1e-11),
            ('PTA (current)', 1e-9, 1e-7, 1e-9),
            ('PTA (future)', 1e-9, 1e-7, 1e-11),
            ('CE/ET', 1e0, 1e3, 1e-12),
        ]
        
        print(f"{'探测器':<15} {'频段(Hz)':<20} {'修正幅度':<15} {'可探测?':<10}")
        print("-"*70)
        
        for name, f_min, f_max, sensitivity in detectors:
            # 找到频段内的最大修正
            mask = (f >= f_min) & (f <= f_max)
            if np.any(mask):
                max_ratio = np.max(omega_mod[mask] / omega_std[mask])
                max_diff = np.max(np.abs(omega_mod[mask] - omega_std[mask]))
                
                # 检查是否超过灵敏度
                detectable = "是" if max_diff > sensitivity else "否"
                
                print(f"{name:<15} {f_min:.0e}-{f_max:.0e}      {max_ratio-1:.2e}        {detectable:<10}")
            else:
                print(f"{name:<15} {f_min:.0e}-{f_max:.0e}      N/A            频段外")

def main():
    print("="*60)
    print("原初引力波谱修正计算")
    print("Primordial Gravitational Wave Spectrum")
    print("="*60)
    
    # 创建计算器
    calc = GWSpectrumCalculator(tau_0=1e-4, r=0.01)
    
    print(f"\n参数设置:")
    print(f"  扭转参数 τ_0 = {calc.tau_0}")
    print(f"  张量-标量比 r = {calc.r}")
    print(f"  暴胀哈勃参数 H_inf = {calc.H_inf:.2e} GeV")
    
    # 计算并绘图
    results = calc.plot_spectrum()
    
    # 探测器可及性
    calc.check_detectability()
    
    print("\n计算完成!")
    print("="*60)

if __name__ == "__main__":
    main()
