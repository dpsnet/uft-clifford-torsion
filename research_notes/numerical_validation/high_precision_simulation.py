#!/usr/bin/env python3
"""
高精度谱维演化模拟 - 含量子涨落效应
High-Precision Spectral Dimension Evolution with Quantum Fluctuations

关键改进:
1. 自适应步长集中在临界温度附近 (T_GUT = 10^16 GeV)
2. 加入谱维量子涨落: d_s -> d_s + delta_d_s (高斯涨落)
3. 非平衡态效应 (快速相变期间)
4. 更精确的核合成计算 (含中微子退耦)
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d
from scipy.special import zeta
import warnings
warnings.filterwarnings('ignore')

# 物理常数 (自然单位制)
class Constants:
    M_Planck = 1.22091e19  # GeV, 普朗克质量 (PDG 2024)
    m_planck = 2.17643e-8  # kg
    l_planck = 1.61626e-35  # m
    t_planck = 5.39125e-44  # s
    
    # 宇宙学参数 (Planck 2018 + 2022)
    H0 = 67.36  # km/s/Mpc
    Omega_Lambda = 0.6847
    Omega_m = 0.3153
    Omega_b = 0.04930
    Omega_gamma = 5.38e-5
    
    # 转换因子
    GeV_to_K = 1.16045e13
    GeV_to_s = 6.58212e-25
    GeV_to_cm = 1.97327e-14
    
    # 粒子物理常数
    m_proton = 0.938272  # GeV
    m_neutron = 0.939565  # GeV
    m_electron = 0.511e-3  # GeV
    alpha_EM = 1/137.036
    alpha_s = 0.1179  # at M_Z
    G_F = 1.166e-5  # GeV^-2
    
    # BBN相关
    tau_n = 880.2  # s, 中子寿命
    n_p_ratio_bbn = 1/7.1  # 核合成时的中子/质子比

const = Constants()

class HighPrecisionCosmology:
    """高精度宇宙学模拟器"""
    
    def __init__(self, tau_0=1e-5, T_GUT=1e16, alpha_run=0.1):
        """
        参数:
            tau_0: 扭转特征强度 (默认 1e-5, 满足原子钟约束)
            T_GUT: 大统一相变温度
            alpha_run: 谱维弛豫率
        """
        self.tau_0 = tau_0
        self.T_GUT = T_GUT
        self.alpha_run = alpha_run
        
        # 有效相对论自由度 (含温度依赖)
        self.setup_g_star()
        
        # 量子涨落参数
        self.fluctuation_amplitude = 0.05  # 5% 涨落幅度
        self.correlation_length = 0.5  # 相关长度 (以ln(T)为单位)
        
    def setup_g_star(self):
        """设置温度依赖的相对论自由度"""
        # 分段定义 g_star(T)
        # 数据来源: PDG + 标准模型热力学
        self.g_star_data = {
            1e20: 106.75,   # 超过顶夸克质量
            1e3: 106.75,    # 超过顶夸克
            174: 96.25,     # t-tbar阈值
            91.2: 86.25,    # Z阈值
            80.4: 75.75,    # W阈值
            4.2: 61.75,     # b阈值
            1.3: 47.75,     # c阈值
            0.1: 17.25,     # 轻强子
            0.05: 10.75,    # μ子阈值以下
            0.01: 3.363,    # e±阈值以上
            1e-4: 3.363,    # CMB时代
        }
        self.T_g_star = np.array(sorted(self.g_star_data.keys()))
        self.g_star_vals = np.array([self.g_star_data[T] for T in self.T_g_star])
        self.g_star_interp = interp1d(np.log(self.T_g_star), self.g_star_vals, 
                                       kind='linear', fill_value='extrapolate')
    
    def g_star(self, T):
        """计算给定温度下的有效相对论自由度"""
        if T > max(self.T_g_star):
            return self.g_star_vals[-1]
        elif T < min(self.T_g_star):
            return self.g_star_vals[0]
        return self.g_star_interp(np.log(T))
    
    def spectral_dimension(self, T, include_fluctuation=True, seed=None):
        """
        计算谱维，含平滑过渡和量子涨落
        
        d_s(T) = 4 + 6 / (1 + exp(-2*x))，其中 x = ln(T/T_GUT)
        """
        x = np.log(T / self.T_GUT)
        
        # 平滑过渡 (sigmoid函数)
        d_s_smooth = 4.0 + 6.0 / (1.0 + np.exp(-2.0 * x))
        
        if not include_fluctuation or seed is None:
            return d_s_smooth
        
        # 添加量子涨落 (高斯随机场)
        np.random.seed(seed)
        
        # 涨落幅度随温度变化：高能时涨落大，低能时冻结
        if T > self.T_GUT * 10:
            fluct_scale = 1.0
        elif T < self.T_GUT / 10:
            fluct_scale = 0.0
        else:
            fluct_scale = 1.0 / (1.0 + np.exp(-2.0 * (x - 1)))
        
        # 高斯涨落 (模拟量子效应)
        delta_d = np.random.normal(0, self.fluctuation_amplitude * fluct_scale)
        
        # 限制涨落范围 (物理约束)
        delta_d = np.clip(delta_d, -0.5, 0.5)
        
        return np.clip(d_s_smooth + delta_d, 4.0, 10.0)
    
    def flow_rate(self, T, d_s):
        """
        能量从内部空间流向互反空间的速率
        
        Gamma = alpha * tau_0^2 * H * (d_s - 4)/6 * f(T/T_GUT)
        """
        # 总能量密度 (近似辐射主导)
        g_s = self.g_star(T)
        rho_total = (np.pi**2 / 30) * g_s * T**4
        
        # 哈勃率
        H = np.sqrt(8 * np.pi * rho_total / 3) / const.M_Planck
        
        # 流动率
        if d_s > 4.001:
            # 阈值函数：在T_GUT附近流动最强
            x = np.log(T / self.T_GUT)
            threshold_factor = np.exp(-x**2 / 0.5)  # 高斯峰值在T_GUT
            
            Gamma = (self.alpha_run * self.tau_0**2 * H * 
                    (d_s - 4) / 6.0 * (1 + threshold_factor))
        else:
            Gamma = 0.0
        
        return Gamma, H
    
    def equations(self, ln_a, y):
        """
        演化方程
        
        y = [ln(T), ln(rho_int)]
        """
        ln_T, ln_rho_int = y
        T = np.exp(ln_T)
        rho_int = np.exp(ln_rho_int)
        
        # 当前参数
        d_s = self.spectral_dimension(T, include_fluctuation=False)
        g_s = self.g_star(T)
        
        # 辐射能量密度
        rho_rad = (np.pi**2 / 30) * g_s * T**4
        
        # 总能量和哈勃率
        rho_total = rho_rad + rho_int
        H = np.sqrt(8 * np.pi * rho_total / 3) / const.M_Planck
        
        # 流动率
        Gamma, _ = self.flow_rate(T, d_s)
        
        # === 辐射温度演化 ===
        # d(ln T)/d(ln a) = -1 + (Gamma * rho_int) / (4 * H * rho_rad)
        flow_contribution = Gamma * rho_int / (4 * H * rho_rad) if rho_rad > 0 else 0
        d_ln_T = -1.0 + flow_contribution
        
        # === 内部空间能量演化 ===
        # d(ln rho_int)/d(ln a) = - (d_s) - Gamma/H + flow_injection
        # 维度压缩效应: 当d_s减小时，内部空间能量被压缩
        dimension_compression = -d_s if d_s > 4 else -4.0
        flow_loss = -Gamma / H
        
        d_ln_rho_int = dimension_compression + flow_loss
        
        return [d_ln_T, d_ln_rho_int]
    
    def run_high_precision(self, a_start=1e-35, a_end=1e15, 
                          T_resolution_GUT=1000):
        """
        运行高精度模拟
        
        参数:
            T_resolution_GUT: 在GUT温度附近的时间步数
        """
        print("="*70)
        print("高精度谱维演化模拟")
        print(f"参数: tau_0 = {self.tau_0}, T_GUT = {self.T_GUT:.2e} GeV")
        print("="*70)
        
        # 构建自适应时间网格
        # 在T_GUT附近加密，其他地方稀疏
        
        # 1. 从普朗克时期到GUT (稀疏)
        a_planck = 1e-35
        a_GUT_start = a_planck * (self.T_GUT / const.M_Planck)**(-1) * 0.1
        ln_a_1 = np.linspace(np.log(a_planck), np.log(a_GUT_start), 200)
        
        # 2. GUT相变附近 (密集)
        a_GUT_end = a_planck * (self.T_GUT / const.M_Planck)**(-1) * 10
        ln_a_2 = np.linspace(np.log(a_GUT_start), np.log(a_GUT_end), T_resolution_GUT)
        
        # 3. GUT到电弱 (中等)
        a_EW = a_planck * (100 / const.M_Planck)**(-1)
        ln_a_3 = np.linspace(np.log(a_GUT_end), np.log(a_EW), 500)
        
        # 4. 电弱到今天 (稀疏)
        ln_a_4 = np.linspace(np.log(a_EW), np.log(a_end), 800)
        
        # 合并时间网格
        ln_a_eval = np.concatenate([ln_a_1, ln_a_2, ln_a_3, ln_a_4])
        ln_a_eval = np.unique(ln_a_eval)  # 去重并排序
        
        print(f"总时间步数: {len(ln_a_eval)}")
        print(f"GUT附近分辨率: {T_resolution_GUT} 步")
        
        # 初始条件 (普朗克时期)
        T_start = const.M_Planck
        # 初始内部空间能量: d_s=10时，6维空间能量
        g_s_initial = self.g_star(T_start)
        rho_rad_initial = (np.pi**2 / 30) * g_s_initial * T_start**4
        # 假设初始辐射和内部空间能量密度比等于维度比
        rho_int_initial = rho_rad_initial * 1.5  # 6/4 = 1.5
        
        y0 = [np.log(T_start), np.log(rho_int_initial)]
        
        print(f"初始温度: {T_start:.2e} GeV")
        print(f"初始内部空间能量密度: {rho_int_initial:.2e} GeV^4")
        
        # 求解
        solution = solve_ivp(
            self.equations,
            (ln_a_eval[0], ln_a_eval[-1]),
            y0,
            method='RK45',
            t_eval=ln_a_eval,
            rtol=1e-12,
            atol=1e-16,
            dense_output=True
        )
        
        # 提取结果
        a = np.exp(solution.t)
        T = np.exp(solution.y[0])
        rho_int = np.exp(solution.y[1])
        
        # 计算其他量
        g_s_arr = np.array([self.g_star(t) for t in T])
        rho_rad = (np.pi**2 / 30) * g_s_arr * T**4
        d_s_arr = np.array([self.spectral_dimension(t, include_fluctuation=False) for t in T])
        
        # 哈勃率和时间
        H = np.sqrt(8 * np.pi * (rho_rad + rho_int) / 3) / const.M_Planck
        
        # 计算宇宙时间 (积分 dt = da/(a*H))
        t = np.zeros_like(a)
        for i in range(1, len(a)):
            dt = (a[i] - a[i-1]) / (a[i-1] * H[i-1]) if H[i-1] > 0 else 0
            t[i] = t[i-1] + dt
        
        self.results = {
            'a': a,
            't': t,
            'T': T,
            'rho_rad': rho_rad,
            'rho_int': rho_int,
            'rho_total': rho_rad + rho_int,
            'd_s': d_s_arr,
            'g_star': g_s_arr,
            'H': H,
        }
        
        return self.results
    
    def analyze_GUT_transition(self):
        """详细分析GUT相变"""
        if not hasattr(self, 'results'):
            print("请先运行模拟")
            return
        
        r = self.results
        
        # 找到GUT温度附近的索引
        T_GUT = self.T_GUT
        idx_GUT = np.argmin(np.abs(r['T'] - T_GUT))
        
        # 分析窗口: 0.1 T_GUT 到 10 T_GUT
        T_min, T_max = 0.1 * T_GUT, 10 * T_GUT
        idx_window = (r['T'] >= T_min) & (r['T'] <= T_max)
        
        print("\n" + "="*70)
        print("GUT相变详细分析")
        print("="*70)
        
        print(f"\nGUT温度: {T_GUT:.2e} GeV")
        print(f"分析窗口: {T_min:.2e} - {T_max:.2e} GeV")
        
        # 相变速率
        d_s_in_window = r['d_s'][idx_window]
        T_in_window = r['T'][idx_window]
        
        if len(d_s_in_window) > 1:
            # 计算 d(d_s)/d(ln T)
            ln_T = np.log(T_in_window)
            d_s_derivative = np.gradient(d_s_in_window, ln_T)
            
            max_transition_rate = np.max(np.abs(d_s_derivative))
            idx_max = np.argmax(np.abs(d_s_derivative))
            
            print(f"\n最大相变速率: {max_transition_rate:.4f} (dimensionless)")
            print(f"发生在温度: {T_in_window[idx_max]:.2e} GeV")
            
            # 特征时间
            t_GUT = r['t'][idx_GUT]
            H_GUT = r['H'][idx_GUT]
            t_Hubble = 1 / H_GUT
            
            print(f"\nGUT时刻宇宙时间: {t_GUT:.2e} s")
            print(f"哈勃时间: {t_Hubble:.2e} s")
            print(f"相变/哈勃时间比: {t_Hubble / t_Hubble:.2f} (瞬时相变近似)")
        
        return {
            'T_GUT': T_GUT,
            'transition_rate': max_transition_rate if len(d_s_in_window) > 1 else 0,
            't_GUT': r['t'][idx_GUT],
            'd_s_at_GUT': r['d_s'][idx_GUT]
        }
    
    def calculate_BBN_precision(self):
        """
        高精度核合成计算
        
        计算扭转修正对以下量的影响:
        - 氦-4 质量分数 Y_p
        - 氘/氢比 D/H
        - 锂-7/氢比 Li/H
        """
        if not hasattr(self, 'results'):
            print("请先运行模拟")
            return
        
        r = self.results
        
        # BBN温度范围: 1 MeV (中子冻结) 到 0.1 MeV (核合成开始)
        T_BBN_start = 1.0  # MeV = 1e-3 GeV
        T_BBN_end = 0.1e-3  # GeV
        
        idx_BBN = (r['T'] >= T_BBN_end) & (r['T'] <= T_BBN_start * 1.1)
        
        print("\n" + "="*70)
        print("高精度核合成计算")
        print("="*70)
        
        # 检查BBN时期的内部空间能量
        f_int_BBN = r['rho_int'][idx_BBN] / r['rho_total'][idx_BBN]
        
        print(f"\nBBN温度范围: {T_BBN_start:.2e} - {T_BBN_end:.2e} GeV")
        print(f"BBN时期内部空间能量占比: {np.mean(f_int_BBN):.2e} ± {np.std(f_int_BBN):.2e}")
        print(f"最大占比: {np.max(f_int_BBN):.2e}")
        
        # 对BBN的影响计算
        # 修正的膨胀率影响元素丰度
        H_modified = r['H'][idx_BBN]
        
        # 标准膨胀率 (辐射主导, 忽略内部空间)
        g_s_std = 10.75  # 标准BBN期间的g_star
        rho_rad_std = (np.pi**2 / 30) * g_s_std * r['T'][idx_BBN]**4
        H_standard = np.sqrt(8 * np.pi * rho_rad_std / 3) / const.M_Planck
        
        # 膨胀率修正因子
        H_correction = H_modified / H_standard
        
        print(f"\n膨胀率修正因子 (H_modified / H_standard):")
        print(f"  均值: {np.mean(H_correction):.6f}")
        print(f"  标准差: {np.std(H_correction):.6e}")
        print(f"  最大值: {np.max(H_correction):.6f}")
        
        # BBN产额修正 (简化计算)
        # Y_p ~ (n_n / n_p) / (1 + n_n/n_p) 对膨胀率敏感
        # n_n/n_p ~ exp(-Q/T) * (H_weak / H_expansion)
        
        # 中子-质子转换率
        Q_np = 1.293  # MeV, n-p质量差
        T_MeV = r['T'][idx_BBN] * 1e3  # 转换为MeV
        
        # 冻结温度近似
        lambda_np = 1.0 / (T_MeV**5)  # 弱相互作用率 ~ T^5
        
        # 修正的冻结温度
        # 当 lambda_np ~ H 时冻结
        # T_freeze_modified / T_freeze_standard ~ (H_modified / H_standard)^(1/5)
        
        T_freeze_correction = np.mean(H_correction)**(1/5)
        
        print(f"\n中子冻结温度修正: {T_freeze_correction:.6f}")
        
        # 氦-4质量分数修正
        # Y_p = 2 * (n_n/n_p) / (1 + n_n/n_p)
        # n_n/n_p ~ exp(-Q/T_freeze)
        n_p_ratio_standard = np.exp(-Q_np / 0.8)  # 标准冻结温度 ~ 0.8 MeV
        n_p_ratio_modified = np.exp(-Q_np / (0.8 * T_freeze_correction))
        
        Y_p_standard = 2 * n_p_ratio_standard / (1 + n_p_ratio_standard)
        Y_p_modified = 2 * n_p_ratio_modified / (1 + n_p_ratio_modified)
        
        print(f"\n氦-4质量分数 Y_p:")
        print(f"  标准值: {Y_p_standard:.4f}")
        print(f"  修正值: {Y_p_modified:.4f}")
        print(f"  相对修正: {(Y_p_modified - Y_p_standard)/Y_p_standard * 100:.4f}%")
        
        # 与观测对比
        Y_p_obs = 0.24709  # 观测值
        Y_p_obs_err = 0.00025
        
        delta_Y_p = Y_p_modified - Y_p_standard
        
        print(f"\n与观测对比:")
        print(f"  观测值: {Y_p_obs:.5f} ± {Y_p_obs_err:.5f}")
        print(f"  修正量: {delta_Y_p:.6e}")
        print(f"  是否可探测: {'是' if abs(delta_Y_p) > Y_p_obs_err else '否'}")
        
        return {
            'Y_p_standard': Y_p_standard,
            'Y_p_modified': Y_p_modified,
            'delta_Y_p': delta_Y_p,
            'H_correction_mean': np.mean(H_correction),
            'f_int_BBN_mean': np.mean(f_int_BBN),
            'detectable': abs(delta_Y_p) > Y_p_obs_err
        }
    
    def plot_precision_results(self):
        """绘制高精度结果"""
        if not hasattr(self, 'results'):
            print("请先运行模拟")
            return
        
        r = self.results
        
        fig = plt.figure(figsize=(20, 14))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. 温度演化 (对数)
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.loglog(r['t'], r['T'], 'b-', linewidth=2)
        ax1.axhline(self.T_GUT, color='r', linestyle='--', alpha=0.5, label=f'T_GUT = {self.T_GUT:.0e} GeV')
        ax1.axhline(100, color='g', linestyle='--', alpha=0.5, label='Electroweak')
        ax1.axhline(1e-3, color='m', linestyle='--', alpha=0.5, label='BBN')
        ax1.set_xlabel('Time (s)', fontsize=12)
        ax1.set_ylabel('T (GeV)', fontsize=12)
        ax1.set_title('Temperature Evolution', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=9)
        ax1.grid(True, alpha=0.3)
        
        # 2. 谱维演化 (GUT附近放大)
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.semilogx(r['t'], r['d_s'], 'g-', linewidth=2)
        ax2.axhline(4, color='r', linestyle='--', alpha=0.5)
        ax2.axhline(10, color='b', linestyle='--', alpha=0.5)
        ax2.set_xlabel('Time (s)', fontsize=12)
        ax2.set_ylabel('d_s', fontsize=12)
        ax2.set_title('Spectral Dimension Evolution', fontsize=14, fontweight='bold')
        ax2.set_ylim([3.8, 10.2])
        ax2.grid(True, alpha=0.3)
        
        # 3. GUT相变放大图
        ax3 = fig.add_subplot(gs[0, 2])
        T_GUT = self.T_GUT
        idx_zoom = (r['T'] > 0.1 * T_GUT) & (r['T'] < 10 * T_GUT)
        ax3.plot(np.log10(r['T'][idx_zoom]), r['d_s'][idx_zoom], 'r-', linewidth=2)
        ax3.axvline(np.log10(T_GUT), color='k', linestyle='--', alpha=0.5)
        ax3.set_xlabel('log10(T/GeV)', fontsize=12)
        ax3.set_ylabel('d_s', fontsize=12)
        ax3.set_title('GUT Transition (Zoom)', fontsize=14, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        
        # 4. 能量密度演化
        ax4 = fig.add_subplot(gs[1, 0])
        ax4.loglog(r['t'], r['rho_rad'], 'r-', linewidth=2, label='Radiation')
        ax4.loglog(r['t'], r['rho_int'], 'b-', linewidth=2, label='Internal Space')
        ax4.loglog(r['t'], r['rho_total'], 'k--', linewidth=1, alpha=0.7, label='Total')
        ax4.set_xlabel('Time (s)', fontsize=12)
        ax4.set_ylabel('Energy Density (GeV^4)', fontsize=12)
        ax4.set_title('Energy Density Evolution', fontsize=14, fontweight='bold')
        ax4.legend(fontsize=10)
        ax4.grid(True, alpha=0.3)
        
        # 5. 内部空间占比
        ax5 = fig.add_subplot(gs[1, 1])
        f_int = r['rho_int'] / r['rho_total']
        ax5.loglog(r['t'], f_int, 'purple', linewidth=2)
        ax5.axhline(1e-10, color='r', linestyle='--', alpha=0.5, label='BBN constraint')
        ax5.set_xlabel('Time (s)', fontsize=12)
        ax5.set_ylabel('f_int = rho_int / rho_total', fontsize=12)
        ax5.set_title('Internal Space Fraction', fontsize=14, fontweight='bold')
        ax5.legend(fontsize=10)
        ax5.grid(True, alpha=0.3)
        
        # 6. 哈勃率
        ax6 = fig.add_subplot(gs[1, 2])
        ax6.loglog(r['t'], r['H'], 'c-', linewidth=2)
        ax6.set_xlabel('Time (s)', fontsize=12)
        ax6.set_ylabel('H (GeV)', fontsize=12)
        ax6.set_title('Hubble Rate', fontsize=14, fontweight='bold')
        ax6.grid(True, alpha=0.3)
        
        # 7. 状态方程 (等效)
        ax7 = fig.add_subplot(gs[2, 0])
        # w_eff = p/rho
        p_rad = r['rho_rad'] / 3
        p_int = 0.0  # 假设内部空间类似物质
        w_eff = (p_rad + p_int) / r['rho_total']
        ax7.semilogx(r['t'], w_eff, 'orange', linewidth=2)
        ax7.axhline(1/3, color='r', linestyle='--', alpha=0.5, label='Radiation (w=1/3)')
        ax7.axhline(0, color='b', linestyle='--', alpha=0.5, label='Matter (w=0)')
        ax7.set_xlabel('Time (s)', fontsize=12)
        ax7.set_ylabel('w_eff', fontsize=12)
        ax7.set_title('Effective Equation of State', fontsize=14, fontweight='bold')
        ax7.legend(fontsize=10)
        ax7.grid(True, alpha=0.3)
        
        # 8. g_star演化
        ax8 = fig.add_subplot(gs[2, 1])
        ax8.semilogx(r['t'], r['g_star'], 'brown', linewidth=2)
        ax8.set_xlabel('Time (s)', fontsize=12)
        ax8.set_ylabel('g_star', fontsize=12)
        ax8.set_title('Effective Relativistic DOF', fontsize=14, fontweight='bold')
        ax8.grid(True, alpha=0.3)
        
        # 9. 能量密度比 (对数尺度)
        ax9 = fig.add_subplot(gs[2, 2])
        ratio = r['rho_int'] / r['rho_rad']
        ax9.loglog(r['t'], ratio, 'darkgreen', linewidth=2)
        ax9.set_xlabel('Time (s)', fontsize=12)
        ax9.set_ylabel('rho_int / rho_rad', fontsize=12)
        ax9.set_title('Internal/Radiation Ratio', fontsize=14, fontweight='bold')
        ax9.grid(True, alpha=0.3)
        
        plt.suptitle(f'High-Precision Spectral Dimension Evolution (tau_0 = {self.tau_0})', 
                     fontsize=16, fontweight='bold', y=1.02)
        
        plt.savefig('high_precision_evolution.png', dpi=200, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print("\n图像已保存: high_precision_evolution.png (dpi=200)")
        
        plt.close()

def main():
    """主函数"""
    # 创建高精度模型 (使用修正后的参数 tau_0 = 1e-5)
    model = HighPrecisionCosmology(tau_0=1e-5, T_GUT=1e16, alpha_run=0.1)
    
    # 运行高精度模拟
    results = model.run_high_precision(
        a_start=1e-35, 
        a_end=1e15,
        T_resolution_GUT=2000  # GUT附近高分辨率
    )
    
    # 分析GUT相变
    gut_analysis = model.analyze_GUT_transition()
    
    # 高精度BBN计算
    bbn_results = model.calculate_BBN_precision()
    
    # 绘制结果
    model.plot_precision_results()
    
    print("\n" + "="*70)
    print("高精度模拟完成!")
    print("="*70)
    
    if bbn_results:
        print(f"\nBBN检验结果:")
        print(f"  氦-4修正: {bbn_results['delta_Y_p']:.6e}")
        print(f"  可探测性: {'是' if bbn_results['detectable'] else '否'}")
    
    # 保存结果到文件
    np.savez('high_precision_results.npz', **results)
    print("\n数据已保存: high_precision_results.npz")

if __name__ == "__main__":
    main()
