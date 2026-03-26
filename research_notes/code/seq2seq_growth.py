"""
简单有效的生长验证实验
任务：序列复制（seq2seq）
- 输入序列长度逐步增加
- 小模型只能处理短序列
- 准确率下降时触发生长
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import random


class GrowingSeq2Seq(nn.Module):
    """可生长的序列复制模型"""
    
    def __init__(self, vocab_size=20, max_len=64):
        super().__init__()
        self.vocab_size = vocab_size
        self.max_len = max_len
        
        self.stage = "embryo"
        self.age = 0
        self.stable_count = 0
        
        # 嵌入
        self.embed = nn.Embedding(vocab_size, 32)
        
        # 初始2层
        self.layers = nn.ModuleList([self._make_layer() for _ in range(2)])
        
        # 输出
        self.output = nn.Linear(32, vocab_size)
        
        # 生长阈值
        self.growth_threshold = 0.85  # 准确率超过此值才生长
        self.growth_log = []
    
    def _make_layer(self):
        return nn.ModuleDict({
            'norm': nn.LayerNorm(32),
            'attn': nn.Linear(32, 32),
            'proj': nn.Linear(32, 32),
        })
    
    def check_growth(self, step, loss, acc):
        """基于能力达标检查生长"""
        self.age = step
        
        # embryo -> infant: 准确率>85%稳定50步
        if self.stage == "embryo" and step > 200:
            if acc > self.growth_threshold:
                self.stable_count += 1
                if self.stable_count >= 50:
                    self._grow_to_infant(step, acc, loss)
                    return f"🌱 embryo→infant (acc={acc:.3f})"
            else:
                self.stable_count = 0
        
        # infant -> child: 准确率>90%稳定100步
        elif self.stage == "infant" and step > 500:
            if acc > 0.90:
                self.stable_count += 1
                if self.stable_count >= 100:
                    self._grow_to_child(step, acc, loss)
                    return f"🌿 infant→child (acc={acc:.3f})"
            else:
                self.stable_count = 0
        
        return None
    
    def _grow_to_infant(self, step, acc, loss):
        self.stage = "infant"
        self.layers.append(self._make_layer())
        self.stable_count = 0
        self.growth_log.append(f"Step {step}: embryo→infant | acc={acc:.3f}")
    
    def _grow_to_child(self, step, acc, loss):
        self.stage = "child"
        self.layers.append(self._make_layer())
        self.stable_count = 0
        self.growth_log.append(f"Step {step}: infant→child | acc={acc:.3f}")
    
    def forward(self, src, tgt=None):
        # src: [batch, seq_len]
        h = self.embed(src)  # [batch, seq, 32]
        
        for layer in self.layers:
            residual = h
            h = layer['norm'](h)
            h = layer['attn'](h)
            h = torch.tanh(h)
            h = layer['proj'](h)
            h = residual + h * 0.5
        
        logits = self.output(h)  # [batch, seq, vocab]
        
        loss = None
        if tgt is not None:
            loss = F.cross_entropy(logits.view(-1, self.vocab_size), tgt.view(-1))
        
        return {'loss': loss, 'logits': logits, 'stage': self.stage}
    
    def get_info(self):
        return {
            'stage': self.stage,
            'layers': len(self.layers),
            'params': sum(p.numel() for p in self.parameters()),
            'stable': self.stable_count,
        }


def generate_copy_task(batch_size, seq_len, vocab_size):
    """生成序列复制任务"""
    # 随机序列
    src = torch.randint(1, vocab_size, (batch_size, seq_len))
    tgt = src.clone()  # 复制任务
    return src, tgt


def run_experiment():
    print("="*60)
    print("序列复制任务 - 验证能力驱动生长")
    print("="*60)
    print("\n实验设计：")
    print("  任务：复制随机序列")
    print("  生长条件：准确率>85%持续50步 → 添加第3层")
    print("           准确率>90%持续100步 → 添加第4层")
    print("="*60)
    
    model = GrowingSeq2Seq(vocab_size=20)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    info = model.get_info()
    print(f"\n初始状态：")
    print(f"  阶段: {info['stage']}")
    print(f"  层数: {info['layers']}")
    print(f"  参数量: {info['params']:,}")
    
    # 训练配置
    seq_lengths = [4, 8, 16]  # 逐步增加难度
    current_seq_idx = 0
    
    print(f"\n开始训练...")
    print("-"*60)
    
    history = []
    
    for step in range(3000):
        # 动态调整序列长度（每500步增加难度）
        if step > 0 and step % 500 == 0 and current_seq_idx < len(seq_lengths) - 1:
            current_seq_idx += 1
            print(f"  📈 Step {step}: 序列长度增加到 {seq_lengths[current_seq_idx]}")
        
        seq_len = seq_lengths[current_seq_idx]
        
        # 生成数据
        src, tgt = generate_copy_task(16, seq_len, 20)
        
        # 前向
        out = model(src, tgt)
        loss = out['loss']
        
        # 反向
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # 计算准确率
        with torch.no_grad():
            preds = out['logits'].argmax(dim=-1)
            acc = (preds == tgt).float().mean().item()
        
        # 检查生长
        growth_msg = model.check_growth(step, loss.item(), acc)
        
        # 显示
        if step % 200 == 0 or growth_msg:
            info = model.get_info()
            status = f"Step {step:5d} | Loss: {loss.item():.4f} | Acc: {acc:.3f} | "
            status += f"Stage: {info['stage']:8s} | Layers: {info['layers']} | SeqLen: {seq_len}"
            print(status)
            if growth_msg:
                print(f"  {growth_msg}")
        
        history.append({'step': step, 'loss': loss.item(), 'acc': acc, 'stage': out['stage']})
    
    print("-"*60)
    info = model.get_info()
    print(f"\n最终状态：")
    print(f"  阶段: {info['stage']}")
    print(f"  层数: {info['layers']}")
    print(f"  参数量: {info['params']:,}")
    print(f"\n生长历史：")
    for entry in model.growth_log:
        print(f"  {entry}")
    
    # 保存
    with open('seq2seq_growth_results.json', 'w') as f:
        json.dump(history, f, indent=2)
    print("\n结果已保存到 seq2seq_growth_results.json")
    
    return model, history


if __name__ == "__main__":
    run_experiment()
