#!/usr/bin/env python3
"""
扭转场驱动的重子产生机制 (Baryogenesis)
=====================================

在统一场理论框架下，重子产生通过以下机制实现:
1. 扭转场诱导的CP破坏
2. 谱维演化驱动的非平衡过程
3. GUT重子数破坏过程

观测目标: η_B = n_B/n_γ ≈ 6×10⁻¹⁰

作者: 统一场理论研究团队
版本: 1.0.0
日期: 2026-03-18
"""

import numpy as np
from scipy.integrate import odeint, quad
from scipy.special import zeta, polygamma
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, Dict

# 物理常数
class Constants:
    M_Planck = 1.22091e19  # GeV
    T_GUT = 1e16  # GeV
    T_EW = 100  # GeV
    alpha_GUT = 1/25
    
    # 重子不对称度观测值
    eta_B_obs = 6.1e-10
    eta_B_obs_err = 0.2e-10
    
    # 有效自由度
    g_star_GUT = 106.75
    g_star_EW = 106.75

const = Constants()


@dataclass
class BaryogenesisParameters:
    """重子产生模型参数"""
    tau_0: float = 1e-5  # 基准扭转参数
    alpha_CP: float = 0.01  # CP破坏参数
    epsilon_B: float = 0.001  # 重子数破坏效率
    M_X: float = 1e16  # 重GUT玻色子质量
    Gamma_X: float = 1e15  # 衰变宽度


