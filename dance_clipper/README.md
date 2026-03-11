# 🩰 Dance Clipper - 舞蹈视频智能剪辑系统

将长舞蹈视频按照音乐结构和动作连贯性智能缩编为指定时长的短视频。

## ✨ 核心特性

- **🎵 音乐结构感知**：在乐句边界剪辑，保持音乐完整性
- **💃 舞蹈类型预设**：支持芭蕾、街舞、民族舞、现代舞、拉丁舞、爵士舞
- **🎬 动作连贯性检测**：避免在跳跃/旋转中间切断
- **⚡ GPU 加速**：NVIDIA CUDA 加速视频处理
- **🌐 Web 界面**：拖拽上传，实时预览剪辑点
- **🎛️ 实时预览**：可视化时间轴，预览推荐片段

## 📦 安装

### 系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载并安装: https://ffmpeg.org/download.html
```

### Python 依赖

```bash
cd dance_clipper
pip install -r requirements.txt
```

### GPU 加速（可选）

如需 NVIDIA GPU 加速，请安装 CUDA 驱动和 PyTorch：

```bash
pip install torch
```

## 🚀 快速开始

### 方式一：Web 界面（推荐）

```bash
./start_web.sh
```

然后在浏览器打开 http://localhost:5000

### 方式二：命令行

```bash
# 基本剪辑（30秒）
python dance_clipper.py your_dance.mp4 -o output.mp4

# 指定舞蹈类型
python dance_clipper.py your_dance.mp4 -o output.mp4 -p ballet

# 指定目标时长
python dance_clipper.py your_dance.mp4 -o output.mp4 -t 15

# 使用 GPU 加速
python dance_clipper.py your_dance.mp4 -o output.mp4 --preset hip_hop

# 列出所有预设
python dance_clipper.py --list-presets
```

## 🎭 舞蹈类型预设

| 类型 | BPM范围 | 特点 | 推荐时长 |
|------|---------|------|---------|
| **芭蕾** (ballet) | 60-120 | 重视连贯性，避免跳跃中切断 | 8-16秒 |
| **街舞** (hip_hop) | 80-150 | 节奏强，适合炸点剪辑 | 4-8秒 |
| **民族舞** (folk) | 60-140 | 文化表达，节奏多变 | 6-12秒 |
| **现代舞** (modern) | 40-120 | 情感优先，需长片段 | 10-20秒 |
| **拉丁舞** (latin) | 100-180 | 热情奔放，适合造型 | 5-10秒 |
| **爵士舞** (jazz) | 90-160 | 线条优美，节奏鲜明 | 4-8秒 |

## 📋 使用示例

### Web 界面流程

1. **上传视频** - 拖拽或点击上传舞蹈视频
2. **选择类型** - 从下拉菜单选择舞蹈类型
3. **设置时长** - 滑动选择目标时长（5-180秒）
4. **预览剪辑点** - 查看推荐片段和时间轴
5. **开始剪辑** - 后台处理，显示进度
6. **下载结果** - 完成后下载剪辑视频

### 命令行高级用法

```python
from dance_clipper import DanceClipper, ClipConfig

# 创建自定义配置
config = ClipConfig(
    target_duration=30.0,
    tolerance=2.0,
    min_segment_duration=4.0,
    audio_weight=0.6,  # 重视音乐
    video_weight=0.4,  # 兼顾动作
    preset='ballet'    # 芭蕾预设
)

# 创建剪辑器
clipper = DanceClipper(config)

# 执行剪辑（自动检测 GPU）
report = clipper.clip("input.mp4", "output.mp4", use_gpu=True)

print(f"原时长: {report['original_duration']:.1f}s")
print(f"输出时长: {report['output_duration']:.1f}s")
print(f"压缩比: {report['compression_ratio']}")
```

## 🔬 工作原理

```
输入视频
    │
    ▼
┌───────────────────────────────────────────────────────┐
│  1. 音频分析层 (Librosa)                               │
│     - BPM检测、节拍跟踪、乐句分割                        │
│     - 自动检测舞蹈类型                                  │
└───────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────┐
│  2. 视频分析层 (FFmpeg/OpenCV)                         │
│     - 动作密度检测、场景切换检测                        │
└───────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────┐
│  3. 舞蹈预设层                                         │
│     - 根据舞种调整剪辑策略                              │
│     - 芭蕾：避免跳跃中切断                              │
│     - 街舞：优先保留炸点                                │
└───────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────┐
│  4. 智能剪辑引擎                                       │
│     - 在乐句边界选择最优片段                            │
│     - 支持 GPU 加速 (h264_nvenc)                       │
└───────────────────────────────────────────────────────┘
    │
    ▼
输出短视频
```

## 🎛️ 配置参数

### config.yaml

```yaml
# 目标时长设置
target_duration: 30.0      # 输出视频时长（秒）
tolerance: 2.0             # 允许误差（±2秒）

# 音频权重 vs 视频权重
audio:
  weight: 0.6              # 音乐结构权重

video:
  weight: 0.4              # 动作连贯性权重

# 最小片段时长
min_segment_duration: 4.0  # 每段至少4秒
```

### 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `-t, --target` | 目标时长（秒） | `-t 30` |
| `--tolerance` | 时长容差（秒） | `--tolerance 2` |
| `-p, --preset` | 舞蹈预设 | `-p ballet` |
| `--no-gpu` | 禁用GPU加速 | `--no-gpu` |
| `--list-presets` | 列出所有预设 | `--list-presets` |

## 🐛 故障排除

### 问题1："ffmpeg not found"

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### 问题2："No module named 'librosa'"

```bash
pip install librosa numpy pyyaml flask
```

### 问题3：GPU 加速不可用

```bash
# 检查 NVIDIA 驱动
nvidia-smi

# 安装 PyTorch (CUDA 版本)
pip install torch torchvision torchaudio
```

### 问题4：剪辑后音乐不连贯

- 降低 `tolerance` 值
- 增加 `min_segment_duration`
- 调高 `audio_weight`
- 选择正确的舞蹈预设

## 📊 性能参考

在普通笔记本（Intel i5, 16GB RAM）上的处理速度：

| 视频时长 | 分辨率 | CPU | GPU | 加速比 |
|---------|-------|-----|-----|-------|
| 5分钟 | 1080p | ~30s | ~10s | 3x |
| 15分钟 | 1080p | ~90s | ~30s | 3x |
| 30分钟 | 4K | ~5min | ~1.5min | 3.3x |

## 📁 项目结构

```
dance_clipper/
├── dance_clipper.py      # 核心剪辑引擎
├── audio_analyzer.py     # 音频分析模块
├── video_analyzer.py     # 视频分析模块
├── dance_presets.py      # 舞蹈类型预设
├── gpu_accelerator.py    # GPU 加速模块
├── web_app.py            # Web 服务
├── templates/
│   └── index.html        # Web 界面
├── config.yaml           # 配置文件
├── requirements.txt      # Python依赖
├── README.md             # 本文档
├── start_web.sh          # Web服务启动脚本
├── batch_clip.sh         # 批量处理脚本
├── example.py            # 使用示例
└── test_installation.py  # 安装测试
```

## 🛠️ 开发计划

- [x] 支持 GPU 加速（CUDA）
- [x] 添加 Web 界面
- [x] 支持实时预览
- [x] 添加舞蹈类型预设（芭蕾、街舞、民族舞、现代舞、拉丁舞、爵士舞）
- [ ] 支持更多视频格式
- [ ] 添加批量处理 API
- [ ] 支持云端部署 (Docker)

## 📄 许可

MIT License

---

**有问题或建议？** 欢迎提交 Issue 或 PR。
