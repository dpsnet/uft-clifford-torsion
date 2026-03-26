#!/usr/bin/env python3
"""
方向2深化 v2: 修复数值稳定性问题
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
from scipy.linalg import expm
import matplotlib.pyplot as plt

# SU(3)生成元
T_a = [
    np.array([[0, 1, 0], [1, 0, 0], [0, 0, 0]]) / np.sqrt(2),
    np.array([[0, -1j, 0], [1j, 0, 0], [0, 0, 0]]) / np.sqrt(2),
    np.array([[1, 0, 0], [0, -1, 0], [0, 0, 0]]) / np.sqrt(2),
    np.array([[0, 0, 1], [0, 0, 0], [1, 0, 0]]) / np.sqrt(2),
    np.array([[0, 0, -1j], [0, 0, 0], [1j, 0, 0]]) / np.sqrt(2),
    np.array([[0, 0, 0], [0, 0, 1], [0, 1, 0]]) / np.sqrt(2),
    np.array([[0, 0, 0], [0, 0, -1j], [0, 1j, 0]]) / np.sqrt(2),
    np.array([[1, 0, 0], [0, 1, 0], [0, -2, 0]]) / np.sqrt(6),
]

class CKMOptimizer:
    def __init__(self):
        self.V_exp = np.array([
            [0.97435, 0.22530, 0.00357],
            [0.22520, 0.97342, 0.04120],
            [0.00874, 0.04080, 0.99905]
        ])
    
    def build_A(self, coeffs):
        """构造联络"""
        A = np.zeros((3, 3), dtype=complex)
        for a in range(8):
            A += coeffs[a] * T_a[a]
        return A
    
    def safe_unitary(self, V):
        """安全幺正化 (修复除以零问题)"""
        # QR分解
        Q, R = np.linalg.qr(V)
        # 调整相位
        diag_R = np.diag(R)
        # 避免除以零
        phases = np.where(np.abs(diag_R) > 1e-10, 
                         diag_R / np.abs(diag_R), 
                         1.0)
        U = Q @ np.diag(np.conj(phases))
        return U
    
    def holonomy(self, A1, A2, steps=10):
        """路径和乐"""
        dt = 1.0 / steps
        V = np.eye(3, dtype=complex)
        for i in range(steps):
            t = (i + 0.5) * dt
            A_t = (1 - t) * A1 + t * A2
            V = expm(1j * A_t * dt) @ V
        return V
    
    def ckm_from_params(self, params):
        """从参数构建CKM"""
        # 6个夸克，每个8个系数
        A_list = [self.build_A(params[i*8:(i+1)*8]) for i in range(6)]
        
        down_idx = [0, 2, 4]  # d, s, b
        up_idx = [1, 3, 5]    # u, c, t
        
        V = np.zeros((3, 3), dtype=complex)
        for i, d in enumerate(down_idx):
            for j, u in enumerate(up_idx):
                h = self.holonomy(A_list[d], A_list[u])
                V[i, j] = h[0, 0]
        
        return self.safe_unitary(V)
    
    def loss(self, params):
        """损失函数"""
        try:
            V = self.ckm_from_params(params)
            V_abs = np.abs(V)
            diff = V_abs - self.V_exp
            return np.sum(diff**2) * 1000
        except:
            return 1e10
    
    def optimize(self):
        """优化"""
        print("开始优化...")
        
        # 减少参数: 每个夸克只用3个主要生成元
        # 简化模型: 24参数而非48
        bounds = [(-1, 1) for _ in range(48)]
        
        result = differential_evolution(
            self.loss,
            bounds,
            seed=42,
            maxiter=500,
            popsize=10,
            polish=True,
            tol=1e-6
        )
        
        return result
    
    def analyze(self, params):
        """分析结果"""
        V = self.ckm_from_params(params)
        V_abs = np.abs(V)
        
        print("\n=== 结果分析 ===")
        print("实验值:")
        print(self.V_exp)
        print("\n理论值:")
        print(V_abs)
        
        diff = V_abs - self.V_exp
        print("\n偏差:")
        print(diff)
        
        print(f"\n最大偏差: {np.max(np.abs(diff)):.6f}")
        print(f"平均偏差: {np.mean(np.abs(diff)):.6f}")
        print(f"相对偏差: {np.mean(np.abs(diff)/self.V_exp)*100:.2f}%")
        
        return V_abs

def main():
    opt = CKMOptimizer()
    result = opt.optimize()
    
    print(f"\n优化完成!")
    print(f"最终损失: {result.fun:.6f}")
    print(f"迭代次数: {result.nit}")
    
    V_final = opt.analyze(result.x)
    
    # 保存结果
    np.save('ckm_direction2_result.npy', {'params': result.x, 'V': V_final})
    print("\n结果已保存: ckm_direction2_result.npy")

if __name__ == "__main__":
    main()
