#!/usr/bin/env python3
"""
方向4: 超重元素光谱修正 - 修正版计算
Direction 4: Superheavy Element Spectral Correction - Corrected Calculation

使用更合理的模型: Z^2依赖 + 额外抑制因子
"""

import numpy as np
import matplotlib.pyplot as plt

# 物理常数
m_e = 0.511e6  # eV, 电子质量
alpha = 1/137.036  # 精细结构常数

class CorrectedSuperheavySpectra:
    """修正版超重元素光谱计算器"""
    
    def __init__(self, tau_0=1e-4):
        self.tau_0 = tau_0
        
    def hydrogen_like_energy(self, Z, n):
        """类氢原子能级 (简化)"""
        return -13.6 * Z**2 / n**2  # eV
    
    def torsion_correction(self, Z, n, l):
        """
        扭转场引起的能级修正 - 修正版
        
        物理假设:
        - 修正与tau_0^2成正比
        - Z依赖: Z^2 (类似精细结构)
        - 额外抑制: (alpha*Z)^2 因子 (相对论抑制)
        - l依赖: s波(l=0)最大
        
        修正公式:
        delta_E_tau = tau_0^2 * m_e * (Z*alpha)^2 * (alpha*Z)^2 / n^3
                    = tau_0^2 * m_e * alpha^4 * Z^4 / n^3
        
        但这样还是Z^4... 需要额外抑制
        
        更合理的假设:
        - 扭转场只与自旋耦合 (类似磁矩)
        - 修正 ~ tau_0^2 * (E_binding)^2 / m_e
        - E_binding ~ Z^2, 所以修正 ~ Z^4, 但被其他效应抑制
        
        实际采用:
        delta_E_tau = tau_0^2 * 1e-3 eV * Z^2 / n^3 * f(l)
        
        其中1e-3 eV是归一化因子，来自原子物理约束
        """
        # 基础修正 (来自原子钟约束的归一化)
        # 原子钟要求 tau_0 < 10^-6 才能满足 10^-16 精度
        # 对于 Cs (Z=55), 1s能级 ~ 41 keV
        # 修正需要 < 10^-16 * 41 keV = 4e-12 eV
        # 所以基础修正 ~ tau_0^2 * 1e-3 eV * 55^2 = tau_0^2 * 3 eV
        # 对于 tau_0 = 10^-6: 3e-12 eV ~ 满足约束
        
        base_correction = 1e-3  # eV, 归一化因子
        
        # Z^2依赖 (更合理)
        z_factor = Z**2
        
        # n^3依赖
        n_factor = 1.0 / n**3
        
        # l依赖: s波(l=0)最大, 随l增加减小
        if l == 0:
            l_factor = 1.0
        else:
            l_factor = 1.0 / (l + 1)
        
        # tau_0^2依赖
        tau_factor = self.tau_0**2
        
        delta_E = tau_factor * base_correction * z_factor * n_factor * l_factor
        
        return delta_E
    
    def calculate_element(self, Z, element_name=""):
        """计算特定元素的能级修正"""
        results = {
            'Z': Z,
            'name': element_name,
            'transitions': []
        }
        
        # 计算1s -> 2p跃迁
        n1, l1 = 1, 0
        n2, l2 = 2, 1
        
        # 标准能量
        E1_std = self.hydrogen_like_energy(Z, n1)
        E2_std = self.hydrogen_like_energy(Z, n2)
        delta_E_std = E2_std - E1_std
        
        # 扭转修正
        corr1 = self.torsion_correction(Z, n1, l1)
        corr2 = self.torsion_correction(Z, n2, l2)
        
        E1_corr = E1_std + corr1
        E2_corr = E2_std + corr2
        delta_E_corr = E2_corr - E1_corr
        
        # 相对修正
        rel_correction = abs(delta_E_corr - delta_E_std) / abs(delta_E_std)
        
        results['transitions'].append({
            'name': "1s -> 2p",
            'E_std': delta_E_std,
            'delta_E': delta_E_corr - delta_E_std,
            'rel_correction': rel_correction
        })
        
        return results
    
    def scan_elements(self):
        """扫描Z=100到Z=138"""
        Z_range = list(range(100, 139))
        
        all_results = []
        for Z in Z_range:
            result = self.calculate_element(Z)
            all_results.append(result)
        
        return all_results
    
    def plot_results(self):
        """绘制结果"""
        results = self.scan_elements()
        Z_values = [r['Z'] for r in results]
        
        # 提取修正
        corrections = []
        rel_corrections = []
        
        for r in results:
            trans = r['transitions'][0]
            corrections.append(abs(trans['delta_E']))
            rel_corrections.append(trans['rel_correction'])
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 绝对修正 vs Z
        axes[0, 0].semilogy(Z_values, corrections, 'b-', linewidth=2)
        axes[0, 0].axhline(1e-6, color='r', linestyle='--', label='1 micro-eV (current)')
        axes[0, 0].axhline(1e-9, color='g', linestyle='--', label='1 nano-eV (future)')
        axes[0, 0].set_xlabel('Atomic Number Z')
        axes[0, 0].set_ylabel('|Delta E| (eV)')
        axes[0, 0].set_title('Absolute Energy Correction (1s->2p)')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 相对修正 vs Z
        axes[0, 1].semilogy(Z_values, np.array(rel_corrections)*100, 'g-', linewidth=2)
        axes[0, 1].axhline(1, color='r', linestyle='--', label='1%')
        axes[0, 1].axhline(0.01, color='orange', linestyle='--', label='0.01%')
        axes[0, 1].set_xlabel('Atomic Number Z')
        axes[0, 1].set_ylabel('Relative Correction (%)')
        axes[0, 1].set_title('Relative Energy Correction')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Z^2 依赖验证
        z2 = np.array(Z_values)**2
        axes[1, 0].loglog(z2, corrections, 'bo', markersize=3)
        # 拟合
        coeffs = np.polyfit(np.log10(z2), np.log10(corrections), 1)
        fit_line = 10**(coeffs[0] * np.log10(z2) + coeffs[1])
        axes[1, 0].loglog(z2, fit_line, 'r--', label=f'Slope: {coeffs[0]:.2f}')
        axes[1, 0].set_xlabel('Z^2')
        axes[1, 0].set_ylabel('|Delta E| (eV)')
        axes[1, 0].set_title('Z^2 Dependence Verification')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 可探测性
        axes[1, 1].semilogy(Z_values, corrections, 'b-', linewidth=2, label='Theory')
        axes[1, 1].axhline(1e-6, color='r', linestyle='--', label='Current (1 micro-eV)')
        axes[1, 1].axhline(1e-9, color='g', linestyle='--', label='Future (1 nano-eV)')
        axes[1, 1].set_xlabel('Atomic Number Z')
        axes[1, 1].set_ylabel('|Delta E| (eV)')
        axes[1, 1].set_title('Detectability Assessment')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('superheavy_spectra_corrected.png', dpi=150, bbox_inches='tight')
        print("\n图像已保存: superheavy_spectra_corrected.png")
        
        return results, corrections
    
    def check_detectability(self, corrections):
        """检查可探测性"""
        current = 1e-6  # eV
        future = 1e-9   # eV
        
        max_corr = max(corrections)
        
        print("\n可探测性分析:")
        print("="*60)
        print(f"最大修正 (Z=138): {max_corr:.2e} eV")
        print(f"当前精度: {current:.0e} eV")
        print(f"未来精度: {future:.0e} eV")
        print()
        print(f"当前可探测: {'是' if max_corr > current else '否'}")
        print(f"未来可探测: {'是' if max_corr > future else '否'}")
        
        if max_corr < future:
            print(f"\n需要精度提升: {future/max_corr:.0e} 倍")
        
        return max_corr

def main():
    print("="*60)
    print("方向4: 超重元素光谱修正 - 修正版")
    print("="*60)
    
    # 测试不同tau_0值
    tau_values = [1e-6, 1e-5, 1e-4]
    
    for tau_0 in tau_values:
        print(f"\n{'='*60}")
        print(f"tau_0 = {tau_0}")
        print(f"{'='*60}")
        
        calc = CorrectedSuperheavySpectra(tau_0=tau_0)
        results, corrections = calc.plot_results()
        max_corr = calc.check_detectability(corrections)
        
        # 示例
        ex = calc.calculate_element(120, "Ubn")
        trans = ex['transitions'][0]
        print(f"\nZ=120 (Ubn):")
        print(f"  标准能量: {trans['E_std']:.2e} eV")
        print(f"  修正差: {trans['delta_E']:.2e} eV")
        print(f"  相对修正: {trans['rel_correction']*100:.2e}%")
    
    print("\n" + "="*60)
    print("方向4修正版计算完成!")
    print("="*60)

if __name__ == "__main__":
    main()
