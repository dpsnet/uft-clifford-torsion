"""
长程记忆任务 Phase A2 (快速版): 生长机制验证
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
from phase_a1_interval_copy import IntervalCopyDataset


class GrowingTNN(nn.Module):
    """可生长的TNN - 简化版"""
    
    def __init__(self, vocab_size=20, hidden_size=64):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, hidden_size)
        self.layers = nn.ModuleList([
            nn.ModuleDict({
                'norm': nn.LayerNorm(hidden_size),
                'attn': nn.Linear(hidden_size, hidden_size),
                'proj': nn.Linear(hidden_size, hidden_size),
            }) for _ in range(2)
        ])
        self.output = nn.Linear(hidden_size, vocab_size)
        
        self.stage = 2
        self.stable_count = 0
        self.threshold = 0.25  # 25%阈值
        self.growth_log = []
    
    def check_growth(self, step, acc):
        if self.stage >= 5:
            return None
        
        if acc >= self.threshold:
            self.stable_count += 1
            if self.stable_count >= 30:  # 30步稳定
                self.layers.append(nn.ModuleDict({
                    'norm': nn.LayerNorm(64),
                    'attn': nn.Linear(64, 64),
                    'proj': nn.Linear(64, 64),
                }))
                self.stage = len(self.layers)
                self.stable_count = 0
                msg = f"Step {step}: {self.stage-1}层 → {self.stage}层 (acc={acc:.3f})"
                self.growth_log.append(msg)
                print(f"  🌱 {msg}")
                return msg
        else:
            self.stable_count = 0
        return None
    
    def forward(self, x, targets=None):
        h = self.embed(x)
        for layer in self.layers:
            residual = h
            h = layer['norm'](h)
            h = layer['attn'](h)
            h = torch.tanh(h)
            h = layer['proj'](h)
            h = residual + h * 0.5
        logits = self.output(h)
        
        loss = None
        if targets is not None:
            mask = targets != -100
            if mask.sum() > 0:
                loss = F.cross_entropy(logits.view(-1, 20)[mask.view(-1)], targets.view(-1)[mask.view(-1)])
        return {'loss': loss, 'logits': logits}


def quick_eval(model, dataset, n=20):
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for i in range(n):
            t, tg, _ = dataset[i]
            out = model(t.unsqueeze(0), tg.unsqueeze(0))
            mask = tg != -100
            if mask.sum() > 0:
                preds = out['logits'][0][mask].argmax(dim=-1)
                correct += (preds == tg[mask]).sum().item()
                total += mask.sum().item()
    model.train()
    return correct / total if total > 0 else 0


def run_quick_a2():
    print("="*50)
    print("Phase A2 (快速版): 生长验证")
    print("="*50)
    
    gap = 8  # 降低难度
    dataset = IntervalCopyDataset(500, 4, gap, 20)
    model = GrowingTNN(20, 64)
    opt = torch.optim.Adam(model.parameters(), lr=0.001)
    
    print(f"任务: gap={gap}, 序列长度={dataset.get_seq_len()}")
    print(f"初始: {model.stage}层, 参数量={sum(p.numel() for p in model.parameters()):,}")
    print(f"生长阈值: {model.threshold}, 稳定步数: 30")
    print("-"*50)
    
    best_acc = 0
    for step in range(2000):
        # 训练
        batch_t, batch_g = [], []
        for _ in range(16):
            i = torch.randint(0, len(dataset), (1,)).item()
            t, g, _ = dataset[i]
            batch_t.append(t)
            batch_g.append(g)
        
        out = model(torch.stack(batch_t), torch.stack(batch_g))
        if out['loss']:
            opt.zero_grad()
            out['loss'].backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        
        # 评估
        if step % 100 == 0:
            acc = quick_eval(model, dataset)
            best_acc = max(best_acc, acc)
            print(f"Step {step:4d} | Loss: {out['loss'].item():.4f} | Acc: {acc:.3f} | Layers: {model.stage} | Stable: {model.stable_count}")
            
            # 检查生长
            model.check_growth(step, acc)
    
    # 最终
    final_acc = quick_eval(model, dataset)
    print("-"*50)
    print(f"\n最终: {model.stage}层, 准确率: {final_acc:.3f}")
    print(f"生长历史: {model.growth_log}")
    
    # 保存
    with open('phase_a2_quick_results.json', 'w') as f:
        json.dump({
            'gap': gap,
            'final_layers': model.stage,
            'final_acc': final_acc,
            'growth_log': model.growth_log,
        }, f)
    
    if model.stage > 2:
        print("\n✅ 生长验证成功！")
    else:
        print("\n❌ 未触发生长")

if __name__ == "__main__":
    run_quick_a2()
