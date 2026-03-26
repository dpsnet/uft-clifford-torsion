#!/usr/bin/env python3
"""
早期宇宙GUT相变动力学精细模拟 - 统一场理论框架
Fine Simulation of GUT Phase Transition Dynamics in Early Universe

核心理论特征:
1. 谱维驱动相变: d_s从10→4演化
2. 扭转场耦合: τ场与Higgs场的非线性相互作用
3. 分形时空效应: 有效维度跑动改变临界行为
4. 原初磁场产生: 扭转场-电磁场耦合

作者: 统一场理论研究团队
版本: 1.0.0
日期: 2026-03-18
"""

import numpy as np
from scipy.integrate import solve_ivp, odeint
from scipy.special import zeta, gamma as gamma_func
from scipy.optimize import fsolve, minimize_scalar
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import warnings
warnings.filterwarnings('ignore')

# 物理常数 (自然单位制 ℏ = c = k_B = 1)
class PhysicalConstants:
    """物理常数类"""
    # 基本常数
    M_Planck = 1.22091e19  # GeV, 普朗克质量
    m_planck = 2.17643e-8  # kg
    l_planck = 1.61626e-35  # m
    t_planck = 5.39125e-44  # s
    
    # 转换因子
    GeV_to_K = 1.16045e13
    GeV_to_s = 6.58212e-25
    GeV_to_cm = 1.97327e-14
    GeV_to_m = 1.97327e-16
    
    # GUT尺度参数
    T_GUT = 1e16  # GeV, GUT温度
    M_GUT = 1e16  # GeV, GUT质量尺度
    alpha_GUT = 1/25  # GUT耦合常数
    
    # 宇宙学参数
    H0 = 67.36  # km/s/Mpc
    Omega_Lambda = 0.6847
    Omega_m = 0.3153
    Omega_b = 0.04930
    
    # 重子不对称度观测值
    eta_B_obs = 6.1e-10  # 观测值 η_B = n_B/n_γ
    
    # 费米常数
    G_F = 1.1663787e-5  # GeV^-2
    
    # 电弱标度
    T_EW = 100  # GeV
    v_EW = 246  # GeV, Higgs VEV

const = PhysicalConstants()


