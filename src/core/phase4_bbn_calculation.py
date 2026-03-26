#!/usr/bin/env python3
"""
6-12个月阶段: BBN精确计算
BBN Precision Calculation

修改标准BBN代码，加入谱维演化效应
"""

import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt

# 物理常数
m_n = 939.565  # MeV, 中子质量
m_p = 938.272  # MeV, 质子质量
Q = m_n - m_p  # MeV, 质量差

# BBN温度点
T_BBN_start = 1.0  # MeV (开始)
T_BBN_end = 0.1    # MeV (结束)

class BBNWithSpectralDimension:
    """带谱维修正的BBN计算器"""
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        
    def neutron_proton_ratio(self, T):
        """
        中子/质子比
        
        标准公式: n/p = exp(-Q/T)
        
        修正: 谱维影响弱相互作用率
        Gamma_weak ~ G_F^2 T^5 -> Gamma_weak_eff ~ Gamma_weak * g(T)
        """
        # 标准比
        ratio_std = np.exp(-Q / T)
        
        # 谱维修正 (简化模型)
        # 高谱维 -> 弱相互作用率变化 -> 平衡温度变化
        if T > 0.5:  # 高T时d_s可能偏离4
            d_s = 4 + 6 * np.exp(-T/0.5)  # 简化模型
            correction = (d_s / 4)**(-1/3)  # 弱作用率 ~ T^(5 + delta)
        else:
            correction = 1.0
        
        ratio_corrected = ratio_std * correction
        
        return ratio_std, ratio_corrected, correction
    
    def helium4_abundance(self, T):
        """
        He-4质量分数 Y_p
        
        Y_p ~ 2 * (n/p) / (1 + n/p)
        """
        ratio_std, ratio_corr, _ = self.neutron_proton_ratio(T)
        
        # 标准He-4丰度
        Y_p_std = 2 * ratio_std / (1 + ratio_std)
        
        # 修正He-4丰度
        Y_p_corr = 2 * ratio_corr / (1 + ratio_corr)
        
        return Y_p_std, Y_p_corr
    
    def deuterium_abundance(self, T):
        """
        D/H 比
        
        简化模型: D/H ~ exp(B_D/T) 其中B_D是氘结合能
        """
        B_D = 2.22  # MeV, 氘结合能
        
        # 标准
        D_H_std = np.exp(-B_D / T) * 1e-5  # 归一化
        
        # 谱维修正 (高谱维增强核反应)
        if T > 0.1:
            d_s = 4 + 2 * np.exp(-T/0.2)
            enhancement = (d_s / 4)**2  # 反应率增强
        else:
            enhancement = 1.0
        
        D_H_corr = D_H_std * enhancement
        
        return D_H_std, D_H_corr
    
    def lithium7_abundance(self, T):
        """
        Li-7/H 比
        
        简化模型
        """
        # 标准 (文献值)
        Li7_H_std = 5e-10
        
        # 谱维修正 (可能对Be-7 -> Li-7影响)
        # 简化: 假设小修正
        correction = 1 + self.tau_0**2 * 1e3
        Li7_H_corr = Li7_H_std * correction
        
        return Li7_H_std, Li7_H_corr
    
    def calculate_bbn(self):
        """计算BBN核合成"""
        # 温度范围
        T_range = np.linspace(T_BBN_start, T_BBN_end, 100)
        
        results = {
            'T': T_range,
            'Y_p_std': [],
            'Y_p_corr': [],
            'D_H_std': [],
            'D_H_corr': [],
            'Li7_H_std': [],
            'Li7_H_corr': [],
            'n_p_ratio_std': [],
            'n_p_ratio_corr': []
        }
        
        for T in T_range:
            # He-4
            Y_std, Y_corr = self.helium4_abundance(T)
            results['Y_p_std'].append(Y_std)
            results['Y_p_corr'].append(Y_corr)
            
            # D
            D_std, D_corr = self.deuterium_abundance(T)
            results['D_H_std'].append(D_std)
            results['D_H_corr'].append(D_corr)
            
            # Li-7
            Li_std, Li_corr = self.lithium7_abundance(T)
            results['Li7_H_std'].append(Li_std)
            results['Li7_H_corr'].append(Li_corr)
            
            # n/p比
            ratio_std, ratio_corr, _ = self.neutron_proton_ratio(T)
            results['n_p_ratio_std'].append(ratio_std)
            results['n_p_ratio_corr'].append(ratio_corr)
        
        return results
    
    def compare_with_observation(self, results):
        """与观测值对比"""
        # 观测值 (Planck 2018 + BBN)
        Y_p_obs = 0.245  # ± 0.003
        D_H_obs = 2.6e-5  # ± 0.1e-5
        Li7_H_obs = 1.6e-10  # 或 5e-10 (锂缺失问题)
        
        # 取最终值 (T = 0.1 MeV)
        idx = -1
        
        print("\nBBN元素丰度对比:")
        print("="*60)
        print(f"{'元素':<10} {'标准BBN':<15} {'修正BBN':<15} {'观测值':<15}")
        print("-"*60)
        print(f"{'Y_p':<10} {results['Y_p_std'][idx]:<15.4f} {results['Y_p_corr'][idx]:<15.4f} {Y_p_obs:<15.4f}")
        print(f"{'D/H':<10} {results['D_H_std'][idx]:<15.2e} {results['D_H_corr'][idx]:<15.2e} {D_H_obs:<15.2e}")
        print(f"{'Li-7/H':<10} {results['Li7_H_std'][idx]:<15.2e} {results['Li7_H_corr'][idx]:<15.2e} {Li7_H_obs:<15.2e}")
        
        # 计算偏差
        print("\n偏差:")
        print(f"  Y_p: 标准 {(results['Y_p_std'][idx]-Y_p_obs)/Y_p_obs*100:.2f}%, 修正 {(results['Y_p_corr'][idx]-Y_p_obs)/Y_p_obs*100:.2f}%")
        print(f"  D/H: 标准 {(results['D_H_std'][idx]-D_H_obs)/D_H_obs*100:.2f}%, 修正 {(results['D_H_corr'][idx]-D_H_obs)/D_H_obs*100:.2f}%")
    
    def plot_bbn(self, results):
        """绘制BBN结果"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        T = results['T']
        
        # 1. He-4丰度
        axes[0, 0].semilogy(T, results['Y_p_std'], 'b-', label='Standard')
        axes[0, 0].semilogy(T, results['Y_p_corr'], 'r--', label='Modified')
        axes[0, 0].axhline(0.245, color='g', linestyle=':', label='Observation')
        axes[0, 0].set_xlabel('T (MeV)')
        axes[0, 0].set_ylabel('Y_p')
        axes[0, 0].set_title('He-4 Mass Fraction')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. D/H
        axes[0, 1].loglog(T, results['D_H_std'], 'b-', label='Standard')
        axes[0, 1].loglog(T, results['D_H_corr'], 'r--', label='Modified')
        axes[0, 1].axhline(2.6e-5, color='g', linestyle=':', label='Observation')
        axes[0, 1].set_xlabel('T (MeV)')
        axes[0, 1].set_ylabel('D/H')
        axes[0, 1].set_title('Deuterium Abundance')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. n/p比
        axes[1, 0].semilogy(T, results['n_p_ratio_std'], 'b-', label='Standard')
        axes[1, 0].semilogy(T, results['n_p_ratio_corr'], 'r--', label='Modified')
        axes[1, 0].set_xlabel('T (MeV)')
        axes[1, 0].set_ylabel('n/p ratio')
        axes[1, 0].set_title('Neutron/Proton Ratio')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 所有元素 (最终值)
        elements = ['He-4', 'D', 'Li-7']
        std_vals = [results['Y_p_std'][-1], results['D_H_std'][-1]/1e-5, results['Li7_H_std'][-1]/1e-10]
        corr_vals = [results['Y_p_corr'][-1], results['D_H_corr'][-1]/1e-5, results['Li7_H_corr'][-1]/1e-10]
        obs_vals = [0.245, 2.6, 5.0]  # 归一化
        
        x = np.arange(len(elements))
        width = 0.25
        
        axes[1, 1].bar(x - width, std_vals, width, label='Standard')
        axes[1, 1].bar(x, corr_vals, width, label='Modified')
        axes[1, 1].bar(x + width, obs_vals, width, label='Observation')
        axes[1, 1].set_ylabel('Abundance (normalized)')
        axes[1, 1].set_title('Final Abundances')
        axes[1, 1].set_xticks(x)
        axes[1, 1].set_xticklabels(elements)
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('bbn_spectral_correction.png', dpi=150, bbox_inches='tight')
        print("\n图像已保存: bbn_spectral_correction.png")

def main():
    print("="*70)
    print("6-12个月阶段: BBN精确计算")
    print("加入谱维演化效应的原初核合成计算")
    print("="*70)
    
    bbn = BBNWithSpectralDimension(tau_0=1e-5)
    
    # 计算BBN
    results = bbn.calculate_bbn()
    
    # 与观测对比
    bbn.compare_with_observation(results)
    
    # 绘图
    bbn.plot_bbn(results)
    
    print("\n" + "="*70)
    print("BBN计算完成!")
    print("注: 这是简化模型，完整计算需要修改PArthENoPE等代码")
    print("="*70)

if __name__ == "__main__":
    main()
