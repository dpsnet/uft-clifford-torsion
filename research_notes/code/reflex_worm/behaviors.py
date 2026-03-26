"""
微型TNN"反射虫" - 预设行为模式
通过不同的扭转场配置实现先天反射行为

核心假设："结构即行为" - 不同的TNN拓扑结构产生不同的先天行为
"""

import torch
import numpy as np
from typing import Dict, Optional
try:
    from .tnn_worm import TNNWorm, TNNWormCore
except ImportError:
    from tnn_worm import TNNWorm, TNNWormCore


def create_phototaxis_worm(
    x: float = 50.0,
    y: float = 50.0,
    heading: float = 0.0,
    device: str = 'cpu'
) -> TNNWorm:
    """
    A. "趋光虫"（Phototaxis）
    
    扭转场配置：光强→前进的正相关
    - 高亮度输入增强前进运动
    - 左右光感受器差异控制转向
    
    预期行为：主动向光源移动
    """
    # 创建虫子
    worm = TNNWorm(x, y, heading, device=device)
    
    # 配置扭转场 - 趋光模式
    # 左/右光感受器 → 前进/转向
    with torch.no_grad():
        # 输入投影层：增强亮度到前进的映射
        # 传感器索引：0=左亮度, 1=右亮度
        worm.brain.input_projection.weight[0, 0] = 0.5  # 左亮度 → 互反空间x
        worm.brain.input_projection.weight[0, 1] = 0.5  # 右亮度 → 互反空间x
        worm.brain.input_projection.weight[1, 0] = -0.3  # 左亮度 → 互反空间y（左转）
        worm.brain.input_projection.weight[1, 1] = 0.3   # 右亮度 → 互反空间y（右转）
        
        # 扭转场配置：增强对光梯度的响应
        # 互反空间扭转场
        worm.brain.layer1_reciprocal.torsion_field[0, 0, 0] = 0.8  # 高亮度 → 前进
        worm.brain.layer1_reciprocal.torsion_field[0, 0, 1] = 0.8
        worm.brain.layer1_reciprocal.torsion_field[0, 1, 0] = -0.5  # 左亮 → 左转
        worm.brain.layer1_reciprocal.torsion_field[0, 1, 1] = 0.5   # 右亮 → 右转
        
        # 扭转耦合强度
        worm.brain.layer1_reciprocal.torsion_coupling.data.fill_(0.7)
        
        # 输出投影：互反空间 → 运动
        # 输出索引：0=左转, 1=右转, 2=前进, 3=后退
        worm.brain.output_projection[0].weight[2, 0] = 1.0  # 亮度信号 → 前进
        worm.brain.output_projection[0].weight[0, 1] = -1.0  # y信号 → 左转
        worm.brain.output_projection[0].weight[1, 1] = 1.0   # y信号 → 右转
    
    return worm


def create_photophobia_worm(
    x: float = 50.0,
    y: float = 50.0,
    heading: float = 0.0,
    device: str = 'cpu'
) -> TNNWorm:
    """
    B. "避光虫"（Photophobia）
    
    扭转场配置：光强→后退
    - 高亮度输入增强后退运动
    - 快速逃离高亮度区域
    
    预期行为：逃离光源
    """
    worm = TNNWorm(x, y, heading, device=device)
    
    with torch.no_grad():
        # 输入投影：亮度 → 后退信号
        worm.brain.input_projection.weight[0, 0] = -0.4  # 左亮度
        worm.brain.input_projection.weight[0, 1] = -0.4  # 右亮度
        worm.brain.input_projection.weight[1, 0] = -0.3  # 左亮 → 左转（逃离）
        worm.brain.input_projection.weight[1, 1] = 0.3   # 右亮 → 右转
        
        # 扭转场：高亮度 → 强后退
        worm.brain.layer1_reciprocal.torsion_field[0, 0, 0] = -0.6
        worm.brain.layer1_reciprocal.torsion_field[0, 0, 1] = -0.6
        worm.brain.layer1_reciprocal.torsion_field[0, 1, 0] = -0.4
        worm.brain.layer1_reciprocal.torsion_field[0, 1, 1] = 0.4
        
        worm.brain.layer1_reciprocal.torsion_coupling.data.fill_(0.6)
        
        # 输出投影：亮度 → 后退
        worm.brain.output_projection[0].weight[3, 0] = 1.0  # 亮度 → 后退
        worm.brain.output_projection[0].weight[0, 1] = -1.0
        worm.brain.output_projection[0].weight[1, 1] = 1.0
    
    return worm


