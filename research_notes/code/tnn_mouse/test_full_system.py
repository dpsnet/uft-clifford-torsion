"""
TNN小鼠实验完整测试
整合大脑、身体、感官系统和行为模块
"""

import sys
import torch
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'sensory_systems'))
sys.path.insert(0, str(Path(__file__).parent / 'behavior_modules'))

from mouse_brain import TNNMouseConfig, create_tnn_mouse_brain
from mouse_body import MouseBodyConfig, MouseBody
from vision import MouseVisualSystem
from olfaction import MouseOlfactorySystem
from audition import MouseAuditorySystem
from exploration import ExplorationBehavior
from fear import FearBehavior


def test_sensory_systems():
    """测试所有感官系统"""
    print("\n" + "="*70)
    print("测试: 感官系统")
    print("="*70)
    
    # 视觉系统
    print("\n1. 视觉系统")
    vision = MouseVisualSystem()
    visual_input = torch.randn(1, 3, 128, 128)
    with torch.no_grad():
        visual_features = vision(visual_input)
    print(f"   输入: {visual_input.shape}")
    print(f"   输出: {visual_features['output'].shape}")
    print(f"   参数量: {sum(p.numel() for p in vision.parameters())/1e6:.2f}M")
    
    # 嗅觉系统
    print("\n2. 嗅觉系统")
    olfaction = MouseOlfactorySystem()
    chemical_input = torch.rand(1, 100)
    with torch.no_grad():
        olfactory_features = olfaction(chemical_input)
    print(f"   输入: {chemical_input.shape}")
    print(f"   输出: {olfactory_features['output'].shape}")
    print(f"   参数量: {sum(p.numel() for p in olfaction.parameters())/1e6:.2f}M")
    
    # 听觉系统
    print("\n3. 听觉系统")
    audition = MouseAuditorySystem()
    audio_input = torch.rand(1, 100, 64)
    with torch.no_grad():
        auditory_features = audition(audio_input, audio_input)
    print(f"   输入: {audio_input.shape}")
    print(f"   输出: {auditory_features['output'].shape}")
    print(f"   参数量: {sum(p.numel() for p in audition.parameters())/1e6:.2f}M")
    
    total_sensory_params = (
        sum(p.numel() for p in vision.parameters()) +
        sum(p.numel() for p in olfaction.parameters()) +
        sum(p.numel() for p in audition.parameters())
    )
    print(f"\n感官系统总参数量: {total_sensory_params/1e6:.2f}M")
    
    return vision, olfaction, audition


def test_behavior_modules():
    """测试行为模块"""
    print("\n" + "="*70)
    print("测试: 行为模块")
    print("="*70)
    
    # 探索行为
    print("\n1. 探索行为")
    exploration = ExplorationBehavior(brain_dim=512)
    brain_state = torch.randn(1, 512)
    position = torch.rand(1, 2)
    
    with torch.no_grad():
        for _ in range(10):
            position = torch.clamp(position + torch.randn(1, 2) * 0.1, 0, 1)
            exp_action = exploration(brain_state, position)
    
    metrics = exploration.get_exploration_metrics()
    print(f"   探索覆盖率: {metrics['coverage']*100:.1f}%")
    print(f"   参数量: {sum(p.numel() for p in exploration.parameters())/1e6:.2f}M")
    
    # 恐惧行为
    print("\n2. 恐惧行为")
    fear = FearBehavior(brain_dim=512)
    threat_detected = torch.tensor([[0.8]])
    threat_direction = torch.tensor([[1.0, 0.0]])
    
    with torch.no_grad():
        fear_action = fear(brain_state, brain_state, threat_detected, threat_direction)
    
    print(f"   恐惧水平: {fear_action['fear_level']:.3f}")
    print(f"   选择行为: {fear_action['selected_behavior'].item()}")
    print(f"   参数量: {sum(p.numel() for p in fear.parameters())/1e6:.2f}M")
    
    total_behavior_params = (
        sum(p.numel() for p in exploration.parameters()) +
        sum(p.numel() for p in fear.parameters())
    )
    print(f"\n行为模块总参数量: {total_behavior_params/1e6:.2f}M")
    
    return exploration, fear


