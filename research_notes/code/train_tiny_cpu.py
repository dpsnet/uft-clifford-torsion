"""
TNN-Transformer Tiny CPU训练脚本
1M参数微型模型的CPU训练实现

特性:
- 支持梯度累积
- 禁用FP16混合精度
- 内存优化
- 实时监控和报告生成

作者: AI Research Assistant
日期: 2026-03-18
"""

import os
import sys
import time
import json
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import math

import numpy as np
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

# 添加代码目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tnn_transformer_tiny import TNNTransformerTinyLM, TNNTransformerTinyConfig, create_tiny_tnn_transformer
from prepare_tiny_data import prepare_data, load_prepared_data, SimpleBPETokenizer


# =============================================================================
# 配置加载
# =============================================================================

def load_config(config_path: str) -> Dict:
    """加载YAML配置"""
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except ImportError:
        print("警告: 未安装PyYAML，使用默认配置")
        return get_default_config()


def get_default_config() -> Dict:
    """默认配置"""
    return {
        'model': {
            'vocab_size': 10000,
            'max_position_embeddings': 512,
            'hidden_size': 128,
            'num_hidden_layers': 4,
            'num_attention_heads': 4,
            'intermediate_size': 512,
            'internal_dim': 32,
            'torsion_order': 2,
            'spectral_dim_min': 2.0,
            'spectral_dim_max': 8.0,
            'adaptation_rate': 0.02,
        },
        'training': {
            'max_steps': 10000,
            'warmup_steps': 500,
            'eval_steps': 100,
            'save_steps': 1000,
            'logging_steps': 50,
            'gradient_accumulation_steps': 4,
            'optimizer': {
                'learning_rate': 5e-4,
                'weight_decay': 0.01,
                'beta1': 0.9,
                'beta2': 0.95,
            },
            'lr_scheduler': {
                'min_lr_ratio': 0.1,
            }
        },
        'data': {
            'batch_size': 8,
        },
        'output': {
            'output_dir': './outputs/tnn_tiny_1m',
            'checkpoint_dir': './checkpoints/tnn_tiny_1m',
        }
    }


# =============================================================================
# 学习率调度器
# =============================================================================

class CosineWarmupScheduler:
    """余弦学习率调度器 (带warmup)"""
    
    def __init__(self, optimizer, warmup_steps: int, max_steps: int, 
                 max_lr: float, min_lr: float):
        self.optimizer = optimizer
        self.warmup_steps = warmup_steps
        self.max_steps = max_steps
        self.max_lr = max_lr
        self.min_lr = min_lr
        self.current_step = 0
        
    def step(self):
        """更新学习率"""
        self.current_step += 1
        
        if self.current_step < self.warmup_steps:
            # 线性warmup
            lr = self.max_lr * self.current_step / self.warmup_steps
        else:
            # 余弦退火
            progress = (self.current_step - self.warmup_steps) / (self.max_steps - self.warmup_steps)
            lr = self.min_lr + (self.max_lr - self.min_lr) * 0.5 * (1 + math.cos(math.pi * progress))
        
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = lr
        
        return lr
    
    def get_lr(self) -> float:
        """获取当前学习率"""
        return self.optimizer.param_groups[0]['lr']


# =============================================================================
# 训练统计
# =============================================================================

