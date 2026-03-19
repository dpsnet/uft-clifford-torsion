"""
运行连续生长系统 - 实际训练版本
从2层开始，逐步生长，记录完整过程
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import os
import sys
import time
from datetime import datetime

# 添加路径导入连续生长模块
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')
from continuous_growing_tnn import ContinuousGrowingTNN, ResourceMonitor


class GrowingExperiment:
    """连续生长实验管理器"""
    
    def __init__(self, log_dir='./growth_experiment_logs'):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # 实验记录
        self.experiment_log = []
        self.start_time = datetime.now()
        
        # 初始化模型（2层胚胎期）
        print("="*70)
        print("🌱 启动连续生长实验")
        print("="*70)
        print(f"\n开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.model = ContinuousGrowingTNN(
            initial_layers=2,
            hidden_dim=128,  # 较小维度，便于快速实验
            vocab_size=100,   # 小词汇表
            max_seq_len=64,
            checkpoint_dir=os.path.join(log_dir, 'checkpoints')
        )
        
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        
        # 初始状态
        self._log_status("EXPERIMENT_START")
        
    def _log_status(self, event_type, data=None):
        """记录状态"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'event': event_type,
            'elapsed_minutes': (datetime.now() - self.start_time).total_seconds() / 60,
            'model_layers': self.model.current_layers,
            'model_params_million': self.model.total_params / 1e6,
            'current_stage': self.model.current_stage,
        }
        
        if data:
            status.update(data)
        
        self.experiment_log.append(status)
        
        # 同时保存到文件
        log_file = os.path.join(self.log_dir, 'experiment_log.jsonl')
        with open(log_file, 'a') as f:
            f.write(json.dumps(status) + '\n')
        
        return status
    
    def generate_training_data(self, batch_size, seq_len):
        """生成简单的序列预测数据"""
        # 简单的模式：重复序列
        data = []
        targets = []
        
        for _ in range(batch_size):
            # 创建简单模式 [0,1,2,3,...] 或重复
            pattern_type = torch.randint(0, 3, (1,)).item()
            
            if pattern_type == 0:
                # 递增序列
                seq = torch.arange(seq_len) % self.model.vocab_size
            elif pattern_type == 1:
                # 重复模式
                seq = torch.tensor([i % 5 for i in range(seq_len)])
            else:
                # 随机但平滑
                start = torch.randint(0, 20, (1,)).item()
                seq = torch.tensor([(start + i) % self.model.vocab_size for i in range(seq_len)])
            
            data.append(seq)
            # 目标是下一个token
            target = torch.cat([seq[1:], torch.tensor([seq[0].item()])])
            targets.append(target)
        
        return torch.stack(data), torch.stack(targets)
    
    def train_step(self, num_batches=10, batch_size=4, seq_len=32):
        """训练一步"""
        self.model.train()
        total_loss = 0
        
        for _ in range(num_batches):
            input_ids, targets = self.generate_training_data(batch_size, seq_len)
            
            # 前向
            logits = self.model(input_ids)
            
            # 计算损失
            loss = F.cross_entropy(
                logits.view(-1, self.model.vocab_size),
                targets.view(-1)
            )
            
            # 反向
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
        
        avg_loss = total_loss / num_batches
        perplexity = torch.exp(torch.tensor(avg_loss)).item()
        
        return avg_loss, perplexity
    
    def evaluate(self, num_batches=5):
        """评估模型"""
        self.model.eval()
        total_loss = 0
        correct_predictions = 0
        total_predictions = 0
        
        with torch.no_grad():
            for _ in range(num_batches):
                input_ids, targets = self.generate_training_data(4, 32)
                logits = self.model(input_ids)
                
                loss = F.cross_entropy(
                    logits.view(-1, self.model.vocab_size),
                    targets.view(-1)
                )
                total_loss += loss.item()
                
                # 计算准确率
                predictions = logits.argmax(dim=-1)
                correct_predictions += (predictions == targets).sum().item()
                total_predictions += targets.numel()
        
        avg_loss = total_loss / num_batches
        perplexity = torch.exp(torch.tensor(avg_loss)).item()
        accuracy = correct_predictions / total_predictions
        
        return avg_loss, perplexity, accuracy
    
    def run_growth_cycle(self, max_cycles=100):
        """运行生长循环"""
        print("\n" + "-"*70)
        print("开始生长循环")
        print("-"*70)
        
        cycle = 0
        total_training_steps = 0
        
        while cycle < max_cycles:
            cycle += 1
            print(f"\n📊 生长周期 #{cycle}")
            print(f"   当前: {self.model.current_layers}层 | {self.model.total_params/1e6:.2f}M参数 | 阶段{self.model.current_stage}")
            
            # 训练阶段
            print(f"   训练...", end=' ')
            train_losses = []
            for step in range(20):  # 每个周期训练20步
                loss, ppl = self.train_step(num_batches=5)
                train_losses.append(loss)
                total_training_steps += 1
            
            avg_train_loss = sum(train_losses) / len(train_losses)
            print(f"完成 | 平均损失: {avg_train_loss:.4f}")
            
            # 评估
            print(f"   评估...", end=' ')
            eval_loss, eval_ppl, accuracy = self.evaluate()
            print(f"损失: {eval_loss:.4f} | 困惑度: {eval_ppl:.2f} | 准确率: {accuracy:.2%}")
            
            # 记录
            self._log_status("CYCLE_COMPLETE", {
                'cycle': cycle,
                'train_loss': avg_train_loss,
                'eval_loss': eval_loss,
                'eval_perplexity': eval_ppl,
                'eval_accuracy': accuracy,
                'training_steps': total_training_steps,
            })
            
            # 检查生长条件
            print(f"   检查生长条件...")
            growth_decision = self.model.check_and_grow(performance_metric=accuracy)
            
            if growth_decision.get('migration_needed'):
                print(f"\n⚠️  资源临界！需要迁移")
                print(f"   当前层数: {self.model.current_layers}")
                print(f"   保存检查点并暂停...")
                checkpoint_path = self.model.save_checkpoint('pre_migration_pause')
                print(f"   检查点: {checkpoint_path}")
                
                self._log_status("MIGRATION_REQUIRED", {
                    'reason': growth_decision['reason'],
                    'checkpoint_path': checkpoint_path,
                })
                
                return {
                    'status': 'PAUSED_FOR_MIGRATION',
                    'checkpoint_path': checkpoint_path,
                    'current_layers': self.model.current_layers,
                }
            
            if growth_decision['should_grow']:
                print(f"\n🌱 触发生长！")
                print(f"   原因: {growth_decision['reason']}")
                
                # 执行生长
                prev_layers = self.model.current_layers
                self.model.grow(num_new_layers=1)
                
                # 更新优化器（包含新参数）
                self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
                
                # 如果达到新阶段，更新阶段标记
                if 'next_stage' in growth_decision:
                    self.model.current_stage = growth_decision['next_stage']
                    print(f"   进入新阶段: {self.model.milestones[self.model.current_stage]['name']}")
                
                # 保存生长后的检查点
                checkpoint_path = self.model.save_checkpoint(f'after_grow_to_{self.model.current_layers}layers')
                
                self._log_status("GROWTH_OCCURRED", {
                    'previous_layers': prev_layers,
                    'new_layers': self.model.current_layers,
                    'checkpoint_path': checkpoint_path,
                })
                
                print(f"   新检查点已保存: {checkpoint_path}")
            
            else:
                print(f"   暂不生长: {growth_decision['reason']}")
            
            # 周期性保存（每5个周期）
            if cycle % 5 == 0:
                checkpoint_path = self.model.save_checkpoint(f'periodic_cycle_{cycle}')
                print(f"   周期性检查点已保存: {checkpoint_path}")
            
            # 显示资源状态
            resource_status = self.model.monitor.check_resources()
            if resource_status['alerts']:
                print(f"   ⚠️ 资源警告: {resource_status['alerts']}")
        
        # 达到最大周期
        print(f"\n" + "="*70)
        print("生长循环完成（达到最大周期）")
        print("="*70)
        
        final_checkpoint = self.model.save_checkpoint('experiment_complete')
        
        self._log_status("EXPERIMENT_COMPLETE", {
            'total_cycles': cycle,
            'total_training_steps': total_training_steps,
            'final_layers': self.model.current_layers,
            'final_params_million': self.model.total_params / 1e6,
            'final_checkpoint': final_checkpoint,
        })
        
        return {
            'status': 'COMPLETE',
            'total_cycles': cycle,
            'final_layers': self.model.current_layers,
            'final_checkpoint': final_checkpoint,
        }
    
    def generate_report(self):
        """生成实验报告"""
        report_file = os.path.join(self.log_dir, 'experiment_report.json')
        
        report = {
            'experiment_summary': {
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration_minutes': (datetime.now() - self.start_time).total_seconds() / 60,
                'final_layers': self.model.current_layers,
                'final_params_million': self.model.total_params / 1e6,
                'final_stage': self.model.current_stage,
                'growth_events': len(self.model.growth_history),
            },
            'growth_history': self.model.growth_history,
            'full_log': self.experiment_log,
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 实验报告已保存: {report_file}")
        return report


def main():
    """主函数"""
    # 创建实验（带时间戳的目录）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = f'./growth_experiment_{timestamp}'
    
    experiment = GrowingExperiment(log_dir=log_dir)
    
    # 运行生长循环
    try:
        result = experiment.run_growth_cycle(max_cycles=50)
        
        print(f"\n实验结果: {result['status']}")
        if result['status'] == 'PAUSED_FOR_MIGRATION':
            print(f"\n需要迁移到更强设备后继续")
            print(f"迁移命令:")
            print(f"  1. 复制检查点到新环境: {result['checkpoint_path']}")
            print(f"  2. 在新环境加载: model = ContinuousGrowingTNN.load_checkpoint('{result['checkpoint_path']}')")
            print(f"  3. 继续实验")
        
    except KeyboardInterrupt:
        print(f"\n\n用户中断实验")
        experiment.model.save_checkpoint('user_interrupted')
    
    # 生成报告
    report = experiment.generate_report()
    
    print("\n" + "="*70)
    print("实验完成！")
    print("="*70)
    print(f"日志目录: {log_dir}")
    print(f"最终层数: {experiment.model.current_layers}")
    print(f"最终参数量: {experiment.model.total_params/1e6:.2f}M")
    print(f"生长次数: {len(experiment.model.growth_history)}")


if __name__ == "__main__":
    main()
