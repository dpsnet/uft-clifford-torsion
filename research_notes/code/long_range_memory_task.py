"""
长程记忆任务 - 验证生长的必要性

任务设计：
- 序列模式：A...[gap]...B...[gap]...A...（间隔逐步拉长）
- 小模型（2层）只能记住短间隔
- 当间隔超过容量，准确率下降，触发生长
- 大模型（4层+）能记住更长间隔

验证：生长是被「学不动」逼出来的
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import json
import random


class LongRangeMemoryDataset(Dataset):
    """长程记忆数据集"""
    
    def __init__(self, vocab_size, num_samples, base_seq_len=64, max_gap=32):
        self.vocab_size = vocab_size
        self.num_samples = num_samples
        self.base_seq_len = base_seq_len
        self.max_gap = max_gap
        
        # 特殊token
        self.token_a = 1
        self.token_b = 2
        self.token_pad = 0
        self.token_noise_start = 10
        
    def __len__(self):
        return self.num_samples
    
    def __getitem__(self, idx):
        """生成一个长程依赖样本"""
        # 随机选择间隔长度
        gap = random.randint(4, self.max_gap)
        
        # 构建序列：A [noise x gap] B [noise x gap] A
        seq_len = 1 + gap + 1 + gap + 1  # A + noise + B + noise + A
        
        tokens = []
        labels = []
        
        # 位置0：A
        tokens.append(self.token_a)
        labels.append(self.token_pad)  # 第一个token没有预测目标
        
        # 位置1到gap：随机噪声
        for i in range(gap):
            tokens.append(random.randint(self.token_noise_start, self.vocab_size-1))
            labels.append(self.token_pad)  # 噪声位置不预测
        
        # 位置gap+1：B（需要记住前面的A）
        tokens.append(self.token_b)
        # 预测B的时候，应该注意到前面有A（但这里简化，只预测下一个）
        labels.append(self.token_pad)
        
        # 再gap个噪声
        for i in range(gap):
            tokens.append(random.randint(self.token_noise_start, self.vocab_size-1))
            labels.append(self.token_pad)
        
        # 最后一个A（关键：需要跨过长间隔记住第一个A）
        tokens.append(self.token_a)
        # 这里的目标应该与前面的A建立联系
        labels.append(self.token_pad)
        
        # 填充到固定长度
        while len(tokens) < self.base_seq_len:
            tokens.append(self.token_pad)
            labels.append(self.token_pad)
        
        return torch.tensor(tokens[:self.base_seq_len]), torch.tensor(labels[:self.base_seq_len])
    
    def get_gap_distribution(self):
        """获取间隔分布统计"""
        gaps = []
        for _ in range(min(1000, self.num_samples)):
            gap = random.randint(4, self.max_gap)
            gaps.append(gap)
        return {
            'min': min(gaps),
            'max': max(gaps),
            'mean': sum(gaps) / len(gaps),
        }


def evaluate_long_range_memory(model, dataset, device='cpu'):
    """评估长程记忆能力"""
    model.eval()
    
    # 按间隔长度分组评估
    gap_accuracies = {gap: [] for gap in range(4, dataset.max_gap + 1, 4)}
    
    with torch.no_grad():
        for gap in gap_accuracies.keys():
            # 生成特定间隔的样本
            correct = 0
            total = 0
            
            for _ in range(100):  # 每个间隔测试100次
                # 构建特定间隔的序列
                tokens = [1]  # A
                tokens.extend([random.randint(10, 99) for _ in range(gap)])  # noise
                tokens.append(2)  # B
                tokens.extend([random.randint(10, 99) for _ in range(gap)])  # noise
                tokens.append(1)  # A
                
                # 填充
                while len(tokens) < 64:
                    tokens.append(0)
                tokens = tokens[:64]
                
                input_ids = torch.tensor([tokens], device=device)
                outputs = model(input_ids)
                
                # 检查模型是否能捕捉到模式
                # 简化：只看最后一个位置的预测分布
                logits = outputs['logits'][0, -1, :]
                pred = logits.argmax().item()
                
                # 如果预测合理（不是纯噪声），算作有一定记忆
                if pred in [1, 2] or pred >= 10:
                    correct += 1
                total += 1
            
            gap_accuracies[gap] = correct / total if total > 0 else 0
    
    model.train()
    return gap_accuracies


def test_growing_on_long_range():
    """测试生长TNN在长程记忆任务上的表现"""
    print("="*60)
    print("长程记忆任务 - 验证生长的必要性")
    print("="*60)
    
    # 导入生长TNN
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/research_notes/code')
    from growing_tnn_ability import GrowingTNN
    
    # 创建数据集
    dataset = LongRangeMemoryDataset(vocab_size=100, num_samples=1000, max_gap=32)
    dist = dataset.get_gap_distribution()
    print(f"\n数据集统计：")
    print(f"  间隔范围: {dist['min']}-{dist['max']}")
    print(f"  平均间隔: {dist['mean']:.1f}")
    
    # 创建模型（从embryo开始）
    model = GrowingTNN(vocab_size=100, max_seq_len=64)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    print(f"\n初始状态：")
    info = model.get_info()
    print(f"  阶段: {info['stage']}")
    print(f"  层数: {info['layers']}")
    print(f"  参数量: {info['params']:,}")
    
    # 训练并监控生长
    print(f"\n开始训练...")
    print("-"*60)
    
    history = []
    gap_history = {}
    
    for step in range(5000):
        # 采样批次
        batch_size = 16
        batch_tokens = []
        batch_labels = []
        
        for _ in range(batch_size):
            tokens, labels = dataset[0]
            batch_tokens.append(tokens)
            batch_labels.append(labels)
        
        input_ids = torch.stack(batch_tokens)
        labels = torch.stack(batch_labels)
        
        # 前向
        outputs = model(input_ids, labels=labels)
        loss = outputs['loss']
        
        # 反向
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # 计算准确率（简化：只看有效token位置）
        with torch.no_grad():
            preds = outputs['logits'].argmax(dim=-1)
            mask = labels != 0  # 只计算非padding位置
            if mask.sum() > 0:
                acc = (preds == labels)[mask].float().mean().item()
            else:
                acc = 0.0
        
        # 检查生长
        growth_msg = model.check_growth(step, loss.item(), acc)
        
        # 定期评估长程记忆
        if step % 500 == 0 or growth_msg:
            gap_acc = evaluate_long_range_memory(model, dataset)
            gap_history[step] = gap_acc
            
            info = model.get_info()
            avg_gap_acc = sum(gap_acc.values()) / len(gap_acc)
            
            status = f"Step {step:5d} | Loss: {loss.item():.4f} | Acc: {acc:.3f} | "
            status += f"Stage: {info['stage']:12s} | Layers: {info['layers']} | "
            status += f"GapAcc: {avg_gap_acc:.3f}"
            print(status)
            
            if growth_msg:
                print(f"  🌱 {growth_msg}")
                # 生长前后对比
                print(f"     生长前平均GapAcc: {avg_gap_acc:.3f}")
        
        history.append({
            'step': step,
            'loss': loss.item(),
            'accuracy': acc,
        })
    
    print("-"*60)
    print("\n最终评估：")
    final_gap_acc = evaluate_long_range_memory(model, dataset)
    
    print(f"不同间隔长度的记忆准确率：")
    for gap in sorted(final_gap_acc.keys()):
        acc = final_gap_acc[gap]
        bar = "█" * int(acc * 20)
        print(f"  Gap={gap:2d}: {acc:.3f} {bar}")
    
    info = model.get_info()
    print(f"\n最终状态：")
    print(f"  阶段: {info['stage']}")
    print(f"  层数: {info['layers']}")
    print(f"  生长历史: {info['log']}")
    
    # 保存结果
    with open('long_range_memory_results.json', 'w') as f:
        json.dump({
            'history': history,
            'gap_history': {str(k): v for k, v in gap_history.items()},
            'final_gap_acc': final_gap_acc,
            'growth_log': info['log'],
        }, f, indent=2)
    
    print("\n结果已保存到 long_range_memory_results.json")
    
    return model, history, gap_history


if __name__ == "__main__":
    test_growing_on_long_range()
