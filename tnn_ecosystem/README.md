# TNN Ecosystem - 扭转神经网络生态系统仿真

基于TNN（Torsion Neural Networks）的多智能体生态系统仿真框架。

## 🎯 核心特性

- **具身智能验证**：反射虫（Reflex Worm）展示零训练下的先天行为
- **群体智能涌现**：50+智能体在虚拟环境中展现类生物群体行为
- **TNN架构**：扭转位置编码、扭转注意力机制
- **完全开源**：研究目的，代码透明

## 📁 项目结构

```
tnn_ecosystem/
├── core/                    # 核心TNN模型
│   ├── reflex_worm.py       # 反射虫（1,363参数，具身智能）
│   └── super_tnn_worm.py    # 超级TNN蠕虫（140万参数）
│
├── environments/            # 环境仿真
│   └── ecosystem_env.py     # 复杂生态系统（1000×1000世界）
│
├── visualizations/          # 可视化工具
│   └── visualize_ecosystem.py
│
├── analysis/                # 涌现行为分析
├── experiments/             # 实验结果保存
└── docs/                    # 文档
    ├── tnn_reflex_worm_experiment.md      # 反射虫实验报告
    └── tnn_super_ecosystem_experiment.md  # 超级生态系统报告
```

## 🐛 反射虫实验（具身智能）

**配置**：
- 仅1,363个参数（微型TNN）
- 2D虚拟环境，8个光感应器

**先天行为**（零训练）：
1. 趋光性（phototaxis）
2. 避光性（negative phototaxis）
3. 壁虎行为（thigmotaxis）
4. 探索行为（exploration）
5. 平衡行为（homeostasis）

**关键发现**：
- 调整扭转场空间编码参数可直接"编程"行为模式
- 验证了"结构即行为"假说

## 🌍 超级生态系统（群体智能）

**配置**：
- 50个TNN智能体
- 1000×1000连续世界
- 动态资源、昼夜循环、信息素系统

**检测到的涌现行为**：
1. 群体聚集
2. 信息素路径
3. 行为同步（置信度77.2%）
4. 领域行为
5. 社会凝聚

**关键发现**：
- 当智能体>20时，出现类生物群体协调
- 与真实鱼群、鸟群的间距分布统计相似

## 🚀 快速开始

### 运行反射虫实验
```bash
cd tnn_ecosystem
python -c "from core.reflex_worm import *; demo_worm()"
```

### 运行超级生态系统
```bash
python core/super_tnn_worm.py
```

### 可视化结果
```bash
python visualizations/visualize_ecosystem.py --experiment experiments/experiment_*
```

## 📊 实验结果

- **反射虫**：完整报告见 `docs/tnn_reflex_worm_experiment.md`
- **超级生态系统**：完整报告见 `docs/tnn_super_ecosystem_experiment.md`

## 🔬 科学意义

这些实验验证了两个核心假说：

1. **结构即行为**：智能可以是结构涌现的，不一定是学出来的
2. **群体涌现**：个体基于局部信息的TNN决策，可在群体层面产生全局秩序

## 📝 引用

如果你使用本项目，请引用：

```
TNN Ecosystem: Emergent Intelligence through Torsion Neural Networks
Part of UFT-Clifford-Torsion Research Project
```

## 📄 开源协议

MIT License - 详见项目根目录 LICENSE 文件

## 🔗 相关项目

- **TNN-OS**：预测式操作系统内核框架
- **UFT-Clifford-Torsion**：统一场论完整研究

---

*本项目属于理论研究，代码开源用于学术交流和协作开发。*
