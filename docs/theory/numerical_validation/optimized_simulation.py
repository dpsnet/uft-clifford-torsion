#!/usr/bin/env python3
"""
优化版早期宇宙谱维演化模拟
Optimized Early Universe Spectral Dimension Evolution

改进点:
1. 更精确的初始条件设置
2. 温度依赖的谱维弛豫率
3. 辐射主导时期的正确处理
4. 物质-辐射平衡过渡
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar

# 物理常数
M_Planck = 1.22e19  # GeV
m_planck_kg = 2.18e-30  # kg

class OptimizedCosmology:
    def __init__(self, tau_0=1e-5, T_GUT=1e16):
        self.tau_0 = tau_0
        self.T_GUT = T_GUT  # GUT相变温度
        self.g_star = 106.75  # 相对论自由度 (标准模型)
        
    def spectral_dimension(self, T):
        """
        改进的谱维模型 - 在T_GUT附近平滑过渡
        """
        if T > self.T_GUT * 10:
            return 10.0
        elif T < self.T_GUT / 10:
            return 4.0
        else:
            # 平滑过渡函数
            x = np.log10(T / self.T_GUT)
            return 4.0 + 6.0 / (1.0 + np.exp(-2.0 * x))
    
    def hubble_rate(self, T, rho_int):
        """
        修正的哈勃参数
        """
        # 辐射能量密度
        rho_rad = (np.pi**2 / 30) * self.g_star * T**4
        # 总能量密度
        rho_total = rho_rad + rho_int
        
        return np.sqrt(8 * np.pi * rho_total / 3) / M_Planck
    
    def energy_flow_rate(self, T, rho_int):
        """
        从内部空间到辐射的能量流动率
        """
        d_s = self.spectral_dimension(T)
        
        if d_s <= 4.01:
            return 0.0  # 已冻结
        
        # 流动率与(d_s - 4)和温度相关
        gamma = self.tau_0**2 * (T / M_Planck)**(d_s - 4)
        
        # 能量流出内部空间
        return gamma * rho_int
    
    def equations(self, ln_t, y):
        """
        演化方程 (以对数时间为变量)
        
        y = [ln_T, ln_rho_int]
        """
        t = np.exp(ln_t)
        T = np.exp(y[0])
        rho_int = np.exp(y[1])
        
        # 当前哈勃率
        H = self.hubble_rate(T, rho_int)
        
        # 谱维
        d_s = self.spectral_dimension(T)
        
        # 能量流出内部空间
        flow = self.energy_flow_rate(T, rho_int)
        
        # d(ln T)/d(ln t) = -1 (标准辐射主导)
        # 但如果有能量注入，温度下降变慢
        d_ln_T = -1.0 + (flow / ((np.pi**2/30) * self.g_star * T**4)) / H
        
        # d(ln rho_int)/d(ln t) = -4 * (d_s - 4)/4 - flow/(H*rho_int)
        # 第一项: 内部空间"维度压缩"导致的稀释
        # 第二项: 能量流出
        dilution = -3.0 * (d_s - 4) / 4.0 if d_s > 4 else 0.0
        d_ln_rho_int = dilution - flow / (H * rho_int)
        
        return [d_ln_T, d_ln_rho_int]
    
    def run_simulation(self, t_start=1e-44, t_end=1e4, n_points=5000):
        """
        运行优化后的模拟
        """
        # 初始条件 (普朗克时期)
        T_start = M_Planck  # 初始温度 ~普朗克能标
        rho_int_start = 6.0 * (np.pi**2 / 30) * T_start**4  # 内部空间能量 (d_s=10-4=6)
        
        y0 = [np.log(T_start), np.log(rho_int_start)]
        
        # 时间范围 (对数)
        ln_t_span = (np.log(t_start), np.log(t_end))
        ln_t_eval = np.linspace(ln_t_span[0], ln_t_span[1], n_points)
        
        print(f"开始模拟...")
        print(f"初始温度: {T_start:.2e} GeV")
        print(f"初始内部空间能量密度: {rho_int_start:.2e} GeV^4")
        print(f"时间范围: {t_start:.2e} s - {t_end:.2e} s")
        
        # 求解
        solution = solve_ivp(
            self.equations,
            ln_t_span,
            y0,
            method='RK45',
            t_eval=ln_t_eval,
            rtol=1e-8,
            atol=1e-12,
            dense_output=True
        )
        
        # 提取结果
        t = np.exp(solution.t)
        T = np.exp(solution.y[0])
        rho_int = np.exp(solution.y[1])
        
        # 计算辐射能量密度
        rho_rad = (np.pi**2 / 30) * self.g_star * T**4
        
        # 计算谱维
        d_s = np.array([self.spectral_dimension(temp) for temp in T])
        
        # 哈勃率
        H = np.array([self.hubble_rate(temp, r_int) for temp, r_int in zip(T, rho_int)])
        
        # 能量流动率
        flow = np.array([self.energy_flow_rate(temp, r_int) for temp, r_int in zip(T, rho_int)])
        
        self.results = {
            't': t,
            'T': T,
            'rho_rad': rho_rad,
            'rho_int': rho_int,
            'd_s': d_s,
            'H': H,
            'flow': flow
        }
        
        return self.results
    
    def analyze_key_moments(self):
        """分析关键宇宙时刻"""
        if not hasattr(self, 'results'):
            print("请先运行模拟")
            return
            
        r = self.results
        
        # 找到关键温度对应的时间
        moments = []
        
        # GUT相变 (T ~ 10^16 GeV)
        idx_gut = np.argmin(np.abs(r['T'] - 1e16))
        moments.append(('GUT相变', r['t'][idx_gut], r['T'][idx_gut], r['d_s'][idx_gut]))
        
        # 电弱相变 (T ~ 100 GeV)
        idx_ew = np.argmin(np.abs(r['T'] - 100))
        moments.append(('电弱相变', r['t'][idx_ew], r['T'][idx_ew], r['d_s'][idx_ew]))
        
        # QCD相变 (T ~ 0.2 GeV = 200 MeV)
        idx_qcd = np.argmin(np.abs(r['T'] - 0.2))
        moments.append(('QCD相变', r['t'][idx_qcd], r['T'][idx_qcd], r['d_s'][idx_qcd]))
        
        # 核合成 (T ~ 0.001 GeV = 1 MeV)
        idx_bbn = np.argmin(np.abs(r['T'] - 1e-3))
        moments.append(('核合成', r['t'][idx_bbn], r['T'][idx_bbn], r['d_s'][idx_bbn]))
        
        # 物质-辐射平衡 (T ~ 0.8 eV)
        idx_eq = np.argmin(np.abs(r['T'] - 8e-4))
        if idx_eq < len(r['t']):
            moments.append(('物质-辐射平衡', r['t'][idx_eq], r['T'][idx_eq], r['d_s'][idx_eq]))
        
        print("\n关键宇宙时刻:")
        print("="*70)
        print(f"{'事件':<15} {'时间 (s)':<15} {'温度 (GeV)':<15} {'谱维 d_s':<10}")
        print("="*70)
        for name, t, T, d_s in moments:
            print(f"{name:<15} {t:<15.2e} {T:<15.2e} {d_s:<10.2f}")
        
        return moments
    
    def plot_results(self):
        """绘制演化结果"""
        if not hasattr(self, 'results'):
            print("请先运行模拟")
            return
            
        r = self.results
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        
        # 1. 尺度因子演化 (从温度推断)
        axes[0, 0].loglog(r['t'], r['T'], 'b-', linewidth=2)
        axes[0, 0].axhline(1e16, color='r', linestyle='--', alpha=0.5, label='GUT')
        axes[0, 0].axhline(1e2, color='g', linestyle='--', alpha=0.5, label='电弱')
        axes[0, 0].axhline(1e-3, color='m', linestyle='--', alpha=0.5, label='核合成')
        axes[0, 0].set_xlabel('时间 (s)')
        axes[0, 0].set_ylabel('温度 (GeV)')
        axes[0, 0].set_title('温度演化')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 谱维演化
        axes[0, 1].semilogx(r['t'], r['d_s'], 'g-', linewidth=2)
        axes[0, 1].axhline(4, color='r', linestyle='--', alpha=0.5, label='d_s = 4')
        axes[0, 1].axhline(10, color='b', linestyle='--', alpha=0.5, label='d_s = 10')
        axes[0, 1].set_xlabel('时间 (s)')
        axes[0, 1].set_ylabel('谱维 d_s')
        axes[0, 1].set_title('谱维从10维演化到4维')
        axes[0, 1].set_ylim([3.5, 10.5])
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 能量密度成分
        axes[0, 2].loglog(r['t'], r['rho_rad'], 'r-', linewidth=2, label='辐射')
        axes[0, 2].loglog(r['t'], r['rho_int'], 'b-', linewidth=2, label='内部空间')
        axes[0, 2].set_xlabel('时间 (s)')
        axes[0, 2].set_ylabel('能量密度 (GeV⁴)')
        axes[0, 2].set_title('能量成分演化')
        axes[0, 2].legend()
        axes[0, 2].grid(True, alpha=0.3)
        
        # 4. 能量流动率
        axes[1, 0].loglog(r['t'], np.abs(r['flow']), 'm-', linewidth=2)
        axes[1, 0].set_xlabel('时间 (s)')
        axes[1, 0].set_ylabel('|dρ/dt| (GeV⁵)')
        axes[1, 0].set_title('跨维度能量流动率')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 5. 哈勃率
        axes[1, 1].loglog(r['t'], r['H'], 'c-', linewidth=2)
        axes[1, 1].set_xlabel('时间 (s)')
        axes[1, 1].set_ylabel('哈勃率 H (GeV)')
        axes[1, 1].set_title('宇宙膨胀率')
        axes[1, 1].grid(True, alpha=0.3)
        
        # 6. 内部空间占比
        ratio = r['rho_int'] / (r['rho_int'] + r['rho_rad'])
        axes[1, 2].semilogx(r['t'], ratio, 'orange', linewidth=2)
        axes[1, 2].set_xlabel('时间 (s)')
        axes[1, 2].set_ylabel('ρ_int / ρ_total')
        axes[1, 2].set_title('内部空间能量占比')
        axes[1, 2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('optimized_early_universe.png', dpi=150, bbox_inches='tight')
        print("\n图像已保存: optimized_early_universe.png")
        
    def check_conservation(self):
        """检查能量守恒"""
        if not hasattr(self, 'results'):
            print("请先运行模拟")
            return
            
        r = self.results
        
        # 总能量密度
        rho_total = r['rho_rad'] + r['rho_int']
        
        # 检查在核合成时期的比值
        idx_bbn = np.argmin(np.abs(r['T'] - 1e-3))
        ratio_bbn = r['rho_int'][idx_bbn] / r['rho_rad'][idx_bbn]
        
        print("\n能量守恒检查:")
        print("="*50)
        print(f"初始总能量密度: {rho_total[0]:.2e} GeV⁴")
        print(f"当前总能量密度: {rho_total[-1]:.2e} GeV⁴")
        print(f"核合成时期内部/辐射比: {ratio_bbn:.2e}")
        
        if ratio_bbn < 1e-10:
            print("✓ 核合成时期内部空间能量可忽略，与观测兼容")
        else:
            print("⚠ 内部空间能量可能影响核合成，需要进一步检验")
        
        return ratio_bbn

def main():
    """主程序"""
    print("="*60)
    print("优化版早期宇宙谱维演化模拟")
    print("Optimized Spectral Dimension Evolution")
    print("="*60)
    
    # 创建模型
    model = OptimizedCosmology(tau_0=1e-5, T_GUT=1e16)
    
    # 运行模拟
    results = model.run_simulation(t_start=1e-44, t_end=1e4, n_points=2000)
    
    # 分析关键时刻
    model.analyze_key_moments()
    
    # 检查守恒
    model.check_conservation()
    
    # 绘制结果
    model.plot_results()
    
    print("\n模拟完成!")
    print("="*60)

if __name__ == "__main__":
    main()
