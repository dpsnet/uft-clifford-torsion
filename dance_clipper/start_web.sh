#!/bin/bash
# start_web.sh - 启动 Web 界面

echo "🌐 Dance Clipper Web 服务启动脚本"
echo "====================================="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    exit 1
fi

echo "✓ Python 版本: $(python3 --version)"

# 检查依赖
echo ""
echo "📦 检查依赖..."
python3 -c "import flask, librosa, numpy, yaml" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  部分依赖缺失，正在安装..."
    pip install -r requirements.txt
fi

# 检查 FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ 错误: 未安装 FFmpeg"
    echo "   请先安装 FFmpeg: https://ffmpeg.org/download.html"
    exit 1
fi
echo "✓ FFmpeg 已安装"

# 检查 GPU
python3 -c "import torch; print('✓ PyTorch CUDA 可用' if torch.cuda.is_available() else '⚠️  PyTorch CUDA 不可用')" 2>/dev/null

echo ""
echo "🚀 启动 Web 服务..."
echo "====================================="
echo ""
echo "服务启动后，请在浏览器访问:"
echo "  http://localhost:5000"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 启动服务
python3 web_app.py
