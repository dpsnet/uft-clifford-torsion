"""
TNN小鼠行为模块 - 探索行为
包含开放场地探索、新物体调查、空间学习
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ExplorationConfig:
    """探索行为配置"""
    # 好奇心参数
    curiosity_base: float = 0.5
    curiosity_decay: float = 0.995
    novelty_bonus: float = 1.0
    
    # 探索策略
    exploration_vs_exploitation: float = 0.7  # 0=纯利用, 1=纯探索
    local_search_radius: float = 0.1  # 米
    
    # 空间记忆
    spatial_map_resolution: int = 50  # 50x50网格
    spatial_map_size: float = 1.0  # 1x1米


class SpatialMemory(nn.Module):
    """
    空间记忆模块 - 海马体功能模拟
    功能: 位置细胞、路径整合、地图构建
    """
    
    def __init__(self, map_size: int = 50, feature_dim: int = 256):
        super().__init__()
        self.map_size = map_size
        self.feature_dim = feature_dim
        
        # 位置编码网格 (模拟网格细胞)
        self.grid_cells = nn.Parameter(torch.randn(3, map_size, map_size))
        
        # 位置细胞 (特定位置激活)
        self.place_cell_centers = nn.Parameter(torch.rand(100, 2))  # 100个位置细胞
        self.place_cell_widths = nn.Parameter(torch.ones(100) * 0.1)
        
        # 空间地图 (可更新的记忆)
        self.register_buffer('spatial_map', torch.zeros(map_size, map_size, feature_dim))
        self.register_buffer('visit_count', torch.zeros(map_size, map_size))
        
    def position_to_grid(self, position: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        将连续位置映射到离散网格
        Args:
            position: [B, 2] (x, y) in [0, 1]
        Returns:
            grid_idx: [B, 2] 网格索引
            grid_pos: [B, 2] 网格内位置
        """
        grid_idx = (position * self.map_size).long().clamp(0, self.map_size - 1)
        grid_pos = position * self.map_size - grid_idx.float()
        return grid_idx, grid_pos
    
    def get_place_cell_activation(self, position: torch.Tensor) -> torch.Tensor:
        """
        计算位置细胞激活
        Args:
            position: [B, 2]
        Returns:
            activation: [B, 100]
        """
        # 计算到各位置细胞中心的距离
        dist = torch.cdist(position, self.place_cell_centers)  # [B, 100]
        
        # 高斯调谐
        activation = torch.exp(-dist**2 / (2 * self.place_cell_widths**2))
        
        return activation
    
    def update_map(self, position: torch.Tensor, features: torch.Tensor):
        """
        更新空间地图
        Args:
            position: [B, 2]
            features: [B, feature_dim]
        """
        grid_idx, _ = self.position_to_grid(position)
        
        for i in range(position.size(0)):
            x, y = grid_idx[i]
            # 移动平均更新
            alpha = 0.1
            self.spatial_map[x, y] = (1 - alpha) * self.spatial_map[x, y] + alpha * features[i]
            self.visit_count[x, y] += 1
    
    def query_map(self, position: torch.Tensor) -> torch.Tensor:
        """
        查询位置的地图特征
        Args:
            position: [B, 2]
        Returns:
            features: [B, feature_dim]
        """
        grid_idx, grid_pos = self.position_to_grid(position)
        
        features = []
        for i in range(position.size(0)):
            x, y = grid_idx[i]
            features.append(self.spatial_map[x, y])
        
        return torch.stack(features)
    
    def get_novelty(self, position: torch.Tensor) -> torch.Tensor:
        """
        计算位置的新奇度 (未探索=高新奇)
        Args:
            position: [B, 2]
        Returns:
            novelty: [B, 1]
        """
        grid_idx, _ = self.position_to_grid(position)
        
        visit_counts = []
        for i in range(position.size(0)):
            x, y = grid_idx[i]
            visit_counts.append(self.visit_count[x, y])
        
        counts = torch.stack(visit_counts).float()
        novelty = torch.exp(-counts / 10.0)  # 衰减函数
        
        return novelty.unsqueeze(-1)


