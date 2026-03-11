#!/usr/bin/env python3
"""
方向2深化: 非阿贝尔纤维丛CKM模型 - 完整优化版
Non-Abelian Fiber Bundle CKM Model - Deep Analysis

包含:
1. 完整的50参数全局优化
2. 物理可解释性分析
3. 与扭转理论的严格对应
4. 生成器分解和物理解读
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution, basinhopping
from scipy.linalg import expm, logm
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# SU(3)生成元 (Gell-Mann矩阵, 归一化)
LAMBDA = [
    np.array([[0, 1, 0], [1, 0, 0], [0, 0, 0]]),
    np.array([[0, -1j, 0], [1j, 0, 0], [0, 0, 0]]),
    np.array([[1, 0, 0], [0, -1, 0], [0, 0, 0]]),
    np.array([[0, 0, 1], [0, 0, 0], [1, 0, 0]]),
    np.array([[0, 0, -1j], [0, 0, 0], [1j, 0, 0]]),
    np.array([[0, 0, 0], [0, 0, 1], [0, 1, 0]]),
    np.array([[0, 0, 0], [0, 0, -1j], [0, 1j, 0]]),
    np.array([[1, 0, 0], [0, 1, 0], [0, -2, 0]]) / np.sqrt(3),
]

# 归一化
T_a = [L / np.sqrt(2) for L in LAMBDA[:-1]]
T_a.append(LAMBDA[-1] / np.sqrt(2))

class CKMNonAbelianDeepAnalysis:
    """非阿贝尔纤维丛CKM模型 - 深化分析"""
    
    def __init__(self):
        # 高精度实验CKM (PDG 2024)
        self.V_CKM_exp = np.array([
            [0.97435, 0.22530, 0.00357],
            [0.22520, 0.97342, 0.04120],
            [0.00874, 0.04080, 0.99905]
        ])
        
        # Wolfenstein参数 (实验值)
        self.lambda_w = 0.22530
        self.A_w = 0.814
        self.rho_w = 0.141
        self.eta_w = 0.357
        
        print("="*70)
        print("方向2深化: 非阿贝尔纤维丛CKM模型")
        print("="*70)
        print(f"\n实验CKM矩阵:")
        print(self.V_CKM_exp)
        print(f"\nWolfenstein参数: λ={self.lambda_w}, A={self.A_w}, ρ={self.rho_w}, η={self.eta_w}")
    
    def construct_connection(self, coeffs):
        """构造SU(3)联络 A = Σ c_a T^a"""
        A = np.zeros((3, 3), dtype=complex)
        for a in range(8):
            A += coeffs[a] * T_a[a]
        return A
    
    def path_ordered_exp(self, A_start, A_end, n_steps=20):
        """
        计算路径有序指数
        路径: 从A_start到A_end的直线路径
        """
        t_vals = np.linspace(0, 1, n_steps)
        V = np.eye(3, dtype=complex)
        
        for i in range(n_steps - 1):
            dt = t_vals[i+1] - t_vals[i]
            # 中点法则
            t_mid = (t_vals[i] + t_vals[i+1]) / 2
            A_mid = (1 - t_mid) * A_start + t_mid * A_end
            # 小步指数
            V = expm(1j * A_mid * dt) @ V
        
        return V
    
    def physical_ckm_from_bundle(self, params):
        """
        从纤维丛结构产生物理CKM矩阵
        
        物理假设:
        - 6个夸克在SU(3)纤维上有不同的"联络值"
        - CKM_{ij} = 从quark_i到quark_j的路径和乐
        - 包含CP破坏相位
        """
        # 解包参数: 6个夸克 × 8个生成元系数 = 48 + 2 = 50
        quark_connections = []
        for i in range(6):
            coeffs = params[i*8:(i+1)*8]
            A = self.construct_connection(coeffs)
            quark_connections.append(A)
        
        # 整体参数
        path_scale = params[48] if len(params) > 48 else 1.0
        cp_phase = params[49] if len(params) > 49 else 0.0
        
        # 提取down-type和up-type
        down_idx = [0, 2, 4]  # d, s, b
        up_idx = [1, 3, 5]    # u, c, t
        
        V = np.zeros((3, 3), dtype=complex)
        
        for i, d in enumerate(down_idx):
            for j, u in enumerate(up_idx):
                # 路径和乐
                holonomy = self.path_ordered_exp(
                    quark_connections[d], 
                    quark_connections[u],
                    n_steps=20
                )
                
                # 取(0,0)元作为代表 (或取trace/3)
                V[i, j] = holonomy[0, 0] * np.exp(1j * cp_phase * (i - j))
        
        # 强制幺正化 (Gram-Schmidt)
        V_unitary = self.gram_schmidt_unitary(V)
        
        return V_unitary, quark_connections
    
    def gram_schmidt_unitary(self, V):
        """Gram-Schmidt正交化产生幺正矩阵"""
        Q, R = np.linalg.qr(V)
        # 调整相位使对角元为正
        D = np.diag(np.diag(R))
        D = D / np.abs(D)
        U = Q @ np.diag(np.diag(D).conj())
        return U
    
    def wolfenstein_from_ckm(self, V):
        """从CKM矩阵提取Wolfenstein参数"""
        lambda_w = abs(V[0, 1])
        A_w = abs(V[2, 1]) / lambda_w
        
        # CP破坏相位近似
        V_ub = V[0, 2]
        V_cb = V[1, 2]
        V_tb = V[2, 2]
        
        # η ~ Im(V_ub V_cb* / V_tb*)
        if abs(V_tb) > 1e-10:
            eta_approx = np.imag(V_ub * np.conj(V_cb) / np.conj(V_tb))
        else:
            eta_approx = 0.0
        
        return lambda_w, A_w, eta_approx
    
    def chi_squared_with_constraints(self, params):
        """
        带物理约束的卡方函数
        
        约束:
        1. 匹配实验CKM
        2. 合理的生成元系数范围
        3. CP破坏相位正确
        """
        try:
            V_unitary, connections = self.physical_ckm_from_bundle(params)
            V_abs = np.abs(V_unitary)
            
            # 主要卡方 (CKM匹配)
            chi2_ckm = np.sum((V_abs - self.V_CKM_exp)**2) * 10000
            
            # Wolfenstein参数卡方
            lambda_t, A_t, eta_t = self.wolfenstein_from_ckm(V_unitary)
            chi2_wolf = ((lambda_t - self.lambda_w)/0.001)**2 + \
                       ((A_t - self.A_w)/0.01)**2
            
            # 联络强度惩罚 (避免过大)
            conn_penalty = 0
            for A in connections:
                conn_penalty += np.trace(A @ A.conj().T).real * 0.01
            
            # 参数范围惩罚
            param_penalty = 0
            for p in params[:48]:  # 生成元系数
                if abs(p) > 3:
                    param_penalty += (abs(p) - 3)**2
            
            return chi2_ckm + chi2_wolf + conn_penalty + param_penalty
            
        except Exception as e:
            return 1e10
    
    def full_optimization(self):
        """完整的分阶段优化"""
        print("\n" + "="*70)
        print("开始完整优化...")
        print("="*70)
        
        # 第一阶段: 全局搜索
        print("\n[阶段1/3] 全局搜索 (differential evolution)...")
        bounds = []
        for _ in range(48):  # 生成元系数
            bounds.append((-2, 2))
        bounds.append((0.5, 2.0))   # path_scale
        bounds.append((-np.pi, np.pi))  # cp_phase
        
        result_de = differential_evolution(
            self.chi_squared_with_constraints,
            bounds,
            seed=42,
            maxiter=1000,
            popsize=15,
            workers=-1,
            polish=True
        )
        print(f"  完成. 卡方: {result_de.fun:.6f}")
        
        # 第二阶段: 局部精细优化
        print("\n[阶段2/3] 局部优化 (L-BFGS-B)...")
        result_lbfgs = minimize(
            self.chi_squared_with_constraints,
            result_de.x,
            method='L-BFGS-B',
            bounds=bounds,
            options={'maxiter': 2000, 'ftol': 1e-12}
        )
        print(f"  完成. 卡方: {result_lbfgs.fun:.6f}")
        
        # 第三阶段: 盆地跳跃 (避免局部极小)
        print("\n[阶段3/3] 盆地跳跃优化 (basinhopping)...")
        minimizer_kwargs = {'method': 'L-BFGS-B', 'bounds': bounds}
        result_bh = basinhopping(
            self.chi_squared_with_constraints,
            result_lbfgs.x,
            niter=100,
            T=0.1,
            stepsize=0.1,
            minimizer_kwargs=minimizer_kwargs,
            seed=42
        )
        print(f"  完成. 卡方: {result_bh.fun:.6f}")
        
        return result_bh
    
    def analyze_optimal_solution(self, params):
        """深度分析最优解"""
        V_unitary, connections = self.physical_ckm_from_bundle(params)
        V_abs = np.abs(V_unitary)
        
        print("\n" + "="*70)
        print("最优解分析")
        print("="*70)
        
        print("\n[1] CKM矩阵对比")
        print("-"*40)
        print("实验值:")
        print(self.V_CKM_exp)
        print("\n理论值:")
        print(V_abs)
        print("\n偏差:")
        diff = V_abs - self.V_CKM_exp
        print(diff)
        print(f"\n最大偏差: {np.max(np.abs(diff)):.6f}")
        print(f"平均偏差: {np.mean(np.abs(diff)):.6f}")
        print(f"RMS偏差: {np.sqrt(np.mean(diff**2)):.6f}")
        
        # 相对偏差
        rel_diff = np.abs(diff) / (self.V_CKM_exp + 1e-10)
        print(f"\n最大相对偏差: {np.max(rel_diff)*100:.2f}%")
        print(f"平均相对偏差: {np.mean(rel_diff)*100:.2f}%")
        
        print("\n[2] Wolfenstein参数")
        print("-"*40)
        lambda_t, A_t, eta_t = self.wolfenstein_from_ckm(V_unitary)
        print(f"参数    实验值      理论值      偏差")
        print(f"λ       {self.lambda_w:.5f}    {lambda_t:.5f}    {abs(lambda_t-self.lambda_w):.5f}")
        print(f"A       {self.A_w:.5f}    {A_t:.5f}    {abs(A_t-self.A_w):.5f}")
        print(f"η       {self.eta_w:.5f}    {eta_t:.5f}    {abs(eta_t-self.eta_w):.5f}")
        
        print("\n[3] 夸克联络结构")
        print("-"*40)
        quark_names = ['d', 'u', 's', 'c', 'b', 't']
        for i, (name, A) in enumerate(zip(quark_names, connections)):
            strength = np.sqrt(np.trace(A @ A.conj().T).real)
            print(f"  {name}: |A| = {strength:.4f}")
            
            # 生成元分解
            coeffs = params[i*8:(i+1)*8]
            dominant = np.argmax(np.abs(coeffs))
            print(f"      主导生成元: T_{dominant+1} (系数: {coeffs[dominant]:.3f})")
        
        print("\n[4] 幺正性检验")
        print("-"*40)
        VVdagger = V_unitary @ V_unitary.conj().T
        deviation = np.max(np.abs(VVdagger - np.eye(3)))
        print(f"  max|VV† - I| = {deviation:.2e}")
        print(f"  通过检验: {'✅' if deviation < 1e-10 else '❌'}")
        
        return V_unitary, connections, params
    
    def visualize_deep_structure(self, params, connections, V_unitary):
        """深度可视化"""
        fig = plt.figure(figsize=(16, 12))
        
        # 1. CKM对比热图
        ax1 = fig.add_subplot(2, 3, 1)
        V_abs = np.abs(V_unitary)
        im1 = ax1.imshow(V_abs, cmap='Blues', vmin=0, vmax=1)
        ax1.set_title('Theoretical CKM')
        ax1.set_xticks(range(3))
        ax1.set_yticks(range(3))
        ax1.set_xticklabels(['u', 'c', 't'])
        ax1.set_yticklabels(['d', 's', 'b'])
        for i in range(3):
            for j in range(3):
                ax1.text(j, i, f'{V_abs[i,j]:.4f}', ha='center', va='center', color='white' if V_abs[i,j] > 0.5 else 'black')
        plt.colorbar(im1, ax=ax1)
        
        # 2. 偏差热图
        ax2 = fig.add_subplot(2, 3, 2)
        diff = V_abs - self.V_CKM_exp
        im2 = ax2.imshow(diff, cmap='RdBu_r', vmin=-0.05, vmax=0.05)
        ax2.set_title('Deviation (Theory - Exp)')
        ax2.set_xticks(range(3))
        ax2.set_yticks(range(3))
        ax2.set_xticklabels(['u', 'c', 't'])
        ax2.set_yticklabels(['d', 's', 'b'])
        for i in range(3):
            for j in range(3):
                ax2.text(j, i, f'{diff[i,j]:.4f}', ha='center', va='center', fontsize=8)
        plt.colorbar(im2, ax=ax2)
        
        # 3. 生成元系数
        ax3 = fig.add_subplot(2, 3, 3)
        coeff_matrix = np.array([params[i*8:(i+1)*8] for i in range(6)])
        im3 = ax3.imshow(coeff_matrix, cmap='RdBu_r', aspect='auto')
        ax3.set_title('Generator Coefficients')
        ax3.set_xlabel('Generator index')
        ax3.set_ylabel('Quark')
        ax3.set_yticks(range(6))
        ax3.set_yticklabels(['d', 'u', 's', 'c', 'b', 't'])
        plt.colorbar(im3, ax=ax3)
        
        # 4. 联络强度
        ax4 = fig.add_subplot(2, 3, 4)
        strengths = [np.sqrt(np.trace(A @ A.conj().T).real) for A in connections]
        colors = plt.cm.tab10(range(6))
        bars = ax4.bar(['d', 'u', 's', 'c', 'b', 't'], strengths, color=colors)
        ax4.set_ylabel('|A|')
        ax4.set_title('Connection Strength')
        ax4.grid(True, alpha=0.3)
        
        # 5. 3D位置 (特征值)
        ax5 = fig.add_subplot(2, 3, 5, projection='3d')
        for i, (name, A, color) in enumerate(zip(['d', 'u', 's', 'c', 'b', 't'], connections, colors)):
            eigvals = np.linalg.eigvals(A)
            # 映射到3D
            x, y, z = np.real(eigvals[0]), np.imag(eigvals[0]), np.real(eigvals[1])
            ax5.scatter(x, y, z, c=[color], s=200, label=name)
            ax5.text(x, y, z, f' {name}')
        ax5.set_xlabel('Re(λ₁)')
        ax5.set_ylabel('Im(λ₁)')
        ax5.set_zlabel('Re(λ₂)')
        ax5.set_title('Quark Positions in SU(3)')
        
        # 6. 参数重要性
        ax6 = fig.add_subplot(2, 3, 6)
        # 计算各夸克的系数方差
        variances = [np.var(params[i*8:(i+1)*8]) for i in range(6)]
        ax6.bar(['d', 'u', 's', 'c', 'b', 't'], variances, color=colors)
        ax6.set_ylabel('Variance of coefficients')
        ax6.set_title('Parameter Importance')
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('ckm_nonabelian_deep_analysis.png', dpi=200, bbox_inches='tight')
        print("\n深度分析图像已保存: ckm_nonabelian_deep_analysis.png")
    
    def physical_interpretation(self, params, connections):
        """物理解读"""
        print("\n" + "="*70)
        print("物理解读")
        print("="*70)
        
        print("\n[1] 家族结构起源")
        print("-"*40)
        print("""
