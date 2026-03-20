"""
V7-数字果蝇
基于V7统一认知架构（皮层+脑干+丘脑）的数字果蝇实现

架构升级:
- 脑干(TNN): 感知-行动反射（逃跑、避障）
- 皮层(Transformer): 序列决策（觅食路径规划、社交识别）
- 丘脑: 跨模态融合与注意力调控
- 课程学习: 从简单反射到复杂决策逐步解锁
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field
from enum import Enum
import sys
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')


class BehaviorState(Enum):
    """果蝇行为状态"""
    IDLE = "idle"
    WALKING = "walking"
    GROOMING = "grooming"
    FORAGING = "foraging"
    ESCAPING = "escaping"
    FEEDING = "feeding"
    RESTING = "resting"
    COURTING = "courting"


@dataclass
class FlyInternalState:
    """果蝇内部生理状态"""
    energy: float = 100.0
    hunger: float = 0.0
    stress: float = 0.0
    arousal: float = 0.5
    health: float = 100.0
    cleanliness: float = 100.0
    current_behavior: BehaviorState = BehaviorState.IDLE
    behavior_duration: int = 0
    
    def update(self, dt: float = 1.0):
        self.energy -= 0.1 * dt
        self.energy = np.clip(self.energy, 0, 100)
        self.hunger = 100 - self.energy
        self.stress *= 0.95
        self.cleanliness -= 0.05 * dt
        self.cleanliness = np.clip(self.cleanliness, 0, 100)
        self.behavior_duration += 1


# =============================================================================
# V7核心组件
# =============================================================================

class V7Cortical(nn.Module):
    """皮层 - 高级序列决策"""
    def __init__(self, input_dim=64, dim=128, num_layers=2):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, dim)
        self.pos_enc = nn.Parameter(torch.randn(1, 16, dim) * 0.02)
        
        self.layers = nn.ModuleList([
            nn.TransformerEncoderLayer(
                d_model=dim, nhead=4, dim_feedforward=dim*2,
                dropout=0.1, batch_first=True
            ) for _ in range(num_layers)
        ])
        
        self.norm = nn.LayerNorm(dim)
        self.decision_head = nn.Linear(dim, 8)  # 8种高级决策
    
    def forward(self, sequence):
        """
        sequence: [batch, seq_len, input_dim] - 历史感知序列
        """
        h = self.input_proj(sequence)
        h = h + self.pos_enc[:, :h.size(1), :]
        
        for layer in self.layers:
            h = layer(h)
        
        h = self.norm(h)
        # 取最后一个时间步的决策
        return self.decision_head(h[:, -1, :])


class V7Brainstem(nn.Module):
    """脑干 - 快速反射（TNN核心）"""
    def __init__(self, sensory_dim=64, action_dim=12, dim=128):
        super().__init__()
        self.sensory_enc = nn.Linear(sensory_dim, dim)
        
        # TNN-style处理
        self.tnn_layers = nn.ModuleList([
            nn.Sequential(
                nn.LayerNorm(dim),
                nn.Linear(dim, dim),
                nn.Tanh(),
                nn.Linear(dim, dim)
            ) for _ in range(3)
        ])
        
        self.action_head = nn.Linear(dim, action_dim)
    
    def forward(self, sensory):
        h = self.sensory_enc(sensory)
        for layer in self.tnn_layers:
            h = h + layer(h)  # 残差
        return self.action_head(h)


class V7Thalamus(nn.Module):
    """丘脑 - 跨模态融合与注意力"""
    def __init__(self, cortical_dim=8, brainstem_dim=128, dim=128):
        super().__init__()
        self.cortical_proj = nn.Linear(cortical_dim, dim)
        self.brainstem_proj = nn.Linear(brainstem_dim, dim)
        
        self.gate = nn.Sequential(nn.Linear(dim * 2, 1), nn.Sigmoid())
        self.fusion = nn.Sequential(
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
            nn.ReLU()
        )
    
    def forward(self, cortical, brainstem):
        """融合皮层和脑干的表示"""
        c = self.cortical_proj(cortical)
        b = self.brainstem_proj(brainstem)
        
        combined = torch.cat([c, b], dim=-1)
        gate = self.gate(combined)
        fused = gate * c + (1 - gate) * b
        return self.fusion(fused)


# =============================================================================
# V7数字果蝇大脑
# =============================================================================

class V7FlyBrain(nn.Module):
    """V7数字果蝇大脑 - 统一认知架构"""
    
    def __init__(self, dim=128):
        super().__init__()
        self.dim = dim
        
        # 感觉编码
        self.vision_enc = nn.Linear(32, dim)      # 复眼视觉
        self.chem_enc = nn.Linear(16, dim)        # 化学感受
        self.mechano_enc = nn.Linear(16, dim)     # 机械感受
        
        # 感觉融合
        self.sensory_fusion = nn.Sequential(
            nn.Linear(dim * 3, dim),
            nn.LayerNorm(dim),
            nn.ReLU()
        )
        
        # V7核心组件
        self.brainstem = V7Brainstem(sensory_dim=dim, action_dim=12, dim=dim)
        self.cortical = V7Cortical(input_dim=dim, dim=dim, num_layers=2)
        self.thalamus = V7Thalamus(cortical_dim=8, brainstem_dim=dim, dim=dim)
        
        # 输出头
        self.reflex_head = nn.Linear(dim, 6)      # 反射动作
        self.decision_head = nn.Linear(dim, 8)    # 高级决策
        self.behavior_head = nn.Linear(dim, len(BehaviorState))
        
        # 状态
        self.cortical_unlocked = False
        self.memory_buffer = []  # 用于皮层的历史序列
        self.max_memory = 16
    
    def unlock_cortical(self):
        """解锁皮层（课程学习晋升）"""
        self.cortical_unlocked = True
        print("   🔓 皮层解锁 - 高级决策能力激活!")
    
    def encode_sensory(self, vision, chemical, mechanical):
        """编码多模态感觉输入"""
        v = self.vision_enc(vision)
        c = self.chem_enc(chemical)
        m = self.mechano_enc(mechanical)
        return self.sensory_fusion(torch.cat([v, c, m], dim=-1))
    
    def forward(self, vision, chemical, mechanical):
        # 编码感觉
        sensory = self.encode_sensory(vision, chemical, mechanical)
        
        # 脑干路径（始终活跃）- 快速反射
        brainstem_action = self.brainstem(sensory)
        reflex = self.reflex_head(sensory)
        
        # 皮层路径（解锁后）- 高级决策
        cortical_decision = None
        behavior_logits = None
        
        if self.cortical_unlocked:
            # 更新记忆缓冲
            self.memory_buffer.append(sensory.detach())
            if len(self.memory_buffer) > self.max_memory:
                self.memory_buffer.pop(0)
            
            if len(self.memory_buffer) >= 4:  # 需要足够历史
                # 构造序列输入
                seq = torch.stack(self.memory_buffer[-4:], dim=1)  # [batch, 4, dim]
                
                # 皮层处理
                cortical_out = self.cortical(seq)
                
                # 丘脑融合
                fused = self.thalamus(cortical_out, sensory)
                
                # 高级决策
                cortical_decision = self.decision_head(fused)
                behavior_logits = self.behavior_head(fused)
                
                # 脑干受皮层调制
                modulation = torch.zeros_like(brainstem_action)
                modulation[:, :min(12, cortical_decision.size(-1))] = cortical_decision[:, :min(12, cortical_decision.size(-1))]
                brainstem_action = brainstem_action + 0.3 * modulation
        
        return {
            'reflex': reflex,
            'action': brainstem_action,
            'cortical_decision': cortical_decision,
            'behavior_logits': behavior_logits
        }


# =============================================================================
# 课程学习器
# =============================================================================

class V7FlyCurriculum:
    """V7果蝇课程学习器"""
    
    STAGES = [
        ('reflex', {'min_acc': 0.85}),       # 阶段1: 反射学习
        ('avoidance', {'min_acc': 0.80}),    # 阶段2: 避障学习
        ('foraging', {'min_acc': 0.75}),     # 阶段3: 觅食学习
        ('social', {'min_acc': 0.70}),       # 阶段4: 社交学习
    ]
    
    def __init__(self):
        self.stage_idx = 0
        self.history = []
    
    def get_task(self):
        """获取当前阶段的训练任务"""
        stage_name, cfg = self.STAGES[self.stage_idx]
        
        if stage_name == 'reflex':
            # 简单反射：看到食物→前进
            vision = torch.randn(16, 32)
            vision[:, :16] = 1.0  # 食物信号
            target_action = torch.zeros(16, 12)
            target_action[:, :2] = 1.0  # 前进
            
        elif stage_name == 'avoidance':
            # 避障：障碍物→后退/转向
            vision = torch.randn(16, 32)
            vision[:, 16:] = 1.0  # 障碍物信号
            target_action = torch.zeros(16, 12)
            target_action[:, 2:4] = 1.0  # 后退
            
        elif stage_name == 'foraging':
            # 觅食：根据气味梯度移动
            chemical = torch.randn(16, 16)
            chemical[:, :8] = torch.linspace(0, 1, 8)  # 梯度
            target_action = torch.zeros(16, 12)
            target_action[:, 4:6] = 1.0  # 转向气味源
            
        else:  # social
            # 社交：识别同类
            vision = torch.randn(16, 32)
            vision[:, 8:24] = 0.5  # 同类特征
            target_action = torch.zeros(16, 12)
            target_action[:, 6:8] = 1.0  # 接近行为
        
        return target_action, stage_name
    
    def check_promotion(self, avg_acc):
        """检查是否晋升"""
        self.history.append(avg_acc)
        if len(self.history) >= 30 and self.stage_idx < len(self.STAGES) - 1:
            recent = sum(self.history[-30:]) / 30
            threshold = self.STAGES[self.stage_idx][1]['min_acc']
            if recent >= threshold:
                self.stage_idx += 1
                self.history.clear()
                return True, self.STAGES[self.stage_idx][0]
        return False, self.STAGES[self.stage_idx][0]


# =============================================================================
# V7数字果蝇主体
# =============================================================================

class V7DigitalFly:
    """V7数字果蝇 - 完整实现"""
    
    def __init__(self, dim=128):
        self.brain = V7FlyBrain(dim=dim)
        self.internal = FlyInternalState()
        self.curriculum = V7FlyCurriculum()
        self.optimizer = torch.optim.Adam(self.brain.parameters(), lr=0.001)
        
        self.training_history = []
    
    def train_step(self):
        """单步训练"""
        # 数据
        batch = 16
        vision = torch.randn(batch, 32)
        chemical = torch.randn(batch, 16)
        mechanical = torch.randn(batch, 16)
        
        target_action, stage = self.curriculum.get_task()
        
        # 前向
        outputs = self.brain(vision, chemical, mechanical)
        
        # 损失
        loss_reflex = F.mse_loss(outputs['action'], target_action)
        
        # 解锁后损失
        loss_cortical = torch.tensor(0.0)
        if self.brain.cortical_unlocked and outputs['cortical_decision'] is not None:
            # 将cortical_decision投影到12维
            cortical_proj = torch.zeros_like(target_action)
            cortical_proj[:, :min(12, outputs['cortical_decision'].size(-1))] = \
                outputs['cortical_decision'][:, :min(12, outputs['cortical_decision'].size(-1))]
            loss_cortical = F.mse_loss(cortical_proj, target_action * 0.5)
        
        # 动态权重
        cortical_weight = 0.3 if self.brain.cortical_unlocked else 0.0
        total_loss = loss_reflex * (1 - cortical_weight) + loss_cortical * cortical_weight
        
        # 反向
        self.optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.brain.parameters(), 1.0)
        self.optimizer.step()
        
        # 统计
        acc = (outputs['action'] - target_action).abs().mean().item()
        self.training_history.append(acc)
        
        return acc, stage
    
    def train(self, n_epochs=500):
        """完整训练"""
        print("="*60)
        print("🪰 V7数字果蝇训练")
        print("="*60)
        print("课程: reflex → avoidance → foraging → social")
        print("解锁条件: 皮层在200轮后解锁（若脑干足够成熟）")
        print("="*60 + "\n")
        
        promotions = []
        epoch_in_stage = 0
        
        for epoch in range(n_epochs):
            acc, stage = self.train_step()
            epoch_in_stage += 1
            
            # 解锁皮层
            if epoch == 200 and not self.brain.cortical_unlocked:
                recent_acc = np.mean(self.training_history[-50:])
                if recent_acc < 0.3:  # 足够低的误差
                    self.brain.unlock_cortical()
            
            # 检查晋升
            if epoch % 50 == 49:
                recent = np.mean(self.training_history[-50:])
                promoted, new_stage = self.curriculum.check_promotion(1 - recent)
                if promoted:
                    promotions.append((epoch, new_stage))
                    print(f"\n🎓 晋升! Epoch {epoch} -> {new_stage}\n")
                    epoch_in_stage = 0
            
            # 报告
            if (epoch + 1) % 100 == 0:
                recent = np.mean(self.training_history[-100:])
                cortical_status = "ON" if self.brain.cortical_unlocked else "OFF"
                print(f"Epoch {epoch+1}: 误差={recent:.3f}, 阶段={stage}, 皮层={cortical_status}")
        
        # 总结
        print(f"\n{'='*60}")
        print("✅ V7数字果蝇训练完成!")
        print(f"最终阶段: {self.curriculum.STAGES[self.curriculum.stage_idx][0]}")
        print(f"皮层解锁: {'是' if self.brain.cortical_unlocked else '否'}")
        print(f"晋升次数: {len(promotions)}")
        if promotions:
            print("晋升记录:", promotions)
        print(f"{'='*60}\n")


# =============================================================================
# 运行
# =============================================================================

def run_v7_fly():
    """运行V7数字果蝇实验"""
    fly = V7DigitalFly(dim=128)
    fly.train(n_epochs=500)


if __name__ == "__main__":
    run_v7_fly()
