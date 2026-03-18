#!/usr/bin/env python3
"""
TNN小鼠实验主运行脚本
"""

import sys
import torch
import numpy as np
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from mouse_brain import TNNMouseConfig, create_tnn_mouse_brain
from mouse_body import MouseBodyConfig, MouseBody


def test_brain_forward():
    """测试大脑前向传播"""
    print("\n" + "="*60)
    print("测试1: TNN小鼠大脑前向传播")
    print("="*60)
    
    # 创建大脑
    config = TNNMouseConfig()
    brain = create_tnn_mouse_brain(config)
    
    # 创建模拟感觉输入
    batch_size = 1
    sensory_input = {
        'vision': torch.randn(batch_size, 3, 128, 128),
        'audition': torch.randn(batch_size, 1024),
        'olfaction': torch.randn(batch_size, 400),
        'touch': torch.randn(batch_size, 256),
        'proprioception': torch.randn(batch_size, 64),
        'internal': torch.randn(batch_size, 32)
    }
    
    # 前向传播
    with torch.no_grad():
        outputs = brain(sensory_input, return_details=True)
    
    print(f"\n输出信息:")
    print(f"  运动输出: {outputs['motor_output'].shape}")
    print(f"  行为选择: {outputs['behavior_logits'].shape}")
    print(f"  状态价值: {outputs['value'].item():.4f}")
    print(f"  谱维: {outputs['spectral_dim']:.2f}")
    print(f"  扭转能量: {outputs['torsion_energy']:.4f}")
    
    print("\n✓ 大脑测试通过")
    return brain


def test_body_dynamics():
    """测试身体动力学"""
    print("\n" + "="*60)
    print("测试2: TNN小鼠身体动力学")
    print("="*60)
    
    body = MouseBody()
    
    print(f"\n身体参数:")
    print(f"  质量: {body.config.body_mass*1000:.1f}g")
    print(f"  体长: {body.config.body_length*100:.1f}cm")
    
    # 模拟100步
    positions = []
    for _ in range(100):
        motor_commands = np.random.randn(168) * 0.2
        body.update(motor_commands)
        positions.append(body.position.copy())
    
    positions = np.array(positions)
    distance = np.linalg.norm(positions[-1] - positions[0])
    
    print(f"\n100步模拟结果:")
    print(f"  移动距离: {distance*100:.2f}cm")
    print(f"  最终位置: [{positions[-1, 0]*100:.2f}, {positions[-1, 1]*100:.2f}, {positions[-1, 2]*100:.2f}] cm")
    print(f"  内部状态: 能量={body.energy:.3f}, 饥饿={body.hunger:.3f}")
    
    print("\n✓ 身体测试通过")
    return body


def test_brain_body_integration():
    """测试大脑-身体集成"""
    print("\n" + "="*60)
    print("测试3: 大脑-身体集成测试")
    print("="*60)
    
    # 创建大脑和身体
    brain_config = TNNMouseConfig()
    brain = create_tnn_mouse_brain(brain_config)
    body = MouseBody()
    
    # 模拟闭环
    memory_state = None
    positions = []
    
    print(f"\n运行50步闭环仿真...")
    
    for step in range(50):
        # 获取本体感觉
        proprio = body.get_proprioception()
        
        # 构建感觉输入
        sensory_input = {
            'vision': torch.randn(1, 3, 128, 128),
            'audition': torch.randn(1, 1024),
            'olfaction': torch.randn(1, 400),
            'touch': torch.randn(1, 256),
            'proprioception': torch.tensor(proprio, dtype=torch.float32).unsqueeze(0),
            'internal': torch.tensor([
                body.energy, body.hunger, body.fear, body.arousal,
                body.stress, 0, 0, 0,  # 填充到32维
                0, 0, 0, 0,
                0, 0, 0, 0,
                0, 0, 0, 0,
                0, 0, 0, 0,
                0, 0, 0, 0,
                0, 0, 0, 0
            ], dtype=torch.float32).unsqueeze(0)
        }
        
        # 大脑决策
        with torch.no_grad():
            outputs = brain(sensory_input, memory_state)
        
        motor_commands = outputs['motor_output'].squeeze().numpy()
        memory_state = outputs['memory_state']
        
        # 身体执行
        body.update(motor_commands)
        positions.append(body.position.copy())
    
    positions = np.array(positions)
    total_distance = np.sum(np.linalg.norm(np.diff(positions, axis=0), axis=1))
    
    print(f"\n闭环仿真结果:")
    print(f"  总步数: 50")
    print(f"  总移动距离: {total_distance*100:.2f}cm")
    print(f"  平均谱维: {np.mean(brain.spectral_dims_history):.2f}" 
          if brain.spectral_dims_history else "  谱维: N/A")
    
    print("\n✓ 集成测试通过")


def estimate_resources():
    """估算资源需求"""
    print("\n" + "="*60)
    print("资源需求估算")
    print("="*60)
    
    config = TNNMouseConfig()
    brain = create_tnn_mouse_brain(config)
    
    n_params = brain.count_parameters()
    
    # 估算内存
    param_memory = n_params * 4 / (1024**3)  # GB (float32)
    activations = sum(config.internal_dims) * 4 * 2 / (1024**3)  # 前向+反向
    
    print(f"\n模型规模:")
    print(f"  参数量: {n_params/1e6:.2f}M")
    print(f"  模型内存: {param_memory:.2f}GB")
    print(f"  激活内存: {activations:.2f}GB")
    print(f"  总内存需求: {param_memory + activations:.2f}GB")
    
    # 估算计算量
    print(f"\n计算需求:")
    print(f"  每步前向传播: ~{n_params * 2 / 1e9:.2f} GFLOPs")
    print(f"  实时仿真(100Hz): 需要 ~{n_params * 2 * 100 / 1e12:.2f} TFLOP/s")
    print(f"  建议GPU: A100 40GB 或同等级")
    
    print(f"\n开发时间估算:")
    print(f"  Phase 1 (基础): 2周")
    print(f"  Phase 2 (行为): 3周")
    print(f"  Phase 3 (学习): 3周")
    print(f"  Phase 4 (验证): 2周")
    print(f"  总计: ~10周")


def main():
    """主函数"""
    print("\n" + "="*70)
    print(" TNN小鼠实验 - 初步测试 ".center(70, "="))
    print("="*70)
    
    print("\n本测试验证TNN小鼠实验的基础架构:")
    print("1. 大脑网络前向传播")
    print("2. 身体动力学")
    print("3. 大脑-身体闭环")
    print("4. 资源需求估算")
    
    try:
        # 运行测试
        test_brain_forward()
        test_body_dynamics()
        test_brain_body_integration()
        estimate_resources()
        
        print("\n" + "="*70)
        print(" 所有测试通过! ".center(70, "="))
        print("="*70)
        print("\n下一步:")
        print("  - 实现感官系统 (视觉、听觉、嗅觉)")
        print("  - 实现行为模块 (探索、社交、恐惧)")
        print("  - 创建测试环境 (开放场地、水迷宫)")
        print("  - 运行标准行为测试")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
