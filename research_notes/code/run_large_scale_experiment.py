"""
大规模生长实验 - 支持断点续训
hidden_dim=256, 从2层开始，目标10层+
支持中断后继续训练
"""

import torch
import torch.nn.functional as F
import sys
import os
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')
from unified_adaptive_tnn import UnifiedAdaptiveTNN


class CheckpointManager:
    """检查点管理器 - 支持保存/加载训练状态"""
    
    def __init__(self, checkpoint_dir='./large_scale_checkpoints'):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        self.metadata_file = os.path.join(checkpoint_dir, 'training_metadata.json')
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> dict:
        """加载元数据"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {
            'checkpoints': [],
            'best_accuracy': 0.0,
            'total_epochs': 0,
            'growth_count': 0,
        }
    
    def _save_metadata(self):
        """保存元数据"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def save_checkpoint(self, model: UnifiedAdaptiveTNN, optimizer, 
                       epoch: int, metrics: dict) -> str:
        """保存训练检查点"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        checkpoint_name = f'checkpoint_epoch{epoch}_{timestamp}.pt'
        checkpoint_path = os.path.join(self.checkpoint_dir, checkpoint_name)
        
        # 保存模型状态
        model_state = {
            'embedding': model.embedding.state_dict(),
            'pos_encoding': model.pos_encoding,
            'output_norm': model.output_norm.state_dict(),
            'lm_head': model.lm_head.state_dict(),
            'torsion_field': model.torsion_field,
        }
        
        # 保存层状态
        layers_state = []
        for layer in model.layers:
            layer_state = {
                'norm1': layer.norm1.state_dict(),
                'norm2': layer.norm2.state_dict(),
                'base_connection': layer.base_connection.state_dict(),
                'blocks': [b.state_dict() for b in layer.blocks],
                'block_selector': layer.block_selector.state_dict(),
                'signal_propagator': layer.signal_propagator.state_dict(),
                'loaded_blocks': list(layer.loaded_blocks),
                'layer_stats': layer.layer_stats,
            }
            layers_state.append(layer_state)
        
        checkpoint = {
            'epoch': epoch,
            'model_state': model_state,
            'layers_state': layers_state,
            'num_layers': len(model.layers),
            'current_stage': model.current_stage,
            'cycle_count': model.cycle_count,
            'growth_history': model.growth_history,
            'training_history': model.training_history[-100:] if len(model.training_history) > 100 else model.training_history,
            'optimizer_state': optimizer.state_dict() if optimizer else None,
            'metrics': metrics,
            'timestamp': timestamp,
        }
        
        torch.save(checkpoint, checkpoint_path)
        
        # 更新元数据
        self.metadata['checkpoints'].append({
            'epoch': epoch,
            'path': checkpoint_path,
            'timestamp': timestamp,
            'accuracy': metrics.get('accuracy', 0),
            'layers': len(model.layers),
        })
        
        if metrics.get('accuracy', 0) > self.metadata['best_accuracy']:
            self.metadata['best_accuracy'] = metrics['accuracy']
            # 保存最佳模型副本
            best_path = os.path.join(self.checkpoint_dir, 'best_model.pt')
            torch.save(checkpoint, best_path)
        
        self.metadata['total_epochs'] = epoch
        self.metadata['growth_count'] = len(model.growth_history)
        self._save_metadata()
        
        print(f"💾 检查点已保存: {checkpoint_path}")
        return checkpoint_path
    
    def load_checkpoint(self, checkpoint_path: str = None) -> dict:
        """加载检查点"""
        if checkpoint_path is None:
            # 自动加载最新的
            if not self.metadata['checkpoints']:
                return None
            checkpoint_path = self.metadata['checkpoints'][-1]['path']
        
        if not os.path.exists(checkpoint_path):
            print(f"⚠️ 检查点不存在: {checkpoint_path}")
            return None
        
        print(f"📂 加载检查点: {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        return checkpoint
    
    def restore_model(self, model: UnifiedAdaptiveTNN, checkpoint: dict):
        """从检查点恢复模型"""
        # 恢复基础组件
        model_state = checkpoint['model_state']
        model.embedding.load_state_dict(model_state['embedding'])
        model.pos_encoding = model_state['pos_encoding']
        model.output_norm.load_state_dict(model_state['output_norm'])
        model.lm_head.load_state_dict(model_state['lm_head'])
        model.torsion_field = model_state['torsion_field']
        
        # 调整层数
        current_layers = len(model.layers)
        target_layers = checkpoint['num_layers']
        
        # 添加或删除层以匹配
        while len(model.layers) < target_layers:
            from unified_adaptive_tnn import AdaptiveLayer
            new_layer = AdaptiveLayer(len(model.layers), model.hidden_dim, (2, 2), model.blocks_per_layer)
            model.layers.append(new_layer)
        
        while len(model.layers) > target_layers:
            model.layers.pop()
        
        # 恢复每层状态
        for i, layer_state in enumerate(checkpoint['layers_state']):
            layer = model.layers[i]
            layer.norm1.load_state_dict(layer_state['norm1'])
            layer.norm2.load_state_dict(layer_state['norm2'])
            layer.base_connection.load_state_dict(layer_state['base_connection'])
            layer.block_selector.load_state_dict(layer_state['block_selector'])
            layer.signal_propagator.load_state_dict(layer_state['signal_propagator'])
            
            # 恢复块状态
            for j, block_state in enumerate(layer_state['blocks']):
                layer.blocks[j].load_state_dict(block_state)
            
            layer.loaded_blocks = set(layer_state['loaded_blocks'])
            layer.layer_stats = layer_state['layer_stats']
        
        # 恢复其他状态
        model.current_stage = checkpoint['current_stage']
        model.cycle_count = checkpoint['cycle_count']
        model.growth_history = checkpoint['growth_history']
        model.training_history = checkpoint['training_history']
        
        print(f"✅ 模型恢复完成: {checkpoint['num_layers']}层, Epoch {checkpoint['epoch']}")
        return checkpoint.get('epoch', 0), checkpoint.get('optimizer_state')


def run_large_scale_experiment():
    """运行大规模实验"""
    print("="*70)
    print("🚀 大规模生长实验")
    print("="*70)
    print("配置: hidden_dim=256, vocab_size=100")
    print("目标: 2层 → 10层")
    print("特性: 支持断点续训")
    print("="*70)
    
    # 检查点管理器
    checkpoint_mgr = CheckpointManager('./large_scale_checkpoints')
    
    # 尝试恢复
    checkpoint = checkpoint_mgr.load_checkpoint()
    start_epoch = 0
    
    if checkpoint:
        # 恢复模型
        hidden_dim = 256  # 必须与保存时一致
        vocab_size = 100
        
        model = UnifiedAdaptiveTNN(
            initial_layers=checkpoint['num_layers'],
            hidden_dim=hidden_dim,
            vocab_size=vocab_size,
            blocks_per_layer=4,
            checkpoint_dir='./large_scale_checkpoints',
        )
        
        start_epoch, optimizer_state = checkpoint_mgr.restore_model(model, checkpoint)
        start_epoch += 1  # 从下一epoch开始
        
        print(f"\n🔄 恢复训练，从Epoch {start_epoch}继续")
    else:
        # 新建模型
        print("\n🆕 新建模型")
        model = UnifiedAdaptiveTNN(
            initial_layers=2,
            hidden_dim=256,
            vocab_size=100,
            blocks_per_layer=4,
            checkpoint_dir='./large_scale_checkpoints',
        )
    
    # 配置（使用更保守的设置以适应更大规模）
    model.growth_threshold_accuracy = 0.75  # 稍低以适应更大难度
    model.growth_threshold_loss = 0.8
    model.min_cycles_before_growth = 15
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # 如果恢复了优化器状态
    if checkpoint and 'optimizer_state' in checkpoint and checkpoint['optimizer_state']:
        try:
            optimizer.load_state_dict(checkpoint['optimizer_state'])
            print("✅ 优化器状态已恢复")
        except:
            print("⚠️ 优化器状态恢复失败，使用新优化器")
    
    # 生成训练数据（更复杂的任务）
    def generate_batch(task_type: str, batch_size: int = 8):
        seq_len = 32
        
        if task_type == "simple":
            # 简单重复
            seq = torch.arange(seq_len) % model.vocab_size
        elif task_type == "arithmetic":
            # 算术序列
            seq = torch.tensor([(i * 2 + 1) % model.vocab_size for i in range(seq_len)])
        elif task_type == "fibonacci":
            # 类斐波那契
            fib = [1, 1]
            for i in range(2, seq_len):
                fib.append((fib[-1] + fib[-2]) % model.vocab_size)
            seq = torch.tensor(fib)
        else:  # random_pattern
            # 随机但固定的模式
            torch.manual_seed(42)
            seq = torch.randint(0, model.vocab_size, (seq_len,))
            torch.manual_seed(int(datetime.now().timestamp()))
        
        data = seq.unsqueeze(0).repeat(batch_size, 1)
        target = torch.roll(data, shifts=-1, dims=1)
        return data, target
    
    tasks = ["simple", "arithmetic", "fibonacci", "random_pattern"]
    
    print(f"\n初始状态:")
    print(f"  层数: {model.num_layers}")
    print(f"  隐藏维度: 256")
    print(f"  阶段: {model.stages[model.current_stage][0]}")
    print(f"  生长阈值: 准确率>{model.growth_threshold_accuracy:.0%}, 损失<{model.growth_threshold_loss}")
    
    print(f"\n训练任务: {tasks}")
    
    # 训练循环
    max_epochs = 200
    save_every = 10  # 每10轮保存一次
    
    print("\n" + "-"*70)
    print("开始训练（按Ctrl+C可中断，下次会自动恢复）")
    print("-"*70)
    
    try:
        for epoch in range(start_epoch, max_epochs):
            epoch_loss = 0
            epoch_acc = 0
            
            for task in tasks:
                input_ids, targets = generate_batch(task)
                result = model.training_step(input_ids, targets, optimizer)
                
                epoch_loss += result['loss']
                epoch_acc += result['accuracy']
            
            avg_loss = epoch_loss / len(tasks)
            avg_acc = epoch_acc / len(tasks)
            
            # 显示状态
            if (epoch + 1) % 5 == 0:
                print(f"\n📚 Epoch {epoch + 1}/{max_epochs}")
                print(f"   损失: {avg_loss:.4f} | 准确率: {avg_acc:.1%}")
                print(f"   层数: {result['layers']} | 阶段: {result['stage']}")
                
                for li, ls in enumerate(result['layer_stats']):
                    print(f"   层{li}: {ls['block_count']}块 兴奋度={ls['avg_excitement']:.2f}")
            
            # 检查生长
            if result['should_grow']:
                print(f"\n🌱 触发生长!")
                model.grow(num_new_layers=1)
                optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            
            # 定期保存检查点
            if (epoch + 1) % save_every == 0:
                metrics = {'loss': avg_loss, 'accuracy': avg_acc}
                checkpoint_mgr.save_checkpoint(model, optimizer, epoch + 1, metrics)
            
            # 达到10层停止
            if model.num_layers >= 10:
                print(f"\n✅ 达到目标层数(10层)，停止训练")
                # 保存最终检查点
                metrics = {'loss': avg_loss, 'accuracy': avg_acc}
                checkpoint_mgr.save_checkpoint(model, optimizer, epoch + 1, metrics)
                break
    
    except KeyboardInterrupt:
        print(f"\n\n⚠️ 训练被中断")
        print("保存检查点...")
        metrics = {'loss': avg_loss, 'accuracy': avg_acc}
        checkpoint_mgr.save_checkpoint(model, optimizer, epoch + 1, metrics)
        print("✅ 检查点已保存，下次运行会自动恢复")
        return model
    
    # 最终状态
    print("\n" + "="*70)
    print("📊 最终状态")
    print("="*70)
    
    model.print_unified_status()
    
    print(f"\n🌱 生长历史:")
    for event in model.growth_history:
        print(f"   {event['timestamp']}: {event['previous_layers']}层 → {event['new_layers']}层 "
              f"({event['stage']})")
    
    # 保存最终检查点
    metrics = {'loss': avg_loss, 'accuracy': avg_acc}
    final_checkpoint = checkpoint_mgr.save_checkpoint(model, optimizer, epoch + 1, metrics)
    
    print(f"\n💾 最终检查点: {final_checkpoint}")
    print("\n" + "="*70)
    print("实验完成!")
    print("="*70)
    
    return model


if __name__ == "__main__":
    run_large_scale_experiment()
