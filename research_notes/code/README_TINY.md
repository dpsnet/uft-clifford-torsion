# TNN-Transformer Tiny CPU验证测试

## 项目概述

本项目实现了**1M参数规模的TNN-Transformer微型模型**，用于在无GPU环境下验证训练流程和代码正确性。

## 文件结构

```
research_notes/code/
├── tnn_transformer_tiny.py      # 微型模型实现 (~1M参数)
├── train_tiny_cpu.py            # CPU训练脚本
├── train_tiny_cpu.sh            # 训练启动脚本
├── prepare_tiny_data.py         # 数据准备脚本
├── tiny_config.yaml             # 训练配置文件
├── test_training_quick.py       # 快速测试脚本
└── README_TINY.md               # 本文档
```

## 模型架构 (1M参数)

| 组件 | 配置 | 说明 |
|------|------|------|
| 词表大小 | 5,000 | 相比原版50K大幅减少 |
| 位置编码 | 256 | 缩短序列长度 |
| 隐藏维度 | 128 | 原版768→128 |
| 层数 | 4 | 原版12→4 |
| 注意力头数 | 4 | 原版12→4 |
| MLP中间层 | 256 | 原版3072→256 |
| 内部维度 | 16 | 原版256→16 |
| 扭转阶数 | 2 | 原版3→2 |
| 扭转场秩 | 8 | 原版64→8 |

**总参数量: ~1.43M** (接近1M目标)

## TNN核心特性保留

1. **扭转注意力机制 (Torsion Attention)**
   - 保留低秩扭转场结构
   - Q/K投影应用扭转修正
   - 螺旋型谱维扭曲

2. **谱维自适应机制**
   - 序列复杂度估计
   - 动态谱维调整
   - 深度缩放因子

3. **互反-内部耦合**
   - 互反空间↔内部空间流动
   - 门控机制控制信息流

4. **谱维自适应MLP**
   - SwiGLU门控结构
   - 扭转场增强
   - 动态宽度调整

## 数据集

支持两种数据集:

1. **TinyStories** (推荐)
   - 短篇故事数据集
   - 约2GB原始数据
   - 适合小模型训练

2. **WikiText-2** (备选)
   - 百科文本数据
   - 约100MB
   - 更正式的语言风格

## 训练配置 (CPU优化)

```yaml
# 关键CPU训练设置
training:
  max_steps: 10000           # 训练10,000步
  batch_size: 8              # 小批次
  gradient_accumulation: 4   # 梯度累积
  fp16: false                # 关闭FP16 (CPU不支持)
  eval_steps: 100            # 每100步评估
  save_steps: 1000           # 每1000步保存
```

**预计训练时间: 6-8小时**

## 快速开始

### 1. 快速测试 (验证代码正确性)

```bash
cd research_notes/code
python3 test_training_quick.py
```

### 2. 完整训练

```bash
# 使用默认配置 (TinyStories, 100K样本, 10K步)
./train_tiny_cpu.sh

# 自定义配置
./train_tiny_cpu.sh tinystories 100000 10000 5000
```

### 3. 仅准备数据

```bash
python3 prepare_tiny_data.py \
    --dataset tinystories \
    --vocab_size 5000 \
    --max_samples 100000
```

### 4. 仅训练 (跳过数据准备)

```bash
python3 train_tiny_cpu.py \
    --dataset tinystories \
    --max_steps 10000 \
    --batch_size 8 \
    --gradient_accumulation_steps 4 \
    --skip_data_prep
```

## 输出文件

训练完成后生成:

```
outputs/tnn_tiny_1m/
├── training_report.md       # 训练报告
├── training_stats.json      # 训练统计数据
├── config.json              # 训练配置
└── plots/
    ├── loss_curve.png       # 损失曲线
    ├── spectral_dim.png     # 谱维演化
    ├── torsion_energy.png   # 扭转场能量
    └── learning_rate.png    # 学习率

checkpoints/tnn_tiny_1m/
├── checkpoint_step_*.pt     # 训练检查点
├── model_step_*/            # 模型快照
└── final_model/             # 最终模型
    ├── pytorch_model.bin
    └── config.json
```

