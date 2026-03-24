# Woodhouse《Geometric Quantization》精读笔记 - 第4-6章

**阅读日期**: 2026-03-24  
**章节**: Ch.4-6 (极化与量子希尔伯特空间)  
**目标**: 建立扭转场的极化理论与Fock空间联系

---

## 第4章：实极化 (Real Polarizations)

### 4.1 极化的定义

**定义4.1 (极化)**
一个**极化** $\mathcal{P}$ 是切丛 $TM$ 的可积Lagrange子丛：
1. **维数**: $\dim \mathcal{P}_m = n = \frac{1}{2}\dim M$（对所有 $m \in M$）
2. **Lagrange性质**: $\omega(X, Y) = 0$ 对所有 $X, Y \in \mathcal{P}$ 成立
3. **可积性**: $[\mathcal{P}, \mathcal{P}] \subset \mathcal{P}$（Frobenius条件）

**物理意义**: 极化选择"一半"变量作为"坐标"，另一半作为"动量"。

### 4.2 实极化的类型

**类型1: 垂直极化 (位形空间极化)**

$$
\mathcal{P} = \text{span}\left\{\frac{\partial}{\partial p_1}, \ldots, \frac{\partial}{\partial p_n}\right\}
$$

**波函数**: $\psi(q)$ —— 仅依赖于位形 $q$

**扭转场对应**:

$$
\mathcal{P} = \text{span}\left\{\frac{\delta}{\delta \pi_\alpha^{\mu\nu}(x)}\right\}
$$

**波函数**: $\Psi[\mathcal{T}]$ —— 扭转场位形上的泛函

**类型2: 水平极化 (动量空间极化)**

$$
\mathcal{P} = \text{span}\left\{\frac{\partial}{\partial q^1}, \ldots, \frac{\partial}{\partial q^n}\right\}
$$

**波函数**: $\phi(p)$ —— 仅依赖于动量 $p$

**扭转场对应**:

$$
\mathcal{P} = \text{span}\left\{\frac{\delta}{\delta \mathcal{T}^\alpha_{\mu\nu}(x)}\right\}
$$  

**波函数**: $\Phi[\pi]$ —— 共轭动量上的泛函

### 4.3 极化波函数

**定义4.2 (极化波函数)**
一个截面 $\psi \in \Gamma(L)$ 是**极化的**，如果：

$$
\nabla_X \psi = 0 \quad \forall X \in \mathcal{P}
$$

**物理意义**: 沿极化方向的协变导数为零 —— "不依赖于极化方向上的坐标"。

**垂直极化下的波函数**:

对于 $\mathcal{P} = \text{span}\{\partial/\partial p_i\}$:
- 条件: $\nabla_{\partial/\partial p_i} \psi = 0$
- 联络: $\nabla = d - (i/\hbar)\theta = d - (i/\hbar)\sum p_i dq^i$
- 解: $\psi(q, p) = e^{(i/\hbar)\sum p_i q^i} \phi(q)$

**关键**: 预量子化波函数包含因子 $e^{(i/\hbar)\sum p_i q^i}$！

### 4.4 内积问题

**问题**: 如何定义极化波函数的内积？

对于垂直极化 $\psi(q, p) = e^{(i/\hbar)pq} \phi(q)$:
- 预量子化内积: $\langle\psi_1|\psi_2\rangle = \int dq dp \, \overline{\psi_1} \psi_2$
- 发散！因为 $|e^{(i/\hbar)pq}|^2 = 1$

**解决方案**: 在商空间 $M/\mathcal{P}$ 上积分

对于垂直极化，$M/\mathcal{P} \cong Q$ (位形空间):

$$
\langle\phi_1|\phi_2\rangle = \int_Q dq \, \overline{\phi_1(q)} \phi_2(q)
$$

### 4.5 Bohr-Sommerfeld量子化

**定理4.3 (Bohr-Sommerfeld)**
对于实极化，波函数在极化叶层上的单值性条件给出量子化：

$$
\oint_\gamma \theta = 2\pi\hbar n, \quad n \in \mathbb{Z}
$$

其中 $\gamma$ 是极化叶层中的闭合回路。

**物理解释**: 
- 经典作用量必须是 $2\pi\hbar$ 的整数倍
- 与旧量子论的量子化条件一致

### 4.6 实极化的问题

**主要问题**:
1. **测度定义**: 在无限维情况下，商空间 $M/\mathcal{P}$ 上的测度难以定义
2. **半形式**: 需要引入半形式来正确归一化
3. **Maslov指标**: 出现额外的相位

