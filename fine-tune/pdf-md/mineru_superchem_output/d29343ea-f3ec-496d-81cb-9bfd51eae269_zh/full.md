# 题目

# 已知：

1. 水的三相点为  $273.16 \mathrm{~K}$ , 凝固点为  $273.15 \mathrm{~K}$  。  
2. 凝固点与压力的关系为  $\Delta \mathrm{T} / \Delta \mathrm{P} = -7.432 \times 10^{-8} \mathrm{~K} / \mathrm{Pa}$  。  
3. 三相点时, 水的蒸气压为  $610.48 \mathrm{~Pa}$  。  
4. 空气中氮气与氧气的体

积分数为  $79\%$  与  $21\%$  ，其亨利常数分别为  $1.035 \times 10^{-5} \mathrm{~mol} \cdot \mathrm{L}^{-1} / \mathrm{kPa}$  与  $2.154 \times 10^{-5} \mathrm{~mol} \cdot \mathrm{L}^{-1} / \mathrm{kPa}$  。

5. 大气压为  $101325 \mathrm{~Pa}$ , 重力加速度取  $9.8 \mathrm{~m} / \mathrm{s}^{2}$  。

根据已知信息，需要求算的问题为：

(a). 单位均取国际单位时，水的凝固点下降常数的数值（保留两位有效数字）  
(b). 将一杯饱和了空气的水置于海拔  $5000 \mathrm{~m}$  的山顶, 这杯水的凝固点 (单位为  $\mathrm{K}$ , 小数点后保留两位有效数字)。

下列选项均含有两个数值，第一个为问题(a)的答案，第二个为问题(b)的答案，这两个答案均正确的选项是（计算误差小于  $0.1\%$  视为正确）：

A. 其他选项均不正确  
B. 1.8541, 273.13  
C. 1.8541, 273.15  
D. 1.8541, 273.14

E. 1.9542, 273.13  
F. 1.9542, 273.14  
G. 1.9542, 273.15  
H. 2.0542, 273.15  
I. 2.0542, 273.14  
J. 2.0542, 273.13  
K. 2.1542, 273.13  
L. 2.1542, 273.14  
M. 2.1542, 273.15

# 答案

正确答案: G

# 详细解析

问题(a):

凝固点的降低由两部分组成：压力与凝固点的关系，以及空气溶于水的稀溶液依数性导致的凝固点降低。

# CHECKPOINT

2 PTS

凝固点的降低由两部分组成：压力与凝固点的关系，以及空气溶于水的稀溶液依数性导致的凝固点降低

由外压引起的凝固点变化：

$$
\Delta T _ {p} = - 7. 4 2 3 \times 1 0 ^ {- 8} \times (1 0 1 3 2 5 - 6 1 0. 4 8) = - 7. 4 8 5 \times 1 0 ^ {- 3} K
$$

# CHECKPOINT

1 PTS

外压引起的凝固点变化  $\Delta T_{p} = -7.485\times 10^{-3}K$

根据亨利定律，溶解气体的摩尔浓度  $c$  与气体分压  $p$  成正比

$$
c = k _ {H} \cdot p
$$

# CHECKPOINT

1 PTS

亨利定律  $c = k_H \cdot p$

因此求出饱和水中空气浓度：

$$
c = c _ {N _ {2}} + c _ {O _ {2}} = \left(1.035 \times 10 ^ {- 5} \times 79 \% + 2.154 \times 10 ^ {- 5} \times 21 \%\right) \times 101.325 = 1.287 \times 10 ^ {- 3} \mathrm {mol} / L
$$

# CHECKPOINT

1 PTS

饱和水中空气浓度  $c = c_{N_2} + c_{O_2} = 1.287 \times 10^{-3} \, \text{mol/L}$

对于稀水溶液，质量摩尔浓度  $b$  在数值上约等于体积摩尔浓度  $c$

# CHECKPOINT

1 PTS

稀水溶液，质量摩尔浓度  $b$  在数值上约等于体积摩尔浓度  $c$

由依数性引起的凝固点变化

$$
\Delta T _ {c} = K _ {f} \cdot b
$$

# CHECKPOINT

1 PTS

依数性  $\Delta T_{c} = K_{f}\cdot b$

$$
K _ {f} = \Delta T _ {c} / b = (\Delta T - \Delta T _ {p}) / c = (0. 0 1 - 7. 4 8 5 \times 1 0 ^ {- 3}) K / (1. 2 8 7 \times 1 0 ^ {- 3}) m o l / L = 1. 9 5 4 2 K / k g \cdot m o l
$$

# CHECKPOINT

2 PTS

$$
K _ {f} = 1. 9 5 4 2 K / k g \cdot m o l
$$

问题(b):

首先需要根据玻尔兹曼分布求出压力随海拔的变化：

$$
\ln (p _ {1} / p _ {2}) = - M g \Delta h / R T
$$

# CHECKPOINT

1 PTS

玻尔兹曼分布  $\ln (p_1 / p_2) = -Mg\Delta h / RT$

其中  $M$  表示气体的相对分子质量。

计算得  $5000m$  处气体分压：

$$
p _ {N _ {2}, 5 0 0 0} = 4 6 k P a, p _ {O _ {2}, 5 0 0 0} = 1 1 k P a
$$

(由于重力加速度取9.8，后续只保留两位有效数字)

# CHECKPOINT

1 PTS

5000m处气体分压  $p_{N_2,5000} = 46kPa,p_{O_2,5000} = 11kPa$

此时由依数性引起的凝固点变化

$$
\Delta T _ {c} = K _ {f} \cdot b = 2. 0 \times (1. 0 3 5 \times 1 0 ^ {- 5} \times 4 6 + 2. 1 5 4 \times 1 0 ^ {- 5} \times 1 1 = 1. 4 \times 1 0 ^ {- 3} K)
$$

# CHECKPOINT

1 PTS

依数性引起的凝固点变化  $\Delta T_{c} = 1.4\times 10^{-3}K)$

由压力引起的凝固点变化

$$
\Delta T _ {p} = - 7. 4 2 3 \times 1 0 ^ {- 8} \times (4 6 + 1 1) \times 1 0 0 0 = - 4. 2 \times 1 0 ^ {- 3} K
$$

# CHECKPOINT

1 PTS

压力引起的凝固点变化  $\Delta T_{p} = -4.2 \times 10^{-3} K$

因此总凝固点变化

$$
\Delta T = - \Delta T _ {p} + \Delta T _ {c} = 5. 6 \times 1 0 ^ {- 3} K
$$

新的凝固点

$$
T = 2 7 3. 1 6 - 5. 6 \times 1 0 ^ {- 3} = 2 7 3. 1 5 K
$$

# CHECKPOINT

1 PTS

新的凝固点  $T = 273.15 \mathrm{~K}$

因此答案G正确。