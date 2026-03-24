# Woodhouse《Geometric Quantization》精读笔记 - 第7-8章

**阅读日期**: 2026-03-24  
**章节**: Ch.7-8 (半形式与实例应用)  
**目标**: 完成扭转场几何量子化框架，建立与熵计算的联系

---

## 第7章：半形式 (Half-Forms)

### 7.1 为什么需要半形式？

**问题背景**: 在实极化中，内积定义需要极化叶层上的测度。

**实极化的内积**:
对于垂直极化 $\mathcal{P}$，波函数是 $\psi = e^{(i/\hbar)pq}\phi(q)$。

预量子化内积：

$$
\langle\psi_1|\psi_2\rangle = \int dq dp \, e^{-(i/\hbar)pq} \overline{\phi_1(q)} e^{(i/\hbar)pq} \phi_2(q) = \int dq dp \, \overline{\phi_1(q)} \phi_2(q)
$$

**发散问题**: 对 $p$ 积分发散！

**传统解决方案**: 在商空间 $M/\mathcal{P} \cong Q$ 上积分：

$$
\langle\phi_1|\phi_2\rangle = \int_Q dq \, \overline{\phi_1(q)} \phi_2(q)
$$

**新问题**: 这个测度没有辛几何的协变定义！

### 7.2 半形式的定义

**动机**: 需要一种几何对象，能自然地提供 $M/\mathcal{P}$ 上的测度。

**定义7.1 (半形式丛)**
设 $\mathcal{P}$ 是实极化。**半形式丛** $\sqrt{|\Lambda|}$ 是 $M/\mathcal{P}$ 上的线丛，满足：

$$
\sqrt{|\Lambda|} \otimes \sqrt{|\Lambda|} = |\Lambda^{\text{top}}| (M/\mathcal{P})^*
$$

其中 $|\Lambda^{\text{top}}|$ 是最高阶外形式（密度丛）。

**物理解释**: 半形式的"平方"是测度。

### 7.3 半形式波函数

**定义7.2 (半形式波函数)**
半形式极化波函数取值于 $L \otimes \sqrt{|\Lambda|}$：

$$
\Psi^{1/2} = \psi \otimes \nu^{1/2}
$$

其中：
- $\psi \in \Gamma(L)$ 是预量子化波函数
- $\nu^{1/2} \in \Gamma(\sqrt{|\Lambda|})$ 是半形式

**内积定义**:

$$
\langle\Psi_1^{1/2}|\Psi_2^{1/2}\rangle = \int_{M/\mathcal{P}} \bar{\psi}_1 \psi_2 \, \nu_1^{1/2} \cdot \nu_2^{1/2}
$$

其中 $\nu_1^{1/2} \cdot \nu_2^{1/2}$ 是全形式（测度）。

### 7.4 Metaplectic结构

**辛群与Metaplectic群**:

**定义7.3 (Metaplectic群)**
**Metaplectic群** $Mp(2n, \mathbb{R})$ 是辛群 $Sp(2n, \mathbb{R})$ 的双重覆盖：

$$
1 \to \mathbb{Z}_2 \to Mp(2n, \mathbb{R}) \to Sp(2n, \mathbb{R}) \to 1
$$

**存在条件**: 辛流形 $M$ 上存在Metaplectic结构当且仅当第二Stiefel-Whitney类 $w_2(M) = 0$。

**与半形式的关系**:
- Metaplectic结构提供了半形式丛的拓扑框架
- 允许定义全局的半形式波函数

### 7.5 Maslov指标

**Bohr-Sommerfeld修正**:

在实极化中，量子化条件修正为：

$$
\oint_\gamma \theta = 2\pi\hbar (n + \mu(\gamma)/4)
$$

其中 $\mu(\gamma)$ 是**Maslov指标**。

**物理解释**:
- Maslov指标计算了极化叶层的"焦散"
- 在经典力学中，对应于作用量变分中的相位跳跃
- 在量子力学中，是波函数的额外相位

**在扭转场中**:
对于Kähler极化（复极化），Maslov相位自动包含在复结构中，不需要显式处理！

### 7.6 Kähler极化中的半形式

**关键洞见**:
在Kähler极化中，半形式可以自然地定义！

**全纯半形式**:
对于Kähler流形，可以考虑**典范丛** $K = \Lambda^{n,0}T^*M$。

**半形式**: $\sqrt{K}$ —— 典范丛的"平方根"。

**波函数**: $\Psi = f(z) \otimes \sqrt{dz^1 \wedge \cdots \wedge dz^n}$

**内积**:

$$
\langle\Psi_1|\Psi_2\rangle = \int_M \frac{\omega^n}{n!} e^{-K/\hbar} \overline{f_1(z)} f_2(z) \sqrt{\det g_{j\bar{k}}}
$$

