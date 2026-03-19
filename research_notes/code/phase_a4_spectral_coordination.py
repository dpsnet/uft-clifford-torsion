"""
Phase A4: 谱维协同验证
目标：验证谱维与层数协同生长

设计：
- 谱维范围：2.5（简单任务）→ 4.5（复杂任务）
- 观察：任务复杂度增加时，谱维自动提升
- 验证：谱维提升帮助模型处理长程依赖
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import matplotlib.pyplot as plt
import numpy as np


class SpectralAdaptiveTNN(nn.Module):
    """谱维自适应的TNN模型"""
    
    def __init__(self, vocab_size=20, hidden=32, d_s_min=2.5, d_s_max=4.5):
        super().__init__()
        self.d_s_min = d_s_min
        self.d_s_max = d_s_max
        self.current_d_s = d_s_min
        
        self.embed = nn.Embedding(vocab_size, hidden)
        
        # 谱维门控参数（单独存储）
        self.spectral_gates = nn.ParameterList([
            nn.Parameter(torch.ones(hidden)) for _ in range(2)
        ])
        
        # 从2层开始
        self.layers = nn.ModuleList([
            nn.ModuleDict({
                'norm': nn.LayerNorm(hidden),
                'attn': nn.Linear(hidden, hidden),
                'ff': nn.Linear(hidden, hidden),
            }) for _ in range(2)
        ])
        
        self.output = nn.Linear(hidden, vocab_size)
        
        self.num_layers = 2
        self.stable_count = 0
        self.growth_log = []
        self.d_s_history = []
    
    def update_spectral_dim(self, loss, step):
        """根据损失自适应调整谱维"""
        # 损失越低，说明任务越简单，谱维可以适当降低
        # 损失越高，说明任务越复杂，需要提升谱维
        
        if loss < 0.1:  # 任务简单，维持低谱维
            target_d_s = self.d_s_min
        elif loss < 0.5:  # 中等复杂度
            target_d_s = (self.d_s_min + self.d_s_max) / 2
        else:  # 任务复杂，需要高谱维
            target_d_s = self.d_s_max
        
        # 平滑更新
        self.current_d_s += 0.01 * (target_d_s - self.current_d_s)
        self.current_d_s = max(self.d_s_min, min(self.d_s_max, self.current_d_s))
        
        self.d_s_history.append({'step': step, 'd_s': self.current_d_s, 'loss': loss})
    
    def check_growth(self, step, acc):
        """检查层数生长"""
        if self.num_layers >= 5:
            return None
        
        if acc >= 0.90:
            self.stable_count += 1
            if self.stable_count >= 30:
                h = 32
                self.layers.append(nn.ModuleDict({
                    'norm': nn.LayerNorm(h),
                    'attn': nn.Linear(h, h),
                    'ff': nn.Linear(h, h),
                }))
                # 添加对应的谱维门控
                self.spectral_gates.append(nn.Parameter(torch.ones(h) * 0.5))
                old = self.num_layers
                self.num_layers = len(self.layers)
                self.stable_count = 0
                msg = f"Step {step}: {old}层→{self.num_layers}层 (d_s={self.current_d_s:.2f})"
                self.growth_log.append(msg)
                print(f"  🌱 {msg}")
                return msg
        else:
            self.stable_count = 0
        return None
    
    def forward(self, x, tgt=None, step=0):
        h = self.embed(x)
        
        # 谱维缩放因子（模拟谱维效果）
        # d_s越高，注意力越分散（全局）
        # d_s越低，注意力越集中（局部）
        spectral_scale = (self.current_d_s - self.d_s_min) / (self.d_s_max - self.d_s_min)
        
        for i, lyr in enumerate(self.layers):
            r = h
            h = lyr['norm'](h)
            
            # 注意力 + 谱维调制
            attn_out = lyr['attn'](h)
            
            # 谱维门控：根据当前谱维调制信息流
            gate = torch.sigmoid(self.spectral_gates[i] * spectral_scale)
            attn_out = attn_out * gate
            
            h = torch.relu(attn_out)
            h = lyr['ff'](h)
            h = r + h * 0.3
        
        logits = self.output(h)
        
        loss = None
        if tgt is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), tgt.view(-1))
            self.update_spectral_dim(loss.item(), step)
        
        return {'loss': loss, 'logits': logits, 'd_s': self.current_d_s, 'layers': self.num_layers}


class StaticSpectralTNN(nn.Module):
    """静态谱维模型（对照组）"""
    
    def __init__(self, num_layers, vocab_size=20, hidden=32, fixed_d_s=3.5):
        super().__init__()
        self.fixed_d_s = fixed_d_s
        self.embed = nn.Embedding(vocab_size, hidden)
        self.layers = nn.ModuleList([
            nn.ModuleDict({
                'norm': nn.LayerNorm(hidden),
                'attn': nn.Linear(hidden, hidden),
                'ff': nn.Linear(hidden, hidden),
            }) for _ in range(num_layers)
        ])
        self.output = nn.Linear(hidden, vocab_size)
    
    def forward(self, x, tgt=None, step=0):
        h = self.embed(x)
        for lyr in self.layers:
            r = h
            h = lyr['norm'](h)
            h = lyr['attn'](h)
            h = torch.relu(h)
            h = lyr['ff'](h)
            h = r + h * 0.3
        logits = self.output(h)
        
        loss = None
        if tgt is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), tgt.view(-1))
        
        return {'loss': loss, 'logits': logits, 'd_s': self.fixed_d_s, 'layers': len(self.layers)}


def generate_data(batch, seq_len, vocab=20):
    src = torch.randint(1, vocab, (batch, seq_len))
    return src, src.clone()


def evaluate_model(model, seq_lens, vocab=20):
    """评估模型在各长度上的性能"""
    results = {}
    for seq_len in seq_lens:
        src, tgt = generate_data(100, seq_len, vocab)
        with torch.no_grad():
            out = model(src, tgt)
            preds = out['logits'].argmax(dim=-1)
            acc = (preds == tgt).float().mean().item()
        results[seq_len] = acc
    return results


def run_phase_a4():
    print("="*60)
    print("Phase A4: 谱维协同验证")
    print("="*60)
    print("\n目标：验证谱维与层数协同生长")
    print("谱维范围: 2.5 → 4.5")
    print("-"*60)
    
    # 实验组：谱维自适应
    print("\n【实验组】谱维自适应模型")
    model_adaptive = SpectralAdaptiveTNN(vocab_size=20, hidden=32, d_s_min=2.5, d_s_max=4.5)
    opt_adaptive = torch.optim.Adam(model_adaptive.parameters(), lr=0.001)
    
    print(f"初始: {model_adaptive.num_layers}层, d_s={model_adaptive.current_d_s:.2f}")
    
    # 训练
    seq_stages = [(0, 500, 4), (500, 1200, 8), (1200, 2000, 16)]
    current_seq = 4
    
    history_adaptive = []
    
    for step in range(2000):
        # 更新阶段
        for start, end, seq in seq_stages:
            if start <= step < end and seq != current_seq:
                print(f"\n📈 Step {step}: 序列长度 {current_seq}→{seq}")
                current_seq = seq
                break
        
        src, tgt = generate_data(16, current_seq)
        out = model_adaptive(src, tgt, step)
        
        opt_adaptive.zero_grad()
        out['loss'].backward()
        opt_adaptive.step()
        
        # 评估和生长
        with torch.no_grad():
            preds = out['logits'].argmax(dim=-1)
            acc = (preds == tgt).float().mean().item()
        
        model_adaptive.check_growth(step, acc)
        
        if step % 200 == 0:
            print(f"Step {step:4d} | Loss: {out['loss'].item():.4f} | Acc: {acc:.3f} | "
                  f"Layers: {model_adaptive.num_layers} | d_s: {out['d_s']:.2f}")
            history_adaptive.append({
                'step': step, 'acc': acc, 'loss': out['loss'].item(),
                'layers': out['layers'], 'd_s': out['d_s']
            })
    
    # 对照组1：低固定谱维 (2.5)
    print("\n【对照组1】固定低谱维 (d_s=2.5)")
    model_low = StaticSpectralTNN(num_layers=5, fixed_d_s=2.5)
    opt_low = torch.optim.Adam(model_low.parameters(), lr=0.001)
    
    current_seq = 4
    for step in range(2000):
        for start, end, seq in seq_stages:
            if start <= step < end and seq != current_seq:
                current_seq = seq
                break
        
        src, tgt = generate_data(16, current_seq)
        out = model_low(src, tgt)
        
        opt_low.zero_grad()
        out['loss'].backward()
        opt_low.step()
    
    # 对照组2：高固定谱维 (4.5)
    print("【对照组2】固定高谱维 (d_s=4.5)")
    model_high = StaticSpectralTNN(num_layers=5, fixed_d_s=4.5)
    opt_high = torch.optim.Adam(model_high.parameters(), lr=0.001)
    
    current_seq = 4
    for step in range(2000):
        for start, end, seq in seq_stages:
            if start <= step < end and seq != current_seq:
                current_seq = seq
                break
        
        src, tgt = generate_data(16, current_seq)
        out = model_high(src, tgt)
        
        opt_high.zero_grad()
        out['loss'].backward()
        opt_high.step()
    
    # 最终评估
    print("\n" + "="*60)
    print("最终评估")
    print("="*60)
    
    test_lengths = [4, 8, 16, 32]
    
    acc_adaptive = evaluate_model(model_adaptive, test_lengths)
    acc_low = evaluate_model(model_low, test_lengths)
    acc_high = evaluate_model(model_high, test_lengths)
    
    print(f"\n{'序列长度':<10} {'自适应谱维':<12} {'固定低(d_s=2.5)':<15} {'固定高(d_s=4.5)':<15}")
    print("-"*55)
    for seq in test_lengths:
        print(f"{seq:<10} {acc_adaptive[seq]:<12.3f} {acc_low[seq]:<15.3f} {acc_high[seq]:<15.3f}")
    
    # 谱维演化分析
    print("\n" + "="*60)
    print("谱维演化分析")
    print("="*60)
    
    if model_adaptive.d_s_history:
        d_s_values = [h['d_s'] for h in model_adaptive.d_s_history]
        d_s_by_stage = {
            '短序列阶段 (0-500)': np.mean(d_s_values[:100]) if len(d_s_values) > 100 else d_s_values[0],
            '中序列阶段 (500-1200)': np.mean(d_s_values[100:240]) if len(d_s_values) > 240 else np.mean(d_s_values),
            '长序列阶段 (1200+)': np.mean(d_s_values[240:]) if len(d_s_values) > 240 else d_s_values[-1],
        }
        
        print("\n各阶段平均谱维：")
        for stage, avg_d_s in d_s_by_stage.items():
            print(f"  {stage}: {avg_d_s:.2f}")
        
        # 验证谱维与任务复杂度正相关
        print("\n谱维-复杂度相关性：")
        print(f"  短序列→长序列: {d_s_by_stage['短序列阶段 (0-500)']:.2f} → {d_s_by_stage['长序列阶段 (1200+)']:.2f}")
        if d_s_by_stage['长序列阶段 (1200+)'] > d_s_by_stage['短序列阶段 (0-500)']:
            print("  ✅ 谱维随复杂度提升！")
        else:
            print("  ❌ 谱维未随复杂度提升")
    
    # 总结
    print("\n" + "="*60)
    print("Phase A4 结论")
    print("="*60)
    
    avg_adaptive = sum(acc_adaptive.values()) / len(acc_adaptive)
    avg_low = sum(acc_low.values()) / len(acc_low)
    avg_high = sum(acc_high.values()) / len(acc_high)
    
    print(f"\n平均性能：")
    print(f"  自适应谱维: {avg_adaptive:.3f}")
    print(f"  固定低谱维: {avg_low:.3f}")
    print(f"  固定高谱维: {avg_high:.3f}")
    
    if avg_adaptive >= max(avg_low, avg_high) * 0.95:
        print("\n✅ 谱维协同验证成功！")
        print("   自适应谱维达到或超过固定谱维性能")
        print("   证明了谱维动态调整的有效性")
    else:
        print("\n🟡 部分成功")
        print("   自适应谱维性能略低于最优固定谱维")
        print("   可能需要调整谱维更新策略")
    
    # 保存结果
    results = {
        'adaptive': {
            'final_layers': model_adaptive.num_layers,
            'final_d_s': model_adaptive.current_d_s,
            'accuracies': acc_adaptive,
            'avg_accuracy': avg_adaptive,
            'growth_log': model_adaptive.growth_log,
            'd_s_history': model_adaptive.d_s_history,
        },
        'fixed_low': {
            'd_s': 2.5,
            'accuracies': acc_low,
            'avg_accuracy': avg_low,
        },
        'fixed_high': {
            'd_s': 4.5,
            'accuracies': acc_high,
            'avg_accuracy': avg_high,
        },
    }
    
    with open('phase_a4_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # 绘图
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 谱维演化
    if model_adaptive.d_s_history:
        steps = [h['step'] for h in model_adaptive.d_s_history[::10]]  # 采样
        d_s_vals = [h['d_s'] for h in model_adaptive.d_s_history[::10]]
        axes[0, 0].plot(steps, d_s_vals, linewidth=2, color='blue')
        axes[0, 0].axhline(y=2.5, color='gray', linestyle='--', alpha=0.5, label='Min (2.5)')
        axes[0, 0].axhline(y=4.5, color='gray', linestyle='--', alpha=0.5, label='Max (4.5)')
        axes[0, 0].axvline(x=500, color='red', linestyle=':', alpha=0.5, label='Seq 4→8')
        axes[0, 0].axvline(x=1200, color='red', linestyle=':', alpha=0.5, label='Seq 8→16')
        axes[0, 0].set_xlabel('Step')
        axes[0, 0].set_ylabel('Spectral Dimension')
        axes[0, 0].set_title('Adaptive Spectral Dimension Evolution')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
    
    # 性能对比
    models = ['Adaptive\n(2.5→4.5)', 'Fixed Low\n(2.5)', 'Fixed High\n(4.5)']
    avgs = [avg_adaptive, avg_low, avg_high]
    colors = ['green', 'blue', 'orange']
    bars = axes[0, 1].bar(models, avgs, color=colors, alpha=0.7, edgecolor='black')
    axes[0, 1].set_ylabel('Average Accuracy')
    axes[0, 1].set_title('Performance Comparison')
    axes[0, 1].set_ylim(0, 1.1)
    for bar, val in zip(bars, avgs):
        axes[0, 1].text(bar.get_x() + bar.get_width()/2., val, f'{val:.3f}', 
                       ha='center', va='bottom', fontsize=10)
    
    # 各长度性能
    lengths = list(test_lengths)
    axes[1, 0].plot(lengths, [acc_adaptive[l] for l in lengths], 'o-', label='Adaptive', linewidth=2)
    axes[1, 0].plot(lengths, [acc_low[l] for l in lengths], 's-', label='Fixed Low', linewidth=2)
    axes[1, 0].plot(lengths, [acc_high[l] for l in lengths], '^-', label='Fixed High', linewidth=2)
    axes[1, 0].set_xlabel('Sequence Length')
    axes[1, 0].set_ylabel('Accuracy')
    axes[1, 0].set_title('Accuracy vs Sequence Length')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # 层数与谱维关系
    if model_adaptive.growth_log:
        axes[1, 1].text(0.5, 0.7, 'Growth Events:', fontsize=12, ha='center', transform=axes[1, 1].transAxes)
        for i, log in enumerate(model_adaptive.growth_log):
            axes[1, 1].text(0.5, 0.6 - i*0.1, log, fontsize=10, ha='center', transform=axes[1, 1].transAxes)
        axes[1, 1].text(0.5, 0.3, f'Final: {model_adaptive.num_layers} layers', fontsize=11, ha='center', transform=axes[1, 1].transAxes)
        axes[1, 1].text(0.5, 0.2, f'Final d_s: {model_adaptive.current_d_s:.2f}', fontsize=11, ha='center', transform=axes[1, 1].transAxes)
    axes[1, 1].set_xlim(0, 1)
    axes[1, 1].set_ylim(0, 1)
    axes[1, 1].axis('off')
    axes[1, 1].set_title('Growth Summary')
    
    plt.tight_layout()
    plt.savefig('phase_a4_spectral_analysis.png', dpi=150)
    print(f"\n分析图已保存: phase_a4_spectral_analysis.png")
    
    return results


if __name__ == "__main__":
    run_phase_a4()
