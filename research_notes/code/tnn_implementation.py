"""
Torsion Neural Network (TNN) Implementation
基于统一场理论的神经网络几何化实现

核心理论映射:
- 神经元 ↔ 互反空间点
- 层间连接 ↔ 内部空间纤维  
- 权重矩阵 ↔ 扭转场强度
- 网络深度 ↔ 谱维 d_s
- 前向传播 ↔ 跨维信息流动

作者: AI Research Assistant
日期: 2026-03-18
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
import torchvision
import torchvision.transforms as transforms
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, Tuple, List, Dict
import time
from collections import defaultdict


# =============================================================================
# 第一部分: 核心数学工具 - Clifford代数与扭转场
# =============================================================================

class CliffordAlgebra:
    """
    Clifford代数 Cl(3,1) 的实现
    用于神经网络的数学基础
    """
    
    def __init__(self, device='cuda'):
        self.device = device
        self.dim = 4  # 时空维度
        self.clifford_dim = 16  # 2^4 = 16维Clifford代数
        
        # Dirac矩阵表示 (4x4实矩阵)
        self.gamma_matrices = self._init_gamma_matrices()
        
    def _init_gamma_matrices(self):
        """初始化Dirac gamma矩阵"""
        gamma = []
        
        # γ^0 (时间分量)
        gamma_0 = torch.tensor([
            [0, 0, 1, 0],
            [0, 0, 0, 1],
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=torch.float32, device=self.device)
        gamma.append(gamma_0)
        
        # γ^1 (空间x)
        gamma_1 = torch.tensor([
            [0, 0, 0, 1],
            [0, 0, 1, 0],
            [0, -1, 0, 0],
            [-1, 0, 0, 0]
        ], dtype=torch.float32, device=self.device)
        gamma.append(gamma_1)
        
        # γ^2 (空间y)
        gamma_2 = torch.tensor([
            [0, 0, 0, -1],
            [0, 0, 1, 0],
            [0, 1, 0, 0],
            [-1, 0, 0, 0]
        ], dtype=torch.float32, device=self.device)
        gamma.append(gamma_2)
        
        # γ^3 (空间z)
        gamma_3 = torch.tensor([
            [0, 0, 1, 0],
            [0, 0, 0, -1],
            [-1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=torch.float32, device=self.device)
        gamma.append(gamma_3)
        
        return gamma
    
    def anticommutator(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        """计算反对易子 {a, b} = ab + ba"""
        return torch.matmul(a, b) + torch.matmul(b, a)
    
    def clifford_multiply(self, a: int, b: int) -> Tuple[int, float]:
        """
        Clifford代数乘法
        返回 (结果基元索引, 符号)
        """
        # 简化的Clifford乘法实现
        # 实际实现需要完整的基元乘法表
        return (a ^ b, 1.0)  # 简化: 使用XOR作为指标运算
    
    def embed_vector(self, v: torch.Tensor) -> torch.Tensor:
        """
        将向量嵌入Clifford代数
        v: [batch, 4] -> [batch, 16]
        """
        batch_size = v.shape[0]
        embedded = torch.zeros(batch_size, 16, device=self.device)
        embedded[:, 0] = 1.0  # 标量部分
        embedded[:, 1:5] = v  # 向量部分
        return embedded


class SpectralDimension:
    """
    谱维自适应管理器
    根据输入复杂度动态调整网络深度
    """
    
    def __init__(
        self,
        d_s_min: float = 2.0,
        d_s_max: float = 8.0,
        adaptation_rate: float = 0.1,
        device='cuda'
    ):
        self.d_s_min = d_s_min  # 最小谱维 (类比最短波长)
        self.d_s_max = d_s_max  # 最大谱维 (类比最长波长)
        self.adaptation_rate = adaptation_rate
        self.device = device
        
        # 当前谱维状态
        self.current_d_s = nn.Parameter(
            torch.tensor(4.0, device=device),
            requires_grad=True
        )
        
        # 谱维流动历史
        self.d_s_history = []
        
    def compute_complexity(self, x: torch.Tensor) -> torch.Tensor:
        """
        计算输入复杂度
        使用梯度信息和熵作为复杂度度量
        """
        # 基于梯度的复杂度估计
        grad_magnitude = torch.abs(x - x.mean(dim=0, keepdim=True))
        complexity = grad_magnitude.mean() + grad_magnitude.std()
        
        # 归一化到[0, 1]
        complexity = torch.tanh(complexity)
        return complexity
    
    def update_spectral_dimension(
        self,
        x: torch.Tensor,
        target_loss: Optional[torch.Tensor] = None
    ) -> float:
        """
        根据输入复杂度和损失更新谱维
        流动方程: d(d_s)/dt = -γ(d_s - d_target) + ξ(t)
        """
        complexity = self.compute_complexity(x)
        
        # 目标谱维与复杂度相关
        # 高复杂度 -> 高谱维 (需要更深层网络)
        d_target = self.d_s_min + complexity * (self.d_s_max - self.d_s_min)
        
        if target_loss is not None:
            # 损失大时增加谱维以增强表达能力
            loss_factor = torch.sigmoid(target_loss - 1.0)
            d_target = d_target + loss_factor * (self.d_s_max - d_target)
        
        # 谱维流动
        delta_d_s = -self.adaptation_rate * (self.current_d_s - d_target)
        self.current_d_s.data += delta_d_s
        
        # 边界约束
        self.current_d_s.data.clamp_(self.d_s_min, self.d_s_max)
        
        current_value = self.current_d_s.item()
        self.d_s_history.append(current_value)
        
        return current_value
    
    def get_effective_depth(self, base_depth: int) -> int:
        """
        根据当前谱维计算有效网络深度
        d_s ≈ 4 对应标准深度
        d_s > 4 对应更深网络
        d_s < 4 对应更浅网络
        """
        depth_scaling = self.current_d_s.item() / 4.0
        effective_depth = max(1, int(base_depth * depth_scaling))
        return effective_depth


# =============================================================================
# 第二部分: 扭转神经网络核心组件
# =============================================================================

class TorsionField(nn.Module):
    """
    扭转场模块
    模拟时空扭转对神经元连接的扭曲效应
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        torsion_order: int = 2,
        torsion_strength: float = 0.1,
        device='cuda'
    ):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.torsion_order = torsion_order  # 扭转阶数 (1, 2, 3 对应不同规范群)
        self.torsion_strength = torsion_strength
        self.device = device
        
        # 标准权重 (互反空间)
        self.weight = nn.Parameter(
            torch.randn(out_features, in_features, device=device) * 0.01
        )
        self.bias = nn.Parameter(torch.zeros(out_features, device=device))
        
        # 扭转场张量 (内部空间)
        # τ_{μνα} 描述纤维的扭转
        self.torsion_field = nn.Parameter(
            torch.randn(
                torsion_order,
                out_features,
                in_features,
                device=device
            ) * torsion_strength
        )
        
        # 扭转耦合系数
        self.torsion_coupling = nn.Parameter(torch.tensor(1.0, device=device))
        
    def compute_torsion_effect(self, x: torch.Tensor) -> torch.Tensor:
        """
        计算扭转场对输入的扭曲效应
        模拟信息在内部空间纤维上的传播
        """
        batch_size = x.shape[0]
        
        # 基础线性变换
        base_output = F.linear(x, self.weight, self.bias)
        
        # 扭转修正
        # 不同扭转阶数对应不同频率的扭曲
        torsion_correction = torch.zeros_like(base_output)
        
        for n in range(self.torsion_order):
            # n阶扭转分量
            torsion_n = self.torsion_field[n]
            
            # 扭转导致的非线性扭曲
            # 使用正弦函数模拟螺旋型扭转
            # 先计算线性变换，然后应用非线性扭曲
            linear_out = F.linear(x, torsion_n)
            phase = 2 * np.pi * (n + 1) * linear_out / (linear_out.abs().mean() + 1e-8)
            twisted = torch.sin(phase) * linear_out
            
            torsion_correction += twisted / (n + 1)  # 高阶扭转衰减
        
        # 组合基础流和扭转流
        coupling = torch.sigmoid(self.torsion_coupling)
        output = base_output + coupling * torsion_correction
        
        return output
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.compute_torsion_effect(x)
    
    def get_torsion_energy(self) -> torch.Tensor:
        """
        计算扭转场的"能量" (正则化项)
        用于约束扭转强度,防止过拟合
        """
        return torch.sum(self.torsion_field ** 2)


