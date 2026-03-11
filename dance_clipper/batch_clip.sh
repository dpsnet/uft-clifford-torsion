#!/bin/bash
# batch_clip.sh - 批量处理舞蹈视频

# 使用说明
if [ $# -lt 1 ]; then
    echo "用法: ./batch_clip.sh <输入目录> [目标时长] [输出目录]"
    echo "示例: ./batch_clip.sh ./raw_videos 30 ./clips"
    exit 1
fi

INPUT_DIR="$1"
TARGET_DURATION="${2:-30}"
OUTPUT_DIR="${3:-./output_clips}"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 处理计数
COUNT=0
SUCCESS=0
FAILED=0

echo "🎬 开始批量处理舞蹈视频"
echo "输入目录: $INPUT_DIR"
echo "目标时长: ${TARGET_DURATION}s"
echo "输出目录: $OUTPUT_DIR"
echo "================================"

# 遍历所有视频文件
for video in "$INPUT_DIR"/*.{mp4,mov,avi,mkv}; do
    # 跳过不存在的文件（当没有匹配时）
    [ -e "$video" ] || continue
    
    filename=$(basename "$video")
    name="${filename%.*}"
    output="$OUTPUT_DIR/${name}_clip.mp4"
    
    echo ""
    echo "[$((++COUNT))] 处理: $filename"
    
    if python dance_clipper.py "$video" -o "$output" -t "$TARGET_DURATION"; then
        echo "✓ 成功: $output"
        ((SUCCESS++))
    else
        echo "✗ 失败: $filename"
        ((FAILED++))
    fi
done

echo ""
echo "================================"
echo "📊 处理完成"
echo "总计: $COUNT"
echo "成功: $SUCCESS"
echo "失败: $FAILED"
