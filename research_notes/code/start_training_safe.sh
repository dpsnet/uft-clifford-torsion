#!/bin/bash
# TNN-Transformer训练启动脚本（带CPU控制）

cd /root/.openclaw/workspace/research_notes/code

echo "=== TNN-Transformer训练启动 ==="
echo "时间: $(date)"
echo "配置: 10,000步, CPU≤60%"

# 清理
pkill -f "train_tiny_cpu.py" 2>/dev/null
sleep 2

# 启动训练
LOG_FILE="training_$(date +%Y%m%d_%H%M).log"
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
    >> "$LOG_FILE" 2>&1 &

PID=$!
echo "PID: $PID"
echo $PID > .training_pid

echo "日志: $LOG_FILE"
echo "预计完成: $(date -d '+10 hours' '+%Y-%m-%d %H:%M')"
echo ""
echo "监控命令:"
echo "  tail -f $LOG_FILE"
echo "  ps aux | grep $PID"
