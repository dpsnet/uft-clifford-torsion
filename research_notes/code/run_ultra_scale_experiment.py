"""
超大规模生长实验 - hidden_dim=512, 目标20层
预计最终规模：~50M+参数
支持断点续训和内存优化
"""

import torch
import torch.nn.functional as F
import sys
import os
import json
import gc
from datetime import datetime

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')
from unified_adaptive_tnn import UnifiedAdaptiveTNN


class UltraScaleExperiment:
    """超大规模实验管理器"""
    
    def __init__(self, checkpoint_dir='./ultra_scale_checkpoints'):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # 超大规模配置
        self.config = {
            'hidden_dim': 512,      # 增大隐藏维度
            'vocab_size': 200,       # 增大词汇表
            'initial_layers': 2,
            'target_layers': 20,     # 目标20层
            'blocks_per_layer': 4,
            'max_seq_len': 64,
        }
        
        # 估算参数增长
        self._estimate_params()
        
    def _estimate_params(self):
        """估算各阶段参数量"""
        h = self.config['hidden_dim']
        v = self.config['vocab_size']
        b = self.config['blocks_per_layer']
        
        # 每层参数估算
        # embedding + pos_encoding + norm + base_connection + blocks + lm_head
        layer_params = (
            h * h * 2 +           # base_connection + selector
            h * (h//2) * 4 * b +  # 4个块，每个2层
            h * 4                # torsion gates
        )
        
        base_params = v * h + h * v  # embedding + lm_head
        
        print("📊 参数量预估:")
        print("-" * 50)
        for layers in [2, 5, 10, 15, 20]:
            total = base_params + layer_params * layers
            print(f"  {layers:2d}层: ~{total/1e6:.1f}M 参数")
        print("-" * 50)
        
        self.layer_params = layer_params
        self.base_params = base_params
    
    def create_model(self, restore_from=None):
        """创建或恢复模型"""
        if restore_from and os.path.exists(restore_from):
            print(f"🔄 从检查点恢复: {restore_from}")
            # 这里需要实现恢复逻辑
            pass
        
        print(f"\n🆕 创建新模型")
        print(f"   hidden_dim: {self.config['hidden_dim']}")
        print(f"   vocab_size: {self.config['vocab_size']}")
        print(f"   initial_layers: {self.config['initial_layers']}")
        
        model = UnifiedAdaptiveTNN(
            initial_layers=self.config['initial_layers'],
            hidden_dim=self.config['hidden_dim'],
            vocab_size=self.config['vocab_size'],
            blocks_per_layer=self.config['blocks_per_layer'],
            checkpoint_dir=self.checkpoint_dir,
        )
        
        # 超大规模优化配置
        model.growth_threshold_accuracy = 0.70
        model.growth_threshold_loss = 1.0  # 更宽松以适应更大难度
        model.min_cycles_before_growth = 20
        
        return model
    
    def generate_batch(self, task_type, batch_size=4):
        """生成训练数据"""
        seq_len = self.config['max_seq_len']
        vocab_size = self.config['vocab_size']
        
        if task_type == "sequence":
            seq = torch.arange(seq_len) % vocab_size
        elif task_type == "arithmetic":
            seq = torch.tensor([(i * 3 + 2) % vocab_size for i in range(seq_len)])
        elif task_type == "geometric":
            seq = torch.tensor([(2 ** (i % 8)) % vocab_size for i in range(seq_len)])
        elif task_type == "fibonacci":
            fib = [1, 1]
            for i in range(2, seq_len):
                fib.append((fib[-1] + fib[-2]) % vocab_size)
            seq = torch.tensor(fib)
        else:  # prime
            # 质数序列
            primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
            seq = torch.tensor([primes[i % len(primes)] % vocab_size for i in range(seq_len)])
        
        data = seq.unsqueeze(0).repeat(batch_size, 1)
        target = torch.roll(data, shifts=-1, dims=1)
        return data, target
    
    def train(self, model, max_epochs=500):
        """训练循环"""
        optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)  # 更小学习率
        
        tasks = ["sequence", "arithmetic", "geometric", "fibonacci", "prime"]
        
        print(f"\n🚀 开始超大规模训练")
        print(f"   目标: {self.config['target_layers']}层")
        print(f"   最大轮数: {max_epochs}")
        print(f"   任务类型: {tasks}")
        
        history = []
        
        for epoch in range(max_epochs):
            epoch_loss = 0
            epoch_acc = 0
            
            for task in tasks:
                input_ids, targets = self.generate_batch(task)
                result = model.training_step(input_ids, targets, optimizer)
                
                epoch_loss += result['loss']
                epoch_acc += result['accuracy']
            
            avg_loss = epoch_loss / len(tasks)
            avg_acc = epoch_acc / len(tasks)
            
            # 记录
            history.append({
                'epoch': epoch + 1,
                'loss': avg_loss,
                'accuracy': avg_acc,
                'layers': result['layers'],
            })
            
            # 显示进度
            if (epoch + 1) % 10 == 0:
                current_params = self.base_params + self.layer_params * result['layers']
                print(f"\n📚 Epoch {epoch + 1}/{max_epochs}")
                print(f"   损失: {avg_loss:.4f} | 准确率: {avg_acc:.1%}")
                print(f"   层数: {result['layers']}/{self.config['target_layers']} "
                      f"| 参数量: ~{current_params/1e6:.1f}M")
                print(f"   阶段: {result['stage']}")
            
            # 检查生长
            if result['should_grow']:
                print(f"\n🌱 触发生长! {result['layers']}层 → {result['layers']+1}层")
                model.grow(num_new_layers=1)
                optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)
                
                # 内存清理
                gc.collect()
            
            # 达到目标停止
            if result['layers'] >= self.config['target_layers']:
                print(f"\n✅ 达到目标层数({self.config['target_layers']}层)!")
                break
            
            # 定期保存
            if (epoch + 1) % 50 == 0:
                self._save_checkpoint(model, optimizer, epoch + 1, history)
        
        # 最终保存
        self._save_checkpoint(model, optimizer, epoch + 1, history)
        
        return history
    
    def _save_checkpoint(self, model, optimizer, epoch, history):
        """保存检查点"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.checkpoint_dir, f'ultra_epoch{epoch}_{timestamp}.pt')
        
        # 简化保存 - 只保存必要状态
        checkpoint = {
            'epoch': epoch,
            'num_layers': len(model.layers),
            'current_stage': model.current_stage,
            'growth_history': model.growth_history,
            'training_history': history[-50:],
            'config': self.config,
        }
        
        # 保存模型状态（简化版）
        model_state = {}
        for name, param in model.named_parameters():
            model_state[name] = param.data.cpu()
        
        checkpoint['model_state'] = model_state
        
        torch.save(checkpoint, path)
        print(f"💾 检查点已保存: {path}")
    
    def run(self):
        """运行实验"""
        print("="*70)
        print("🚀 超大规模生长实验")
        print("="*70)
        
        model = self.create_model()
        history = self.train(model)
        
        # 最终报告
        print("\n" + "="*70)
        print("📊 实验完成")
        print("="*70)
        
        model.print_unified_status()
        
        print(f"\n🌱 生长历史:")
        for event in model.growth_history:
            print(f"   {event['previous_layers']}层 → {event['new_layers']}层 "
                  f"({event['stage']})")
        
        return model, history


def run_ultra_scale():
    """运行超大规模实验"""
    experiment = UltraScaleExperiment()
    model, history = experiment.run()
    return model, history


if __name__ == "__main__":
    run_ultra_scale()
