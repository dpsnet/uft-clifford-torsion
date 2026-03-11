#!/usr/bin/env python3
"""
修正版早期宇宙谱维演化模拟
Corrected Early Universe Spectral Dimension Evolution

关键修正:
1. 正确的能量守恒方程
2. 内部空间能量持续流入辐射
3. 总能量密度守恒 (在共动体积中)
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# 物理常数
M_Planck = 1.22e19  # GeV

class CorrectedCosmology:
    def __init__(self, tau_0=1e-5, T_GUT=1e16):
        self.tau_0 = tau_0
        self.T_GUT = T_GUT
        self.g_star = 106.75  # 标准模型相对论自由度
        
    def spectral_dimension(self, T):
        """谱维随温度变化"""
        if T > self.T_GUT * 10:
            return 10.0
        elif T < self.T_GUT / 10:
            return 4.0
        else:
            x = np.log10(T / self.T_GUT)
            return 4.0 + 6.0 / (1.0 + np.exp(-2.0 * x))
    
    def equations(self, ln_a, y):
        """
        演化方程 (以ln(a)为自变量)
        
        y = [ln(T), f_int]
        其中 f_int = rho_int / (rho_rad + rho_int) 是内部空间能量占比
        """
        T = np.exp(y[0])
        f_int = y[1]
        
        # 确保f_int在[0,1]范围内
        f_int = np.clip(f_int, 0.0, 1.0)
        
        # 谱维
        d_s = self.spectral_dimension(T)
        
        # 当前辐射能量密度 (从温度推导)
        rho_rad = (np.pi**2 / 30) * self.g_star * T**4
        
        # 总能量密度
        rho_total = rho_rad / (1 - f_int) if f_int < 0.999 else rho_rad * 1000
        
        # 内部空间能量密度
        rho_int = f_int * rho_total
        
        # 哈勃率
        H = np.sqrt(8 * np.pi * rho_total / 3) / M_Planck
        
        # === 关键修正: 能量流动 ===
        # 内部空间能量转化为辐射的速率
        if d_s > 4.01 and f_int > 1e-30:
            # 流动率与 (d_s - 4) 和当前内部空间能量成正比
            Gamma = self.tau_0**2 * H * (d_s - 4) / 6.0  # 归一化到6维差
            flow_rate = Gamma * rho_int
        else:
            flow_rate = 0.0
        
        # === 辐射能量密度演化 ===
        # 标准: d(ln rho_rad)/d(ln a) = -4 (膨胀稀释)
        # 修正: + (flow_rate / rho_rad) / H (能量注入)
        d_ln_rho_rad = -4.0 + flow_rate / (H * rho_rad) if rho_rad > 0 else 0.0
        
        # === 温度演化 ===
        # 从 rho_rad ~ T^4 得到 d(ln T)/d(ln a) = (1/4) * d(ln rho_rad)/d(ln a)
        d_ln_T = d_ln_rho_rad / 4.0
        
        # === 内部空间能量占比演化 ===
        # df_int/d(ln a) = (1/rho_total) * (drho_int/d(ln a) - f_int * drho_total/d(ln a))
        # drho_int/d(ln a) = -flow_rate/H - 3*rho_int (维度压缩稀释)
        # drho_total/d(ln a) = -3*(rho_total + p_total) = -4*rho_rad - 3*rho_int (近似)
        
        dimension_dilution = -3.0 * (d_s - 4) / 4.0 if d_s > 4 else 0.0
        d_ln_rho_int = dimension_dilution - flow_rate / (H * rho_int) if rho_int > 1e-100 else 0.0
        
        # 总能量密度演化 (近似为辐射+内部空间)
        # p_total = (1/3)*rho_rad + p_int
        # 假设内部空间状态方程 w_int ≈ 0 (类似物质)
        d_ln_rho_total = (f_int * d_ln_rho_int + (1-f_int) * d_ln_rho_rad) if f_int < 0.999 else d_ln_rho_rad
        
        # df_int/d(ln a)
        if f_int > 1e-10 and f_int < 0.999:
            df_int = f_int * (d_ln_rho_int - d_ln_rho_total)
        else:
            df_int = 0.0
        
        return [d_ln_T, df_int]
    
    def run_simulation(self, a_start=1e-30, a_end=1e12, n_points=3000):
        """运行修正后的模拟"""
        
        # 初始条件
        # 普朗克时期: T ~ M_Planck, f_int ~ 0.86 (6/7, 因为d_s=10, 辐射等效4维)
        T_start = M_Planck
        f_int_start = 6.0 / 7.0  # 内部空间能量占总能量的大部分
        
        y0 = [np.log(T_start), f_int_start]
        
        ln_a_span = (np.log(a_start), np.log(a_end))
        ln_a_eval = np.linspace(ln_a_span[0], ln_a_span[1], n_points)
        
        print("开始修正版模拟...")
        print(f"初始温度: {T_start:.2e} GeV")
        print(f"初始内部空间占比: {f_int_start:.4f}")
        print(f"尺度因子范围: {a_start:.2e} - {a_end:.2e}")
        
        # 求解
        solution = solve_ivp(
            self.equations,
            ln_a_span,
            y0,
            method='RK45',
            t_eval=ln_a_eval,
            rtol=1e-10,
            atol=1e-15,
            dense_output=True
        )
        
        # 提取结果
        a = np.exp(solution.t)
        T = np.exp(solution.y[0])
        f_int = np.clip(solution.y[1], 0.0, 1.0)
        
        # 计算能量密度
        rho_rad = (np.pi**2 / 30) * self.g_star * T**4
        # 从 f_int = rho_int / (rho_rad + rho_int) 反推 rho_int
        rho_int = f_int * rho_rad / (1 - f_int + 1e-100)
        
        # 谱维
        d_s = np.array([self.spectral_dimension(temp) for temp in T])
        
        # 计算时间 (从 da/dt = H*a = a' 得到 dt = da/(H*a))
        # 简化为: t ~ 1/(2H) 对于辐射主导
        H = np.sqrt(8 * np.pi * (rho_rad + rho_int) / 3) / M_Planck
        t = 1.0 / (2.0 * H)  # 辐射主导宇宙近似
        
        self.results = {
            'a': a,
            't': t,
            'T': T,
            'rho_rad': rho_rad,
            'rho_int': rho_int,
            'f_int': f_int,
            'd_s': d_s,
            'H': H
        }
        
        return self.results
    
    def analyze_key_moments(self):
        """分析关键时刻"""
        if not hasattr(self, 'results'):
            print("请先运行模拟")
            return
            
        r = self.results
        
        moments = []
        
        # 找到关键温度对应的时间
        targets = [
            ('GUT相变', 1e16),
            ('电弱相变', 100),
            ('QCD相变', 0.2),
            ('核合成', 1e-3),
            ('物质-辐射平衡', 8e-4)
        ]
        
        for name, T_target in targets:
            idx = np.argmin(np.abs(r['T'] - T_target))
            if idx < len(r['t']):
                moments.append((name, r['t'][idx], r['T'][idx], r['d_s'][idx], r['f_int'][idx]))
        
        print("\n关键宇宙时刻:")
        print("="*80)
        print(f"{'事件':<12} {'时间(s)':<12} {'温度(GeV)':<12} {'d_s':<8} {'f_int':<12}")
        print("="*80)
        for name, t, T, d_s, f_int in moments:
            print(f"{name:<12} {t:<12.2e} {T:<12.2e} {d_s:<8.2f} {f_int:<12.2e}")
        
        return moments
    
    def check_nucleosynthesis(self):
        """检查核合成时期的能量占比"""
        if not hasattr(self, 'results'):
            print("请先运行模拟")
            return
            
        r = self.results
        
        # 核合成时期 T ~ 1 MeV = 1e-3 GeV
        idx_bbn = np.argmin(np.abs(r['T'] - 1e-3))
        
        f_int_bbn = r['f_int'][idx_bbn]
        ratio = r['rho_int'][idx_bbn] / r['rho_rad'][idx_bbn]
        
        print("\n核合成时期检查:")
        print("="*50)
        print(f"温度: {r['T'][idx_bbn]:.2e} GeV")
        print(f"内部空间能量占比: {f_int_bbn:.2e}")
        print(f"内部/辐射能量比: {ratio:.2e}")
        
        if f_int_bbn < 1e-10:
            print("✓ 内部空间能量可忽略，与观测兼容")
            status = "PASS"
        elif f_int_bbn < 1e-5:
            print("⚠ 内部空间能量较小，可能影响不大")
            status = "MARGINAL"
        else:
            print("✗ 内部空间能量过高，与观测冲突")
            status = "FAIL"
        
        return {
            'f_int': f_int_bbn,
            'ratio': ratio,
            'status': status,
            'T_bbn': r['T'][idx_bbn],
            't_bbn': r['t'][idx_bbn]
        }
    
    def plot_results(self):
        """绘制结果"""
        if not hasattr(self, 'results'):
            print("请先运行模拟")
            return
            
        r = self.results
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        
        # 1. 温度演化
        axes[0, 0].loglog(r['t'], r['T'], 'b-', linewidth=2)
        axes[0, 0].axhline(1e16, color='r', linestyle='--', alpha=0.5)
        axes[0, 0].axhline(1e2, color='g', linestyle='--', alpha=0.5)
        axes[0, 0].axhline(1e-3, color='m', linestyle='--', alpha=0.5)
        axes[0, 0].set_xlabel('Time (s)')
        axes[0, 0].set_ylabel('T (GeV)')
        axes[0, 0].set_title('Temperature Evolution')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 谱维演化
        axes[0, 1].semilogx(r['t'], r['d_s'], 'g-', linewidth=2)
        axes[0, 1].axhline(4, color='r', linestyle='--', alpha=0.5)
        axes[0, 1].axhline(10, color='b', linestyle='--', alpha=0.5)
        axes[0, 1].set_xlabel('Time (s)')
        axes[0, 1].set_ylabel('d_s')
        axes[0, 1].set_title('Spectral Dimension: 10 → 4')
        axes[0, 1].set_ylim([3.5, 10.5])
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 能量密度
        axes[0, 2].loglog(r['t'], r['rho_rad'], 'r-', linewidth=2, label='Radiation')
        axes[0, 2].loglog(r['t'], r['rho_int'], 'b-', linewidth=2, label='Internal Space')
        axes[0, 2].set_xlabel('Time (s)')
        axes[0, 2].set_ylabel('Energy Density (GeV^4)')
        axes[0, 2].set_title('Energy Components')
        axes[0, 2].legend()
        axes[0, 2].grid(True, alpha=0.3)
        
        # 4. 内部空间占比
        axes[1, 0].semilogx(r['t'], r['f_int'], 'm-', linewidth=2)
        axes[1, 0].set_xlabel('Time (s)')
        axes[1, 0].set_ylabel('f_int = rho_int / rho_total')
        axes[1, 0].set_title('Internal Space Fraction')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 5. 哈勃率
        axes[1, 1].loglog(r['t'], r['H'], 'c-', linewidth=2)
        axes[1, 1].set_xlabel('Time (s)')
        axes[1, 1].set_ylabel('H (GeV)')
        axes[1, 1].set_title('Hubble Rate')
        axes[1, 1].grid(True, alpha=0.3)
        
        # 6. 能量密度比
        ratio = r['rho_int'] / (r['rho_rad'] + 1e-100)
        axes[1, 2].loglog(r['t'], ratio, 'orange', linewidth=2)
        axes[1, 2].set_xlabel('Time (s)')
        axes[1, 2].set_ylabel('rho_int / rho_rad')
        axes[1, 2].set_title('Internal/Radiation Ratio')
        axes[1, 2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('corrected_early_universe.png', dpi=150, bbox_inches='tight')
        print("\n图像已保存: corrected_early_universe.png")

def main():
    print("="*60)
    print("修正版早期宇宙谱维演化模拟")
    print("Corrected Spectral Dimension Evolution")
    print("="*60)
    
    model = CorrectedCosmology(tau_0=1e-5, T_GUT=1e16)
    
    results = model.run_simulation(a_start=1e-30, a_end=1e12, n_points=3000)
    
    model.analyze_key_moments()
    
    bbn_check = model.check_nucleosynthesis()
    
    model.plot_results()
    
    print("\n模拟完成!")
    print("="*60)
    
    if bbn_check['status'] == "PASS":
        print("✓ 核合成检验通过")
    else:
        print(f"✗ 核合成检验未通过: {bbn_check['status']}")

if __name__ == "__main__":
    main()
