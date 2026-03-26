"""
V7数字果蝇活动视频记录器
记录果蝇的行为轨迹、脑区激活、决策过程
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Arrow
from matplotlib.collections import LineCollection
import matplotlib.animation as animation
from typing import List, Dict, Tuple
import sys
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code/tnn_digital_fly')

# 导入V7果蝇大脑
from v7_fly_brain import V7FlyBrain, FlyInternalState, BehaviorState


class V7FlyRecorder:
    """V7数字果蝇活动记录器"""
    
    def __init__(self, dim=128):
        self.brain = V7FlyBrain(dim=dim)
        self.internal = FlyInternalState()
        
        # 位置和运动状态
        self.position = np.array([50.0, 50.0])
        self.velocity = np.array([0.0, 0.0])
        self.orientation = 0.0  # 朝向角度
        
        # 环境
        self.food_positions = [
            np.array([20.0, 20.0]),
            np.array([80.0, 80.0]),
            np.array([20.0, 80.0]),
        ]
        self.obstacles = [
            np.array([50.0, 30.0]),  # 障碍物位置
        ]
        
        # 记录数据
        self.position_history = [self.position.copy()]
        self.behavior_history = [self.internal.current_behavior]
        self.energy_history = [self.internal.energy]
        self.brainstem_activity = []
        self.cortical_activity = []
        self.thalamus_gate = []
        
    def get_sensory_input(self):
        """获取感觉输入"""
        # 视觉：检测食物和障碍物
        vision = np.zeros(32)
        
        # 检测食物（简化：基于距离）
        for i, food_pos in enumerate(self.food_positions):
            dist = np.linalg.norm(food_pos - self.position)
            if dist < 30:  # 视觉范围
                angle = np.arctan2(food_pos[1] - self.position[1], 
                                  food_pos[0] - self.position[0])
                angle_diff = (angle - self.orientation) % (2 * np.pi)
                sector = int(angle_diff / (2 * np.pi) * 16) % 16
                vision[sector] = max(vision[sector], 1.0 - dist/30)
        
        # 检测障碍物
        for obs_pos in self.obstacles:
            dist = np.linalg.norm(obs_pos - self.position)
            if dist < 25:
                angle = np.arctan2(obs_pos[1] - self.position[1],
                                  obs_pos[0] - self.position[0])
                angle_diff = (angle - self.orientation) % (2 * np.pi)
                sector = int(angle_diff / (2 * np.pi) * 16) % 16
                vision[16 + sector] = max(vision[16 + sector], 1.0 - dist/25)
        
        # 化学感受：食物气味梯度
        chemical = np.zeros(16)
        min_dist = float('inf')
        nearest_food = None
        for food_pos in self.food_positions:
            dist = np.linalg.norm(food_pos - self.position)
            if dist < min_dist:
                min_dist = dist
                nearest_food = food_pos
        
        if nearest_food is not None:
            # 气味强度随距离衰减
            smell_strength = max(0, 1.0 - min_dist / 50)
            angle_to_food = np.arctan2(nearest_food[1] - self.position[1],
                                       nearest_food[0] - self.position[0])
            angle_diff = (angle_to_food - self.orientation) % (2 * np.pi)
            chem_sector = int(angle_diff / (2 * np.pi) * 16) % 16
            chemical[chem_sector] = smell_strength
        
        # 机械感受：身体状态
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
        # 获取感觉输入
        vision, chemical, mechanical = self.get_sensory_input()
        
        # 大脑决策
        with torch.no_grad():
            outputs = self.brain(vision, chemical, mechanical)
        
        # 解析动作
        action = outputs['action'].squeeze().numpy()
        
        # 动作映射
        speed = action[0] * 2.0  # 前进速度
        turn = action[1] * 0.5   # 转向
        
        # 更新朝向
        self.orientation += turn
        self.orientation %= (2 * np.pi)
        
        # 更新速度
        self.velocity[0] = speed * np.cos(self.orientation)
        self.velocity[1] = speed * np.sin(self.orientation)
        
        # 更新位置
        self.position += self.velocity
        self.position = np.clip(self.position, 5, 95)
        
        # 检查食物摄入
        for i, food_pos in enumerate(self.food_positions):
            if np.linalg.norm(food_pos - self.position) < 5:
                self.internal.energy = min(100, self.internal.energy + 20)
                # 食物被吃掉后重新生成
                self.food_positions[i] = np.random.rand(2) * 80 + 10
                break
        
        # 检查障碍物碰撞
        for obs_pos in self.obstacles:
            if np.linalg.norm(obs_pos - self.position) < 8:
                self.internal.stress = min(100, self.internal.stress + 10)
                # 反弹
                self.velocity = -self.velocity
                self.position += self.velocity * 2
        
        # 更新内部状态
        self.internal.update()
        
        # 根据能量和应激决定行为
        if self.internal.stress > 50:
            self.internal.current_behavior = BehaviorState.ESCAPING
        elif self.internal.hunger > 60:
            self.internal.current_behavior = BehaviorState.FORAGING
        elif speed < 0.1:
            self.internal.current_behavior = BehaviorState.RESTING
        else:
            self.internal.current_behavior = BehaviorState.WALKING
        
        # 记录数据
        self.position_history.append(self.position.copy())
        self.behavior_history.append(self.internal.current_behavior)
        self.energy_history.append(self.internal.energy)
        
        # 记录脑区活动
        self.brainstem_activity.append(np.abs(action).mean())
        if outputs['cortical_decision'] is not None:
            self.cortical_activity.append(
                torch.abs(outputs['cortical_decision']).mean().item()
            )
        else:
            self.cortical_activity.append(0)
    
    def simulate(self, n_steps=300):
        """运行完整模拟"""
        print(f"🎬 开始录制V7数字果蝇活动 ({n_steps}帧)...")
        for i in range(n_steps):
            self.step()
            if (i + 1) % 50 == 0:
                print(f"  进度: {i+1}/{n_steps}")
        print("✅ 录制完成!")
    
    def create_video(self, output_path='v7_fly_activity.mp4'):
        """创建活动视频"""
        print("🎥 生成视频中...")
        
        fig = plt.figure(figsize=(16, 10))
        
        # 布局
        gs = fig.add_gridspec(3, 3, height_ratios=[2, 1, 1])
        ax_env = fig.add_subplot(gs[0, :2])      # 环境视图
        ax_brain = fig.add_subplot(gs[0, 2])     # 脑区激活
        ax_traj = fig.add_subplot(gs[1, :])      # 轨迹
        ax_energy = fig.add_subplot(gs[2, :2])   # 能量变化
        ax_behavior = fig.add_subplot(gs[2, 2])  # 行为统计
        
        # 颜色映射
        behavior_colors = {
            BehaviorState.IDLE: 'gray',
            BehaviorState.WALKING: 'blue',
            BehaviorState.FORAGING: 'green',
            BehaviorState.ESCAPING: 'red',
            BehaviorState.RESTING: 'purple',
        }
        
        def animate(frame):
            # 清空
            ax_env.clear()
            ax_brain.clear()
            ax_traj.clear()
            ax_energy.clear()
            ax_behavior.clear()
            
            # ===== 环境视图 =====
            ax_env.set_xlim(0, 100)
            ax_env.set_ylim(0, 100)
            ax_env.set_aspect('equal')
            ax_env.set_title(f'V7 Digital Fly - Frame {frame}', fontsize=14, fontweight='bold')
            
            # 绘制食物
            for food_pos in self.food_positions:
                food = Circle(food_pos, 3, color='green', alpha=0.6)
                ax_env.add_patch(food)
            
            # 绘制障碍物
            for obs_pos in self.obstacles:
                obs = Circle(obs_pos, 5, color='red', alpha=0.4)
                ax_env.add_patch(obs)
            
            # 绘制轨迹（最近50步）
            start = max(0, frame - 50)
            traj = np.array(self.position_history[start:frame+1])
            if len(traj) > 1:
                ax_env.plot(traj[:, 0], traj[:, 1], 'b-', alpha=0.5, linewidth=1)
            
            # 绘制果蝇
            pos = self.position_history[frame]
            behavior = self.behavior_history[frame]
            color = behavior_colors.get(behavior, 'black')
            
            fly_body = Circle(pos, 3, color=color, alpha=0.8)
            ax_env.add_patch(fly_body)
            
            # 朝向箭头
            if frame < len(self.position_history) - 1:
                next_pos = self.position_history[frame + 1]
                direction = next_pos - pos
                if np.linalg.norm(direction) > 0.1:
                    direction = direction / np.linalg.norm(direction) * 5
                    ax_env.arrow(pos[0], pos[1], direction[0], direction[1],
                                head_width=2, head_length=2, fc=color, ec=color)
            
            # 状态信息
            energy = self.energy_history[frame]
            info_text = f'Behavior: {behavior.value}\nEnergy: {energy:.1f}%'
            ax_env.text(5, 95, info_text, fontsize=10, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # ===== 脑区激活 =====
            ax_brain.set_xlim(0, 1)
            ax_brain.set_ylim(0, 3)
            ax_brain.set_title('Brain Activity', fontsize=12, fontweight='bold')
            ax_brain.axis('off')
            
            if frame < len(self.brainstem_activity):
                b_act = self.brainstem_activity[frame]
                c_act = self.cortical_activity[frame] if frame < len(self.cortical_activity) else 0
                
                # 脑干
                ax_brain.barh(2.5, b_act, height=0.4, color='orange', alpha=0.7)
                ax_brain.text(0.5, 2.5, f'Brainstem: {b_act:.2f}', 
                             ha='center', va='center', fontsize=9)
                
                # 皮层
                ax_brain.barh(1.5, c_act, height=0.4, color='purple', alpha=0.7)
                ax_brain.text(0.5, 1.5, f'Cortical: {c_act:.2f}',
                             ha='center', va='center', fontsize=9)
                
                # 丘脑（估算）
                th_act = (b_act + c_act) / 2
                ax_brain.barh(0.5, th_act, height=0.4, color='cyan', alpha=0.7)
                ax_brain.text(0.5, 0.5, f'Thalamus: {th_act:.2f}',
                             ha='center', va='center', fontsize=9)
            
            # ===== 完整轨迹 =====
            traj_full = np.array(self.position_history[:frame+1])
            if len(traj_full) > 1:
                # 根据行为着色
                for i in range(len(traj_full) - 1):
                    behavior = self.behavior_history[i]
                    color = behavior_colors.get(behavior, 'black')
                    ax_traj.plot([traj_full[i, 0], traj_full[i+1, 0]],
                                [traj_full[i, 1], traj_full[i+1, 1]],
                                color=color, linewidth=1.5, alpha=0.7)
            
            ax_traj.set_xlim(0, 100)
            ax_traj.set_ylim(0, 100)
            ax_traj.set_aspect('equal')
            ax_traj.set_title('Full Trajectory', fontsize=12, fontweight='bold')
            
            # 图例
            for behavior, color in behavior_colors.items():
                ax_traj.scatter([], [], c=color, label=behavior.value)
            ax_traj.legend(loc='upper right', fontsize=8)
            
            # ===== 能量变化 =====
            x = range(min(frame + 1, len(self.energy_history)))
            y = self.energy_history[:frame+1]
            ax_energy.plot(x, y, 'g-', linewidth=2)
            ax_energy.fill_between(x, y, alpha=0.3, color='green')
            ax_energy.set_xlim(0, len(self.energy_history))
            ax_energy.set_ylim(0, 100)
            ax_energy.set_xlabel('Time Step')
            ax_energy.set_ylabel('Energy (%)')
            ax_energy.set_title('Energy Level', fontsize=12, fontweight='bold')
            ax_energy.axhline(y=60, color='r', linestyle='--', alpha=0.5, label='Hunger threshold')
            ax_energy.legend()
            
            # ===== 行为统计 =====
            behavior_counts = {}
            for b in self.behavior_history[:frame+1]:
                behavior_counts[b] = behavior_counts.get(b, 0) + 1
            
            if behavior_counts:
                behaviors = list(behavior_counts.keys())
                counts = list(behavior_counts.values())
                colors = [behavior_colors.get(b, 'gray') for b in behaviors]
                labels = [b.value for b in behaviors]
                
                ax_behavior.pie(counts, labels=labels, colors=colors, autopct='%1.1f%%',
                               startangle=90)
                ax_behavior.set_title('Behavior Distribution', fontsize=12, fontweight='bold')
            
            plt.tight_layout()
            return []
        
        # 创建动画
        anim = animation.FuncAnimation(
            fig, animate, frames=len(self.position_history),
            interval=50, blit=False
        )
        
        # 保存
        try:
            anim.save(output_path, writer='ffmpeg', fps=20, dpi=100)
            print(f"✅ 视频已保存: {output_path}")
        except Exception as e:
            print(f"⚠️ FFmpeg保存失败: {e}")
            print("💾 尝试保存为GIF...")
            try:
                gif_path = output_path.replace('.mp4', '.gif')
                anim.save(gif_path, writer='pillow', fps=20)
                print(f"✅ GIF已保存: {gif_path}")
            except Exception as e2:
                print(f"❌ GIF保存也失败: {e2}")
                print("📊 改为保存静态帧...")
                # 保存关键帧
                for frame_idx in [0, len(self.position_history)//4, 
                                 len(self.position_history)//2,
                                 3*len(self.position_history)//4, -1]:
                    animate(frame_idx)
                    plt.savefig(f'v7_fly_frame_{frame_idx}.png', dpi=150, bbox_inches='tight')
                print("✅ 静态帧已保存")
        
        plt.close()


def main():
    """主函数"""
    print("="*60)
    print("🪰 V7数字果蝇活动视频记录器")
    print("="*60)
    print("\n功能:")
    print("  • 记录果蝇在虚拟环境中的运动轨迹")
    print("  • 可视化脑区激活（脑干/皮层/丘脑）")
    print("  • 展示行为状态变化（觅食/逃跑/休息等）")
    print("  • 生成能量变化曲线")
    print("="*60 + "\n")
    
    # 创建记录器
    recorder = V7FlyRecorder(dim=128)
    
    # 运行模拟
    recorder.simulate(n_steps=300)
    
    # 生成视频
    output_path = '/root/.openclaw/workspace/research_notes/code/tnn_digital_fly/v7_fly_activity.mp4'
    recorder.create_video(output_path)
    
    print("\n" + "="*60)
    print("🎬 视频生成完成!")
    print("="*60)
    print(f"\n文件位置: {output_path}")
    print("\n视频内容包括:")
    print("  1. 果蝇在环境中的实时运动")
    print("  2. 脑区激活水平（脑干/皮层/丘脑）")
    print("  3. 完整运动轨迹（按行为着色）")
    print("  4. 能量水平变化曲线")
    print("  5. 行为分布统计")
    print("="*60)


if __name__ == "__main__":
    main()
