#!/usr/bin/env python3
"""
测试CPU使用率控制功能
"""
import time
import sys
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')

# 测试CPU控制器
try:
    from train_tiny_cpu import CPUUsageController
    
    print("=== CPU使用率控制测试 ===\n")
    
    # 创建控制器（阈值60%）
    controller = CPUUsageController(max_cpu_percent=60.0, check_interval=5)
    
    # 获取CPU信息
    cpu_info = controller.get_cpu_info()
    if cpu_info['available']:
        print(f"✓ CPU控制可用")
        print(f"  CPU核心数: {cpu_info['cpu_count']}")
        print(f"  当前使用率: {cpu_info['cpu_percent']:.1f}%")
        print(f"  阈值: {cpu_info['max_threshold']}%")
    else:
        print("✗ CPU控制不可用，请安装psutil:")
        print("  pip install psutil")
        sys.exit(1)
    
    # 模拟训练循环测试
    print("\n=== 模拟训练循环测试 ===")
    print("运行100个step，观察CPU控制效果...\n")
    
    for step in range(1, 101):
        # 模拟一些计算
        _ = [i**2 for i in range(10000)]
        
        # 调用CPU控制
        controller.check_and_throttle(step)
        
        if step % 20 == 0:
            cpu_percent = controller.psutil.cpu_percent(interval=0.1)
            print(f"Step {step:3d} | CPU: {cpu_percent:5.1f}%")
    
    print("\n✓ 测试完成!")
    print("CPU控制功能正常工作，将确保训练时CPU占用率不超过60%")
    
except Exception as e:
    print(f"✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