class TrainingStats:
    """训练统计跟踪"""
    
    def __init__(self):
        self.step_losses = []
        self.eval_losses = []
        self.spectral_dims = []
        self.torsion_energies = []
        self.learning_rates = []
        self.timestamps = []
        
    def add_step(self, step: int, loss: float, spectral_dim: float, 
                 torsion_energy: float, lr: float):
        """添加训练步骤统计"""
        self.step_losses.append((step, loss))
        self.spectral_dims.append((step, spectral_dim))
        self.torsion_energies.append((step, torsion_energy))
        self.learning_rates.append((step, lr))
        self.timestamps.append(time.time())
    
    def add_eval(self, step: int, loss: float, perplexity: float):
        """添加评估统计"""
        self.eval_losses.append((step, loss, perplexity))
    
    def save(self, path: str):
        """保存统计"""
        data = {
            'step_losses': self.step_losses,
            'eval_losses': self.eval_losses,
            'spectral_dims': self.spectral_dims,
            'torsion_energies': self.torsion_energies,
            'learning_rates': self.learning_rates,
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def plot(self, save_dir: str):
        """绘制训练曲线"""
        os.makedirs(save_dir, exist_ok=True)
        
        # 损失曲线
        if self.step_losses:
            steps, losses = zip(*self.step_losses)
            plt.figure(figsize=(10, 6))
            plt.plot(steps, losses, alpha=0.3, label='Training Loss')
            
            # 移动平均
            window = min(50, len(losses) // 10)
            if window > 1:
                smoothed = np.convolve(losses, np.ones(window)/window, mode='valid')
                plt.plot(steps[window-1:], smoothed, label=f'MA({window})', linewidth=2)
            
            plt.xlabel('Step')
            plt.ylabel('Loss')
            plt.title('Training Loss')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig(os.path.join(save_dir, 'loss_curve.png'), dpi=150, bbox_inches='tight')
            plt.close()
        
        # 谱维演化
        if self.spectral_dims:
            steps, dims = zip(*self.spectral_dims)
            plt.figure(figsize=(10, 6))
            plt.plot(steps, dims, label='Spectral Dimension')
            plt.axhline(y=4.0, color='r', linestyle='--', alpha=0.5, label='Target (d_s=4)')
            plt.xlabel('Step')
            plt.ylabel('Spectral Dimension')
            plt.title('Spectral Dimension Evolution')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig(os.path.join(save_dir, 'spectral_dim.png'), dpi=150, bbox_inches='tight')
            plt.close()
        
        # 扭转场能量
        if self.torsion_energies:
            steps, energies = zip(*self.torsion_energies)
            plt.figure(figsize=(10, 6))
            plt.plot(steps, energies, label='Torsion Energy', color='green')
            plt.xlabel('Step')
            plt.ylabel('Torsion Energy')
            plt.title('Torsion Field Energy')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig(os.path.join(save_dir, 'torsion_energy.png'), dpi=150, bbox_inches='tight')
            plt.close()
        
        # 学习率
        if self.learning_rates:
            steps, lrs = zip(*self.learning_rates)
            plt.figure(figsize=(10, 6))
            plt.plot(steps, lrs, label='Learning Rate', color='orange')
            plt.xlabel('Step')
            plt.ylabel('Learning Rate')
            plt.title('Learning Rate Schedule')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig(os.path.join(save_dir, 'learning_rate.png'), dpi=150, bbox_inches='tight')
            plt.close()


# =============================================================================
# 评估函数
# =============================================================================

@torch.no_grad()
def evaluate(model: nn.Module, dataloader: DataLoader, max_iters: int = 50) -> Dict[str, float]:
    """评估模型"""
    model.eval()
    
    total_loss = 0.0
    total_tokens = 0
    all_spectral_dims = []
    all_torsion_energies = []
    
    for i, batch in enumerate(dataloader):
        if i >= max_iters:
            break
        
        batch = batch.to(model.wte.weight.device)
        
        outputs = model(batch, labels=batch)
        
        # 计算token级别的损失
        shift_logits = outputs['logits'][:, :-1, :].contiguous()
        shift_labels = batch[:, 1:].contiguous()
        
        # 只计算非pad token的损失
        mask = (shift_labels != 0).float()
        loss_fct = nn.CrossEntropyLoss(reduction='none')
        loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
        loss = loss * mask.view(-1)
        
        total_loss += loss.sum().item()
        total_tokens += mask.sum().item()
        
        all_spectral_dims.append(outputs['spectral_dimension'])
        all_torsion_energies.append(outputs['torsion_energy'])
    
    avg_loss = total_loss / total_tokens if total_tokens > 0 else float('inf')
    perplexity = math.exp(avg_loss) if avg_loss < 10 else float('inf')
    
    model.train()
    
    return {
        'loss': avg_loss,
        'perplexity': perplexity,
        'spectral_dimension': np.mean(all_spectral_dims),
        'torsion_energy': np.mean(all_torsion_energies),
    }


# =============================================================================
# 生成样本
# =============================================================================

@torch.no_grad()
def generate_samples(model: nn.Module, tokenizer: SimpleBPETokenizer, 
                     prompts: List[str], max_length: int = 50, 
                     device: str = 'cpu') -> List[str]:
    """生成文本样本"""
    model.eval()
    
    results = []
    for prompt in prompts:
        input_ids = torch.tensor([tokenizer.encode(prompt, add_special_tokens=True)], device=device)
        
        generated = model.generate(input_ids, max_length=max_length, temperature=1.0, top_k=20)
        
        generated_text = tokenizer.decode(generated[0].cpu().tolist())
        results.append({
            'prompt': prompt,
            'generated': generated_text,
        })
    
    model.train()
    return results


# =============================================================================
# 训练循环
# =============================================================================

def train(
    config: Dict,
    train_dataset: Dataset,
    val_dataset: Dataset,
    tokenizer: SimpleBPETokenizer,
    device: str = 'cpu',
):
    """主训练循环"""
    
    # 配置
    model_config = config['model']
    training_config = config['training']
    data_config = config['data']
    output_config = config['output']
    
    # 创建输出目录
    output_dir = output_config['output_dir']
    checkpoint_dir = output_config['checkpoint_dir']
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    # 保存配置
    with open(os.path.join(output_dir, 'config.json'), 'w') as f:
        json.dump(config, f, indent=2)
    
    # 创建模型
    print("\n" + "="*60)
    print("创建TNN-Transformer Tiny模型")
    print("="*60)
    
    model_config_obj = TNNTransformerTinyConfig(**model_config)
    model = TNNTransformerTinyLM(model_config_obj).to(device)
    
    n_params = sum(p.numel() for p in model.parameters())
    print(f"\n模型参数量: {n_params/1e6:.2f}M")
    
    # 创建数据加载器
    train_loader = DataLoader(
        train_dataset,
        batch_size=data_config.get('batch_size', 8),
        shuffle=True,
        num_workers=0,  # CPU训练使用0
        pin_memory=False,
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=data_config.get('batch_size', 8),
        shuffle=False,
        num_workers=0,
        pin_memory=False,
    )
    
    # 创建优化器
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=training_config['optimizer']['learning_rate'],
        betas=(training_config['optimizer']['beta1'], training_config['optimizer']['beta2']),
        weight_decay=training_config['optimizer']['weight_decay'],
        eps=1e-8,
    )
    
    # 创建学习率调度器
    scheduler = CosineWarmupScheduler(
        optimizer,
        warmup_steps=training_config['warmup_steps'],
        max_steps=training_config['max_steps'],
        max_lr=training_config['optimizer']['learning_rate'],
        min_lr=training_config['optimizer']['learning_rate'] * 
               training_config['lr_scheduler']['min_lr_ratio'],
    )
    
    # 训练参数
    max_steps = training_config['max_steps']
    eval_steps = training_config['eval_steps']
    save_steps = training_config['save_steps']
    logging_steps = training_config['logging_steps']
    grad_accum_steps = training_config.get('gradient_accumulation_steps', 1)
    
    # 训练统计
    stats = TrainingStats()
    
    # 训练循环
    print("\n" + "="*60)
    print("开始训练")
    print("="*60)
    
    model.train()
    step = 0
    epoch = 0
    accumulated_loss = 0.0
    accumulated_spectral_dim = 0.0
    accumulated_torsion_energy = 0.0
    
    start_time = time.time()
    
    while step < max_steps:
        epoch += 1
        
        for batch_idx, batch in enumerate(train_loader):
            if step >= max_steps:
                break
            
            batch = batch.to(device)
            
            # 前向传播
            outputs = model(batch, labels=batch)
            loss = outputs['loss']
            
            # 梯度累积
            loss = loss / grad_accum_steps
            loss.backward()
            
            accumulated_loss += loss.item()
            accumulated_spectral_dim += outputs['spectral_dimension']
            accumulated_torsion_energy += outputs['torsion_energy']
            
            # 梯度更新
            if (batch_idx + 1) % grad_accum_steps == 0:
                # 梯度裁剪
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                
                optimizer.step()
                optimizer.zero_grad()
                scheduler.step()
                
                step += 1
                
                # 记录统计
                avg_loss = accumulated_loss
                avg_spectral_dim = accumulated_spectral_dim / grad_accum_steps
                avg_torsion_energy = accumulated_torsion_energy / grad_accum_steps
                current_lr = scheduler.get_lr()
                
                stats.add_step(step, avg_loss, avg_spectral_dim, avg_torsion_energy, current_lr)
                
                # 打印日志
                if step % logging_steps == 0:
                    elapsed = time.time() - start_time
                    tokens_per_sec = (step * train_loader.batch_size * model_config['max_position_embeddings']) / elapsed
                    
                    print(f"Step {step}/{max_steps} | "
                          f"Loss: {avg_loss:.4f} | "
                          f"d_s: {avg_spectral_dim:.2f} | "
                          f"E_t: {avg_torsion_energy:.4f} | "
                          f"LR: {current_lr:.2e} | "
                          f"{elapsed:.1f}s")
                
                # 重置累积
                accumulated_loss = 0.0
                accumulated_spectral_dim = 0.0
                accumulated_torsion_energy = 0.0
                
                # 评估
                if step % eval_steps == 0:
                    print(f"\n[Step {step}] 进行评估...")
                    eval_results = evaluate(model, val_loader, max_iters=50)
                    
                    stats.add_eval(step, eval_results['loss'], eval_results['perplexity'])
                    
                    print(f"  Eval Loss: {eval_results['loss']:.4f}")
                    print(f"  Perplexity: {eval_results['perplexity']:.2f}")
                    print(f"  Spectral Dim: {eval_results['spectral_dimension']:.2f}")
                    print(f"  Torsion Energy: {eval_results['torsion_energy']:.4f}")
                    
                    # 生成样本
                    prompts = [
                        "Once upon a time",
                        "In a small village",
                        "The little girl",
                        "A brave knight",
                    ]
                    samples = generate_samples(model, tokenizer, prompts, max_length=50, device=device)
                    
                    print("\n  生成样本:")
                    for sample in samples[:2]:  # 只显示前2个
                        print(f"    '{sample['prompt']}' -> '{sample['generated'][:100]}...'")
                    print()
                
                # 保存检查点
                if step % save_steps == 0:
                    checkpoint_path = os.path.join(checkpoint_dir, f"checkpoint_step_{step}.pt")
                    torch.save({
                        'step': step,
                        'model_state_dict': model.state_dict(),
                        'optimizer_state_dict': optimizer.state_dict(),
                        'scheduler_state_dict': {'current_step': scheduler.current_step},
                        'loss': avg_loss,
                    }, checkpoint_path)
                    print(f"[Step {step}] 检查点已保存: {checkpoint_path}")
                    
                    # 保存模型
                    model.save_pretrained(os.path.join(checkpoint_dir, f"model_step_{step}"))
    
    # 训练结束
    total_time = time.time() - start_time
    print("\n" + "="*60)
    print("训练完成!")
    print(f"总时间: {total_time/3600:.2f}小时")
    print(f"平均速度: {step/total_time:.2f} steps/s")
    print("="*60)
    
    # 最终评估
    print("\n最终评估...")
    final_eval = evaluate(model, val_loader, max_iters=100)
    print(f"Final Loss: {final_eval['loss']:.4f}")
    print(f"Final Perplexity: {final_eval['perplexity']:.2f}")
    
    # 保存最终模型
    model.save_pretrained(os.path.join(checkpoint_dir, "final_model"))
    
    # 保存统计
    stats.save(os.path.join(output_dir, 'training_stats.json'))
    stats.plot(os.path.join(output_dir, 'plots'))
    
    # 生成最终报告
    generate_report(stats, final_eval, output_dir, total_time, n_params)
    
    return model, stats


def generate_report(stats: TrainingStats, final_eval: Dict, output_dir: str, 
                    total_time: float, n_params: int):
    """生成训练报告"""
    
    report_path = os.path.join(output_dir, 'training_report.md')
    
    with open(report_path, 'w') as f:
        f.write("# TNN-Transformer Tiny 训练报告\n\n")
        f.write(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 模型信息\n\n")
        f.write(f"- 参数量: {n_params/1e6:.2f}M\n")
        f.write(f"- 隐藏维度: 128\n")
        f.write(f"- 层数: 4\n")
        f.write(f"- 注意力头数: 4\n\n")
        
        f.write("## 训练统计\n\n")
        f.write(f"- 总训练步数: {len(stats.step_losses)}\n")
        f.write(f"- 总训练时间: {total_time/3600:.2f}小时\n")
        f.write(f"- 平均速度: {len(stats.step_losses)/total_time:.2f} steps/s\n\n")
        
        f.write("## 最终评估结果\n\n")
        f.write(f"- 验证损失: {final_eval['loss']:.4f}\n")
        f.write(f"- 验证困惑度: {final_eval['perplexity']:.2f}\n")
        f.write(f"- 谱维: {final_eval['spectral_dimension']:.2f}\n")
        f.write(f"- 扭转场能量: {final_eval['torsion_energy']:.4f}\n\n")
        
        f.write("## 谱维演化\n\n")
        if stats.spectral_dims:
            initial_d_s = stats.spectral_dims[0][1]
            final_d_s = stats.spectral_dims[-1][1]
            f.write(f"- 初始谱维: {initial_d_s:.2f}\n")
            f.write(f"- 最终谱维: {final_d_s:.2f}\n")
            f.write(f"- 变化: {final_d_s - initial_d_s:+.2f}\n\n")
        
        f.write("## 扭转场能量\n\n")
        if stats.torsion_energies:
            initial_e = stats.torsion_energies[0][1]
            final_e = stats.torsion_energies[-1][1]
            f.write(f"- 初始能量: {initial_e:.4f}\n")
            f.write(f"- 最终能量: {final_e:.4f}\n")
            f.write(f"- 变化: {final_e - initial_e:+.4f}\n\n")
        
        f.write("## 验证目标检查\n\n")
        
        # 检查损失下降
        if stats.step_losses:
            initial_loss = stats.step_losses[0][1]
            final_loss = stats.step_losses[-1][1]
            loss_decreased = final_loss < initial_loss
            f.write(f"- [ {'✓' if loss_decreased else '✗'} ] 损失下降: {initial_loss:.4f} → {final_loss:.4f}\n")
        
        # 检查谱维
        if stats.spectral_dims:
            spectral_in_range = 2.5 <= final_eval['spectral_dimension'] <= 6.0
            f.write(f"- [ {'✓' if spectral_in_range else '✗'} ] 谱维在期望范围 [2.5, 6.0]\n")
        
        # 检查扭转场能量
        energy_stable = abs(final_e - initial_e) < 0.5 if stats.torsion_energies else False
        f.write(f"- [ {'✓' if energy_stable else '✗'} ] 扭转场能量稳定\n")
        
        f.write("\n## 图表\n\n")
        f.write("- [损失曲线](./plots/loss_curve.png)\n")
        f.write("- [谱维演化](./plots/spectral_dim.png)\n")
        f.write("- [扭转场能量](./plots/torsion_energy.png)\n")
        f.write("- [学习率调度](./plots/learning_rate.png)\n\n")
        
        f.write("---\n\n")
        f.write("*由TNN-Transformer Tiny CPU训练脚本生成*\n")
    
    print(f"\n报告已保存至: {report_path}")


# =============================================================================
# 主函数
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="TNN-Transformer Tiny CPU训练")
    parser.add_argument("--config", type=str, default=None,
                        help="配置文件路径")
    parser.add_argument("--data_dir", type=str, default="./data",
                        help="数据目录")
    parser.add_argument("--dataset", type=str, default="tinystories",
                        choices=["tinystories", "wikitext2"],
                        help="数据集名称")
    parser.add_argument("--vocab_size", type=int, default=10000,
                        help="词表大小")
    parser.add_argument("--max_samples", type=int, default=100000,
                        help="最大样本数")
    parser.add_argument("--max_steps", type=int, default=10000,
                        help="最大训练步数")
    parser.add_argument("--batch_size", type=int, default=8,
                        help="批次大小")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4,
                        help="梯度累积步数")
    parser.add_argument("--lr", type=float, default=5e-4,
                        help="学习率")
    parser.add_argument("--seed", type=int, default=42,
                        help="随机种子")
    parser.add_argument("--skip_data_prep", action="store_true",
                        help="跳过数据准备")
    
    args = parser.parse_args()
    
    # 设置随机种子
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    
    # 设备
    device = 'cpu'
    print(f"使用设备: {device}")
    
    # 加载配置
    if args.config:
        config = load_config(args.config)
    else:
        config = get_default_config()
    
    # 覆盖配置
    config['training']['max_steps'] = args.max_steps
    config['training']['gradient_accumulation_steps'] = args.gradient_accumulation_steps
    config['data']['batch_size'] = args.batch_size
    config['training']['optimizer']['learning_rate'] = args.lr
    config['model']['vocab_size'] = args.vocab_size
    
    # 准备数据
    if not args.skip_data_prep:
        data_info = prepare_data(
            dataset_name=args.dataset,
            data_dir=args.data_dir,
            vocab_size=args.vocab_size,
            max_length=config['model']['max_position_embeddings'],
            max_samples=args.max_samples,
        )
        
        # 加载准备好的数据
        processed_dir = os.path.join(args.data_dir, "processed", args.dataset)
        train_dataset, val_dataset, tokenizer = load_prepared_data(processed_dir)
    else:
        # 直接加载
        processed_dir = os.path.join(args.data_dir, "processed", args.dataset)
        train_dataset, val_dataset, tokenizer = load_prepared_data(processed_dir)
    
    print(f"\n训练集大小: {len(train_dataset)}")
    print(f"验证集大小: {len(val_dataset)}")
    
    # 更新配置中的vocab_size
    config['model']['vocab_size'] = len(tokenizer.vocab)
    
    # 开始训练
    model, stats = train(config, train_dataset, val_dataset, tokenizer, device)
    
    print("\n✓ 训练完成!")


if __name__ == "__main__":
    main()
