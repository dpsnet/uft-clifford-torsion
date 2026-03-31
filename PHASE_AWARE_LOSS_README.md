# Phase-Aware Loss Module - CUDA/C++ Implementation

CUDA/C++移植实现，源自Python的TNN-Transformer损失函数调优实验。

## 源文件

- **Python源码**: `research_notes/code/tnn_loss_experiment.py`
- **移植目标**: 高性能CUDA/C++实现，用于生产环境训练

## 文件结构

```
uft-clifford-torsion/
├── include/core/
│   └── phase_aware_loss.h      # 头文件 (340行)
├── src/core/
│   └── phase_aware_loss.cpp    # C++实现 (425行)
├── kernels/
│   └── phase_loss_kernels.cu   # CUDA核函数 (442行)
├── tests/
│   └── test_phase_aware_loss.cpp    # 单元测试 (273行)
├── benchmarks/
│   └── benchmark_phase_loss.cpp     # 性能基准 (295行)
└── CMakeLists.txt              # 构建配置 (220行)
```

**总代码行数**: 1,995行 (C++/CUDA)

## 功能模块

### 1. 扭转场能量正则化 (Torsion Field Energy Regularization)

对应Python中的扭转场正则化系统：

```cpp
// 基础正则化
loss = torsion_coef * total_energy

// 最小能量约束 (防止能量过低)
penalty = 0.1 * relu(min_energy - avg_energy)^2

// 目标能量约束 (鼓励接近目标值)
penalty = 0.01 * (avg_energy - target_energy)^2
```

### 2. 自适应正则化 (Adaptive Regularization)

根据能量动态调整正则化系数：

```cpp
if (avg_energy < 1.0) {
    coef = 0.01 * (1.0 - avg_energy);  // 能量过低，增加正则化
} else if (avg_energy > 10.0) {
    coef = 0.001;                       // 能量较高，适度正则化
} else {
    coef = 0.0001;                      // 能量在最佳范围，轻正则化
}
```

### 3. 谱维约束损失 (Spectral Dimension Constraint)

鼓励谱维保持在合理范围 [3.0, 6.0]：

```cpp
penalty = relu(3.0 - d_s) + relu(d_s - 6.0)
loss = spectral_reg * penalty
```

### 4. 熵正则化 (Entropy Regularization)

鼓励输出分布的多样性：

```cpp
entropy = -sum(p * log(p))
loss = -entropy_reg * entropy  // 负号表示最大化熵
```

### 5. 相位一致性损失 (Phase Consistency Loss)

鼓励跨层相位一致性：

```cpp
mean_phase = mean(phases across layers)
variance = mean((phase - mean_phase)^2)
loss = consistency_coef * variance
```

### 6. 容量最大化损失 (Capacity Maximization Loss)

通过有效秩近似最大化模型记忆容量：

```cpp
// 基于隐层状态方差评估容量
capacity_ratio = count(variance > threshold) / hidden_dim
loss = (target_capacity - capacity_ratio)^2
```

## 配置结构

```cpp
struct PhaseLossConfig {
    std::string name = "baseline";
    float torsion_coef = 0.0001f;        // 扭转场系数
    float torsion_min_energy = 0.0f;     // 最小能量约束
    float torsion_target = -1.0f;        // 目标能量 (负值=无目标)
    float spectral_reg = 0.0f;           // 谱维正则化
    float entropy_reg = 0.0f;            // 熵正则化
    std::string description = "";
};
```

## 使用示例

```cpp
#include <core/phase_aware_loss.h>
#include <torch/torch.h>

// 创建配置
uft::PhaseLossConfig config;
config.name = "strong_reg";
config.torsion_coef = 0.001f;
config.torsion_min_energy = 1.0f;
config.spectral_reg = 0.01f;
config.entropy_reg = 0.01f;

// 初始化损失模块
uft::PhaseAwareLoss loss_module(config, num_layers=12, device=0);

// 在训练循环中使用
torch::Tensor total_loss = loss_module.compute_loss(
    base_loss,           // 基础交叉熵损失
    torsion_energies,    // 每层扭转场能量
    logits,              // 模型输出
    current_spectral_dim,// 当前谱维
    step                 // 训练步数
);

// 获取统计信息
uft::LossStatistics stats = loss_module.get_statistics();
std::cout << "Torsion energy: " << stats.torsion_energy << std::endl;
std::cout << "Spectral dim: " << stats.spectral_dimension << std::endl;
```

## 构建

```bash
# 创建构建目录
mkdir build && cd build

# 配置
cmake .. -DCMAKE_BUILD_TYPE=Release

# 编译
make -j$(nproc)

# 运行测试
./bin/test_phase_aware_loss

# 运行基准
./bin/benchmark_phase_loss
```

## 与PyTorch集成

模块使用LibTorch API，可直接与PyTorch训练循环集成：

```python
import torch
# 加载C++扩展
phase_loss = torch.utils.cpp_extension.load(
    name="phase_aware_loss",
    sources=[
        "src/core/phase_aware_loss.cpp",
        "kernels/phase_loss_kernels.cu",
    ],
    extra_cflags=["-O3"],
    extra_cuda_cflags=["-O3", "--use_fast_math"],
)
```

## 性能优化

- **CUDA核函数**: 使用warp级归约优化
- **异步执行**: 支持CUDA流重叠
- **内存复用**: 预分配缓冲区避免动态分配
- **混合精度**: 支持FP16/FP32 (可通过模板扩展)

## 移植对比

| 特性 | Python实现 | CUDA/C++实现 |
|------|-----------|-------------|
| 执行速度 | CPU/GPU通用 | GPU加速 10-100x |
| 内存效率 | PyTorch自动管理 | 显式缓冲区管理 |
| 可定制性 | 高 | 高 |
| 部署便利 | 需要Python环境 | 独立库/嵌入C++ |

## 参考配置

基于Python实验的最佳配置：

```cpp
// 基准配置 (baseline)
config.torsion_coef = 0.0001f;

// 强正则化 (strong_reg)
config.torsion_coef = 0.001f;

// 强正则化 + 最小能量约束
config.torsion_coef = 0.001f;
config.torsion_min_energy = 5.0f;

// 自适应正则化
config.torsion_coef = -1.0f;  // 特殊标记

// 熵奖励配置
config.torsion_coef = 0.001f;
config.entropy_reg = 0.01f;
```

## 许可

与原项目保持一致
