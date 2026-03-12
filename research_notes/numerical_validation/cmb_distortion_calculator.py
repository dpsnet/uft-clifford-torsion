#!/usr/bin/env python3
"""
CMB (宇宙微波背景) 谱畸变计算
CMB Spectral Distortion Calculations

计算统一场理论预言的CMB谱畸变:
1. μ-畸变 (化学势畸变) - 高能光子注入
2. y-畸变 (热康普顿畸变) - SZ效应
3. 非高斯性 f_NL 修正

与COBE/FIRAS、PIXIE、Super-PIXIE等实验的灵敏度对比
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import quad
from scipy.special import zeta
import warnings
warnings.filterwarnings('ignore')

# 物理常数
class Constants:
    # 基本常数
    h = 6.62607015e-34  # J·s
    hbar = 1.054571817e-34  # J·s
    c = 299792858  # m/s
    k_B = 1.380649e-23  # J/K
    
    # 派生常数
    T_CMB = 2.725  # K, CMB温度
    h_planck = 6.626e-34
    
    # 转换因子
    eV_to_J = 1.602176634e-19
    eV_to_K = 1.16045e4  # 1 eV = 1.16e4 K
    
    # 宇宙学参数
    H0 = 67.4  # km/s/Mpc
    Omega_b = 0.0493
    Omega_m = 0.315
    Omega_gamma = 5.38e-5
    
    # 粒子物理
    m_e = 511e3  # eV, 电子质量
    sigma_T = 6.652e-25  # cm^2, 汤姆逊散射截面
    
    # 热力学
    a_rad = 7.5657e-15  # erg/cm^3/K^4, 辐射常数

const = Constants()

class CMB_Distortion:
    """
    CMB谱畸变计算器
    
    畸变类型:
    - μ-畸变: 化学势畸变，发生在红移 z = 5e4 - 2e6
    - y-畸变: 康普顿y参数，发生在红移 z < 5e4
    """
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        
    def planck_spectrum(self, x):
        """
        普朗克黑体谱 (无量纲频率 x = hν/kT)
        
        B_ν = (2hν³/c²) / (exp(x) - 1)
        """
        return x**3 / (np.exp(x) - 1)
    
    def mu_distortion_spectrum(self, x, mu):
        """
        μ-畸变谱
        
        I(x) = I_0(x) * exp(-μ/x) / (exp(x) - 1)
        
        对于小μ:
        ΔI/I ≈ μ / (exp(x) - 1) * (x coth(x/2) - 4)
        """
        if np.isscalar(x):
            x = np.array([x])
        
        # 避免除零
        x_safe = np.where(x < 0.01, 0.01, x)
        
        # μ-畸变谱形
        # Bose-Einstein分布偏离
        base = self.planck_spectrum(x_safe)
        correction = mu * (x_safe / np.tanh(x_safe/2) - 4) / (np.exp(x_safe) - 1)
        
        return base + correction
    
    def y_distortion_spectrum(self, x, y):
        """
        y-畸变谱 (SZ效应)
        
        ΔI/I = y * (x coth(x/2) - 4)
        """
        if np.isscalar(x):
            x = np.array([x])
        
        x_safe = np.where(x < 0.01, 0.01, x)
        
        base = self.planck_spectrum(x_safe)
        correction = y * x_safe * (x_safe * np.exp(x_safe) / (np.exp(x_safe) - 1)**2 - 
                                   1 / (np.exp(x_safe) - 1))
        
        return base + correction
    
    def uft_mu_distortion(self):
        """
        统一场理论预言的μ-畸变
        
        来源: 早期宇宙内部空间能量释放
        
        μ ~ 1.4 * (E_injected / E_CMB) 在 z = 5e4 - 2e6
        """
        # 注入能量比例
        # 来自内部空间能量释放
        f_injected = 0.1 * self.tau_0**2  # 假设10%的内部空间能量转化为CMB
        
        # μ-畸变幅度
        mu = 1.4 * f_injected
        
        return mu
    
    def uft_y_distortion(self):
        """
        统一场理论预言的y-畸变
        
        来源: 晚期能量释放 (z < 5e4)
        """
        # y参数
        # 与扭转场能量密度相关
        y = 1e-7 * self.tau_0**2
        
        return y
    
    def uft_spectral_index_running(self):
        """
        谱指数跑动 (n_s run)
        
        统一场理论预言的额外跑动
        """
        # 标准跑动
        dn_s_dlnk_std = -0.0005
        
        # 扭转修正
        dn_s_dlnk_uft = dn_s_dlnk_std + 0.01 * self.tau_0
        
        return dn_s_dlnk_uft

class CMB_Experiments:
    """
    CMB实验灵敏度
    
    支持:
    - COBE/FIRAS (已完成)
    - PIXIE (拟议)
    - Super-PIXIE (概念)
    - PRISM (概念)
    """
    
    def __init__(self, experiment='FIRAS'):
        self.experiment = experiment
        self.setup_experiment()
    
    def setup_experiment(self):
        """设置实验参数"""
        params = {
            'FIRAS': {
                'mu_limit': 9e-5,  # 95% CL
                'y_limit': 1.5e-5,
                'frequency_range': (60, 6000),  # GHz
                'sensitivity': 1e-7,  # 相对灵敏度
            },
            'PIXIE': {
                'mu_limit': 5e-8,
                'y_limit': 1e-8,
                'frequency_range': (30, 6000),
                'sensitivity': 1e-9,
            },
            'Super-PIXIE': {
                'mu_limit': 1e-9,
                'y_limit': 1e-10,
                'frequency_range': (10, 10000),
                'sensitivity': 1e-11,
            },
            'PRISM': {
                'mu_limit': 5e-9,
                'y_limit': 5e-10,
                'frequency_range': (10, 10000),
                'sensitivity': 1e-11,
            }
        }
        
        p = params.get(self.experiment, params['FIRAS'])
        self.mu_limit = p['mu_limit']
        self.y_limit = p['y_limit']
        self.freq_range = p['frequency_range']
        self.sensitivity = p['sensitivity']

class UFT_CMB_Signals:
    """
    统一场理论CMB信号计算器
    """
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        self.distortion = CMB_Distortion(tau_0)
    
    def calculate_all_signals(self):
        """计算所有CMB信号"""
        signals = {}
        
        # 1. μ-畸变
        signals['mu'] = self.distortion.uft_mu_distortion()
        
        # 2. y-畸变
        signals['y'] = self.distortion.uft_y_distortion()
        
        # 3. 谱指数跑动
        signals['dn_s_dlnk'] = self.distortion.uft_spectral_index_running()
        
        return signals
    
    def check_detectability(self):
        """检查各实验的可探测性"""
        signals = self.calculate_all_signals()
        
        experiments = ['FIRAS', 'PIXIE', 'Super-PIXIE', 'PRISM']
        
        results = {}
        
        for exp_name in experiments:
            exp = CMB_Experiments(exp_name)
            
            # μ-畸变
            mu_detectable = signals['mu'] > exp.mu_limit
            
            # y-畸变
            y_detectable = signals['y'] > exp.y_limit
            
            results[exp_name] = {
                'mu_limit': exp.mu_limit,
                'mu_signal': signals['mu'],
                'mu_detectable': mu_detectable,
                'y_limit': exp.y_limit,
                'y_signal': signals['y'],
                'y_detectable': y_detectable,
            }
        
        return results, signals
    
    def generate_report(self):
        """生成CMB探测前景报告"""
        print("="*70)
        print("CMB谱畸变探测前景分析")
        print(f"参数: tau_0 = {self.tau_0}")
        print("="*70)
        
        signals = self.calculate_all_signals()
        
        print("\n统一场理论预言的CMB信号:")
        print("-"*70)
        print(f"μ-畸变:     μ = {signals['mu']:.2e}")
        print(f"y-畸变:     y = {signals['y']:.2e}")
        print(f"谱指数跑动: dn_s/dlnk = {signals['dn_s_dlnk']:.6f}")
        
        print("\n与实验灵敏度对比:")
        print("-"*70)
        print(f"{'实验':<15} {'μ限制':<12} {'μ可探测?':<10} {'y限制':<12} {'y可探测?':<10}")
        print("-"*70)
        
        results, _ = self.check_detectability()
        
        for exp_name, result in results.items():
            mu_status = "是" if result['mu_detectable'] else "否"
            y_status = "是" if result['y_detectable'] else "否"
            print(f"{exp_name:<15} {result['mu_limit']:<12.0e} {mu_status:<10} {result['y_limit']:<12.0e} {y_status:<10}")
        
        print("\n参数敏感性:")
        print("-"*70)
        
        for tau in [1e-6, 3e-6, 1e-5, 3e-5, 1e-4]:
            temp = UFT_CMB_Signals(tau)
            sig = temp.calculate_all_signals()
            print(f"tau_0 = {tau:.0e}: μ = {sig['mu']:.2e}, y = {sig['y']:.2e}")
    
    def plot_spectra(self):
        """绘制CMB谱畸变"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 频率范围 (无量纲 x = hν/kT)
        x = np.linspace(0.1, 20, 500)
        
        # 1. 黑体谱 vs μ-畸变
        ax1 = axes[0, 0]
        
        I_bb = self.distortion.planck_spectrum(x)
        ax1.plot(x, I_bb, 'k-', linewidth=2, label='Blackbody')
        
        # 不同μ值的畸变
        mu_values = [1e-4, 1e-5, 1e-6]
        colors = ['red', 'blue', 'green']
        
        for mu, color in zip(mu_values, colors):
            I_mu = self.distortion.mu_distortion_spectrum(x, mu)
            ax1.plot(x, I_mu, color=color, linewidth=2, label=f'μ = {mu:.0e}')
        
        # 标记我们的预言
        mu_uft = self.distortion.uft_mu_distortion()
        I_uft = self.distortion.mu_distortion_spectrum(x, mu_uft)
        ax1.plot(x, I_uft, 'purple', linewidth=3, linestyle='--', 
                label=f'UFT (μ={mu_uft:.2e})')
        
        ax1.set_xlabel('x = hν/kT', fontsize=12)
        ax1.set_ylabel('Intensity (arb. units)', fontsize=12)
        ax1.set_title('μ-type Distortion', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # 2. 相对差异
        ax2 = axes[0, 1]
        
        for mu, color in zip(mu_values, colors):
            I_mu = self.distortion.mu_distortion_spectrum(x, mu)
            delta_I = (I_mu - I_bb) / I_bb
            ax2.plot(x, delta_I, color=color, linewidth=2, label=f'μ = {mu:.0e}')
        
        delta_I_uft = (I_uft - I_bb) / I_bb
        ax2.plot(x, delta_I_uft, 'purple', linewidth=3, linestyle='--',
                label=f'UFT (μ={mu_uft:.2e})')
        
        # 标记PIXIE灵敏度
        ax2.axhline(y=1e-7, color='gray', linestyle=':', label='PIXIE sensitivity')
        
        ax2.set_xlabel('x = hν/kT', fontsize=12)
        ax2.set_ylabel('ΔI/I', fontsize=12)
        ax2.set_title('Relative Intensity Change', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # 3. y-畸变
        ax3 = axes[1, 0]
        
        y_values = [1e-4, 1e-5, 1e-6]
        
        for y, color in zip(y_values, colors):
            I_y = self.distortion.y_distortion_spectrum(x, y)
            ax3.plot(x, I_y, color=color, linewidth=2, label=f'y = {y:.0e}')
        
        y_uft = self.distortion.uft_y_distortion()
        I_y_uft = self.distortion.y_distortion_spectrum(x, y_uft)
        ax3.plot(x, I_y_uft, 'purple', linewidth=3, linestyle='--',
                label=f'UFT (y={y_uft:.2e})')
        
        ax3.plot(x, I_bb, 'k-', linewidth=2, label='Blackbody')
        
        ax3.set_xlabel('x = hν/kT', fontsize=12)
        ax3.set_ylabel('Intensity (arb. units)', fontsize=12)
        ax3.set_title('y-type Distortion (SZ effect)', fontsize=14, fontweight='bold')
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)
        
        # 4. 探测前景总结
        ax4 = axes[1, 1]
        
        experiments = ['FIRAS', 'PIXIE', 'Super-PIXIE', 'PRISM']
        mu_limits = [9e-5, 5e-8, 1e-9, 5e-9]
        y_limits = [1.5e-5, 1e-8, 1e-10, 5e-10]
        
        mu_signal = self.distortion.uft_mu_distortion()
        y_signal = self.distortion.uft_y_distortion()
        
        x_pos = np.arange(len(experiments))
        width = 0.35
        
        bars1 = ax4.bar(x_pos - width/2, mu_limits, width, label='μ limit', alpha=0.7)
        bars2 = ax4.bar(x_pos + width/2, y_limits, width, label='y limit', alpha=0.7)
        
        # 标记我们的信号
        ax4.axhline(y=mu_signal, color='red', linestyle='--', linewidth=2, 
                   label=f'UFT μ = {mu_signal:.2e}')
        ax4.axhline(y=y_signal, color='blue', linestyle='--', linewidth=2,
                   label=f'UFT y = {y_signal:.2e}')
        
        ax4.set_ylabel('Distortion Amplitude', fontsize=12)
        ax4.set_title('Experimental Sensitivity vs UFT Predictions', fontsize=14, fontweight='bold')
        ax4.set_xticks(x_pos)
        ax4.set_xticklabels(experiments)
        ax4.set_yscale('log')
        ax4.legend(fontsize=10)
        ax4.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig('cmb_distortion_forecast.png', dpi=200, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        print("\n图像已保存: cmb_distortion_forecast.png")
        plt.close()

def main():
    """主函数"""
    # 创建CMB信号分析
    uft_cmb = UFT_CMB_Signals(tau_0=1e-5)
    
    # 生成报告
    uft_cmb.generate_report()
    
    # 绘制谱图
    uft_cmb.plot_spectra()
    
    print("\n" + "="*70)
    print("CMB谱畸变分析完成!")
    print("="*70)

if __name__ == "__main__":
    main()