class TorsionBaryogenesis:
    """
    扭转场驱动的重子产生机制
    
    核心思想:
    - 在分形时空中，扭转场 τ_μν 与费米子场的耦合产生有效CP破坏
    - 谱维演化 d_s: 10→4 驱动系统偏离热平衡
    - GUT玻色子X的衰变产生重子不对称
    """
    
    def __init__(self, params: BaryogenesisParameters = None):
        if params is None:
            params = BaryogenesisParameters()
        self.params = params
        
        # 计算派生参数
        self.H_GUT = self.calculate_hubble_rate(const.T_GUT)
        self.t_GUT = 1.0 / self.H_GUT
        
    def calculate_hubble_rate(self, T):
        """计算哈勃率 H = √(8πρ/3)/M_P"""
        rho = (np.pi**2 / 30) * const.g_star_GUT * T**4
        H = np.sqrt(8 * np.pi * rho / 3) / const.M_Planck
        return H
    
    def spectral_dimension(self, T):
        """谱维作为温度函数"""
        x = np.log(T / const.T_GUT)
        return 4.0 + 6.0 / (1.0 + np.exp(-2.0 * x))
    
    def torsion_field(self, T):
        """
        有效扭转场作为温度函数
        
        τ(T) = τ₀ × (T/T_GUT)^n × f(d_s)
        
        其中f(d_s)考虑了维度效应
        """
        # 温度依赖
        n = 2.0  # 跑动指数
        tau_T = self.params.tau_0 * (T / const.T_GUT)**n
        
        # 维度修正: 高维时扭转效应更强
        d_s = self.spectral_dimension(T)
        dim_factor = (d_s - 4) / 6.0  # 0到1之间
        
        return tau_T * (1.0 + dim_factor)
    
    def cp_violation_parameter(self, T):
        """
        计算有效CP破坏参数
        
        在统一场理论中，CP破坏来源于:
        1. 扭转场的几何相位
        2. 分形时空的非对易几何效应
        
        ε_CP ∝ α_CP × τ(T) × sin(δ_phase)
        """
        tau = self.torsion_field(T)
        
        # 相位因子 (来自扭转场动力学)
        delta_phase = np.pi / 4  # 典型值
        
        epsilon = self.params.alpha_CP * tau * np.sin(delta_phase)
        return epsilon
    
    def baryon_violation_rate(self, T):
        """
        重子数破坏过程速率
        
        GUT尺度: X玻色子衰变 B-L破坏
        Γ_B ∝ α_GUT² × T⁴ / M_X²
        """
        rate = const.alpha_GUT**2 * T**4 / self.params.M_X**2
        return rate
    
    def out_of_equilibrium_parameter(self, T):
        """
        非平衡参数
        
        K = Γ_X / H(T)
        
        K << 1: 强烈非平衡 ( washout可忽略)
        K ~ 1: 过渡区
        K >> 1: 热平衡
        """
        H = self.calculate_hubble_rate(T)
        Gamma_X = self.params.Gamma_X * (self.torsion_field(T) / self.params.tau_0)
        K = Gamma_X / H
        return K
    
    def calculate_baryon_asymmetry(self):
        """
        计算重子不对称度 η_B = n_B/n_γ
        
        基于Sakharov条件的统一场理论实现:
        
        1. 重子数破坏: GUT玻色子衰变
        2. C/CP破坏: 扭转场诱导
        3. 非平衡: 谱维演化驱动
        
        关键公式:
        η_B ≈ (n_X/n_γ) × ε_CP × Br × κ_washout
        
        其中:
        - n_X/n_γ: 重粒子丰度
        - ε_CP: CP破坏参数
        - Br: 分支比
        - κ_washout: washout抑制因子
        """
        # 1. 计算GUT温度下的重粒子丰度
        # 假设热产生
        n_X_over_s = 3/4 * (135/4/np.pi**4/const.g_star_GUT)  # 近似值
        
        # 2. 有效CP破坏
        epsilon_CP = self.cp_violation_parameter(const.T_GUT)
        
        # 3. 衰变不对称
        # ε = (Γ(X→q) - Γ(X→q̄)) / (Γ(X→q) + Γ(X→q̄))
        decay_asymmetry = epsilon_CP * self.params.epsilon_B
        
        # 4. Washout因子
        K = self.out_of_equilibrium_parameter(const.T_GUT)
        if K < 1:
            # 弱washout
            washout_factor = 1.0 - 0.5 * K
        else:
            # 强washout
            washout_factor = 1.0 / (1.0 + K**1.2)
        
        # 5. 熵密度转换 n_γ/s ≈ 1/7
        n_gamma_over_s = 1.0 / 7.0
        
        # 6. 最终不对称度
        eta_B = n_X_over_s * decay_asymmetry * washout_factor / n_gamma_over_s
        
        return {
            'eta_B': eta_B,
            'epsilon_CP': epsilon_CP,
            'decay_asymmetry': decay_asymmetry,
            'washout_factor': washout_factor,
            'K': K,
            'components': {
                'n_X_over_s': n_X_over_s,
                'n_gamma_over_s': n_gamma_over_s
            }
        }
    
    def solve_boltzmann_equations(self, T_range=None):
        """
        数值求解Boltzmann方程
        
        跟踪:
        - n_X: 重GUT玻色子丰度
        - n_B: 重子数密度
        - 考虑扭转场修正
        """
        if T_range is None:
            T_range = np.logspace(np.log10(const.T_GUT*2), np.log10(const.T_GUT/10), 1000)
        
        # 变量: Y_X = n_X/s, Y_B = n_B/s
        # s = (2π²/45)g*T³ 是熵密度
        
        def entropy_density(T):
            return (2 * np.pi**2 / 45) * const.g_star_GUT * T**3
        
        def equations(Y, T):
            """Boltzmann方程组"""
            Y_X, Y_B = Y
            
            # 哈勃率
            H = self.calculate_hubble_rate(T)
            
            # 熵密度
            s = entropy_density(T)
            
            # 热平衡丰度
            Y_X_eq = (45 / (4 * np.pi**4)) * (const.M_Planck * self.params.Gamma_X / T**2) * np.exp(-self.params.M_X / T)
            
            # 相互作用率
            Gamma_X = self.params.Gamma_X * (self.torsion_field(T) / self.params.tau_0)
            
            # CP破坏
            epsilon = self.cp_violation_parameter(T)
            
            # washout率
            Gamma_wash = self.baryon_violation_rate(T)
            
            # dY_X/dT (使用dT/dt = -HT)
            dY_X_dT = (Gamma_X / (H * T)) * (Y_X - Y_X_eq)
            
            # dY_B/dT
            source = epsilon * Gamma_X * (Y_X - Y_X_eq) / (H * T)
            washout = Gamma_wash * Y_B / (H * T)
            dY_B_dT = source - washout
            
            return [dY_X_dT, dY_B_dT]
        
        # 初始条件
        Y_X_init = 0.01  # 初始丰度
        Y_B_init = 0.0
        Y_init = [Y_X_init, Y_B_init]
        
        # 求解 (从高到低温度)
        solution = odeint(equations, Y_init, T_range[::-1])
        solution = solution[::-1]  # 恢复顺序
        
        Y_X = solution[:, 0]
        Y_B = solution[:, 1]
        
        # 转换为η_B
        s_over_gamma = 7.04  # s/n_γ
        eta_B = Y_B * s_over_gamma
        
        return {
            'T': T_range,
            'Y_X': Y_X,
            'Y_B': Y_B,
            'eta_B': eta_B,
            'final_eta_B': eta_B[-1] if len(eta_B) > 0 else 0
        }
    
    def compare_with_observation(self, eta_B_calculated):
        """与观测值比较"""
        eta_B_obs = const.eta_B_obs
        eta_B_obs_err = const.eta_B_obs_err
        
        ratio = eta_B_calculated / eta_B_obs
        sigma = abs(eta_B_calculated - eta_B_obs) / eta_B_obs_err
        
        return {
            'calculated': eta_B_calculated,
            'observed': eta_B_obs,
            'ratio': ratio,
            'sigma': sigma,
            'compatible': sigma < 2  # 2σ以内认为兼容
        }
    
    def parameter_scan(self):
        """
        参数空间扫描，寻找能产生正确η_B的参数
        """
        # 扫描tau_0和alpha_CP
        tau_0_values = np.logspace(-6, -3, 20)
        alpha_CP_values = np.logspace(-3, -1, 20)
        
        results = np.zeros((len(tau_0_values), len(alpha_CP_values)))
        
        for i, tau_0 in enumerate(tau_0_values):
            for j, alpha_CP in enumerate(alpha_CP_values):
                self.params.tau_0 = tau_0
                self.params.alpha_CP = alpha_CP
                
                result = self.calculate_baryon_asymmetry()
                eta_B = result['eta_B']
                
                # 记录与观测值的差距 (log scale)
                results[i, j] = np.log10(abs(eta_B) + 1e-20)
        
        return {
            'tau_0': tau_0_values,
            'alpha_CP': alpha_CP_values,
            'log_eta_B': results
        }
    
    def visualize_baryogenesis(self, boltzmann_results=None, save_path=None):
        """可视化重子产生过程"""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        
        # 1. CP破坏参数随温度变化
        ax1 = axes[0, 0]
        T_range = np.logspace(15, 17, 100)
        epsilon_vals = [self.cp_violation_parameter(T) for T in T_range]
        ax1.loglog(T_range, epsilon_vals, 'b-', linewidth=2)
        ax1.axvline(const.T_GUT, color='r', linestyle='--', alpha=0.5, label='T_GUT')
        ax1.set_xlabel('T (GeV)', fontsize=11)
        ax1.set_ylabel('ε_CP', fontsize=11)
        ax1.set_title('CP Violation Parameter', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 扭转场
        ax2 = axes[0, 1]
        tau_vals = [self.torsion_field(T) for T in T_range]
        ax2.loglog(T_range, tau_vals, 'g-', linewidth=2)
        ax2.axvline(const.T_GUT, color='r', linestyle='--', alpha=0.5)
        ax2.set_xlabel('T (GeV)', fontsize=11)
        ax2.set_ylabel('τ(T)', fontsize=11)
        ax2.set_title('Torsion Field Evolution', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # 3. 非平衡参数
        ax3 = axes[0, 2]
        K_vals = [self.out_of_equilibrium_parameter(T) for T in T_range]
        ax3.loglog(T_range, K_vals, 'purple', linewidth=2)
        ax3.axvline(const.T_GUT, color='r', linestyle='--', alpha=0.5)
        ax3.axhline(1.0, color='k', linestyle=':', alpha=0.5, label='K=1')
        ax3.set_xlabel('T (GeV)', fontsize=11)
        ax3.set_ylabel('K = Γ/H', fontsize=11)
        ax3.set_title('Out-of-Equilibrium Parameter', fontsize=12, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Boltzmann演化 (如果有)
        ax4 = axes[1, 0]
        if boltzmann_results:
            ax4.semilogy(boltzmann_results['T'], boltzmann_results['Y_X'], 
                        'b-', linewidth=2, label='Y_X')
            ax4.semilogy(boltzmann_results['T'], np.abs(boltzmann_results['Y_B']), 
                        'r-', linewidth=2, label='|Y_B|')
            ax4.set_xlabel('T (GeV)', fontsize=11)
            ax4.set_ylabel('Y = n/s', fontsize=11)
            ax4.set_title('Abundance Evolution', fontsize=12, fontweight='bold')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            ax4.invert_xaxis()
        else:
            ax4.text(0.5, 0.5, 'Boltzmann\nnot run', ha='center', va='center', 
                    transform=ax4.transAxes)
        
        # 5. η_B演化
        ax5 = axes[1, 1]
        if boltzmann_results:
            ax5.semilogx(boltzmann_results['T'], boltzmann_results['eta_B'], 
                        'g-', linewidth=2)
            ax5.axhline(const.eta_B_obs, color='r', linestyle='--', 
                       label=f'Obs: {const.eta_B_obs:.2e}')
            ax5.fill_between([1e15, 1e17], 
                           const.eta_B_obs - const.eta_B_obs_err,
                           const.eta_B_obs + const.eta_B_obs_err,
                           alpha=0.3, color='red')
            ax5.set_xlabel('T (GeV)', fontsize=11)
            ax5.set_ylabel('η_B', fontsize=11)
            ax5.set_title('Baryon Asymmetry Evolution', fontsize=12, fontweight='bold')
            ax5.legend()
            ax5.grid(True, alpha=0.3)
            ax5.invert_xaxis()
        else:
            ax5.text(0.5, 0.5, 'Boltzmann\nnot run', ha='center', va='center',
                    transform=ax5.transAxes)
        
        # 6. 结果总结
        ax6 = axes[1, 2]
        ax6.axis('off')
        
        result = self.calculate_baryon_asymmetry()
        comparison = self.compare_with_observation(result['eta_B'])
        
        summary = f"""
╔═══════════════════════════════════════════════════════════════╗
║           BARYOGENESIS RESULTS SUMMARY                        ║
╠═══════════════════════════════════════════════════════════════╣
║  Calculated η_B:        {result['eta_B']:.3e}                 ║
║  Observed η_B:          {const.eta_B_obs:.3e} ± {const.eta_B_obs_err:.1e}         ║
║  Ratio (calc/obs):      {comparison['ratio']:.2f}                      ║
║  Deviation:             {comparison['sigma']:.1f}σ                      ║
║  Compatible:            {'YES ✓' if comparison['compatible'] else 'NO ✗'}                    ║
╠═══════════════════════════════════════════════════════════════╣
║  Key Parameters:                                              ║
║    τ₀ = {self.params.tau_0:.2e}                                  ║
║    α_CP = {self.params.alpha_CP:.3f}                                ║
║    ε_B = {self.params.epsilon_B:.4f}                              ║
╠═══════════════════════════════════════════════════════════════╣
║  Intermediate Results:                                        ║
║    ε_CP = {result['epsilon_CP']:.3e}                         ║
║    Washout factor = {result['washout_factor']:.3f}                   ║
║    K = {result['K']:.3f}                                 ║
╚═══════════════════════════════════════════════════════════════╝
        """
        ax6.text(0.05, 0.95, summary, transform=ax6.transAxes, fontsize=10,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightgreen' if comparison['compatible'] else 'lightcoral',
                         alpha=0.5))
        
        plt.suptitle('Torsion-Driven Baryogenesis in Unified Field Theory', 
                     fontsize=14, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"Figure saved to: {save_path}")
        
        plt.close()
        
        return fig


def main():
    """主函数"""
    print("="*80)
    print("TORSION-DRIVEN BARYOGENESIS CALCULATION")
    print("Unified Field Theory Framework")
    print("="*80)
    
    # 创建模型 (精确调整参数以匹配观测 η_B ≈ 6×10^-10)
    # 公式: eta_B ~ (n_X/s) * epsilon_CP * epsilon_B * washout / (n_gamma/s)
    params = BaryogenesisParameters(
        tau_0=1.2e-4,    # 略微增加扭转场
        alpha_CP=0.035,  # 略微增加CP破坏
        epsilon_B=0.035, # 重子数破坏效率
        M_X=1e16,
        Gamma_X=2.5e14   # 调节非平衡参数
    )
    
    model = TorsionBaryogenesis(params)
    
    print(f"\nModel Parameters:")
    print(f"  τ₀ = {params.tau_0:.2e}")
    print(f"  α_CP = {params.alpha_CP:.3f}")
    print(f"  M_X = {params.M_X:.2e} GeV")
    print(f"  Γ_X = {params.Gamma_X:.2e} GeV")
    
    # 解析计算
    print("\n--- Analytical Calculation ---")
    result = model.calculate_baryon_asymmetry()
    print(f"  η_B = {result['eta_B']:.3e}")
    print(f"  ε_CP = {result['epsilon_CP']:.3e}")
    print(f"  Washout factor = {result['washout_factor']:.4f}")
    
    # 与观测比较
    comparison = model.compare_with_observation(result['eta_B'])
    print(f"\nComparison with Observation:")
    print(f"  Observed: η_B = {const.eta_B_obs:.3e} ± {const.eta_B_obs_err:.1e}")
    print(f"  Ratio: {comparison['ratio']:.2f}")
    print(f"  Deviation: {comparison['sigma']:.1f}σ")
    print(f"  Compatible: {'YES ✓' if comparison['compatible'] else 'NO ✗'}")
    
    # 数值求解Boltzmann方程
    print("\n--- Numerical Boltzmann Evolution ---")
    boltzmann_results = model.solve_boltzmann_equations()
    print(f"  Final η_B (numerical) = {boltzmann_results['final_eta_B']:.3e}")
    
    # 可视化
    model.visualize_baryogenesis(boltzmann_results, 
                                 save_path='torsion_baryogenesis.png')
    
    print("\n" + "="*80)
    
    return model, result, boltzmann_results


if __name__ == "__main__":
    model, result, boltzmann_results = main()
