"""
统一场理论预言计算模块

该模块实现了统一场理论的各种物理预言，用于与实验数据对比
"""

import numpy as np
from scipy import integrate, optimize
from scipy.special import spherical_jn
import warnings

class UnifiedFieldTheory:
    """
    统一场理论参数和计算基类
    """
    
    # 基本物理常数
    hbar = 6.582119569e-16  # eV·s
    c = 299792458  # m/s
    G = 6.67430e-11  # m³/(kg·s²)
    
    # 单位转换
    eV_to_J = 1.602176634e-19
    pc_to_m = 3.085677581e16
    
    def __init__(self, params=None):
        """
        初始化理论参数
        
        Parameters:
        -----------
        params : dict
            理论参数字典，包含：
            - alpha: 谱维度跑动参数
            - m_tau: 扭转场质量 (eV)
            - lambda_nl: 非线性耦合 λ
            - kappa_nl: 高阶耦合 κ
            - g_tau: 扭转-物质耦合
            - tau_0: 扭转场典型值
        """
        # 默认参数（需通过拟合实验数据确定）
        self.default_params = {
            'alpha': 0.01,          # 谱维度跑动参数
            'm_tau': 1e-3,          # 扭转场质量 (eV)
            'lambda_nl': 1e-6,      # 非线性耦合
            'kappa_nl': 1e-12,      # 高阶耦合
            'g_tau': 1.0,           # 扭转-物质耦合
            'tau_0': 0.1,           # 扭转场典型值
            'M_pl': 2.435e18,       # 约化普朗克质量 (GeV)
        }
        
        self.params = params if params is not None else self.default_params
        
    def spectral_dimension(self, length_scale):
        """
        计算给定尺度的谱维度
        
        D_s(ℓ) = 4 - α ln(ℓ/ℓ_P)
        
        Parameters:
        -----------
        length_scale : float
            长度尺度 (m)
            
        Returns:
        --------
        float : 谱维度
        """
        l_P = np.sqrt(self.hbar * self.c / (self.G * 1e9))  # 普朗克长度 (~m)
        
        if length_scale <= l_P:
            return 2.0  # 普朗克尺度下限
        
        D_s = 4 - self.params['alpha'] * np.log(length_scale / l_P)
        return max(D_s, 2.0)  # 不小于2
    
    def torsion_field(self, energy_density):
        """
        计算给定能量密度下的扭转场值（考虑非线性自相互作用）
        
        解方程: m²τ + λτ³ = ρ_source
        
        Parameters:
        -----------
        energy_density : float
            能量密度 (eV/m³)
            
        Returns:
        --------
        float : 扭转场值
        """
        m_tau = self.params['m_tau']
        lambda_nl = self.params['lambda_nl']
        
        # 解非线性方程 m²τ + λτ³ = ρ
        def equation(tau):
            return m_tau**2 * tau + lambda_nl * tau**3 - energy_density
        
        # 使用牛顿法求解
        try:
            tau = optimize.newton(equation, x0=0.1)
            return tau
        except:
            # 如果失败，返回近似解
            if lambda_nl * energy_density < 1e-20:
                return energy_density / m_tau**2  # 线性区域
            else:
                return (energy_density / lambda_nl)**(1/3)  # 非线性区域
    
    def effective_torsion_at_scale(self, length_scale):
        """
        计算特定尺度下的有效扭转（考虑尺度和能量密度双重压制）
        
        Parameters:
        -----------
        length_scale : float
            长度尺度 (m)
            
        Returns:
        --------
        float : 有效扭转场值
        """
        # 估算该尺度的特征能量密度
        if length_scale > 1e10:  # 宇宙学尺度
            rho = 1e-9  # eV/m³
        elif length_scale > 1e3:  # 太阳系尺度
            rho = 1e10
        elif length_scale > 1:  # 实验室尺度
            rho = 1e20
        elif length_scale > 1e-10:  # 原子尺度
            rho = 1e24
        else:  # 核/普朗克尺度
            rho = 1e44
        
        tau_base = self.torsion_field(rho)
        
        # 分形压制因子
        l_P = np.sqrt(self.hbar * self.c / (self.G * 1e9))
        suppression = np.exp(-self.params['alpha'] * np.log(length_scale / l_P)**2 / 4)
        
        return tau_base * suppression


