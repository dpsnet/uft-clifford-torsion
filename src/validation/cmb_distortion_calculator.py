#!/usr/bin/env python3
"""
CMB谱畸变计算
CMB Spectral Distortion Calculation

计算谱维演化对CMB黑体谱的偏离 (μ畸变和y畸变)
"""

import numpy as np
import matplotlib.pyplot as plt

# 物理常数
M_Planck = 1.22e19  # GeV
m_e = 0.511e-3  # GeV, 电子质量
sigma_T = 6.65e-25  # cm^2, 汤姆逊散射截面

# CMB参数
T_CMB = 2.725e-4  # GeV (2.725 K)
n_gamma = 410  # cm^-3, CMB光子数密度

class CMBDistortionCalculator:
    """CMB谱畸变计算器"""
    
    def __init__(self, tau_0=1e-4):
        self.tau_0 = tau_0
        
    def calculate_mu_distortion(self):
        """
        计算化学势畸变 (μ畸变)
        
        μ畸变产生时期: 5×10^4 < z < 2×10^6 (0.5 keV < T < 0.5 MeV)
        机制: 能量注入导致光子化学势偏离零
        
        本理论贡献: 内部空间能量转化为辐射，在特定红移产生额外能量注入
        """
        # 标准μ畸变 (来自暗物质湮灭等)
        mu_standard = 0  # 标准ΛCDM几乎没有μ畸变
        
        # 本理论贡献
        # 内部空间能量在z ~ 10^6 (T ~ 0.5 keV) 附近转化为辐射
        # 这会产生μ畸变
        
        # 简化计算: 假设内部空间能量转化产生能量注入
        # ΔE/E ~ τ_0^2 × (红移因子)
        
        # 红移范围: z = 10^4 到 10^6
        z_min = 5e4
        z_max = 2e6
        
        # 能量注入率 (简化模型)
        energy_injection = self.tau_0**2 * 1e-8  # 归一化因子
        
        # μ畸变振幅 (~能量注入/光子能量)
        mu_distortion = energy_injection * np.log(z_max / z_min)
        
        return mu_distortion
    
    def calculate_y_distortion(self):
        """
        计算y畸变 (Sunyaev-Zeldovich效应)
        
        y畸变产生时期: z < 5×10^4 (T < 0.5 keV)
        机制: 热电子对CMB光子的康普顿散射
        
        本理论贡献: 内部空间能量转化产生热电子
        """
        # 标准y畸变 (来自星系团等)
        y_standard = 1e-6  # 来自星系团的平均贡献
        
        # 本理论贡献 (极小)
        y_distortion = self.tau_0**2 * 1e-10
        
        return y_distortion
    
    def cmb_spectrum(self, nu, T=T_CMB, mu=0, y=0):
        """
        CMB谱 (包含畸变)
        
        参数:
            nu: 频率 (Hz)
            T: 温度
            mu: 化学势畸变
            y: y畸变参数
        
        返回:
            I_nu: 比强度 (W/m^2/sr/Hz)
        """
        h = 6.626e-34  # J·s
        k_B = 1.381e-23  # J/K
        c = 3e8  # m/s
        
        x = h * nu / (k_B * T)  # 无量纲频率
        
        # 黑体谱
        if mu == 0 and y == 0:
            I_nu = (2 * h * nu**3 / c**2) / (np.exp(x) - 1)
        else:
            # Bose-Einstein谱 (有化学势)
            I_nu = (2 * h * nu**3 / c**2) / (np.exp(x + mu) - 1)
        
        return I_nu
    
    def plot_cmb_spectrum(self):
        """绘制CMB谱和畸变"""
        # 频率范围 (0.5 GHz 到 10 THz)
        nu = np.logspace(9, 13, 1000)  # Hz
        
        # 计算各种谱
        I_standard = self.cmb_spectrum(nu, T=T_CMB, mu=0, y=0)
        
        # 本理论预言的畸变
        mu = self.calculate_mu_distortion()
        y = self.calculate_y_distortion()
        
        I_modified_mu = self.cmb_spectrum(nu, T=T_CMB, mu=mu, y=0)
        
        # 相对差异
        delta_I_mu = (I_modified_mu - I_standard) / I_standard
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. CMB谱 (线性)
        axes[0, 0].plot(nu / 1e9, I_standard, 'b-', linewidth=2, label='Standard Blackbody')
        axes[0, 0].plot(nu / 1e9, I_modified_mu, 'r--', linewidth=2, label=f'Modified (μ={mu:.2e})')
        axes[0, 0].set_xlabel('Frequency (GHz)')
        axes[0, 0].set_ylabel('Intensity (W/m²/sr/Hz)')
        axes[0, 0].set_title('CMB Spectrum')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].set_xlim([0, 1000])
        
        # 2. CMB谱 (对数)
        axes[0, 1].loglog(nu, I_standard, 'b-', linewidth=2, label='Standard')
        axes[0, 1].loglog(nu, I_modified_mu, 'r--', linewidth=2, label='Modified')
        axes[0, 1].set_xlabel('Frequency (Hz)')
        axes[0, 1].set_ylabel('Intensity')
        axes[0, 1].set_title('CMB Spectrum (Log)')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 相对差异 (μ畸变)
        axes[1, 0].semilogx(nu, delta_I_mu, 'purple', linewidth=2)
        axes[1, 0].axhline(0, color='k', linestyle='--', alpha=0.5)
        axes[1, 0].set_xlabel('Frequency (Hz)')
        axes[1, 0].set_ylabel('ΔI/I')
        axes[1, 0].set_title(f'μ Distortion Effect (μ={mu:.2e})')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Rayleigh-Jeans区域 (低频)
        nu_RJ = np.logspace(9, 11, 100)  # 1 GHz 到 100 GHz
        I_RJ_std = self.cmb_spectrum(nu_RJ, T=T_CMB)
        I_RJ_mod = self.cmb_spectrum(nu_RJ, T=T_CMB, mu=mu)
        delta_RJ = (I_RJ_mod - I_RJ_std) / I_RJ_std
        
        axes[1, 1].loglog(nu_RJ / 1e9, np.abs(delta_RJ), 'orange', linewidth=2)
        axes[1, 1].axhline(1e-8, color='r', linestyle='--', label='PIXIE sensitivity')
        axes[1, 1].set_xlabel('Frequency (GHz)')
        axes[1, 1].set_ylabel('|ΔI/I|')
        axes[1, 1].set_title('Low Frequency Distortion')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('cmb_distortion.png', dpi=150, bbox_inches='tight')
        print("图像已保存: cmb_distortion.png")
        
        return {
            'mu': mu,
            'y': y,
            'max_delta_I': np.max(np.abs(delta_I_mu))
        }
    
    def check_detectability(self):
        """检查畸变是否可被探测到"""
        mu = self.calculate_mu_distortion()
        y = self.calculate_y_distortion()
        
        print("\nCMB谱畸变探测性分析:")
        print("="*70)
        print(f"理论预言:")
        print(f"  μ畸变: {mu:.2e}")
        print(f"  y畸变: {y:.2e}")
        print()
        
        # 探测器灵敏度
        detectors = [
            ('COBE/FIRAS', 1e-4, 'current'),
            ('PIXIE', 1e-8, 'future'),
            ('CMB-S4', 1e-7, 'future'),
            ('Voyage 2050', 1e-9, 'concept'),
        ]
        
        print(f"{'探测器':<15} {'灵敏度':<15} {'可探测μ?':<10} {'可探测y?':<10}")
        print("-"*70)
        
        for name, sensitivity, status in detectors:
            detect_mu = "是" if mu > sensitivity else "否"
            detect_y = "是" if y > sensitivity else "否"
            print(f"{name:<15} {sensitivity:<15.0e} {detect_mu:<10} {detect_y:<10}")
        
        return mu, y

def main():
    print("="*60)
    print("CMB谱畸变计算")
    print("CMB Spectral Distortion")
    print("="*60)
    
    calc = CMBDistortionCalculator(tau_0=1e-4)
    
    print(f"\n参数: τ_0 = {calc.tau_0}")
    
    # 计算畸变
    result = calc.plot_cmb_spectrum()
    
    # 探测性分析
    mu, y = calc.check_detectability()
    
    print("\n" + "="*60)
    print("计算完成!")
    print("="*60)
    
    if result['max_delta_I'] > 1e-8:
        print("✓ 畸变可能被PIXIE探测到")
    else:
        print("✗ 畸变太小，当前和未来探测器均不可探测")

if __name__ == "__main__":
    main()