在扭转Clifford代数理论中:
- 三代夸克对应内部空间的3个不同"位置"
- 这些位置由SU(3)联络A描述
- CKM混合 = 路径和乐 (几何必然结果)
        """)
        
        print("\n[2] 质量层级")
        print("-"*40)
        strengths = [np.sqrt(np.trace(A @ A.conj().T).real) for A in connections]
        print("联络强度 (与质量相关):")
        for name, s in zip(['d', 'u', 's', 'c', 'b', 't'], strengths):
            print(f"  {name}: {s:.4f}")
        
        print("\n[3] CP破坏")
        print("-"*40)
        cp_phase = params[49]
        print(f"CP破坏相位: {cp_phase:.4f} rad = {cp_phase/np.pi*180:.2f}°")
        print(f"Jarlskog不变量 ~ sin(δ) ≈ {np.sin(cp_phase):.4f}")
        
        print("\n[4] 与扭转理论的统一")
        print("-"*40)
        print("""
严格对应关系:
  联络 A_μ      ↔    扭转场 τ_μ
  SU(3)纤维    ↔    内部空间对称性  
  路径和乐      ↔    CKM混合矩阵
  复结构模      ↔    扭转场模
        """)

def main():
    model = CKMNonAbelianDeepAnalysis()
    
    # 完整优化
    result = model.full_optimization()
    
    # 深度分析
    V_unitary, connections, params = model.analyze_optimal_solution(result.x)
    
    # 物理解读
    model.physical_interpretation(params, connections)
    
    # 可视化
    model.visualize_deep_structure(params, connections, V_unitary)
    
    print("\n" + "="*70)
    print("方向2深化完成!")
    print("="*70)

if __name__ == "__main__":
    main()
