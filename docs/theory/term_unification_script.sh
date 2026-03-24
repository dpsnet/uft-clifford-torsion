#!/bin/bash
# 论文术语统一替换脚本
# 执行全文术语标准化

echo "========================================="
echo "  论文术语统一替换脚本"
echo "========================================="
echo ""

# 创建术语映射表
cat > /tmp/term_mapping.txt << 'EOF'
# 旧术语 -> 新术语
基于分形测度理论 -> 基于分形-扭转双重表象
分形Clifford代数框架 -> 分形-扭转双重表象框架
分形时空理论 -> 分形-扭转时空理论
Ahlfors指数Q -> 有效维度d_eff=4-τ²
d_s = Q -> d_s = 4-τ² (分形表象) 或 d_s^τ = 4-c₁τ²+... (扭转表象)
EOF

echo "[步骤1/3] 术语映射表创建完成"
cat /tmp/term_mapping.txt
echo ""

# 检查需要修改的文件
echo "[步骤2/3] 检查目标文件..."
FILES=(
    "/root/.openclaw/workspace/research_notes/paper_full_integration.md"
    "/root/.openclaw/workspace/research_notes/paper_chapter_experimental.md"
    "/root/.openclaw/workspace/research_notes/paper_abstract_conclusion.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ 找到: $(basename $file)"
    else
        echo "  ✗ 缺失: $(basename $file)"
    fi
done
echo ""

# 生成修改建议
echo "[步骤3/3] 生成修改建议..."
echo ""
echo "需要执行的替换操作:"
echo "----------------------------------------"
echo "1. 统一'分形-扭转双重表象'术语"
echo "2. 添加分形/扭转视角标注"
echo "3. 统一公式符号 (d_s vs d_s^τ)"
echo "4. 添加对偶变换Φ引用"
echo ""
echo "手动修改建议:"
echo "  - 第3章: 添加'基于第2章双重表象...'"
echo "  - 第4章: 明确视角选择策略"
echo "  - 第5章: 波函数坍塌两种表述"
echo "  - 第8章: 实验预言视角分配"
echo ""
echo "========================================="
echo "  执行完毕，请手动检查关键章节"
echo "========================================="