def test_full_integration():
    """测试完整集成"""
    print("\n" + "="*70)
    print("测试: 完整系统集成")
    print("="*70)
    
    # 创建所有组件
    print("\n初始化所有组件...")
    brain = create_tnn_mouse_brain()
    body = MouseBody()
    
    vision = MouseVisualSystem()
    olfaction = MouseOlfactorySystem()
    audition = MouseAuditorySystem()
    
    exploration = ExplorationBehavior(brain_dim=512)
    fear = FearBehavior(brain_dim=512)
    
    # 运行闭环仿真
    print("\n运行100步闭环仿真...")
    position = torch.rand(1, 2)
    memory_state = None
    
    behaviors = []
    fear_levels = []
    
    for step in range(100):
        # 生成感觉输入
        visual_input = torch.randn(1, 3, 128, 128)
        chemical_input = torch.rand(1, 100)
        audio_input = torch.rand(1, 100, 64)
        
        # 感官处理
        with torch.no_grad():
            visual_feat = vision(visual_input)
            olfactory_feat = olfaction(chemical_input)
            auditory_feat = audition(audio_input, audio_input)
        
        # 构建感觉输入字典 (简化)
        sensory_input = {
            'vision': visual_input,
            'audition': torch.randn(1, 1024),
            'olfaction': olfactory_feat['output'],
            'touch': torch.randn(1, 256),
            'proprioception': torch.tensor(body.get_proprioception(), dtype=torch.float32).unsqueeze(0),
            'internal': torch.randn(1, 32)
        }
        
        # 大脑处理
        with torch.no_grad():
            brain_output = brain(sensory_input, memory_state)
        
        brain_state = brain_output['internal_representation'] if 'internal_representation' in brain_output else brain_output['value']
        memory_state = brain_output['memory_state']
        
        # 行为决策 (交替测试探索和恐惧)
        if step < 50:
            # 探索
            position = torch.clamp(position + torch.randn(1, 2) * 0.05, 0, 1)
            with torch.no_grad():
                action = exploration(brain_state, position)
            behaviors.append('exploration')
            fear_levels.append(0.0)
        else:
            # 恐惧 (模拟威胁出现)
            threat = torch.tensor([[0.7]]) if step == 50 else torch.tensor([[0.0]])
            threat_dir = torch.tensor([[-1.0, 0.0]])
            with torch.no_grad():
                action = fear(brain_state, brain_state, threat, threat_dir)
            behaviors.append('fear' if action['selected_behavior'].item() != 4 else 'normal')
            fear_levels.append(action['fear_level'])
        
        # 身体更新
        motor_commands = brain_output['motor_output'].squeeze().numpy()
        body.update(motor_commands)
        
        if step % 25 == 0:
            print(f"  Step {step}: 行为={behaviors[-1]}, 恐惧={fear_levels[-1]:.3f}")
    
    print(f"\n仿真统计:")
    print(f"  探索步数: {behaviors.count('exploration')}")
    print(f"  恐惧响应步数: {behaviors.count('fear')}")
    print(f"  平均恐惧水平: {np.mean(fear_levels):.3f}")
    
    exploration_metrics = exploration.get_exploration_metrics()
    print(f"  空间覆盖率: {exploration_metrics['coverage']*100:.1f}%")


def calculate_total_parameters():
    """计算总参数量"""
    print("\n" + "="*70)
    print("资源需求汇总")
    print("="*70)
    
    brain = create_tnn_mouse_brain()
    body = MouseBody()
    
    vision = MouseVisualSystem()
    olfaction = MouseOlfactorySystem()
    audition = MouseAuditorySystem()
    exploration = ExplorationBehavior(brain_dim=512)
    fear = FearBehavior(brain_dim=512)
    
    brain_params = brain.count_parameters()
    vision_params = sum(p.numel() for p in vision.parameters())
    olfaction_params = sum(p.numel() for p in olfaction.parameters())
    audition_params = sum(p.numel() for p in audition.parameters())
    exploration_params = sum(p.numel() for p in exploration.parameters())
    fear_params = sum(p.numel() for p in fear.parameters())
    
    sensory_params = vision_params + olfaction_params + audition_params
    behavior_params = exploration_params + fear_params
    total_params = brain_params + sensory_params + behavior_params
    
    print(f"\n各组件参数量:")
    print(f"  大脑 (TNN): {brain_params/1e6:.2f}M")
    print(f"  视觉系统: {vision_params/1e6:.2f}M")
    print(f"  嗅觉系统: {olfaction_params/1e6:.2f}M")
    print(f"  听觉系统: {audition_params/1e6:.2f}M")
    print(f"  探索行为: {exploration_params/1e6:.2f}M")
    print(f"  恐惧行为: {fear_params/1e6:.2f}M")
    
    print(f"\n汇总:")
    print(f"  感官系统总计: {sensory_params/1e6:.2f}M")
    print(f"  行为模块总计: {behavior_params/1e6:.2f}M")
    print(f"  完整系统总计: {total_params/1e6:.2f}M")
    
    # 内存估算
    param_memory = total_params * 4 / (1024**3)  # GB
    print(f"\n内存需求:")
    print(f"  模型参数: {param_memory:.2f} GB")
    print(f"  推荐GPU: A100 40GB 或同等级")


def main():
    """主函数"""
    print("\n" + "="*70)
    print(" TNN小鼠实验 - 完整系统测试 ".center(70, "="))
    print("="*70)
    
    try:
        # 测试各个组件
        test_sensory_systems()
        test_behavior_modules()
        test_full_integration()
        calculate_total_parameters()
        
        print("\n" + "="*70)
        print(" 所有测试通过! ".center(70, "="))
        print("="*70)
        
        print("\n已完成:")
        print("  ✓ TNN小鼠大脑 (30M参数)")
        print("  ✓ 物理身体模型")
        print("  ✓ 视觉系统 (视网膜→IT区)")
        print("  ✓ 嗅觉系统 (受体→杏仁核)")
        print("  ✓ 听觉系统 (耳蜗→下丘)")
        print("  ✓ 探索行为 (空间记忆、新奇度)")
        print("  ✓ 恐惧行为 (恐惧记忆、防御策略)")
        
        print("\n下一步:")
        print("  - 创建测试环境 (开放场地、水迷宫)")
        print("  - 实现标准行为测试")
        print("  - 与真实小鼠数据对比验证")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
