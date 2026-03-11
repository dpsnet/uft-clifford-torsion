#!/bin/bash
# 论文最终审校脚本
# 全面检查术语、公式、引用、语言

echo "========================================="
echo "  论文最终审校执行脚本"
echo "========================================="
echo ""

# 定义检查函数
check_term_consistency() {
    echo "[检查1/5] 术语一致性检查"
    echo "----------------------------------------"
    
    # 关键术语列表
    TERMS=(
        "分形-扭转双重表象"
        "分形表象"
        "扭转表象"
        "分形-扭转对偶"
        "互内空间对偶"
        "纵-横复合拓扑"
        "三重统一框架"
    )
    
    for term in "${TERMS[@]}"; do
        count=$(grep -r "$term" /root/.openclaw/workspace/research_notes/*.md 2>/dev/null | wc -l)
        echo "  '$term': 出现 $count 次"
    done
    echo ""
}

check_formula_consistency() {
    echo "[检查2/5] 公式符号一致性检查"
    echo "----------------------------------------"
    
    # 检查关键公式
    echo "  检查 d_s = 4 - τ² 格式..."
    grep -n "d_s.*=.*4.*-.*τ" /root/.openclaw/workspace/research_notes/*.md 2>/dev/null | head -5
    
    echo ""
    echo "  检查 d_s^τ 格式..."
    grep -n "d_s\^τ" /root/.openclaw/workspace/research_notes/*.md 2>/dev/null | head -5
    
    echo ""
    echo "  检查 Φ (对偶变换) 使用..."
    grep -n "Φ" /root/.openclaw/workspace/research_notes/*.md 2>/dev/null | wc -l
    echo ""
}

check_citation_completeness() {
    echo "[检查3/5] 引用完整性检查"
    echo "----------------------------------------"
    
    # 检查章节引用
    echo "  第2章引用检查..."
    grep -n "第2章\|Chapter 2" /root/.openclaw/workspace/research_notes/paper_full_integration.md 2>/dev/null | head -3
    
    echo ""
    echo "  定理引用检查..."
    grep -n "定理.*[0-9]\.[0-9]" /root/.openclaw/workspace/research_notes/*.md 2>/dev/null | wc -l
    echo ""
}

check_language_quality() {
    echo "[检查4/5] 语言质量检查"
    echo "----------------------------------------"
    
    # 检查常见语言问题
    echo "  检查重复用词..."
    grep -n "非常.*非常" /root/.openclaw/workspace/research_notes/*.md 2>/dev/null
    
    echo ""
    echo "  检查口语化表达..."
    grep -n "我们.*认为\|我.*觉得" /root/.openclaw/workspace/research_notes/*.md 2>/dev/null | head -3
    
    echo ""
    echo "  检查被动语态过度使用..."
    grep -n "被.*了\|由.*所" /root/.openclaw/workspace/research_notes/*.md 2>/dev/null | wc -l
    echo ""
}

generate_quality_report() {
    echo "[检查5/5] 生成质量报告"
    echo "----------------------------------------"
    
    # 统计文档信息
    total_files=$(find /root/.openclaw/workspace/research_notes -name "*.md" -type f | wc -l)
    total_lines=$(find /root/.openclaw/workspace/research_notes -name "*.md" -type f -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}')
    total_words=$(find /root/.openclaw/workspace/research_notes -name "*.md" -type f -exec cat {} \; 2>/dev/null | wc -w)
    
    echo "  总文档数: $total_files"
    echo "  总行数: $total_lines"
    echo "  总词数: $total_words"
    echo ""
    
    # 质量评估
    echo "  质量评估:"
    echo "    - 术语一致性: 待检查"
    echo "    - 公式规范性: 待检查"
    echo "    - 引用完整性: 待检查"
    echo "    - 语言质量: 待检查"
    echo ""
}

# 执行检查
check_term_consistency
check_formula_consistency
check_citation_completeness
check_language_quality
generate_quality_report

echo "========================================="
echo "  审校执行完毕"
echo "========================================="
