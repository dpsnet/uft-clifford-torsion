"""
V7数字果蝇活动记录器（简化版）
生成关键帧静态图像
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from typing import List
import sys
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code/tnn_digital_fly')

from v7_fly_brain import V7FlyBrain, FlyInternalState, BehaviorState


class SimpleV7FlyRecorder:
    """简化版V7数字果蝇记录器"""
    
    def __init__(self, dim=128):
        self.brain = V7FlyBrain(dim=dim)
        self.internal = FlyInternalState()
        
        self.position = np.array([50.0, 50.0])
        self.velocity = np.array([0.0, 0.0])
        self.orientation = 0.0
        
        self.food_positions = [
            np.array([20.0, 20.0]),
            np.array([80.0, 80.0]),
            np.array([20.0, 80.0]),
        ]
        self.obstacles = [np.array([50.0, 30.0])]
        
        self.position_history = [self.position.copy()]
        self.behavior_history = [self.internal.current_behavior]
        self.energy_history = [self.internal.energy]
        self.brainstem_activity = []
        self.cortical_activity = []
    
    def get_sensory_input(self):
        """获取感觉输入"""
        vision = np.zeros(32)
        
        for i, food_pos in enumerate(self.food_positions):
            dist = np.linalg.norm(food_pos - self.position)
            if dist < 30:
                angle = np.arctan2(food_pos[1] - self.position[1], 
                                  food_pos[0] - self.position[0])
                angle_diff = (angle - self.orientation) % (2 * np.pi)
                sector = int(angle_diff / (2 * np.pi) * 16) % 16
                vision[sector] = max(vision[sector], 1.0 - dist/30)
        
        for obs_pos in self.obstacles:
            dist = np.linalg.norm(obs_pos - self.position)
            if dist < 25:
                angle = np.arctan2(obs_pos[1] - self.position[1],
                                  obs_pos[0] - self.position[0])
                angle_diff = (angle - self.orientation) % (2 * np.pi)
                sector = int(angle_diff / (2 * np.pi) * 16) % 16
                vision[16 + sector] = max(vision[16 + sector], 1.0 - dist/25)
        
        chemical = np.zeros(16)
        min_dist = float('inf')
        nearest_food = None
        for food_pos in self.food_positions:
            dist = np.linalg.norm(food_pos - self.position)
            if dist < min_dist:
                min_dist = dist
                nearest_food = food_pos
        
        if nearest_food is not None:
            smell_strength = max(0, 1.0 - min_dist / 50)
            angle_to_food = np.arctan2(nearest_food[1] - self.position[1],
                                       nearest_food[0] - self.position[0])
            angle_diff = (angle_to_food - self.orientation) % (2 * np.pi)
            chem_sector = int(angle_diff / (2 * np.pi) * 16) % 16
            chemical[chem_sector] = smell_strength
        
        mechanical = np.zeros(16)
        mechanical[0] = self.internal.energy / 100.0
        mechanical[1] = self.internal.hunger / 100.0
        mechanical[2] = self.internal.stress / 100.0
        mechanical[3] = float(self.velocity[0] != 0 or self.velocity[1] != 0)
        
        return (torch.tensor(vision, dtype=torch.float32).unsqueeze(0),
                torch.tensor(chemical, dtype=torch.float32).unsqueeze(0),
                torch.tensor(mechanical, dtype=torch.float32).unsqueeze(0))
    
    def step(self):
        """单步模拟"""
        vision, chemical, mechanical = self.get_sensory_input()
        
        with torch.no_grad():
            outputs = self.brain(vision, chemical, mechanical)
        
        action = outputs['action'].squeeze().numpy()
        
        speed = action[0] * 2.0
        turn = action[1] * 0.5
        
        self.orientation += turn
        self.orientation %= (2 * np.pi)
        
        self.velocity[0] = speed * np.cos(self.orientation)
        self.velocity[1] = speed * np.sin(self.orientation)
        
        self.position += self.velocity
        self.position = np.clip(self.position, 5, 95)
        
        for i, food_pos in enumerate(self.food_positions):
            if np.linalg.norm(food_pos - self.position) < 5:
                self.internal.energy = min(100, self.internal.energy + 20)
                self.food_positions[i] = np.random.rand(2) * 80 + 10
                break
        
        for obs_pos in self.obstacles:
            if np.linalg.norm(obs_pos - self.position) < 8:
                self.internal.stress = min(100, self.internal.stress + 10)
                self.velocity = -self.velocity
                self.position += self.velocity * 2
        
        self.internal.update()
        
        if self.internal.stress > 50:
            self.internal.current_behavior = BehaviorState.ESCAPING
        elif self.internal.hunger > 60:
            self.internal.current_behavior = BehaviorState.FORAGING
        elif speed < 0.1:
            self.internal.current_behavior = BehaviorState.RESTING
        else:
            self.internal.current_behavior = BehaviorState.WALKING
        
        self.position_history.append(self.position.copy())
        self.behavior_history.append(self.internal.current_behavior)
        self.energy_history.append(self.internal.energy)
        
        self.brainstem_activity.append(np.abs(action).mean())
        if outputs['cortical_decision'] is not None:
            self.cortical_activity.append(
                torch.abs(outputs['cortical_decision']).mean().item()
            )
        else:
            self.cortical_activity.append(0)
    
    def simulate(self, n_steps=200):
        """运行模拟"""
        print(f"🎬 录制V7数字果蝇活动 ({n_steps}帧)...")
        for i in range(n_steps):
            self.step()
            if (i + 1) % 50 == 0:
                print(f"  进度: {i+1}/{n_steps}")
        print("✅ 录制完成!")
    
    def plot_frame(self, frame_idx, ax_main, ax_brain, ax_energy):
        """绘制单帧"""
        behavior_colors = {
            BehaviorState.IDLE: 'gray',
            BehaviorState.WALKING: 'blue',
            BehaviorState.FORAGING: 'green',
            BehaviorState.ESCAPING: 'red',
            BehaviorState.RESTING: 'purple',
        }
        
        # ===== 主视图 =====
        ax_main.set_xlim(0, 100)
        ax_main.set_ylim(0, 100)
        ax_main.set_aspect('equal')
        ax_main.set_title(f'V7 Digital Fly - Frame {frame_idx}', fontsize=12, fontweight='bold')
        
        # 食物
        for food_pos in self.food_positions:
            food = Circle(food_pos, 3, color='green', alpha=0.6)
            ax_main.add_patch(food)
        
        # 障碍物
        for obs_pos in self.obstacles:
            obs = Circle(obs_pos, 5, color='red', alpha=0.4)
            ax_main.add_patch(obs)
        
        # 轨迹
        start = max(0, frame_idx - 30)
        traj = np.array(self.position_history[start:frame_idx+1])
        if len(traj) > 1:
            ax_main.plot(traj[:, 0], traj[:, 1], 'b-', alpha=0.4, linewidth=1)
        
        # 果蝇
        pos = self.position_history[frame_idx]
        behavior = self.behavior_history[frame_idx]
        color = behavior_colors.get(behavior, 'black')
        fly_body = Circle(pos, 3, color=color, alpha=0.9)
        ax_main.add_patch(fly_body)
        
        # 状态信息
        energy = self.energy_history[frame_idx]
        info_text = f'Behavior: {behavior.value}\nEnergy: {energy:.1f}%'
        ax_main.text(5, 95, info_text, fontsize=9, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # ===== 脑区活动 =====
        ax_brain.set_xlim(0, 1)
        ax_brain.set_ylim(0, 3)
        ax_brain.set_title('Brain Activity', fontsize=10, fontweight='bold')
        ax_brain.axis('off')
        
        if frame_idx < len(self.brainstem_activity):
            b_act = self.brainstem_activity[frame_idx]
            c_act = self.cortical_activity[frame_idx] if frame_idx < len(self.cortical_activity) else 0
            
            ax_brain.barh(2.5, b_act, height=0.4, color='orange', alpha=0.7)
            ax_brain.text(0.5, 2.5, f'Brainstem: {b_act:.2f}', 
                         ha='center', va='center', fontsize=8)
            
            ax_brain.barh(1.5, c_act, height=0.4, color='purple', alpha=0.7)
            ax_brain.text(0.5, 1.5, f'Cortical: {c_act:.2f}',
                         ha='center', va='center', fontsize=8)
            
            th_act = (b_act + c_act) / 2
            ax_brain.barh(0.5, th_act, height=0.4, color='cyan', alpha=0.7)
            ax_brain.text(0.5, 0.5, f'Thalamus: {th_act:.2f}',
                         ha='center', va='center', fontsize=8)
        
        # ===== 能量曲线 =====
        x = range(min(frame_idx + 1, len(self.energy_history)))
        y = self.energy_history[:frame_idx+1]
        ax_energy.plot(x, y, 'g-', linewidth=2)
        ax_energy.fill_between(x, y, alpha=0.3, color='green')
        ax_energy.set_xlim(0, len(self.energy_history))
        ax_energy.set_ylim(0, 100)
        ax_energy.set_ylabel('Energy (%)')
        ax_energy.set_title('Energy Level', fontsize=10, fontweight='bold')
        ax_energy.axhline(y=60, color='r', linestyle='--', alpha=0.5)
    
    def create_snapshots(self, output_dir='/root/.openclaw/workspace/research_notes/code/tnn_digital_fly/'):
        """创建关键帧快照"""
        print("📸 生成关键帧...")
        
        key_frames = [0, 50, 100, 150, 199]
        
        for idx, frame_idx in enumerate(key_frames):
            if frame_idx >= len(self.position_history):
                continue
            
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            ax_main = axes[0, 0]
            ax_brain = axes[0, 1]
            ax_traj = axes[1, 0]
            ax_energy = axes[1, 1]
            
            # 绘制主视图
            self.plot_frame(frame_idx, ax_main, ax_brain, ax_energy)
            
            # 完整轨迹
            behavior_colors = {
                BehaviorState.IDLE: 'gray',
                BehaviorState.WALKING: 'blue',
                BehaviorState.FORAGING: 'green',
                BehaviorState.ESCAPING: 'red',
                BehaviorState.RESTING: 'purple',
            }
            
            traj_full = np.array(self.position_history[:frame_idx+1])
            if len(traj_full) > 1:
                for i in range(len(traj_full) - 1):
                    behavior = self.behavior_history[i]
                    color = behavior_colors.get(behavior, 'black')
                    ax_traj.plot([traj_full[i, 0], traj_full[i+1, 0]],
                                [traj_full[i, 1], traj_full[i+1, 1]],
                                color=color, linewidth=1.5, alpha=0.7)
            
            ax_traj.set_xlim(0, 100)
            ax_traj.set_ylim(0, 100)
            ax_traj.set_aspect('equal')
            ax_traj.set_title('Full Trajectory', fontsize=10, fontweight='bold')
            
            # 图例
            for behavior, color in behavior_colors.items():
                ax_traj.scatter([], [], c=color, label=behavior.value, s=20)
            ax_traj.legend(loc='upper right', fontsize=8)
            
            plt.tight_layout()
            
            output_path = f'{output_dir}v7_fly_snapshot_{idx:02d}_frame{frame_idx:03d}.png'
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"  ✅ 已保存: {output_path}")
            plt.close()
        
        # 保存完整轨迹图
        fig, ax = plt.subplots(figsize=(10, 10))
        behavior_colors = {
            BehaviorState.IDLE: 'gray',
            BehaviorState.WALKING: 'blue',
            BehaviorState.FORAGING: 'green',
            BehaviorState.ESCAPING: 'red',
            BehaviorState.RESTING: 'purple',
        }
        
        traj_full = np.array(self.position_history)
        for i in range(len(traj_full) - 1):
            behavior = self.behavior_history[i]
            color = behavior_colors.get(behavior, 'black')
            ax.plot([traj_full[i, 0], traj_full[i+1, 0]],
                   [traj_full[i, 1], traj_full[i+1, 1]],
                   color=color, linewidth=1.5, alpha=0.7)
        
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_aspect('equal')
        ax.set_title('V7 Digital Fly - Complete Trajectory (200 frames)', fontsize=14, fontweight='bold')
        
        for behavior, color in behavior_colors.items():
            ax.scatter([], [], c=color, label=behavior.value, s=30)
        ax.legend(loc='upper right', fontsize=10)
        
        output_path = f'{output_dir}v7_fly_complete_trajectory.png'
        plt.savefig(output_path, dpi=200, bbox_inches='tight')
        print(f"  ✅ 已保存: {output_path}")
        plt.close()
        
        print("\n📊 所有快照已生成!")


def main():
    """主函数"""
    print("="*60)
    print("🪰 V7数字果蝇活动记录器（简化版）")
    print("="*60)
    print("\n生成内容:")
    print("  • 5个关键帧快照（0, 50, 100, 150, 199帧）")
    print("  • 完整轨迹图")
    print("  • 脑区活动可视化")
    print("  • 能量变化曲线")
    print("="*60 + "\n")
    
    recorder = SimpleV7FlyRecorder(dim=128)
    recorder.simulate(n_steps=200)
    recorder.create_snapshots()
    
    print("\n" + "="*60)
    print("🎬 记录完成!")
    print("="*60)
    print("\n文件位置:")
    print("  /research_notes/code/tnn_digital_fly/v7_fly_snapshot_*.png")
    print("  /research_notes/code/tnn_digital_fly/v7_fly_complete_trajectory.png")
    print("\n每张图包含:")
    print("  [左上] 实时环境视图（果蝇位置、食物、障碍物）")
    print("  [右上] 脑区激活水平（脑干/皮层/丘脑）")
    print("  [左下] 完整运动轨迹（按行为着色）")
    print("  [右下] 能量水平变化曲线")
    print("="*60)


if __name__ == "__main__":
    main()
