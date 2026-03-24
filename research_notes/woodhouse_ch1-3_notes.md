# Woodhouse《Geometric Quantization》精读笔记 - 第1-3章

**阅读日期**: 2026-03-24  
**章节**: Ch.1-3 (辛几何基础)  
**目标**: 建立扭转场几何量子化的数学基础

---

## 第1章：辛流形基础

### 1.1 定义与基本性质

**定义1.1 (辛流形)**
一个**辛流形** $(M, \omega)$ 是一个光滑流形 $M$ 配备一个闭的、非退化的2-形式 $\omega \in \Omega^2(M)$：
1. **闭性**: $d\omega = 0$
2. **非退化**: 对于任意 $p \in M$，若 $\omega(X, Y) = 0$ 对所有 $Y$ 成立，则 $X = 0$

**维数约束**: 辛流形必须是偶数维，$\dim M = 2n$。

**物理对应 (扭转场)**:
- $M$: 扭转场位形空间（无限维）
- $\omega = \int d^3x \, \delta \mathcal{T} \wedge \delta \pi$: 辛形式
- 非退化性 ↔ 正则对易关系 $[\hat{\mathcal{T}}, \hat{\pi}] = i\hbar \delta^3(x-y)$

### 1.2 达布定理 (Darboux's Theorem)

**定理1.2 (达布)**
对于任意辛流形 $(M, \omega)$，在每点 $p \in M$ 的邻域内存在**达布坐标** $(q^1, \ldots, q^n, p_1, \ldots, p_n)$ 使得：

$$
\omega = \sum_{i=1}^n dq^i \wedge dp_i
$$

**意义**: 所有辛流形在局部上看起来都一样！没有曲率不变量。

**扭转场应用**:
- 达布坐标: $(\mathcal{T}^\alpha_{\mu\nu}(x), \pi_\alpha^{\mu\nu}(x))$
- 局部上，扭转场系统类似于无限多个谐振子的集合

### 1.3 辛映射与辛同构

**定义1.3 (辛映射)**
映射 $\phi: M_1 \to M_2$ 是**辛的**，如果 $\phi^*\omega_2 = \omega_1$。

**物理意义**: 辛映射保持哈密顿结构，对应正则变换。

**例子**:
- 时间演化: 哈密顿流是辛同构
- 规范变换: 保持辛结构的变换

### 1.4 与扭转场的联系

**辛结构回顾**:
对于扭转场，相空间是 $(\mathcal{T}, \pi)$ 的无限维空间：

$$
\omega = \int_\Sigma d^3x \, \delta \mathcal{T}^\alpha_{\mu\nu}(x) \wedge \delta \pi_\alpha^{\mu\nu}(x)
$$

**验证闭性**:
- $\omega = d\Theta$，其中 $\Theta = \int d^3x \, \pi \wedge \delta \mathcal{T}$
- 因此 $d\omega = d^2\Theta = 0$ ✓

**验证非退化性**:
- 对于任意变分 $\delta \mathcal{T}, \delta \pi$
- 若 $\omega((\delta \mathcal{T}, \delta \pi), (\cdot, \cdot)) = 0$ 对所有变分成立
- 则必须有 $\delta \pi = 0$ 和 $\delta \mathcal{T} = 0$
- 因此非退化 ✓

---

## 第2章：哈密顿系统与泊松括号

### 2.1 哈密顿向量场

**定义2.1 (哈密顿向量场)**
对于函数 $f \in C^\infty(M)$，其**哈密顿向量场** $X_f$ 定义为：

$$
\iota_{X_f}\omega = -df
$$

或等价地:

$$
\omega(X_f, Y) = -df(Y) = -Y(f) \quad \forall Y
$$

**存在唯一性**: 由 $\omega$ 的非退化性保证。

**扭转场对应**:
- 哈密顿函数: $f[\mathcal{T}, \pi] = \int d^3x \, \mathcal{H}$
- 哈密顿向量场: 产生正则方程的向量场

### 2.2 泊松括号

