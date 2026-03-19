# TNN损失函数调优实验 - 运行记录

**开始时间**: 2026-03-19 07:45 AM
**任务**: 测试8种不同损失函数配置对1.39M参数TNN-Transformer存储能力的影响
**进程ID**: sharp-trail
**预计完成**: 15-20分钟

## 测试配置

1. baseline - 原始0.0001系数（对照组）
2. strong_reg - 10倍强正则化
3. very_strong_reg - 100倍强正则化
4. min_energy_1 - 最小能量约束1.0
5. min_energy_5 - 最小能量约束5.0
6. target_energy_3 - 目标能量3.0
7. entropy_bonus - 熵奖励鼓励多样性
8. adaptive_reg - 自适应正则化

## 预期结果

- 找到能让扭转场能量稳定的正则化策略
- 评估不同配置对存储容量的影响
- 确定最佳生成质量配置

## 输出文件

- loss_experiment_results/training_comparison.png
- loss_experiment_results/final_metrics.png
- loss_experiment_results/experiment_report.md
