#!/usr/bin/env python3
"""
统一场理论综合探测前景分析仪表板
Unified Field Theory Detection Prospects Dashboard

整合所有探测渠道的分析结果:
1. LISA (引力波6偏振)
2. PTA (脉冲星计时阵)
3. CMB (谱畸变)
4. 原子钟 (频移约束)
5. BBN (元素丰度)
6. 宇宙学常数演化

生成综合对比图和最佳探测策略建议
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.collections import PatchCollection
import warnings
warnings.filterwarnings('ignore')

# 物理常数
class Constants:
    year = 365.25 * 24 * 3600
    Mpc = 3.08567758e22  # m
    Gpc = 3.08567758e25  # m

const = Constants()

class DetectionChannel:
    """单个探测渠道的数据结构"""
    
    def __init__(self, name, experiment, status, snr_or_significance, 
                 tau_sensitivity, time_horizon, description):
        self.name = name
        self.experiment = experiment
        self.status = status  # 'detectable', 'constraining', 'not_detectable'
        self.snr = snr_or_significance
        self.tau_sensitivity = tau_sensitivity  # 能探测到的最小tau_0
        self.time_horizon = time_horizon  # 年份
        self.description = description

class UFT_Detection_Prospects:
    """统一场理论探测前景综合分析"""
    
    def __init__(self, tau_0=1e-5):
        self.tau_0 = tau_0
        self.setup_channels()
    
    def setup_channels(self):
        """设置所有探测渠道"""
        
        self.channels = [
            # 引力波探测器
            DetectionChannel(
                'LISA (6-pol)',
                'LISA (ESA/NASA)',
                'detectable',
                70,  # SNR
                1e-6,  # 可探测到tau_0 ~ 10^-6
                2034,
                '6种偏振模式，最明确的检验信号'
            ),
            DetectionChannel(
                'Cosmic Explorer',
                'Cosmic Explorer (地面)',
                'detectable',
                150,  # 预计SNR
                5e-7,
                2035,
                '高频引力波，6偏振检验'
            ),
            DetectionChannel(
                'Einstein Telescope',
                'ET (欧洲)',
                'detectable',
                100,
                7e-7,
                2035,
                '三角构型，偏振敏感'
            ),
            
            # PTA
            DetectionChannel(
                'NANOGrav',
                'NANOGrav (北美)',
                'not_detectable',
                0.01,  # UFT修正/背景
                1e-3,  # 需要tau_0 > 10^-3才能探测修正
                2024,  # 当前运行中
                '天体物理背景主导，UFT修正不可分辨'
            ),
            DetectionChannel(
                'IPTA',
                '国际脉冲星计时阵',
                'not_detectable',
                0.005,
                2e-3,
                2030,
                '联合分析，背景修正仍不可探测'
            ),
            
            # CMB
            DetectionChannel(
                'CMB-S4',
                'CMB Stage-4',
                'not_detectable',
                0.001,
                3e-4,
                2030,
                '原初引力波，tau_0=10^-5效应太弱'
            ),
            DetectionChannel(
                'PIXIE',
                'PIXIE (谱畸变)',
                'not_detectable',
                0.0001,
                1e-4,
                2035,
                'mu-畸变，需要tau_0 > 10^-4'
            ),
            
            # 原子物理
            DetectionChannel(
                'Optical Clocks',
                '光晶格原子钟',
                'constraining',
                -1,  # 不是SNR，是约束
                1e-6,  # 当前最优约束 tau_0 < 10^-6
                2024,
                '最严格的tau_0上限约束'
            ),
            DetectionChannel(
                'Spectroscopy',
                '氢原子光谱',
                'constraining',
                -1,
                2e-5,
                2024,
                '精细结构分裂，温和约束'
            ),
            
            # 宇宙学
            DetectionChannel(
                'BBN',
                '原初核合成',
                'constraining',
                -1,
                4e-3,
                2024,
                '氦-4丰度，宽松约束'
            ),
            DetectionChannel(
                'Dark Energy',
                'DESI/Euclid',
                'not_detectable',
                0.001,
                1e-2,
                2030,
                '宇宙学常数演化，效应太弱'
            ),
        ]
    
    def generate_summary_report(self):
        """生成综合报告"""
        print("="*80)
        print("统一场理论综合探测前景分析")
        print(f"当前参数: τ₀ = {self.tau_0}")
        print("="*80)
        
        # 分类统计
        detectable = [c for c in self.channels if c.status == 'detectable']
        constraining = [c for c in self.channels if c.status == 'constraining']
        not_detectable = [c for c in self.channels if c.status == 'not_detectable']
        
        print(f"\n📊 探测渠道统计:")
        print(f"   可探测: {len(detectable)} 个")
        print(f"   约束中: {len(constraining)} 个")
        print(f"   不可探测: {len(not_detectable)} 个")
        
        print(f"\n✅ 可探测渠道 (τ₀ = {self.tau_0}):")
        print("-"*80)
        for c in detectable:
            print(f"   {c.name:25s} | SNR={c.snr:8.1f} | {c.experiment}")
        
        print(f"\n⚠️ 约束渠道 (提供上限):")
        print("-"*80)
        for c in constraining:
            print(f"   {c.name:25s} | τ₀ < {c.tau_sensitivity:.0e} | {c.experiment}")
        
        print(f"\n❌ 不可探测 (效应太弱):")
        print("-"*80)
        for c in not_detectable:
            print(f"   {c.name:25s} | 需τ₀ > {c.tau_sensitivity:.0e} | {c.experiment}")
        
        # 最佳探测策略
        print(f"\n🎯 推荐探测策略:")
        print("-"*80)
        print("   1. 【最高优先级】LISA (2034发射)")
        print("      - 6种偏振模式是最明确检验")
        print("      - 预期SNR ~70 (高置信度)")
        print("      - 可探测τ₀ ~ 10⁻⁶")
        print()
        print("   2. 【高优先级】Cosmic Explorer/Einstein Telescope (2035)")
        print("      - 高频引力波补充LISA")
        print("      - 地面探测器更快实现")
        print()
        print("   3. 【理论确认】原子钟约束")
        print("      - 当前τ₀ = 10⁻⁵ 接近但略超约束")
        print("      - 建议调整至τ₀ = 10⁻⁶ 确保兼容")
        
        # 参数调整建议
        print(f"\n📈 参数敏感性分析:")
        print("-"*80)
        print(f"   当前τ₀ = {self.tau_0} 的探测状态:")
        
        for tau_test in [1e-6, 3e-6, 1e-5, 3e-5, 1e-4]:
            n_detect = sum(1 for c in self.channels 
                          if c.status == 'detectable' or 
                          (c.status == 'not_detectable' and tau_test >= c.tau_sensitivity))
            marker = "✓" if tau_test == self.tau_0 else " "
            print(f"   {marker} τ₀ = {tau_test:.0e}: {n_detect} 个渠道可探测")
    
    def plot_comprehensive_dashboard(self):
        """绘制综合探测前景仪表板"""
        fig = plt.figure(figsize=(20, 14))
        gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.35)
        
        # 1. 探测渠道时间线
        ax1 = fig.add_subplot(gs[0, :])
        
        colors = {'detectable': 'green', 'constraining': 'orange', 'not_detectable': 'red'}
        labels = {'detectable': '可探测', 'constraining': '约束中', 'not_detectable': '不可探测'}
        
        y_pos = 0
        for status in ['detectable', 'constraining', 'not_detectable']:
            channels = [c for c in self.channels if c.status == status]
            for c in channels:
                year = c.time_horizon
                ax1.barh(y_pos, 1, left=year-0.5, height=0.6, 
                        color=colors[status], alpha=0.7, edgecolor='black')
                ax1.text(year, y_pos, c.name, ha='center', va='center', 
                        fontsize=9, fontweight='bold')
                y_pos += 1
            y_pos += 0.5
        
        ax1.set_xlim(2020, 2040)
        ax1.set_xlabel('Year', fontsize=12)
        ax1.set_title('Detection Timeline', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='x')
        
        # 添加图例
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=colors[s], label=labels[s]) for s in colors.keys()]
        ax1.legend(handles=legend_elements, loc='upper left')
        
        # 2. tau_0敏感性
        ax2 = fig.add_subplot(gs[1, 0])
        
        tau_range = np.logspace(-6, -3, 50)
        n_detectable = []
        
        for tau in tau_range:
            n = sum(1 for c in self.channels 
                   if c.status == 'detectable' or 
                   (c.status == 'not_detectable' and tau >= c.tau_sensitivity))
            n_detectable.append(n)
        
        ax2.semilogx(tau_range, n_detectable, 'b-', linewidth=3)
        ax2.axvline(x=self.tau_0, color='r', linestyle='--', linewidth=2, 
                   label=f'Current τ₀={self.tau_0:.0e}')
        ax2.set_xlabel('τ₀', fontsize=12)
        ax2.set_ylabel('Number of Detectable Channels', fontsize=12)
        ax2.set_title('Sensitivity to τ₀', fontsize=14, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. SNR对比 (可探测渠道)
        ax3 = fig.add_subplot(gs[1, 1])
        
        detectable_channels = [c for c in self.channels if c.status == 'detectable']
        names = [c.name for c in detectable_channels]
        snrs = [c.snr for c in detectable_channels]
        
        bars = ax3.barh(names, snrs, color='green', alpha=0.7, edgecolor='black')
        ax3.axvline(x=10, color='red', linestyle='--', linewidth=2, label='SNR=10 threshold')
        ax3.set_xlabel('SNR', fontsize=12)
        ax3.set_title('Detectable Channels SNR', fontsize=14, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='x')
        
        # 4. 约束强度对比
        ax4 = fig.add_subplot(gs[1, 2])
        
        constraining_channels = [c for c in self.channels if c.status == 'constraining']
        names = [c.name for c in constraining_channels]
        limits = [c.tau_sensitivity for c in constraining_channels]
        
        bars = ax4.barh(names, limits, color='orange', alpha=0.7, edgecolor='black')
        ax4.axvline(x=self.tau_0, color='red', linestyle='--', linewidth=2, 
                   label=f'Current τ₀={self.tau_0:.0e}')
        ax4.set_xlabel('Upper Limit on τ₀', fontsize=12)
        ax4.set_xscale('log')
        ax4.set_title('Constraining Channels', fontsize=14, fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3, axis='x')
        
        # 5. 探测能力矩阵
        ax5 = fig.add_subplot(gs[2, :2])
        
        # 创建矩阵: 渠道 x tau_0值
        tau_values = [1e-6, 3e-6, 1e-5, 3e-5, 1e-4]
        channel_names = [c.name for c in self.channels]
        
        matrix = np.zeros((len(self.channels), len(tau_values)))
        
        for i, c in enumerate(self.channels):
            for j, tau in enumerate(tau_values):
                if c.status == 'detectable':
                    if tau <= c.tau_sensitivity * 10:  # 可探测范围
                        matrix[i, j] = 2  # 绿色 - 可探测
                    else:
                        matrix[i, j] = 1  # 黄色 - 边缘
                elif c.status == 'constraining':
                    if tau < c.tau_sensitivity:
                        matrix[i, j] = 1  # 黄色 - 通过约束
                    else:
                        matrix[i, j] = 0  # 红色 - 违反约束
                else:  # not_detectable
                    if tau >= c.tau_sensitivity:
                        matrix[i, j] = 2  # 绿色 - 可探测
                    else:
                        matrix[i, j] = 0  # 红色 - 不可探测
        
        im = ax5.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=2)
        ax5.set_xticks(range(len(tau_values)))
        ax5.set_xticklabels([f'{t:.0e}' for t in tau_values])
        ax5.set_yticks(range(len(channel_names)))
        ax5.set_yticklabels(channel_names, fontsize=9)
        ax5.set_xlabel('τ₀', fontsize=12)
        ax5.set_title('Detection Capability Matrix', fontsize=14, fontweight='bold')
        
        # 添加颜色条
        from matplotlib.colorbar import ColorbarBase
        cbar = plt.colorbar(im, ax=ax5, orientation='horizontal', pad=0.2)
        cbar.set_ticks([0, 1, 2])
        cbar.set_ticklabels(['Not Detectable', 'Marginal', 'Detectable'])
        
        # 6. 推荐策略
        ax6 = fig.add_subplot(gs[2, 2])
        ax6.axis('off')
        
        strategy_text = """
        🎯 RECOMMENDED STRATEGY
        
        Current: τ₀ = 10⁻⁵
        
        1. 【IMMEDIATE】
           Adjust τ₀ → 10⁻⁶
           - Passes atomic clock constraint
           - Still LISA-detectable
        
        2. 【2024-2030】
           Develop LISA data pipeline
           - 6-polarization templates
           - Bayesian parameter estimation
        
        3. 【2034+】
           LISA science operations
           - Search for extra polarizations
           - Constraint: τ₀ < 10⁻⁶
        
        4. 【2035+】
           Cosmic Explorer/ET
           - High-frequency complement
           - Independent confirmation
        """
        
        ax6.text(0.05, 0.95, strategy_text, transform=ax6.transAxes,
                fontsize=10, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.suptitle(f'UFT Detection Prospects Dashboard (τ₀ = {self.tau_0})', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        plt.savefig('detection_prospects_dashboard.png', dpi=200, 
                   bbox_inches='tight', facecolor='white')
        print("\n综合仪表板已保存: detection_prospects_dashboard.png")
        plt.close()
    
    def plot_parameter_space(self):
        """绘制参数空间图"""
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        # 1. tau_0 vs 探测年份
        ax1 = axes[0]
        
        for c in self.channels:
            if c.status == 'detectable':
                color = 'green'
                marker = 'o'
            elif c.status == 'constraining':
                color = 'orange'
                marker = 's'
            else:
                color = 'red'
                marker = '^'
            
            ax1.scatter(c.time_horizon, c.tau_sensitivity, 
                       c=color, marker=marker, s=200, alpha=0.7, edgecolors='black')
            ax1.annotate(c.name, (c.time_horizon, c.tau_sensitivity),
                        xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        ax1.axhline(y=self.tau_0, color='purple', linestyle='--', linewidth=2,
                   label=f'Current τ₀={self.tau_0:.0e}')
        ax1.set_xlabel('Year', fontsize=12)
        ax1.set_ylabel('τ₀ Sensitivity', fontsize=12)
        ax1.set_yscale('log')
        ax1.set_title('Parameter Space: τ₀ vs Time', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 约束排除图
        ax2 = axes[1]
        
        # 已排除区域
        tau_range = np.logspace(-7, -2, 100)
        
        # 各种约束
        ax2.fill_between(tau_range, 0, 1, 
                        where=(tau_range > 1e-6),
                        alpha=0.3, color='red', label='Excluded by optical clocks')
        ax2.fill_between(tau_range, 0, 1,
                        where=(tau_range > 4e-3),
                        alpha=0.3, color='orange', label='Excluded by BBN')
        
        # 当前参数
        ax2.axvline(x=self.tau_0, color='purple', linewidth=3, 
                   label=f'Current τ₀={self.tau_0:.0e}')
        
        # 最佳拟合区域
        ax2.axvspan(1e-6, 3e-6, alpha=0.3, color='green', 
                   label='Preferred region')
        
        ax2.set_xlabel('τ₀', fontsize=12)
        ax2.set_ylabel('Probability Density (arb.)', fontsize=12)
        ax2.set_xscale('log')
        ax2.set_title('Parameter Constraints', fontsize=14, fontweight='bold')
        ax2.set_xlim([1e-7, 1e-2])
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('parameter_space_analysis.png', dpi=200,
                   bbox_inches='tight', facecolor='white')
        print("参数空间图已保存: parameter_space_analysis.png")
        plt.close()

def main():
    """主函数"""
    # 创建探测前景分析
    prospects = UFT_Detection_Prospects(tau_0=1e-5)
    
    # 生成报告
    prospects.generate_summary_report()
    
    # 绘制图表
    prospects.plot_comprehensive_dashboard()
    prospects.plot_parameter_space()
    
    print("\n" + "="*80)
    print("统一场理论综合探测前景分析完成!")
    print("="*80)

if __name__ == "__main__":
    main()
