"""
TNN-Transformer 损失函数调优实验 - 快速版本
测试关键配置，减少训练步数以快速获得结果
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
import numpy as np
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from tnn_transformer_tiny import TNNTransformerTinyLM, TNNTransformerTinyConfig


@dataclass
class LossConfig:
    name: str
    torsion_coef: float = 0.0001
    torsion_min_energy: float = 0.0
    torsion_target: Optional[float] = None
    entropy_reg: float = 0.0
    description: str = ""


# 只测试4个关键配置
EXPERIMENT_CONFIGS = [
    LossConfig(name="baseline", torsion_coef=0.0001, description="原始配置"),
    LossConfig(name="strong_reg", torsion_coef=0.001, description="10倍强正则化"),
    LossConfig(name="min_energy_5", torsion_coef=0.001, torsion_min_energy=5.0, description="强正则+最小能量5"),
    LossConfig(name="entropy_bonus", torsion_coef=0.001, entropy_reg=0.01, description="强正则+熵奖励"),
]


class TNNModelWithLossConfig(TNNTransformerTinyLM):
    def __init__(self, config, loss_config):
        super().__init__(config)
        self.loss_config = loss_config
        
    def forward(self, input_ids, attention_mask=None, labels=None):
        batch_size, seq_len = input_ids.shape
        device = input_ids.device
        
        position_ids = torch.arange(0, seq_len, dtype=torch.long, device=device).unsqueeze(0)
        inputs_embeds = self.wte(input_ids)
        position_embeds = self.wpe(position_ids)
        hidden_states = inputs_embeds + position_embeds
        hidden_states = self.drop(hidden_states)
        
        causal_mask = torch.triu(torch.ones((seq_len, seq_len), device=device) * float('-inf'), diagonal=1)
        causal_mask = causal_mask.unsqueeze(0).unsqueeze(0)
        depth_scale = self.spectral_manager.get_depth_scale()
        
        internal_states = None
        all_torsion_energies = []
        
        for layer in self.layers:
            hidden_states, internal_states = layer(hidden_states, internal_states, causal_mask, depth_scale)
            all_torsion_energies.append(layer.get_torsion_energy())
        
        hidden_states = self.ln_f(hidden_states)
        logits = self.lm_head(hidden_states)
        
        loss = None
        base_loss = torch.tensor(0.0)
        torsion_loss_val = 0.0
        
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss_fct = nn.CrossEntropyLoss()
            base_loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
            loss = base_loss
            
            total_torsion_energy = sum(all_torsion_energies)
            avg_torsion_energy = total_torsion_energy / len(all_torsion_energies)
            
            lc = self.loss_config
            
            # 扭转场正则化
            if lc.torsion_coef > 0:
                torsion_loss = lc.torsion_coef * total_torsion_energy
                
                if lc.torsion_min_energy > 0:
                    min_energy_penalty = torch.relu(lc.torsion_min_energy - avg_torsion_energy)
                    torsion_loss = torsion_loss + 0.1 * min_energy_penalty ** 2
                
                if lc.torsion_target is not None:
                    target_penalty = (avg_torsion_energy - lc.torsion_target) ** 2
                    torsion_loss = torsion_loss + 0.01 * target_penalty
                
                loss = loss + torsion_loss
                torsion_loss_val = torsion_loss.item()
            
            # 熵正则化
            if lc.entropy_reg > 0:
                probs = F.softmax(logits, dim=-1)
                entropy = -torch.sum(probs * torch.log(probs + 1e-10), dim=-1).mean()
                loss = loss - lc.entropy_reg * entropy
        
        current_d_s = self.spectral_manager.update_spectral_dimension(hidden_states, loss)
        avg_torsion_energy_val = (sum(all_torsion_energies) / len(all_torsion_energies)).item()
        
        return {
            'loss': loss,
            'base_loss': base_loss.item() if labels is not None else 0,
            'torsion_loss': torsion_loss_val,
            'torsion_energy': avg_torsion_energy_val,
            'spectral_dimension': current_d_s,
        }


def generate_data(vocab_size, num_sequences, seq_length):
    return torch.randint(0, vocab_size, (num_sequences, seq_length))


def train_config(loss_config, vocab_size=1000, num_steps=500, device='cpu'):
    print(f"\n{'='*50}")
    print(f"实验: {loss_config.name} - {loss_config.description}")
    print(f"{'='*50}")
    
    base_config = TNNTransformerTinyConfig(
        vocab_size=vocab_size,
        max_position_embeddings=128,
        hidden_size=128,
        num_hidden_layers=4,
        num_attention_heads=4,
        intermediate_size=256,
        internal_dim=16,
        torsion_order=2,
        torsion_rank=8,
    )
    
    model = TNNModelWithLossConfig(base_config, loss_config)
    model = model.to(device)
    
    n_params = sum(p.numel() for p in model.parameters())
    print(f"参数量: {n_params/1e6:.2f}M")
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    
    history = {'step': [], 'loss': [], 'base_loss': [], 'torsion_energy': [], 'spectral_dim': []}
    
    model.train()
    batch_size = 8
    seq_length = 32
    
    for step in range(num_steps):
        input_ids = generate_data(vocab_size, batch_size, seq_length).to(device)
        labels = input_ids.clone()
        
        outputs = model(input_ids, labels=labels)
        loss = outputs['loss']
        
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        
        if step % 100 == 0 or step == num_steps - 1:
            history['step'].append(step)
            history['loss'].append(loss.item())
            history['base_loss'].append(outputs['base_loss'])
            history['torsion_energy'].append(outputs['torsion_energy'])
            history['spectral_dim'].append(outputs['spectral_dimension'])
            
            print(f"Step {step:4d} | Loss: {loss.item():.4f} | "
                  f"Base: {outputs['base_loss']:.4f} | "
                  f"Torsion: {outputs['torsion_energy']:.4f} | "
                  f"d_s: {outputs['spectral_dimension']:.2f}")
    
    return {'config': loss_config, 'history': history}


def main():
    print("="*50)
    print("TNN-Transformer 损失函数调优实验 (快速版)")
    print("="*50)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试配置数: {len(EXPERIMENT_CONFIGS)}")
    print(f"每配置训练: 500步\n")
    
    results = []
    for cfg in EXPERIMENT_CONFIGS:
        try:
            result = train_config(cfg, num_steps=500)
            results.append(result)
        except Exception as e:
            print(f"错误: {e}")
    
    # 汇总
    print("\n" + "="*50)
    print("实验结果汇总")
    print("="*50)
    print(f"{'配置':<15} {'最终损失':<10} {'最终能量':<10} {'最终谱维':<10}")
    print("-"*50)
    
    for r in results:
        name = r['config'].name
        h = r['history']
        print(f"{name:<15} {h['loss'][-1]:<10.4f} {h['torsion_energy'][-1]:<10.4f} {h['spectral_dim'][-1]:<10.2f}")
    
    # 保存结果
    output_dir = "/root/.openclaw/workspace/research_notes/code/loss_experiment_results"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/quick_experiment_results.json", 'w') as f:
        json.dump([{
            'config': asdict(r['config']),
            'final_loss': r['history']['loss'][-1],
            'final_torsion': r['history']['torsion_energy'][-1],
            'final_spectral': r['history']['spectral_dim'][-1],
        } for r in results], f, indent=2)
    
    print(f"\n结果已保存: {output_dir}/quick_experiment_results.json")
    
    # 推荐最佳配置
    best = max(results, key=lambda x: x['history']['torsion_energy'][-1])
    print(f"\n最佳配置 (能量最高): {best['config'].name}")
    print(f"  描述: {best['config'].description}")
    print(f"  最终扭转场能量: {best['history']['torsion_energy'][-1]:.4f}")


if __name__ == "__main__":
    main()