**对于扭转场**:
- 位形空间泛函积分 $\int \mathcal{D}\mathcal{T}$ 没有严格定义
- 需要更精细的数学处理

**结论**: 对于扭转场（无限维场论），实极化不太实用。需要Kähler极化！

---

## 第5章：Kähler极化 (复极化)

### 5.1 近复结构

**定义5.1 (近复结构)**
一个**近复结构** $J$ 是切丛的线性自同构：

$$
J: TM \to TM, \quad J^2 = -I
$$

**可积性**: $J$ 是**可积的**，如果Nijenhuis张量 $N_J = 0$：

$$
N_J(X, Y) = [JX, JY] - J[JX, Y] - J[X, JY] - [X, Y]
$$

**Newlander-Nirenberg定理**: 可积的近复结构 $ightarrow$ 复流形结构。

### 5.2 相容性条件

**定义5.2 (相容三元组)**
$(g, \omega, J)$ 构成**相容三元组**，如果：
1. **辛相容**: $\omega(JX, JY) = \omega(X, Y)$
2. **度量定义**: $g(X, Y) = \omega(X, JY)$ 是正定的

**等价表述**:
- $g(JX, JY) = g(X, Y)$ （$J$ 是等距）
- $\omega(X, Y) = g(JX, Y)$ （辛形式来自复结构）

### 5.3 Kähler流形

**定义5.3 (Kähler流形)**
一个**Kähler流形** $(M, \omega, J)$ 是配备相容复结构的辛流形。

**Kähler势**: 局部存在函数 $K$ 使得：

$$
\omega = i \partial \bar{\partial} K
$$

**在坐标** $(z^1, \ldots, z^n)$ 下：

$$
\omega = i \sum_{j,k} g_{j\bar{k}} dz^j \wedge d\bar{z}^k
$$

其中 $g_{j\bar{k}} = \partial^2 K / \partial z^j \partial \bar{z}^k$ 是Hermite度规。

### 5.4 Kähler极化的构造

**复坐标分解**:

对于相容的 $J$，切空间分解为：

$$
TM \otimes \mathbb{C} = T^{(1,0)}M \oplus T^{(0,1)}M
$$

其中：
- $T^{(1,0)}M = \{X - iJX : X \in TM\}$ （全纯切丛）
- $T^{(0,1)}M = \{X + iJX : X \in TM\}$ （反全纯切丛）

**Kähler极化**:

$$
\mathcal{P} = T^{(0,1)}M = \text{span}\left\{\frac{\partial}{\partial \bar{z}^1}, \ldots, \frac{\partial}{\partial \bar{z}^n}\right\}
$$

**性质验证**:
1. **维数**: $\dim_\mathbb{C} T^{(0,1)}M = n = \frac{1}{2}\dim_\mathbb{R} M$ ✓
2. **Lagrange**: $\omega$ 是 $(1,1)$-形式，因此 $\omega|_{T^{(0,1)}} = 0$ ✓
3. **可积**: $[T^{(0,1)}, T^{(0,1)}] \subset T^{(0,1)}$（复结构的可积性）✓

### 5.5 全纯波函数

**极化条件**:

对于 $\psi \in \Gamma(L)$，Kähler极化条件是：

$$
\nabla_{\partial/\partial \bar{z}^j} \psi = 0 \quad \forall j
$$

**解的形式**:

使用局部平凡化，联络是 $\nabla = d - (i/\hbar)\theta$。

对于Kähler流形，联络1-形式可以写成：

$$
\theta = -i \partial K = -i \sum_j \frac{\partial K}{\partial z^j} dz^j
$$

因此极化波函数满足：

$$
\frac{\partial \psi}{\partial \bar{z}^j} - \frac{1}{\hbar}\frac{\partial K}{\partial \bar{z}^j}\psi = 0
$$

**解**: $\psi = e^{-K/\hbar} f(z)$，其中 $f(z)$ 是全纯函数！

### 5.6 扭转场的Kähler极化

**复结构定义**:

定义复坐标：

$$
\mathcal{T}^\pm(x) = \frac{1}{\sqrt{2}}\left(\mathcal{T}(x) \pm \frac{i}{\mu}\pi(x)\right)
$$

其中 $\mu$ 是具有质量量纲的参数。

**复结构算符**:

$$
J: \begin{cases}
\mathcal{T} \mapsto \frac{1}{\mu}\pi \\
\pi \mapsto -\mu \mathcal{T}
\end{cases}
$$

验证：$J^2 = -I$ ✓

**相容性验证**:

辛形式在复坐标下：

$$
\omega = i \int d^3x \, \delta \mathcal{T}^-(x) \wedge \delta \mathcal{T}^+(x)
$$

