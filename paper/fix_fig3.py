import numpy as np
import matplotlib.pyplot as plt

# 设置样式
plt.rcParams['font.size'] = 10
plt.rcParams['figure.dpi'] = 150

# 颜色方案
colors = {'primary': '#2E86AB', 'accent': '#F18F01', 'secondary': '#A23B72', 'gray': '#6B6B6B'}

# FRB 周期关系图
fig, ax = plt.subplots(figsize=(8, 6))

# 磁星自转周期范围（小时）
P_spin = np.array([0.5, 1, 2, 3, 4, 5, 6, 8, 10, 12])
P_FRB = 200 * P_spin / 24  # 转换为天

# 绘制理论线
ax.plot(P_spin, P_FRB, 'o-', color=colors['primary'], linewidth=2.5, 
        markersize=8, label='P_FRB = 200 × P_spin')

# 标记FRB 180916
ax.scatter([1.96], [16.35], s=200, c=colors['accent'], marker='*', 
           zorder=5, edgecolors='black', linewidths=1.5, 
           label='FRB 180916.J0158+65')

# 标记其他候选区域
ax.axhspan(4, 8, alpha=0.15, color=colors['secondary'], 
           label='FRB 121102 candidate range')
ax.axhspan(40, 100, alpha=0.15, color=colors['gray'], 
           label='Long period regime')

ax.set_xlabel('Magnetar Spin Period P_spin (hours)', fontsize=11)
ax.set_ylabel('FRB Period P_FRB (days)', fontsize=11)
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
print("All 3 figures generated successfully!")
print("="*50)
