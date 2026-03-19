"""
TNN-Transformer 损失函数调优实验
测试不同正则化策略对1.39M参数模型存储能力的影响

实验目标：找到让扭转场能量稳定、同时最大化模型存储容量的损失函数配置
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import os
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# 导入基础模型
sys.path.insert(0, str(Path(__file__).parent))
from tnn_transformer_tiny import TNNTransformerTinyLM, TNNTransformerTinyConfig, create_tiny_tnn_transformer


# =============================================================================
# 实验配置
# =============================================================================

@dataclass
class LossConfig:
    """损失函数配置"""
    name: str
    torsion_coef: float = 0.0001  # 扭转场正则化系数
    torsion_min_energy: float = 0.0  # 最小能量约束 (0表示无约束)
    torsion_target: Optional[float] = None  # 目标能量值 (None表示无目标)
    spectral_reg: float = 0.0  # 谱维正则化
    entropy_reg: float = 0.0  # 熵正则化 (鼓励多样性)
    description: str = ""


# 定义要测试的配置
EXPERIMENT_CONFIGS = [
    LossConfig(
        name="baseline",
        torsion_coef=0.0001,
        description="原始配置 - 基准线"
    ),
    LossConfig(
        name="strong_reg",
        torsion_coef=0.001,
        description="10倍强正则化"
    ),
    LossConfig(
        name="very_strong_reg",
        torsion_coef=0.01,
        description="100倍强正则化"
    ),
    LossConfig(
        name="min_energy_1",
        torsion_coef=0.001,
        torsion_min_energy=1.0,
        description="强正则化 + 最小能量约束=1.0"
    ),
    LossConfig(
        name="min_energy_5",
        torsion_coef=0.001,
        torsion_min_energy=5.0,
        description="强正则化 + 最小能量约束=5.0"
    ),
    LossConfig(
        name="target_energy_3",
        torsion_coef=0.001,
        torsion_target=3.0,
        description="强正则化 + 目标能量=3.0"
    ),
    LossConfig(
        name="entropy_bonus",
        torsion_coef=0.001,
        entropy_reg=0.01,
        description="强正则化 + 熵奖励"
    ),
    LossConfig(
        name="adaptive_reg",
        torsion_coef=-1.0,  # 标记为自适应
        description="自适应正则化 (根据能量动态调整)"
    ),
]


# =============================================================================
# 修改后的模型 (支持不同的损失函数配置)
# =============================================================================

class TNNTransformerWithLossConfig(TNNTransformerTinyLM):
    """支持自定义损失函数配置的TNN模型"""
    
    def __init__(self, config: TNNTransformerTinyConfig, loss_config: LossConfig):
        super().__init__(config)
        self.loss_config = loss_config
        self.step_count = 0
        
    def forward(self, input_ids: torch.Tensor,
                attention_mask: Optional[torch.Tensor] = None,
                labels: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        """前向传播 - 使用自定义损失配置"""
        batch_size, seq_len = input_ids.shape
        device = input_ids.device
        
        # 位置ID
        position_ids = torch.arange(0, seq_len, dtype=torch.long, device=device).unsqueeze(0)
        
        # 嵌入
        inputs_embeds = self.wte(input_ids)
        position_embeds = self.wpe(position_ids)
        hidden_states = inputs_embeds + position_embeds
        hidden_states = self.drop(hidden_states)
        
        # 因果掩码
        causal_mask = torch.triu(
            torch.ones((seq_len, seq_len), device=device) * float('-inf'), diagonal=1
        )
        causal_mask = causal_mask.unsqueeze(0).unsqueeze(0)
        
        # 深度缩放
        depth_scale = self.spectral_manager.get_depth_scale()
        
        # Transformer层
        internal_states = None
        all_torsion_energies = []
        
        for layer in self.layers:
            hidden_states, internal_states = layer(
                hidden_states, internal_states, causal_mask, depth_scale
            )
            all_torsion_energies.append(layer.get_torsion_energy())
        
        hidden_states = self.ln_f(hidden_states)
        
        # 语言建模头
        logits = self.lm_head(hidden_states)
        
        # 计算损失
        loss = None
        torsion_loss = torch.tensor(0.0, device=device)
        entropy_loss = torch.tensor(0.0, device=device)
        spectral_loss = torch.tensor(0.0, device=device)
        
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss_fct = nn.CrossEntropyLoss()
            base_loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
            loss = base_loss
            
            # 计算总扭转场能量
            total_torsion_energy = sum(all_torsion_energies)
            avg_torsion_energy = total_torsion_energy / len(all_torsion_energies)
            
            lc = self.loss_config
            
            # 1. 扭转场正则化
            if lc.torsion_coef > 0:
                torsion_loss = lc.torsion_coef * total_torsion_energy
                
                # 最小能量约束 (如果能量太低，给予惩罚)
                if lc.torsion_min_energy > 0:
                    min_energy_penalty = torch.relu(lc.torsion_min_energy - avg_torsion_energy)
                    torsion_loss = torsion_loss + 0.1 * min_energy_penalty ** 2
                
                # 目标能量约束 (鼓励能量接近目标值)
                if lc.torsion_target is not None:
                    target_penalty = (avg_torsion_energy - lc.torsion_target) ** 2
                    torsion_loss = torsion_loss + 0.01 * target_penalty
                
                loss = loss + torsion_loss
            
            # 2. 自适应正则化
            elif lc.torsion_coef == -1.0:  # 自适应模式
                # 如果能量太低，增加正则化；如果能量合适，减少正则化
                if avg_torsion_energy < 1.0:
                    adaptive_coef = 0.01 * (1.0 - avg_torsion_energy)
                    torsion_loss = adaptive_coef * total_torsion_energy
                elif avg_torsion_energy > 10.0:
                    adaptive_coef = 0.001
                    torsion_loss = adaptive_coef * total_torsion_energy
                else:
                    adaptive_coef = 0.0001
                    torsion_loss = adaptive_coef * total_torsion_energy
                loss = loss + torsion_loss
            
            # 3. 谱维正则化 (鼓励谱维在合理范围内)
            if lc.spectral_reg > 0:
                current_d_s = self.spectral_manager.current_d_s
                # 鼓励谱维在 3-6 之间
                spectral_penalty = torch.relu(3.0 - current_d_s) + torch.relu(current_d_s - 6.0)
                spectral_loss = lc.spectral_reg * spectral_penalty
                loss = loss + spectral_loss
            
            # 4. 熵正则化 (鼓励输出分布的多样性)
            if lc.entropy_reg > 0:
                probs = F.softmax(logits, dim=-1)
                entropy = -torch.sum(probs * torch.log(probs + 1e-10), dim=-1).mean()
                # 负号是因为我们要最大化熵（增加多样性）
                entropy_loss = -lc.entropy_reg * entropy
                loss = loss + entropy_loss
        
        # 更新谱维
        current_d_s = self.spectral_manager.update_spectral_dimension(hidden_states, loss)
        
        self.step_count += 1
        
        return {
            'loss': loss,
            'base_loss': base_loss if labels is not None else None,
            'torsion_loss': torsion_loss,
            'entropy_loss': entropy_loss,
            'spectral_loss': spectral_loss,
            'logits': logits,
            'last_hidden_state': hidden_states,
            'spectral_dimension': current_d_s,
            'torsion_energy': avg_torsion_energy.item() if labels is not None else 0.0,
            'depth_scale': depth_scale,
        }


# =============================================================================
# 数据生成
# =============================================================================

def generate_synthetic_data(vocab_size: int, num_sequences: int, seq_length: int, 
                            pattern_type: str = "random") -> Tuple[torch.Tensor, torch.Tensor]:
    """生成合成训练数据"""
    
    if pattern_type == "random":
        # 纯随机数据 (最难记忆)
        input_ids = torch.randint(0, vocab_size, (num_sequences, seq_length))
        labels = input_ids.clone()
        
    elif pattern_type == "repeat":
        # 重复模式 (测试周期性记忆)
        input_ids = torch.zeros(num_sequences, seq_length, dtype=torch.long)
        for i in range(num_sequences):
            pattern_len = torch.randint(5, 20, (1,)).item()
            pattern = torch.randint(0, vocab_size, (pattern_len,))
            for j in range(seq_length):
                input_ids[i, j] = pattern[j % pattern_len]
        labels = input_ids.clone()
        
    elif pattern_type == "sequence":
        # 递增序列 (测试顺序记忆)
        input_ids = torch.zeros(num_sequences, seq_length, dtype=torch.long)
        for i in range(num_sequences):
            start = torch.randint(0, vocab_size - seq_length, (1,)).item()
            input_ids[i] = torch.arange(start, start + seq_length) % vocab_size
        labels = input_ids.clone()
        
    elif pattern_type == "mixed":
        # 混合模式 (50%随机 + 50%结构化)
        input_ids = torch.zeros(num_sequences, seq_length, dtype=torch.long)
        for i in range(num_sequences):
            if i % 2 == 0:
                # 随机
                input_ids[i] = torch.randint(0, vocab_size, (seq_length,))
            else:
                # 重复模式
                pattern_len = torch.randint(5, 15, (1,)).item()
                pattern = torch.randint(0, vocab_size, (pattern_len,))
                for j in range(seq_length):
                    input_ids[i, j] = pattern[j % pattern_len]
        labels = input_ids.clone()
    
    return input_ids, labels


def generate_copy_task_data(vocab_size: int, num_sequences: int, seq_length: int) -> Tuple[torch.Tensor, torch.Tensor]:
    """生成复制任务数据 (输入 -> 输出相同序列，测试记忆容量)"""
    # 前半部分随机，后半部分复制
    half_len = seq_length // 2
    
    input_ids = torch.zeros(num_sequences, seq_length, dtype=torch.long)
    labels = torch.zeros(num_sequences, seq_length, dtype=torch.long)
    
    for i in range(num_sequences):
        # 前半部分随机
        first_half = torch.randint(0, vocab_size, (half_len,))
        # 后半部分复制前半部分
        second_half = first_half.clone()
        
        input_ids[i, :half_len] = first_half
        input_ids[i, half_len:] = second_half
        labels[i] = input_ids[i]
    
    return input_ids, labels


# =============================================================================
# 评估指标
# =============================================================================

def evaluate_model(model: TNNTransformerWithLossConfig, test_data: torch.Tensor, 
                   test_labels: torch.Tensor, device: str = 'cpu') -> Dict[str, float]:
    """评估模型性能"""
    model.eval()
    
    with torch.no_grad():
        test_data = test_data.to(device)
        test_labels = test_labels.to(device)
        
        outputs = model(test_data, labels=test_labels)
        
        # 基础指标
        loss = outputs['loss'].item()
        perplexity = torch.exp(torch.tensor(loss)).item()
        
        # 扭转场能量
        torsion_energy = outputs['torsion_energy']
        
        # 谱维
        spectral_dim = outputs['spectral_dimension']
        
        # 准确率
        logits = outputs['logits']
        predictions = logits.argmax(dim=-1)
        shift_labels = test_labels[:, 1:]
        shift_preds = predictions[:, :-1]
        accuracy = (shift_preds == shift_labels).float().mean().item()
        
        # 生成质量测试
        prompt = test_data[:1, :10]
        generated = model.generate(prompt, max_length=30, temperature=1.0)
        generated_seq = generated[0].cpu().tolist()
        
        # 计算重复率 (衡量生成多样性)
        unique_tokens = len(set(generated_seq))
        repetition_rate = 1.0 - (unique_tokens / len(generated_seq))
        
    model.train()
    
    return {
        'loss': loss,
        'perplexity': perplexity,
        'accuracy': accuracy,
        'torsion_energy': torsion_energy,
        'spectral_dim': spectral_dim,
        'repetition_rate': repetition_rate,
        'generated_sample': generated_seq[:20],
    }


def measure_memory_capacity(model: TNNTransformerWithLossConfig, vocab_size: int, 
                            device: str = 'cpu') -> Dict[str, float]:
    """测量模型的有效记忆容量"""
    model.eval()
    
    capacities = {}
    
    # 测试1: 简单序列记忆 (递增序列)
    with torch.no_grad():
        seq_lens = [10, 20, 50, 100]
        for seq_len in seq_lens:
            data = torch.arange(seq_len).unsqueeze(0) % vocab_size
            labels = data.clone()
            
            outputs = model(data, labels=labels)
            loss = outputs['loss'].item()
            acc = torch.exp(torch.tensor(-loss)).item()  # 近似准确率
            
            capacities[f'seq_{seq_len}'] = acc
    
    # 测试2: 重复模式记忆
    with torch.no_grad():
        pattern_lens = [5, 10, 20]
        for pattern_len in pattern_lens:
            pattern = torch.randint(0, vocab_size, (pattern_len,))
            data = pattern.repeat(10).unsqueeze(0)[:100]
            labels = data.clone()
            
            outputs = model(data, labels=labels)
            loss = outputs['loss'].item()
            acc = torch.exp(torch.tensor(-loss)).item()
            
            capacities[f'pattern_{pattern_len}'] = acc
    
    model.train()
    
    return capacities


# =============================================================================
# 训练循环
# =============================================================================

def train_with_config(loss_config: LossConfig, vocab_size: int = 1000, 
                      num_steps: int = 2000, device: str = 'cpu') -> Dict:
    """使用指定损失配置训练模型"""
    
    print(f"\n{'='*60}")
    print(f"开始实验: {loss_config.name}")
    print(f"描述: {loss_config.description}")
    print(f"{'='*60}")
    
    # 创建模型
    base_config = TNNTransformerTinyConfig(
        vocab_size=vocab_size,
        max_position_embeddings=256,
        hidden_size=128,
        num_hidden_layers=4,
        num_attention_heads=4,
        intermediate_size=256,
        internal_dim=16,
        torsion_order=2,
        torsion_rank=8,
        hidden_dropout_prob=0.05,
        attention_dropout_prob=0.05,
    )
    
    model = TNNTransformerWithLossConfig(base_config, loss_config)
    model = model.to(device)
    
    n_params = sum(p.numel() for p in model.parameters())
    print(f"模型参数量: {n_params/1e6:.2f}M")
    
    # 优化器
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_steps, eta_min=1e-6)
    
    # 训练记录
    history = {
        'step': [],
        'loss': [],
        'base_loss': [],
        'torsion_loss': [],
        'torsion_energy': [],
        'spectral_dim': [],
        'learning_rate': [],
    }
    
    # 训练
    model.train()
    batch_size = 8
    seq_length = 64
    
    for step in range(num_steps):
        # 生成数据 (混合模式)
        if step % 4 == 0:
            pattern = "random"
        elif step % 4 == 1:
            pattern = "repeat"
        elif step % 4 == 2:
            pattern = "sequence"
        else:
            pattern = "mixed"
        
        input_ids, labels = generate_synthetic_data(vocab_size, batch_size, seq_length, pattern)
        input_ids = input_ids.to(device)
        labels = labels.to(device)
        
        # 前向
        outputs = model(input_ids, labels=labels)
        loss = outputs['loss']
        
        # 反向
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
        
        # 记录
        if step % 50 == 0 or step == num_steps - 1:
            history['step'].append(step)
            history['loss'].append(loss.item())
            history['base_loss'].append(outputs['base_loss'].item() if outputs['base_loss'] is not None else 0)
            history['torsion_loss'].append(outputs['torsion_loss'].item())
            history['torsion_energy'].append(outputs['torsion_energy'])
            history['spectral_dim'].append(outputs['spectral_dimension'])
            history['learning_rate'].append(optimizer.param_groups[0]['lr'])
            
            if step % 200 == 0:
                print(f"Step {step:5d} | Loss: {loss.item():.4f} | "
                      f"Torsion: {outputs['torsion_energy']:.4f} | "
                      f"d_s: {outputs['spectral_dimension']:.2f}")
    
    # 最终评估
    print("\n最终评估...")
    test_data, test_labels = generate_synthetic_data(vocab_size, 16, seq_length, "mixed")
    eval_results = evaluate_model(model, test_data, test_labels, device)
    
    print(f"  损失: {eval_results['loss']:.4f}")
    print(f"  困惑度: {eval_results['perplexity']:.2f}")
    print(f"  准确率: {eval_results['accuracy']:.4f}")
    print(f"  扭转场能量: {eval_results['torsion_energy']:.4f}")
    print(f"  谱维: {eval_results['spectral_dim']:.2f}")
    print(f"  重复率: {eval_results['repetition_rate']:.4f}")
    print(f"  生成样本: {eval_results['generated_sample']}")
    
    # 记忆容量测试
    capacity = measure_memory_capacity(model, vocab_size, device)
    
    return {
        'config': loss_config,
        'history': history,
        'eval': eval_results,
        'capacity': capacity,
        'model': model,
    }


# =============================================================================
# 可视化
# =============================================================================

def plot_comparison(results: List[Dict], save_path: str = "loss_comparison.png"):
    """绘制实验对比图"""
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(results)))
    
    for idx, result in enumerate(results):
        name = result['config'].name
        h = result['history']
        color = colors[idx]
        
        # 1. 损失曲线
        axes[0, 0].plot(h['step'], h['loss'], label=name, color=color, alpha=0.7)
        axes[0, 0].set_xlabel('Step')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].set_title('Training Loss')
        axes[0, 0].legend(fontsize=8)
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 扭转场能量
        axes[0, 1].plot(h['step'], h['torsion_energy'], label=name, color=color, alpha=0.7)
        axes[0, 1].set_xlabel('Step')
        axes[0, 1].set_ylabel('Torsion Energy')
        axes[0, 1].set_title('Torsion Energy Evolution')
        axes[0, 1].legend(fontsize=8)
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 谱维
        axes[0, 2].plot(h['step'], h['spectral_dim'], label=name, color=color, alpha=0.7)
        axes[0, 2].set_xlabel('Step')
        axes[0, 2].set_ylabel('Spectral Dimension')
        axes[0, 2].set_title('Spectral Dimension')
        axes[0, 2].legend(fontsize=8)
        axes[0, 2].grid(True, alpha=0.3)
        
        # 4. 基础损失
        axes[1, 0].plot(h['step'], h['base_loss'], label=name, color=color, alpha=0.7)
        axes[1, 0].set_xlabel('Step')
        axes[1, 0].set_ylabel('Base Loss')
        axes[1, 0].set_title('Base Loss (without regularization)')
        axes[1, 0].legend(fontsize=8)
        axes[1, 0].grid(True, alpha=0.3)
        
        # 5. 正则化损失
        axes[1, 1].plot(h['step'], h['torsion_loss'], label=name, color=color, alpha=0.7)
        axes[1, 1].set_xlabel('Step')
        axes[1, 1].set_ylabel('Torsion Loss')
        axes[1, 1].set_title('Torsion Regularization Loss')
        axes[1, 1].legend(fontsize=8)
        axes[1, 1].grid(True, alpha=0.3)
        
        # 6. 学习率
        axes[1, 2].plot(h['step'], h['learning_rate'], label=name, color=color, alpha=0.7)
        axes[1, 2].set_xlabel('Step')
        axes[1, 2].set_ylabel('Learning Rate')
        axes[1, 2].set_title('Learning Rate Schedule')
        axes[1, 2].legend(fontsize=8)
        axes[1, 2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"\n对比图已保存: {save_path}")
    plt.close()


def plot_final_comparison(results: List[Dict], save_path: str = "final_comparison.png"):
    """绘制最终指标对比"""
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    names = [r['config'].name for r in results]
    x = np.arange(len(names))
    width = 0.6
    
    # 1. 最终损失
    final_losses = [r['eval']['loss'] for r in results]
    axes[0, 0].bar(x, final_losses, width, color='steelblue', alpha=0.7)
    axes[0, 0].set_ylabel('Final Loss')
    axes[0, 0].set_title('Final Loss Comparison')
    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels(names, rotation=45, ha='right')
    axes[0, 0].grid(True, alpha=0.3, axis='y')
    
    # 2. 最终扭转场能量
    final_energies = [r['eval']['torsion_energy'] for r in results]
    axes[0, 1].bar(x, final_energies, width, color='coral', alpha=0.7)
    axes[0, 1].set_ylabel('Final Torsion Energy')
    axes[0, 1].set_title('Final Torsion Energy Comparison')
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(names, rotation=45, ha='right')
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    
    # 3. 准确率
    accuracies = [r['eval']['accuracy'] for r in results]
    axes[1, 0].bar(x, accuracies, width, color='seagreen', alpha=0.7)
    axes[1, 0].set_ylabel('Accuracy')
    axes[1, 0].set_title('Final Accuracy Comparison')
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(names, rotation=45, ha='right')
    axes[1, 0].grid(True, alpha=0.3, axis='y')
    
    # 4. 重复率 (越低越好)
    rep_rates = [r['eval']['repetition_rate'] for r in results]
    axes[1, 1].bar(x, rep_rates, width, color='salmon', alpha=0.7)
    axes[1, 1].set_ylabel('Repetition Rate')
    axes[1, 1].set_title('Generation Repetition Rate (lower is better)')
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(names, rotation=45, ha='right')
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"最终对比图已保存: {save_path}")
    plt.close()


# =============================================================================
# 主函数
# =============================================================================

def run_experiment(output_dir: str = "loss_experiment_results"):
    """运行完整实验"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("="*60)
    print("TNN-Transformer 损失函数调优实验")
    print("="*60)
    print(f"实验时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试配置数: {len(EXPERIMENT_CONFIGS)}")
    print(f"每个配置训练步数: 2000")
    print()
    
    device = 'cpu'
    vocab_size = 1000  # 使用较小词表便于快速测试
    num_steps = 2000
    
    results = []
    
    for config in EXPERIMENT_CONFIGS:
        try:
            result = train_with_config(config, vocab_size, num_steps, device)
            results.append(result)
            
            # 保存单个结果
            result_path = os.path.join(output_dir, f"result_{config.name}.json")
            with open(result_path, 'w') as f:
                json.dump({
                    'config': asdict(config),
                    'eval': result['eval'],
                    'capacity': result['capacity'],
                }, f, indent=2)
                
        except Exception as e:
            print(f"实验 {config.name} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 绘制对比图
    plot_comparison(results, os.path.join(output_dir, "training_comparison.png"))
    plot_final_comparison(results, os.path.join(output_dir, "final_metrics.png"))
    
    # 生成报告
    print("\n" + "="*60)
    print("实验完成 - 结果汇总")
    print("="*60)
    
    # 排序：按准确率
    results_sorted = sorted(results, key=lambda x: x['eval']['accuracy'], reverse=True)
    
    print("\n按准确率排序:")
    print(f"{'排名':<4} {'配置':<20} {'损失':<8} {'准确率':<8} {'能量':<8} {'重复率':<8}")
    print("-"*60)
    for idx, r in enumerate(results_sorted, 1):
        print(f"{idx:<4} {r['config'].name:<20} "
              f"{r['eval']['loss']:.4f}  "
              f"{r['eval']['accuracy']:.4f}   "
              f"{r['eval']['torsion_energy']:.4f}   "
              f"{r['eval']['repetition_rate']:.4f}")
    
    # 找到最佳配置
    best = results_sorted[0]
    print(f"\n最佳配置: {best['config'].name}")
    print(f"  描述: {best['config'].description}")
    print(f"  最终损失: {best['eval']['loss']:.4f}")
    print(f"  最终准确率: {best['eval']['accuracy']:.4f}")
    print(f"  最终扭转场能量: {best['eval']['torsion_energy']:.4f}")
    print(f"  生成重复率: {best['eval']['repetition_rate']:.4f}")
    
    # 保存完整报告
    report_path = os.path.join(output_dir, "experiment_report.md")
    with open(report_path, 'w') as f:
        f.write("# TNN-Transformer 损失函数调优实验报告\n\n")
        f.write(f"**实验时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**模型规模**: 1.39M 参数\n\n")
        f.write(f"**训练步数**: {num_steps}\n\n")
        
        f.write("## 测试配置\n\n")
        for cfg in EXPERIMENT_CONFIGS:
            f.write(f"### {cfg.name}\n")
            f.write(f"- 描述: {cfg.description}\n")
            f.write(f"- 扭转场系数: {cfg.torsion_coef}\n")
            f.write(f"- 最小能量约束: {cfg.torsion_min_energy}\n")
            f.write(f"- 目标能量: {cfg.torsion_target}\n")
            f.write(f"- 谱维正则化: {cfg.spectral_reg}\n")
            f.write(f"- 熵正则化: {cfg.entropy_reg}\n\n")
        
        f.write("## 结果汇总\n\n")
        f.write("| 排名 | 配置 | 损失 | 准确率 | 扭转场能量 | 重复率 |\n")
        f.write("|------|------|------|--------|------------|--------|\n")
        for idx, r in enumerate(results_sorted, 1):
            f.write(f"| {idx} | {r['config'].name} | "
                   f"{r['eval']['loss']:.4f} | "
                   f"{r['eval']['accuracy']:.4f} | "
                   f"{r['eval']['torsion_energy']:.4f} | "
                   f"{r['eval']['repetition_rate']:.4f} |\n")
        
        f.write(f"\n## 最佳配置详情\n\n")
        f.write(f"**配置名称**: {best['config'].name}\n\n")
        f.write(f"**配置描述**: {best['config'].description}\n\n")
        f.write(f"### 最终指标\n\n")
        f.write(f"- 损失: {best['eval']['loss']:.4f}\n")
        f.write(f"- 困惑度: {best['eval']['perplexity']:.2f}\n")
        f.write(f"- 准确率: {best['eval']['accuracy']:.4f}\n")
        f.write(f"- 扭转场能量: {best['eval']['torsion_energy']:.4f}\n")
        f.write(f"- 谱维: {best['eval']['spectral_dim']:.2f}\n")
        f.write(f"- 生成重复率: {best['eval']['repetition_rate']:.4f}\n\n")
        f.write(f"### 生成样本\n\n")
        f.write(f"```\n{best['eval']['generated_sample']}\n```\n\n")
        
        f.write("### 记忆容量测试\n\n")
        for key, val in best['capacity'].items():
            f.write(f"- {key}: {val:.4f}\n")
    
    print(f"\n完整报告已保存: {report_path}")
    print(f"所有结果保存在: {output_dir}/")
    
    return results


if __name__ == "__main__":
    run_experiment()
