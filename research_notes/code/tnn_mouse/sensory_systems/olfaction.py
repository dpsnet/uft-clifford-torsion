"""
TNN小鼠嗅觉系统
模拟嗅觉受体、嗅球和梨状皮层处理
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List


class OlfactoryReceptors(nn.Module):
    """
    嗅觉受体层
    小鼠有约400种功能性嗅觉受体
    每种受体对特定化学特征敏感
    """
    
    def __init__(self, n_receptors: int = 400, n_features: int = 100):
        super().__init__()
        self.n_receptors = n_receptors
        
        # 受体调谐曲线 (模拟不同受体对不同化学特征的响应)
        # 这是一个可学习的映射，模拟受体的化学敏感性
        self.receptor_tuning = nn.Linear(n_features, n_receptors, bias=False)
        
        # 受体增益 (可塑性)
        self.receptor_gain = nn.Parameter(torch.ones(n_receptors))
        
        # 适应机制 (长时间暴露后敏感性下降)
        self.adaptation_rate = 0.01
        self.running_mean = nn.Parameter(torch.zeros(n_receptors), requires_grad=False)
        
    def forward(self, chemical_features: torch.Tensor) -> torch.Tensor:
        """
        Args:
            chemical_features: [B, n_features] 化学特征向量
        Returns:
            receptor_activations: [B, n_receptors] 受体激活
        """
        # 基础受体响应
        activations = F.relu(self.receptor_tuning(chemical_features))
        
        # 应用增益
        activations = activations * self.receptor_gain
        
        # 归一化 (受体竞争)
        activations = activations / (activations.sum(dim=-1, keepdim=True) + 1e-8)
        
        # 更新running mean (用于适应)
        with torch.no_grad():
            batch_mean = activations.mean(dim=0)
            self.running_mean.data = (1 - self.adaptation_rate) * self.running_mean + \
                                     self.adaptation_rate * batch_mean
        
        # 减去适应水平 (感知适应)
        adapted_activations = F.relu(activations - 0.5 * self.running_mean)
        
        return adapted_activations


class OlfactoryBulb(nn.Module):
    """
    嗅球处理层
    功能: 模式分离、锐化、降噪
    结构: 僧帽细胞、颗粒细胞、球旁细胞
    """
    
    def __init__(self, n_receptors: int = 400, n_mitral: int = 200):
        super().__init__()
        self.n_receptors = n_receptors
        self.n_mitral = n_mitral
        
        # 僧帽细胞 (兴奋性)
        self.mitral_cells = nn.Linear(n_receptors, n_mitral)
        
        # 颗粒细胞 (抑制性，侧抑制)
        self.granular_inhibition = nn.Linear(n_mitral, n_mitral, bias=False)
        
        # 球旁细胞 (前馈抑制)
        self.periglomerular = nn.Linear(n_receptors, n_mitral)
        
    def forward(self, receptor_input: torch.Tensor) -> torch.Tensor:
        """
        Args:
            receptor_input: [B, n_receptors]
        Returns:
            mitral_output: [B, n_mitral]
        """
        # 僧帽细胞兴奋
        mitral_excitation = F.relu(self.mitral_cells(receptor_input))
        
        # 颗粒细胞侧抑制
        lateral_inhibition = torch.sigmoid(self.granular_inhibition(mitral_excitation))
        
        # 球旁细胞前馈抑制
        feedforward_inhibition = torch.sigmoid(self.periglomerular(receptor_input))
        
        # 整合 (兴奋 - 抑制)
        output = mitral_excitation * (1 - lateral_inhibition) * (1 - feedforward_inhibition)
        
        # 归一化 ( winner-take-all 效应)
        output = F.normalize(output, p=2, dim=-1)
        
        return output


class PiriformCortex(nn.Module):
    """
    梨状皮层 - 气味识别和表征
    功能: 从稀疏的嗅球表示中提取气味身份
    特点: 模式完成、联想记忆
    """
    
    def __init__(self, n_mitral: int = 200, n_features: int = 256):
        super().__init__()
        self.n_mitral = n_mitral
        self.n_features = n_features
        
        # 气味表征层
        self.odor_representation = nn.Sequential(
            nn.Linear(n_mitral, n_features),
            nn.LayerNorm(n_features),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        
        # 联想记忆 (Hebbian-like可塑性模拟)
        self.associative_weights = nn.Parameter(torch.eye(n_features) * 0.1)
        
    def forward(self, mitral_input: torch.Tensor, 
                use_association: bool = True) -> torch.Tensor:
        """
        Args:
            mitral_input: [B, n_mitral]
            use_association: 是否使用联想记忆
        Returns:
            odor_identity: [B, n_features]
        """
        # 基础表征
        odor_features = self.odor_representation(mitral_input)
        
        # 联想记忆增强 (模式完成)
        if use_association:
            # 递归联想
            for _ in range(2):  # 2步递归
                odor_features = odor_features + torch.matmul(odor_features, self.associative_weights)
                odor_features = F.relu(odor_features)
                odor_features = F.normalize(odor_features, p=2, dim=-1)
        
        return odor_features


class AmygdalaOlfactory(nn.Module):
    """
    杏仁核嗅觉处理
    功能: 气味-情绪关联
    """
    
    def __init__(self, n_features: int = 256, n_emotions: int = 4):
        super().__init__()
        
        # 情绪评估: 恐惧、吸引、厌恶、中性
        self.emotion_assessment = nn.Linear(n_features, n_emotions)
        
        # 情绪记忆 (条件性恐惧学习)
        self.emotion_memory = nn.Parameter(torch.zeros(n_emotions, n_features))
        
    def forward(self, odor_features: torch.Tensor,
                learning_signal: torch.Tensor = None) -> torch.Tensor:
        """
        Args:
            odor_features: [B, n_features]
            learning_signal: [B, n_emotions] 学习信号 (可选)
        Returns:
            emotion_response: [B, n_emotions]
        """
        # 基础情绪评估
        base_emotion = self.emotion_assessment(odor_features)
        
        # 记忆检索
        memory_emotion = torch.matmul(odor_features, self.emotion_memory.t())
        
        # 整合
        emotion_response = base_emotion + 0.5 * memory_emotion
        
        # 更新记忆 (如果提供学习信号)
        if learning_signal is not None and self.training:
            with torch.no_grad():
                # Hebbian-like更新
                update = torch.matmul(learning_signal.t(), odor_features) / odor_features.size(0)
                self.emotion_memory.data += 0.01 * update
                # 限制记忆大小
                self.emotion_memory.data = torch.clamp(self.emotion_memory.data, -1, 1)
        
        return torch.sigmoid(emotion_response)


class MouseOlfactorySystem(nn.Module):
    """
    小鼠完整嗅觉系统
    
    通路:
    化学分子 -> 嗅觉受体 -> 嗅球 -> 梨状皮层 -> 情绪评估
    """
    
    def __init__(self, 
                 n_receptors: int = 400,
                 n_chemical_features: int = 100,
                 output_dim: int = 256):
        super().__init__()
        
        self.receptors = OlfactoryReceptors(n_receptors, n_chemical_features)
        self.bulb = OlfactoryBulb(n_receptors, n_mitral=200)
        self.piriform = PiriformCortex(n_mitral=200, n_features=output_dim)
        self.amygdala = AmygdalaOlfactory(n_features=output_dim)
        
        self.n_receptors = n_receptors
        self.output_dim = output_dim
        
    def forward(self, 
                chemical_features: torch.Tensor,
                learning_signal: torch.Tensor = None) -> Dict[str, torch.Tensor]:
        """
        Args:
            chemical_features: [B, n_chemical_features] 化学特征
            learning_signal: [B, 4] 情绪学习信号 (可选)
            
        Returns:
            包含各级嗅觉特征的字典
        """
        features = {}
        
        # 嗅觉受体
        receptor_activations = self.receptors(chemical_features)
        features['receptors'] = receptor_activations
        
        # 嗅球
        mitral_output = self.bulb(receptor_activations)
        features['mitral'] = mitral_output
        
        # 梨状皮层
        odor_identity = self.piriform(mitral_output)
        features['piriform'] = odor_identity
        
        # 杏仁核情绪评估
        emotion = self.amygdala(odor_identity, learning_signal)
        features['emotion'] = emotion
        features['output'] = odor_identity
        
        return features
    
    def get_output_dim(self) -> int:
        return self.output_dim


# 测试
if __name__ == "__main__":
    print("=== TNN小鼠嗅觉系统测试 ===\n")
    
    # 创建嗅觉系统
    olfactory = MouseOlfactorySystem()
    
    # 模拟化学输入 (100种化学特征)
    batch_size = 2
    chemical_input = torch.rand(batch_size, 100)  # 浓度值
    
    print(f"化学输入: {chemical_input.shape}")
    
    # 前向传播
    with torch.no_grad():
        features = olfactory(chemical_input)
    
    print(f"\n各级特征:")
    for name, feat in features.items():
        print(f"  {name}: {feat.shape}, 均值={feat.mean():.3f}")
    
    # 测试情绪学习
    print(f"\n测试情绪学习...")
    learning_signal = torch.tensor([[1.0, 0.0, 0.0, 0.0],  # 第一个样本: 恐惧
                                    [0.0, 1.0, 0.0, 0.0]])  # 第二个样本: 吸引
    
    olfactory.train()
    features_learned = olfactory(chemical_input, learning_signal)
    print(f"学习后情绪响应: {features_learned['emotion']}")
    
    print(f"\n总参数量: {sum(p.numel() for p in olfactory.parameters())/1e6:.2f}M")
    
    print("\n✓ 嗅觉系统测试通过!")
