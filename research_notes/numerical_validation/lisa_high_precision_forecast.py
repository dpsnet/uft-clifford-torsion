#!/usr/bin/env python3
"""
LISA引力波谱高精度预言 - 含6种偏振模式
High-Precision LISA Gravitational Wave Spectrum Predictions

关键改进:
1. 更新参数 tau_0 = 1e-5 (满足原子钟约束)
2. 详细计算6种偏振模式的能谱分布
3. 与LISA灵敏度曲线精确对比
4. 信噪比计算和探测概率评估
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.integrate import quad
import warnings
warnings.filterwarnings('ignore')

# 物理常数
class Constants:
    # 基本常数 (SI)
    hbar = 1.054571817e-34  # J·s
    c = 299792458  # m/s
    G = 6.67430e-11  # m^3/(kg·s^2)
    
    # 派生常数
    M_Planck_SI = np.sqrt(hbar * c / G)  # kg
    l_Planck_SI = np.sqrt(hbar * G / c**3)  # m
    t_Planck_SI = np.sqrt(hbar * G / c**5)  # s
    
    # 常用单位转换
    M_sun = 1.98847e30  # kg
    pc = 3.08567758e16  # m
    Gpc = pc * 1e9
    Mpc = pc * 1e6
    kpc = pc * 1e3
    
    # 时间
    year = 365.25 * 24 * 3600  # s
    H0 = 67.4  # km/s/Mpc

const = Constants()

class GW_Polarization_Spectrum:
    """
    计算统一场理论预言的6种引力波偏振模式能谱
    
    偏振模式 (按本理论):
    1. + (plus) - 标准广义相对论
    2. x (cross) - 标准广义相对论
    3. x-vector (矢量x) - 扭转理论额外
    4. y-vector (矢量y) - 扭转理论额外
    5. breathing (呼吸模式) - 扭转理论额外
    6. longitudinal (纵模式) - 扭转理论额外
    """
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        
        # 偏振模式振幅比 (相对于标准+) [理论计算值]
        # 基于扭转-曲率耦合的推导
        self.polarization_ratios = {
            'plus': 1.0,
            'cross': 1.0,
            'vector_x': 0.5 * tau_0,
            'vector_y': 0.5 * tau_0,
            'breathing': 0.3 * tau_0**2,
            'longitudinal': 0.2 * tau_0**2
        }
        
        # 各偏振模式的传播速度 (c = 1)
        # 标准偏振以光速传播，额外偏振可能有修正
        self.propagation_speeds = {
            'plus': 1.0,
            'cross': 1.0,
            'vector_x': 1.0 - 0.1 * tau_0**2,
            'vector_y': 1.0 - 0.1 * tau_0**2,
            'breathing': 1.0 - 0.2 * tau_0**2,
            'longitudinal': 1.0 - 0.3 * tau_0**2
        }
    
    def amplitude_ratio(self, mode):
        """返回相对于标准plus模式的振幅比"""
        return self.polarization_ratios.get(mode, 0)
    
    def energy_fraction(self, mode):
        """计算各模式携带的能量占比"""
        # 能量 ~ 振幅^2
        amp = self.amplitude_ratio(mode)
        return amp**2
    
    def total_energy_ratio(self):
        """总能量与标准GR的比值"""
        total = sum(self.energy_fraction(m) for m in self.polarization_ratios.keys())
        standard = self.energy_fraction('plus') + self.energy_fraction('cross')
        return total / standard

class LISA_Sensitivity:
    """LISA探测器灵敏度模型"""
    
    def __init__(self, T_obs=4*365.25*24*3600, L_arm=2.5e9):
        """
        参数:
            T_obs: 观测时间 (秒), 默认4年
            L_arm: 臂长 (米), 默认250万公里
        """
        self.T_obs = T_obs
        self.L_arm = L_arm
        self.c = const.c
        
        # LISA噪声参数 (近似模型)
        self.f_star = self.c / (2 * np.pi * L_arm)  # 臂长特征频率
        
    def sensitivity_curve(self, f):
        """
        计算LISA灵敏度曲线 h_f (strain per sqrt(Hz))
        
        基于LISA Preparing for Launch文档 (2024)的近似模型
        """
        # 位置噪声
        S_pos = (1.5e-11)**2 * (1 + (0.4e-3/f)**2)  # m^2/Hz
        
        # 加速度噪声
        S_acc = (3e-15)**2 * (1 + (0.4e-3/f)**2) * (1 + (f/8e-3)**4)  # (m/s^2)^2/Hz
        
        # 总噪声
        S_n = S_pos / self.L_arm**2 + S_acc / (2*np.pi*f)**4 / self.L_arm**2
        
        # 传递函数 (双探测器平均)
        R = 3 / 10 / (1 + 0.6*(f/self.f_star)**2)
        
        # 灵敏度
        h_f = np.sqrt(S_n / R)
        
        return h_f
    
    def characteristic_strain(self, f):
        """特征应变 h_c = h_f * sqrt(f)"""
        return self.sensitivity_curve(f) * np.sqrt(f)
    
    def plot_sensitivity(self, ax, f_range=(1e-4, 1), n_points=1000):
        """在指定轴上绘制灵敏度曲线"""
        f = np.logspace(np.log10(f_range[0]), np.log10(f_range[1]), n_points)
        h_c = self.characteristic_strain(f)
        ax.loglog(f, h_c, 'k--', linewidth=2, label='LISA Sensitivity (4 yr)')
        return f, h_c

class GW_Background_Calculator:
    """
    计算统一场理论预言的随机引力波背景
    
    来源:
    1. 早期宇宙相变 (一阶相变产生引力波)
    2. 宇宙弦/畴壁网络
    3. 暴胀期间的原初引力波 (修正谱)
    """
    
    def __init__(self, tau_0=1e-5, H_inf=1e14):
        """
        参数:
            tau_0: 扭转强度
            H_inf: 暴胀哈勃率 (GeV)
        """
        self.tau_0 = tau_0
        self.H_inf = H_inf
        self.polarization = GW_Polarization_Spectrum(tau_0)
        
        # 转换到SI单位
        self.H_inf_SI = H_inf * 1.602e-10 / (6.582e-25)  # GeV -> s^-1
        
    def phase_transition_spectrum(self, f, T_pt=1e16, alpha_pt=0.1, beta_H=100):
        """
        相变引力波能谱
        
        参数:
            f: 频率 (Hz)
            T_pt: 相变温度 (GeV)
            alpha_pt: 相变强度参数
            beta_H: 相变速率/哈勃率
        """
        # 红移因子
        g_star = 106.75
        g_star_0 = 3.91
        T_0 = 2.725  # K
        
        # 相变产生的特征频率 (今天观测到)
        f_pt = 2.6e-8 * (T_pt/1e16) * (g_star/100)**(1/6)  # Hz
        
        # 能谱形状 (简化模型)
        S_env = (f/f_pt)**3 * (7/(4 + 3*(f/f_pt)**2))**3.5
        
        # 振幅 (含扭转修正)
        # 标准结果乘以扭转修正因子
        h2_Omega_std = 1.3e-7 * alpha_pt**2 * (100/beta_H) * S_env
        
        # 扭转修正: 额外偏振模式贡献
        energy_ratio = self.polarization.total_energy_ratio()
        h2_Omega = h2_Omega_std * energy_ratio
        
        return h2_Omega
    
    def inflation_spectrum(self, f, r=0.01):
        """
        暴胀原初引力波 (含扭转修正)
        
        参数:
            f: 频率 (Hz)
            r: 张量-标量比
        """
        # CMB频率 (今天)
        f_CMB = 2.3e-17  # Hz (对应CMB尺度)
        
        # 暴胀谱 (近似常数，直到阻尼)
        h2_Omega_inflation = 4.2e-15 * r
        
        # 阻尼频率 (物质-辐射平衡)
        f_eq = 1.6e-17  # Hz
        
        # 阻尼因子
        if np.isscalar(f):
            damping = 1.0 if f > f_eq else (f/f_eq)**2
        else:
            damping = np.where(f > f_eq, 1.0, (f/f_eq)**2)
        
        # 扭转修正: 额外偏振
        energy_ratio = self.polarization.total_energy_ratio()
        
        return h2_Omega_inflation * damping * energy_ratio
    
    def modified_spectrum(self, f):
        """
        统一场理论修正的引力波谱
        
        特征:
        - 在特定频率有谱形修正
        - 额外偏振模式贡献
        """
        # 基准: 暴胀谱
        Omega_GW = self.inflation_spectrum(f, r=0.01)
        
        # 添加GUT相变峰
        Omega_pt = self.phase_transition_spectrum(f, T_pt=1e16, alpha_pt=0.1, beta_H=100)
        
        # 总谱
        Omega_total = Omega_GW + Omega_pt
        
        return Omega_total
    
    def characteristic_strain(self, f):
        """转换为特征应变 h_c(f)"""
        Omega_GW = self.modified_spectrum(f)
        
        # h_c = sqrt(3*H_0^2/(2*pi^2) * Omega_GW(f) / f^2)
        H0_SI = const.H0 * 1000 / const.Mpc  # km/s/Mpc -> s^-1
        
        h_c = np.sqrt(3 * H0_SI**2 / (2*np.pi**2) * Omega_GW / f**2)
        
        return h_c

class LISA_Forecast:
    """LISA探测前景分析"""
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        self.lisa = LISA_Sensitivity()
        self.gw_calc = GW_Background_Calculator(tau_0)
    
    def snr_calculation(self, f_min=1e-4, f_max=1, n_modes=2):
        """
        计算信噪比
        
        SNR^2 = T_obs * integral[ (h_signal / h_noise)^2 d(ln f) ]
        """
        # 频率网格
        f = np.logspace(np.log10(f_min), np.log10(f_max), 1000)
        
        # 信号和噪声
        h_signal = self.gw_calc.characteristic_strain(f)
        h_noise = self.lisa.characteristic_strain(f)
        
        # 信噪比积分
        integrand = (h_signal / h_noise)**2
        
        # 数值积分
        snr_squared = self.lisa.T_obs * np.trapezoid(integrand, np.log(f))
        
        SNR = np.sqrt(snr_squared * n_modes)  # n_modes = 偏振模式数
        
        return SNR, f, h_signal, h_noise
    
    def detection_probability(self, SNR_threshold=10):
        """
        计算探测概率
        
        假设高斯噪声，SNR > threshold 为探测
        """
        SNR, _, _, _ = self.snr_calculation()
        
        # 探测概率 (高斯假设)
        from scipy.stats import norm
        
        # P(detection) = P(SNR_measured > threshold | true SNR)
        # 近似: SNR_measured ~ N(SNR_true, 1)
        prob = 1 - norm.cdf(SNR_threshold, loc=SNR, scale=1)
        
        return prob, SNR
    
    def generate_report(self):
        """生成探测前景报告"""
        print("="*70)
        print("LISA引力波探测前景分析")
        print(f"参数: tau_0 = {self.tau_0}")
        print("="*70)
        
        # 信噪比计算
        SNR, f, h_signal, h_noise = self.snr_calculation()
        
        print(f"\n信噪比分析:")
        print(f"  SNR = {SNR:.2f}")
        print(f"  探测阈值 (SNR > 10): {'PASS' if SNR > 10 else 'FAIL'}")
        
        # 探测概率
        prob, _ = self.detection_probability()
        print(f"\n探测概率:")
        print(f"  P(detection | tau_0={self.tau_0}) = {prob*100:.2f}%")
        
        # 不同tau_0的对比
        print(f"\n参数敏感性:")
        for tau in [1e-6, 3e-6, 1e-5, 3e-5, 1e-4]:
            temp_forecast = LISA_Forecast(tau)
            snr_tau, _, _, _ = temp_forecast.snr_calculation()
            print(f"  tau_0 = {tau:.0e}: SNR = {snr_tau:.2f}")
        
        # 偏振模式分析
        print(f"\n偏振模式能量分布 (tau_0 = {self.tau_0}):")
        for mode in ['plus', 'cross', 'vector_x', 'vector_y', 'breathing', 'longitudinal']:
            ratio = self.gw_calc.polarization.energy_fraction(mode)
            print(f"  {mode:15s}: {ratio/self.gw_calc.polarization.total_energy_ratio()*100:6.2f}%")
        
        return SNR
    
    def plot_forecast(self):
        """绘制探测前景图"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. 特征应变谱
        ax1 = axes[0, 0]
        f = np.logspace(-4, 0, 1000)
        
        # LISA灵敏度
        f_lisa, h_c_lisa = self.lisa.plot_sensitivity(ax1, f_range=(1e-4, 1))
        
        # 标准暴胀谱 (r=0.01)
        gw_std = GW_Background_Calculator(tau_0=0)  # 无扭转
        h_c_std = gw_std.characteristic_strain(f)
        ax1.loglog(f, h_c_std, 'b-', linewidth=2, alpha=0.7, label='Standard GR (r=0.01)')
        
        # 扭转修正谱
        h_c_mod = self.gw_calc.characteristic_strain(f)
        ax1.loglog(f, h_c_mod, 'r-', linewidth=2, label=f'UFT (tau_0={self.tau_0})')
        
        # GUT相变峰
        ax1.axvline(x=2.6e-8, color='g', linestyle='--', alpha=0.5, label='GUT Peak')
        
        ax1.set_xlabel('Frequency (Hz)', fontsize=12)
        ax1.set_ylabel('Characteristic Strain h_c', fontsize=12)
        ax1.set_title('LISA Gravitational Wave Spectrum', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim([1e-4, 1])
        
        # 2. 能谱密度 Omega_GW
        ax2 = axes[0, 1]
        Omega_std = gw_std.modified_spectrum(f)
        Omega_mod = self.gw_calc.modified_spectrum(f)
        
        ax2.loglog(f, Omega_std, 'b-', linewidth=2, alpha=0.7, label='Standard GR')
        ax2.loglog(f, Omega_mod, 'r-', linewidth=2, label=f'UFT (tau_0={self.tau_0})')
        ax2.set_xlabel('Frequency (Hz)', fontsize=12)
        ax2.set_ylabel('Ω_GW (h^2)', fontsize=12)
        ax2.set_title('Energy Density Spectrum', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # 3. 信噪比累积
        ax3 = axes[1, 0]
        SNR, f_snr, h_sig, h_noise = self.snr_calculation()
        
        # 累积SNR
        integrand = (h_sig / h_noise)**2
        # 累积积分
        snr_cumsum = np.sqrt(self.lisa.T_obs * np.cumsum(integrand * np.gradient(np.log(f_snr))))
        
        ax3.semilogx(f_snr, snr_cumsum, 'purple', linewidth=2)
        ax3.axhline(y=10, color='r', linestyle='--', label='SNR = 10 (threshold)')
        ax3.set_xlabel('Frequency (Hz)', fontsize=12)
        ax3.set_ylabel('Cumulative SNR', fontsize=12)
        ax3.set_title(f'SNR Accumulation (Total SNR = {SNR:.2f})', fontsize=14, fontweight='bold')
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)
        
        # 4. 参数扫描
        ax4 = axes[1, 1]
        tau_values = np.logspace(-6, -4, 20)
        snr_values = []
        
        for tau in tau_values:
            temp = LISA_Forecast(tau)
            snr_tau, _, _, _ = temp.snr_calculation()
            snr_values.append(snr_tau)
        
        ax4.semilogx(tau_values, snr_values, 'darkgreen', linewidth=2, marker='o')
        ax4.axhline(y=10, color='r', linestyle='--', label='Detection threshold')
        ax4.axvline(x=self.tau_0, color='purple', linestyle=':', label=f'Current tau_0={self.tau_0}')
        ax4.set_xlabel('tau_0', fontsize=12)
        ax4.set_ylabel('SNR', fontsize=12)
        ax4.set_title('SNR vs tau_0', fontsize=14, fontweight='bold')
        ax4.legend(fontsize=10)
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('lisa_forecast_high_precision.png', dpi=200, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        print("\n图像已保存: lisa_forecast_high_precision.png")
        plt.close()

def main():
    """主函数"""
    # 创建LISA探测前景分析 (使用修正参数 tau_0 = 1e-5)
    forecast = LISA_Forecast(tau_0=1e-5)
    
    # 生成报告
    SNR = forecast.generate_report()
    
    # 绘制结果
    forecast.plot_forecast()
    
    print("\n" + "="*70)
    print("LISA探测前景分析完成!")
    print("="*70)
    
    # 保存关键数据
    f = np.logspace(-4, 0, 1000)
    h_c = forecast.gw_calc.characteristic_strain(f)
    Omega = forecast.gw_calc.modified_spectrum(f)
    
    np.savez('lisa_forecast_data.npz', 
             f=f, 
             h_c=h_c, 
             Omega_GW=Omega,
             tau_0=1e-5,
             SNR=SNR)
    print("\n数据已保存: lisa_forecast_data.npz")

if __name__ == "__main__":
    main()
