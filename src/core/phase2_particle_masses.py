#!/usr/bin/env python3
"""
第二阶段: 粒子谱的精确计算
Phase 2: Precision Calculation of Particle Spectrum

计算电子、μ子、τ子的质量比
基于扭转场理论的质量公式: m = m_0 * sqrt(tau^2 + (1/3)*tau^4)
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
import matplotlib.pyplot as plt

# 物理常数
m_e_exp = 0.5109989461  # MeV, 电子质量 (实验值)
m_mu_exp = 105.6583745   # MeV, μ子质量 (实验值)
m_tau_exp = 1776.86      # MeV, τ子质量 (实验值)

# 实验质量比
mu_e_ratio_exp = m_mu_exp / m_e_exp   # ~206.77
tau_mu_ratio_exp = m_tau_exp / m_mu_exp  # ~16.82
tau_e_ratio_exp = m_tau_exp / m_e_exp   # ~3477.2

class ParticleMassCalculator:
    """粒子质量计算器"""
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        self.m_0_e = 1.0  # 电子裸质量 (归一化)
        
    def mass_formula(self, tau, m_0):
        """
        扭转场质量公式
        m = m_0 * sqrt(tau^2 + (1/3)*tau^4)
        
        参数:
            tau: 扭转场强度
            m_0: 裸质量
        """
        return m_0 * np.sqrt(tau**2 + (1/3)*tau**4)
    
    def tau_for_generation(self, g, tau_gut=1.0):
        """
        代依赖的扭转场强度
        
        假设: 不同代的粒子感受不同强度的扭转场
        可能与它们在内部空间中的"位置"有关
        
        模型: tau_g = tau_gut * exp(-alpha * g)
        其中 g = 1, 2, 3 对应 e, mu, tau
        """
        alpha = np.log(10)  # 衰减系数 (待拟合)
        return self.tau_0 * np.exp(-alpha * (g - 1))
    
    def calculate_masses_v1(self, params):
        """
        版本1: 三代具有相同的裸质量，不同的扭转场
        
        参数: [tau_e, tau_mu, tau_tau]
        """
        tau_e, tau_mu, tau_tau = params
        
        m_e = self.mass_formula(tau_e, self.m_0_e)
        m_mu = self.mass_formula(tau_mu, self.m_0_e)
        m_tau = self.mass_formula(tau_tau, self.m_0_e)
        
        return m_e, m_mu, m_tau
    
    def calculate_masses_v2(self, params):
        """
        版本2: 三代具有不同的裸质量，相同的扭转场
        
        参数: [m_0_e, m_0_mu, m_0_tau, tau]
        """
        m_0_e, m_0_mu, m_0_tau, tau = params
        
        m_e = self.mass_formula(tau, m_0_e)
        m_mu = self.mass_formula(tau, m_0_mu)
        m_tau = self.mass_formula(tau, m_0_tau)
        
        return m_e, m_mu, m_tau
    
    def calculate_masses_v3(self, params):
        """
        版本3: 组合模型 - 不同的裸质量和扭转场
        
        参数: [m_0_e, m_0_mu, m_0_tau, tau_e, tau_mu, tau_tau]
        """
        m_0_e, m_0_mu, m_0_tau, tau_e, tau_mu, tau_tau = params
        
        m_e = self.mass_formula(tau_e, m_0_e)
        m_mu = self.mass_formula(tau_mu, m_0_mu)
        m_tau = self.mass_formula(tau_tau, m_0_tau)
        
        return m_e, m_mu, m_tau
    
    def chi_squared(self, params, version=3):
        """计算与实验值的卡方偏差"""
        if version == 1:
            m_e, m_mu, m_tau = self.calculate_masses_v1(params)
        elif version == 2:
            m_e, m_mu, m_tau = self.calculate_masses_v2(params)
        else:
            m_e, m_mu, m_tau = self.calculate_masses_v3(params)
        
        # 归一化到电子质量
        norm = m_e / m_e_exp
        m_e_calc = m_e / norm
        m_mu_calc = m_mu / norm
        m_tau_calc = m_tau / norm
        
        # 卡方
        chi2 = ((m_e_calc - m_e_exp) / (0.0000001))**2  # 电子质量固定
        chi2 += ((m_mu_calc - m_mu_exp) / (0.000002))**2
        chi2 += ((m_tau_calc - m_tau_exp) / (0.12))**2
        
        return chi2
    
    def fit_parameters(self, version=3):
        """拟合参数以匹配实验值"""
        print(f"\n拟合版本 {version}...")
        
        if version == 1:
            # 初始猜测: [tau_e, tau_mu, tau_tau]
            x0 = [1e-5, 1e-4, 1e-3]
            bounds = [(1e-8, 1), (1e-8, 1), (1e-8, 1)]
        elif version == 2:
            # 初始猜测: [m_0_e, m_0_mu, m_0_tau, tau]
            x0 = [1.0, 100.0, 1700.0, 1e-5]
            bounds = [(0.1, 10), (10, 1000), (100, 10000), (1e-8, 1)]
        else:
            # 初始猜测: [m_0_e, m_0_mu, m_0_tau, tau_e, tau_mu, tau_tau]
            x0 = [1.0, 10.0, 100.0, 1e-5, 1e-4, 1e-3]
            bounds = [(0.1, 10), (1, 1000), (10, 10000), 
                     (1e-8, 1), (1e-8, 1), (1e-8, 1)]
        
        # 使用差分进化算法
        result = differential_evolution(
            lambda x: self.chi_squared(x, version),
            bounds,
            seed=42,
            maxiter=1000
        )
        
        return result
    
    def evaluate_model(self, params, version=3):
        """评估模型拟合质量"""
        if version == 1:
            m_e, m_mu, m_tau = self.calculate_masses_v1(params)
        elif version == 2:
            m_e, m_mu, m_tau = self.calculate_masses_v2(params)
        else:
            m_e, m_mu, m_tau = self.calculate_masses_v3(params)
        
        # 归一化到电子质量
        norm = m_e / m_e_exp
        m_e_calc = m_e / norm
        m_mu_calc = m_mu / norm
        m_tau_calc = m_tau / norm
        
        # 计算质量比
        mu_e_ratio_calc = m_mu_calc / m_e_calc
        tau_mu_ratio_calc = m_tau_calc / m_mu_calc
        tau_e_ratio_calc = m_tau_calc / m_e_calc
        
        return {
            'm_e': m_e_calc,
            'm_mu': m_mu_calc,
            'm_tau': m_tau_calc,
            'mu_e_ratio': mu_e_ratio_calc,
            'tau_mu_ratio': tau_mu_ratio_calc,
            'tau_e_ratio': tau_e_ratio_calc
        }

def main():
    print("="*70)
    print("第二阶段: 粒子谱的精确计算")
    print("目标: 计算 e, μ, τ 的质量比")
    print("="*70)
    
    print("\n实验值:")
    print(f"  m_e = {m_e_exp:.7f} MeV")
    print(f"  m_mu = {m_mu_exp:.4f} MeV")
    print(f"  m_tau = {m_tau_exp:.2f} MeV")
    print()
    print(f"  m_mu / m_e = {mu_e_ratio_exp:.4f}")
    print(f"  m_tau / m_mu = {tau_mu_ratio_exp:.4f}")
    print(f"  m_tau / m_e = {tau_e_ratio_exp:.2f}")
    
    calc = ParticleMassCalculator(tau_0=1e-5)
    
    # 测试三个版本
    for version in [1, 2, 3]:
        print(f"\n{'='*70}")
        print(f"版本 {version} 拟合")
        print(f"{'='*70}")
        
        result = calc.fit_parameters(version)
        
        print(f"拟合成功: {result.success}")
        print(f"最小卡方: {result.fun:.2e}")
        print(f"最优参数: {result.x}")
        
        # 评估
        eval_result = calc.evaluate_model(result.x, version)
        
        print("\n计算结果:")
        print(f"  m_e = {eval_result['m_e']:.7f} MeV (目标: {m_e_exp:.7f})")
        print(f"  m_mu = {eval_result['m_mu']:.4f} MeV (目标: {m_mu_exp:.4f})")
        print(f"  m_tau = {eval_result['m_tau']:.2f} MeV (目标: {m_tau_exp:.2f})")
        print()
        print(f"  m_mu / m_e = {eval_result['mu_e_ratio']:.4f} (目标: {mu_e_ratio_exp:.4f})")
        print(f"  m_tau / m_mu = {eval_result['tau_mu_ratio']:.4f} (目标: {tau_mu_ratio_exp:.4f})")
        print(f"  m_tau / m_e = {eval_result['tau_e_ratio']:.2f} (目标: {tau_e_ratio_exp:.2f})")
        
        # 偏差
        print("\n偏差:")
        print(f"  μ/e 比偏差: {abs(eval_result['mu_e_ratio'] - mu_e_ratio_exp) / mu_e_ratio_exp * 100:.4f}%")
        print(f"  τ/μ 比偏差: {abs(eval_result['tau_mu_ratio'] - tau_mu_ratio_exp) / tau_mu_ratio_exp * 100:.4f}%")
        print(f"  τ/e 比偏差: {abs(eval_result['tau_e_ratio'] - tau_e_ratio_exp) / tau_e_ratio_exp * 100:.4f}%")
    
    print("\n" + "="*70)
    print("第二阶段计算完成!")
    print("="*70)

if __name__ == "__main__":
    main()
