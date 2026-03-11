#!/usr/bin/env python3
"""
下一步: LISA可探测引力波谱计算 (tau_0 = 1e-5)
Next Step: LISA-detectable GW Spectrum Calculation

使用调整后的参数 tau_0 = 10^-5，计算LISA可探测的引力波谱修正
"""

import numpy as np
import matplotlib.pyplot as plt

# 物理常数
M_Planck = 1.22e19  # GeV

class LISADetectableGW:
    """LISA可探测引力波谱计算器"""
    
    def __init__(self, tau_0=1e-5, r=0.01):
        self.tau_0 = tau_0
        self.r = r
        
    def spectral_dimension(self, f):
        """与频率相关的有效谱维"""
        # GUT能标对应的频率
        T_GUT = 1e16  # GeV
        f_GUT = T_GUT * 1.97e16 / (2 * np.pi)  # Hz (转换)
        
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
    
    def omega_gw_standard(self, f):
        """标准暴胀引力波谱"""
        Omega_gamma = 5.4e-5
        f_eq = 1e-16  # Hz
        
        omega = (self.r * Omega_gamma / 24) * np.ones_like(f)
        
        mask_low = f < f_eq
        omega[mask_low] *= (f[mask_low] / f_eq)**2
        
        return omega
    
    def omega_gw_modified(self, f):
        """修正的引力波谱"""
        omega_std = self.omega_gw_standard(f)
        d_s = self.spectral_dimension(f)
        
        f_Planck = M_Planck * 1.97e16 / (2 * np.pi)
        correction = 1.0 + self.tau_0**2 * (f / f_Planck)**(d_s - 4)
        
        return omega_std * correction
    
    def lisa_sensitivity(self, f):
        """LISA灵敏度曲线 (简化模型)"""
        # LISA灵敏度近似
        # 最佳灵敏度在 ~1 mHz
        f_ref = 1e-3  # Hz
        h_ref = 1e-11  # 特征应变
        
        # 近似曲线
        sens = h_ref * ((f / f_ref)**2 + (f_ref / f)**2)
        
        # 转换为能量密度
        # Omega_GW ~ h^2 * f^2
        omega_sens = sens**2 * (f / f_ref)**2 * 1e-12
        
        return omega_sens
    
    def calculate_lisa_band(self):
        """计算LISA频段内的信号"""
        # LISA频段: 0.1 mHz 到 1 Hz
        f_min = 1e-4  # Hz
        f_max = 1e0   # Hz
        
        f = np.logspace(np.log10(f_min), np.log10(f_max), 500)
        
        omega_std = self.omega_gw_standard(f)
        omega_mod = self.omega_gw_modified(f)
        omega_lisa = self.lisa_sensitivity(f)
        
        return {
            'f': f,
            'omega_std': omega_std,
            'omega_mod': omega_mod,
            'omega_lisa': omega_lisa,
            'signal_to_noise': omega_mod / omega_lisa
        }
    
    def plot_lisa_spectrum(self):
        """绘制LISA频段引力波谱"""
        results = self.calculate_lisa_band()
        f = results['f']
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # 1. 引力波能量密度谱
        axes[0].loglog(f, results['omega_std'], 'b-', linewidth=2, label='Standard Inflation')
        axes[0].loglog(f, results['omega_mod'], 'r--', linewidth=2, label=f'Modified (tau_0={self.tau_0})')
        axes[0].loglog(f, results['omega_lisa'], 'g:', linewidth=2, label='LISA Sensitivity')
        
        axes[0].set_xlabel('Frequency (Hz)')
        axes[0].set_ylabel('Omega_GW(f)')
        axes[0].set_title('LISA-band Gravitational Wave Spectrum')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        axes[0].set_ylim([1e-20, 1e-8])
        
        # 2. 信噪比
        snr = results['omega_mod'] / results['omega_lisa']
        axes[1].semilogx(f, snr, 'purple', linewidth=2)
        axes[1].axhline(1.0, color='r', linestyle='--', label='SNR = 1 (threshold)')
        axes[1].axhline(5.0, color='orange', linestyle='--', label='SNR = 5 (detection)')
        axes[1].set_xlabel('Frequency (Hz)')
        axes[1].set_ylabel('Signal-to-Noise Ratio')
        axes[1].set_title('LISA Detectability')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('lisa_gw_spectrum.png', dpi=150, bbox_inches='tight')
        print("\n图像已保存: lisa_gw_spectrum.png")
        
        return results
    
    def calculate_snr(self):
        """计算总信噪比"""
        results = self.calculate_lisa_band()
        
        # 简单积分 SNR
        snr_per_bin = results['omega_mod'] / results['omega_lisa']
        snr_total = np.sqrt(np.sum(snr_per_bin**2)) / np.sqrt(len(snr_per_bin))
        
        max_snr = np.max(snr_per_bin)
        
        return snr_total, max_snr, results

def main():
    print("="*60)
    print("下一步: LISA可探测引力波谱")
    print("参数: tau_0 = 10^-5")
    print("="*60)
    
    calc = LISADetectableGW(tau_0=1e-5, r=0.01)
    
    # 计算并绘图
    results = calc.plot_lisa_spectrum()
    
    # 计算SNR
    snr_total, max_snr, _ = calc.calculate_snr()
    
    print("\nLISA探测分析:")
    print("="*60)
    print(f"参数: tau_0 = {calc.tau_0}")
    print(f"张量-标量比: r = {calc.r}")
    print()
    print(f"最大信噪比 (单频): {max_snr:.2f}")
    print(f"总信噪比 (宽带): {snr_total:.2f}")
    print()
    
    if max_snr > 5:
        print("✓ LISA可以探测到引力波谱修正 (SNR > 5)")
    elif max_snr > 1:
        print("⚠ LISA可能探测到引力波谱修正 (SNR > 1)")
    else:
        print("✗ LISA无法探测到引力波谱修正 (SNR < 1)")
    
    # 对比不同tau_0
    print("\n不同tau_0的对比:")
    print("-"*60)
    print(f"{'tau_0':<12} {'Max SNR':<12} {'Detectable?':<15}")
    print("-"*60)
    
    for tau in [1e-6, 1e-5, 1e-4]:
        c = LISADetectableGW(tau_0=tau, r=0.01)
        _, max_s, _ = c.calculate_snr()
        det = "是" if max_s > 5 else ("可能" if max_s > 1 else "否")
        print(f"{tau:<12.0e} {max_s:<12.2f} {det:<15}")
    
    print("\n" + "="*60)
    print("下一步计算完成!")
    print("="*60)

if __name__ == "__main__":
    main()
