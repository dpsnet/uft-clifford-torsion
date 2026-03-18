"""
TNN快速测试脚本 - 验证实现正确性
"""

import torch
import torch.nn as nn
import sys
sys.path.append('/root/.openclaw/workspace/research_notes/code')

# 导入TNN模块
from tnn_implementation import (
    CliffordAlgebra, SpectralDimension, TorsionField,
    ReciprocalInternalLayer, TorsionNeuralNetwork, AdaptiveDepthTNN,
    TNNForImageClassification, StandardMLP, StandardCNN
)

def test_clifford_algebra():
    """测试Clifford代数"""
    print("\n[1/6] 测试 CliffordAlgebra...")
    ca = CliffordAlgebra(device='cpu')
    assert ca.dim == 4
    assert ca.clifford_dim == 16
    print(f"  ✓ 维度: {ca.dim}, Clifford维度: {ca.clifford_dim}")
    print(f"  ✓ Gamma矩阵数量: {len(ca.gamma_matrices)}")
    return True

def test_spectral_dimension():
    """测试谱维管理器"""
    print("\n[2/6] 测试 SpectralDimension...")
    sd = SpectralDimension(d_s_min=2.0, d_s_max=8.0, device='cpu')
    
    # 测试复杂度计算
    x = torch.randn(10, 100)
    complexity = sd.compute_complexity(x)
    print(f"  ✓ 输入复杂度: {complexity.item():.4f}")
    
    # 测试谱维更新
    d_s = sd.update_spectral_dimension(x)
    print(f"  ✓ 初始谱维: 4.0")
    print(f"  ✓ 更新后谱维: {d_s:.4f}")
    
    # 测试有效深度计算
    depth = sd.get_effective_depth(base_depth=6)
    print(f"  ✓ 有效深度 (base=6): {depth}")
    return True

def test_torsion_field():
    """测试扭转场模块"""
    print("\n[3/6] 测试 TorsionField...")
    tf = TorsionField(64, 128, torsion_order=2, device='cpu')
    
    x = torch.randn(32, 64)
    y = tf(x)
    
    assert y.shape == (32, 128)
    print(f"  ✓ 输入形状: {x.shape}")
    print(f"  ✓ 输出形状: {y.shape}")
    print(f"  ✓ 扭转阶数: {tf.torsion_order}")
    
    energy = tf.get_torsion_energy()
    print(f"  ✓ 扭转能量: {energy.item():.4f}")
    return True

def test_tnn():
    """测试完整TNN"""
    print("\n[4/6] 测试 TorsionNeuralNetwork...")
    tnn = TorsionNeuralNetwork(
        input_dim=784,
        output_dim=10,
        hidden_dims=[128, 128],
        internal_dim=32,
        device='cpu'
    )
    
    x = torch.randn(16, 784)
    y = tnn(x)
    
    assert y.shape == (16, 10)
    print(f"  ✓ 输入形状: {x.shape}")
    print(f"  ✓ 输出形状: {y.shape}")
    print(f"  ✓ 参数数量: {sum(p.numel() for p in tnn.parameters())/1e6:.3f}M")
    print(f"  ✓ 当前谱维: {tnn.get_spectral_dimension():.2f}")
    return True

def test_adaptive_tnn():
    """测试自适应深度TNN"""
    print("\n[5/6] 测试 AdaptiveDepthTNN...")
    atnn = AdaptiveDepthTNN(
        input_dim=784,
        output_dim=10,
        base_depth=4,
        base_width=64,
        device='cpu'
    )
    
    x = torch.randn(16, 784)
    y = atnn(x)
    
    assert y.shape == (16, 10)
    print(f"  ✓ 输入形状: {x.shape}")
    print(f"  ✓ 输出形状: {y.shape}")
    print(f"  ✓ 基准深度: 4")
    print(f"  ✓ 当前谱维: {atnn.get_spectral_dimension():.2f}")
    print(f"  ✓ 有效深度: {atnn.spectral_manager.get_effective_depth(4)}")
    return True

def test_tnn_cnn():
    """测试图像分类TNN"""
    print("\n[6/6] 测试 TNNForImageClassification...")
    tnn_cnn = TNNForImageClassification(
        num_classes=10,
        in_channels=3,
        device='cpu'
    )
    
    x = torch.randn(8, 3, 32, 32)
    y = tnn_cnn(x)
    
    assert y.shape == (8, 10)
    print(f"  ✓ 输入形状: {x.shape}")
    print(f"  ✓ 输出形状: {y.shape}")
    print(f"  ✓ 参数数量: {sum(p.numel() for p in tnn_cnn.parameters())/1e6:.3f}M")
    return True

def mini_training_test():
    """小规模训练测试"""
    print("\n" + "="*60)
    print("小规模训练测试 (MNIST子集)")
    print("="*60)
    
    import torch.optim as optim
    import torch.nn.functional as F
    from torchvision import datasets, transforms
    
    # 加载少量MNIST数据
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    dataset = datasets.MNIST('./data', train=True, download=True, transform=transform)
    
    # 只使用1000个样本
    subset_indices = torch.randperm(len(dataset))[:1000]
    subset = torch.utils.data.Subset(dataset, subset_indices)
    loader = torch.utils.data.DataLoader(subset, batch_size=32, shuffle=True)
    
    # 测试MLP
    print("\n[MLP]")
    mlp = StandardMLP(784, [128, 128], 10)
    optimizer = optim.Adam(mlp.parameters(), lr=0.001)
    
    for epoch in range(3):
        total_loss = 0
        correct = 0
        for data, target in loader:
            data = data.view(data.size(0), -1)
            optimizer.zero_grad()
            output = mlp(data)
            loss = F.cross_entropy(output, target)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            pred = output.argmax(dim=1)
            correct += pred.eq(target).sum().item()
        
        acc = 100. * correct / len(subset)
        print(f"  Epoch {epoch+1}/3: Loss={total_loss/len(loader):.4f}, Acc={acc:.2f}%")
    
    # 测试TNN
    print("\n[TNN]")
    tnn = TorsionNeuralNetwork(784, 10, [128, 128], internal_dim=32, device='cpu')
    optimizer = optim.Adam(tnn.parameters(), lr=0.001)
    
    for epoch in range(3):
        total_loss = 0
        correct = 0
        for data, target in loader:
            data = data.view(data.size(0), -1)
            optimizer.zero_grad()
            output = tnn(data)
            loss = F.cross_entropy(output, target)
            
            # 添加扭转场正则化
            reg_loss = tnn.get_regularization_loss()
            total_loss_batch = loss + 0.001 * reg_loss
            
            total_loss_batch.backward()
            optimizer.step()
            
            total_loss += loss.item()
            pred = output.argmax(dim=1)
            correct += pred.eq(target).sum().item()
        
        acc = 100. * correct / len(subset)
        d_s = tnn.get_spectral_dimension()
        print(f"  Epoch {epoch+1}/3: Loss={total_loss/len(loader):.4f}, Acc={acc:.2f}%, d_s={d_s:.2f}")
    
    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)

if __name__ == "__main__":
    print("="*60)
    print("TNN实现验证测试")
    print("="*60)
    
    try:
        test_clifford_algebra()
        test_spectral_dimension()
        test_torsion_field()
        test_tnn()
        test_adaptive_tnn()
        test_tnn_cnn()
        
        print("\n" + "="*60)
        print("所有模块测试通过! ✓")
        print("="*60)
        
        # 运行小规模训练测试
        mini_training_test()
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
