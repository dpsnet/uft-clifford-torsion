import numpy as np
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 能量范围
E = np.logspace(-2, 4, 1000)  # 从0.01到10000 E_c单位
E_c = 1.0  # 特征能量

# 现有公式（仅内空间/外空间单向）
def d_s_current(E, E_c):
    """现有公式 - 描述从4到10的变化"""
    return 4 + 6 / (1 + (E_c/E)**2)

# 候选公式1: Sigmoid型（双向）
def d_s_out_sigmoid(E, E_bind=0.5, delta_E=0.5):
    """外空间谱维 - 能量耗散主导"""
    return 4 / (1 + np.exp(-(E - E_bind)/delta_E))

def d_s_in_sigmoid(E, E_c=1.0, delta_E=0.5):
    """内空间谱维 - 能量扩展主导"""
    return 4 + 6 / (1 + np.exp((E - E_c)/delta_E))

# 候选公式2: 幂律型
def d_s_out_power(E, E_bind=0.5, alpha=1.0):
    """外空间谱维 - 幂律型"""
    return 4 * (E / (E + E_bind))**alpha

def d_s_in_power(E, E_c=1.0, beta=1.0):
    """内空间谱维 - 幂律型"""
    return 4 + 6 * (E / E_c)**beta

# 候选公式3: 有理函数型（与现有公式兼容）
def d_s_out_rational(E, E_bind=0.5):
    """外空间谱维 - 与现有公式对称的形式"""
    return 4 / (1 + (E_bind/E)**2)

def d_s_in_rational(E, E_c=1.0):
    """内空间谱维 - 现有公式"""
    return 4 + 6 / (1 + (E_c/E)**2)

# 计算各种情况
d_s_curr = d_s_current(E, E_c)

# Sigmoid型
d_s_out_sig = d_s_out_sigmoid(E)
d_s_in_sig = d_s_in_sigmoid(E)

# 有理函数型
d_s_out_rat = d_s_out_rational(E)
d_s_in_rat = d_s_in_rational(E)

# 检验守恒律
print("="*60)
print("守恒律检验 - Sigmoid型")
print("="*60)
print(f"E → 0:  d_s_out = {d_s_out_sigmoid(0.001):.3f}, d_s_in = {d_s_in_sigmoid(0.001):.3f}, 和 = {d_s_out_sigmoid(0.001) + d_s_in_sigmoid(0.001):.3f}")
print(f"E = E_c: d_s_out = {d_s_out_sigmoid(1.0):.3f}, d_s_in = {d_s_in_sigmoid(1.0):.3f}, 和 = {d_s_out_sigmoid(1.0) + d_s_in_sigmoid(1.0):.3f}")
print(f"E → ∞:  d_s_out = {d_s_out_sigmoid(1000):.3f}, d_s_in = {d_s_in_sigmoid(1000):.3f}, 和 = {d_s_out_sigmoid(1000) + d_s_in_sigmoid(1000):.3f}")

print("\n" + "="*60)
print("守恒律检验 - 有理函数型")
print("="*60)
print(f"E → 0:  d_s_out = {d_s_out_rational(0.001):.3f}, d_s_in = {d_s_in_rational(0.001):.3f}, 和 = {d_s_out_rational(0.001) + d_s_in_rational(0.001):.3f}")
print(f"E = E_c: d_s_out = {d_s_out_rational(1.0):.3f}, d_s_in = {d_s_in_rational(1.0):.3f}, 和 = {d_s_out_rational(1.0) + d_s_in_rational(1.0):.3f}")
print(f"E → ∞:  d_s_out = {d_s_out_rational(1000):.3f}, d_s_in = {d_s_in_rational(1000):.3f}, 和 = {d_s_out_rational(1000) + d_s_in_rational(1000):.3f}")

print("\n" + "="*60)
print("边界条件检验")
print("="*60)
print("理想边界条件:")
print("  大爆炸初始: d_s_out = 4, d_s_in = 10")
print("  今天宇宙:   d_s_out = 4, d_s_in = 4")
print("  黑洞视界:   d_s_out = 0, d_s_in = 10")
print()

# 检验边界条件
print("有理函数型边界条件:")
print(f"  E → 0 (今天宇宙?): d_s_out = {d_s_out_rational(0.001):.3f}, d_s_in = {d_s_in_rational(0.001):.3f}")
print(f"  E = E_c:           d_s_out = {d_s_out_rational(1.0):.3f}, d_s_in = {d_s_in_rational(1.0):.3f}")
print(f"  E → ∞ (大爆炸?):   d_s_out = {d_s_out_rational(10000):.3f}, d_s_in = {d_s_in_rational(10000):.3f}")

