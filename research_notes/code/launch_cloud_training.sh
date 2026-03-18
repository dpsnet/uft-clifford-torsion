#!/bin/bash
# TNN-Transformer 125M 云端训练启动脚本
# 使用Lambda Labs (推荐，价格最低)

# ========================================
# 配置
# ========================================
INSTANCE_TYPE="gpu_1x_a100"  # 或 gpu_4x_a100
PROJECT_NAME="tnn-transformer-125m"
REGION="us-west-1"

# Lambda Labs API Key (需要替换)
LAMBDA_API_KEY="your_api_key_here"

# ========================================
# 启动实例
# ========================================
echo "启动 Lambda Labs GPU 实例..."
echo "实例类型: $INSTANCE_TYPE"
echo "项目: $PROJECT_NAME"

# 创建启动脚本
cat > /tmp/launch_script.sh << 'EOF'
#!/bin/bash
set -e

# 更新系统
apt-get update && apt-get install -y git wget vim

# 安装Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
bash /tmp/miniconda.sh -b -p /opt/conda
export PATH="/opt/conda/bin:$PATH"

# 创建环境
conda create -n tnn python=3.10 -y
source activate tnn

# 安装PyTorch (CUDA 12.1)
pip install torch==2.2.0 torchvision==0.17.0 torchaudio==2.2.0 --index-url https://download.pytorch.org/whl/cu121

# 安装其他依赖
pip install transformers==4.38.0 datasets==2.16.0 accelerate==0.27.0
pip install wandb tensorboard sentencepiece protobuf
pip install flash-attn --no-build-isolation

# 克隆项目 (假设代码已上传到GitHub)
git clone https://github.com/yourusername/tnn-transformer.git /workspace/tnn-transformer
cd /workspace/tnn-transformer

# 下载数据
python -c "
from datasets import load_dataset
dataset = load_dataset('allenai/c4', 'en', split='train', streaming=True)
print('C4 dataset ready')
"

# 启动训练
echo "开始训练..."
python train.py --config configs/tnn_transformer_125m.yaml

EOF

# 使用 Lambda CLI 启动实例 (需要安装 lambda-cli)
# lambda launch $INSTANCE_TYPE --name $PROJECT_NAME --region $REGION --file /tmp/launch_script.sh

echo ""
echo "============================================"
echo "请完成以下步骤:"
echo "============================================"
echo "1. 注册 Lambda Labs: https://lambdalabs.com/service/gpu-cloud"
echo "2. 获取 API Key"
echo "3. 安装 Lambda CLI: pip install lambda-labs"
echo "4. 运行: lambda launch gpu_4x_a100 --name tnn-transformer-125m"
echo ""
echo "预计成本: $1.10/小时 × 4卡 × 168小时 = ~$740"
echo "============================================"
