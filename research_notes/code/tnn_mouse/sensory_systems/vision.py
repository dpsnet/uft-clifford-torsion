"""
TNN小鼠视觉系统
包含视网膜、初级视觉皮层V1、高级视觉处理
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Dict


class Retina(nn.Module):
    """视网膜处理 - 模拟感光细胞和双极细胞"""
    
    def __init__(self, input_size: Tuple[int, int] = (128, 128), n_channels: int = 3):
        super().__init__()
        self.input_size = input_size
        
        # 中心- surround 感受野 (模拟视网膜神经节细胞)
        self.center_surround = nn.Conv2d(n_channels, 16, kernel_size=7, padding=3)
        
        # 方向选择性 (简化版)
        self.direction_selective = nn.Conv2d(16, 32, kernel_size=5, padding=2)
        
        # 对比度归一化
        self.bn = nn.BatchNorm2d(32)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, 3, 128, 128] RGB图像
        Returns:
            视网膜输出特征
        """
        # 中心-surround
        x = F.relu(self.center_surround(x))
        
        # 方向选择
        x = F.relu(self.direction_selective(x))
        
        # 归一化
        x = self.bn(x)
        
        return x


class VisualCortexV1(nn.Module):
    """初级视觉皮层V1 - 边缘检测和方向选择"""
    
    def __init__(self, in_channels: int = 32, out_channels: int = 64):
        super().__init__()
        
        # 模拟简单细胞 (Gabor-like滤波器)
        self.simple_cells = nn.Conv2d(in_channels, out_channels, kernel_size=5, padding=2)
        
        # 模拟复杂细胞 (池化响应)
        self.complex_cells = nn.MaxPool2d(kernel_size=2, stride=2)
        
        # 方向调谐 (8个方向)
        self.direction_tuning = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, 32, 128, 128]
        Returns:
            V1输出 [B, 64, 64, 64]
        """
        # 简单细胞响应
        x = F.relu(self.simple_cells(x))
        
        # 复杂细胞池化
        x = self.complex_cells(x)
        
        # 方向调谐
        x = F.relu(self.direction_tuning(x))
        
        return x


class VisualCortexV2(nn.Module):
    """次级视觉皮层V2 - 纹理、轮廓整合"""
    
    def __init__(self, in_channels: int = 64, out_channels: int = 128):
        super().__init__()
        
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """[B, 64, 64, 64] -> [B, 128, 32, 32]"""
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = self.pool(x)
        return x


class VisualCortexV4(nn.Module):
    """V4区 - 形状、颜色处理"""
    
    def __init__(self, in_channels: int = 128, out_channels: int = 256):
        super().__init__()
        
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d((16, 16))
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """[B, 128, 32, 32] -> [B, 256, 16, 16]"""
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = self.pool(x)
        return x


class VisualCortexIT(nn.Module):
    """IT区 - 物体识别 (模拟)"""
    
    def __init__(self, in_channels: int = 256, feature_dim: int = 512):
        super().__init__()
        
        self.conv = nn.Conv2d(in_channels, 512, kernel_size=3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d((8, 8))
        
        # 展平后的特征
        self.feature_dim = 512 * 8 * 8
        self.fc = nn.Linear(self.feature_dim, feature_dim)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """[B, 256, 16, 16] -> [B, 512]"""
        x = F.relu(self.conv(x))
        x = self.pool(x)
        x = x.flatten(1)
        x = F.relu(self.fc(x))
        return x


class MouseVisualSystem(nn.Module):
    """
    小鼠完整视觉系统
    视网膜 -> V1 -> V2 -> V4 -> IT
    """
    
    def __init__(self, input_size: Tuple[int, int] = (128, 128), output_dim: int = 512):
        super().__init__()
        
        self.retina = Retina(input_size)
        self.v1 = VisualCortexV1()
        self.v2 = VisualCortexV2()
        self.v4 = VisualCortexV4()
        self.it = VisualCortexIT(feature_dim=output_dim)
        
        self.output_dim = output_dim
        
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            x: [B, 3, 128, 128] RGB图像
        Returns:
            包含各级视觉特征的字典
        """
        features = {}
        
        # 视网膜
        x = self.retina(x)
        features['retina'] = x
        
        # V1
        x = self.v1(x)
        features['v1'] = x
        
        # V2
        x = self.v2(x)
        features['v2'] = x
        
        # V4
        x = self.v4(x)
        features['v4'] = x
        
        # IT (高级特征)
        x = self.it(x)
        features['it'] = x
        features['output'] = x
        
        return features
    
    def get_output_dim(self) -> int:
        return self.output_dim


# 测试
if __name__ == "__main__":
    print("=== TNN小鼠视觉系统测试 ===\n")
    
    # 创建视觉系统
    visual_system = MouseVisualSystem()
    
    # 测试输入
    batch_size = 2
    test_input = torch.randn(batch_size, 3, 128, 128)
    
    print(f"输入形状: {test_input.shape}")
    
    # 前向传播
    with torch.no_grad():
        features = visual_system(test_input)
    
    print(f"\n各级特征形状:")
    for name, feat in features.items():
        print(f"  {name}: {feat.shape}")
    
    print(f"\n总参数量: {sum(p.numel() for p in visual_system.parameters())/1e6:.2f}M")
    
    print("\n✓ 视觉系统测试通过!")
