#!/bin/bash
# TNN-Transformer Tiny CPU训练启动脚本
# 1M参数微型模型验证测试

set -e

echo "============================================================"
echo "TNN-Transformer Tiny CPU训练启动"
echo "============================================================"

# 设置工作目录
cd "$(dirname "$0")"

# 检查依赖
echo ""
echo "检查依赖..."
python3 -c "import torch; print(f'PyTorch: {torch.__version__}')" || {
    echo "错误: PyTorch未安装"
    exit 1
}

python3 -c "import yaml; print('PyYAML: OK')" 2>/dev/null || {
    echo "警告: PyYAML未安装，使用默认配置"
}

python3 -c "import matplotlib; print('Matplotlib: OK')" 2>/dev/null || {
    echo "警告: Matplotlib未安装，无法生成图表"
}

# 设置参数
DATASET=${1:-tinystories}
MAX_SAMPLES=${2:-100000}
MAX_STEPS=${3:-10000}
VOCAB_SIZE=${4:-5000}

echo ""
echo "训练配置:"
echo "  数据集: $DATASET"
echo "  最大样本数: $MAX_SAMPLES"
echo "  训练步数: $MAX_STEPS"
echo "  词表大小: $VOCAB_SIZE"

# 数据准备
echo ""
echo "============================================================"
echo "步骤1: 准备数据"
echo "============================================================"

if [ -f "./data/processed/$DATASET/train.pt" ]; then
    echo "数据已存在，跳过准备步骤"
else
    python3 prepare_tiny_data.py \
        --dataset $DATASET \
        --data_dir ./data \
        --vocab_size $VOCAB_SIZE \
        --max_length 256 \
        --max_samples $MAX_SAMPLES
fi

# 开始训练
echo ""
echo "============================================================"
echo "步骤2: 开始训练"
echo "============================================================"
echo "预计训练时间: 6-8小时 (CPU)"
echo "按 Ctrl+C 可随时中断训练"
echo ""

python3 train_tiny_cpu.py \
    --dataset $DATASET \
    --data_dir ./data \
    --vocab_size $VOCAB_SIZE \
    --max_samples $MAX_SAMPLES \
    --max_steps $MAX_STEPS \
    --batch_size 8 \
    --gradient_accumulation_steps 4 \
    --lr 5e-4 \
    --seed 42 \
    --skip_data_prep

echo ""
echo "============================================================"
echo "训练完成!"
echo "============================================================"
echo ""
echo "输出文件:"
echo "  模型检查点: ./checkpoints/tnn_tiny_1m/"
echo "  训练报告: ./outputs/tnn_tiny_1m/training_report.md"
echo "  训练曲线: ./outputs/tnn_tiny_1m/plots/"
echo "  训练统计: ./outputs/tnn_tiny_1m/training_stats.json"
echo ""
echo "查看报告:"
echo "  cat ./outputs/tnn_tiny_1m/training_report.md"
