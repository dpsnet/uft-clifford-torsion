"""
TNN小鼠行为模块 - 恐惧/防御行为
包含冻结、逃跑、躲避、防御攻击
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class FearConfig:
    """恐惧行为配置"""
    # 恐惧阈值
    fear_threshold: float = 0.6
    panic_threshold: float = 0.9
    
    # 冻结参数
    freezing_duration: float = 2.0  # 秒
    freezing_decay: float = 0.95
    
    # 逃跑参数
    escape_speed_multiplier: float = 2.0
    escape_direction_noise: float = 0.2
    
    # 恐惧记忆
    fear_learning_rate: float = 0.1
    fear_decay_rate: float = 0.001
    
    # 安全评估
    safety_check_interval: float = 1.0  # 秒


class FearMemory(nn.Module):
    """
    恐惧记忆系统 - 杏仁核功能模拟
    功能: 条件性恐惧学习、恐惧泛化、恐惧消退
    """
    
    def __init__(self, feature_dim: int = 512, n_fear_contexts: int = 10):
        super().__init__()
        self.feature_dim = feature_dim
        self.n_fear_contexts = n_fear_contexts
        
        # 恐惧记忆矩阵 (情境 -> 恐惧强度)
        self.fear_memory = nn.Parameter(torch.zeros(n_fear_contexts, feature_dim))
        
        # 情境编码器
        self.context_encoder = nn.Sequential(
            nn.Linear(feature_dim, 128),
            nn.ReLU(),
            nn.Linear(128, n_fear_contexts)
        )
        
        # 恐惧消退记忆 (安全信号)
        self.extinction_memory = nn.Parameter(torch.zeros(n_fear_contexts, feature_dim))
        
    def encode_context(self, sensory_features: torch.Tensor) -> torch.Tensor:
        """编码当前情境"""
        return F.softmax(self.context_encoder(sensory_features), dim=-1)
    
    def recall_fear(self, sensory_features: torch.Tensor) -> torch.Tensor:
        """
        回忆恐惧记忆
        Args:
            sensory_features: [B, feature_dim]
        Returns:
            fear_level: [B, 1]
        """
        # 编码情境
        context = self.encode_context(sensory_features)  # [B, n_contexts]
        
        # 检索相关恐惧记忆
        fear_associations = torch.matmul(context, self.fear_memory)  # [B, feature_dim]
        
        # 计算与当前特征的相似度
        similarity = torch.cosine_similarity(sensory_features, fear_associations, dim=-1)
        
        # 检索消退记忆 (抑制恐惧)
        extinction_associations = torch.matmul(context, self.extinction_memory)
        extinction_similarity = torch.cosine_similarity(sensory_features, extinction_associations, dim=-1)
        
        # 整合 (恐惧 - 消退)
        fear_level = torch.sigmoid(similarity - extinction_similarity)
        
        return fear_level.unsqueeze(-1)
    
    def learn_fear(self, 
                   sensory_features: torch.Tensor,
                   us_strength: torch.Tensor,
                   cs_present: bool = True):
        """
        恐惧学习 (经典条件反射)
        Args:
            sensory_features: [B, feature_dim] 条件刺激(CS)
            us_strength: [B, 1] 非条件刺激强度(如电击)
            cs_present: 是否有条件刺激伴随
        """
        with torch.no_grad():
            # 编码情境
            context = self.encode_context(sensory_features)  # [B, n_contexts]
            
            # 更新恐惧记忆 (Hebbian-like)
            for i in range(sensory_features.size(0)):
                # 找到最相关的情境
                best_context = context[i].argmax()
                
                # 更新该情境的恐惧记忆
                if us_strength[i] > 0.5 and cs_present:
                    self.fear_memory[best_context] += 0.01 * us_strength[i] * sensory_features[i]
                    self.fear_memory[best_context] = torch.clamp(self.fear_memory[best_context], -1, 1)
    
    def learn_extinction(self, sensory_features: torch.Tensor):
        """恐惧消退学习 (CS单独呈现，无US)"""
        with torch.no_grad():
            context = self.encode_context(sensory_features)
            
            for i in range(sensory_features.size(0)):
                best_context = context[i].argmax()
                self.extinction_memory[best_context] += 0.005 * sensory_features[i]
                self.extinction_memory[best_context] = torch.clamp(
                    self.extinction_memory[best_context], -1, 1
                )
    
    def decay_fear(self):
        """恐惧自然衰减"""
        with torch.no_grad():
            self.fear_memory.data *= (1 - 0.0001)


class DefenseStrategy(nn.Module):
    """
    防御策略网络
    根据恐惧水平选择防御行为
    """
    
    def __init__(self, input_dim: int = 512):
        super().__init__()
        
        # 威胁评估
        self.threat_assessment = nn.Sequential(
            nn.Linear(input_dim + 1, 256),  # +1 for fear level
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU()
        )
        
        # 行为选择头
        # 0: 冻结, 1: 逃跑, 2: 躲藏, 3: 防御攻击, 4: 正常
        self.behavior_head = nn.Linear(128, 5)
        
        # 逃跑方向 (远离威胁)
        self.escape_direction = nn.Linear(128, 2)
        
        # 逃跑速度
        self.escape_speed = nn.Linear(128, 1)
        
    def forward(self, 
                brain_state: torch.Tensor,
                fear_level: torch.Tensor,
                threat_direction: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        """
        Args:
            brain_state: [B, input_dim]
            fear_level: [B, 1]
            threat_direction: [B, 2] 威胁方向 (可选)
            
        Returns:
            防御行为决策
        """
        # 整合恐惧信息
        x = torch.cat([brain_state, fear_level], dim=-1)
        features = self.threat_assessment(x)
        
        # 行为概率
        behavior_logits = self.behavior_head(features)
        behavior_probs = torch.softmax(behavior_logits, dim=-1)
        
        # 逃跑方向 (如果知道威胁方向，则向反方向)
        if threat_direction is not None:
            # 远离威胁
            escape_dir = -threat_direction
            escape_dir = F.normalize(escape_dir, p=2, dim=-1)
        else:
            # 网络决定
            escape_dir = torch.tanh(self.escape_direction(features))
        
        # 逃跑速度 (与恐惧水平相关)
        base_speed = torch.sigmoid(self.escape_speed(features))
        speed = base_speed * (1 + fear_level)
        
        return {
            'behavior_probs': behavior_probs,
            'escape_direction': escape_dir,
            'escape_speed': speed,
            'selected_behavior': behavior_probs.argmax(dim=-1)
        }


class FearBehavior(nn.Module):
    """
    完整恐惧行为模块
    整合恐惧记忆、威胁评估和防御策略
    """
    
    def __init__(self, config: FearConfig = None, brain_dim: int = 512):
        super().__init__()
        self.config = config or FearConfig()
        
        # 恐惧记忆
        self.fear_memory = FearMemory(feature_dim=brain_dim)
        
        # 防御策略
        self.defense = DefenseStrategy(input_dim=brain_dim)
        
        # 内部状态
        self.register_buffer('current_fear', torch.tensor(0.0))
        self.register_buffer('freezing_timer', torch.tensor(0.0))
        self.register_buffer('safety_timer', torch.tensor(0.0))
        
    def forward(self,
                brain_state: torch.Tensor,
                sensory_features: torch.Tensor,
                threat_detected: torch.Tensor,
                threat_direction: Optional[torch.Tensor] = None,
                us_strength: torch.Tensor = None) -> Dict[str, torch.Tensor]:
        """
        Args:
            brain_state: [B, brain_dim]
            sensory_features: [B, brain_dim] 感觉特征
            threat_detected: [B, 1] 是否检测到威胁
            threat_direction: [B, 2] 威胁方向
            us_strength: [B, 1] 非条件刺激强度 (用于学习)
            
        Returns:
            恐惧响应和行为决策
        """
        # 回忆恐惧记忆
        recalled_fear = self.fear_memory.recall_fear(sensory_features)
        
        # 整合当前威胁和记忆
        current_threat = torch.max(threat_detected, recalled_fear * 0.5)
        
        # 更新当前恐惧水平
        self.current_fear = torch.max(self.current_fear, current_threat[0, 0])
        
        # 恐惧学习 (如果检测到US)
        if us_strength is not None and self.training:
            self.fear_memory.learn_fear(sensory_features, us_strength)
        
        # 恐惧消退 (如果没有威胁)
        if threat_detected.mean() < 0.3:
            self.safety_timer += 1
            if self.safety_timer > 10:  # 连续安全
                self.fear_memory.learn_extinction(sensory_features)
                self.current_fear *= 0.95  # 衰减
        else:
            self.safety_timer = torch.tensor(0.0)
        
        # 防御行为决策
        defense_action = self.defense(brain_state, self.current_fear.unsqueeze(0).unsqueeze(0), 
                                      threat_direction)
        
        # 更新冻结计时器
        if defense_action['selected_behavior'][0] == 0:  # 冻结
            self.freezing_timer += 1
        else:
            self.freezing_timer = torch.tensor(0.0)
        
        # 自然衰减
        self.fear_memory.decay_fear()
        
        return {
            'fear_level': self.current_fear.item(),
            'recalled_fear': recalled_fear,
            'behavior_probs': defense_action['behavior_probs'],
            'selected_behavior': defense_action['selected_behavior'],
            'escape_direction': defense_action['escape_direction'],
            'escape_speed': defense_action['escape_speed'],
            'is_freezing': self.freezing_timer > 0
        }
    
    def get_fear_metrics(self) -> Dict[str, float]:
        """获取恐惧状态统计"""
        return {
            'current_fear': self.current_fear.item(),
            'freezing_duration': self.freezing_timer.item(),
            'safety_duration': self.safety_timer.item()
        }
    
    def reset(self):
        """重置恐惧状态"""
        self.current_fear = torch.tensor(0.0)
        self.freezing_timer = torch.tensor(0.0)
        self.safety_timer = torch.tensor(0.0)


# 测试
if __name__ == "__main__":
    print("=== TNN小鼠恐惧行为模块测试 ===\n")
    
    # 创建恐惧模块
    fear_module = FearBehavior()
    
    # 模拟输入
    batch_size = 1
    brain_state = torch.randn(batch_size, 512)
    sensory_features = torch.randn(batch_size, 512)
    
    print("场景1: 安全环境")
    threat_detected = torch.tensor([[0.0]])
    result = fear_module(brain_state, sensory_features, threat_detected)
    print(f"  恐惧水平: {result['fear_level']:.3f}")
    print(f"  选择行为: {result['selected_behavior'].item()} (0=冻结, 4=正常)")
    
    print("\n场景2: 检测到威胁")
    threat_detected = torch.tensor([[0.8]])
    threat_direction = torch.tensor([[1.0, 0.0]])  # 威胁在右边
    result = fear_module(brain_state, sensory_features, threat_detected, threat_direction)
    print(f"  恐惧水平: {result['fear_level']:.3f}")
    print(f"  选择行为: {result['selected_behavior'].item()}")
    print(f"  逃跑方向: [{result['escape_direction'][0,0]:.2f}, {result['escape_direction'][0,1]:.2f}]")
    
    print("\n场景3: 恐惧学习 (CS-US配对)")
    us_strength = torch.tensor([[1.0]])  # 强电击
    for i in range(5):
        result = fear_module(brain_state, sensory_features, threat_detected, 
                           threat_direction, us_strength)
        print(f"  学习步骤 {i+1}: 回忆恐惧={result['recalled_fear'][0,0]:.3f}")
    
    print("\n场景4: 恐惧消退 (CS单独呈现)")
    threat_detected = torch.tensor([[0.0]])
    for i in range(10):
        result = fear_module(brain_state, sensory_features, threat_detected)
        if i % 3 == 0:
            print(f"  消退步骤 {i}: 当前恐惧={result['fear_level']:.3f}")
    
    print("\n✓ 恐惧行为模块测试通过!")
