#!/usr/bin/env python3
"""
方向4: 超重元素光谱修正 - 详细计算
Direction 4: Superheavy Element Spectral Correction - Detailed Calculation

计算超重元素(Z>100)的原子能级修正
"""

import numpy as np
import matplotlib.pyplot as plt

# 物理常数
m_e = 0.511e6  # eV, 电子质量
alpha = 1/137.036  # 精细结构常数
hbar = 6.582e-16  # eV·s

class SuperheavySpectra:
    """超重元素光谱计算器"""
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        
    def hydrogen_like_energy(self, Z, n, j):
        """
        类氢原子能级 (Dirac方程解)
        
        E_nj = m_e * c^2 * [1 + (Z*alpha)^2 / (n - delta_j)^2]^(-1/2)
        
        其中delta_j是量子数依赖的修正
        """
        # 主量子数n, 总角动量j
        # 简化: 使用非相对论近似 + 精细结构修正
        
        # 非相对论能级 (Rydberg)
        E_nonrel = -13.6 * Z**2 / n**2  # eV
        
        # 精细结构修正 (相对论效应)
        # delta_E_fs = E_nonrel * (Z*alpha)^2 / n * (1/(j+1/2) - 3/4/n)
        if j > 0:
            delta_E_fs = E_nonrel * (Z*alpha)**2 / n * (1/(j+0.5) - 0.75/n)
        else:
            delta_E_fs = 0
        
        return E_nonrel + delta_E_fs
    
    def torsion_correction(self, Z, n, l):
        """
        扭转场引起的能级修正
        
        机制: 扭转场与电子自旋-轨道耦合
        
        修正大小:
        delta_E_tau ~ tau_0^2 * (Z*alpha)^4 * m_e * (l/Z)^2
        
        参考: 统一场理论原子物理文档
        """
        # 简化模型: 修正与Z^4成正比，与tau_0^2成正比
        # 这是从扭转场与电磁场的耦合推导的
        
        g_tau = 1.0  # 耦合常数
        
        # 基本修正幅度
        base_correction = g_tau * self.tau_0**2 * m_e  # eV
        
        # Z依赖: 对于s波(l=0)，修正最大; 对于高l，修正减小
        if l == 0:
            z_factor = Z**4
        else:
            z_factor = Z**4 * (l/Z)**2
        
        # 主量子数依赖
        n_factor = 1.0 / n**3
        
        delta_E = base_correction * z_factor * n_factor
        
        return delta_E
    
    def calculate_element(self, Z, element_name=""):
        """
        计算特定元素(Z)的能级和修正
        
        返回: 标准能级, 修正能级, 相对修正
        """
        results = {
            'Z': Z,
            'name': element_name,
            'transitions': []
        }
        
        # 计算几个关键跃迁
        # 1s -> 2p (Lyman-alpha)
        # 2s -> 2p (精细结构)
        # 2p -> 3d (Balmer)
        
        transitions = [
            (1, 0, 0.5, 2, 1, 0.5, "1s -> 2p"),  # l=0, j=1/2 -> l=1, j=1/2
            (2, 0, 0.5, 2, 1, 1.5, "2s -> 2p"),  # l=0, j=1/2 -> l=1, j=3/2
            (2, 1, 0.5, 3, 2, 1.5, "2p -> 3d"),  # l=1, j=1/2 -> l=2, j=3/2
        ]
        
        for n1, l1, j1, n2, l2, j2, name in transitions:
            # 标准能级
            E1_std = self.hydrogen_like_energy(Z, n1, j1)
            E2_std = self.hydrogen_like_energy(Z, n2, j2)
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
                'name': name,
                'E_std': delta_E_std,
                'E_corr': delta_E_corr,
                'delta_E': delta_E_corr - delta_E_std,
                'rel_correction': rel_correction
            })
        
        return results
    
    def scan_elements(self):
        """扫描Z=100到Z=138的超重元素"""
        # 元素符号 (部分)
        elements = {
            100: "Fm", 101: "Md", 102: "No", 103: "Lr",
            104: "Rf", 105: "Db", 106: "Sg", 107: "Bh",
            108: "Hs", 109: "Mt", 110: "Ds", 111: "Rg",
            112: "Cn", 113: "Nh", 114: "Fl", 115: "Mc",
            116: "Lv", 117: "Ts", 118: "Og",
            119: "Uue", 120: "Ubn", 121: "Ubu", 138: "Uto"
        }
        
        Z_range = list(range(100, 139))
        
        all_results = []
        for Z in Z_range:
            name = elements.get(Z, f"Z={Z}")
            result = self.calculate_element(Z, name)
            all_results.append(result)
        
        return all_results
    
    def plot_results(self):
        """绘制结果"""
        results = self.scan_elements()
        
        Z_values = [r['Z'] for r in results]
        
        # 提取1s->2p跃迁的修正
        corrections_1s2p = []
        rel_corrections = []
        
        for r in results:
            for trans in r['transitions']:
                if trans['name'] == "1s -> 2p":
                    corrections_1s2p.append(abs(trans['delta_E']))
                    rel_corrections.append(trans['rel_correction'])
                    break
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 绝对修正 vs Z
        axes[0, 0].semilogy(Z_values, corrections_1s2p, 'b-', linewidth=2)
        axes[0, 0].axhline(1e-6, color='r', linestyle='--', label='1 micro-eV')
        axes[0, 0].axhline(1e-3, color='orange', linestyle='--', label='1 milli-eV')
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
        
        # 3. Z^4 依赖验证
        z4 = np.array(Z_values)**4
        axes[1, 0].loglog(z4, corrections_1s2p, 'bo', markersize=3)
        # 拟合直线
        coeffs = np.polyfit(np.log10(z4), np.log10(corrections_1s2p), 1)
        fit_line = 10**(coeffs[0] * np.log10(z4) + coeffs[1])
        axes[1, 0].loglog(z4, fit_line, 'r--', label=f'Slope: {coeffs[0]:.2f}')
        axes[1, 0].set_xlabel('Z^4')
        axes[1, 0].set_ylabel('|Delta E| (eV)')
        axes[1, 0].set_title('Z^4 Dependence Verification')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 当前光谱精度对比
        # 现代光谱精度 ~ 10^-6 eV (对于高Z元素)
        axes[1, 1].semilogy(Z_values, corrections_1s2p, 'b-', linewidth=2, label='Theory prediction')
        axes[1, 1].axhline(1e-6, color='r', linestyle='--', label='Current precision (1 micro-eV)')
        axes[1, 1].axhline(1e-9, color='g', linestyle='--', label='Future precision (1 nano-eV)')
        axes[1, 1].set_xlabel('Atomic Number Z')
        axes[1, 1].set_ylabel('|Delta E| (eV)')
        axes[1, 1].set_title('Detectability Assessment')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('superheavy_spectra.png', dpi=150, bbox_inches='tight')
        print("\n图像已保存: superheavy_spectra.png")
        
        return results, corrections_1s2p
    
    def check_detectability(self, corrections):
        """检查可探测性"""
        current_precision = 1e-6  # eV
        future_precision = 1e-9   # eV
        
        detectable_current = any(c > current_precision for c in corrections)
        detectable_future = any(c > future_precision for c in corrections)
        
        print("\n可探测性分析:")
        print("="*60)
        print(f"当前光谱精度: {current_precision:.0e} eV")
        print(f"未来光谱精度: {future_precision:.0e} eV")
        print(f"最大修正 (Z=138): {max(corrections):.2e} eV")
        print()
        print(f"当前可探测: {'是' if detectable_current else '否'}")
        print(f"未来可探测: {'是' if detectable_future else '否'}")
        
        if not detectable_future:
            needed_improvement = min(corrections) / future_precision
            print(f"需要精度提升: {needed_improvement:.0e} 倍")
        
        return detectable_current, detectable_future

def main():
    print("="*60)
    print("方向4: 超重元素光谱修正 - 详细计算")
    print("="*60)
    
    # 使用当前参数
    tau_0 = 1e-5
    print(f"\n参数: tau_0 = {tau_0}")
    
    calc = SuperheavySpectra(tau_0=tau_0)
    
    # 计算并绘图
    results, corrections = calc.plot_results()
    
    # 可探测性
    det_curr, det_fut = calc.check_detectability(corrections)
    
    # 示例计算
    print("\n示例元素 (Z=120):")
    print("-"*60)
    ex = calc.calculate_element(120, "Ubn")
    for trans in ex['transitions']:
        print(f"跃迁: {trans['name']}")
        print(f"  标准能量: {trans['E_std']:.2e} eV")
        print(f"  修正能量: {trans['E_corr']:.2e} eV")
        print(f"  修正差: {trans['delta_E']:.2e} eV")
        print(f"  相对修正: {trans['rel_correction']*100:.2e}%")
        print()
    
    print("="*60)
    print("方向4计算完成!")
    print("="*60)

if __name__ == "__main__":
    main()
