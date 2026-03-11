#!/usr/bin/env python3
"""
CMB谱畸变计算 - 简化版
CMB Spectral Distortion Calculation (Simplified)
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 物理常数
T_CMB = 2.725  # K

class CMBDistortionCalculator:
    def __init__(self, tau_0=1e-4):
        self.tau_0 = tau_0
        
    def calculate_mu_distortion(self):
        """计算化学势畸变"""
        # 简化模型: μ ~ τ_0^2 × ln(z_max/z_min)
        energy_injection = self.tau_0**2 * 1e-10
        mu = energy_injection * np.log(2e6 / 5e4)
        return mu
    
    def plot_results(self):
        """绘制结果"""
        mu = self.calculate_mu_distortion()
        
        # 频率 (GHz)
        nu = np.linspace(0.5, 1000, 500)
        
        # 简化CMB谱 (Rayleigh-Jeans近似 I ~ ν² for low freq)
        x = nu / 56.8  # hν/kT
        I_std = x**2 / (np.exp(x) - 1)
        I_mod = x**2 / (np.exp(x + mu) - 1) if mu > 1e-20 else I_std
        
        # 相对差异
        delta = (I_mod - I_std) / I_std if mu > 1e-20 else np.zeros_like(I_std)
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # 谱对比
        axes[0].plot(nu, I_std, 'b-', linewidth=2, label='Standard')
        axes[0].plot(nu, I_mod, 'r--', linewidth=2, label=f'Modified (μ={mu:.2e})')
        axes[0].set_xlabel('Frequency (GHz)')
        axes[0].set_ylabel('Intensity (arb. units)')
        axes[0].set_title('CMB Spectrum')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # 相对差异
        axes[1].semilogy(nu, np.abs(delta) + 1e-20, 'purple', linewidth=2)
        axes[1].axhline(1e-8, color='r', linestyle='--', label='PIXIE sensitivity')
        axes[1].axhline(1e-4, color='g', linestyle='--', label='COBE/FIRAS')
        axes[1].set_xlabel('Frequency (GHz)')
        axes[1].set_ylabel('|ΔI/I|')
        axes[1].set_title('Spectral Distortion')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('cmb_distortion_simple.png', dpi=150, bbox_inches='tight')
        
        return mu

def main():
    print("="*60)
    print("CMB谱畸变计算 (简化版)")
    print("="*60)
    
    calc = CMBDistortionCalculator(tau_0=1e-4)
    mu = calc.plot_results()
    
    print(f"\n理论预言 μ畸变: {mu:.2e}")
    print(f"\n探测器灵敏度:")
    print(f"  COBE/FIRAS (已实现): 10⁻⁴")
    print(f"  PIXIE (未来): 10⁻⁸")
    print(f"  Voyage 2050 (概念): 10⁻⁹")
    
    if mu > 1e-8:
        print("\n✓ 可能被PIXIE探测到")
    elif mu > 1e-9:
        print("\n⚠ 可能被未来概念探测器探测到")
    else:
        print("\n✗ 当前和未来探测器均不可探测")
    
    print("\n图像已保存: cmb_distortion_simple.png")
    print("="*60)

if __name__ == "__main__":
    main()