**关键**: 对于平坦Kähler流形（如扭转场的自由场），$\sqrt{\det g} = 1$，半形式因子是平凡的！

### 7.7 扭转场的半形式分析

**结论**: 对于扭转场的自由场（谐振子型），Kähler极化下的半形式是平凡的。

**理由**:
1. **Kähler度规**: $g_{j\bar{k}} = \delta_{jk}$ （平坦）
2. **半形式因子**: $\sqrt{\det g} = 1$
3. **无需显式处理半形式**

**物理意义**: 扭转场的几何量子化可以直接使用全纯波函数，无需额外的半形式修正。

**例外情况**: 如果考虑弯曲背景或相互作用，可能需要半形式。但对于自由场→熵计算的路径，半形式不是障碍。

---

## 第8章：实例与应用

### 8.1 例1：谐振子

**经典哈密顿量**:

$$
H = \frac{1}{2}(p^2 + q^2)
$$

**辛形式**:

$$
\omega = dq \wedge dp
$$

**复结构**:

$$
z = \frac{1}{\sqrt{2}}(q + ip)
$$

**Kähler势**:

$$
K = z\bar{z} = \frac{1}{2}(q^2 + p^2)
$$

**全纯波函数**:

$$
\Psi_n(z) = e^{-z\bar{z}/2\hbar} \frac{z^n}{\sqrt{n! (\hbar/2)^n}}
$$

**能量本征值**:

$$
E_n = \hbar\omega(n + 1/2)
$$

**与扭转场的联系**:
- 扭转场的每个模式 $\mathcal{T}_{\mathbf{k}}$ 是独立的谐振子
- 总Hilbert空间是单模空间的张量积

### 8.2 例2：自旋 (Coadjoint Orbit)

**辛流形**: $S^2$ (二维球面)

**辛形式**:

$$
\omega = \frac{1}{2} \sin\theta d\theta \wedge d\phi
$$

**几何量子化**:
- 预量子化条件: $\frac{1}{2\pi\hbar}\int_{S^2} \omega = \frac{2s}{2\pi\hbar} \cdot 2\pi = 2s/\hbar \in \mathbb{Z}$
- 因此 $s = \hbar n/2$, $n \in \mathbb{Z}$

**结果**: 自旋量子化 $s = 0, 1/2, 1, \ldots$

**对扭转场的启示**:
- 拓扑约束可以导致量子化
- 在扭转场中，可能类似地出现拓扑量子化

### 8.3 例3：磁单极子 (Dirac Monopole)

**背景**: 带电粒子在磁单极子场中运动

**辛形式**: 包含磁项 $e\mathbf{A} \cdot d\mathbf{x}$

**量子化条件 (Dirac)**:

$$
\frac{e g}{\hbar} = \frac{n}{2}, \quad n \in \mathbb{Z}
$$

其中 $g$ 是磁荷。

**几何解释**:
- 这是预量子化条件在拓扑非平凡情况的应用
- 纤维丛的Chern类给出量子化

### 8.4 应用：扭转场几何量子化完整框架

**步骤总结**:

#### Step 1: 辛结构 (已完成 ✓)

$$
\omega = \int_\Sigma d^3x \, \delta \mathcal{T}^\alpha_{\mu\nu}(x) \wedge \delta \pi_\alpha^{\mu\nu}(x)
$$

**验证**:
- 闭性: $d\omega = 0$ ✓
- 非退化: $[\hat{\mathcal{T}}, \hat{\pi}] = i\hbar\delta^3(x-y)$ ✓

#### Step 2: 预量子化 (已完成 ✓)

**条件**: $[\omega]/(2\pi\hbar) = 0 \in H^2(M, \mathbb{Z})$ ✓

**线丛**: 平凡丛 $L = M \times \mathbb{C}$

**联络**: $\nabla = d - (i/\hbar)\Theta$

#### Step 3: Kähler极化 (已完成 ✓)

**复结构**:

$$
\mathcal{T}^\pm(x) = \frac{1}{\sqrt{2}}\left(\mathcal{T}(x) \pm \frac{i}{\mu}\pi(x)\right)
$$

**Kähler势**:

$$
K = \int d^3x \, \mathcal{T}^+(x) \mathcal{T}^-(x)
$$

**全纯波函数**:

$$
\Psi[\mathcal{T}^+] = e^{-K/\hbar} f[\mathcal{T}^+]
$$

#### Step 4: 量子希尔伯特空间 (已完成 ✓)

**内积**:

$$
\langle\Psi_1|\Psi_2\rangle = \int \mathcal{D}\mathcal{T}^+ \mathcal{D}\mathcal{T}^- e^{-K/\hbar} \overline{f_1[\mathcal{T}^-]} f_2[\mathcal{T}^+]
$$

**算符对应**:

| 算符 | 表示 |
|------|------|
| $\hat{\mathcal{T}}^+(x)$ | 乘法 $\mathcal{T}^+(x)$ |
| $\hat{\mathcal{T}}^-(x)$ | 微分 $\hbar \frac{\delta}{\delta \mathcal{T}^+(x)}$ |
| $\hat{H}$ | $\int \frac{d^3k}{(2\pi)^3} \hbar\omega_{\mathbf{k}} \hat{a}^\dagger_{\mathbf{k}} \hat{a}_{\mathbf{k}}$ |

#### Step 5: 半形式 (简单 ✓)

对于平坦Kähler流形，半形式因子为1，无需显式处理。

---

## 扭转场量子态的显式构造

### 8.5 真空态

**Fock真空**:

$$
|0\rangle \leftrightarrow \Psi_0[\mathcal{T}^+] = e^{-K/\hbar} = \exp\left(-\frac{1}{2\hbar}\int d^3x \, \mathcal{T}^+(x)\mathcal{T}^-(x)\right)
$$

**性质**:
- 高斯型波函数
- 湮灭算符本征态: $\hat{a}(x)|0\rangle = 0$
- 能量: $E_0 = \frac{1}{2}\sum_{\mathbf{k}} \hbar\omega_{\mathbf{k}}$ （零点能）

### 8.6 单粒子态

**定义**: $\hat{a}^\dagger_{\mathbf{k},\lambda}|0\rangle$

**波函数**:

$$
\Psi_{\mathbf{k},\lambda}[\mathcal{T}^+] = \mathcal{T}^+_{\mathbf{k},\lambda} e^{-K/\hbar}
$$

**物理**: 一个扭转场量子，动量 $\mathbf{k}$，极化 $\lambda$

### 8.7 多粒子态

**n粒子态**:

$$
|n_{\mathbf{k}_1,\lambda_1}, \ldots, n_{\mathbf{k}_N,\lambda_N}\rangle = \prod_{j=1}^N \frac{(\hat{a}^\dagger_{\mathbf{k}_j,\lambda_j})^{n_j}}{\sqrt{n_j!}} |0\rangle
$$

**波函数**:

$$
\Psi_n[\mathcal{T}^+] = H_n(\{\mathcal{T}^+_{\mathbf{k},\lambda}\}) e^{-K/\hbar}
$$

其中 $H_n$ 是Hermite多项式（泛函推广）。

### 8.8 相干态

**定义**: 

$$
|\alpha\rangle = e^{-|\alpha|^2/2} e^{\int \alpha(x) \hat{a}^\dagger(x)} |0\rangle
$$

**波函数**:

$$
\Psi_\alpha[\mathcal{T}^+] = \exp\left(\int d^3x \, \alpha(x)\mathcal{T}^+(x) - \frac{1}{2}\int d^3x \, |\alpha(x)|^2 - \frac{1}{2\hbar}K\right)
$$

**性质**:
- 最小不确定态
- 湮灭算符本征态: $\hat{a}(x)|\alpha\rangle = \alpha(x)|\alpha\rangle$
- 在熵计算中有重要作用！

---

## 与阶段C的衔接：黑洞熵计算

### 8.9 密度矩阵的构造

**在几何量子化中**:

密度矩阵 $\rho$ 是Hilbert空间上的正算符，$\text{Tr}\rho = 1$。

**对于正则系综**:

$$
\rho = \frac{e^{-\beta \hat{H}}}{Z}, \quad Z = \text{Tr}(e^{-\beta \hat{H}})
$$

**核函数表示**:

在坐标表象中：

$$
\rho(\mathcal{T}^+_1, \mathcal{T}^+_2) = \langle \mathcal{T}^+_1 | \rho | \mathcal{T}^+_2 \rangle
$$

### 8.10 熵的几何公式

**von Neumann熵**:

$$
S = -\text{Tr}(\rho \ln \rho)
$$

**几何量子化中的计算**:

对于自由场（高斯态）：

$$
S = \sum_{\mathbf{k},\lambda} \left[(n_{\mathbf{k},\lambda} + 1)\ln(n_{\mathbf{k},\lambda} + 1) - n_{\mathbf{k},\lambda}\ln n_{\mathbf{k},\lambda}\right]
$$

其中 $n_{\mathbf{k},\lambda} = \langle \hat{a}^\dagger_{\mathbf{k},\lambda} \hat{a}_{\mathbf{k},\lambda} \rangle$ 是占据数。

### 8.11 黑洞熵的目标

**Bekenstein-Hawking公式**:

$$
S_{BH} = \frac{A}{4G}
$$

**我们的目标**:
用扭转场的几何量子化，从微观状态计数推导这个公式。

**关键步骤**:
1. **黑洞作为热平衡态**: 在Hartle-Hawking真空中的扭转场
2. **模式求和**: 对视界附近的模式求和
3. **紫外截断**: 在Planck尺度截断（扭转场自然提供）
4. **熵计算**: 使用几何量子化的密度矩阵