class ReciprocalInternalLayer(nn.Module):
    """
    互反-内部空间耦合层
    实现信息在互反空间(d=4)和内部空间(d_s维)之间的流动
    """
    
    def __init__(
        self,
        reciprocal_dim: int,
        internal_dim: int,
        spectral_dim_manager: SpectralDimension,
        device='cuda'
    ):
        super().__init__()
        self.reciprocal_dim = reciprocal_dim  # 互反空间维度 (通常4)
        self.internal_dim = internal_dim      # 内部空间纤维维度
        self.spectral_manager = spectral_dim_manager
        self.device = device
        
        # 互反空间内部连接
        self.reciprocal_transform = TorsionField(
            reciprocal_dim,
            reciprocal_dim,
            torsion_order=2,
            device=device
        )
        
        # 内部空间纤维连接
        self.internal_transform = TorsionField(
            internal_dim,
            internal_dim,
            torsion_order=3,
            device=device
        )
        
        # 跨空间映射
        self.reciprocal_to_internal = nn.Linear(reciprocal_dim, internal_dim)
        self.internal_to_reciprocal = nn.Linear(internal_dim, reciprocal_dim)
        
        # 流动门控
        self.flow_gate = nn.Parameter(torch.tensor(0.5, device=device))
        
    def forward(self, x_reciprocal: torch.Tensor, x_internal: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播: 信息在互反空间和内部空间之间流动
        
        Returns:
            (互反空间输出, 内部空间输出)
        """
        batch_size = x_reciprocal.shape[0]
        
        if x_internal is None:
            x_internal = torch.zeros(batch_size, self.internal_dim, device=self.device)
        
        # 互反空间变换
        h_reciprocal = self.reciprocal_transform(x_reciprocal)
        h_reciprocal = F.layer_norm(h_reciprocal, h_reciprocal.shape[1:])
        h_reciprocal = F.gelu(h_reciprocal)
        
        # 内部空间变换
        h_internal = self.internal_transform(x_internal)
        h_internal = F.layer_norm(h_internal, h_internal.shape[1:])
        h_internal = F.gelu(h_internal)
        
        # 跨维度流动
        gate = torch.sigmoid(self.flow_gate)
        
        # 互反 -> 内部
        flow_to_internal = self.reciprocal_to_internal(h_reciprocal)
        h_internal = h_internal + gate * flow_to_internal
        
        # 内部 -> 互反
        flow_to_reciprocal = self.internal_to_reciprocal(h_internal)
        h_reciprocal = h_reciprocal + gate * flow_to_reciprocal
        
        return h_reciprocal, h_internal


# =============================================================================
# 第三部分: 完整TNN架构
# =============================================================================

class TorsionNeuralNetwork(nn.Module):
    """
    扭转神经网络 (TNN)
    基于统一场理论的几何化神经网络实现
    """
    
    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        hidden_dims: List[int] = [256, 256, 256],
        internal_dim: int = 64,
        use_spectral_adaptation: bool = True,
        torsion_strength: float = 0.1,
        device='cuda'
    ):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.hidden_dims = hidden_dims
        self.internal_dim = internal_dim
        self.use_spectral_adaptation = use_spectral_adaptation
        self.device = device
        
        # 谱维管理器
        if use_spectral_adaptation:
            self.spectral_manager = SpectralDimension(device=device)
        else:
            self.spectral_manager = None
        
        # 输入投影 (将输入映射到互反空间)
        self.input_projection = nn.Linear(input_dim, 4)
        
        # 互反-内部耦合层堆叠
        self.layers = nn.ModuleList()
        prev_dim = 4
        for hidden_dim in hidden_dims:
            layer = ReciprocalInternalLayer(
                reciprocal_dim=prev_dim,
                internal_dim=internal_dim,
                spectral_dim_manager=self.spectral_manager,
                device=device
            )
            self.layers.append(layer)
            prev_dim = 4  # 互反空间保持4维
        
        # 输出投影
        self.output_projection = nn.Sequential(
            nn.Linear(4, 128),
            nn.GELU(),
            nn.LayerNorm(128),
            nn.Linear(128, output_dim)
        )
        
        # 内部空间记忆 (可学习)
        self.internal_memory = nn.Parameter(
            torch.randn(1, internal_dim, device=device) * 0.01
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        """
        batch_size = x.shape[0]
        
        # 输入投影到互反空间
        x_reciprocal = self.input_projection(x)
        
        # 扩展内部记忆到batch大小
        x_internal = self.internal_memory.expand(batch_size, -1)
        
        # 通过耦合层
        for layer in self.layers:
            x_reciprocal, x_internal = layer(x_reciprocal, x_internal)
        
        # 输出投影
        output = self.output_projection(x_reciprocal)
        
        return output
    
    def get_regularization_loss(self) -> torch.Tensor:
        """
        获取扭转场正则化损失
        """
        reg_loss = torch.tensor(0.0, device=self.device)
        for layer in self.layers:
            reg_loss += layer.reciprocal_transform.get_torsion_energy()
            reg_loss += layer.internal_transform.get_torsion_energy()
        return reg_loss * 0.001  # 正则化系数
    
    def get_spectral_dimension(self) -> float:
        """获取当前谱维"""
        if self.spectral_manager is not None:
            return self.spectral_manager.current_d_s.item()
        return 4.0


class AdaptiveDepthTNN(nn.Module):
    """
    自适应深度TNN
    根据谱维动态调整有效深度
    """
    
    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        base_depth: int = 6,
        base_width: int = 128,
        device='cuda'
    ):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.base_depth = base_depth
        self.base_width = base_width
        self.device = device
        
        # 谱维管理器
        self.spectral_manager = SpectralDimension(
            d_s_min=2.0,
            d_s_max=10.0,
            device=device
        )
        
        # 创建所有可能的层
        self.all_layers = nn.ModuleList()
        
        # 输入层
        self.input_proj = nn.Linear(input_dim, base_width)
        
        # 扭转层
        for i in range(base_depth):
            layer = nn.ModuleDict({
                'torsion': TorsionField(
                    base_width,
                    base_width,
                    torsion_order=min(i+1, 4),
                    device=device
                ),
                'norm': nn.LayerNorm(base_width),
                'dropout': nn.Dropout(0.1)
            })
            self.all_layers.append(layer)
        
        # 输出层
        self.output_proj = nn.Linear(base_width, output_dim)
        
        # 深度门控 (学习何时停止)
        self.depth_gates = nn.Parameter(torch.ones(base_depth) * 0.5)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播,根据谱维选择有效深度"""
        batch_size = x.shape[0]
        
        # 输入投影
        h = F.gelu(self.input_proj(x))
        
        # 根据谱维确定有效深度
        effective_depth = self.spectral_manager.get_effective_depth(self.base_depth)
        
        # 通过扭转层
        for i in range(effective_depth):
            layer = self.all_layers[i]
            
            # 扭转变换
            h_new = layer['torsion'](h)
            h_new = layer['norm'](h_new)
            h_new = F.gelu(h_new)
            h_new = layer['dropout'](h_new)
            
            # 残差连接
            gate = torch.sigmoid(self.depth_gates[i])
            h = h + gate * h_new
        
        # 输出
        output = self.output_proj(h)
        return output
    
    def update_spectral_dimension(self, x: torch.Tensor, loss: Optional[torch.Tensor] = None):
        """更新谱维"""
        return self.spectral_manager.update_spectral_dimension(x, loss)
    
    def get_spectral_dimension(self) -> float:
        """获取当前谱维"""
        return self.spectral_manager.current_d_s.item()


# =============================================================================
# 第四部分: 用于图像数据的TNN变体
# =============================================================================

class TorsionConv2d(nn.Module):
    """
    扭转卷积层
    将扭转场概念扩展到卷积操作
    """
    
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int = 3,
        torsion_order: int = 2,
        torsion_strength: float = 0.05,
        device='cuda'
    ):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.torsion_order = torsion_order
        self.device = device
        
        # 标准卷积权重
        self.weight = nn.Parameter(
            torch.randn(
                out_channels,
                in_channels,
                kernel_size,
                kernel_size,
                device=device
            ) * 0.1
        )
        self.bias = nn.Parameter(torch.zeros(out_channels, device=device))
        
        # 扭转场 (空间变化的扭曲)
        self.torsion_fields = nn.ParameterList([
            nn.Parameter(torch.randn(
                out_channels,
                in_channels,
                kernel_size,
                kernel_size,
                device=device
            ) * torsion_strength / (i+1))
            for i in range(torsion_order)
        ])
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        扭转卷积前向传播
        """
        # 基础卷积
        base_output = F.conv2d(
            x, self.weight, self.bias,
            padding=self.kernel_size // 2
        )
        
        # 扭转修正
        torsion_output = torch.zeros_like(base_output)
        
        for i, torsion_field in enumerate(self.torsion_fields):
            # 计算扭转效应
            torsion_conv = F.conv2d(
                x, torsion_field,
                padding=self.kernel_size // 2
            )
            
            # 非线性扭曲 (模拟螺旋型扭转)
            twisted = torch.sin(2 * np.pi * (i+1) * torsion_conv)
            torsion_output += twisted / (i + 1)
        
        # 组合
        output = base_output + 0.1 * torsion_output
        return output


