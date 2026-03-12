#!/usr/bin/env python3
"""
PTA (脉冲星计时阵) 引力波背景探测预言
Pulsar Timing Array Gravitational Wave Background Forecast

计算统一场理论在PTA频段 (nHz - μHz) 的引力波背景预言
并与NANOGrav、EPTA、PPTA、CPTA等实验的灵敏度对比
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import warnings
warnings.filterwarnings('ignore')

# 物理常数
class Constants:
    # 基本常数
    c = 299792458  # m/s
    G = 6.67430e-11  # m^3/(kg·s^2)
    M_sun = 1.98847e30  # kg
    
    # 距离单位
    pc = 3.08567758e16  # m
    kpc = pc * 1e3
    Mpc = pc * 1e6
    Gpc = pc * 1e9
    
    # 时间
    year = 365.25 * 24 * 3600  # s
    
    # 宇宙学参数
    H0 = 67.4  # km/s/Mpc
    h = 0.674
    Omega_m = 0.315
    Omega_Lambda = 0.685
    
    # 天文参数
    ms = 1.989e30  # kg, 太阳质量

const = Constants()

class PTA_Sensitivity:
    """
    PTA实验灵敏度模型
    
    支持: NANOGrav, EPTA, PPTA, CPTA (中国脉冲星计时阵)
    """
    
    def __init__(self, experiment='NANOGrav', T_obs=15*const.year, N_pulsars=68):
        """
        参数:
            experiment: 实验名称
            T_obs: 观测时间 (秒)
            N_pulsars: 脉冲星数量
        """
        self.experiment = experiment
        self.T_obs = T_obs
        self.N_pulsars = N_pulsars
        
        # 不同实验的参数
        self.setup_experiment()
    
    def setup_experiment(self):
        """设置实验参数"""
        params = {
            'NANOGrav': {
                'T_obs': 15 * const.year,
                'N_pulsars': 68,
                'sigma_rms': 100e-9,  # 100 ns 计时精度
                'cadence': 2 * const.year,  # 观测频率
            },
            'EPTA': {
                'T_obs': 24 * const.year,
                'N_pulsars': 25,
                'sigma_rms': 200e-9,
                'cadence': 1 * const.year,
            },
                'PPTA': {
                'T_obs': 15 * const.year,
                'N_pulsars': 26,
                'sigma_rms': 150e-9,
                'cadence': 3 * const.year,
            },
            'CPTA': {
                'T_obs': 3 * const.year,  #  FAST早期数据
                'N_pulsars': 5,  # 目前数量，预期增长到50+
                'sigma_rms': 300e-9,  # FAST预期精度
                'cadence': 2 * const.year,
            },
            'IPTA': {  # 国际脉冲星计时阵 (联合)
                'T_obs': 20 * const.year,
                'N_pulsars': 100,
                'sigma_rms': 100e-9,
                'cadence': 2 * const.year,
            }
        }
        
        p = params.get(self.experiment, params['NANOGrav'])
        self.T_obs = p['T_obs']
        self.N_pulsars = p['N_pulsars']
        self.sigma_rms = p['sigma_rms']
        self.cadence = p['cadence']
    
    def characteristic_strain_sensitivity(self, f):
        """
        计算PTA特征应变灵敏度
        
        基于Hellings & Downs 1983; Moore et al. 2015
        
        h_c(f) ~ sigma_rms / (T_obs * sqrt(N_pulsars)) * (f * T_obs)
        """
        # 红噪声和白噪声贡献
        # 简化的灵敏度模型
        
        # 白噪声项
        sigma_t = self.sigma_rms  # 秒
        T = self.T_obs
        N = self.N_pulsars
        
        # 特征频率
        f_min = 1 / T
        
        # Hellings-Downs系数 (空间相关因子)
        A_HD = 1.0  # 近似
        
        # 灵敏度 (粗略估计)
        # 更精确的模型需要完整的噪声功率谱
        h_c_white = sigma_t / (T * np.sqrt(N * A_HD)) * (f / f_min)
        
        # 红噪声 (低频主导)
        # h_c_red ~ f^(-2/3) (对应Omega_GW ~ 常数)
        gamma_red = -2/3
        h_c_red = h_c_white * (f / f_min)**gamma_red * 0.1
        
        # 总灵敏度
        h_c_total = np.sqrt(h_c_white**2 + h_c_red**2)
        
        return h_c_total
    
    def plot_sensitivity(self, ax, f_range=(1e-10, 1e-6), color='blue'):
        """绘制灵敏度曲线"""
        f = np.logspace(np.log10(f_range[0]), np.log10(f_range[1]), 500)
        h_c = self.characteristic_strain_sensitivity(f)
        
        ax.loglog(f, h_c, color=color, linewidth=2, 
                 label=f'{self.experiment} ({self.N_pulsars} pulsars, {self.T_obs/const.year:.0f} yr)')
        return f, h_c

class UFT_GW_Background_PTA:
    """
    统一场理论在PTA频段的引力波背景
    
    来源:
    1. 超大质量双黑洞 (SMBHB) 合并 - 主导
    2. 早期宇宙相变 (GUT, 电弱)
    3. 宇宙弦/畴壁网络
    4. 暴胀原初引力波
    """
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        
    def smbhb_background(self, f):
        """
        超大质量双黑洞背景 (标准天体物理)
        
        特征: h_c ~ f^(-2/3) (啁啾信号叠加)
        """
        # 参考振幅 (来自观测拟合)
        A_smbhb = 1.3e-15  # 在 f = 1/yr
        f_ref = 1 / const.year
        
        h_c = A_smbhb * (f / f_ref)**(-2/3)
        
        return h_c
    
    def phase_transition_pta(self, f, T_pt=1e16, alpha_pt=0.1):
        """
        相变引力波 (PTA频段)
        
        频率红移到今天的PTA频段:
        f_pt(today) ~ 10^-9 Hz * (T_pt/1e16 GeV)
        """
        # 今天的特征频率
        f_pt = 1e-9 * (T_pt / 1e16)  # Hz
        
        # 能谱形状 (峰值在f_pt附近)
        # 简化模型: 高斯峰
        sigma_f = f_pt * 0.5
        peak_amplitude = 5e-16 * alpha_pt**2
        
        h_c = peak_amplitude * np.exp(-0.5 * ((f - f_pt) / sigma_f)**2)
        
        return h_c
    
    def cosmic_string_background(self, f):
        """
        宇宙弦网络引力波
        
        特征: 平坦谱 (h_c ~ 常数) 或 Ω_GW ~ f^0
        """
        # 张力参数 Gμ
        Gmu = 1e-11  # 与CMB约束兼容
        
        # 宇宙弦背景振幅
        A_cs = 1.4e-14 * (Gmu / 1e-11)**0.5
        
        # 谱指数 (平坦)
        h_c = A_cs * np.ones_like(f) if np.isscalar(f) else A_cs * np.ones(len(f))
        
        return h_c
    
    def inflation_tensor_modes(self, f, r=0.01):
        """
        暴胀原初引力波 (张量模式)
        
        在PTA频段非常弱
        """
        # 在CMB尺度 (f ~ 1e-17 Hz) 的振幅
        f_cmb = 1.7e-17  # Hz
        h_c_cmb = 1.3e-15 * np.sqrt(r)
        
        # 红移到PTA频段 (假设平坦谱直到阻尼)
        h_c = h_c_cmb * np.ones_like(f) if np.isscalar(f) else h_c_cmb * np.ones(len(f))
        
        return h_c
    
    def uft_modification(self, f):
        """
        统一场理论修正
        
        效应:
        1. 额外偏振模式 (6种 vs 2种)
        2. 传播速度修正 (色散)
        3. 谱形修正 (高频抑制)
        """
        # 基础背景 (SMBHB主导)
        h_c_base = self.smbhb_background(f)
        
        # 扭转修正因子
        # 在PTA频段，扭转效应表现为色散关系修正
        # 额外偏振模式贡献 ~ tau_0^2
        correction_factor = 1.0 + self.tau_0**2 * 0.5
        
        # 色散导致的频率依赖
        # 高频模式传播更慢，导致振幅下降
        f_damp = 1e-7  # Hz, 特征阻尼频率
        damping = 1 / (1 + (f / f_damp)**2 * self.tau_0**2)
        
        h_c_uft = h_c_base * correction_factor * damping
        
        return h_c_uft
    
    def total_background(self, f):
        """总引力波背景 (统一场理论版本)"""
        h_c_smbhb = self.smbhb_background(f)
        h_c_pt = self.phase_transition_pta(f)
        h_c_cs = self.cosmic_string_background(f)
        h_c_inf = self.inflation_tensor_modes(f)
        
        # 功率叠加
        h_c_total = np.sqrt(h_c_smbhb**2 + h_c_pt**2 + h_c_cs**2 + h_c_inf**2)
        
        # 应用统一场理论修正
        correction = 1.0 + self.tau_0**2 * 0.3
        
        return h_c_total * correction

class PTA_Forecast:
    """PTA探测前景综合分析"""
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        self.gw_bg = UFT_GW_Background_PTA(tau_0)
        
        # 初始化各PTA实验
        self.pta_experiments = {
            'NANOGrav': PTA_Sensitivity('NANOGrav'),
            'EPTA': PTA_Sensitivity('EPTA'),
            'PPTA': PTA_Sensitivity('PPTA'),
            'CPTA': PTA_Sensitivity('CPTA'),
            'IPTA': PTA_Sensitivity('IPTA'),
        }
    
    def calculate_snr(self, experiment_name, f_min=1e-9, f_max=1e-7):
        """
        计算信噪比
        
        SNR^2 = sum over frequencies of (h_signal / h_noise)^2
        """
        pta = self.pta_experiments[experiment_name]
        
        f = np.logspace(np.log10(f_min), np.log10(f_max), 200)
        
        h_signal = self.gw_bg.total_background(f)
        h_noise = pta.characteristic_strain_sensitivity(f)
        
        # 信噪比平方
        snr_sq = np.sum((h_signal / h_noise)**2)
        
        return np.sqrt(snr_sq)
    
    def generate_report(self):
        """生成探测前景报告"""
        print("="*70)
        print("PTA引力波背景探测前景分析")
        print(f"参数: tau_0 = {self.tau_0}")
        print("="*70)
        
        print("\n各PTA实验灵敏度对比:")
        print("-"*70)
        print(f"{'实验':<12} {'脉冲星数':<10} {'观测时间':<12} {'计时精度':<12}")
        print("-"*70)
        
        for name, pta in self.pta_experiments.items():
            print(f"{name:<12} {pta.N_pulsars:<10} {pta.T_obs/const.year:.0f}年{'':<6} {pta.sigma_rms*1e9:.0f} ns{'':<6}")
        
        print("\n信噪比分析:")
        print("-"*70)
        
        for name in self.pta_experiments.keys():
            snr = self.calculate_snr(name)
            status = "可探测" if snr > 3 else "边缘" if snr > 1 else "不可探测"
            print(f"{name:<12} SNR = {snr:.2f}  ({status})")
        
        print("\n统一场理论修正效应:")
        print("-"*70)
        
        f_test = 1e-8  # Hz
        h_c_std = self.gw_bg.smbhb_background(f_test)
        h_c_uft = self.gw_bg.uft_modification(f_test)
        
        print(f"测试频率: {f_test:.0e} Hz")
        print(f"标准背景: h_c = {h_c_std:.2e}")
        print(f"UFT修正:  h_c = {h_c_uft:.2e}")
        print(f"相对修正: {(h_c_uft/h_c_std - 1)*100:.4f}%")
        
        # 不同tau_0的对比
        print("\n参数敏感性 (tau_0 vs SNR in NANOGrav):")
        print("-"*70)
        
        for tau in [1e-6, 3e-6, 1e-5, 3e-5, 1e-4]:
            temp_forecast = PTA_Forecast(tau)
            snr_tau = temp_forecast.calculate_snr('NANOGrav')
            print(f"tau_0 = {tau:.0e}: SNR = {snr_tau:.2f}")
    
    def plot_forecast(self):
        """绘制PTA探测前景图"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 频率范围
        f = np.logspace(-10, -6, 500)
        
        # 1. 各PTA实验灵敏度对比
        ax1 = axes[0, 0]
        
        colors = {'NANOGrav': 'blue', 'EPTA': 'green', 'PPTA': 'red', 
                 'CPTA': 'purple', 'IPTA': 'orange'}
        
        for name, pta in self.pta_experiments.items():
            pta.plot_sensitivity(ax1, color=colors.get(name, 'gray'))
        
        # 引力波背景
        h_c_bg = self.gw_bg.total_background(f)
        ax1.loglog(f, h_c_bg, 'k-', linewidth=3, label='GW Background (UFT)')
        
        ax1.set_xlabel('Frequency (Hz)', fontsize=12)
        ax1.set_ylabel('Characteristic Strain h_c', fontsize=12)
        ax1.set_title('PTA Sensitivity Curves', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim([1e-10, 1e-6])
        
        # 2. 引力波背景成分分解
        ax2 = axes[0, 1]
        
        h_c_smbhb = self.gw_bg.smbhb_background(f)
        h_c_pt = self.gw_bg.phase_transition_pta(f)
        h_c_cs = self.gw_bg.cosmic_string_background(f)
        h_c_inf = self.gw_bg.inflation_tensor_modes(f)
        
        ax2.loglog(f, h_c_smbhb, 'b-', linewidth=2, label='SMBHB (astrophysical)')
        ax2.loglog(f, h_c_pt, 'r-', linewidth=2, label='Phase Transition (GUT)')
        ax2.loglog(f, h_c_cs, 'g-', linewidth=2, label='Cosmic Strings')
        ax2.loglog(f, h_c_inf, 'm-', linewidth=2, label='Inflation (tensor)')
        ax2.loglog(f, h_c_bg, 'k--', linewidth=2, alpha=0.7, label='Total')
        
        ax2.set_xlabel('Frequency (Hz)', fontsize=12)
        ax2.set_ylabel('Characteristic Strain h_c', fontsize=12)
        ax2.set_title('GW Background Components', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # 3. 统一场理论修正效应
        ax3 = axes[1, 0]
        
        h_c_std = self.gw_bg.smbhb_background(f)
        h_c_uft = self.gw_bg.uft_modification(f)
        
        ax3.loglog(f, h_c_std, 'b-', linewidth=2, label='Standard GR')
        ax3.loglog(f, h_c_uft, 'r-', linewidth=2, label=f'UFT (tau_0={self.tau_0})')
        
        # NANOGrav灵敏度
        ng = self.pta_experiments['NANOGrav']
        f_ng, h_c_ng = ng.plot_sensitivity(ax3, color='gray')
        
        ax3.set_xlabel('Frequency (Hz)', fontsize=12)
        ax3.set_ylabel('Characteristic Strain h_c', fontsize=12)
        ax3.set_title('UFT Modification vs Standard GR', fontsize=14, fontweight='bold')
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)
        
        # 4. 信噪比累积
        ax4 = axes[1, 1]
        
        experiments = list(self.pta_experiments.keys())
        snrs = [self.calculate_snr(name) for name in experiments]
        
        colors_list = [colors.get(name, 'gray') for name in experiments]
        bars = ax4.bar(experiments, snrs, color=colors_list, alpha=0.7, edgecolor='black')
        
        # 添加阈值线
        ax4.axhline(y=3, color='r', linestyle='--', linewidth=2, label='Detection threshold (SNR=3)')
        ax4.axhline(y=5, color='orange', linestyle='--', linewidth=2, label='High confidence (SNR=5)')
        
        ax4.set_ylabel('Signal-to-Noise Ratio', fontsize=12)
        ax4.set_title('SNR by PTA Experiment', fontsize=14, fontweight='bold')
        ax4.legend(fontsize=10)
        ax4.grid(True, alpha=0.3, axis='y')
        
        # 在柱状图上添加数值
        for bar, snr in zip(bars, snrs):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{snr:.1f}', ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        plt.savefig('pta_forecast.png', dpi=200, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print("\n图像已保存: pta_forecast.png")
        plt.close()

def main():
    """主函数"""
    # 创建PTA探测前景分析
    forecast = PTA_Forecast(tau_0=1e-5)
    
    # 生成报告
    forecast.generate_report()
    
    # 绘制结果
    forecast.plot_forecast()
    
    print("\n" + "="*70)
    print("PTA探测前景分析完成!")
    print("="*70)

if __name__ == "__main__":
    main()
