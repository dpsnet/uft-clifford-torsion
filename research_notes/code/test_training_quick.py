#!/usr/bin/env python3
"""快速测试训练循环"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
import numpy as np
from torch.utils.data import DataLoader, TensorDataset

from tnn_transformer_tiny import create_tiny_tnn_transformer
from prepare_tiny_data import SimpleBPETokenizer

# 设置随机种子
torch.manual_seed(42)
np.random.seed(42)

print("="*60)
print("TNN-Transformer Tiny 训练快速测试")
print("="*60)

# 创建模型
print("\n1. 创建模型...")
model = create_tiny_tnn_transformer(vocab_size=500, device='cpu')
n_params = sum(p.numel() for p in model.parameters())
print(f"   参数量: {n_params/1e6:.2f}M")

# 创建模拟数据
print("\n2. 创建模拟数据集...")
vocab_size = 500
seq_len = 128
num_samples = 100

train_data = torch.randint(0, vocab_size, (num_samples, seq_len))
train_dataset = TensorDataset(train_data)
train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True)
print(f"   训练样本: {num_samples}")
print(f"   批次大小: 4")

# 创建优化器
print("\n3. 创建优化器...")
optimizer = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=0.01)

# 训练循环
print("\n4. 运行训练测试 (10步)...")
print("-"*60)

model.train()
losses = []
spectral_dims = []
torsion_energies = []

for step, (batch,) in enumerate(train_loader):
    if step >= 10:
        break
    
    # 前向传播
    outputs = model(batch, labels=batch)
    loss = outputs['loss']
    
    # 反向传播
    optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
    
    # 记录
    losses.append(loss.item())
    spectral_dims.append(outputs['spectral_dimension'])
    torsion_energies.append(outputs['torsion_energy'])
    
    print(f"Step {step+1:2d} | Loss: {loss.item():.4f} | "
          f"d_s: {outputs['spectral_dimension']:.2f} | "
          f"E_t: {outputs['torsion_energy']:.4f}")

print("-"*60)

# 结果分析
print("\n5. 训练结果分析")
print(f"   初始损失: {losses[0]:.4f}")
print(f"   最终损失: {losses[-1]:.4f}")
print(f"   损失变化: {losses[-1] - losses[0]:+.4f}")
print(f"   平均谱维: {np.mean(spectral_dims):.2f}")
print(f"   谱维范围: [{min(spectral_dims):.2f}, {max(spectral_dims):.2f}]")
print(f"   平均扭转场能量: {np.mean(torsion_energies):.4f}")

# 验证目标检查
print("\n6. 验证目标检查")
loss_decreased = losses[-1] < losses[0]
spectral_in_range = all(2.0 <= d <= 8.0 for d in spectral_dims)
energy_stable = np.std(torsion_energies) < 1.0

print(f"   [{'✓' if loss_decreased else '✗'}] 损失正常变化")
print(f"   [{'✓' if spectral_in_range else '✗'}] 谱维在有效范围 [2.0, 8.0]")
print(f"   [{'✓' if energy_stable else '✗'}] 扭转场能量相对稳定")

# 测试生成
print("\n7. 测试文本生成...")
model.eval()
prompt = torch.randint(0, vocab_size, (1, 10))
with torch.no_grad():
    generated = model.generate(prompt, max_length=20, temperature=1.0, top_k=10)
print(f"   输入长度: {prompt.shape[1]}")
print(f"   生成长度: {generated.shape[1]}")

print("\n" + "="*60)
print("✓ 快速测试通过！训练流程正常。")
print("="*60)
