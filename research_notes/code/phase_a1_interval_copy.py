"""
长程记忆任务 Phase A1: 基础验证
目标：验证2层模型无法处理长间隔

任务：间隔复制 (Interval Copy Task)
- 输入: START [noise×gap] PATTERN [noise×gap] END
- 输出: 复制 PATTERN
- 关键: 必须记住跨越 gap 的 PATTERN
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import json
import matplotlib.pyplot as plt


class IntervalCopyDataset(Dataset):
    """间隔复制数据集"""
    
    def __init__(self, num_samples=1000, pattern_len=4, gap=8, vocab_size=20):
        self.num_samples = num_samples
        self.pattern_len = pattern_len
        self.gap = gap
        self.vocab_size = vocab_size
        
        # 特殊token
        self.START = 1
        self.END = 2
        self.NOISE_START = 10  # 噪声token从10开始
        
    def __len__(self):
        return self.num_samples
    
    def __getitem__(self, idx):
        """生成一个样本"""
        # 生成随机 PATTERN (长度为pattern_len)
        pattern = torch.randint(self.NOISE_START, self.vocab_size, (self.pattern_len,))
        
        # 构建输入序列
        tokens = []
        targets = []
        
        # START token
        tokens.append(self.START)
        targets.append(-100)  # 忽略
        
        # gap 个噪声
        for _ in range(self.gap):
            tokens.append(torch.randint(self.NOISE_START, self.vocab_size, (1,)).item())
            targets.append(-100)  # 忽略
        
        # PATTERN (需要记住的部分)
        for p in pattern:
            tokens.append(p.item())
            targets.append(-100)  # 忽略
        
        # gap 个噪声
        for _ in range(self.gap):
            tokens.append(torch.randint(self.NOISE_START, self.vocab_size, (1,)).item())
            targets.append(-100)  # 忽略
        
        # END token
        tokens.append(self.END)
        targets.append(-100)  # 忽略
        
        # 然后重复 PATTERN (输出目标)
        for p in pattern:
            tokens.append(self.START)  # 占位
            targets.append(p.item())
        
        return torch.tensor(tokens), torch.tensor(targets), pattern
    
    def get_seq_len(self):
        """获取序列长度"""
        return 2 + 2 * self.gap + self.pattern_len + self.pattern_len


class StaticTNN2Layer(nn.Module):
    """静态2层TNN基线"""
    
    def __init__(self, vocab_size=20, hidden_size=64):
        super().__init__()
        self.vocab_size = vocab_size
        self.hidden_size = hidden_size
        
        self.embed = nn.Embedding(vocab_size, hidden_size)
        
        # 2层TNN
        self.layer1 = nn.ModuleDict({
            'norm': nn.LayerNorm(hidden_size),
            'attn': nn.Linear(hidden_size, hidden_size),
            'proj': nn.Linear(hidden_size, hidden_size),
        })
        
        self.layer2 = nn.ModuleDict({
            'norm': nn.LayerNorm(hidden_size),
            'attn': nn.Linear(hidden_size, hidden_size),
            'proj': nn.Linear(hidden_size, hidden_size),
        })
        
        self.output = nn.Linear(hidden_size, vocab_size)
    
    def forward(self, x, targets=None):
        # x: [batch, seq_len]
        h = self.embed(x)  # [batch, seq, hidden]
        
        # Layer 1
        residual = h
        h = self.layer1['norm'](h)
        h = self.layer1['attn'](h)
        h = torch.tanh(h)
        h = self.layer1['proj'](h)
        h = residual + h * 0.5
        
        # Layer 2
        residual = h
        h = self.layer2['norm'](h)
        h = self.layer2['attn'](h)
        h = torch.tanh(h)
        h = self.layer2['proj'](h)
        h = residual + h * 0.5
        
        logits = self.output(h)  # [batch, seq, vocab]
        
        loss = None
        if targets is not None:
            # 只计算目标位置的loss
            mask = targets != -100
            if mask.sum() > 0:
                loss = F.cross_entropy(
                    logits.view(-1, self.vocab_size)[mask.view(-1)],
                    targets.view(-1)[mask.view(-1)]
                )
        
        return {'loss': loss, 'logits': logits}


def evaluate_model(model, dataset, device='cpu'):
    """评估模型在间隔复制任务上的准确率"""
    model.eval()
    correct = 0
    total = 0
    
    with torch.no_grad():
        for i in range(min(100, len(dataset))):
            tokens, targets, pattern = dataset[i]
            tokens = tokens.unsqueeze(0).to(device)
            targets = targets.unsqueeze(0).to(device)
            
            outputs = model(tokens, targets)
            logits = outputs['logits']
            
            # 找到目标位置
            mask = targets[0] != -100
            if mask.sum() > 0:
                target_logits = logits[0][mask]
                preds = target_logits.argmax(dim=-1)
                true_targets = targets[0][mask]
                
                correct += (preds == true_targets).sum().item()
                total += len(true_targets)
    
    model.train()
    return correct / total if total > 0 else 0.0


def run_phase_a1():
    """Phase A1: 基础验证"""
    print("="*60)
    print("Phase A1: 长程记忆任务 - 基础验证")
    print("="*60)
    print("\n目标：验证2层模型无法处理长间隔")
    print("任务：间隔复制 (记住跨越噪声的pattern)")
    print("-"*60)
    
    # 测试不同间隔长度
    gaps = [4, 8, 16, 32, 64]
    results = []
    
    for gap in gaps:
        print(f"\n测试间隔长度: {gap}")
        print("-" * 40)
        
        # 创建数据集
        dataset = IntervalCopyDataset(
            num_samples=500,
            pattern_len=4,
            gap=gap,
            vocab_size=20
        )
        
        # 创建2层模型
        model = StaticTNN2Layer(vocab_size=20, hidden_size=64)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        
        print(f"  序列长度: {dataset.get_seq_len()}")
        print(f"  参数量: {sum(p.numel() for p in model.parameters()):,}")
        
        # 训练
        best_acc = 0.0
        history = []
        
        for step in range(1000):
            # 采样批次
            batch_tokens = []
            batch_targets = []
            
            for _ in range(16):
                tokens, targets, _ = dataset[torch.randint(0, len(dataset), (1,)).item()]
                batch_tokens.append(tokens)
                batch_targets.append(targets)
            
            tokens = torch.stack(batch_tokens)
            targets = torch.stack(batch_targets)
            
            # 前向
            outputs = model(tokens, targets)
            loss = outputs['loss']
            
            # 反向
            if loss is not None:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            
            # 定期评估
            if step % 200 == 0:
                acc = evaluate_model(model, dataset)
                best_acc = max(best_acc, acc)
                history.append({'step': step, 'acc': acc, 'loss': loss.item() if loss else 0})
                print(f"    Step {step:4d} | Loss: {loss.item():.4f} | Acc: {acc:.3f}")
        
        # 最终评估
        final_acc = evaluate_model(model, dataset)
        print(f"  最终准确率: {final_acc:.3f}")
        
        results.append({
            'gap': gap,
            'seq_len': dataset.get_seq_len(),
            'final_acc': final_acc,
            'best_acc': best_acc,
            'history': history,
        })
    
    # 汇总结果
    print("\n" + "="*60)
    print("Phase A1 结果汇总")
    print("="*60)
    print(f"{'间隔长度':<10} {'序列长度':<10} {'最终准确率':<12} {'状态':<10}")
    print("-"*60)
    
    for r in results:
        status = "✅ 学会" if r['final_acc'] > 0.8 else "❌ 失败"
        print(f"{r['gap']:<10} {r['seq_len']:<10} {r['final_acc']:<12.3f} {status:<10}")
    
    # 保存结果
    with open('phase_a1_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # 绘图
    fig, ax = plt.subplots(figsize=(10, 6))
    gaps_plot = [r['gap'] for r in results]
    accs_plot = [r['final_acc'] for r in results]
    
    ax.plot(gaps_plot, accs_plot, 'o-', linewidth=2, markersize=8)
    ax.axhline(y=0.8, color='r', linestyle='--', label='阈值 (80%)')
    ax.set_xlabel('间隔长度 (Gap)', fontsize=12)
    ax.set_ylabel('准确率', fontsize=12)
    ax.set_title('2层TNN: 间隔长度 vs 准确率', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig('phase_a1_results.png', dpi=150)
    print(f"\n结果图已保存: phase_a1_results.png")
    print("数据已保存: phase_a1_results.json")
    
    # 关键发现
    failed_gaps = [r['gap'] for r in results if r['final_acc'] <= 0.8]
    if failed_gaps:
        print(f"\n🔍 关键发现:")
        print(f"  2层模型在间隔 >= {min(failed_gaps)} 时失效")
        print(f"  这为后续'生长解决瓶颈'提供了验证基础")
    
    return results


if __name__ == "__main__":
    run_phase_a1()
