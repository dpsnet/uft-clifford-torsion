#!/usr/bin/env python3
"""
方向1: CKM矩阵3D球面模型
3D Sphere Model for CKM Matrix

将三代夸克放置在S³上，替代2D平面模型
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

class CKM3DSphereModel:
    """CKM 3D球面模型"""
    
    def __init__(self):
        # 实验值
        self.V_CKM_exp = np.array([
            [0.97435, 0.22530, 0.00357],
            [0.22520, 0.97342, 0.04120],
            [0.00874, 0.04080, 0.99905]
        ])
        
    def spherical_to_cartesian(self, theta, phi, r=1.0):
        """球坐标转笛卡尔坐标"""
        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)
        return np.array([x, y, z])
    
    def great_circle_distance(self, p1, p2, r=1.0):
        """计算球面上两点的大圆距离"""
        # p1, p2 是笛卡尔坐标
        cos_angle = np.dot(p1, p2) / (r**2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.arccos(cos_angle)
        return r * angle
    
    def geometric_ckm_sphere(self, params):
        """
        基于S²球面的CKM模型 (简化3D)
        
        参数: [θ_d, φ_d, θ_u, φ_u, θ_s, φ_s, θ_c, φ_c, θ_b, φ_b, θ_t, φ_t, alpha]
        其中 (θ, φ) 是球坐标，alpha是整体相位系数
        """
        # 解包参数
        theta = params[0:12:2]  # θ值
        phi = params[1:12:2]    # φ值
        alpha = params[12] if len(params) > 12 else 1.0
        
        # 计算位置 (d, u, s, c, b, t)
        positions = []
        for i in range(6):
            pos = self.spherical_to_cartesian(theta[i], phi[i])
            positions.append(pos)
        
        # 构建CKM矩阵
        # V_ij = exp(-alpha * d²) 其中d是球面距离
        V = np.zeros((3, 3), dtype=complex)
        
        down_quarks = [0, 2, 4]  # d, s, b
        up_quarks = [1, 3, 5]    # u, c, t
        
        for i, d_idx in enumerate(down_quarks):
            for j, u_idx in enumerate(up_quarks):
                dist = self.great_circle_distance(positions[d_idx], positions[u_idx])
                # 距离越小，混合越强
                mixing = np.exp(-alpha * dist)
                # 添加相位（来自经度差）
                phase = np.exp(1j * (phi[u_idx] - phi[d_idx]))
                V[i, j] = mixing * phase
        
        # 单位化（近似）
        for i in range(3):
            norm = np.sqrt(np.sum(np.abs(V[i, :])**2))
            if norm > 0:
                V[i, :] /= norm
        
        return np.abs(V), positions
    
    def chi_squared(self, params):
        """计算与实验值的偏差"""
        V_theory, _ = self.geometric_ckm_sphere(params)
        
        # 计算偏差
        diff = V_theory - self.V_CKM_exp
        chi2 = np.sum(diff**2) * 100
        
        return chi2
    
    def fit_parameters(self):
        """拟合球面位置参数"""
        print("拟合3D球面模型...")
        
        # 初始猜测 (球面上大致均匀分布)
        x0 = [
            # d夸克 (北极附近)
            0.1, 0.0,
            # u夸克
            0.2, np.pi/6,
            # s夸克 (赤道)
            np.pi/2, 0.0,
            # c夸克
            np.pi/2, 2*np.pi/3,
            # b夸克 (南极附近)
            np.pi - 0.1, 4*np.pi/3,
            # t夸克
            np.pi - 0.2, 5*np.pi/3,
            # alpha
            2.0
        ]
        
        # 边界
        bounds = []
        for i in range(6):  # 6个夸克
            bounds.append((0, np.pi))      # θ ∈ [0, π]
            bounds.append((0, 2*np.pi))    # φ ∈ [0, 2π]
        bounds.append((0.1, 10.0))        # alpha
        
        # 优化
        result = differential_evolution(
            self.chi_squared,
            bounds,
            seed=42,
            maxiter=2000,
            polish=True
        )
        
        return result
    
    def evaluate_fit(self, params):
        """评估拟合结果"""
        V_theory, positions = self.geometric_ckm_sphere(params)
        
        print("\n实验CKM矩阵:")
        print(self.V_CKM_exp)
        
        print("\n理论CKM矩阵 (3D球面):")
        print(V_theory)
        
        print("\n偏差:")
        diff = V_theory - self.V_CKM_exp
        print(diff)
        print(f"\n最大偏差: {np.max(np.abs(diff)):.4f}")
        print(f"平均偏差: {np.mean(np.abs(diff)):.4f}")
        
        # 计算各元素的相对偏差
        rel_diff = np.abs(diff) / self.V_CKM_exp
        print(f"\n相对偏差 (%):")
        print(rel_diff * 100)
        print(f"最大相对偏差: {np.max(rel_diff)*100:.2f}%")
        
        return V_theory, positions, rel_diff
    
    def visualize_3d_sphere(self, positions):
        """3D可视化"""
        fig = plt.figure(figsize=(12, 5))
        
        # 1. 3D球面图
        ax1 = fig.add_subplot(121, projection='3d')
        
        # 绘制球面网格
        u = np.linspace(0, 2 * np.pi, 50)
        v = np.linspace(0, np.pi, 50)
        x = np.outer(np.cos(u), np.sin(v))
        y = np.outer(np.sin(u), np.sin(v))
        z = np.outer(np.ones(np.size(u)), np.cos(v))
        ax1.plot_surface(x, y, z, alpha=0.1, color='gray')
        
        # 绘制夸克位置
        quark_names = ['d', 'u', 's', 'c', 'b', 't']
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown']
        
        for i, (pos, name, color) in enumerate(zip(positions, quark_names, colors)):
            ax1.scatter(*pos, c=color, s=200, label=name)
            ax1.text(pos[0], pos[1], pos[2], f'  {name}', fontsize=10)
        
        # 连接线
        down_indices = [0, 2, 4]
        up_indices = [1, 3, 5]
        for d_idx in down_indices:
            for u_idx in up_indices:
                p1, p2 = positions[d_idx], positions[u_idx]
                ax1.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], 
                        'k--', alpha=0.3, linewidth=0.5)
        
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_zlabel('Z')
        ax1.set_title('Quark Positions on S² Sphere')
        ax1.legend()
        
        # 2. 偏差对比
        ax2 = fig.add_subplot(122)
        
        elements = ['Vud', 'Vus', 'Vub', 'Vcd', 'Vcs', 'Vcb', 'Vtd', 'Vts', 'Vtb']
        exp_flat = self.V_CKM_exp.flatten()
        
        V_theory, _, _ = self.geometric_ckm_sphere(params)
        theory_flat = V_theory.flatten()
        
        x = np.arange(len(elements))
        width = 0.35
        
        ax2.bar(x - width/2, exp_flat, width, label='Experiment', alpha=0.8)
        ax2.bar(x + width/2, theory_flat, width, label='3D Sphere Model', alpha=0.8)
        
        ax2.set_ylabel('|V|')
        ax2.set_title('CKM Matrix Elements Comparison')
        ax2.set_xticks(x)
        ax2.set_xticklabels(elements, rotation=45)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('ckm_3d_sphere_model.png', dpi=150, bbox_inches='tight')
        print("\n图像已保存: ckm_3d_sphere_model.png")

def main():
    print("="*70)
    print("方向1: CKM矩阵3D球面模型")
    print("="*70)
    
    model = CKM3DSphereModel()
    
    # 拟合
    result = model.fit_parameters()
    
    print(f"\n拟合成功: {result.success}")
    print(f"最小卡方: {result.fun:.4f}")
    
    # 解析参数
    params = result.x
    theta = params[0:12:2]
    phi = params[1:12:2]
    alpha = params[12]
    
    print(f"\n最优参数:")
    quark_names = ['d', 'u', 's', 'c', 'b', 't']
    for i, name in enumerate(quark_names):
        print(f"  {name}: θ = {theta[i]:.3f}, φ = {phi[i]:.3f}")
    print(f"  alpha = {alpha:.3f}")
    
    # 评估
    V_theory, positions, rel_diff = model.evaluate_fit(params)
    
    # 可视化
    model.visualize_3d_sphere(positions)
    
    print("\n" + "="*70)
    print("3D球面模型完成!")
    print("="*70)

if __name__ == "__main__":
    main()
