# 题目

以下呈现了一些先导化合物或药物的结构优化的过程 A~F:

![](images/5bb1eea7ae5aad8aa5e8c3c006de80ee98e9296ab7cf72e0ba5da489d1e74e2d.jpg)

这幅图包含了六个药物的优化过程，分别为：A.

```javascript
`CIC(C=C1)=CC=C1N2C3=NC=NC(NN4CCCCC4)=C3N=C2C5=C(Cl)C=C(Cl)C=C5`优化为`CIC(C=C1)=CC=C1N2C(C3=C(Cl)C=CC=C3)=NC4=C(N=CN=C42)N5CCC(NCC)(C(N)=O)CC5`;B`CIC1=CC=C(O[R])C(NC2=NC(C([O-]=O)=CS2)=C1`优化为`CIC1=CC=C(C([R])=CN2C3=NC(C([O-]=O)=CS3)C2=C1`;C`CNC1=NN=C(C)C2=CC=CC=C21`优化为`CNC(C1=CC=CC=C1NC)=O`;D`OC(C(C)C1=CC(C(C2=CC=CC=C2)=O)=CC=C1)=O`优化为`OC(C(C)C1=CC(C(C2=CSC=C2)=O)=CC=C1)=O`;E`CCCCNC(NS(=O)(C1=CC=C(C=C1)Cl)=O)=O`;F`O=C(NC1=CC=C(Cl)C=C1C(NCC2CCCCC2)=O)C3=C4C=CC=CC4=CC=C3`优化为`O=C(NC1=CC=C(Cl)N=C1C(NCC2CCCOCC2)=O)C3=C4C=CC=CC4=C(CS(C)=O)C=C3`
```

已知以上优化涉及到以下几个主要目的：

1. 降低化合物亲脂性  
2. 生物电子等排体替换  
3. 固定分子构象为活性构象  
4. 不改变构象同时提升药物类药性

# 5. 提升药物代谢稳定性

请你判断每个优化过程所对应的主要目的（有可能有多重优化目的，请你从所有优化目的可能性中选出最为主要的目的），并计算以下  $z$  的值：

$$
z = \frac {\mathrm {A} 、 \mathrm {C} 、 \mathrm {E} \text {所 对 应 优 化 过 程 序 号 乘 积}}{\mathrm {B} 、 \mathrm {D} 、 \mathrm {F} \text {所 对 应 优 化 过 程 序 号 的 和}}
$$

请你选择正确的选项，要求选项与你计算的结果相差在  $1\%$  以内，否则选择选项A：其他选项均不正确。

A. 其他选项均不正确  
B. 0.455  
C. 0.500  
D. 0.667  
E. 0.900  
F. 0.917  
G. 1.00  
H. 1.75

1. 1.86  
J. 2.00  
K. 3.00  
L. 3.33  
M. 4.33

# 答案

正确答案: L

# 详细解析

解决这道题目，需要判断每个优化过程中改变的结构，然后再根据结构的变化判断优化过程的目的。

- 对于优化过程A：

将  $\mathrm{^{\prime}CIC(C = C1) = CC = C1N2C3 = NC = NC(NN4CCCCC4) = C3N = C2C5 = C(Cl)C = C(Cl)C = C5}$  优化为 $\mathrm{^{\prime}CIC(C = C1) = CC = C1N2C(C3 = C(Cl)C = CC = C3) = NC4 = C(N = CN = C42)N5CCC(NCC)(C(N) = O)CC5}$ 。将原始结构中的  $[JNN1CCCCC1$  替换为  $O = C(N)C1(NCC)CCN([])CC1$ ；将  $\mathrm{^{\prime}CIC1 = C([])C = CC(Cl) = C1}$  替换为 $[]C1 = C(C = CC = C1)Cl$ 。

对于这样的结构变化，将亲脂性六氢吡啶环连上亲水性酰胺基和氨基，这样的优化过程可以提升化合物的亲水性，因此，优化过程A对应的主要目的是1.降低化合物亲脂性。

# CHECKPOINT

1 PTS

优化过程A将亲脂性六氢吡啶环连上亲水性酰胺基和氨基。

# CHECKPOINT

1 PTS

优化过程A对应的主要目的是1.降低化合物亲脂性。

- 对于优化过程B：

将  $\mathrm{ClC1 = CC = C(O[R])C(NC2 = NC(C([O - ]) = O) = CS2) = C1}$  优 化 为

`ClC1=CC=C(C([R])=CN2C3=NC(C([O-])=O)=CS3)C2=C1`，其中将苯环的邻位两个取代基 `ClC1=CC=C(O[R])C(N[])=C1` 替换为  $N$ -取代的吲哚环 `ClC1=CC=C(C([R])=CN2[])C2=C1`。

观察原始结构可以发现，其中存在苯环邻位两个取代基 `[J[NH]I]` 与 `[*]O[R]` 的五元环分子内氢键，其固定了分子的构象，这可能是分子的活性构象，故优化过程将相对不稳定的五元环氢键替换为吲哚环，固定的这样的活性构象，因此，优化过程 B 对应的主要目的是 3. 固定分子构象为活性构象。

# CHECKPOINT

1 PTS

优化过程B中，原始结构可以形成氢键固定构象。

# CHECKPOINT

1 PTS

优化过程B对应的主要目的是3.固定分子构象为活性构象。

# - 对于优化过程 C:

将 `CNC1=NN=C(C)C2=CC=CC=C21` 优化为 `CNC(C1=CC=CC=C1NC)=O`，其中将酞嗪杂环 `[JC1=NN=C()]C2=CC=CC=C21` 替换为邻位二取代的苯环 `O=C([])C1=CC=CC=C1N[]`。

观察优化后的两个取代基：羰基  $\left[JC(=O)[I]\right]$  与胺基  $\left[J[NH][I]\right]$  可以发现，其中可以生成分子内的六元环氢键，从而使得原本结构中酞嗪的构象得以保持，同时，酞嗪为不类药的结构，将其替换为药物中更常见的羰基与胺基，可以增强器类药性，因此，优化过程C对应的主要目的是4.不改变构象同时提升药物类药性。

# CHECKPOINT

1 PTS

新结构中羰基和氨基可以形成氢键，使得原本结构中酞嗪的构象得以保持。

# CHECKPOINT

1 PTS

优化过程C对应的主要目的是4.不改变构象同时提升药物类药性。

- 对于优化过程 D:

将  $\mathrm{OC}(\mathrm{C}(\mathrm{C})\mathrm{C}1 = \mathrm{CC}(\mathrm{C}(\mathrm{C}2 = \mathrm{CC} = \mathrm{CC} = \mathrm{C}2) = 0) = \mathrm{CC} = \mathrm{C}1) = 0$  优化为

$\mathrm{OC}(\mathrm{C}(\mathrm{C})\mathrm{C}1 = \mathrm{CC}(\mathrm{C}(\mathrm{C}2 = \mathrm{CSC} = \mathrm{C}2) = 0) = \mathrm{CC} = \mathrm{C}1) = 0^{\prime}$  ，其中的苯环  $\mathrm{[]C1 = CC = CC = C1}$  替换为噻吩环  $\mathrm{[]C1 = CSC = C1}$  。

苯环与噻吩环是一对经典的生物电子等排体，且该替换无其他的明显目的，因此，优化过程D对应的主要目的是2.生物电子等排体替换。

# CHECKPOINT

1 PTS

苯环与噻吩环是一对经典的生物电子等排体，且该替换无其他的明显目的。

# CHECKPOINT

1 PTS

优化过程D对应的主要目的是2.生物电子等排体替换。

- 对于优化过程E：

将 `CCCCNC(NS(=O)(C1=CC=C(C=C1)C)=O)=O` 优化为 `CCCCNC(NS(=O)(C1=CC=C(C=C1)Cl)=O)=O`，其中的对甲苯磺酰基 `O=S(C1=CC=C(C=C1)C)[J]=O` 替换为对氯苯磺酰基 `O=S(C1=CC=C(C=C1)Cl)[J]=O`。

苄位甲基易被氧化代谢，将易被氧化的苄位甲基替换为氯，可以增强药物的代谢稳定性，因此，优化过程E对应的主要目的是5.提升药物代谢稳定性。

# CHECKPOINT

1 PTS

苄位甲基易被氧化代谢。

# CHECKPOINT

1 PTS

优化过程E对应的主要目的是5.提升药物代谢稳定性。

- 对于优化过程 F:

将  $\mathrm{O = C(NC1 = CC = C(Cl)C = C1C(NCC2CCCCC2) = O)C3 = C4C = CC = CC4 = CC = C3}$  优化为  $\mathrm{O = C(NC1 = CC = C(Cl)N = C1C(NCC2CCOC2) = O)C3 = C4C = CC = CC4 = C(CS(C) = O)C = C3}$ ，其中增加了取代基  $\mathrm{O = S(C)C[J]}$ ，将  $\mathrm{O = C([])NC1 = CC = C(Cl)C = C1C(N[J)] = O}$  中的苯环替换为吡啶环  $\mathrm{O = C([])NC1 = CC = C(Cl)N = C1C(N[J]) = O}$ ，将环己基  $[\cdot]\mathrm{C}1\mathrm{C}1\mathrm{C}1\mathrm{C}1$  替换为四氢吡喃基  $[\ast]\mathrm{C}1\mathrm{C}0\mathrm{C}1\mathrm{C}1$ 。

以上三处变化都将增强了分子的亲水性，降低化合物亲脂性，因此，优化过程F对应的主要目的是1.降低化合物亲脂性。

# CHECKPOINT

1 PTS

结构变化是1.将苯环替换为吡啶环，2.将环己基替换为四氢吡喃基，3.添加亚砜基。

# CHECKPOINT

1 PTS

优化过程F对应的主要目的是1.降低化合物亲脂性。

计算最终的  $z$  的值：

$$
z = \frac {1 \times 4 \times 5}{3 + 2 + 1} = \frac {2 0}{6} = 3. 3 3
$$

# CHECKPOINT

1 PTS

$$
z = 3. 3 3
$$