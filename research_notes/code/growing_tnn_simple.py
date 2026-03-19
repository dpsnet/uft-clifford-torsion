"""
发育式TNN - 简化稳定版
展示从embryo到child的渐进生长
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json


class GrowingTNN(nn.Module):
    """可生长的TNN模型"""
    
    def __init__(self, vocab_size=50, max_seq_len=32):
        super().__init__()
        self.vocab_size = vocab_size
        self.max_seq_len = max_seq_len
        
        # 嵌入
        self.embedding = nn.Embedding(vocab_size, 64)
        self.pos_embed = nn.Embedding(max_seq_len, 64)
        
        # 初始架构（embryo阶段）
        self.stage = "embryo"
        self.age = 0
        
        # 2层基础
        self.layers = nn.ModuleList([
            self._make_layer() for _ in range(2)
        ])
        
        # 谱维
        self.spectral_dim = 2.5
        self.spectral_max = 2.5  # 随年龄解锁
        
        # 输出
        self.output = nn.Linear(64, vocab_size)
        
        self.growth_log = []
    
    def _make_layer(self):
        return nn.ModuleDict({
            'attn': nn.Linear(64, 64),
            'torsion_a': nn.Linear(64, 16, bias=False),
            'torsion_b': nn.Linear(16, 64, bias=False),
            'norm': nn.LayerNorm(64),
        })
    
    def check_growth(self, step, metrics):
        """检查是否需要生长"""
        self.age = step
        
        # 解锁谱维
        if step < 1000:
            self.spectral_max = 2.5
        elif step < 3000:
            self.spectral_max = 3.5
        elif step < 6000:
            self.spectral_max = 4.5
        else:
            self.spectral_max = 5.5
        
        # 阶段转换
        if self.stage == "embryo" and step >= 1000:
            self._grow_to_infant()
            return "🌱 生长到 infant 阶段"
        
        if self.stage == "infant" and step >= 3000:
            self._grow_to_child()
            return "🌿 生长到 child 阶段"
        
        return None
    
    def _grow_to_infant(self):
        """添加第3层"""
        self.stage = "infant"
        self.layers.append(self._make_layer())
        self.growth_log.append(f"Step {self.age}: 添加第3层")
    
    def _grow_to_child(self):
        """添加第4层"""
        self.stage = "child"
        self.layers.append(self._make_layer())
        self.growth_log.append(f"Step {self.age}: 添加第4层")
    
    def forward(self, x, labels=None):
        batch, seq = x.shape
        device = x.device
        
        # 嵌入
        pos = torch.arange(seq, device=device).unsqueeze(0)
        h = self.embedding(x) + self.pos_embed(pos)
        
        # 层处理
        for layer in self.layers:
            residual = h
            h = layer['norm'](h)
            
            # 注意力
            attn = layer['attn'](h)
            
            # 扭转场
            low = layer['torsion_a'](h)
            twist = layer['torsion_b'](low)
            twist = torch.sin(twist) * 0.1
            
            h = residual + attn + twist
        
        logits = self.output(h)
        
        loss = None
        if labels is not None:
            loss = F.cross_entropy(logits.view(-1, self.vocab_size), labels.view(-1))
        
        return {
            'loss': loss,
            'logits': logits,
            'stage': self.stage,
            'spectral': min(self.spectral_dim, self.spectral_max),
        }
    
    def get_info(self):
        return {
            'stage': self.stage,
            'age': self.age,
            'layers': len(self.layers),
            'params': sum(p.numel() for p in self.parameters()),
            'spectral_max': self.spectral_max,
            'log': self.growth_log,
        }


def run_experiment():
    print("="*60)
    print("发育式TNN实验 - 简化版")
    print("="*60)
    
    model = GrowingTNN()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    info = model.get_info()
    print(f"\n初始状态:")
    print(f"  阶段: {info['stage']}")
    print(f"  层数: {info['layers']}")
    print(f"  参数量: {info['params']:,}")
    
    print(f"\n开始训练...")
    print("-"*60)
    
    history = []
    
    for step in range(5000):
        # 简单数据
        batch_size, seq_len = 8, 16
        x = torch.randint(0, 50, (batch_size, seq_len))
        labels = x.clone()
        
        # 前向
        out = model(x, labels)
        loss = out['loss']
        
        # 反向
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # 检查生长
        with torch.no_grad():
            preds = out['logits'].argmax(dim=-1)
            acc = (preds == labels).float().mean().item()
        
        growth_msg = model.check_growth(step, {'acc': acc})
        
        # 记录
        if step % 500 == 0 or growth_msg:
            info = model.get_info()
            print(f"Step {step:5d} | Loss: {loss.item():.4f} | Acc: {acc:.3f} | "
                  f"Stage: {info['stage']:8s} | Layers: {info['layers']} | "
                  f"Spectral: {info['spectral_max']:.1f}")
            if growth_msg:
                print(f"  {growth_msg}")
            history.append({
                'step': step,
                'loss': loss.item(),
                'acc': acc,
                'stage': info['stage'],
                'layers': info['layers'],
                'spectral': info['spectral_max'],
            })
    
    print("-"*60)
    info = model.get_info()
    print(f"\n最终状态:")
    print(f"  阶段: {info['stage']}")
    print(f"  年龄: {info['age']}")
    print(f"  层数: {info['layers']}")
    print(f"  参数量: {info['params']:,}")
    print(f"  生长历史:")
    for entry in info['log']:
        print(f"    {entry}")
    
    # 保存
    with open('growing_tnn_results.json', 'w') as f:
        json.dump(history, f, indent=2)
    print("\n结果已保存到 growing_tnn_results.json")
    
    return model, history


if __name__ == "__main__":
    run_experiment()