def create_thigmotaxis_worm(
    x: float = 50.0,
    y: float = 50.0,
    heading: float = 0.0,
    device: str = 'cpu'
) -> TNNWorm:
    """
    C. "壁虎虫"（Thigmotaxis）
    
    扭转场配置：触觉→沿墙运动
    - 前触觉激活 → 转向（避免碰撞）
    - 侧触觉激活 → 保持接触（沿墙运动）
    - 后触觉激活 → 前进（离开边界）
    
    预期行为：跟随边界移动
    """
    worm = TNNWorm(x, y, heading, device=device)
    
    with torch.no_grad():
        # 输入投影：触觉传感器
        # 传感器索引：2=前触觉, 3=后触觉
        worm.brain.input_projection.weight[0, 2] = -0.5  # 前触觉 → x（后退信号）
        worm.brain.input_projection.weight[0, 3] = 0.3   # 后触觉 → x（前进信号）
        worm.brain.input_projection.weight[1, 2] = 0.8   # 前触觉 → y（强转向）
        worm.brain.input_projection.weight[2, 2] = 0.4   # 前触觉 → z（备用）
        worm.brain.input_projection.weight[3, 2] = 0.4   # 前触觉 → w
        
        # 扭转场：触觉响应
        # 前触觉 → 快速转向
        worm.brain.layer1_reciprocal.torsion_field[0, 1, 2] = 1.0  # 前触觉 → y轴强扭转
        worm.brain.layer1_reciprocal.torsion_field[1, 1, 2] = 0.5  # 二阶扭转
        
        # 侧触觉 → 维持接触（不对称扭转）
        worm.brain.layer1_reciprocal.torsion_field[0, 0, 2] = -0.3
        worm.brain.layer1_reciprocal.torsion_field[0, 2, 2] = 0.3
        
        worm.brain.layer1_reciprocal.torsion_coupling.data.fill_(0.8)
        
        # 输出投影：触觉 → 转向/前进
        worm.brain.output_projection[0].weight[0, 1] = 1.0   # y信号 → 左转
        worm.brain.output_projection[0].weight[1, 1] = -1.0  # y信号 → 右转
        worm.brain.output_projection[0].weight[2, 0] = 0.5   # x信号 → 前进
        worm.brain.output_projection[0].weight[3, 0] = -0.5  # x信号 → 后退
    
    return worm


def create_exploration_worm(
    x: float = 50.0,
    y: float = 50.0,
    heading: float = 0.0,
    device: str = 'cpu'
) -> TNNWorm:
    """
    D. "探索虫"（Exploration）
    
    扭转场配置：随机扭转分量
    - 高阶扭转场引入随机性
    - 内部空间随机演化
    - 对感觉输入的低响应
    
    预期行为：随机游走
    """
    worm = TNNWorm(x, y, heading, device=device)
    
    with torch.no_grad():
        # 弱感觉输入响应
        worm.brain.input_projection.weight.mul_(0.1)
        
        # 随机扭转场（高熵配置）
        torch.manual_seed(42)  # 可重复
        worm.brain.layer1_reciprocal.torsion_field.normal_(mean=0.0, std=0.5)
        worm.brain.layer1_internal.torsion_field.normal_(mean=0.0, std=0.5)
        
        # 高扭转耦合
        worm.brain.layer1_reciprocal.torsion_coupling.data.fill_(0.9)
        worm.brain.layer1_internal.torsion_coupling.data.fill_(0.9)
        
        # 内部记忆随机初始化
        worm.brain.internal_memory.normal_(mean=0.0, std=0.1)
        
        # 输出投影：允许随机运动
        worm.brain.output_projection[0].weight.normal_(mean=0.0, std=0.3)
    
    return worm