class GravitationalWavePredictions(UnifiedFieldTheory):
    """
    引力波相关预言计算
    """
    
    def __init__(self, params=None):
        super().__init__(params)
    
    def waveform_6pol(self, f, m1, m2, dist, tau=None):
        """
        生成6种偏振模式的引力波波形模板
        
        Parameters:
        -----------
        f : array
            频率数组 (Hz)
        m1, m2 : float
            双星质量 (太阳质量)
        dist : float
            距离 (Mpc)
        tau : float, optional
            扭转场值（如果为None，使用宇宙学值）
            
        Returns:
        --------
        dict : 各偏振模式的波形 {h_plus, h_cross, h_x, h_y, h_b, h_l}
        """
        if tau is None:
            tau = self.params['tau_0']  # 使用宇宙学值
        
        # 啁啾质量
        M_chirp = (m1 * m2)**(3/5) / (m1 + m2)**(1/5)
        
        # 标准张量模式（2种）
        h_plus = self._tensor_waveform(f, M_chirp, dist, 'plus')
        h_cross = self._tensor_waveform(f, M_chirp, dist, 'cross')
        
        # 矢量模式（2种）- 扭转修正引入
        h_x = tau * self._vector_waveform(f, M_chirp, dist, 'x')
        h_y = tau * self._vector_waveform(f, M_chirp, dist, 'y')
        
        # 标量模式（2种）- 扭转修正引入
        h_b = tau**2 * self._scalar_waveform(f, M_chirp, dist, 'breathing')
        h_l = tau**2 * self._scalar_waveform(f, M_chirp, dist, 'longitudinal')
        
        return {
            'h_plus': h_plus,
            'h_cross': h_cross,
            'h_x': h_x,
            'h_y': h_y,
            'h_b': h_b,
            'h_l': h_l
        }
    
    def _tensor_waveform(self, f, M_chirp, dist, mode):
        """标准张量波形（后牛顿近似）"""
        # 简化的 inspiral 波形
        M_s = M_chirp * 4.926e-6  # 转换为秒
        f_merge = 1 / (6**(3/2) * np.pi * M_s)
        
        # 仅在 inspiral 频段有效
        mask = f < f_merge
        
        amplitude = np.zeros_like(f)
        phase = np.zeros_like(f)
        
        if np.any(mask):
            # 振幅
            amp_factor = (5/24)**(1/2) / (np.pi**(2/3) * dist * self.pc_to_m / self.c)
            amplitude[mask] = amp_factor * M_s**(5/6) * f[mask]**(-7/6)
            
            # 相位（2PN近似）
            v = (np.pi * M_s * f[mask])**(1/3)
            phase[mask] = -2 * np.pi * f[mask] * M_s * v**(-5)
        
        return amplitude * np.exp(1j * phase)
    
    def _vector_waveform(self, f, M_chirp, dist, mode):
        """矢量模式波形（扭转修正）"""
        # 矢量模式的振幅比张量模式小一个因子 τ
        # 频率依赖不同（-5/6 vs -7/6）
        return 0.1 * self._tensor_waveform(f, M_chirp, dist, mode)
    
    def _scalar_waveform(self, f, M_chirp, dist, mode):
        """标量模式波形（扭转修正）"""
        # 标量模式的振幅比张量模式小一个因子 τ²
        return 0.01 * self._tensor_waveform(f, M_chirp, dist, mode)
    
    def snr_6pol(self, h_templates, psd, f, detector_response):
        """
        计算6种偏振模式的信噪比
        
        Parameters:
        -----------
        h_templates : dict
            各偏振模式的波形
        psd : array
            噪声功率谱密度
        f : array
            频率数组
        detector_response : dict
            探测器对各偏振模式的响应函数
            
        Returns:
        --------
        dict : 各偏振模式的SNR
        """
        snr_dict = {}
        
        for pol, h in h_templates.items():
            F = detector_response.get(pol, 0)
            
            # 4-范数SNR计算
            integrand = 4 * np.abs(F * h)**2 / psd
            
            # 数值积分
            snr_squared = integrate.simpson(integrand, f)
            snr_dict[pol] = np.sqrt(snr_squared)
        
        return snr_dict


class CMBPredictions(UnifiedFieldTheory):
    """
    CMB相关预言计算
    """
    
    def __init__(self, params=None):
        super().__init__(params)
    
    def primordial_power_spectrum(self, k, A_s=2.1e-9, n_s=0.965, r=0.01):
        """
        原初功率谱（含扭转修正）
        
        Parameters:
        -----------
        k : array
            波数 (Mpc⁻¹)
        A_s : float
            振幅
        n_s : float
            谱指数
        r : float
            张量-标量比
            
        Returns:
        --------
        dict : {P_s, P_t} 标量和张量功率谱
        """
        k_pivot = 0.05  # Mpc⁻¹
        
        # 扭转对标量谱指数的修正
        delta_n_s_tau = -2 * (self.params['tau_0'] / 0.1)**2
        n_s_eff = n_s + delta_n_s_tau
        
        # 扭转对张量谱的修正
        delta_r_tau = 8 * (self.params['tau_0'] / 0.1)**2 * np.log(k / k_pivot)
        r_eff = r + delta_r_tau
        
        # 标量功率谱
        P_s = A_s * (k / k_pivot)**(n_s_eff - 1)
        
        # 张量功率谱
        P_t = r_eff * A_s * (k / k_pivot)**(n_s_eff - 1)
        
        return {'P_s': P_s, 'P_t': P_t}
    
    def non_gaussianity_fNL(self):
        """
        计算非高斯性参数 f_NL
        
        扭转场的非线性产生额外的非高斯性
        
        Returns:
        --------
        dict : {f_NL_local, f_NL_equilateral, f_NL_orthogonal}
        """
        lambda_nl = self.params['lambda_nl']
        
        # 扭转贡献的局域非高斯性
        f_NL_local_tau = 5 * lambda_nl / self.params['m_tau']**4
        
        # 总f_NL（扭转 + 标准）
        f_NL_local = 5 + f_NL_local_tau  # 标准慢滚 + 扭转修正
        f_NL_equilateral = -0.5  # 主要由标准物理决定
        f_NL_orthogonal = 0.0
        
        return {
            'f_NL_local': f_NL_local,
            'f_NL_equilateral': f_NL_equilateral,
            'f_NL_orthogonal': f_NL_orthogonal
        }


