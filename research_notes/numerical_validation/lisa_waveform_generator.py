#!/usr/bin/env python3
"""
LISA双黑洞并合6偏振波形模板生成器
LISA Binary Black Hole Merger 6-Polarization Waveform Generator

生成统一场理论预言的双黑洞并合引力波波形，包含6种偏振模式:
1. Plus (+) - 标准GR
2. Cross (x) - 标准GR  
3. Vector-x (x) - UFT额外
4. Vector-y (y) - UFT额外
5. Breathing (b) - UFT额外
6. Longitudinal (l) - UFT额外

特点:
- 基于IMRPhenomD近似 (Inspiral-Merger-Ringdown)
- 包含UFT修正的传播速度色散
- 振幅修正因子 (τ₀依赖)
- 完整的LISA探测器响应

作者: 理论验证组
日期: 2026-03-12
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.integrate import odeint
import warnings
warnings.filterwarnings('ignore')

# 物理常数
class Constants:
    # 基本常数
    c = 299792458  # m/s
    G = 6.67430e-11  # m^3/(kg·s^2)
    
    # 天文单位
    M_sun = 1.98847e30  # kg
    M_sun_GeV = 1.115e57  # GeV/c^2
    
    # 距离
    pc = 3.08567758e16  # m
    Mpc = pc * 1e6
    Gpc = pc * 1e9
    
    # 时间
    year = 365.25 * 24 * 3600
    
    # 宇宙学
    H0 = 67.4  # km/s/Mpc
    
    # LISA参数
    LISA_arm = 2.5e9  # m
    LISA_f_star = 19.09e-3  # Hz (臂长特征频率)

const = Constants()

class UFT_GW_Polarizations:
    """
    统一场理论的6种引力波偏振模式
    
    偏振张量 (在TT规范下，传播方向为z):
    """
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        
        # 偏振张量定义 (对称无迹)
        self.polarization_tensors = {
            'plus': np.array([[1, 0, 0],
                             [0, -1, 0],
                             [0, 0, 0]]),
            'cross': np.array([[0, 1, 0],
                              [1, 0, 0],
                              [0, 0, 0]]),
            'vector_x': np.array([[0, 0, 1],
                                 [0, 0, 0],
                                 [1, 0, 0]]),
            'vector_y': np.array([[0, 0, 0],
                                 [0, 0, 1],
                                 [0, 1, 0]]),
            'breathing': np.array([[1, 0, 0],
                                  [0, 1, 0],
                                  [0, 0, 0]]) / np.sqrt(2),  # 归一化
            'longitudinal': np.array([[0, 0, 0],
                                     [0, 0, 0],
                                     [0, 0, 1]])
        }
        
        # 振幅比 (相对plus模式)
        self.amplitude_ratios = {
            'plus': 1.0,
            'cross': 1.0,
            'vector_x': 0.5 * tau_0,
            'vector_y': 0.5 * tau_0,
            'breathing': 0.3 * tau_0**2,
            'longitudinal': 0.2 * tau_0**2
        }
        
        # 传播速度修正 (c_GW = c * (1 - alpha * tau_0^2))
        self.speed_corrections = {
            'plus': 0.0,
            'cross': 0.0,
            'vector_x': 0.1 * tau_0**2,
            'vector_y': 0.1 * tau_0**2,
            'breathing': 0.2 * tau_0**2,
            'longitudinal': 0.3 * tau_0**2
        }
    
    def propagation_speed(self, mode):
        """返回给定偏振模式的传播速度 (以c为单位)"""
        correction = self.speed_corrections.get(mode, 0.0)
        return 1.0 - correction
    
    def amplitude_factor(self, mode):
        """返回振幅修正因子"""
        return self.amplitude_ratios.get(mode, 0.0)

class IMRPhenomD_UFT:
    """
    IMRPhenomD近似 + 统一场理论修正
    
    生成非旋近双黑洞并合的引力波波形
    """
    
    def __init__(self, m1, m2, tau_0=1e-5, dist_mpc=1000):
        """
        参数:
            m1, m2: 黑洞质量 (太阳质量)
            tau_0: 扭转强度
            dist_mpc: 距离 (Mpc)
        """
        self.m1 = m1 * const.M_sun
        self.m2 = m2 * const.M_sun
        self.tau_0 = tau_0
        self.dist = dist_mpc * const.Mpc
        
        # 派生参数
        self.M_total = self.m1 + self.m2
        self.mu = self.m1 * self.m2 / self.M_total  # 约化质量
        self.eta = self.mu / self.M_total  # 对称质量比
        self.M_chirp = self.mu**(3/5) * self.M_total**(2/5)  # 啁啾质量
        
        # 几何单位制转换
        self.M_total_geom = self.M_total * const.G / const.c**2  # 米
        self.M_chirp_geom = self.M_chirp * const.G / const.c**2
        
        # 偏振信息
        self.pols = UFT_GW_Polarizations(tau_0)
        
        # 计算特征频率 (Hz)
        # f_merger ~ c^3 / (6^(3/2) * pi * G * M) 在几何单位制中
        # 转换为SI: f = c / (2 * pi * r_isco) where r_isco = 6GM/c^2
        self.f_merger = const.c**3 / (6**1.5 * np.pi * const.G * self.M_total)  # Hz
        self.f_ring = self.f_merger * 0.5  # 铃宕频率
        self.f_cut = self.f_merger * 2.0  # 截止频率
    
    def amplitude_inspiral(self, f):
        """
        旋近阶段振幅
        
        A(f) ~ f^(-7/6) (啁啾信号)
        """
        # 啁啾振幅
        A_chirp = (self.M_chirp_geom**(5/6) * f**(-7/6) / self.dist * 
                  (const.G / const.c**2) * np.sqrt(5/24/np.pi**(4/3)))
        
        return A_chirp
    
    def amplitude_merger(self, f):
        """并合阶段振幅 (简化模型)"""
        # 高斯峰在并合频率附近
        sigma = self.f_ring * 0.2
        A_peak = self.M_total_geom / self.dist * 0.5
        
        return A_peak * np.exp(-0.5 * ((f - self.f_merger) / sigma)**2)
    
    def amplitude_ringdown(self, f):
        """铃宕阶段振幅"""
        # 阻尼振荡
        f_qnm = self.f_ring
        tau = 10 * self.M_total_geom / const.c  # 阻尼时间
        
        # Lorentzian线型
        gamma = 1 / (2 * np.pi * tau)
        A_rd = (self.M_total_geom / self.dist * 0.3 * 
                gamma / ((f - f_qnm)**2 + gamma**2))
        
        return A_rd
    
    def phase_inspiral(self, f):
        """
        旋近阶段相位
        
        使用TaylorF2后牛顿展开到2PN
        """
        v = (np.pi * self.M_total_geom * f)**(1/3)
        
        # 2PN相位
        psi = (2 * np.pi * f * self.M_total_geom * 
               (1 + (3715/756 + 55*self.eta/9) * v**2 + 
                (15293365/508032 + 27145*self.eta/504 + 3085*self.eta**2/72) * v**4))
        
        return psi
    
    def waveform_mode(self, f, mode='plus'):
        """
        生成特定偏振模式的频率域波形
        
        h(f) = A(f) * exp(i * psi(f) + i * phi_0)
        """
        # 振幅
        if np.isscalar(f):
            if f < self.f_merger:
                A = self.amplitude_inspiral(f)
            elif f < self.f_ring:
                A = self.amplitude_merger(f)
            elif f < self.f_cut:
                A = self.amplitude_ringdown(f)
            else:
                A = 0.0
        else:
            # 数组输入
            A = np.zeros_like(f)
            mask_inspiral = f < self.f_merger
            mask_merger = (f >= self.f_merger) & (f < self.f_ring)
            mask_ringdown = (f >= self.f_ring) & (f < self.f_cut)
            
            A[mask_inspiral] = self.amplitude_inspiral(f[mask_inspiral])
            A[mask_merger] = self.amplitude_merger(f[mask_merger])
            A[mask_ringdown] = self.amplitude_ringdown(f[mask_ringdown])
        
        # 相位
        if np.isscalar(f):
            psi = self.phase_inspiral(f)
        else:
            psi = np.zeros_like(f)
            mask = f > 0
            psi[mask] = self.phase_inspiral(f[mask])
        
        # UFT修正
        # 1. 振幅修正
        amp_factor = self.pols.amplitude_factor(mode)
        A = A * amp_factor
        
        # 2. 传播速度修正 (色散)
        # 慢偏振模式累积相位差
        v_gw = self.pols.propagation_speed(mode)
        if v_gw < 1.0 and not np.isscalar(f):
            # 频率依赖的相位修正
            phase_corr = 2 * np.pi * f * self.dist / const.c * (1/v_gw - 1)
            psi = psi + phase_corr
        elif v_gw < 1.0 and np.isscalar(f) and f > 0:
            phase_corr = 2 * np.pi * f * self.dist / const.c * (1/v_gw - 1)
            psi = psi + phase_corr
        
        return A * np.exp(1j * psi)
    
    def all_polarizations(self, f):
        """生成所有6种偏振模式的波形"""
        waveforms = {}
        for mode in self.pols.polarization_tensors.keys():
            waveforms[mode] = self.waveform_mode(f, mode)
        return waveforms

class LISA_Response:
    """
    LISA探测器响应函数
    
    包含天线方向图和臂长响应
    """
    
    def __init__(self):
        self.L = const.LISA_arm
        self.f_star = const.LISA_f_star
        
    def transfer_function(self, f):
        """
        LISA臂长传递函数
        
        T(f) = sinc(f / (2 * f_star)) * exp(-i * f / (2 * f_star))
        """
        x = f / (2 * self.f_star)
        # 避免除零
        if np.isscalar(x):
            if x == 0:
                return 1.0
            T = np.sin(np.pi * x) / (np.pi * x) * np.exp(-1j * np.pi * x)
        else:
            T = np.ones_like(x, dtype=complex)
            nonzero = x != 0
            T[nonzero] = (np.sin(np.pi * x[nonzero]) / (np.pi * x[nonzero]) * 
                         np.exp(-1j * np.pi * x[nonzero]))
        return T
    
    def antenna_pattern(self, theta, phi, psi, mode='plus'):
        """
        天线方向图 (简化模型)
        
        参数:
            theta, phi: 源方向 (极角, 方位角)
            psi: 极化角
            mode: 偏振模式
        """
        # 简化: 假设方向平均响应
        if mode in ['plus', 'cross']:
            F = 0.5  # 典型值
        else:
            F = 0.1  # 额外偏振响应较弱
        
        return F
    
    def signal_to_noise(self, waveforms, f, T_obs=4*const.year):
        """
        计算信噪比
        
        SNR^2 = 4 * integral[ |h(f)|^2 / S_n(f) df ]
        """
        # LISA噪声功率谱 (简化)
        # 位置噪声
        S_pos = (1.5e-11)**2 * (1 + (0.4e-3/f)**2)
        # 加速度噪声  
        S_acc = (3e-15)**2 * (1 + (0.4e-3/f)**2) * (1 + (f/8e-3)**4)
        
        S_n = S_pos / self.L**2 + S_acc / (2*np.pi*f)**4 / self.L**2
        
        # 总信号 (所有偏振)
        h_total = sum(np.abs(waveforms[m])**2 for m in waveforms.keys())
        
        # SNR积分
        integrand = h_total / S_n
        snr_sq = 4 * np.trapezoid(integrand, f)
        
        return np.sqrt(snr_sq)

class WaveformGenerator:
    """
    波形生成主类
    
    生成完整的时域和频域波形
    """
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        self.lisa = LISA_Response()
    
    def generate_binary_waveform(self, m1, m2, dist_mpc=1000, 
                                 theta=0, phi=0, psi=0,
                                 f_low=1e-4, f_high=1, n_points=10000):
        """
        生成双黑洞并合完整波形
        
        参数:
            m1, m2: 质量 (太阳质量)
            dist_mpc: 距离 (Mpc)
            theta, phi: 天空位置
            psi: 极化角
            f_low, f_high: 频率范围 (Hz)
        """
        # 创建IMR模型
        imr = IMRPhenomD_UFT(m1, m2, self.tau_0, dist_mpc)
        
        # 频率网格
        f = np.logspace(np.log10(f_low), np.log10(f_high), n_points)
        
        # 生成所有偏振模式
        waveforms = {}
        for mode in ['plus', 'cross', 'vector_x', 'vector_y', 'breathing', 'longitudinal']:
            waveforms[mode] = imr.waveform_mode(f, mode)
        
        # 计算SNR
        snr = self.lisa.signal_to_noise(waveforms, f)
        
        return f, waveforms, snr, imr
    
    def generate_template_bank(self, mass_range=(10, 100), n_masses=10):
        """
        生成波形模板库
        
        参数:
            mass_range: (最小总质量, 最大总质量) 太阳质量
            n_masses: 质量点数
        """
        print("="*70)
        print("LISA波形模板库生成")
        print(f"参数: tau_0 = {self.tau_0}")
        print("="*70)
        
        M_totals = np.logspace(np.log10(mass_range[0]), 
                               np.log10(mass_range[1]), n_masses)
        
        templates = []
        
        print(f"\n生成 {n_masses} 个质量组合的模板...")
        print(f"{'M_total':<12} {'eta':<8} {'f_merger':<12} {'SNR':<10} {'Status'}")
        print("-"*70)
        
        for M in M_totals:
            # 等质量情况
            m1 = m2 = M / 2
            eta = 0.25
            
            f, waveforms, snr, imr = self.generate_binary_waveform(
                m1, m2, dist_mpc=1000
            )
            
            status = "✓" if snr > 10 else "○" if snr > 5 else "×"
            
            print(f"{M:<12.1f} {eta:<8.2f} {imr.f_merger:<12.2e} {snr:<10.2f} {status}")
            
            templates.append({
                'M_total': M,
                'eta': eta,
                'f': f,
                'waveforms': waveforms,
                'snr': snr,
                'imr': imr
            })
        
        return templates
    
    def plot_waveform(self, f, waveforms, title="Gravitational Waveform"):
        """绘制波形"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        axes = axes.flatten()
        
        modes = ['plus', 'cross', 'vector_x', 'vector_y', 'breathing', 'longitudinal']
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown']
        
        for i, (mode, color) in enumerate(zip(modes, colors)):
            ax = axes[i]
            
            h = waveforms[mode]
            amp = np.abs(h)
            phase = np.angle(h)
            
            # 振幅
            ax.loglog(f, amp, color=color, linewidth=2)
            ax.set_xlabel('Frequency (Hz)', fontsize=11)
            ax.set_ylabel('|h(f)|', fontsize=11)
            ax.set_title(f'{mode.capitalize()} Polarization', fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # 标记特征频率
            ax.axvline(x=self.f_merger if hasattr(self, 'f_merger') else 1e-3, 
                      color='gray', linestyle='--', alpha=0.5)
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        return fig

def main():
    """主函数"""
    # 创建波形生成器
    generator = WaveformGenerator(tau_0=1e-5)
    
    # 生成示例波形 (10000+10000 太阳质量中等质量黑洞 - 适合LISA频段)
    print("="*70)
    print("LISA 6偏振波形模板示例")
    print("="*70)
    
    m1, m2 = 10000, 10000  # 太阳质量 (中等质量黑洞，适合LISA频段)
    dist = 1000  # Mpc
    
    f, waveforms, snr, imr = generator.generate_binary_waveform(
        m1, m2, dist_mpc=dist,
        f_low=1e-4, f_high=1, n_points=5000
    )
    
    print(f"\n源参数:")
    print(f"  质量: m1 = {m1} M_sun, m2 = {m2} M_sun")
    print(f"  总质量: {imr.M_total/const.M_sun:.1f} M_sun")
    print(f"  啁啾质量: {imr.M_chirp/const.M_sun:.1f} M_sun")
    print(f"  距离: {dist} Mpc")
    print(f"  并合频率: {imr.f_merger:.2e} Hz")
    
    print(f"\n信噪比: SNR = {snr:.2f}")
    
    print(f"\n各偏振模式振幅比 (相对于plus):")
    for mode in ['cross', 'vector_x', 'vector_y', 'breathing', 'longitudinal']:
        ratio = imr.pols.amplitude_factor(mode)
        print(f"  {mode:15s}: {ratio:.2e}")
    
    print(f"\n各偏振模式传播速度 (以c为单位):")
    for mode in ['plus', 'cross', 'vector_x', 'vector_y', 'breathing', 'longitudinal']:
        speed = imr.pols.propagation_speed(mode)
        print(f"  {mode:15s}: {speed:.10f}")
    
    # 绘制波形
    fig = generator.plot_waveform(f, waveforms, 
                                  title=f"BBH Waveform: {m1}+{m2} M_sun, d={dist} Mpc, SNR={snr:.1f}")
    plt.savefig('lisa_waveform_6pol.png', dpi=200, bbox_inches='tight',
               facecolor='white', edgecolor='none')
    print("\n波形图像已保存: lisa_waveform_6pol.png")
    
    # 生成模板库 (LISA敏感的质量范围: 10^4 - 10^7 太阳质量)
    print("\n" + "="*70)
    templates = generator.generate_template_bank(mass_range=(1e4, 1e7), n_masses=10)
    
    # 统计SNR分布
    snrs = [t['snr'] for t in templates]
    print(f"\n模板库统计:")
    print(f"  SNR范围: {min(snrs):.2f} - {max(snrs):.2f}")
    print(f"  SNR > 10 的模板: {sum(1 for s in snrs if s > 10)} / {len(snrs)}")
    print(f"  平均SNR: {np.mean(snrs):.2f}")
    
    print("\n" + "="*70)
    print("LISA波形模板生成完成!")
    print("="*70)

if __name__ == "__main__":
    main()
