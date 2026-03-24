# 扭转场的Fock空间表示：数学细节

## 1. Fock空间作为诱导表示

### 1.1 单粒子希尔伯特空间

单粒子态由扭转场的平方可积函数组成：

$$\mathcal{H}_1 = L^2(\mathbb{R}^3, d^3x) \otimes \mathcal{V}_{tensor}$$

其中 $\mathcal{V}_{tensor}$ 是扭转场的内部向量空间。

**内积定义**：

$$\langle \psi | \phi \rangle = \int d^3x \, \psi^*(x) \phi(x)$$

### 1.2 张量积构造

$N$-粒子空间是单粒子空间的张量积：

$$\mathcal{H}_N = \mathcal{H}_1^{\otimes N}$$

对于玻色子（扭转场是玻色场），需要对称化：

$$\mathcal{H}_N^{sym} = S_N \mathcal{H}_1^{\otimes N}$$

其中 $S_N$ 是对称化投影算符：

$$S_N = \frac{1}{N!}\sum_{\sigma \in S_N} P_\sigma$$

### 1.3 Fock空间的直和分解

$$\mathcal{F} = \bigoplus_{N=0}^\infty \mathcal{H}_N^{sym}$$

**零粒子空间**：$\mathcal{H}_0 = \mathbb{C}$（真空态）

**Fock空间内积**：

对于 $|\Psi\rangle = (\psi_0, \psi_1, \psi_2, ...)$ 和 $|\Phi\rangle = (\phi_0, \phi_1, \phi_2, ...)$：

$$\langle \Psi | \Phi \rangle = \sum_{N=0}^\infty \langle \psi_N | \phi_N \rangle_N$$

## 2. 产生湮灭算符的严格定义

### 2.1 湮灭算符

作用于Fock空间的湮灭算符：

$$\hat{a}(f) : \mathcal{H}_N \rightarrow \mathcal{H}_{N-1}$$

对于测试函数 $f \in \mathcal{H}_1$：

$$\hat{a}(f) = \int d^3x \, f(x) \hat{a}(x)$$

**作用在N粒子态上**：

$$\hat{a}(x) |\psi_1, ..., \psi_N\rangle = \frac{1}{\sqrt{N}}\sum_{i=1}^N \delta(x-x_i) |\psi_1, ..., \hat{\psi}_i, ..., \psi_N\rangle$$

### 2.2 产生算符

$$\hat{a}^\dagger(f) : \mathcal{H}_N \rightarrow \mathcal{H}_{N+1}$$

**作用**：

$$\hat{a}^\dagger(x) |\psi_1, ..., \psi_N\rangle = \sqrt{N+1} |x, \psi_1, ..., \psi_N\rangle$$

### 2.3 CCR代数

产生湮灭算符满足标准正则对易关系（CCR）：

$$[\hat{a}(f), \hat{a}^\dagger(g)] = \langle f | g \rangle \hat{I}$$

$$[\hat{a}(f), \hat{a}(g)] = 0$$

$$[\hat{a}^\dagger(f), \hat{a}^\dagger(g)] = 0$$

## 3. 粒子数算符与占据数表示

### 3.1 粒子数算符

$$\hat{N} = \int d^3x \, \hat{a}^\dagger(x)\hat{a}(x)$$

**本征值方程**：

$$\hat{N} |\psi_N\rangle = N |\psi_N\rangle$$

### 3.2 动量空间占据数

使用傅里叶基 $\{e_k(x) = e^{ikx}/\sqrt{V}\}$：

$$\hat{a}_k = \hat{a}(e_k) = \int \frac{d^3x}{\sqrt{V}} e^{-ikx} \hat{a}(x)$$

**占据数基**：

$$|n_{k_1}, n_{k_2}, ...\rangle = \prod_i \frac{(\hat{a}^\dagger_{k_i})^{n_{k_i}}}{\sqrt{n_{k_i}!}}|0\rangle$$

### 3.3 粒子数算符谱

$$\hat{N} = \sum_k \hat{a}^\dagger_k \hat{a}_k = \sum_k \hat{n}_k$$

其中 $\hat{n}_k = \hat{a}^\dagger_k \hat{a}_k$ 是模式 $k$ 的占据数算符。

## 4. 场算符的算符值分布理论

### 4.1 分布意义下的场算符

场算符 $\hat{\phi}(x)$ 是算符值分布（Operator-Valued Distribution, OVD）：

$$\hat{\phi}(f) = \int d^3x \, f(x) \hat{\phi}(x)$$

其中 $f \in \mathcal{D}(\mathbb{R}^3)$ 是测试函数。

### 4.2 涂抹场算符（Smeared Field Operators）

**定义**：

