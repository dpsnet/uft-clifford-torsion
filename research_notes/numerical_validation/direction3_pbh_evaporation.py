#!/usr/bin/env python3
"""
方向3: 原初黑洞蒸发修正
Direction 3: Primordial Black Hole Evaporation

计算小质量原初黑洞的蒸发修正，寻找可探测信号
"""

import numpy as np
import matplotlib.pyplot as plt

# 物理常数
M_Planck = 1.22e19  # GeV
m_planck_kg = 2.18e-8  # kg
G = 6.674e-11  # m^3 kg^-1 s^-2
hbar = 1.055e-34  # J·s
c = 3e8  # m/s

class PBHEvaporation:
    """原初黑洞蒸发计算器"""
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        
    def hawking_temperature(self, M):
        """霍金温度 (K)"""
        return hbar * c**3 / (8 * np.pi * G * M * 1.38e-23)
    
    def standard_evaporation_rate(self, M):
        """标准蒸发率 (kg/s)"""
        # dM/dt = -C * M^-2
        # C ~ 10^-16 kg^3/s (取决于粒子种类)
        C = 1e-16
        return C * M**(-2)
    
    def internal_space_flow(self, M):
        """
        内部空间能量流动导致的额外质量损失
        
        机制: 黑洞视界附近，部分能量流入内部空间
        """
        # 流动强度 ~ tau_0^2 * (M_Planck/M)^3
        alpha_tau = 1e-3  # 归一化因子
        
        M_planck_kg = m_planck_kg
        flow_rate = alpha_tau * self.tau_0**2 * (M_planck_kg / M)**3
        
        return flow_rate
    
    def calculate_lifetime(self, M_initial):
        """
        计算黑洞从M_initial蒸发到普朗克质量的寿命
        
        返回: 标准寿命, 修正寿命, 寿命变化比例
        """
        # 标准寿命 (简化公式)
        # t ~ M^3 / (3*C)
        C = 1e-16
        t_std = M_initial**3 / (3 * C)
        
        # 修正寿命 (数值积分简化)
        # 由于内部空间流动，蒸发更快
        # 近似: t_corrected ~ t_std / (1 + alpha)
        
        alpha = self.tau_0**2 * (m_planck_kg / M_initial) * 1e3
        
        if alpha > 0.1:
            # 显著修正
            t_corr = t_std / (1 + alpha)
        else:
            t_corr = t_std * (1 - alpha/3)  # 一阶近似
        
        delta_t = (t_std - t_corr) / t_std
        
        return t_std, t_corr, delta_t
    
    def gamma_ray_flux(self, M, distance=1e20):
        """
        计算伽马射线通量 (简化模型)
        
        参数:
            M: 黑洞质量 (kg)
            distance: 距离 (m), 默认约3kpc
        """
        # 霍金温度
        T_H = self.hawking_temperature(M)
        
        # 标准霍金辐射通量 (简化)
        # 假设主要辐射光子
        flux_std = 1e-10 * (1e9 / M)**2 / (distance / 1e20)**2  # 任意单位
        
        # 修正通量 (内部空间流动改变辐射谱)
        # 产生额外的"扭率子"辐射
        correction = 1 + self.tau_0**2 * (m_planck_kg / M)
        flux_corr = flux_std * correction
        
        return flux_std, flux_corr
    
    def scan_mass_range(self):
        """扫描原初黑洞质量范围"""
        # 质量范围: 10^6 kg 到 10^12 kg
        M_range = np.logspace(6, 12, 100)
        
        results = {
            'M': M_range,
            'T_H': [],
            't_std': [],
            't_corr': [],
            'delta_t': [],
            'flux_std': [],
            'flux_corr': []
        }
        
        for M in M_range:
            # 霍金温度
            T_H = self.hawking_temperature(M)
            results['T_H'].append(T_H)
            
            # 寿命
            t_s, t_c, dt = self.calculate_lifetime(M)
            results['t_std'].append(t_s)
            results['t_corr'].append(t_c)
            results['delta_t'].append(dt)
            
            # 伽马射线通量
            f_s, f_c = self.gamma_ray_flux(M)
            results['flux_std'].append(f_s)
            results['flux_corr'].append(f_c)
        
        return results
    
    def plot_results(self):
        """绘制结果"""
        results = self.scan_mass_range()
        M = results['M']
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 霍金温度
        axes[0, 0].loglog(M, results['T_H'], 'b-', linewidth=2)
        axes[0, 0].axhline(1e9, color='r', linestyle='--', label='1 GeV')
        axes[0, 0].axhline(1e12, color='orange', linestyle='--', label='1 TeV')
        axes[0, 0].set_xlabel('Mass (kg)')
        axes[0, 0].set_ylabel('Hawking Temperature (K)')
        axes[0, 0].set_title('Hawking Temperature vs Mass')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 蒸发寿命
        axes[0, 1].loglog(M, results['t_std'], 'b-', linewidth=2, label='Standard')
        axes[0, 1].loglog(M, results['t_corr'], 'r--', linewidth=2, label='Modified')
        axes[0, 1].set_xlabel('Mass (kg)')
        axes[0, 1].set_ylabel('Lifetime (s)')
        axes[0, 1].set_title('Evaporation Lifetime')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 寿命变化比例
        delta_t = np.array(results['delta_t'])
        axes[1, 0].semilogx(M, delta_t * 100, 'g-', linewidth=2)
        axes[1, 0].axhline(10, color='r', linestyle='--', label='10% change')
        axes[1, 0].axhline(50, color='orange', linestyle='--', label='50% change')
        axes[1, 0].set_xlabel('Mass (kg)')
        axes[1, 0].set_ylabel('Lifetime Change (%)')
        axes[1, 0].set_title('Lifetime Modification')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 伽马射线通量
        axes[1, 1].loglog(M, results['flux_std'], 'b-', linewidth=2, label='Standard')
        axes[1, 1].loglog(M, results['flux_corr'], 'r--', linewidth=2, label='Modified')
        axes[1, 1].set_xlabel('Mass (kg)')
        axes[1, 1].set_ylabel('Gamma-ray Flux (arb. units)')
        axes[1, 1].set_title('Gamma-ray Flux')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('pbh_evaporation.png', dpi=150, bbox_inches='tight')
        print("\n图像已保存: pbh_evaporation.png")
        
        return results
    
    def find_detectable_masses(self, results):
        """找到可能有可探测信号的质量范围"""
        M = results['M']
        delta_t = np.array(results['delta_t'])
        
        # 寿命变化 > 10%
        idx_10 = np.where(delta_t > 0.1)[0]
        if len(idx_10) > 0:
            M_10_min = M[idx_10[0]]
            M_10_max = M[idx_10[-1]]
        else:
            M_10_min = M_10_max = None
        
        # 寿命变化 > 50%
        idx_50 = np.where(delta_t > 0.5)[0]
        if len(idx_50) > 0:
            M_50_min = M[idx_50[0]]
            M_50_max = M[idx_50[-1]]
        else:
            M_50_min = M_50_max = None
        
        print("\n可探测质量范围 (寿命变化):")
        print("="*60)
        if M_10_min:
            print(f"  > 10% 变化: {M_10_min:.2e} kg - {M_10_max:.2e} kg")
        else:
            print(f"  > 10% 变化: 无")
        
        if M_50_min:
            print(f"  > 50% 变化: {M_50_min:.2e} kg - {M_50_max:.2e} kg")
        else:
            print(f"  > 50% 变化: 无")
        
        return M_10_min, M_50_min

def main():
    print("="*60)
    print("方向3: 原初黑洞蒸发修正")
    print("="*60)
    
    # 使用保守参数
    tau_0 = 1e-5
    print(f"\n参数: tau_0 = {tau_0}")
    
    pbh = PBHEvaporation(tau_0=tau_0)
    
    # 计算并绘图
    results = pbh.plot_results()
    
    # 找到可探测质量
    pbh.find_detectable_masses(results)
    
    # 示例计算
    print("\n示例黑洞:")
    print("-"*60)
    M_example = 1e9  # kg
    t_s, t_c, dt = pbh.calculate_lifetime(M_example)
    T_H = pbh.hawking_temperature(M_example)
    
    print(f"质量: {M_example:.2e} kg")
    print(f"霍金温度: {T_H:.2e} K ({T_H/1.16e13:.2e} GeV)")
    print(f"标准寿命: {t_s:.2e} s ({t_s/3.15e7:.2e} 年)")
    print(f"修正寿命: {t_c:.2e} s ({t_c/3.15e7:.2e} 年)")
    print(f"寿命变化: {dt*100:.2f}%")
    
    print("\n" + "="*60)
    print("方向3计算完成!")
    print("="*60)

if __name__ == "__main__":
    main()