**预期结果**:
扭转场的谱维流动（$d_s = 4 \to 10$）提供正确的态密度，给出 $S \sim A$。

---

## 完整框架总结

### 阶段A → 阶段B → 阶段C 流程

```
阶段A: 正则量子化
├── 辛结构: Ω = ∫ δ𝒯 ∧ δπ
├── 泊松括号: {𝒯,π} = δ³(x-y)
├── Fock空间: |nₖ⟩
└── 对易关系: [â,â†] = ℏ

    ↓

阶段B: 几何量子化
├── 预量子化: [Ω]/(2πℏ) ∈ H²(M,ℤ) ✓
├── Kähler极化: 𝒯⁺ = (𝒯 + iπ/μ)/√2
├── 全纯波函数: Ψ = e^(-K/ℏ) f[𝒯⁺]
├── 半形式: 平凡（平坦Kähler）
└── 与Fock同构: 建立 ✓

    ↓

阶段C: 黑洞熵计算 (准备开始)
├── 密度矩阵: ρ = e^(-βĤ)/Z
├── 熵公式: S = -Tr(ρ ln ρ)
└── 目标: S = A/4G
```

---

## 关键公式总表

### 扭转场几何量子化完整公式

| 概念 | 公式 |
|------|------|
| **辛形式** | $\omega = \int d^3x \, \delta \mathcal{T} \wedge \delta \pi$ |
| **复坐标** | $\mathcal{T}^\pm = (\mathcal{T} \pm i\pi/\mu)/\sqrt{2}$ |
| **Kähler势** | $K = \int d^3x \, \mathcal{T}^+ \mathcal{T}^-$ |
| **全纯波函数** | $\Psi = e^{-K/\hbar} f[\mathcal{T}^+]$ |
| **内积** | $\int \mathcal{D}\mathcal{T}^+ \mathcal{D}\mathcal{T}^- e^{-K/\hbar} \bar{f}_1 f_2$ |
| **产生算符** | $\hat{a}^\dagger \leftrightarrow \mathcal{T}^+$ (乘法) |
| **湮灭算符** | $\hat{a} \leftrightarrow \hbar \delta/\delta \mathcal{T}^+$ (微分) |
| **真空** | $\Psi_0 = e^{-K/\hbar}$ |
| **半形式** | 平凡（平坦度规） |

---

## 练习题

1. **验证**: 证明平坦Kähler流形上半形式丛是平凡的。

2. **计算**: 对于一维谐振子，计算前三个能级的波函数 $\Psi_0, \Psi_1, \Psi_2$，并验证正交归一性。

3. **推导**: 从 $\rho = e^{-\beta H}/Z$ 出发，推导自由玻色气体的熵公式 $S = \sum_k [(n_k+1)\ln(n_k+1) - n_k\ln n_k]$。

4. **思考**: 为什么扭转场的几何量子化自然地导向高斯型真空波函数？这与黑洞熵计算有什么关系？

5. **探索**: 如果扭转场有自相互作用，半形式会如何变化？Kähler极化是否仍然适用？

---

## 阶段B完成总结

### 成果清单

✅ **数学框架完整建立**:
- 预量子化条件验证通过
- Kähler极化显式构造
- 与Fock空间的同构建立
- 半形式分析（平凡情况）

✅ **扭转场专用公式**:
- 复坐标: $\mathcal{T}^\pm = (\mathcal{T} \pm i\pi/\mu)/\sqrt{2}$
- Kähler势: $K = \int \mathcal{T}^+ \mathcal{T}^-$
- 全纯波函数: $\Psi = e^{-K/\hbar} f[\mathcal{T}^+]$

✅ **量子态构造**:
- 真空态: $\Psi_0 = e^{-K/\hbar}$
- 单粒子态: $\Psi_{\mathbf{k}} = \mathcal{T}^+_{\mathbf{k}} e^{-K/\hbar}$
- 相干态: $\Psi_\alpha = \exp(\int \alpha \mathcal{T}^+ - K/\hbar)$

✅ **阶段C准备就绪**:
- 密度矩阵框架
- 熵的几何公式
- 与Bekenstein-Hawking公式的联系路径

### 下一步：阶段C启动

**阶段C: 黑洞熵微观状态计数**

**计划**:
1. **Hartle-Hawking真空**: 黑洞背景中的扭转场态
2. **模式分析**: 视界附近的准正规模
3. **态密度计算**: 利用谱维流动
4. **熵推导**: $S = A/4G$ 的微观起源

---

**阅读心得**:
- 半形式在Kähler极化下通常是平凡的，简化了计算
- 几何量子化与Fock空间的联系清晰明确
- 扭转场的框架已经完成，可以开始黑洞熵计算
- Woodhouse的书提供了坚实的数学基础