class TNNEncoder(nn.Module):
    """
    基于扭转场的编码器 (用于图像)
    """
    
    def __init__(
        self,
        in_channels: int = 3,
        latent_dim: int = 128,
        device='cuda'
    ):
        super().__init__()
        self.device = device
        
        # 特征提取层
        self.conv_layers = nn.Sequential(
            TorsionConv2d(in_channels, 32, kernel_size=3, device=device),
            nn.BatchNorm2d(32),
            nn.GELU(),
            nn.MaxPool2d(2),  # /2
            
            TorsionConv2d(32, 64, kernel_size=3, device=device),
            nn.BatchNorm2d(64),
            nn.GELU(),
            nn.MaxPool2d(2),  # /4
            
            TorsionConv2d(64, 128, kernel_size=3, device=device),
            nn.BatchNorm2d(128),
            nn.GELU(),
            nn.AdaptiveAvgPool2d(1),  # 全局平均
        )
        
        # 潜在空间投影
        self.fc = nn.Sequential(
            nn.Linear(128, 256),
            nn.GELU(),
            nn.LayerNorm(256),
            nn.Linear(256, latent_dim)
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.conv_layers(x)
        features = features.view(features.size(0), -1)
        latent = self.fc(features)
        return latent


class TNNForImageClassification(nn.Module):
    """
    用于图像分类的完整TNN模型
    """
    
    def __init__(
        self,
        num_classes: int = 10,
        in_channels: int = 3,
        img_size: int = 32,
        device='cuda'
    ):
        super().__init__()
        self.device = device
        
        # 编码器
        self.encoder = TNNEncoder(
            in_channels=in_channels,
            latent_dim=256,
            device=device
        )
        
        # 分类头 (使用扭转层)
        self.classifier = nn.Sequential(
            TorsionField(256, 128, torsion_order=2, device=device),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(0.3),
            
            TorsionField(128, 64, torsion_order=2, device=device),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(0.3),
            
            nn.Linear(64, num_classes)
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        latent = self.encoder(x)
        logits = self.classifier(latent)
        return logits


# =============================================================================
# 第五部分: 训练与评估工具
# =============================================================================

def train_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    optimizer: optim.Optimizer,
    criterion: nn.Module,
    device: str = 'cuda',
    use_torsion_reg: bool = True
) -> Dict[str, float]:
    """
    训练一个epoch
    """
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0
    
    for batch_idx, (data, target) in enumerate(dataloader):
        data, target = data.to(device), target.to(device)
        
        optimizer.zero_grad()
        
        # 前向传播
        output = model(data)
        
        # 基础损失
        loss = criterion(output, target)
        
        # 添加扭转场正则化
        if use_torsion_reg and hasattr(model, 'get_regularization_loss'):
            reg_loss = model.get_regularization_loss()
            loss = loss + reg_loss
        
        # 反向传播
        loss.backward()
        optimizer.step()
        
        # 统计
        total_loss += loss.item()
        pred = output.argmax(dim=1)
        correct += pred.eq(target).sum().item()
        total += target.size(0)
    
    avg_loss = total_loss / len(dataloader)
    accuracy = 100.0 * correct / total
    
    return {
        'loss': avg_loss,
        'accuracy': accuracy
    }


def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: str = 'cuda'
) -> Dict[str, float]:
    """
    评估模型
    """
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for data, target in dataloader:
            data, target = data.to(device), target.to(device)
            
            output = model(data)
            loss = criterion(output, target)
            
            total_loss += loss.item()
            pred = output.argmax(dim=1)
            correct += pred.eq(target).sum().item()
            total += target.size(0)
    
    avg_loss = total_loss / len(dataloader)
    accuracy = 100.0 * correct / total
    
    return {
        'loss': avg_loss,
        'accuracy': accuracy
    }