**定义2.2 (泊松括号)**
两个函数的泊松括号定义为：

$$
\{f, g\} = \omega(X_f, X_g) = X_f(g) = -X_g(f)
$$

**性质**:
1. **反对称**: $\{f, g\} = -\{g, f\}$
2. **双线性**: 对两个参数都是线性的
3. **莱布尼茨法则**: $\{fg, h\} = f\{g, h\} + g\{f, h\}$
4. **雅可比恒等式**: $\{f, \{g, h\}\} + \{g, \{h, f\}\} + \{h, \{f, g\}\} = 0$

**物理意义**: 泊松括号描述可观测量之间的"正则对易关系"。

### 2.3 泊松括号与量子化

**关键洞见 (Dirac)**:
经典泊松括号与量子对易子的对应：

$$
\{f, g\}_{\text{classical}} \longleftrightarrow \frac{1}{i\hbar}[\hat{f}, \hat{g}]_{\text{quantum}}
$$

**阶段A验证**:
对于扭转场：
- $\{\mathcal{T}(x), \pi(y)\} = \delta^3(x-y)$ （经典泊松括号）
- $[\hat{\mathcal{T}}(x), \hat{\pi}(y)] = i\hbar \delta^3(x-y)$ （量子对易子）

完全对应！✓

### 2.4 诺特定理 (Noether's Theorem)

**定理2.3 (诺特)**
若函数 $f$ 生成一个保持哈密顿量 $H$ 的辛流，则 $f$ 是守恒量：

$$
\{f, H\} = 0 \iff \frac{df}{dt} = 0
$$

**几何表述**: 
- 对称性 ↔ 守恒量
- 矩映射 (Moment Map) 将李群作用映射到守恒量

---

## 第3章：预量子化

### 3.1 预量子化的动机

**问题**: 如何构造满足以下条件的量子化映射 $Q$？
1. $Q(1) = I$ （单位元映射到恒等算符）
2. $Q(\{f, g\}) = \frac{1}{i\hbar}[Q(f), Q(g)]$ （Dirac条件）
3. $Q$ 是线性的

**障碍**: Groenewold-van Hove定理指出，对于多项式函数，这样的 $Q$ 不存在！

**解决方案**: 
- 先构造**预量子化**（满足1-2但不对所有函数定义）
- 然后通过**极化**约化到物理希尔伯特空间

### 3.2 Kostant-Weil定理

**定理3.1 (Kostant-Weil)**
预量子化线丛 $L \to M$ 存在的充要条件是：

$$
\frac{1}{2\pi\hbar}[\omega] \in H^2(M, \mathbb{Z})
$$

其中 $[\omega]$ 是 $\omega$ 的de Rham上同调类。

**证明概要**:
1. 线丛的曲率形式 $F_\nabla$ 满足 $[F_\nabla] = c_1(L)$ （第一陈类）
2. 预量子化要求 $F_\nabla = -\frac{i}{\hbar}\omega$
3. 因此 $c_1(L) = -\frac{i}{2\pi\hbar}[\omega]$
4. 陈类必须是整同调类，得到条件

### 3.3 预量子化线丛的构造

**假设**: $[\omega]/(2\pi\hbar) \in H^2(M, \mathbb{Z})$

**步骤1**: 构造线丛 $L \to M$
- 选取开覆盖 $\{U_\alpha\}$
- 在 $U_\alpha$ 上定义局部联络1-形式 $\theta_\alpha$
- 转移函数 $g_{\alpha\beta} = \exp(\frac{i}{\hbar} \Lambda_{\alpha\beta})$

**步骤2**: 定义联络
$$
\nabla = d - \frac{i}{\hbar}\theta_\alpha \quad \text{在 } U_\alpha \text{ 上}
$$

**步骤3**: 验证曲率
$$
F_\nabla = d\nabla + \nabla \wedge \nabla = -\frac{i}{\hbar}d\theta_\alpha = -\frac{i}{\hbar}\omega
$$

### 3.4 预量子化算符