这是 $(1,1)$-形式！✓

**Kähler势**:

$$
K = \int d^3x \, \mathcal{T}^-(x) \mathcal{T}^+(x) = \frac{1}{2}\int d^3x \left(\mathcal{T}^2 + \frac{\pi^2}{\mu^2}\right)
$$

这与谐振子的经典作用量一致！

**全纯波函数**:

$$
\Psi[\mathcal{T}^+] = e^{-K/\hbar} f[\mathcal{T}^+]
$$

其中 $f[\mathcal{T}^+]$ 是 $\mathcal{T}^+$ 的全纯泛函。

---

## 第6章：量子希尔伯特空间

### 6.1 Kähler极化下的内积

**内积定义**:

对于全纯波函数 $\Psi_j = e^{-K/\hbar} f_j(z)$：

$$
\langle \Psi_1 | \Psi_2 \rangle = \int_M \frac{\omega^n}{n!} e^{-K/\hbar} \overline{f_1(z)} f_2(z)
$$

**关键**: $e^{-K/\hbar}$ 因子保证了测度的收敛性！

**在复坐标下**:

$$
\langle \Psi_1 | \Psi_2 \rangle = \int \prod_j d^2z^j \, \det(g_{k\bar{l}}) e^{-K/\hbar} \overline{f_1(z)} f_2(z)
$$

### 6.2 全纯表示中的算符

**乘法算符**:

全纯函数 $a(z)$ 的作用：

$$
\hat{a} \Psi = e^{-K/\hbar} a(z) f(z)
$$

**微分算符**:

共轭变量 $b(\bar{z})$ 的作用（在 Bargmann 表示中）：

$$
\hat{b} \Psi = \hbar \frac{\partial}{\partial z} \Psi = e^{-K/\hbar} \hbar \frac{\partial f}{\partial z}
$$

**关键对应**:
- 全纯坐标 $z \leftrightarrow$ 产生算符 $a^\dagger$
- 反全纯坐标 $\bar{z} \leftrightarrow$ 湮灭算符 $a$

### 6.3 与Fock空间的同构

**Segal-Bargmann变换**:

定义相干态：

$$
|z\rangle = e^{-|z|^2/2} e^{z a^\dagger} |0\rangle
$$

**波函数作为内积**:

$$
\Psi(z) = \langle z | \Psi \rangle
$$

**产生湮灭算符的作用**:

$$
a^\dagger |z\rangle = z |z\rangle \Rightarrow \hat{a}^\dagger \Psi(z) = z \Psi(z)
$$

$$
a |z\rangle = \hbar \frac{\partial}{\partial z} |z\rangle \Rightarrow \hat{a} \Psi(z) = \hbar \frac{\partial}{\partial z} \Psi(z)
$$

### 6.4 扭转场的Fock空间对应

**全纯坐标 ↔ 产生算符**:

$$
\hat{\mathcal{T}}^+(x) \Psi[\mathcal{T}^+] = \mathcal{T}^+(x) \Psi[\mathcal{T}^+]
$$

**反全纯坐标 ↔ 湮灭算符**:

$$
\hat{\mathcal{T}}^-(x) \Psi[\mathcal{T}^+] = \hbar \frac{\delta}{\delta \mathcal{T}^+(x)} \Psi[\mathcal{T}^+]
$$

**对应关系表**:

| 阶段A (Fock) | 阶段B (几何量子化) |
|-------------|-------------------|
| 粒子数态 $|n_{\mathbf{k},\lambda}\rangle$ | $\Psi_n[\mathcal{T}^+] \propto (\mathcal{T}^+)^n e^{-K/\hbar}$ |
| 产生算符 $\hat{a}^\dagger_{\mathbf{k},\lambda}$ | 乘法 $\mathcal{T}^+_{\mathbf{k},\lambda}$ |
| 湮灭算符 $\hat{a}_{\mathbf{k},\lambda}$ | 微分 $\hbar \delta/\delta \mathcal{T}^+_{\mathbf{k},\lambda}$ |
| Fock真空 $|0\rangle$ | 常数波函数 $\Psi_0 = e^{-K/\hbar}$ |
| 相干态 $|\alpha\rangle$ | 全纯波函数 $\exp(\int \alpha \mathcal{T}^+ - K/\hbar)$ |

### 6.5 真空波函数

**Fock真空** $|0\rangle$ 对应几何量子化中的波函数：

$$
\Psi_0[\mathcal{T}^+] = e^{-K/\hbar} = \exp\left(-\frac{1}{2\hbar}\int d^3x \, \mathcal{T}^+(x) \mathcal{T}^-(x)\right)
$$