def get_mnist_loaders(batch_size: int = 128, data_dir: str = './data'):
    """获取MNIST数据加载器"""
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    train_dataset = torchvision.datasets.MNIST(
        data_dir, train=True, download=True, transform=transform
    )
    test_dataset = torchvision.datasets.MNIST(
        data_dir, train=False, download=True, transform=transform
    )
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    return train_loader, test_loader


def get_cifar10_loaders(batch_size: int = 128, data_dir: str = './data'):
    """获取CIFAR-10数据加载器"""
    transform_train = transforms.Compose([
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    
    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    
    train_dataset = torchvision.datasets.CIFAR10(
        data_dir, train=True, download=True, transform=transform_train
    )
    test_dataset = torchvision.datasets.CIFAR10(
        data_dir, train=False, download=True, transform=transform_test
    )
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=2)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=2)
    
    return train_loader, test_loader


# =============================================================================
# 第六部分: 对比基线模型
# =============================================================================

class StandardMLP(nn.Module):
    """标准MLP基线"""
    
    def __init__(self, input_dim: int, hidden_dims: List[int], output_dim: int):
        super().__init__()
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.GELU(),
                nn.Dropout(0.1)
            ])
            prev_dim = hidden_dim
        
        layers.append(nn.Linear(prev_dim, output_dim))
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)


