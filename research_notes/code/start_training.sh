#!/bin/bash
# TNN-Transformer训练启动脚本
# 使用方式: ./start_training.sh

cd /root/.openclaw/workspace/research_notes/code

echo "=== 启动TNN-Transformer训练 ==="
echo "时间: $(date)"

# 清理旧进程
pkill -f "train_tiny_cpu.py" 2>/dev/null
sleep 2

# 启动训练
nohup python3 train_tiny_cpu.py \
    --dataset tinystories \
    --data_dir ./data \
    --vocab_size 5000 \
    --max_samples 100000 \
    --max_steps 10000 \
    --batch_size 8 \
    --gradient_accumulation_steps 4 \
    --lr 5e-4 \
    --seed 42 \
    --skip_data_prep \
    > training_live.log 2>&1 &

PID=$!
echo "训练PID: $PID"
echo $PID > training.pid

echo "日志文件: training_live.log"
echo "预计完成: $(date -d '+8 hours' '+%Y-%m-%d %H:%M')"
echo ""
echo "监控命令:"
echo "  tail -f training_live.log"
echo "  ps aux | grep $PID"