class ExplorationPolicy(nn.Module):
    """
    探索策略网络
    决定探索方向和速度
    """
    
    def __init__(self, input_dim: int = 512, hidden_dim: int = 256):
        super().__init__()
        
        self.policy_net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # 方向选择 (8个方向 + 停止)
        self.direction_head = nn.Linear(hidden_dim, 9)
        
        # 速度控制
        self.speed_head = nn.Linear(hidden_dim, 1)
        
        # 探索vs利用
        self.exploration_gate = nn.Linear(hidden_dim, 1)
        
    def forward(self, state_features: torch.Tensor, novelty: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            state_features: [B, input_dim]
            novelty: [B, 1]
        Returns:
            探索动作
        """
        # 整合新奇度
        x = torch.cat([state_features, novelty], dim=-1)
        x = x[:, :state_features.size(-1)]  # 确保维度一致
        
        features = self.policy_net(x)
        
        # 方向概率
        direction_logits = self.direction_head(features)
        direction_probs = torch.softmax(direction_logits, dim=-1)
        
        # 速度
        speed = torch.sigmoid(self.speed_head(features))
        
        # 探索倾向
        exploration_prob = torch.sigmoid(self.exploration_gate(features))
        
        return {
            'direction_probs': direction_probs,
            'speed': speed,
            'exploration_prob': exploration_prob
        }


class ExplorationBehavior(nn.Module):
    """
    完整探索行为模块
    整合空间记忆、新奇度评估和探索策略
    """
    
    def __init__(self, config: ExplorationConfig = None, brain_dim: int = 512):
        super().__init__()
        self.config = config or ExplorationConfig()
        
        # 空间记忆 (海马体功能)
        self.spatial_memory = SpatialMemory(
            map_size=self.config.spatial_map_resolution,
            feature_dim=brain_dim
        )
        
        # 探索策略
        self.policy = ExplorationPolicy(input_dim=brain_dim + 100)  # +位置细胞
        
        # 好奇心状态
        self.register_buffer('curiosity', torch.tensor(self.config.curiosity_base))
        
    def forward(self, 
                brain_state: torch.Tensor,
                position: torch.Tensor,
                update_memory: bool = True) -> Dict[str, torch.Tensor]:
        """
        Args:
            brain_state: [B, brain_dim] 大脑内部状态
            position: [B, 2] 当前位置 [0, 1]
            update_memory: 是否更新空间记忆
            
        Returns:
            探索动作和内部状态
        """
        # 位置细胞激活
        place_cells = self.spatial_memory.get_place_cell_activation(position)
        
        # 计算新奇度
        novelty = self.spatial_memory.get_novelty(position)
        
        # 查询地图
        map_features = self.spatial_memory.query_map(position)
        
        # 整合状态
        integrated_state = torch.cat([brain_state, place_cells], dim=-1)
        
        # 探索策略
        action = self.policy(integrated_state, novelty)
        
        # 更新空间记忆
        if update_memory:
            self.spatial_memory.update_map(position, brain_state)
        
        # 更新好奇心
        self.curiosity = self.curiosity * self.config.curiosity_decay
        
        return {
            'direction_probs': action['direction_probs'],
            'speed': action['speed'],
            'exploration_prob': action['exploration_prob'],
            'novelty': novelty,
            'place_cells': place_cells,
            'curiosity': self.curiosity.item()
        }
    
    def get_exploration_metrics(self) -> Dict[str, float]:
        """获取探索统计"""
        total_visits = self.spatial_memory.visit_count.sum().item()
        visited_cells = (self.spatial_memory.visit_count > 0).sum().item()
        total_cells = self.config.spatial_map_resolution ** 2
        
        return {
            'coverage': visited_cells / total_cells,
            'total_visits': total_visits,
            'avg_visits_per_cell': total_visits / max(visited_cells, 1),
            'curiosity': self.curiosity.item()
        }
    
    def reset(self):
        """重置探索状态"""
        self.spatial_memory.spatial_map.zero_()
        self.spatial_memory.visit_count.zero_()
        self.curiosity = torch.tensor(self.config.curiosity_base)


# 测试
if __name__ == "__main__":
    print("=== TNN小鼠探索行为模块测试 ===\n")
    
    # 创建探索模块
    exploration = ExplorationBehavior()
    
    # 模拟输入
    batch_size = 2
    brain_state = torch.randn(batch_size, 512)
    position = torch.rand(batch_size, 2)  # 随机位置
    
    print(f"初始状态:")
    print(f"  大脑状态: {brain_state.shape}")
    print(f"  位置: {position}")
    
    # 运行多步探索
    print(f"\n运行50步探索...")
    for step in range(50):
        # 随机移动 (模拟)
        position = torch.clamp(position + torch.randn(batch_size, 2) * 0.05, 0, 1)
        
        # 探索决策
        with torch.no_grad():
            action = exploration(brain_state, position)
        
        if step % 10 == 0:
            print(f"  Step {step}: 位置=[{position[0,0]:.2f}, {position[0,1]:.2f}], "
                  f"新奇度={action['novelty'][0,0]:.3f}, "
                  f"探索倾向={action['exploration_prob'][0,0]:.3f}")
    
    # 探索统计
    metrics = exploration.get_exploration_metrics()
    print(f"\n探索统计:")
    print(f"  覆盖率: {metrics['coverage']*100:.1f}%")
    print(f"  总访问次数: {metrics['total_visits']}")
    print(f"  好奇心: {metrics['curiosity']:.3f}")
    
    print("\n✓ 探索行为模块测试通过!")