**物理意义**: 真空是高斯型的 —— 在场论中自然出现！

### 6.6 自洽性验证

**检验1**: 算符对易关系

$$[\hat{\mathcal{T}}^-(x), \hat{\mathcal{T}}^+(y)] = \left[\hbar \frac{\delta}{\delta \mathcal{T}^+(x)}, \mathcal{T}^+(y)\right] = \hbar \delta^3(x-y)$$

与阶段A的 $[\hat{a}, \hat{a}^\dagger] = \hbar$ 一致！✓

**检验2**: 哈密顿量对角化

对于自由扭转场：

$$
\hat{H} = \int d^3x \left(\frac{1}{2}\hat{\pi}^2 + \frac{1}{2}(\nabla \hat{\mathcal{T}})^2\right)
$$

在复坐标下：

$$
\hat{H} = \int \frac{d^3k}{(2\pi)^3} \, \hbar \omega_{\mathbf{k}} \left(\hat{a}^\dagger_{\mathbf{k}} \hat{a}_{\mathbf{k}} + \frac{1}{2}\right)
$$

与标准的Fock空间哈密顿量一致！✓

---

## 关键公式总结

### 实极化
| 概念 | 公式 | 扭转场对应 |
|------|------|-----------|
| 垂直极化 | $\mathcal{P} = \text{span}\{\partial/\partial p_i\}$ | $\text{span}\{\delta/\delta \pi(x)\}$ |
| 波函数 | $\psi(q, p) = e^{(i/\hbar)pq} \phi(q)$ | $\Psi[\mathcal{T}, \pi] = e^{(i/\hbar)\int \pi \mathcal{T}} \Phi[\mathcal{T}]$ |
| 内积 | $\langle\phi_1|\phi_2\rangle = \int dq \, \bar{\phi}_1 \phi_2$ | 泛函积分问题 |

### Kähler极化
| 概念 | 公式 | 说明 |
|------|------|------|
| 复结构 | $J^2 = -I$ | $J: \mathcal{T} \mapsto \pi/\mu$ |
| 复坐标 | $z = (q + ip/\mu)/\sqrt{2}$ | $\mathcal{T}^+ = (\mathcal{T} + i\pi/\mu)/\sqrt{2}$ |
| Kähler势 | $K = \sum z^j \bar{z}^j$ | $K = \int \mathcal{T}^+ \mathcal{T}^-$ |
| 全纯波函数 | $\Psi = e^{-K/\hbar} f(z)$ | $f[\mathcal{T}^+]$ 全纯泛函 |
| 内积 | $\int \omega^n e^{-K/\hbar} \bar{f}_1 f_2$ | 收敛性良好 |

### 阶段A→B桥梁
| 阶段A (Fock) | 阶段B (几何量子化) |
|-------------|-------------------|
| $|n\rangle$ | $H_n(\mathcal{T}^+) e^{-K/\hbar}$ |
| $\hat{a}^\dagger$ | 乘法 $\mathcal{T}^+$ |
| $\hat{a}$ | 微分 $\hbar \delta/\delta \mathcal{T}^+$ |
| $|0\rangle$ | $e^{-K/\hbar}$ (高斯型) |

---

## 第7-8章预告

**第7章**: 半形式 (Half-Forms)
- 为什么需要半形式？
- Metaplectic结构
- Maslov相位

**第8章**: 实例与应用
- 谐振子
- 自旋
- 磁单极子
- **我们的应用**: 扭转场

---

## 练习题

1. **推导**: 从 $\omega = \int d^3x \, \delta \mathcal{T} \wedge \delta \pi$ 出发，推导复坐标下的表达式 $\omega = i \int d^3x \, \delta \mathcal{T}^- \wedge \delta \mathcal{T}^+$。

2. **验证**: 证明复结构 $J: \mathcal{T} \mapsto \pi/\mu, \pi \mapsto -\mu \mathcal{T}$ 满足 $J^2 = -I$ 且与 $\omega$ 相容。

3. **计算**: 证明Kähler极化下的真空波函数 $\Psi_0 = e^{-K/\hbar}$ 是湮灭算符的本征态：$\hat{a}(x) \Psi_0 = 0$。

4. **思考**: 为什么实极化在无限维场论中难以应用，而Kähler极化更合适？

---

**阅读心得**:
- Kähler极化是无限维场论的自然选择
- 与Fock空间的对应关系清晰明确
- 阶段A和阶段B的衔接已经建立
- 下一步：半形式修正（第7章）