## 验证目标

训练完成后应验证:

| 目标 | 期望结果 | 检查方式 |
|------|----------|----------|
| 损失下降 | 初始→最终明显降低 | 查看损失曲线 |
| 谱维自适应 | d_s ∈ [2.5, 6.0] | 查看谱维演化图 |
| 扭转场稳定 | 能量波动 < 0.5 | 查看扭转场能量图 |
| 生成可读 | 50%+样本有意义 | 查看生成样本 |

## 模型使用示例

```python
import torch
from tnn_transformer_tiny import create_tiny_tnn_transformer
from prepare_tiny_data import SimpleBPETokenizer

# 加载模型
model = create_tiny_tnn_transformer(vocab_size=5000, device='cpu')

# 加载训练好的权重
# model.load_state_dict(torch.load('checkpoints/tnn_tiny_1m/final_model/pytorch_model.bin'))

# 准备输入
tokenizer = SimpleBPETokenizer.load('./data/tokenizer')
input_ids = torch.tensor([tokenizer.encode("Once upon a time")])

# 生成
generated = model.generate(input_ids, max_length=50)
output_text = tokenizer.decode(generated[0].tolist())
print(output_text)
```

## 与原版对比

| 特性 | Tiny (1M) | 原版 (125M) | 说明 |
|------|-----------|-------------|------|
| 参数量 | 1.43M | ~125M | 1/87 |
| 词表 | 5K | 50K | 1/10 |
| 隐藏维度 | 128 | 768 | 1/6 |
| 层数 | 4 | 12 | 1/3 |
| 序列长度 | 256 | 1024 | 1/4 |
| 训练时间 | ~8h (CPU) | ~7d (4xA100) | CPU验证 |
| 适用场景 | 验证/教学 | 生产部署 | 不同目的 |

## 技术细节

### 内存优化策略

1. **梯度累积**: 有效batch_size = 8 × 4 = 32
2. **关闭FP16**: CPU不支持混合精度
3. **小批次**: batch_size=8减少内存占用
4. **pin_memory=false**: CPU训练不需要

### 学习率调度

- Warmup: 500步线性增长
- 主训练: 余弦退火
- 初始LR: 5e-4
- 最小LR: 5e-5

### 正则化

- Dropout: 0.05 (较小，适合小模型)
- Weight Decay: 0.01
- 梯度裁剪: max_norm=1.0
- 扭转场正则化: λ=0.0001

## 故障排除

### 内存不足

```bash
# 减小批次大小
python3 train_tiny_cpu.py --batch_size 4 --gradient_accumulation_steps 8

# 或使用更小的模型配置
# 修改 tnn_transformer_tiny.py 中的 create_tiny_tnn_transformer()
```

### 训练速度慢

```bash
# 减少评估频率
python3 train_tiny_cpu.py --eval_steps 200

# 使用更少样本
python3 train_tiny_cpu.py --max_samples 50000
```

### 数据下载问题

```bash
# 离线模式 (使用示例数据)
# datasets库会自动使用本地缓存
```

## 后续工作

完成CPU验证后，可以:

1. **扩展词表**: 增加到10K-20K提升表达能力
2. **增大模型**: 尝试5M-10M参数版本
3. **GPU训练**: 迁移到GPU进行更大规模训练
4. **对比实验**: 与标准Transformer对比
5. **消融研究**: 禁用各TNN特性评估贡献

## 参考

- 原版TNN-Transformer: `tnn_transformer.py`
- 原版配置: `tnn_transformer_config.yaml`
- TNN理论文档: `../tnn_theory.md`

## 作者

AI Research Assistant  
日期: 2026-03-18