class StandardCNN(nn.Module):
    """标准CNN基线"""
    
    def __init__(self, num_classes: int = 10, in_channels: int = 3):
        super().__init__()
        
        self.features = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
            
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),
            
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        
        self.classifier = nn.Sequential(
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x


# =============================================================================
# 第七部分: 主实验脚本
# =============================================================================

def run_mnist_experiment(
    epochs: int = 10,
    batch_size: int = 128,
    lr: float = 0.001,
    device: str = 'cuda'
) -> Dict:
    """运行MNIST对比实验"""
    
    print("="*60)
    print("MNIST手写数字识别实验")
    print("="*60)
    
    # 数据加载
    train_loader, test_loader = get_mnist_loaders(batch_size)
    
    results = {}
    
    # 1. 标准MLP
    print("\n[1/3] 训练标准MLP...")
    mlp = StandardMLP(784, [256, 256, 256], 10).to(device)
    optimizer = optim.Adam(mlp.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    
    mlp_history = {'train_acc': [], 'test_acc': [], 'train_loss': []}
    start_time = time.time()
    
    for epoch in range(epochs):
        train_stats = train_epoch(mlp, train_loader, optimizer, criterion, device, use_torsion_reg=False)
        test_stats = evaluate(mlp, test_loader, criterion, device)
        mlp_history['train_acc'].append(train_stats['accuracy'])
        mlp_history['test_acc'].append(test_stats['accuracy'])
        mlp_history['train_loss'].append(train_stats['loss'])
        print(f"  Epoch {epoch+1}/{epochs}: Train Acc={train_stats['accuracy']:.2f}%, Test Acc={test_stats['accuracy']:.2f}%")
    
    mlp_time = time.time() - start_time
    mlp_params = sum(p.numel() for p in mlp.parameters())
    
    results['MLP'] = {
        'model': mlp,
        'history': mlp_history,
        'final_test_acc': mlp_history['test_acc'][-1],
        'training_time': mlp_time,
        'params': mlp_params
    }
    
    # 2. TNN (我们的模型)
    print("\n[2/3] 训练TNN (扭转神经网络)...")
    tnn = TorsionNeuralNetwork(
        input_dim=784,
        output_dim=10,
        hidden_dims=[256, 256, 256],
        internal_dim=64,
        device=device
    ).to(device)
    
    optimizer = optim.Adam(tnn.parameters(), lr=lr)
    
    tnn_history = {'train_acc': [], 'test_acc': [], 'train_loss': [], 'spectral_dim': []}
    start_time = time.time()
    
    for epoch in range(epochs):
        train_stats = train_epoch(tnn, train_loader, optimizer, criterion, device, use_torsion_reg=True)
        test_stats = evaluate(tnn, test_loader, criterion, device)
        tnn_history['train_acc'].append(train_stats['accuracy'])
        tnn_history['test_acc'].append(test_stats['accuracy'])
        tnn_history['train_loss'].append(train_stats['loss'])
        if tnn.spectral_manager:
            tnn_history['spectral_dim'].append(tnn.get_spectral_dimension())
        print(f"  Epoch {epoch+1}/{epochs}: Train Acc={train_stats['accuracy']:.2f}%, Test Acc={test_stats['accuracy']:.2f}%, d_s={tnn.get_spectral_dimension():.2f}")
    
    tnn_time = time.time() - start_time
    tnn_params = sum(p.numel() for p in tnn.parameters())
    
    results['TNN'] = {
        'model': tnn,
        'history': tnn_history,
        'final_test_acc': tnn_history['test_acc'][-1],
        'training_time': tnn_time,
        'params': tnn_params
    }
    
    # 3. 自适应深度TNN
    print("\n[3/3] 训练自适应深度TNN...")
    adaptive_tnn = AdaptiveDepthTNN(
        input_dim=784,
        output_dim=10,
        base_depth=6,
        base_width=128,
        device=device
    ).to(device)
    
    optimizer = optim.Adam(adaptive_tnn.parameters(), lr=lr)
    
    adaptive_history = {'train_acc': [], 'test_acc': [], 'train_loss': [], 'spectral_dim': []}
    start_time = time.time()
    
    for epoch in range(epochs):
        train_stats = train_epoch(adaptive_tnn, train_loader, optimizer, criterion, device, use_torsion_reg=False)
        test_stats = evaluate(adaptive_tnn, test_loader, criterion, device)
        adaptive_history['train_acc'].append(train_stats['accuracy'])
        adaptive_history['test_acc'].append(test_stats['accuracy'])
        adaptive_history['train_loss'].append(train_stats['loss'])
        adaptive_history['spectral_dim'].append(adaptive_tnn.get_spectral_dimension())
        print(f"  Epoch {epoch+1}/{epochs}: Train Acc={train_stats['accuracy']:.2f}%, Test Acc={test_stats['accuracy']:.2f}%, d_s={adaptive_tnn.get_spectral_dimension():.2f}")
    
    adaptive_time = time.time() - start_time
    adaptive_params = sum(p.numel() for p in adaptive_tnn.parameters())
    
    results['Adaptive-TNN'] = {
        'model': adaptive_tnn,
        'history': adaptive_history,
        'final_test_acc': adaptive_history['test_acc'][-1],
        'training_time': adaptive_time,
        'params': adaptive_params
    }
    
    return results


def run_cifar10_experiment(
    epochs: int = 50,
    batch_size: int = 128,
    lr: float = 0.001,
    device: str = 'cuda'
) -> Dict:
    """运行CIFAR-10对比实验"""
    
    print("="*60)
    print("CIFAR-10图像分类实验")
    print("="*60)
    
    # 数据加载
    train_loader, test_loader = get_cifar10_loaders(batch_size)
    
    results = {}
    criterion = nn.CrossEntropyLoss()
    
    # 1. 标准CNN
    print("\n[1/2] 训练标准CNN...")
    cnn = StandardCNN(num_classes=10, in_channels=3).to(device)
    optimizer = optim.Adam(cnn.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    cnn_history = {'train_acc': [], 'test_acc': [], 'train_loss': []}
    start_time = time.time()
    
    for epoch in range(epochs):
        train_stats = train_epoch(cnn, train_loader, optimizer, criterion, device, use_torsion_reg=False)
        test_stats = evaluate(cnn, test_loader, criterion, device)
        cnn_history['train_acc'].append(train_stats['accuracy'])
        cnn_history['test_acc'].append(test_stats['accuracy'])
        cnn_history['train_loss'].append(train_stats['loss'])
        scheduler.step()
        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1}/{epochs}: Train Acc={train_stats['accuracy']:.2f}%, Test Acc={test_stats['accuracy']:.2f}%")
    
    cnn_time = time.time() - start_time
    cnn_params = sum(p.numel() for p in cnn.parameters())
    
    results['CNN'] = {
        'model': cnn,
        'history': cnn_history,
        'final_test_acc': cnn_history['test_acc'][-1],
        'training_time': cnn_time,
        'params': cnn_params
    }
    
    # 2. TNN-CNN
    print("\n[2/2] 训练TNN-CNN...")
    tnn_cnn = TNNForImageClassification(num_classes=10, in_channels=3, device=device).to(device)
    optimizer = optim.Adam(tnn_cnn.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    tnn_cnn_history = {'train_acc': [], 'test_acc': [], 'train_loss': []}
    start_time = time.time()
    
    for epoch in range(epochs):
        train_stats = train_epoch(tnn_cnn, train_loader, optimizer, criterion, device, use_torsion_reg=True)
        test_stats = evaluate(tnn_cnn, test_loader, criterion, device)
        tnn_cnn_history['train_acc'].append(train_stats['accuracy'])
        tnn_cnn_history['test_acc'].append(test_stats['accuracy'])
        tnn_cnn_history['train_loss'].append(train_stats['loss'])
        scheduler.step()
        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1}/{epochs}: Train Acc={train_stats['accuracy']:.2f}%, Test Acc={test_stats['accuracy']:.2f}%")
    
    tnn_cnn_time = time.time() - start_time
    tnn_cnn_params = sum(p.numel() for p in tnn_cnn.parameters())
    
    results['TNN-CNN'] = {
        'model': tnn_cnn,
        'history': tnn_cnn_history,
        'final_test_acc': tnn_cnn_history['test_acc'][-1],
        'training_time': tnn_cnn_time,
        'params': tnn_cnn_params
    }
    
    return results


def plot_results(mnist_results: Dict, cifar_results: Dict, save_path: str = './results'):
    """
    可视化实验结果
    """
    import os
    os.makedirs(save_path, exist_ok=True)
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    # MNIST准确率曲线
    ax = axes[0, 0]
    for name, data in mnist_results.items():
        ax.plot(data['history']['test_acc'], label=f"{name} ({data['final_test_acc']:.1f}%)")
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Test Accuracy (%)')
    ax.set_title('MNIST Test Accuracy')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # MNIST损失曲线
    ax = axes[0, 1]
    for name, data in mnist_results.items():
        ax.plot(data['history']['train_loss'], label=name)
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Training Loss')
    ax.set_title('MNIST Training Loss')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 谱维演化 (TNN)
    ax = axes[0, 2]
    if 'TNN' in mnist_results and 'spectral_dim' in mnist_results['TNN']['history']:
        ax.plot(mnist_results['TNN']['history']['spectral_dim'], label='TNN', color='blue')
    if 'Adaptive-TNN' in mnist_results and 'spectral_dim' in mnist_results['Adaptive-TNN']['history']:
        ax.plot(mnist_results['Adaptive-TNN']['history']['spectral_dim'], label='Adaptive-TNN', color='red')
    ax.axhline(y=4.0, color='gray', linestyle='--', label='d_s = 4 (baseline)')
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Spectral Dimension d_s')
    ax.set_title('Spectral Dimension Evolution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # CIFAR-10准确率
    ax = axes[1, 0]
    for name, data in cifar_results.items():
        ax.plot(data['history']['test_acc'], label=f"{name} ({data['final_test_acc']:.1f}%)")
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Test Accuracy (%)')
    ax.set_title('CIFAR-10 Test Accuracy')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 性能对比柱状图
    ax = axes[1, 1]
    models = list(mnist_results.keys())
    accuracies = [mnist_results[m]['final_test_acc'] for m in models]
    times = [mnist_results[m]['training_time'] for m in models]
    
    x = np.arange(len(models))
    width = 0.35
    
    ax2 = ax.twinx()
    bars1 = ax.bar(x - width/2, accuracies, width, label='Accuracy (%)', color='steelblue')
    bars2 = ax2.bar(x + width/2, times, width, label='Time (s)', color='coral')
    
    ax.set_xlabel('Model')
    ax.set_ylabel('Accuracy (%)')
    ax2.set_ylabel('Training Time (s)')
    ax.set_title('MNIST Performance Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    
    # 添加数值标签
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8)
    
    # 参数量对比
    ax = axes[1, 2]
    all_models = list(mnist_results.keys()) + list(cifar_results.keys())
    all_params = [mnist_results[m]['params']/1e6 if m in mnist_results else cifar_results[m]['params']/1e6 for m in all_models]
    colors = ['steelblue']*len(mnist_results) + ['coral']*len(cifar_results)
    
    bars = ax.barh(all_models, all_params, color=colors)
    ax.set_xlabel('Parameters (Millions)')
    ax.set_title('Model Size Comparison')
    
    for bar, val in zip(bars, all_params):
        ax.text(val + 0.05, bar.get_y() + bar.get_height()/2, 
                f'{val:.2f}M', va='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(f'{save_path}/tnn_benchmark_results.png', dpi=150, bbox_inches='tight')
    print(f"\n结果图表已保存至: {save_path}/tnn_benchmark_results.png")
    plt.close()


def print_comparison_table(mnist_results: Dict, cifar_results: Dict):
    """打印对比表格"""
    print("\n" + "="*80)
    print("实验结果对比表")
    print("="*80)
    
    print("\n【MNIST手写数字识别】")
    print("-"*80)
    print(f"{'模型':<20} {'测试准确率':>12} {'训练时间(s)':>12} {'参数量':>12}")
    print("-"*80)
    for name, data in mnist_results.items():
        print(f"{name:<20} {data['final_test_acc']:>11.2f}% {data['training_time']:>11.1f}s {data['params']/1e6:>11.3f}M")
    
    print("\n【CIFAR-10图像分类】")
    print("-"*80)
    print(f"{'模型':<20} {'测试准确率':>12} {'训练时间(s)':>12} {'参数量':>12}")
    print("-"*80)
    for name, data in cifar_results.items():
        print(f"{name:<20} {data['final_test_acc']:>11.2f}% {data['training_time']:>11.1f}s {data['params']/1e6:>11.3f}M")
    
    print("="*80)


def main():
    """
    主函数: 运行所有实验
    """
    # 检查CUDA可用性
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"使用设备: {device}")
    
    # 设置随机种子
    torch.manual_seed(42)
    np.random.seed(42)
    
    # 运行MNIST实验
    print("\n开始MNIST实验...")
    mnist_results = run_mnist_experiment(
        epochs=10,
        batch_size=128,
        lr=0.001,
        device=device
    )
    
    # 运行CIFAR-10实验
    print("\n开始CIFAR-10实验...")
    cifar_results = run_cifar10_experiment(
        epochs=50,
        batch_size=128,
        lr=0.001,
        device=device
    )
    
    # 打印对比表格
    print_comparison_table(mnist_results, cifar_results)
    
    # 绘制结果图表
    plot_results(mnist_results, cifar_results)
    
    # 保存详细结果
    import json
    summary = {
        'mnist': {
            name: {
                'final_test_acc': data['final_test_acc'],
                'training_time': data['training_time'],
                'params': data['params']
            }
            for name, data in mnist_results.items()
        },
        'cifar10': {
            name: {
                'final_test_acc': data['final_test_acc'],
                'training_time': data['training_time'],
                'params': data['params']
            }
            for name, data in cifar_results.items()
        }
    }
    
    with open('./results/tnn_experiment_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n实验完成!")
    
    return mnist_results, cifar_results


if __name__ == "__main__":
    main()
