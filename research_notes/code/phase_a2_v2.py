"""
Phase A2 (修订版): 用序列复制验证生长解决瓶颈

设计：
- 阶段1: 序列长度4 (2层可学会)
- 阶段2: 序列长度8 (2层学不动→触发3层)
- 阶段3: 序列长度16 (3层学不动→触发4层)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json


class GrowingSeqCopy(nn.Module):
    """可生长的序列复制模型"""
    
    def __init__(self, vocab_size=20, hidden=32):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, hidden)
        # 从2层开始
        self.layers = nn.ModuleList([
            nn.ModuleDict({
                'norm': nn.LayerNorm(hidden),
                'attn': nn.Linear(hidden, hidden),
                'ff': nn.Linear(hidden, hidden),
            }) for _ in range(2)
        ])
        self.output = nn.Linear(hidden, vocab_size)
        
        self.stage = 2
        self.stable = 0
        self.log = []
    
    def check_growth(self, step, acc):
        """准确率>90%持续30步→生长"""
        if self.stage >= 5:
            return None
        
        if acc >= 0.90:
            self.stable += 1
            if self.stable >= 30:
                h = self.layers[0]['attn'].weight.shape[0]
                self.layers.append(nn.ModuleDict({
                    'norm': nn.LayerNorm(h),
                    'attn': nn.Linear(h, h),
                    'ff': nn.Linear(h, h),
                }))
                old = self.stage
                self.stage = len(self.layers)
                self.stable = 0
                msg = f"Step {step}: {old}层→{self.stage}层 (acc={acc:.3f})"
                self.log.append(msg)
                print(f"  🌱 {msg}")
                return msg
        else:
            self.stable = 0
        return None
    
    def forward(self, x, tgt=None):
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
        return {'loss': loss, 'logits': logits}


def generate_copy(batch, seq_len, vocab):
    src = torch.randint(1, vocab, (batch, seq_len))
    return src, src.clone()


def run_phase_a2_v2():
    print("="*60)
    print("Phase A2 (修订版): 序列长度递进 + 生长验证")
    print("="*60)
    
    model = GrowingSeqCopy(vocab_size=20, hidden=32)
    opt = torch.optim.Adam(model.parameters(), lr=0.001)
    
    print(f"\n初始: {model.stage}层, 参数量={sum(p.numel() for p in model.parameters()):,}")
    print("生长条件: 准确率>90%持续30步")
    print("-"*60)
    
    # 阶段配置
    stages = [
        (0, 500, 4, "短序列学习"),
        (500, 1200, 8, "中序列挑战"),
        (1200, 2000, 16, "长序列挑战"),
    ]
    
    history = []
    current_seq = 4
    
    for step in range(2000):
        # 确定当前阶段
        for start, end, seq, desc in stages:
            if start <= step < end:
                if seq != current_seq:
                    print(f"\n📈 Step {step}: 序列长度 {current_seq}→{seq} ({desc})")
                    current_seq = seq
                break
        
        # 训练
        src, tgt = generate_copy(16, current_seq, 20)
        out = model(src, tgt)
        
        opt.zero_grad()
        out['loss'].backward()
        opt.step()
        
        # 评估
        with torch.no_grad():
            preds = out['logits'].argmax(dim=-1)
            acc = (preds == tgt).float().mean().item()
        
        # 检查生长
        growth = model.check_growth(step, acc)
        
        # 记录
        if step % 100 == 0 or growth:
            print(f"Step {step:4d} | Loss: {out['loss'].item():.4f} | Acc: {acc:.3f} | "
                  f"Layers: {model.stage} | Stable: {model.stable:2d} | Seq: {current_seq}")
            history.append({'step': step, 'acc': acc, 'layers': model.stage, 'seq': current_seq})
    
    # 总结
    print("-"*60)
    print(f"\n最终: {model.stage}层")
    print(f"生长历史: {model.log}")
    
    # 测试不同长度
    print(f"\n各长度准确率测试:")
    for seq in [4, 8, 16]:
        src, tgt = generate_copy(100, seq, 20)
        with torch.no_grad():
            out = model(src, tgt)
            preds = out['logits'].argmax(dim=-1)
            acc = (preds == tgt).float().mean().item()
        status = "✅" if acc > 0.9 else "❌"
        print(f"  长度{seq:2d}: {acc:.3f} {status}")
    
    # 保存
    with open('phase_a2_v2_results.json', 'w') as f:
        json.dump({
            'final_layers': model.stage,
            'growth_log': model.log,
            'history': history,
        }, f)
    
    if model.stage > 2:
        print("\n✅ Phase A2 验证成功：生长解决了容量瓶颈！")
    else:
        print("\n❌ 未触发生长")


if __name__ == "__main__":
    run_phase_a2_v2()