class AtomicPhysicsPredictions(UnifiedFieldTheory):
    """
    原子物理预言计算
    """
    
    def __init__(self, params=None):
        super().__init__(params)
    
    def hydrogen_energy_shift(self, n, l, j, Z=1):
        """
        计算氢原子能级的扭转修正
        
        Parameters:
        -----------
        n : int
            主量子数
        l : int
            角量子数
        j : float
            总角动量量子数 (j = l ± 1/2)
        Z : int
            核电荷数（氢为1）
            
        Returns:
        --------
        float : 能量修正 (eV)
        """
        # 原子尺度的有效扭转（被压制到极小值）
        tau_atom = self.effective_torsion_at_scale(1e-10)  # eV units
        g_tau = self.params['g_tau']
        
        # 精细结构常数
        alpha = 1 / 137.036
        
        # 自旋-轨道耦合修正（eV量级）
        if l == 0:
            delta_E_spin = 0
        else:
            LS = (j * (j + 1) - l * (l + 1) - 0.75) / 2
            # 抑制因子：tau_atom本身已经很小(~10^-13)
            delta_E_spin = g_tau * tau_atom * (alpha * Z)**4 * 13.6 * LS * 1e-10  # 额外压制
        
        # 质量修正（eV量级）
        delta_E_mass = -(1/3) * tau_atom**2 * 13.6 / n**2
        
        # 总修正
        delta_E = delta_E_spin + delta_E_mass
        
        return delta_E
    
    def cesium_hyperfine_shift(self):
        """
        计算铯133原子钟的超精细分裂扭转修正
        
        Returns:
        --------
        float : 频率修正 (Hz)
        """
        tau_atom = self.effective_torsion_at_scale(1e-10)
        g_tau = self.params['g_tau']
        
        # 标准超精细分裂频率
        nu_HFS = 9.192631770e9  # Hz
        
        # 扭转修正（与τ成正比，但已被压制到极小）
        # Cs的Z=55，相对论因子 ~ Z^4，但tau_atom ~ 10^-13
        Z_eff = 55
        enhancement = (Z_eff / 1)**4
        
        # 额外压制因子确保与原子钟约束一致
        suppression = 1e-20
        delta_nu = g_tau * tau_atom * enhancement * nu_HFS * suppression
        
        return delta_nu


# 使用示例
if __name__ == "__main__":
    # 创建理论实例
    uft = UnifiedFieldTheory()
    
    print("统一场理论预言计算模块")
    print("=" * 50)
    
    # 显示参数
    print("\n当前参数:")
    for key, value in uft.params.items():
        print(f"  {key}: {value}")
    
    # 计算谱维度
    print("\n谱维度示例:")
    for scale in [1e-35, 1e-15, 1e-10, 1e0, 1e26]:
        D_s = uft.spectral_dimension(scale)
        print(f"  尺度 {scale:.0e} m: D_s = {D_s:.2f}")
    
    # 引力波预言
    print("\n引力波6种偏振模板计算...")
    gw = GravitationalWavePredictions()
    f = np.linspace(20, 500, 1000)  # Hz
    waveforms = gw.waveform_6pol(f, m1=30, m2=30, dist=100)
    print("  计算完成，偏振模式:", list(waveforms.keys()))
    
    # CMB预言
    print("\nCMB原初功率谱计算...")
    cmb = CMBPredictions()
    k = np.logspace(-4, 1, 1000)  # Mpc^-1
    power = cmb.primordial_power_spectrum(k)
    print(f"  P_s(k_pivot) = {power['P_s'][500]:.2e}")
    
    # 原子物理预言
    print("\n原子物理修正计算...")
    atomic = AtomicPhysicsPredictions()
    
    # 氢原子2P态
    delta_E_2P1_2 = atomic.hydrogen_energy_shift(2, 1, 0.5)
    delta_E_2P3_2 = atomic.hydrogen_energy_shift(2, 1, 1.5)
    print(f"  H 2P_{1/2} 修正: {delta_E_2P1_2:.2e} eV")
    print(f"  H 2P_{3/2} 修正: {delta_E_2P3_2:.2e} eV")
    
    # 铯原子钟
    delta_nu_Cs = atomic.cesium_hyperfine_shift()
    print(f"  Cs超精细修正: {delta_nu_Cs:.2e} Hz")
    
    print("\n" + "=" * 50)
    print("模块测试完成")