**定义3.2 (预量子化算符)**
对于 $f \in C^\infty(M)$，预量子化算符 $\hat{f}^{(pre)}$ 在截面 $\psi \in \Gamma(L)$ 上作用为：

$$
\hat{f}^{(pre)}\psi = -i\hbar \nabla_{X_f}\psi + f\psi
$$

**性质验证**:
1. $\hat{1}^{(pre)} = -i\hbar \nabla_{X_1} + 1 = 1$ （因为 $X_1 = 0$）✓
2. 满足Dirac条件：$[\hat{f}^{(pre)}, \hat{g}^{(pre)}] = i\hbar \widehat{\{f,g\}}^{(pre)}$ ✓

**问题**: 预量子化希尔伯特空间太大！需要极化约化。

### 3.5 与扭转场的联系

**预量子化条件验证**:

对于扭转场，$\omega = d\Theta$ 是恰当形式：
- $[\omega] = 0 \in H^2(M, \mathbb{R})$
- 因此 $[\omega]/(2\pi\hbar) = 0 \in H^2(M, \mathbb{Z})$ ✓

**平凡线丛**: $L = M \times \mathbb{C}$

**联络**:
$$
\nabla = d - \frac{i}{\hbar}\Theta = d - \frac{i}{\hbar}\int d^3x \, \pi \wedge \delta \mathcal{T}
$$

**预量子化算符**:
$$
\hat{\mathcal{T}}^{(pre)} = -i\hbar \frac{\delta}{\delta \pi} + \mathcal{T}
$$

$$
\hat{\pi}^{(pre)} = i\hbar \frac{\delta}{\delta \mathcal{T}}
$$

**注意**: 这不是我们想要的！我们期望：
- $\hat{\mathcal{T}}$ 是乘法算符
- $\hat{\pi}$ 是微分算符

解决：通过**极化**约化。

---

## 关键公式总结

### 辛几何
| 概念 | 公式 | 扭转场对应 |
|------|------|-----------|
| 辛形式 | $\omega = \sum dq^i \wedge dp_i$ | $\int d^3x \, \delta \mathcal{T} \wedge \delta \pi$ |
| 闭性 | $d\omega = 0$ | $\omega = d\Theta$ |
| 泊松括号 | $\{f,g\} = \omega(X_f, X_g)$ | $\{\mathcal{T},\pi\} = \delta^3(x-y)$ |

### 预量子化
| 概念 | 公式 | 说明 |
|------|------|------|
| 存在条件 | $[\omega]/(2\pi\hbar) \in H^2(M, \mathbb{Z})$ | Kostant-Weil定理 |
| 联络 | $\nabla = d - (i/\hbar)\theta$ | 曲率 $F_\nabla = -(i/\hbar)\omega$ |
| 预量子算符 | $\hat{f}^{(pre)} = -i\hbar \nabla_{X_f} + f$ | 满足Dirac条件 |

---

## 下一步预告

**第4-6章**: 极化与量子希尔伯特空间

核心内容:
1. **实极化**: 波函数仅依赖于一半变量
2. **Kähler极化**: 复结构下的全纯波函数
3. **半形式**: 测度修正
4. **与Fock空间的联系**: 我们的目标！

---

## 练习题

1. **验证**: 证明扭转场的辛形式 $\omega = \int d^3x \, \delta \mathcal{T} \wedge \delta \pi$ 满足达布定理的条件。

2. **计算**: 对于哈密顿量 $H = \int d^3x \left(\frac{1}{2}\pi^2 + \frac{1}{2}(\nabla \mathcal{T})^2\right)$，计算其哈密顿向量场 $X_H$。

3. **验证**: 证明预量子化算符满足 $[\hat{f}^{(pre)}, \hat{g}^{(pre)}] = i\hbar \widehat{\{f,g\}}^{(pre)}$。

---

**阅读心得**: 
- Woodhouse的表述清晰严谨，特别是达布定理和Kostant-Weil定理的证明思路
- 预量子化是"半成品"，极化约化是关键
- 扭转场的辛结构与标准场论一致，几何量子化框架可以直接应用
