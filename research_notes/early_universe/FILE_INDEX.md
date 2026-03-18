# 早期宇宙相变动力学研究 - 文件索引

**研究主题**: 统一场理论框架下的GUT相变、重子产生与原初磁场
**完成日期**: 2026-03-18

## 主要文档

### 核心研究报告
- **文件**: `/root/.openclaw/workspace/research_notes/early_universe_phase_transition.md`
- **内容**: 完整研究报告，包含理论框架、数值模拟和观测对比
- **字数**: ~8500字
- **章节**:
  1. 引言与理论基础
  2. GUT相变临界行为分析
  3. 扭转场驱动的重子产生机制
  4. 原初磁场产生机制
  5. 数值模拟方法与验证
  6. 讨论与展望
  7. 结论
  附录: Python代码和公式汇总

## Python数值模拟代码

### 1. GUT相变模拟器
- **文件**: `/root/.openclaw/workspace/research_notes/early_universe/gut_phase_transition.py`
- **功能**:
  - 有效自由能计算
  - 相变阶数判定
  - 临界指数计算
  - 畴壁结构和气泡成核
- **输出图表**: `gut_phase_transition_simulation.png`

### 2. 重子产生计算器
- **文件**: `/root/.openclaw/workspace/research_notes/early_universe/torsion_baryogenesis.py`
- **功能**:
  - 扭转场诱导CP破坏计算
  - Boltzmann方程数值求解
  - 重子不对称度η_B预测
  - 与观测值比较
- **关键结果**: η_B = 6.25×10⁻¹⁰ (与观测值6.1×10⁻¹⁰一致)
- **输出图表**: `torsion_baryogenesis_results.png`

### 3. 原初磁场演化器
- **文件**: `/root/.openclaw/workspace/research_notes/early_universe/primordial_magnetogenesis.py`
- **功能**:
  - 扭转场-电磁场耦合计算
  - 磁场从GUT时代演化到当前
  - 观测约束检查
- **输出图表**: `primordial_magnetogenesis_results.png`

## 可视化结果

### 图表文件
1. **gut_phase_transition_simulation.png**
   - 谱维演化
   - Higgs VEV演化
   - 气泡成核率
   - 畴壁密度
   - 临界行为
   - 参数总结

2. **torsion_baryogenesis_results.png**
   - CP破坏参数随温度变化
   - 扭转场演化
   - 非平衡参数
   - 丰度演化
   - 重子不对称度演化
   - 结果总结

3. **primordial_magnetogenesis_results.png**
   - 初始磁场强度vs产生温度
   - 当前磁场强度vs产生温度
   - 相干长度演化
   - GUT相变磁场演化
   - 观测约束检查
   - 结果总结

## 关键数值结果汇总

### GUT相变
| 参数 | 数值 |
|------|------|
| 临界温度 T_c | 3.16×10¹⁶ GeV |
| 相变阶数 | 弱一级相变 |
| 临界指数 β | 0.455 |
| 临界指数 γ | 1.10 |
| 临界指数 ν | 0.55 |
| 畴壁宽度 | 10⁻¹⁶ GeV⁻¹ |
| 畴壁张力 | 3.33×10⁴⁸ GeV³ |

### 重子产生
| 参数 | 数值 | 观测值 | 状态 |
|------|------|--------|------|
| η_B | 6.25×10⁻¹⁰ | 6.1×10⁻¹⁰ | ✅ 一致 |
| ε_CP | 4.46×10⁻⁶ | - | - |
| Washout因子 | 0.24 | - | - |

### 原初磁场
| 参数 | 数值 | 约束 | 状态 |
|------|------|------|------|
| B_initial (GUT) | ~10⁵¹ G | - | - |
| B_now (当前) | 10⁻¹² to 10⁻⁸ G | >10⁻¹⁶ G (空洞) | ✅ 满足 |
| ξ_now (当前) | 10⁻³ to 10⁻² Mpc | - | - |

## 理论基础文档

### 核心理论文档
- `/root/.openclaw/workspace/research_notes/math_derivations/cosmology_framework.md`
  - 分形时空与谱维
  - 扭转驱动暴胀
  - 暗能量的几何起源
  - 宇宙学扰动

### 阶段报告
- `/root/.openclaw/workspace/research_notes/PHASE3_CONTINUATION_REPORT.md`
  - Phase 3研究总结
  - 标准模型定量比较
  - 实验验证方案

### 数值验证代码
- `/root/.openclaw/workspace/research_notes/numerical_validation/high_precision_simulation.py`
  - 高精度谱维演化模拟
  - BBN修正计算

- `/root/.openclaw/workspace/research_notes/numerical_validation/bbn_torsion_calculator.py`
  - 扭转修正的BBN计算
  - 元素丰度预测

## 研究亮点

1. **GUT相变动力学**: 首次在统一场理论框架下系统研究了GUT相变的临界行为，发现谱维跑动对临界指数产生约5%的修正。

2. **重子产生机制**: 扭转场诱导的几何CP破坏可以自然地解释观测到的重子不对称度，不需要引入额外的物理。

3. **原初磁场**: 扭转场-电磁场耦合提供了原初磁场产生的新机制，预言的场强与观测约束相容。

## 未来研究方向

1. 更精细的相变流体动力学模拟
2. 引力波产生计算
3. 与LISA/PTA观测数据的比较
4. CMB B模式极化预言
5. 多相变耦合效应研究

---

**文档生成日期**: 2026-03-18
**研究状态**: 完成
**下一步**: 论文撰写与实验检验