$$\hat{T}(f) = \int d^4x \, f^{\mu\nu}(x) \hat{T}_{\mu\nu}(x)$$

**对易关系**：

$$[\hat{T}(f), \hat{T}(g)] = i\hbar \Delta(f, g) \hat{I}$$

其中 $\Delta$ 是因果传播子。

### 4.3 算符值分布的正则性

在Fock空间中，场算符满足：

- 对于每个测试函数 $f$，$\hat{\phi}(f)$ 是定义在稠密域 $D \subset \mathcal{F}$ 上的算符
- 向量值函数 $f \mapsto \hat{\phi}(f)|\psi\rangle$ 是连续的

## 5. 真空态与相干态

### 5.1 真空态性质

**唯一性**：在不可约表示中，真空态 $|0\rangle$（在相差相因子意义下）唯一确定。

**循环性**：真空态是循环向量，即通过产生算符作用可以得到Fock空间的完备基：

$$\mathcal{F} = \overline{\text{span}}\{\hat{a}^\dagger(f_1)...\hat{a}^\dagger(f_n)|0\rangle\}$$

### 5.2 相干态构造

**定义**：相干态 $|\alpha\rangle$ 满足：

$$\hat{a}(x)|\alpha\rangle = \alpha(x)|\alpha\rangle$$

其中 $\alpha(x)$ 是复函数。

**显式形式**：

$$|\alpha\rangle = e^{-\frac{1}{2}\|\alpha\|^2} \exp\left(\int d^3x \, \alpha(x)\hat{a}^\dagger(x)\right)|0\rangle$$

**完备性关系**：

$$\int \mathcal{D}^2\alpha \, |\alpha\rangle\langle\alpha| = \hat{I}$$

### 5.3 相干态的最小不确定性

相干态最小化海森堡不确定性关系：

$$\Delta T \cdot \Delta \pi = \frac{\hbar}{2}$$

## 6. Fock空间的泛函表示

### 6.1  Bargmann-Segal表示

将Fock空间与全纯函数空间等同：

$$\mathcal{F} \cong \mathcal{H}^2(L^2(\mathbb{R}^3), e^{-|z|^2}d\mu)$$

**同构映射**：

$$|\psi\rangle \mapsto \psi(z) = \langle z | \psi \rangle$$

其中 $|z\rangle$ 是相干态。

### 6.2 产生湮灭算符的作用

在Bargmann表示中：

$$\hat{a}(x) \rightarrow \frac{\delta}{\delta z(x)}$$

$$\hat{a}^\dagger(x) \rightarrow z(x)$$

**内积**：

$$\langle \phi | \psi \rangle = \int \mathcal{D}^2z \, e^{-|z|^2} \phi^*(z) \psi(z)$$

## 7. 与几何量子化的联系

### 7.1 预量子化希尔伯特空间

$$\mathcal{H}_{pre} = L^2(\mathcal{M}, L)$$

其中 $\mathcal{M}$ 是相空间，$L$ 是预量子化线丛。

### 7.2 极化约化

通过选择极化 $\mathcal{P}$（如Kähler极化），约化到物理希尔伯特空间：

$$\mathcal{H}_{phys} = \{\psi \in \mathcal{H}_{pre} : \nabla_X \psi = 0, \forall X \in \mathcal{P}\}$$

对于扭转场，Kähler极化给出Fock空间。

### 7.3 半经典极限

当 $\hbar \rightarrow 0$ 时，量子对易关系退化为经典泊松括号：

$$\frac{1}{i\hbar}[\hat{f}, \hat{g}] \rightarrow \{f, g\}_{PB}$$

## 8. 热核与配分函数

### 8.1 单粒子配分函数

$$Z_1(\beta) = \text{Tr}(e^{-\beta\hat{H}_1}) = \int \frac{d^3k}{(2\pi)^3} e^{-\beta\omega_k}$$

### 8.2 多粒子配分函数（玻色-爱因斯坦统计）

$$Z(\beta) = \prod_k \frac{1}{1 - e^{-\beta\omega_k}}$$

**自由能**：

$$F = -\frac{1}{\beta}\ln Z = \frac{1}{\beta}\sum_k \ln(1 - e^{-\beta\omega_k})$$

## 9. 总结

Fock空间表示为扭转场量子化提供了严格的数学框架：

1. **单粒子空间**：$\mathcal{H}_1 = L^2 \otimes \mathcal{V}_{tensor}$
2. **多粒子空间**：对称化张量积
3. **产生湮灭算符**：满足CCR代数
4. **相干态**：超完备基，最小不确定性
5. **几何量子化联系**：Kähler极化约化

此框架为后续黑洞熵的微观状态计数奠定了基础。
