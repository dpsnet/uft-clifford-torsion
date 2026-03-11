#!/usr/bin/env python3
"""
方向2: 宇宙学常数演化计算
Direction 2: Cosmological Constant Evolution

计算随时间演化的暗能量密度，预测高红移观测偏差
"""

import numpy as np
import matplotlib.pyplot as plt

# 物理常数
M_Planck = 1.22e19  # GeV
H0 = 67.4  # km/s/Mpc (今天哈勃常数)
Omega_Lambda_0 = 0.684  # 今天暗能量密度参数

class LambdaEvolution:
    """宇宙学常数演化计算器"""
    
    def __init__(self, tau_0=1e-4):
        self.tau_0 = tau_0
        self.Lambda_0 = self.calculate_today_lambda()
        
    def calculate_today_lambda(self):
        """
        计算今天的宇宙学常数 (几何起源)
        
        Lambda ~ tau_0^2 * M_Planck^2 * (残余内部空间能量)
        """
        # 今天的残余内部空间能量密度
        # 与tau_0^2成正比
        rho_int_today = self.tau_0**2 * (M_Planck)**4 * 1e-120  # 极度稀释
        
        # 转换为宇宙学常数
        Lambda = 8 * np.pi * rho_int_today / M_Planck**2
        
        return Lambda
    
    def lambda_of_z(self, z):
        """
        计算红移z处的等效宇宙学常数
        
        模型: Lambda(z) = Lambda_0 * [1 + epsilon(z)]
        其中epsilon(z)来自内部空间能量的时变贡献
        """
        # 内部空间能量随红移的演化
        # 早期(z大): 内部空间能量更多，Lambda有效值更大
        # 晚期(z小): 接近今天的值
        
        # 简化模型: epsilon ~ tau_0^2 * ln(1+z)
        epsilon = self.tau_0**2 * np.log(1 + z) * 10
        
        Lambda_z = self.Lambda_0 * (1 + epsilon)
        
        return Lambda_z, epsilon
    
    def distance_modulus(self, z, w=-1):
        """
        计算距离模数 (m-M)
        
        对比: 标准LCDM (w=-1) vs 本理论 (时变Lambda)
        """
        # 简化: 使用积分近似
        # 对于标准LCDM
        c = 3e5  # km/s
        
        # 光度距离 (简化计算)
        # d_L ~ c/H0 * z for z << 1
        # d_L ~ c/H0 * 2 * (1 - 1/sqrt(1+z)) for matter-dominated
        
        d_L_LCDM = (c / H0) * 2 * (1 - 1/np.sqrt(1 + z))
        
        # 本理论: Lambda有效值更大 -> 加速更多 -> 距离更大
        Lambda_z, epsilon = self.lambda_of_z(z)
        
        # 修正因子 (近似)
        correction = 1 + 0.1 * epsilon * np.log(1 + z)
        d_L_theory = d_L_LCDM * correction
        
        # 距离模数
        mu_LCDM = 5 * np.log10(d_L_LCDM) + 25
        mu_theory = 5 * np.log10(d_L_theory) + 25
        
        return mu_LCDM, mu_theory, mu_theory - mu_LCDM
    
    def hubble_parameter(self, z):
        """
        计算哈勃参数 H(z)
        """
        # 标准LCDM
        Omega_m = 0.316
        Omega_L = 0.684
        
        H_LCDM = H0 * np.sqrt(Omega_m * (1 + z)**3 + Omega_L)
        
        # 本理论: 时变Lambda
        Lambda_z, epsilon = self.lambda_of_z(z)
        Omega_L_z = Omega_L * (1 + epsilon)
        
        H_theory = H0 * np.sqrt(Omega_m * (1 + z)**3 + Omega_L_z)
        
        return H_LCDM, H_theory, (H_theory - H_LCDM) / H_LCDM
    
    def plot_evolution(self):
        """绘制宇宙学常数演化"""
        z = np.logspace(-2, 2, 500)  # z from 0.01 to 100
        
        # 计算Lambda(z)
        Lambda_z = []
        epsilon_z = []
        for zi in z:
            L, e = self.lambda_of_z(zi)
            Lambda_z.append(L)
            epsilon_z.append(e)
        
        Lambda_z = np.array(Lambda_z)
        epsilon_z = np.array(epsilon_z)
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. Lambda随红移演化
        axes[0, 0].semilogx(1 + z, Lambda_z / self.Lambda_0, 'b-', linewidth=2)
        axes[0, 0].axhline(1.0, color='r', linestyle='--', label='LCDM (constant)')
        axes[0, 0].set_xlabel('1 + z')
        axes[0, 0].set_ylabel('Lambda(z) / Lambda_0')
        axes[0, 0].set_title('Cosmological Constant Evolution')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 相对偏差 epsilon
        axes[0, 1].semilogx(1 + z, epsilon_z * 100, 'g-', linewidth=2)
        axes[0, 1].axhline(1.0, color='r', linestyle='--', label='1% deviation')
        axes[0, 1].axhline(10.0, color='orange', linestyle='--', label='10% deviation')
        axes[0, 1].set_xlabel('1 + z')
        axes[0, 1].set_ylabel('Deviation (%)')
        axes[0, 1].set_title('Relative Change in Lambda')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 距离模数偏差
        z_mu = np.linspace(0.1, 10, 100)
        delta_mu = []
        for zi in z_mu:
            _, _, dmu = self.distance_modulus(zi)
            delta_mu.append(dmu)
        
        axes[1, 0].plot(z_mu, delta_mu, 'm-', linewidth=2)
        axes[1, 0].axhline(0.1, color='r', linestyle='--', label='0.1 mag (detectable)')
        axes[1, 0].axhline(-0.1, color='r', linestyle='--')
        axes[1, 0].set_xlabel('Redshift z')
        axes[1, 0].set_ylabel('Delta (m-M) (mag)')
        axes[1, 0].set_title('Distance Modulus Difference')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 哈勃参数偏差
        z_H = np.linspace(0.1, 10, 100)
        delta_H = []
        for zi in z_H:
            _, _, dH = self.hubble_parameter(zi)
            delta_H.append(dH * 100)
        
        axes[1, 1].plot(z_H, delta_H, 'c-', linewidth=2)
        axes[1, 1].axhline(1.0, color='r', linestyle='--', label='1% deviation')
        axes[1, 1].axhline(10.0, color='orange', linestyle='--', label='10% deviation')
        axes[1, 1].set_xlabel('Redshift z')
        axes[1, 1].set_ylabel('Delta H / H (%)')
        axes[1, 1].set_title('Hubble Parameter Difference')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('lambda_evolution.png', dpi=150, bbox_inches='tight')
        print("\n图像已保存: lambda_evolution.png")
    
    def check_jwst_observability(self):
        """检查JWST可能观测到的信号"""
        print("\nJWST可观测性分析:")
        print("="*60)
        
        # JWST主要观测红移范围
        z_JWST = [6, 8, 10, 12, 15]
        
        print(f"{'Redshift z':<12} {'Lambda deviation':<20} {'Distance modulus diff':<20}")
        print("-"*60)
        
        detectable = False
        for z in z_JWST:
            _, epsilon = self.lambda_of_z(z)
            _, _, dmu = self.distance_modulus(z)
            
            print(f"{z:<12} {epsilon*100:<20.4f}% {dmu:<20.4f} mag")
            
            if abs(dmu) > 0.1:  # JWST大致灵敏度
                detectable = True
        
        if detectable:
            print("\n✓ JWST可能探测到距离模数偏差")
        else:
            print("\n✗ JWST可能无法探测 (需要更高红移或更高精度)")
        
        return detectable

def main():
    print("="*60)
    print("方向2: 宇宙学常数演化")
    print("="*60)
    
    # 使用参数扫描建议的值
    tau_0 = 1e-5  # 满足原子钟约束且可能被LISA探测
    
    print(f"\n参数: tau_0 = {tau_0}")
    
    calc = LambdaEvolution(tau_0=tau_0)
    
    print(f"今天宇宙学常数: {calc.Lambda_0:.2e}")
    
    # 绘制演化
    calc.plot_evolution()
    
    # JWST可观测性
    calc.check_jwst_observability()
    
    print("\n" + "="*60)
    print("方向2计算完成!")
    print("="*60)

if __name__ == "__main__":
    main()