def create_homeostasis_worm(
    x: float = 50.0,
    y: float = 50.0,
    heading: float = 0.0,
    device: str = 'cpu'
) -> TNNWorm:
    """
    E. "平衡虫"（Homeostasis）
    
    扭转场配置：多感觉整合
    - 光强适中区域 → 静止/慢速运动
    - 光强变化 → 调整位置回到舒适区
    - 碰撞风险 → 规避
    
    预期行为：在光源边缘保持平衡
    """
    worm = TNNWorm(x, y, heading, device=device)
    
    with torch.no_grad():
        # 输入投影：多感觉整合
        # 亮度梯度决定运动方向
        worm.brain.input_projection.weight[0, 4] = 0.6   # grad_x → x
        worm.brain.input_projection.weight[1, 5] = 0.6   # grad_y → y
        
        # 触觉抑制运动
        worm.brain.input_projection.weight[2, 2] = -0.4  # 前触觉 → 抑制
        worm.brain.input_projection.weight[3, 3] = -0.2  # 后触觉 → 抑制
        
        # 扭转场：平衡响应
        # 梯度 → 平滑跟随
        worm.brain.layer1_reciprocal.torsion_field[0, 0, 4] = 0.3
        worm.brain.layer1_reciprocal.torsion_field[0, 1, 5] = 0.3
        
        # 高阶扭转提供阻尼
        worm.brain.layer1_reciprocal.torsion_field[1, 0, 0] = -0.2
        worm.brain.layer1_reciprocal.torsion_field[1, 1, 1] = -0.2
        
        # 中等扭转耦合
        worm.brain.layer1_reciprocal.torsion_coupling.data.fill_(0.5)
        
        # 流动门控：中等信息流动
        worm.brain.flow_gate.data.fill_(0.0)  # 适中流动
        
        # 输出投影：平滑运动
        worm.brain.output_projection[0].weight[2, 0] = 0.3   # x → 前进
        worm.brain.output_projection[0].weight[3, 0] = -0.3  # x → 后退
        worm.brain.output_projection[0].weight[0, 1] = -0.4  # y → 左转
        worm.brain.output_projection[0].weight[1, 1] = 0.4   # y → 右转
    
    return worm


# 行为预设工厂
BEHAVIOR_PRESETS = {
    'phototaxis': {
        'name': '趋光虫',
        'name_en': 'Phototaxis',
        'description': '主动向光源移动',
        'torsion_pattern': '光强→前进正相关',
        'creator': create_phototaxis_worm
    },
    'photophobia': {
        'name': '避光虫',
        'name_en': 'Photophobia',
        'description': '逃离光源',
        'torsion_pattern': '光强→后退',
        'creator': create_photophobia_worm
    },
    'thigmotaxis': {
        'name': '壁虎虫',
        'name_en': 'Thigmotaxis',
        'description': '跟随边界移动',
        'torsion_pattern': '触觉→沿墙运动',
        'creator': create_thigmotaxis_worm
    },
    'exploration': {
        'name': '探索虫',
        'name_en': 'Exploration',
        'description': '随机游走探索环境',
        'torsion_pattern': '随机扭转分量',
        'creator': create_exploration_worm
    },
    'homeostasis': {
        'name': '平衡虫',
        'name_en': 'Homeostasis',
        'description': '在光源边缘保持平衡',
        'torsion_pattern': '多感觉整合',
        'creator': create_homeostasis_worm
    }
}


