#!/bin/bash
# 修复 Unicode 字符以便与 revtex4-2 兼容

cd /root/.openclaw/workspace/uft-clifford-torsion/paper

# 修复 emoji 和特殊 Unicode 字符
echo "修复 Unicode 字符..."

# 修复 sections/05a_ckm_effective.tex
sed -i 's/❌/$\\times$/g; s/✅/$\\checkmark$/g; s/✓/$\\checkmark$/g; s/⚠/Warning:/g; s/⚠️/Warning:/g' sections/05a_ckm_effective.tex

# 修复 sections/05c_methodology.tex
sed -i 's/✅/$\\checkmark$/g; s/✓/$\\checkmark$/g; s/❌/$\\times$/g' sections/05c_methodology.tex

# 修复 appendices/F_meta_framework.tex  
sed -i 's/✅/$\\checkmark$/g; s/✓/$\\checkmark$/g; s/❌/$\\times$/g; s/↔/$\\leftrightarrow$/g' appendices/F_meta_framework.tex

# 修复 sections/03b_multiple_twisting.tex
sed -i 's/Z₂/$Z_2$/g' sections/03b_multiple_twisting.tex

# 修复 appendices/D_code_interface.tex - 替换框图字符为 ASCII
sed -i 's/├/|/g; s/─/-/g; s/│/|/g; s/└/\\/g' appendices/D_code_interface.tex

echo "Unicode 修复完成！"
