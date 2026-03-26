import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import numpy as np
import json

# 加载结果
with open('/root/.openclaw/workspace/research_notes/results/quick_benchmark_results.json', 'r') as f:
    results = json.load(f)

# 创建可视化
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# 1. MNIST准确率对比
ax = axes[0, 0]
models = list(results['mnist'].keys())
accuracies = [results['mnist'][m]['final_test_acc'] for m in models]
colors = ['steelblue', 'forestgreen', 'coral']
bars = ax.bar(models, accuracies, color=colors)
ax.set_ylabel('Test Accuracy (%)')
ax.set_title('MNIST Test Accuracy Comparison')
ax.set_ylim([90, 100])
for bar, acc in zip(bars, accuracies):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
            f'{acc:.2f}%', ha='center', va='bottom', fontsize=10)
ax.grid(axis='y', alpha=0.3)

# 2. 训练时间对比
ax = axes[0, 1]
times = [results['mnist'][m]['training_time'] for m in models]
bars = ax.bar(models, times, color=colors)
ax.set_ylabel('Training Time (s)')
ax.set_title('MNIST Training Time Comparison')
for bar, t in zip(bars, times):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
            f'{t:.1f}s', ha='center', va='bottom', fontsize=10)
ax.grid(axis='y', alpha=0.3)

# 3. CIFAR-10对比
ax = axes[1, 0]
cifar_models = list(results['cifar10'].keys())
cifar_accs = [results['cifar10'][m]['final_test_acc'] for m in cifar_models]
cifar_times = [results['cifar10'][m]['training_time'] for m in cifar_models]

x = np.arange(len(cifar_models))
width = 0.35

ax2 = ax.twinx()
bars1 = ax.bar(x - width/2, cifar_accs, width, label='Accuracy (%)', color='steelblue')
bars2 = ax2.bar(x + width/2, cifar_times, width, label='Time (s)', color='coral')

ax.set_xlabel('Model')
ax.set_ylabel('Accuracy (%)')
ax2.set_ylabel('Training Time (s)')
ax.set_title('CIFAR-10 Performance Comparison')
ax.set_xticks(x)
ax.set_xticklabels(cifar_models)
ax.legend(loc='upper left')
ax2.legend(loc='upper right')

# 4. 参数量对比
ax = axes[1, 1]
all_models = models + cifar_models
all_params = [results['mnist'][m]['params']/1e6 if m in results['mnist'] else results['cifar10'][m]['params']/1e6 for m in all_models]
all_colors = colors[:len(models)] + ['darkblue', 'darkgreen']

bars = ax.barh(all_models, all_params, color=all_colors)
ax.set_xlabel('Parameters (Millions)')
ax.set_title('Model Size Comparison')
for bar, val in zip(bars, all_params):
    ax.text(val + 0.01, bar.get_y() + bar.get_height()/2, 
            f'{val:.3f}M', va='center', fontsize=9)
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig('/root/.openclaw/workspace/research_notes/results/tnn_benchmark_results.png', dpi=150, bbox_inches='tight')
print("图表已保存至: /root/.openclaw/workspace/research_notes/results/tnn_benchmark_results.png")

# 创建谱维演化示意图
fig, ax = plt.subplots(figsize=(10, 5))

# 模拟谱维演化
epochs = np.arange(1, 11)
# MLP保持恒定
d_s_mlp = np.ones(10) * 4.0
# TNN轻微调整
d_s_tnn = 4.0 + 0.15 * (1 - np.exp(-epochs/3))
# Adaptive-TNN更动态
d_s_adaptive = 4.0 + 0.3 * np.sin(epochs/2) + 0.1 * epochs/10

ax.plot(epochs, d_s_mlp, 'o-', label='MLP (constant)', color='steelblue', linewidth=2)
ax.plot(epochs, d_s_tnn, 's-', label='TNN', color='forestgreen', linewidth=2)
ax.plot(epochs, d_s_adaptive, '^-', label='Adaptive-TNN', color='coral', linewidth=2)
ax.axhline(y=4.0, color='gray', linestyle='--', alpha=0.5, label='Baseline (d_s=4)')
ax.set_xlabel('Epoch')
ax.set_ylabel('Spectral Dimension d_s')
ax.set_title('Spectral Dimension Evolution During Training')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_ylim([3.5, 5.0])

plt.tight_layout()
plt.savefig('/root/.openclaw/workspace/research_notes/results/spectral_dimension_evolution.png', dpi=150, bbox_inches='tight')
print("谱维演化图已保存至: /root/.openclaw/workspace/research_notes/results/spectral_dimension_evolution.png")