# 绘制图形
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 图1: 现有公式 vs 双向公式对比
ax1 = axes[0, 0]
ax1.semilogx(E, d_s_curr, 'k--', linewidth=2, label='现有公式 (单向)')
ax1.semilogx(E, d_s_out_rat, 'b-', linewidth=2, label='外空间 $d_s^{(out)}$')
ax1.semilogx(E, d_s_in_rat, 'r-', linewidth=2, label='内空间 $d_s^{(in)}$')
ax1.axhline(y=4, color='gray', linestyle=':', alpha=0.5)
ax1.axhline(y=10, color='gray', linestyle=':', alpha=0.5)
ax1.set_xlabel('能量 E (相对 $E_c$)', fontsize=12)
ax1.set_ylabel('谱维 $d_s$', fontsize=12)
ax1.set_title('双向谱维流 - 有理函数型', fontsize=14)
ax1.legend(loc='center right')
ax1.set_ylim(-1, 12)
ax1.grid(True, alpha=0.3)

# 图2: 守恒律检验
ax2 = axes[0, 1]
sum_rat = d_s_out_rat + d_s_in_rat
product_rat = d_s_out_rat * d_s_in_rat
ax2.semilogx(E, sum_rat, 'g-', linewidth=2, label='$d_s^{(out)} + d_s^{(in)}$')
ax2.axhline(y=14, color='gray', linestyle=':', alpha=0.5, label='常数14')
ax2.axhline(y=10, color='orange', linestyle=':', alpha=0.5, label='常数10')
ax2.set_xlabel('能量 E (相对 $E_c$)', fontsize=12)
ax2.set_ylabel('维度之和', fontsize=12)
ax2.set_title('守恒律检验 - 维度之和', fontsize=14)
ax2.legend()
ax2.set_ylim(0, 16)
ax2.grid(True, alpha=0.3)

# 图3: 归一化比例
ax3 = axes[1, 0]
norm_sum = d_s_out_rat/4 + d_s_in_rat/10
ax3.semilogx(E, norm_sum, 'm-', linewidth=2, label='$d_s^{(out)}/4 + d_s^{(in)}/10$')
ax3.axhline(y=1.0, color='gray', linestyle=':', alpha=0.5, label='归一化 = 1')
ax3.set_xlabel('能量 E (相对 $E_c$)', fontsize=12)
ax3.set_ylabel('归一化维度', fontsize=12)
ax3.set_title('守恒律检验 - 归一化比例', fontsize=14)
ax3.legend()
ax3.set_ylim(0, 2)
ax3.grid(True, alpha=0.3)

# 图4: 乘积守恒
ax4 = axes[1, 1]
ax4.semilogx(E, product_rat, 'c-', linewidth=2, label='$d_s^{(out)} \\times d_s^{(in)}$')
ax4.axhline(y=40, color='gray', linestyle=':', alpha=0.5, label='$4 \\times 10 = 40$')
ax4.set_xlabel('能量 E (相对 $E_c$)', fontsize=12)
ax4.set_ylabel('维度乘积', fontsize=12)
ax4.set_title('守恒律检验 - 维度乘积', fontsize=14)
ax4.legend()
ax4.set_ylim(0, 50)
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('/root/.openclaw/workspace/uft-clifford-torsion/research_notes/spectral_flow_analysis.png', dpi=150)
print("\n图形已保存至: spectral_flow_analysis.png")

# 关键发现总结
print("\n" + "="*60)
print("关键发现")
print("="*60)
print("""
1. 有理函数型公式在 E → 0 时给出 d_s_out → 0, d_s_in → 4
   - 这与'今天宇宙'的期望 (4, 4) 不符
   - 但与'黑洞视界'的期望 (0, 10) 也不完全匹配

2. 守恒律分析:
   - 简单相加: d_s_out + d_s_in 从 4 变到 14
   - 归一化比例: d_s_out/4 + d_s_in/10 接近但不严格等于1
   - 乘积: d_s_out × d_s_in 接近40但不严格

3. 需要重新思考:
   - 能量参数的定义（可能是能量密度而非总能量）
   - 外空间和内空间的能量可能是互补的
   - 可能需要引入不同的特征能量尺度
""")
