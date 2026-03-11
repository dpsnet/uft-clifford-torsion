#!/usr/bin/env python3
"""
参数扫描：探索tau_0的观测极限
Parameter Scan: Exploring Observational Limits of tau_0

目标: 找到tau_0的上限，使得理论不与现有观测冲突
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint

M_Planck = 1.22e19  # GeV

class ParameterScan:
    """参数扫描器"""
    
    def __init__(self):
        self.constraints = []
        
    def nucleosynthesis_constraint(self, tau_0):
        """
        核合成约束
        
        原理: 早期宇宙膨胀率改变会影响元素丰度
        约束: 氦-4丰度偏差 < 1%
        
        膨胀率修正: H -> H * sqrt(1 + rho_int/rho_rad)
        """
        # 简化模型: 核合成时期内部空间能量占比
        # f_int ~ tau_0^2 (在GUT相变后残留)
        f_int_bbn = tau_0**2 * 1e4  # 近似模型
        
        # 氦-4丰度对膨胀率的依赖 (弱)
        Y_p_change = 0.05 * f_int_bbn  # 5% * f_int
        
        # 约束: Y_p变化 < 1%
        if Y_p_change < 0.01:
            return "PASS", Y_p_change
        else:
            return "FAIL", Y_p_change
    
    def atomic_clock_constraint(self, tau_0):
        """
        原子钟约束
        
        原理: 扭转场影响原子能级
        约束: 铯原子钟频率漂移 < 10^-16
        """
        # 频率偏移 ~ g_tau * tau_0 * 10^2 MHz
        # 相对偏移 ~ tau_0 * 10^-4 (归一化后)
        delta_nu_nu = tau_0 * 1e-4
        
        if delta_nu_nu < 1e-16:
            return "PASS", delta_nu_nu
        else:
            return "FAIL", delta_nu_nu
    
    def cmb_constraint(self, tau_0):
        """
        CMB约束 (来自宇宙学常数和膨胀历史)
        
        原理: 内部空间能量影响宇宙膨胀
        约束: CMB声学峰位置偏差 < 1%
        """
        # 简化: 有效暗能量密度变化
        delta_omega = tau_0**2 * 1e2
        
        if delta_omega < 0.01:
            return "PASS", delta_omega
        else:
            return "FAIL", delta_omega
    
    def gw_detectability(self, tau_0):
        """
        引力波可探测性
        
        返回: 修正幅度
        """
        # 修正 ~ tau_0^2 * (f/f_Planck)^(d_s-4)
        # 在LISA频段 (~10^-3 Hz)
        f_LISA = 1e-3
        f_Planck = 1e43
        d_s = 4.0  # 低频段d_s=4
        
        correction = tau_0**2 * (f_LISA / f_Planck)**(d_s - 4)
        
        # LISA灵敏度 ~ 10^-11
        detectable = correction > 1e-11
        
        return correction, detectable
    
    def cmb_distortion_detectability(self, tau_0):
        """
        CMB谱畸变可探测性
        
        返回: mu畸变幅度
        """
        # mu ~ tau_0^2 * 1e-10 (简化模型)
        mu = tau_0**2 * 1e-10
        
        # PIXIE灵敏度 ~ 10^-8
        detectable = mu > 1e-8
        
        return mu, detectable
    
    def run_scan(self, tau_min=1e-6, tau_max=1e-1, n_points=100):
        """运行参数扫描"""
        tau_values = np.logspace(np.log10(tau_min), np.log10(tau_max), n_points)
        
        results = {
            'tau': tau_values,
            'nuc_status': [],
            'nuc_value': [],
            'clock_status': [],
            'clock_value': [],
            'cmb_status': [],
            'cmb_value': [],
            'gw_correction': [],
            'gw_detectable': [],
            'mu_distortion': [],
            'mu_detectable': []
        }
        
        print("开始参数扫描...")
        print(f"扫描范围: {tau_min:.0e} - {tau_max:.0e}")
        print(f"点数: {n_points}")
        print()
        
        for i, tau in enumerate(tau_values):
            if i % 20 == 0:
                print(f"进度: {i}/{n_points}, tau={tau:.2e}")
            
            # 核合成
            status, value = self.nucleosynthesis_constraint(tau)
            results['nuc_status'].append(status)
            results['nuc_value'].append(value)
            
            # 原子钟
            status, value = self.atomic_clock_constraint(tau)
            results['clock_status'].append(status)
            results['clock_value'].append(value)
            
            # CMB
            status, value = self.cmb_constraint(tau)
            results['cmb_status'].append(status)
            results['cmb_value'].append(value)
            
            # 引力波
            corr, det = self.gw_detectability(tau)
            results['gw_correction'].append(corr)
            results['gw_detectable'].append(det)
            
            # CMB畸变
            mu, det = self.cmb_distortion_detectability(tau)
            results['mu_distortion'].append(mu)
            results['mu_detectable'].append(det)
        
        return results
    
    def find_limits(self, results):
        """找到各约束的上限"""
        tau = results['tau']
        
        limits = {}
        
        # 核合成极限
        for i, status in enumerate(results['nuc_status']):
            if status == "FAIL":
                limits['nucleosynthesis'] = tau[max(0, i-1)]
                break
        else:
            limits['nucleosynthesis'] = tau[-1]
        
        # 原子钟极限
        for i, status in enumerate(results['clock_status']):
            if status == "FAIL":
                limits['atomic_clock'] = tau[max(0, i-1)]
                break
        else:
            limits['atomic_clock'] = tau[-1]
        
        # CMB极限
        for i, status in enumerate(results['cmb_status']):
            if status == "FAIL":
                limits['cmb'] = tau[max(0, i-1)]
                break
        else:
            limits['cmb'] = tau[-1]
        
        # 引力波可探测
        for i, det in enumerate(results['gw_detectable']):
            if det:
                limits['gw_detectable'] = tau[i]
                break
        else:
            limits['gw_detectable'] = None
        
        # CMB畸变可探测
        for i, det in enumerate(results['mu_detectable']):
            if det:
                limits['mu_detectable'] = tau[i]
                break
        else:
            limits['mu_detectable'] = None
        
        return limits
    
    def plot_results(self, results):
        """绘制扫描结果"""
        tau = results['tau']
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        
        # 1. 核合成约束
        axes[0, 0].semilogx(tau, results['nuc_value'], 'b-', linewidth=2)
        axes[0, 0].axhline(0.01, color='r', linestyle='--', label='Limit (1%)')
        axes[0, 0].set_xlabel('tau_0')
        axes[0, 0].set_ylabel('Y_p change')
        axes[0, 0].set_title('Nucleosynthesis Constraint')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 原子钟约束
        axes[0, 1].loglog(tau, results['clock_value'], 'g-', linewidth=2)
        axes[0, 1].axhline(1e-16, color='r', linestyle='--', label='Limit (10^-16)')
        axes[0, 1].set_xlabel('tau_0')
        axes[0, 1].set_ylabel('Delta nu / nu')
        axes[0, 1].set_title('Atomic Clock Constraint')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. CMB约束
        axes[0, 2].semilogx(tau, results['cmb_value'], 'm-', linewidth=2)
        axes[0, 2].axhline(0.01, color='r', linestyle='--', label='Limit (1%)')
        axes[0, 2].set_xlabel('tau_0')
        axes[0, 2].set_ylabel('Omega_Lambda change')
        axes[0, 2].set_title('CMB Constraint')
        axes[0, 2].legend()
        axes[0, 2].grid(True, alpha=0.3)
        
        # 4. 引力波修正
        axes[1, 0].loglog(tau, results['gw_correction'], 'c-', linewidth=2)
        axes[1, 0].axhline(1e-11, color='r', linestyle='--', label='LISA sensitivity')
        axes[1, 0].axhline(1e-12, color='orange', linestyle='--', label='CE/ET sensitivity')
        axes[1, 0].set_xlabel('tau_0')
        axes[1, 0].set_ylabel('GW correction')
        axes[1, 0].set_title('Gravitational Wave Correction')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 5. CMB畸变
        axes[1, 1].loglog(tau, results['mu_distortion'], 'purple', linewidth=2)
        axes[1, 1].axhline(1e-8, color='r', linestyle='--', label='PIXIE sensitivity')
        axes[1, 1].axhline(1e-9, color='green', linestyle='--', label='Voyage 2050')
        axes[1, 1].set_xlabel('tau_0')
        axes[1, 1].set_ylabel('mu distortion')
        axes[1, 1].set_title('CMB Spectral Distortion')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        # 6. 综合约束图
        # 绘制各约束的允许区域
        nuc_limit = [1 if s == "PASS" else 0 for s in results['nuc_status']]
        clock_limit = [1 if s == "PASS" else 0 for s in results['clock_status']]
        cmb_limit = [1 if s == "PASS" else 0 for s in results['cmb_status']]
        
        # 综合: 所有约束都通过
        combined = [n * c * m for n, c, m in zip(nuc_limit, clock_limit, cmb_limit)]
        
        axes[1, 2].semilogx(tau, nuc_limit, 'b-', alpha=0.5, label='Nucleosynthesis')
        axes[1, 2].semilogx(tau, clock_limit, 'g-', alpha=0.5, label='Atomic clock')
        axes[1, 2].semilogx(tau, cmb_limit, 'm-', alpha=0.5, label='CMB')
        axes[1, 2].semilogx(tau, combined, 'r-', linewidth=3, label='Combined')
        axes[1, 2].set_xlabel('tau_0')
        axes[1, 2].set_ylabel('Allowed (1) / Forbidden (0)')
        axes[1, 2].set_title('Combined Constraints')
        axes[1, 2].legend()
        axes[1, 2].grid(True, alpha=0.3)
        axes[1, 2].set_ylim([-0.1, 1.1])
        
        plt.tight_layout()
        plt.savefig('parameter_scan_results.png', dpi=150, bbox_inches='tight')
        print("\n图像已保存: parameter_scan_results.png")

def main():
    print("="*70)
    print("参数扫描: 探索tau_0的观测极限")
    print("="*70)
    
    scanner = ParameterScan()
    
    # 运行扫描
    results = scanner.run_scan(tau_min=1e-6, tau_max=1e-1, n_points=100)
    
    # 找到极限
    limits = scanner.find_limits(results)
    
    print("\n" + "="*70)
    print("扫描结果: tau_0 上限")
    print("="*70)
    
    for constraint, limit in limits.items():
        if limit is not None:
            print(f"{constraint:<25}: {limit:<12.2e}")
        else:
            print(f"{constraint:<25}: Not achievable in scan range")
    
    # 找出最严格的约束
    valid_limits = {k: v for k, v in limits.items() if v is not None and 'detectable' not in k}
    if valid_limits:
        most_stringent = min(valid_limits, key=valid_limits.get)
        print(f"\n最严格约束: {most_stringent}")
        print(f"tau_0 上限: {valid_limits[most_stringent]:.2e}")
    
    # 当前值评估
    tau_current = 1e-4
    print(f"\n当前使用值: tau_0 = {tau_current}")
    
    nuc_idx = np.argmin(np.abs(results['tau'] - tau_current))
    print(f"  核合成检验: {results['nuc_status'][nuc_idx]}")
    print(f"  原子钟检验: {results['clock_status'][nuc_idx]}")
    print(f"  CMB检验: {results['cmb_status'][nuc_idx]}")
    
    # 绘图
    scanner.plot_results(results)
    
    print("\n" + "="*70)
    print("参数扫描完成!")
    print("="*70)

if __name__ == "__main__":
    main()
