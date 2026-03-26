#!/usr/bin/env python3
"""
TNN旋转球谱维流模拟
验证双向谱维流假设

目标: 观察能量输入对拓扑结构谱维分布的影响
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, List
import json

@dataclass
class TNNSphere:
    """TNN拓扑球 - 模拟旋转小球的几何结构"""
    n_nodes: int = 100  # 拓扑节点数
    dimension: int = 10  # 总维度
    tau_0: float = 0.005  # 特征扭转强度
    
    def __post_init__(self):
        # 初始化拓扑连接
        # 外空间: 4维 (3空间 + 1时间)
        # 内空间: 6维补充
        self.external_dim = 4
        self.internal_dim = 6
        
        # 初始化节点位置 (球坐标)
        self.theta = np.linspace(0, np.pi, self.n_nodes)
        self.phi = np.linspace(0, 2*np.pi, self.n_nodes)
        
        # 扭转场强度 (初始)
        self.torsion = np.ones(self.n_nodes) * self.tau_0
        
        # 能量分布
        self.energy = np.zeros(self.n_nodes)
        
        # 谱维分布
        self.d_s_external = np.ones(self.n_nodes) * 4.0
        self.d_s_internal = np.ones(self.n_nodes) * 4.0
        
    def inject_energy(self, energy_input: float, mode: str = "uniform"):
        """
        向系统注入能量
        
        mode: "uniform" - 均匀分布
              "polar" - 极区集中 (模拟旋转轴)
              "equator" - 赤道集中
        """
        if mode == "uniform":
            self.energy += energy_input / self.n_nodes
        elif mode == "polar":
            # 能量集中在极区 (模拟高速旋转)
            polar_weight = np.abs(np.cos(self.theta))
            self.energy += energy_input * polar_weight / np.sum(polar_weight)
        elif mode == "equator":
            # 能量集中在赤道
            equator_weight = np.sin(self.theta)
            self.energy += energy_input * equator_weight / np.sum(equator_weight)
            
    def compute_torsion(self):
        """基于能量分布计算扭转场"""
        # 高能量 → 高扭转
        E_max = np.max(self.energy) + 1e-10
        self.torsion = self.tau_0 * (1 + 10 * self.energy / E_max)
        
    def compute_spectral_dimensions_v2(self):
        """
        计算外空间和内空间的谱维 - 修正版
        
        物理假设:
        - 外空间拓扑维固定为4 (观测者视角)
        - 内空间谱维随能量从4→10变化
        - 极端情况 (黑洞): 外空间谱维→0 (信息不可达)
        
        这对应于:
        - 今天宇宙 (低能): d_s_out=4, d_s_in=4
        - 大爆炸 (高能): d_s_out=4, d_s_in=10
        - 黑洞视界 (极端): d_s_out=0, d_s_in=10
        """
        E_total = np.sum(self.energy) + 1e-10
        E_global = E_total / self.n_nodes  # 平均能量密度
        
        for i in range(self.n_nodes):
            # 节点能量相对于全局平均的比值
            E_local = self.energy[i] / (E_global + 1e-10)
            
            # 外空间谱维: 基于能量密度
            # 普通能量密度 → d_s = 4 (稳定观测)
            # 极端能量密度 → d_s → 0 (奇点/黑洞极限)
            if E_global < 10:  # 普通能量范围
                self.d_s_external[i] = 4.0
            else:  # 极端能量 (模拟黑洞形成)
                # 超高能量 → 信息向内泄露 → 外空间不可观测
                self.d_s_external[i] = 4.0 * np.exp(-0.1 * (E_global - 10))
                
            # 内空间谱维: 基于全局能量
            # 低能量 → d_s = 4 (关闭)
            # 高能量 → d_s → 10 (开放)
            base_internal = 4.0 + 6.0 * E_global / (1.0 + E_global)
            # 局部能量差异造成小扰动
            local_mod = 0.2 * np.tanh(E_local - 1.0)
            self.d_s_internal[i] = base_internal + local_mod
            
    def measure_global_dims(self) -> Tuple[float, float]:
        """测量全局平均谱维"""
        return np.mean(self.d_s_external), np.mean(self.d_s_internal)
    
    def measure_local_dims(self, region: str = "pole") -> Tuple[float, float]:
        """测量局部区域谱维"""
        if region == "pole":
            mask = np.abs(np.cos(self.theta)) > 0.8
        elif region == "equator":
            mask = np.abs(np.cos(self.theta)) < 0.3
        else:
            mask = np.ones(self.n_nodes, dtype=bool)
            
        return np.mean(self.d_s_external[mask]), np.mean(self.d_s_internal[mask])


def run_rotation_sphere_experiment(
    energy_levels: List[float] = None,
    modes: List[str] = ["uniform", "polar", "equator"],
    save_results: bool = True
) -> dict:
    """
    运行旋转球实验
    
    模拟不同能量输入模式下的谱维演化
    """
    if energy_levels is None:
        # 对数 spaced 能量水平
        energy_levels = np.logspace(-2, 3, 50)  # 0.01 到 1000
        
    results = {
        "energy_levels": energy_levels.tolist(),
        "modes": {}
    }
    
    for mode in modes:
        print(f"\n运行模式: {mode}")
        
        d_s_ext_global = []
        d_s_int_global = []
        d_s_ext_pole = []
        d_s_int_pole = []
        d_s_ext_equator = []
        d_s_int_equator = []
        
        for E in energy_levels:
            sphere = TNNSphere(n_nodes=200)
            sphere.inject_energy(E, mode=mode)
            sphere.compute_torsion()
            sphere.compute_spectral_dimensions_v2()
            
            # 全局测量
            d_ext, d_int = sphere.measure_global_dims()
            d_s_ext_global.append(d_ext)
            d_s_int_global.append(d_int)
            
            # 局部测量
            d_ext_pole, d_int_pole = sphere.measure_local_dims("pole")
            d_s_ext_pole.append(d_ext_pole)
            d_s_int_pole.append(d_int_pole)
            
            d_ext_eq, d_int_eq = sphere.measure_local_dims("equator")
            d_s_ext_equator.append(d_ext_eq)
            d_s_int_equator.append(d_int_eq)
            
        results["modes"][mode] = {
            "d_s_external_global": d_s_ext_global,
            "d_s_internal_global": d_s_int_global,
            "d_s_external_pole": d_s_ext_pole,
            "d_s_internal_pole": d_s_int_pole,
            "d_s_external_equator": d_s_ext_equator,
            "d_s_internal_equator": d_s_int_equator,
        }
        
        print(f"  完成 {len(energy_levels)} 个能量水平的模拟")
        
    if save_results:
        with open("tnn_sphere_simulation_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print("\n结果已保存至: tnn_sphere_simulation_results.json")
        
    return results


def plot_results(results: dict):
    """可视化模拟结果"""
    energy_levels = np.array(results["energy_levels"])
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    colors = {"uniform": "blue", "polar": "red", "equator": "green"}
    
    for mode, data in results["modes"].items():
        color = colors.get(mode, "black")
        
        # 全局外空间谱维
        axes[0, 0].semilogx(energy_levels, data["d_s_external_global"], 
                           color=color, label=mode, linewidth=2)
        
        # 全局内空间谱维
        axes[0, 1].semilogx(energy_levels, data["d_s_internal_global"], 
                           color=color, label=mode, linewidth=2)
        
        # 维度之和
        sum_dims = np.array(data["d_s_external_global"]) + np.array(data["d_s_internal_global"])
        axes[0, 2].semilogx(energy_levels, sum_dims, 
                           color=color, label=mode, linewidth=2)
        
        # 极区 vs 赤道对比 (仅polar模式)
        if mode == "polar":
            axes[1, 0].semilogx(energy_levels, data["d_s_external_pole"], 
                               'r-', label="pole", linewidth=2)
            axes[1, 0].semilogx(energy_levels, data["d_s_external_equator"], 
                               'b-', label="equator", linewidth=2)
            
            axes[1, 1].semilogx(energy_levels, data["d_s_internal_pole"], 
                               'r-', label="pole", linewidth=2)
            axes[1, 1].semilogx(energy_levels, data["d_s_internal_equator"], 
                               'b-', label="equator", linewidth=2)
        
        # 归一化比例
        norm_sum = (np.array(data["d_s_external_global"]) / 4 + 
                    np.array(data["d_s_internal_global"]) / 10)
        axes[1, 2].semilogx(energy_levels, norm_sum, 
                           color=color, label=mode, linewidth=2)
    
    # 设置标签
    axes[0, 0].set_ylabel("d_s (external)", fontsize=12)
    axes[0, 0].set_title("External Spectral Dimension", fontsize=14)
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].axhline(y=4, color='gray', linestyle='--', alpha=0.5)
    axes[0, 0].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    
    axes[0, 1].set_ylabel("d_s (internal)", fontsize=12)
    axes[0, 1].set_title("Internal Spectral Dimension", fontsize=14)
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].axhline(y=4, color='gray', linestyle='--', alpha=0.5)
    axes[0, 1].axhline(y=10, color='gray', linestyle='--', alpha=0.5)
    
    axes[0, 2].set_ylabel("d_s_out + d_s_in", fontsize=12)
    axes[0, 2].set_title("Sum of Dimensions", fontsize=14)
    axes[0, 2].legend()
    axes[0, 2].grid(True, alpha=0.3)
    axes[0, 2].axhline(y=14, color='gray', linestyle='--', alpha=0.5, label="14")
    axes[0, 2].axhline(y=10, color='orange', linestyle='--', alpha=0.5, label="10")
    
    axes[1, 0].set_ylabel("d_s (external)", fontsize=12)
    axes[1, 0].set_xlabel("Energy Input", fontsize=12)
    axes[1, 0].set_title("Polar vs Equator (External)", fontsize=14)
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    axes[1, 1].set_ylabel("d_s (internal)", fontsize=12)
    axes[1, 1].set_xlabel("Energy Input", fontsize=12)
    axes[1, 1].set_title("Polar vs Equator (Internal)", fontsize=14)
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    axes[1, 2].set_ylabel("d_s_out/4 + d_s_in/10", fontsize=12)
    axes[1, 2].set_xlabel("Energy Input", fontsize=12)
    axes[1, 2].set_title("Normalized Conservation", fontsize=14)
    axes[1, 2].legend()
    axes[1, 2].grid(True, alpha=0.3)
    axes[1, 2].axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig("tnn_sphere_simulation.png", dpi=150)
    print("图形已保存至: tnn_sphere_simulation.png")
    

def analyze_conservation(results: dict):
    """分析守恒律"""
    print("\n" + "="*60)
    print("守恒律分析")
    print("="*60)
    
    for mode, data in results["modes"].items():
        d_ext = np.array(data["d_s_external_global"])
        d_int = np.array(data["d_s_internal_global"])
        
        print(f"\n模式: {mode}")
        print(f"  能量→0:  d_s_out={d_ext[0]:.2f}, d_s_in={d_int[0]:.2f}, sum={d_ext[0]+d_int[0]:.2f}")
        print(f"  能量~1:   d_s_out={d_ext[25]:.2f}, d_s_in={d_int[25]:.2f}, sum={d_ext[25]+d_int[25]:.2f}")
        print(f"  能量→∞:  d_s_out={d_ext[-1]:.2f}, d_s_in={d_int[-1]:.2f}, sum={d_ext[-1]+d_int[-1]:.2f}")
        
        # 检验守恒律
        sum_const = np.std(d_ext + d_int)
        norm_const = np.std(d_ext/4 + d_int/10)
        
        print(f"  和的标准差: {sum_const:.3f} (越小越守恒)")
        print(f"  归一化标准差: {norm_const:.3f}")


if __name__ == "__main__":
    print("="*60)
    print("TNN旋转球谱维流模拟")
    print("="*60)
    
    # 运行实验
    results = run_rotation_sphere_experiment(
        energy_levels=np.logspace(-2, 3, 100),
        modes=["uniform", "polar", "equator"]
    )
    
    # 绘制结果
    plot_results(results)
    
    # 分析守恒律
    analyze_conservation(results)
    
    print("\n" + "="*60)
    print("模拟完成!")
    print("="*60)
