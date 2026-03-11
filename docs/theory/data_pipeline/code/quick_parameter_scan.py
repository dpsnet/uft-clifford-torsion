#!/usr/bin/env python3
"""
快速参数扫描 - 寻找最佳拟合参数

使用简化方法快速扫描参数空间，找到与实验数据一致的参数组合
"""

import sys
import json
import numpy as np

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/data_pipeline/code')

from uft_predictions import UnifiedFieldTheory

def quick_parameter_scan():
    """
    快速扫描关键参数 tau_0，寻找与实验数据一致的值
    """
    print("快速参数扫描")
    print("=" * 60)
    
    # 实验约束（简化）
    constraints = {
        'GW_vector_snr_limit': 0.1,      # 矢量偏振SNR上限
        'GW_scalar_snr_limit': 0.05,      # 标量偏振SNR上限
        'CMB_r_limit': 0.06,              # r值上限
        'CMB_n_s_center': 0.965,          # n_s中心值
        'CMB_n_s_sigma': 0.004,           # n_s误差
        'Atomic_shift_limit_Hz': 0.001,   # 原子钟偏移上限(Hz)
    }
    
    # 扫描 tau_0
    tau_0_values = np.logspace(-4, -1, 20)  # 1e-4 到 0.1
    
    results = []
    
    for tau_0 in tau_0_values:
        params = {
            'alpha': 0.01,
            'm_tau': 1e-3,
            'lambda_nl': 1e-6,
            'kappa_nl': 1e-12,
            'g_tau': 1.0,
            'tau_0': tau_0,
            'M_pl': 2.435e18,
        }
        
        uft = UnifiedFieldTheory(params)
        
        # 检查各项约束
        
        # 1. GW约束
        # 矢量偏振SNR ~ tau
        gw_vector_ok = tau_0 < constraints['GW_vector_snr_limit']
        # 标量偏振SNR ~ tau^2
        gw_scalar_ok = tau_0**2 < constraints['GW_scalar_snr_limit']
        
        # 2. CMB约束
        # n_s = 0.965 - 2*(tau/0.1)^2
        n_s_pred = 0.965 - 2 * (tau_0 / 0.1)**2
        n_s_ok = abs(n_s_pred - constraints['CMB_n_s_center']) < 3 * constraints['CMB_n_s_sigma']
        
        # r = 0.01 + 0.04*(tau/0.1)^2
        r_pred = 0.01 + 0.04 * (tau_0 / 0.1)**2
        r_ok = r_pred < constraints['CMB_r_limit']
        
        # 3. 原子物理约束
        # 简化估计：原子尺度 tau ~ tau_0 * 10^-11（压制因子）
        tau_atom = tau_0 * 1e-11
        # 超精细偏移 ~ tau_atom * 10^9 (Z^4增强) * 10 Hz
        cs_shift = tau_atom * 1e9 * 10
        atomic_ok = cs_shift < constraints['Atomic_shift_limit_Hz']
        
        # 计算通过约束的比例
        passed = sum([gw_vector_ok, gw_scalar_ok, n_s_ok, r_ok, atomic_ok])
        total = 5
        score = passed / total
        
        result = {
            'tau_0': tau_0,
            'score': score,
            'n_s_pred': n_s_pred,
            'r_pred': r_pred,
            'cs_shift_Hz': cs_shift,
            'constraints_passed': passed,
            'details': {
                'gw_vector': gw_vector_ok,
                'gw_scalar': gw_scalar_ok,
                'cmb_n_s': n_s_ok,
                'cmb_r': r_ok,
                'atomic': atomic_ok,
            }
        }
        
        results.append(result)
    
    # 找到最佳参数
    best_result = max(results, key=lambda x: x['score'])
    
    print(f"\n扫描完成，测试了 {len(tau_0_values)} 个参数点")
    print(f"\n最佳参数:")
    print(f"  tau_0 = {best_result['tau_0']:.2e}")
    print(f"  通过约束: {best_result['constraints_passed']}/5 ({best_result['score']*100:.0f}%)")
    print(f"  n_s 预言: {best_result['n_s_pred']:.4f}")
    print(f"  r 预言: {best_result['r_pred']:.4f}")
    print(f"  Cs钟偏移: {best_result['cs_shift_Hz']:.2e} Hz")
    
    print(f"\n详细约束状态:")
    for key, value in best_result['details'].items():
        status = "✓" if value else "✗"
        print(f"  {status} {key}")
    
    # 保存所有结果
    with open('parameter_scan_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n完整结果已保存: parameter_scan_results.json")
    
    return best_result

if __name__ == "__main__":
    best = quick_parameter_scan()
    
    print("\n" + "=" * 60)
    print("建议使用最佳参数重新运行验证:")
    print(f"  tau_0 = {best['tau_0']:.2e}")
