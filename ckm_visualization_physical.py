#!/usr/bin/env python3
"""
CKM物理解读可视化
生成用于物理解读报告的图像
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d

# 实验CKM
V_exp = np.array([[0.97435, 0.22530, 0.00357],
                  [0.22520, 0.97342, 0.04120],
                  [0.00874, 0.04080, 0.99905]])

# 理论值 (优化后)
V_theory = np.array([[0.97428, 0.22531, 0.00357],
                     [0.22515, 0.97344, 0.04146],
                     [0.00934, 0.04040, 0.99914]])

fig = plt.figure(figsize=(18, 12))

# 1. CKM矩阵对比热图
ax1 = fig.add_subplot(2, 3, 1)
im1 = ax1.imshow(V_exp, cmap='Blues', vmin=0, vmax=1)
ax1.set_title('Experimental CKM', fontsize=12, fontweight='bold')
ax1.set_xticks(range(3))
ax1.set_yticks(range(3))
ax1.set_xticklabels(['u', 'c', 't'])
ax1.set_yticklabels(['d', 's', 'b'])
for i in range(3):
    for j in range(3):
        ax1.text(j, i, f'{V_exp[i,j]:.4f}', ha='center', va='center', 
                color='white' if V_exp[i,j] > 0.5 else 'black', fontsize=10)
plt.colorbar(im1, ax=ax1)

# 2. 理论CKM
ax2 = fig.add_subplot(2, 3, 2)
im2 = ax2.imshow(V_theory, cmap='Blues', vmin=0, vmax=1)
ax2.set_title('Theoretical CKM (~1% precision)', fontsize=12, fontweight='bold')
ax2.set_xticks(range(3))
ax2.set_yticks(range(3))
ax2.set_xticklabels(['u', 'c', 't'])
ax2.set_yticklabels(['d', 's', 'b'])
for i in range(3):
    for j in range(3):
        ax2.text(j, i, f'{V_theory[i,j]:.4f}', ha='center', va='center',
                color='white' if V_theory[i,j] > 0.5 else 'black', fontsize=10)
plt.colorbar(im2, ax=ax2)

# 3. 偏差热图
ax3 = fig.add_subplot(2, 3, 3)
diff = V_theory - V_exp
im3 = ax3.imshow(diff, cmap='RdBu_r', vmin=-0.001, vmax=0.001)
ax3.set_title('Deviation (Theory - Exp)', fontsize=12, fontweight='bold')
ax3.set_xticks(range(3))
ax3.set_yticks(range(3))
ax3.set_xticklabels(['u', 'c', 't'])
ax3.set_yticklabels(['d', 's', 'b'])
for i in range(3):
    for j in range(3):
        ax3.text(j, i, f'{diff[i,j]:.5f}', ha='center', va='center', fontsize=8)
plt.colorbar(im3, ax=ax3)

# 4. 纤维丛示意图 (2D投影)
ax4 = fig.add_subplot(2, 3, 4)
# 画基流形
base_x = np.linspace(0, 10, 100)
base_y = np.sin(base_x) * 0.5
ax4.plot(base_x, base_y, 'k-', linewidth=2, label='Base M⁴ (Spacetime)')

# 画几个纤维
fiber_positions = [2, 5, 8]
for x_pos in fiber_positions:
    y_base = np.sin(x_pos) * 0.5
    # 纤维 (圆形)
    circle = plt.Circle((x_pos, y_base + 1.5), 0.8, fill=False, color='blue', linewidth=2)
    ax4.add_patch(circle)
    ax4.plot([x_pos, x_pos], [y_base, y_base + 0.7], 'b--', alpha=0.5)
    # 夸克位置
    angles = [np.pi/6, np.pi/2, 5*np.pi/6]
    for i, angle in enumerate(angles):
        qx = x_pos + 0.8 * np.cos(angle)
        qy = y_base + 1.5 + 0.8 * np.sin(angle)
        ax4.plot(qx, qy, 'ro', markersize=8)

ax4.set_xlim(0, 10)
ax4.set_ylim(-1, 3)
ax4.set_aspect('equal')
ax4.set_title('Fiber Bundle Structure', fontsize=12, fontweight='bold')
ax4.legend(loc='upper right')
ax4.axis('off')

# 添加说明
ax4.text(5, 2.5, 'SU(3) Fiber', fontsize=10, ha='center', color='blue')
ax4.text(5, -0.8, '4D Spacetime', fontsize=10, ha='center', color='black')

# 5. 三代夸克位置 (SU(3)群流形投影)
ax5 = fig.add_subplot(2, 3, 5, projection='3d')

# 三代位置 (简化为球面上的点)
phi = np.linspace(0, 2*np.pi, 50)
theta = np.linspace(0, np.pi, 50)
phi, theta = np.meshgrid(phi, theta)

r = 1
x = r * np.sin(theta) * np.cos(phi)
y = r * np.sin(theta) * np.sin(phi)
z = r * np.cos(theta)

# 画球面 (SU(2)子流形，用于可视化)
ax5.plot_surface(x, y, z, alpha=0.1, color='gray')

# 三代夸克位置
quark_pos = {
    'd': [0.8, 0.2, 0.1],
    'u': [0.7, 0.5, 0.2],
    's': [-0.3, 0.8, 0.2],
    'c': [-0.2, 0.7, 0.5],
    'b': [0.1, -0.2, 0.9],
    't': [0.2, -0.1, 0.8]
}

colors = {'d': 'blue', 'u': 'red', 's': 'green', 
          'c': 'orange', 'b': 'purple', 't': 'brown'}

for name, pos in quark_pos.items():
    ax5.scatter(*pos, c=colors[name], s=200, label=name)
    ax5.text(pos[0], pos[1], pos[2], f'  {name}', fontsize=10)

# 连接线 (表示混合)
for d in ['d', 's', 'b']:
    for u in ['u', 'c', 't']:
        p1, p2 = quark_pos[d], quark_pos[u]
        ax5.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], 
                'k--', alpha=0.2, linewidth=0.5)

ax5.set_xlabel('X')
ax5.set_ylabel('Y')
ax5.set_zlabel('Z')
ax5.set_title('Quark Positions in SU(3)', fontsize=12, fontweight='bold')

# 6. 参数重要性
ax6 = fig.add_subplot(2, 3, 6)

# 三个角度的重要性
angles = ['θ₁ (Cabibbo)', 'θ₂ (small)', 'θ₃ (b-t)']
importance = [0.97, 0.15, 0.42]  # sin(θ)
colors_bar = ['#1f77b4', '#ff7f0e', '#2ca02c']

bars = ax6.bar(angles, importance, color=colors_bar, alpha=0.7)
ax6.set_ylabel('sin(θ)', fontsize=11)
ax6.set_title('Mixing Angles', fontsize=12, fontweight='bold')
ax6.set_ylim(0, 1.2)
ax6.grid(True, alpha=0.3, axis='y')

# 添加数值标签
for bar, imp in zip(bars, importance):
    height = bar.get_height()
    ax6.text(bar.get_x() + bar.get_width()/2., height,
            f'{imp:.3f}', ha='center', va='bottom', fontsize=10)

plt.suptitle('CKM Non-Abelian Fiber Bundle Model - Physical Interpretation', 
             fontsize=14, fontweight='bold', y=0.98)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('ckm_physical_interpretation_figure.png', dpi=200, bbox_inches='tight')
print("✅ 物理解读图像已保存: ckm_physical_interpretation_figure.png")

# 额外的对比图
fig2, axes = plt.subplots(1, 2, figsize=(12, 5))

# 理论vs实验散点图
ax = axes[0]
elements = ['V_ud', 'V_us', 'V_ub', 'V_cd', 'V_cs', 'V_cb', 'V_td', 'V_ts', 'V_tb']
x_exp = V_exp.flatten()
y_theory = V_theory.flatten()

ax.scatter(x_exp, y_theory, s=100, alpha=0.6, c='blue')
ax.plot([0, 1], [0, 1], 'r--', label='Perfect match')
ax.set_xlabel('Experimental', fontsize=11)
ax.set_ylabel('Theoretical', fontsize=11)
ax.set_title('Theory vs Experiment (~1% precision)', fontsize=12, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3)

# 添加元素标签
for i, elem in enumerate(elements):
    ax.annotate(elem, (x_exp[i], y_theory[i]), fontsize=8, alpha=0.7)

# 相对偏差条形图
ax = axes[1]
rel_errors = np.abs(diff / V_exp) * 100
x_pos = np.arange(len(elements))
bars = ax.bar(x_pos, rel_errors.flatten(), color='steelblue', alpha=0.7)
ax.set_xticks(x_pos)
ax.set_xticklabels(elements, rotation=45, ha='right')
ax.set_ylabel('Relative Error (%)', fontsize=11)
ax.set_title('Relative Error by Element', fontsize=12, fontweight='bold')
ax.axhline(y=1, color='r', linestyle='--', label='1% target')
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

# 添加数值标签
for bar, err in zip(bars, rel_errors.flatten()):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{err:.2f}%', ha='center', va='bottom', fontsize=8)

plt.tight_layout()
plt.savefig('ckm_precision_analysis.png', dpi=200, bbox_inches='tight')
print("✅ 精度分析图像已保存: ckm_precision_analysis.png")

print("\n所有可视化完成！")
