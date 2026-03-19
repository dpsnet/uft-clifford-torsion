"""
TNN-Transformer Tiny - 修复版训练
使用 min_energy=5.0 约束防止扭转场能量归零
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import json
import os
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np

# 导入修复后的模型
import sys
sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')

from tnn_transformer_tiny import (
    TNNTransformerTinyLM, 
    TNNTransformerTinyConfig,
    create_tiny_tnn_transformer
)


class TNNTransformerFixed(TNNTransformerTinyLM):
    """修复版：添加最小能量约束"""
    
    def forward(self, input_ids, attention_mask=None, labels=None):
        batch_size, seq_len = input_ids.shape
        device = input_ids.device
        
        position_ids = torch.arange(0, seq_len, dtype=torch.long, device=device).unsqueeze(0)
        
        inputs_embeds = self.wte(input_ids)
        position_embeds = self.wpe(position_ids)
        hidden_states = inputs_embeds + position_embeds
        hidden_states = self.drop(hidden_states)
        
        causal_mask = torch.triu(
            torch.ones((seq_len, seq_len), device=device) * float('-inf'), diagonal=1
        )
        causal_mask = causal_mask.unsqueeze(0).unsqueeze(0)
        
        depth_scale = self.spectral_manager.get_depth_scale()
        
        internal_states = None
        all_torsion_energies = []
        
        for layer in self.layers:
            hidden_states, internal_states = layer(
                hidden_states, internal_states, causal_mask, depth_scale
            )
            all_torsion_energies.append(layer.get_torsion_energy())
        
        hidden_states = self.ln_f(hidden_states)
        logits = self.lm_head(hidden_states)
        
        loss = None
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss_fct = nn.CrossEntropyLoss()
            base_loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
            loss = base_loss
            
            # 扭转场能量计算
            total_torsion_energy = sum(all_torsion_energies)
            avg_torsion_energy = total_torsion_energy / len(all_torsion_energies)
            
            # 关键修复：强正则化 + 最小能量约束
            torsion_coef = 0.001  # 10倍于原始
            min_energy = 5.0      # 最小能量约束
            
            # 基础正则化
            torsion_loss = torsion_coef * total_torsion_energy
            
            # 最小能量约束（如果能量低于5.0，给予惩罚）
            if avg_torsion_energy < min_energy:
                energy_penalty = (min_energy - avg_torsion_energy) ** 2
                torsion_loss = torsion_loss + 0.1 * energy_penalty
            
            loss = loss + torsion_loss
        
        current_d_s = self.spectral_manager.update_spectral_dimension(hidden_states, loss)
        avg_torsion_energy_val = (sum(all_torsion_energies) / len(all_torsion_energies)).item() if labels is not None else 0.0
        
        return {
            'loss': loss,
            'base_loss': base_loss.item() if labels is not None else 0,
            'torsion_loss': torsion_loss.item() if labels is not None else 0,
            'logits': logits,
            'spectral_dimension': current_d_s,
            'torsion_energy': avg_torsion_energy_val,
        }


def create_fixed_model(vocab_size=10000, device='cpu'):
    """创建修复版模型"""
    config = TNNTransformerTinyConfig(
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
    
    model = TNNTransformerFixed(config)
    return model.to(device)


class SimpleDataset(Dataset):
    """简单数据集"""
    def __init__(self, vocab_size, num_samples, seq_length):
        self.vocab_size = vocab_size
        self.num_samples = num_samples
        self.seq_length = seq_length
        
    def __len__(self):
        return self.num_samples
    
    def __getitem__(self, idx):
        # 生成简单序列（重复模式）
        seq = torch.randint(0, self.vocab_size, (self.seq_length,))
        return seq, seq.clone()


def train_fixed_model(num_steps=5000, device='cpu'):
    """训练修复版模型"""
    print("="*60)
    print("TNN-Transformer 修复版训练")
    print("="*60)
    print("关键改进：min_energy=5.0 约束防止扭转场归零")
    print("="*60)
    
    model = create_fixed_model(vocab_size=1000, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=0.01)
    
    # 训练记录
    history = {
        'step': [],
        'loss': [],
        'base_loss': [],
        'torsion_loss': [],
        'torsion_energy': [],
        'spectral_dim': [],
    }
    
    model.train()
    
    print(f"\n开始训练 {num_steps} 步...")
    print("-"*60)
    
    for step in range(num_steps):
        # 生成数据
        input_ids = torch.randint(0, 1000, (8, 32), device=device)
        labels = input_ids.clone()
        
        # 前向
        outputs = model(input_ids, labels=labels)
        loss = outputs['loss']
        
        # 反向
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        
        # 记录
        if step % 200 == 0 or step == num_steps - 1:
            history['step'].append(step)
            history['loss'].append(loss.item())
            history['base_loss'].append(outputs['base_loss'])
            history['torsion_loss'].append(outputs['torsion_loss'])
            history['torsion_energy'].append(outputs['torsion_energy'])
            history['spectral_dim'].append(outputs['spectral_dimension'])
            
            print(f"Step {step:5d} | Loss: {loss.item():.4f} | "
                  f"Base: {outputs['base_loss']:.4f} | "
                  f"Torsion: {outputs['torsion_loss']:.4f} | "
                  f"Energy: {outputs['torsion_energy']:.4f} | "
                  f"d_s: {outputs['spectral_dimension']:.2f}")
    
    # 保存
    output_dir = '/root/.openclaw/workspace/research_notes/code/tnn_fixed_training'
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存模型
    model.save_pretrained(os.path.join(output_dir, 'final_model'))
    
    # 保存历史
    with open(os.path.join(output_dir, 'training_history.json'), 'w') as f:
        json.dump(history, f, indent=2)
    
    # 绘图
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    
    axes[0, 0].plot(history['step'], history['loss'], label='Total Loss')
    axes[0, 0].plot(history['step'], history['base_loss'], label='Base Loss')
    axes[0, 0].set_xlabel('Step')
    axes[0, 0].set_ylabel('Loss')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    axes[0, 1].plot(history['step'], history['torsion_energy'], color='orange')
    axes[0, 1].axhline(y=5.0, color='r', linestyle='--', label='min_energy=5.0')
    axes[0, 1].set_xlabel('Step')
    axes[0, 1].set_ylabel('Torsion Energy')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    axes[1, 0].plot(history['step'], history['torsion_loss'], color='green')
    axes[1, 0].set_xlabel('Step')
    axes[1, 0].set_ylabel('Torsion Loss')
    axes[1, 0].grid(True, alpha=0.3)
    
    axes[1, 1].plot(history['step'], history['spectral_dim'], color='purple')
    axes[1, 1].set_xlabel('Step')
    axes[1, 1].set_ylabel('Spectral Dimension')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'training_curves.png'), dpi=150)
    
    print(f"\n训练完成！")
    print(f"最终扭转场能量: {history['torsion_energy'][-1]:.4f}")
    print(f"最终结果保存至: {output_dir}/")
    
    return model, history


if __name__ == "__main__":
    train_fixed_model(num_steps=5000)
