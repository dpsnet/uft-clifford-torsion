import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches

# 设置中文字体（如果可用）和样式
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.dpi'] = 150

# 颜色方案
colors = {
    'primary': '#2E86AB',      # 蓝色
    'secondary': '#A23B72',    # 紫红色
    'accent': '#F18F01',       # 橙色
    'light': '#C73E1D',        # 红色
    'dark': '#1B1B1E',         # 深灰
    'gray': '#6B6B6B'          # 中灰
}

# ==================== Figure 1: 谱维坍缩演化 ====================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

# 左图：f_in vs d_s
f_in = np.linspace(0, 1, 100)
d_s_out = 4 * (1 - f_in)
d_s_in = 4 + 6 * f_in

ax1.plot(f_in, d_s_out, color=colors['primary'], linewidth=2.5, 
         label=r'$d_s^{(\mathrm{out})} = 4(1-f_{\mathrm{in}})$')
ax1.plot(f_in, d_s_in, color=colors['secondary'], linewidth=2.5, 
         label=r'$d_s^{(\mathrm{in})} = 4 + 6f_{\mathrm{in}}$')
ax1.axvline(x=0.9, color=colors['accent'], linestyle='--', alpha=0.7, 
            label='Supernova core ($f_{\\mathrm{in}} \\approx 0.9$)')
ax1.fill_between([0.9, 1.0], [0, 0], [4, 4], alpha=0.2, color=colors['accent'])

ax1.set_xlabel(r'$f_{\mathrm{in}}$ (Internal Space Energy Fraction)', fontsize=10)
ax1.set_ylabel('Spectral Dimension $d_s$', fontsize=10)
ax1.set_title('Spectral Dimension Flow', fontsize=11, fontweight='bold')
ax1.legend(loc='upper right', framealpha=0.9)
ax1.set_xlim(0, 1)
ax1.set_ylim(0, 10)
ax1.grid(True, alpha=0.3)

# 右图：超新星核心示意图（简化）
r = np.linspace(0, 1, 100)
f_in_profile = 0.5 + 0.4 * (1 - np.exp(-r*3))  # 核心f_in更高
d_s_profile = 4 * (1 - f_in_profile)

ax2.plot(r, d_s_profile, color=colors['primary'], linewidth=2.5)
ax2.fill_between(r, 0, d_s_profile, alpha=0.3, color=colors['primary'])
ax2.axhline(y=1, color=colors['light'], linestyle='--', alpha=0.7, 
            label='Critical $d_s \\approx 1$')

ax2.set_xlabel('Normalized Radius $r/R_{\mathrm{core}}$', fontsize=10)
ax2.set_ylabel(r'$d_s^{(\mathrm{out})}$', fontsize=10)
ax2.set_title('Supernova Core Profile', fontsize=11, fontweight='bold')
ax2.set_xlim(0, 1)
ax2.set_ylim(0, 2.5)
ax2.legend(loc='upper right')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('spectral_collapse.pdf', bbox_inches='tight', dpi=300)
plt.savefig('spectral_collapse.png', bbox_inches='tight', dpi=150)
print("✓ Generated: spectral_collapse.pdf/png")

# ==================== Figure 2: 中微子时间结构 ====================
fig, ax = plt.subplots(figsize=(10, 5))

# 时间轴（毫秒）
t = np.linspace(0, 12000, 1000)  # 0-12秒

# 早期脉冲（左旋中微子快速逃逸）
early_pulse = 0.8 * np.exp(-((t - 300)**2) / (200**2)) * (t < 1000)

# 主爆发（谱维坍缩后）
main_burst = 3.0 * np.exp(-((t - 2000)**2) / (1500**2)) * (t > 1000)

# 残余拖尾
tail = 0.5 * np.exp(-t / 3000)

# 总和
total = early_pulse + main_burst + tail

ax.fill_between(t/1000, 0, total, alpha=0.3, color=colors['primary'], 
                label='Total neutrino flux')
ax.plot(t/1000, early_pulse, color=colors['accent'], linewidth=2, 
        linestyle='--', label='Early pulse (left-handed)')
ax.plot(t/1000, main_burst, color=colors['secondary'], linewidth=2, 
        linestyle='--', label='Main burst')

# 标记关键时间点
ax.axvline(x=0.3, color=colors['light'], linestyle=':', alpha=0.7)
ax.text(0.35, 2.5, '$t_{\\mathrm{esc}}^{(L)} \\sim 6.6$ ms', 
        fontsize=9, color=colors['light'])

ax.axvline(x=6, color=colors['accent'], linestyle=':', alpha=0.7)
ax.text(6.5, 2.5, 'GW-$\\nu$ delay', fontsize=9, color=colors['accent'])

ax.set_xlabel('Time since core bounce (s)', fontsize=11)
ax.set_ylabel('Normalized neutrino flux', fontsize=11)
ax.set_title('CTUFT Neutrino Time Structure', fontsize=12, fontweight='bold')
ax.legend(loc='upper right', framealpha=0.9)
ax.set_xlim(0, 12)
ax.set_ylim(0, 3.5)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('neutrino_time_structure.pdf', bbox_inches='tight', dpi=300)
plt.savefig('neutrino_time_structure.png', bbox_inches='tight', dpi=150)
print("✓ Generated: neutrino_time_structure.pdf/png")

# ==================== Figure 3: FRB 周期关系 ====================
fig, ax = plt.subplots(figsize=(8, 6))

# 磁星自转周期范围（小时）
P_spin = np.array([0.5, 1, 2, 3, 4, 5, 6, 8, 10, 12])
P_FRB = 200 * P_spin / 24  # 转换为天

# 绘制理论线
ax.plot(P_spin, P_FRB, 'o-', color=colors['primary'], linewidth=2.5, 
        markersize=8, label=r'$P_{\\mathrm{FRB}} = 200 \\times P_{\\mathrm{spin}}$')

# 标记FRB 180916
ax.scatter([1.96], [16.35], s=200, c=colors['accent'], marker='*', 
           zorder=5, edgecolors='black', linewidths=1.5, 
           label='FRB 180916.J0158+65')

# 标记其他候选区域
ax.axhspan(4, 8, alpha=0.15, color=colors['secondary'], 
           label='FRB 121102 candidate range')
ax.axhspan(40, 100, alpha=0.15, color=colors['gray'], 
           label='Long period regime')

ax.set_xlabel('Magnetar Spin Period $P_{\\mathrm{spin}}$ (hours)', fontsize=11)
ax.set_ylabel('FRB Period $P_{\\mathrm{FRB}}$ (days)', fontsize=11)
ax.set_title('CTUFT Prediction: FRB Period vs Magnetar Spin', 
             fontsize=12, fontweight='bold')
ax.legend(loc='upper left', framealpha=0.9)
ax.set_xlim(0, 13)
ax.set_ylim(0, 110)
ax.grid(True, alpha=0.3)

# 添加注释
ax.annotate('Observable\n(4-8 days)', xy=(1, 6), fontsize=9, 
            ha='center', color=colors['secondary'])
ax.annotate('Marginal\n(>100 days)', xy=(10, 100), fontsize=9, 
            ha='center', color=colors['gray'])

plt.tight_layout()
plt.savefig('frb_period_relation.pdf', bbox_inches='tight', dpi=300)
plt.savefig('frb_period_relation.png', bbox_inches='tight', dpi=150)
print("✓ Generated: frb_period_relation.pdf/png")

print("\n" + "="*50)
print("All figures generated successfully!")
print("="*50)
