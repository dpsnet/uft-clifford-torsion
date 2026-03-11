#!/usr/bin/env python3
"""
方向2详细计算: 非阿贝尔纤维丛CKM模型
Non-Abelian Fiber Bundle Model for CKM Matrix

CKM作为SU(3)主丛上的和乐(holonomy)
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
from scipy.linalg import expm  # 矩阵指数
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# SU(3)生成元 (Gell-Mann矩阵)
T_a = [
    np.array([[0, 1, 0], [1, 0, 0], [0, 0, 0]]) / np.sqrt(2),  # λ1
    np.array([[0, -1j, 0], [1j, 0, 0], [0, 0, 0]]) / np.sqrt(2),  # λ2
    np.array([[1, 0, 0], [0, -1, 0], [0, 0, 0]]) / np.sqrt(2),  # λ3
    np.array([[0, 0, 1], [0, 0, 0], [1, 0, 0]]) / np.sqrt(2),  # λ4
    np.array([[0, 0, -1j], [0, 0, 0], [1j, 0, 0]]) / np.sqrt(2),  # λ5
    np.array([[0, 0, 0], [0, 0, 1], [0, 1, 0]]) / np.sqrt(2),  # λ6
    np.array([[0, 0, 0], [0, 0, -1j], [0, 1j, 0]]) / np.sqrt(2),  # λ7
    np.array([[1, 0, 0], [0, 1, 0], [0, -2, 0]]) / np.sqrt(6),  # λ8
]

class CKMNonAbelianBundle:
    """非阿贝尔纤维丛CKM模型"""
    
    def __init__(self):
        # 实验CKM矩阵 (Wolfenstein近似)
        self.V_CKM_exp = np.array([
            [0.97435, 0.22530, 0.00357],
            [0.22520, 0.97342, 0.04120],
            [0.00874, 0.04080, 0.99905]
        ])
        
        # 检查幺正性
        self.check_unitarity(self.V_CKM_exp, "实验")
        
    def check_unitarity(self, V, name):
        """检查矩阵幺正性"""
        VVdagger = V @ V.conj().T
        identity = np.eye(3)
        deviation = np.max(np.abs(VVdagger - identity))
        print(f"{name}矩阵幺正性偏差: {deviation:.2e}")
        return deviation < 1e-10
    
    def construct_connection(self, A_coeffs):
        """
        构造SU(3)联络
        
        参数: A_coeffs[8] - 8个生成元的系数
        返回: 3x3复矩阵
        """
        A = np.zeros((3, 3), dtype=complex)
        for a in range(8):
            A += A_coeffs[a] * T_a[a]
        return A
    
    def path_ordered_exponential(self, A_list, t_list):
        """
        计算路径有序指数积分
        
        V = P exp(i ∫ A dt) ≈ Π exp(i A(t_i) Δt_i)
        
        参数:
            A_list: 路径上各点的联络列表
            t_list: 对应参数值
        返回:
            3x3和乐矩阵
        """
        V = np.eye(3, dtype=complex)
        
        for i in range(len(A_list) - 1):
            dt = t_list[i+1] - t_list[i]
            A_avg = (A_list[i] + A_list[i+1]) / 2
            # 小步长近似
            V = expm(1j * A_avg * dt) @ V
        
        return V
    
    def geometric_ckm_bundle(self, params):
        """
        基于非阿贝尔纤维丛的CKM模型
        
        参数解释:
        - params[0:8]: d夸克的联络系数
        - params[8:16]: u夸克的联络系数  
        - params[16:24]: s夸克的联络系数
        - params[24:32]: c夸克的联络系数
        - params[32:40]: b夸克的联络系数
        - params[40:48]: t夸克的联络系数
        - params[48]: 路径长度参数
        - params[49]: 整体相位
        
        模型假设:
        1. 三代夸克在SU(3)纤维上有不同"位置"(不同联络)
        2. CKM混合 = 连接down-type和up-type的路径和乐
        """
        n_params_per_quark = 8
        
        # 提取各夸克的联络
        A_d = self.construct_connection(params[0:8])
        A_u = self.construct_connection(params[8:16])
        A_s = self.construct_connection(params[16:24])
        A_c = self.construct_connection(params[24:32])
        A_b = self.construct_connection(params[32:40])
        A_t = self.construct_connection(params[40:48])
        
        path_length = params[48] if len(params) > 48 else 1.0
        global_phase = params[49] if len(params) > 49 else 0.0
        
        # 构造路径上的联络
        # 路径: d -> u (第一列), s -> c (第二列), b -> t (第三列)
        down_quarks = [A_d, A_s, A_b]
        up_quarks = [A_u, A_c, A_t]
        
        V = np.zeros((3, 3), dtype=complex)
        
        for i, A_down in enumerate(down_quarks):
            for j, A_up in enumerate(up_quarks):
                # 构造从down到up的路径
                # 简化: 直线路径插值
                n_steps = 10
                t_list = np.linspace(0, path_length, n_steps)
                A_list = []
                
                for t in t_list:
                    # 线性插值
                    A_t = (1 - t/path_length) * A_down + (t/path_length) * A_up
                    A_list.append(A_t)
                
                # 计算和乐
                V_ij = self.path_ordered_exponential(A_list, t_list)
                
                # 取(0,0)矩阵元作为近似
                V[i, j] = V_ij[0, 0] * np.exp(1j * global_phase * (i + j))
        
        # 单位化 (Gram-Schmidt正交化简化版)
        for i in range(3):
            norm = np.sqrt(np.sum(np.abs(V[i, :])**2))
            if norm > 1e-10:
                V[i, :] /= norm
        
        return np.abs(V), V  # 返回绝对值和复矩阵
    
    def chi_squared(self, params):
        """计算与实验值的卡方偏差"""
        V_abs, V_complex = self.geometric_ckm_bundle(params)
        
        # 计算偏差
        diff = V_abs - self.V_CKM_exp
        chi2 = np.sum(diff**2) * 1000  # 权重因子
        
        # 添加幺正性惩罚
        VVdagger = V_complex @ V_complex.conj().T
        unitarity_penalty = np.sum(np.abs(VVdagger - np.eye(3))**2) * 100
        
        return chi2 + unitarity_penalty
    
    def fit_parameters(self):
        """拟合纤维丛参数"""
        print("拟合非阿贝尔纤维丛模型...")
        print("这可能需要几分钟...")
        
        # 初始猜测 (小随机值)
        np.random.seed(42)
        x0 = np.random.randn(50) * 0.1
        
        # 边界
        bounds = [(-2, 2) for _ in range(50)]
        
        # 分阶段优化
        # 第一阶段: 粗优化
        print("第一阶段: 粗优化...")
        result1 = differential_evolution(
            self.chi_squared,
            bounds,
            seed=42,
            maxiter=500,
            popsize=10,
            workers=-1
        )
        
        print(f"粗优化完成, 卡方: {result1.fun:.4f}")
        
        # 第二阶段: 精细优化
        print("第二阶段: 精细优化...")
        result2 = minimize(
            self.chi_squared,
            result1.x,
            method='L-BFGS-B',
            bounds=bounds,
            options={'maxiter': 1000}
        )
        
        return result2
    
    def evaluate_fit(self, params):
        """评估拟合结果"""
        V_abs, V_complex = self.geometric_ckm_bundle(params)
        
        print("\n实验CKM矩阵:")
        print(self.V_CKM_exp)
        
        print("\n理论CKM矩阵 (非阿贝尔纤维丛):")
        print(V_abs)
        
        print("\n复数矩阵 (相位信息):")
        print(np.angle(V_complex) / np.pi * 180)  # 转换为角度
        
        print("\n偏差:")
        diff = V_abs - self.V_CKM_exp
        print(diff)
        print(f"\n最大偏差: {np.max(np.abs(diff)):.4f}")
        print(f"平均偏差: {np.mean(np.abs(diff)):.4f}")
        
        # 相对偏差
        rel_diff = np.abs(diff) / (self.V_CKM_exp + 1e-10)
        print(f"\n相对偏差 (%):")
        print(rel_diff * 100)
        print(f"最大相对偏差: {np.max(rel_diff)*100:.2f}%")
        print(f"平均相对偏差: {np.mean(rel_diff)*100:.2f}%")
        
        # 检查幺正性
        VVdagger = V_complex @ V_complex.conj().T
        print(f"\n理论矩阵幺正性:")
        print(np.abs(VVdagger))
        
        return V_abs, V_complex, rel_diff
    
    def visualize_bundle_structure(self, params):
        """可视化纤维丛结构"""
        # 提取联络
        n = 8
        A_d = self.construct_connection(params[0:n])
        A_u = self.construct_connection(params[n:2*n])
        A_s = self.construct_connection(params[2*n:3*n])
        A_c = self.construct_connection(params[3*n:4*n])
        A_b = self.construct_connection(params[4*n:5*n])
        A_t = self.construct_connection(params[5*n:6*n])
        
        quark_names = ['d', 'u', 's', 'c', 'b', 't']
        quark_A = [A_d, A_u, A_s, A_c, A_b, A_t]
        
        # 计算特征值 (在SU(3)中的"位置")
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 联络强度对比
        ax1 = axes[0, 0]
        strengths = [np.trace(A @ A.conj().T).real for A in quark_A]
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown']
        ax1.bar(quark_names, strengths, color=colors, alpha=0.7)
        ax1.set_ylabel('|A|²')
        ax1.set_title('Gauge Connection Strength for Each Quark')
        ax1.grid(True, alpha=0.3)
        
        # 2. 生成元分解
        ax2 = axes[0, 1]
        coeffs = np.array([params[i*n:(i+1)*n] for i in range(6)])
        im = ax2.imshow(coeffs, cmap='RdBu', aspect='auto')
        ax2.set_xticks(range(8))
        ax2.set_xticklabels([f'T{a+1}' for a in range(8)])
        ax2.set_yticks(range(6))
        ax2.set_yticklabels(quark_names)
        ax2.set_title('SU(3) Generator Coefficients')
        plt.colorbar(im, ax=ax2)
        
        # 3. 路径示意 (简化3D)
        ax3 = axes[1, 0]
        # 计算"位置": A的特征值实部
        positions = []
        for A in quark_A:
            eigvals = np.linalg.eigvals(A)
            # 取第一个特征值的实部和虚部
            positions.append([eigvals[0].real, eigvals[0].imag])
        positions = np.array(positions)
        
        for i, (pos, name, color) in enumerate(zip(positions, quark_names, colors)):
            ax3.scatter(pos[0], pos[1], c=color, s=200, label=name)
            ax3.annotate(name, (pos[0], pos[1]), fontsize=10)
        
        # 连接线 (d-u, s-c, b-t)
        pairs = [(0, 1), (2, 3), (4, 5)]
        for d_idx, u_idx in pairs:
            ax3.plot([positions[d_idx, 0], positions[u_idx, 0]],
                    [positions[d_idx, 1], positions[u_idx, 1]],
                    'k--', alpha=0.3)
        
        ax3.set_xlabel('Re(λ)')
        ax3.set_ylabel('Im(λ)')
        ax3.set_title('Quark Positions in SU(3) (Eigenvalue Representation)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. CKM矩阵对比热图
        ax4 = axes[1, 1]
        V_abs, _ = self.geometric_ckm_bundle(params)
        diff = np.abs(V_abs - self.V_CKM_exp)
        im = ax4.imshow(diff, cmap='Reds', aspect='auto')
        ax4.set_xticks(range(3))
        ax4.set_yticks(range(3))
        ax4.set_xticklabels(['u', 'c', 't'])
        ax4.set_yticklabels(['d', 's', 'b'])
        ax4.set_title('CKM Deviation Heatmap')
        for i in range(3):
            for j in range(3):
                ax4.text(j, i, f'{diff[i,j]:.4f}', ha='center', va='center')
        plt.colorbar(im, ax=ax4)
        
        plt.tight_layout()
        plt.savefig('ckm_nonabelian_bundle.png', dpi=150, bbox_inches='tight')
        print("\n图像已保存: ckm_nonabelian_bundle.png")

def main():
    print("="*70)
    print("方向2详细计算: 非阿贝尔纤维丛CKM模型")
    print("="*70)
    
    model = CKMNonAbelianBundle()
    
    # 拟合
    result = model.fit_parameters()
    
    print(f"\n拟合成功: {result.success}")
    print(f"最小卡方: {result.fun:.4f}")
    
    # 评估
    V_abs, V_complex, rel_diff = model.evaluate_fit(result.x)
    
    # 可视化
    model.visualize_bundle_structure(result.x)
    
    print("\n" + "="*70)
    print("非阿贝尔纤维丛模型完成!")
    print("="*70)
    
    if np.mean(rel_diff) < 0.05:
        print("✅ 成功! 偏差 < 5%")
    elif np.mean(rel_diff) < 0.10:
        print("⚠️ 改进显著，但仍有~10%偏差")
    else:
        print("⚠️ 需要进一步优化模型")

if __name__ == "__main__":
    main()