def create_worm_by_behavior(
    behavior_type: str,
    x: float = 50.0,
    y: float = 50.0,
    heading: float = 0.0,
    device: str = 'cpu'
) -> TNNWorm:
    """
    根据行为类型创建反射虫
    
    Args:
        behavior_type: 行为类型，可选 'phototaxis', 'photophobia', 'thigmotaxis', 
                      'exploration', 'homeostasis'
        x, y: 初始位置
        heading: 初始朝向
        device: 计算设备
    
    Returns:
        配置好的TNNWorm实例
    """
    if behavior_type not in BEHAVIOR_PRESETS:
        raise ValueError(f"未知行为类型: {behavior_type}。可用类型: {list(BEHAVIOR_PRESETS.keys())}")
    
    creator = BEHAVIOR_PRESETS[behavior_type]['creator']
    return creator(x, y, heading, device)


def get_behavior_info() -> Dict:
    """获取所有行为预设的信息"""
    return {
        key: {
            'name': value['name'],
            'name_en': value['name_en'],
            'description': value['description'],
            'torsion_pattern': value['torsion_pattern']
        }
        for key, value in BEHAVIOR_PRESETS.items()
    }


def compare_torsion_fields(worm1: TNNWorm, worm2: TNNWorm) -> Dict:
    """
    比较两个虫子的扭转场配置
    用于验证"结构即行为"假说
    """
    with torch.no_grad():
        # 获取扭转场参数
        torsion1_reciprocal = worm1.brain.layer1_reciprocal.torsion_field.cpu().numpy()
        torsion1_internal = worm1.brain.layer1_internal.torsion_field.cpu().numpy()
        torsion2_reciprocal = worm2.brain.layer1_reciprocal.torsion_field.cpu().numpy()
        torsion2_internal = worm2.brain.layer1_internal.torsion_field.cpu().numpy()
        
        # 计算差异
        diff_reciprocal = np.abs(torsion1_reciprocal - torsion2_reciprocal).mean()
        diff_internal = np.abs(torsion1_internal - torsion2_internal).mean()
        
        # 统计信息
        return {
            'reciprocal_field_shape': torsion1_reciprocal.shape,
            'internal_field_shape': torsion1_internal.shape,
            'mean_diff_reciprocal': float(diff_reciprocal),
            'mean_diff_internal': float(diff_internal),
            'torsion_energy_1': (
                worm1.brain.layer1_reciprocal.get_torsion_energy().item() +
                worm1.brain.layer1_internal.get_torsion_energy().item()
            ),
            'torsion_energy_2': (
                worm2.brain.layer1_reciprocal.get_torsion_energy().item() +
                worm2.brain.layer1_internal.get_torsion_energy().item()
            )
        }


# 测试代码
if __name__ == "__main__":
    print("TNN反射虫行为预设测试")
    print("=" * 60)
    
    # 显示所有行为预设
    info = get_behavior_info()
    print("\n可用行为预设:")
    for key, value in info.items():
        print(f"\n  [{key}]")
        print(f"    名称: {value['name']} ({value['name_en']})")
        print(f"    描述: {value['description']}")
        print(f"    扭转模式: {value['torsion_pattern']}")
    
    # 测试创建虫子
    print("\n" + "=" * 60)
    print("创建不同行为模式的虫子...")
    
    for behavior in ['phototaxis', 'photophobia', 'exploration']:
        worm = create_worm_by_behavior(behavior)
        info = worm.brain.get_architecture_info()
        print(f"\n  {behavior}:")
        print(f"    参数数量: {info['total_params']}")
        print(f"    扭转阶数: {info['torsion_order']}")
    
    # 比较不同行为的扭转场
    print("\n" + "=" * 60)
    print("比较扭转场差异:")
    
    worm_photo = create_worm_by_behavior('phototaxis')
    worm_phobo = create_worm_by_behavior('photophobia')
    
    comparison = compare_torsion_fields(worm_photo, worm_phobo)
    print(f"\n  趋光虫 vs 避光虫:")
    print(f"    互反空间差异: {comparison['mean_diff_reciprocal']:.4f}")
    print(f"    内部空间差异: {comparison['mean_diff_internal']:.4f}")
    print(f"    趋光虫扭转能量: {comparison['torsion_energy_1']:.4f}")
    print(f"    避光虫扭转能量: {comparison['torsion_energy_2']:.4f}")