class GUTPhaseTransition:
    """
    GUT相变动力学模拟器
    
    在统一场理论框架下，GUT相变由谱维演化驱动:
    - 高能区 (T > T_GUT): d_s ≈ 10, 内部空间活跃
    - 过渡区 (T ~ T_GUT): d_s快速演化
    - 低能区 (T < T_GUT): d_s ≈ 4, 有效4维时空
    """
    
    def __init__(self, tau_0=1e-5, alpha_run=0.1, lambda_torsion=0.01):
        """
        初始化参数
        
        参数:
            tau_0: 基准扭转参数 (满足原子钟约束 ~10^-6)
            alpha_run: 谱维跑动率
            lambda_torsion: 扭转自耦合常数
        """
        self.tau_0 = tau_0
        self.alpha_run = alpha_run
        self.lambda_torsion = lambda_torsion
        
        # GUT Higgs场参数 (简单SO(10)模型)
        self.m_phi = 1e16  # GUT Higgs质量
        self.lambda_phi = 0.1  # Higgs自耦合
        
        # 扭转-Higgs耦合
        self.g_tau_phi = 0.01  # 耦合强度
        
        # 临界温度 (初始估计)
        self.T_c = self.calculate_critical_temperature()
        
        # 相变状态跟踪
        self.transition_complete = False
        self.transition_start_time = None
        self.transition_end_time = None
        
    def spectral_dimension(self, T):
        """
        计算谱维作为温度的函数
        
        使用平滑过渡函数:
        d_s(T) = 4 + 6 / (1 + exp(-2*x)), x = ln(T/T_GUT)
        
        参数:
            T: 温度 (GeV)
        返回:
            d_s: 谱维度
        """
        x = np.log(T / const.T_GUT)
        # 平滑sigmoid过渡
        d_s = 4.0 + 6.0 / (1.0 + np.exp(-2.0 * x))
        return d_s
    
    def spectral_dimension_derivative(self, T):
        """计算 d(d_s)/dT """
        x = np.log(T / const.T_GUT)
        exp_term = np.exp(-2.0 * x)
        d_ds_dx = 12.0 * exp_term / (1.0 + exp_term)**2
        return d_ds_dx / T
    
    def effective_free_energy(self, phi, T, tau):
        """
        有效自由能密度 (Ginzburg-Landau形式)
        
        F(φ, T, τ) = (1/2)m²(T)φ² + (1/4)λφ⁴ + (1/2)τ²φ² + 耦合项
        
        参数:
            phi: Higgs场值
            T: 温度
            tau: 扭转场值
        返回:
            自由能密度
        """
        # 温度依赖的质量项
        m_T_sq = self.lambda_phi * (T**2 - self.T_c**2)
        
        # Higgs势能
        V_higgs = 0.5 * m_T_sq * phi**2 + 0.25 * self.lambda_phi * phi**4
        
        # 扭转场势能
        V_torsion = 0.5 * tau**2 * phi**2 + self.lambda_torsion * tau**4
        
        # 扭转-Higgs耦合 (几何诱导)
        d_s = self.spectral_dimension(T)
        coupling = self.g_tau_phi * (d_s - 4) * tau * phi**2 / 6.0
        
        return V_higgs + V_torsion + coupling
    
    def calculate_critical_temperature(self):
        """
        计算临界温度
        
        在统一场理论中，临界温度受扭转场修正:
        T_c² = (m_φ² + τ²) / λ_φ
        """
        m_eff_sq = self.m_phi**2 + (self.tau_0 * const.T_GUT)**2
        T_c = np.sqrt(m_eff_sq / self.lambda_phi)
        return T_c
    
    def calculate_critical_exponents(self):
        """
        计算临界指数
        
        在平均场近似下:
        - β: 序参量临界指数 φ ~ (Tc - T)^β
        - α: 比热临界指数 C ~ |T - Tc|^{-α}
        - γ: 磁化率指数 χ ~ |T - Tc|^{-γ}
        - ν: 关联长度指数 ξ ~ |T - Tc|^{-ν}
        
        扭转修正会影响这些指数
        """
        # 平均场值
        beta_MF = 0.5
        alpha_MF = 0.0
        gamma_MF = 1.0
        nu_MF = 0.5
        
        # 扭转修正 (通过改变有效维度)
        # 在d_s = 10时，涨落更弱，平均场行为更稳定
        d_s_at_Tc = self.spectral_dimension(self.T_c)
        
        # 修正因子 (简化估计)
        epsilon = (d_s_at_Tc - 4) / 6.0  # 0到1之间
        correction = 1.0 - 0.1 * epsilon  # 弱修正
        
        return {
            'beta': beta_MF * correction,
            'alpha': alpha_MF,
            'gamma': gamma_MF / correction,
            'nu': nu_MF / correction,
            'epsilon': epsilon
        }
    
    def determine_transition_order(self):
        """
        判定相变阶数
        
        基于势能有效质量项的符号变化:
        - 一级相变: 势能有势垒
        - 二级相变: 势能连续变化
        """
        # 检查势能曲率
        T_range = np.linspace(0.5 * self.T_c, 1.5 * self.T_c, 100)
        
        barrier_heights = []
        for T in T_range:
            phi_range = np.linspace(0, 2 * self.m_phi, 200)
            V_vals = [self.effective_free_energy(phi, T, self.tau_0) for phi in phi_range]
            
            # 检查是否有势垒
            if len(V_vals) > 2:
                # 寻找局部极大值
                local_max = np.maximum.accumulate(V_vals)
                has_barrier = np.any(local_max[1:-1] > V_vals[0])
                barrier_heights.append(has_barrier)
        
        # 如果存在温度窗口有势垒，则是一级相变
        if np.any(barrier_heights):
            return "First Order", barrier_heights
        else:
            return "Second Order", barrier_heights
    
    def domain_wall_structure(self, T):
        """
        计算畴壁结构和张力
        
        在相变过程中，畴壁分隔不同真空态区域
        """
        # 畴壁宽度
        delta = 1.0 / self.m_phi
        
        # 畴壁张力 (能量/面积)
        sigma_wall = self.m_phi**3 / (3 * self.lambda_phi)
        
        # 扭转修正
        tau_correction = 1.0 + self.tau_0 * np.log(const.T_GUT / T)
        
        return {
            'width': delta,
            'tension': sigma_wall * tau_correction,
            'profile': lambda x: self.m_phi * np.tanh(x / delta)
        }
    
    def bubble_nucleation_rate(self, T):
        """
        计算气泡成核率
        
        Γ ~ exp(-S_E), S_E是欧几里得作用量
        """
        # 简化计算 (Coleman-DeLuccia形式)
        delta_T = (self.T_c - T) / self.T_c
        
        if delta_T <= 0:
            return 0.0
        
        # 欧几里得作用量 (近似)
        S_E = 27.0 * np.pi**2 * self.lambda_phi / (2.0 * delta_T**3)
        
        # 预因子 (粗略估计)
        A = self.T_c**4
        
        Gamma = A * np.exp(-S_E)
        return Gamma
    
    def simulate_phase_transition(self, T_initial=1.2e16, T_final=0.8e16, n_steps=10000):
        """
        数值模拟相变过程
        
        求解耦合的场方程:
        - Higgs场演化: 热力学+扭转修正
        - 温度演化: 宇宙膨胀+相变潜热
        """
        # 温度对数网格 (在T_c附近加密)
        T_center = self.T_c
        T_log = np.concatenate([
            np.logspace(np.log10(T_initial), np.log10(1.1*T_center), n_steps//4),
            np.logspace(np.log10(1.1*T_center), np.log10(0.9*T_center), n_steps//2),
            np.logspace(np.log10(0.9*T_center), np.log10(T_final), n_steps//4)
        ])
        T_log = np.sort(T_log)[::-1]  # 从高到低
        
        results = {
            'T': T_log,
            'd_s': [],
            'phi_vev': [],
            'transition_rate': [],
            'bubble_fraction': [],
            'domain_wall_density': []
        }
        
        bubble_fraction = 0.0
        
        for T in T_log:
            # 谱维
            d_s = self.spectral_dimension(T)
            results['d_s'].append(d_s)
            
            # Higgs VEV (最小化自由能)
            phi_vev = self.find_higgs_vev(T)
            results['phi_vev'].append(phi_vev)
            
            # 成核率
            gamma = self.bubble_nucleation_rate(T)
            results['transition_rate'].append(gamma)
            
            # 气泡填充分数 (简化模型)
            if T < self.T_c:
                bubble_fraction += gamma * 1e-40  # 时间步长近似
            bubble_fraction = min(bubble_fraction, 1.0)
            results['bubble_fraction'].append(bubble_fraction)
            
            # 畴壁密度
            if bubble_fraction > 0 and bubble_fraction < 1:
                wall_density = 3 * bubble_fraction * (1 - bubble_fraction)
            else:
                wall_density = 0
            results['domain_wall_density'].append(wall_density)
        
        return {k: np.array(v) if k != 'T' else v for k, v in results.items()}
    
    def find_higgs_vev(self, T):
        """找到给定温度下的Higgs VEV"""
        if T > self.T_c * 1.1:
            return 0.0
        
        # 最小化自由能
        def dV_dphi(phi):
            if phi < 0:
                return 1e10
            m_T_sq = self.lambda_phi * (T**2 - self.T_c**2)
            tau_eff = self.tau_0 * T
            return m_T_sq * phi + self.lambda_phi * phi**3 + tau_eff**2 * phi
        
        try:
            phi_min = fsolve(dV_dphi, self.m_phi)[0]
            return max(0, phi_min)
        except:
            return 0.0
    
    def visualize_phase_transition(self, results, save_path=None):
        """可视化相变过程"""
        fig = plt.figure(figsize=(16, 12))
        gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        T = results['T']
        
        # 1. 谱维演化
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.semilogx(T, results['d_s'], 'b-', linewidth=2)
        ax1.axvline(self.T_c, color='r', linestyle='--', alpha=0.5, label=f'T_c = {self.T_c:.2e}')
        ax1.set_xlabel('T (GeV)', fontsize=11)
        ax1.set_ylabel('d_s', fontsize=11)
        ax1.set_title('Spectral Dimension Evolution', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.invert_xaxis()
        
        # 2. Higgs VEV
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.loglog(T, results['phi_vev'], 'g-', linewidth=2)
        ax2.axvline(self.T_c, color='r', linestyle='--', alpha=0.5)
        ax2.set_xlabel('T (GeV)', fontsize=11)
        ax2.set_ylabel('<φ> (GeV)', fontsize=11)
        ax2.set_title('Higgs VEV Evolution', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.invert_xaxis()
        
        # 3. 相变速率
        ax3 = fig.add_subplot(gs[0, 2])
        ax3.loglog(T, results['transition_rate'] + 1e-100, 'r-', linewidth=2)
        ax3.axvline(self.T_c, color='k', linestyle='--', alpha=0.5)
        ax3.set_xlabel('T (GeV)', fontsize=11)
        ax3.set_ylabel('Nucleation Rate', fontsize=11)
        ax3.set_title('Bubble Nucleation Rate', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.invert_xaxis()
        
        # 4. 气泡填充
        ax4 = fig.add_subplot(gs[1, 0])
        ax4.semilogx(T, results['bubble_fraction'], 'purple', linewidth=2)
        ax4.axvline(self.T_c, color='r', linestyle='--', alpha=0.5)
        ax4.set_xlabel('T (GeV)', fontsize=11)
        ax4.set_ylabel('Bubble Fraction', fontsize=11)
        ax4.set_title('Bubble Volume Fraction', fontsize=12, fontweight='bold')
        ax4.set_ylim([0, 1.1])
        ax4.grid(True, alpha=0.3)
        ax4.invert_xaxis()
        
        # 5. 畴壁密度
        ax5 = fig.add_subplot(gs[1, 1])
        ax5.semilogx(T, results['domain_wall_density'], 'orange', linewidth=2)
        ax5.axvline(self.T_c, color='r', linestyle='--', alpha=0.5)
        ax5.set_xlabel('T (GeV)', fontsize=11)
        ax5.set_ylabel('Domain Wall Density', fontsize=11)
        ax5.set_title('Topological Defect Density', fontsize=12, fontweight='bold')
        ax5.grid(True, alpha=0.3)
        ax5.invert_xaxis()
        
        # 6. 临界行为 (缩放)
        ax6 = fig.add_subplot(gs[1, 2])
        t_reduced = (self.T_c - T) / self.T_c
        valid = (t_reduced > 0) & (t_reduced < 0.2)
        if np.any(valid):
            ax6.loglog(t_reduced[valid], results['phi_vev'][valid], 'o', markersize=3)
            # 拟合临界指数
            log_t = np.log10(t_reduced[valid])
            log_phi = np.log10(results['phi_vev'][valid])
            if len(log_t) > 5:
                slope = np.polyfit(log_t, log_phi, 1)[0]
                ax6.plot(t_reduced[valid], 10**(slope*log_t[0]) * t_reduced[valid]**slope, 
                        'r--', label=f'β ≈ {slope:.2f}')
            ax6.set_xlabel('(Tc - T)/Tc', fontsize=11)
            ax6.set_ylabel('<φ>', fontsize=11)
            ax6.set_title('Critical Behavior (Order Parameter)', fontsize=12, fontweight='bold')
            ax6.legend()
            ax6.grid(True, alpha=0.3)
        
        # 7. 自由能景观
        ax7 = fig.add_subplot(gs[2, 0])
        phi_range = np.linspace(0, 2e16, 100)
        for T_plot in [0.8*self.T_c, 0.95*self.T_c, self.T_c, 1.05*self.T_c]:
            V_vals = [self.effective_free_energy(phi, T_plot, self.tau_0) for phi in phi_range]
            V_vals = np.array(V_vals) - min(V_vals)
            ax7.plot(phi_range/1e16, V_vals/1e60, label=f'T = {T_plot/1e16:.2f}×10¹⁶ GeV')
        ax7.set_xlabel('φ/(10¹⁶ GeV)', fontsize=11)
        ax7.set_ylabel('V(φ) (×10⁶⁰ GeV⁴)', fontsize=11)
        ax7.set_title('Free Energy Landscape', fontsize=12, fontweight='bold')
        ax7.legend(fontsize=9)
        ax7.grid(True, alpha=0.3)
        
        # 8. 参数总结
        ax8 = fig.add_subplot(gs[2, 1:])
        ax8.axis('off')
        
        # 获取临界指数
        exponents = self.calculate_critical_exponents()
        order, _ = self.determine_transition_order()
        wall = self.domain_wall_structure(self.T_c)
        
        summary_text = f"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                    GUT PHASE TRANSITION ANALYSIS SUMMARY                          ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  Phase Transition Order: {order:<25}                                     ║
║  Critical Temperature:   T_c = {self.T_c:.3e} GeV                              ║
║  Spectral Dimension:     d_s(T_c) = {self.spectral_dimension(self.T_c):.2f}                         ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  Critical Exponents:                                                             ║
║    β (order parameter) = {exponents['beta']:.3f}  [MF: 0.5]                              ║
║    α (specific heat)   = {exponents['alpha']:.3f}  [MF: 0.0]                              ║
║    γ (susceptibility)  = {exponents['gamma']:.3f}  [MF: 1.0]                              ║
║    ν (correlation len) = {exponents['nu']:.3f}  [MF: 0.5]                              ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  Domain Wall Properties:                                                         ║
║    Width:   δ = {wall['width']:.2e} GeV⁻¹                                          ║
║    Tension: σ = {wall['tension']:.2e} GeV³                                        ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  Model Parameters:                                                               ║
║    τ₀ = {self.tau_0:.2e}, α_run = {self.alpha_run:.2f}, λ_τ = {self.lambda_torsion:.3f}                    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
        """
        ax8.text(0.05, 0.95, summary_text, transform=ax8.transAxes, fontsize=10,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.suptitle('GUT Phase Transition Dynamics in Unified Field Theory', 
                     fontsize=14, fontweight='bold', y=0.98)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"Figure saved to: {save_path}")
        
        plt.close()
        
        return fig


def main():
    """主函数 - 运行GUT相变模拟"""
    print("="*80)
    print("GUT PHASE TRANSITION DYNAMICS SIMULATION")
    print("Unified Field Theory Framework")
    print("="*80)
    
    # 创建模型实例
    model = GUTPhaseTransition(
        tau_0=1e-5,
        alpha_run=0.1,
        lambda_torsion=0.01
    )
    
    print(f"\nModel Parameters:")
    print(f"  τ₀ = {model.tau_0:.2e}")
    print(f"  α_run = {model.alpha_run:.2f}")
    print(f"  T_c = {model.T_c:.3e} GeV")
    
    # 计算临界指数
    exponents = model.calculate_critical_exponents()
    print(f"\nCritical Exponents:")
    print(f"  β = {exponents['beta']:.4f}")
    print(f"  α = {exponents['alpha']:.4f}")
    print(f"  γ = {exponents['gamma']:.4f}")
    print(f"  ν = {exponents['nu']:.4f}")
    
    # 判定相变阶数
    order, _ = model.determine_transition_order()
    print(f"\nPhase Transition Order: {order}")
    
    # 畴壁性质
    wall = model.domain_wall_structure(model.T_c)
    print(f"\nDomain Wall Properties:")
    print(f"  Width: {wall['width']:.2e} GeV⁻¹")
    print(f"  Tension: {wall['tension']:.2e} GeV³")
    
    # 运行数值模拟
    print("\nRunning phase transition simulation...")
    results = model.simulate_phase_transition(
        T_initial=1.2e16,
        T_final=0.8e16,
        n_steps=5000
    )
    
    # 可视化
    model.visualize_phase_transition(
        results,
        save_path='gut_phase_transition.png'
    )
    
    print("\nSimulation complete!")
    print("="*80)
    
    return model, results


if __name__ == "__main__":
    model, results = main()
