# 题目

$$
x _ {k} = \frac {\lambda^ {k}}{k !} e ^ {- \lambda}
$$

以某方法制备得的聚合物表现出摩尔分数与聚合度会遵循如下的泊松分布。  
式中  $x_{k}$  为聚合度为  $k$  的聚合物链的物质的量与聚合物链总物质的量的比例， $k$  为聚合度， $\lambda$  为单体与引发剂的反应比例。假设该聚合物的相对分子质量为  $M_{k} = M_{0} + kM$  。则对于下面所给的几组参数中，聚合物分子量分布最均一的是：  
A. 其他选项均不正确  
B.  $\lambda = 25, M_0 = 100, M = 80$  
C.  $\lambda = 25, M_{0} = 100, M = 100$  
D.  $\lambda = 25, M_0 = 200, M = 55$  
E.  $\lambda = 25, M_0 = 200, M = 75$  
F.  $\lambda = 25, M_0 = 400, M = 60$  
G.  $\lambda = 25, M_0 = 400, M = 76$  
H.  $\lambda = 50, M_0 = 40, M = 55$  
1.  $\lambda = 50, M_0 = 40, M = 65$  
J.  $\lambda = 50, M_0 = 70, M = 50$  
K.  $\lambda = 50, M_0 = 70, M = 60$  
L.  $\lambda = 50, M_0 = 90, M = 48$  
M.  $\lambda = 50, M_0 = 90, M = 57$

# 答案

正确答案: L

# 详细解析

能够体现聚合物分子量分布的物理量是重均分子量与数均分子量之比  $\frac{X_w}{X_n}$ ，因此需要先推导出  $\frac{X_w}{X_n}$  的表达式。

# CHECKPOINT

1 PTS

$\frac{X_{w}}{X_{n}}$  能够体现聚合物分子量分布

根据定义有  $\frac{X_w}{X_n} = \frac{\sum n_k\sum n_kM_k^2}{(\sum n_kM_k)^2} = \frac{\sum x_kM_k^2}{(\sum x_kM_k)^2}$

# CHECKPOINT

1 PTS

$$
\frac {X _ {w}}{X _ {n}} = \frac {\sum x _ {k} M _ {k} ^ {2}}{(\sum x _ {k} M _ {k}) ^ {2}}
$$

其中  $\sum x_{k}M_{k} = M_{0}\sum \frac{\lambda^{k}}{k!} e^{-\lambda} + M\sum k\frac{\lambda^{k}}{k!} e^{-\lambda}$

并且有  $M_0\sum \frac{\lambda^k}{k!} e^{-\lambda} = M_0$

$$
M \sum k \frac {\lambda^ {k}}{k !} e ^ {- \lambda} = M \lambda e ^ {- \lambda} \sum \frac {\lambda^ {k - 1}}{(k - 1) !} = M \lambda
$$

因此有  $\sum x_{k}M_{k} = M_{0} + M\lambda$

# CHECKPOINT

1 PTS

$$
\sum x _ {k} M _ {k} = M _ {0} + M \lambda
$$

此外还有

$$
\sum x _ {k} M _ {k} ^ {2} = M _ {0} ^ {2} \sum \frac {\lambda^ {k}}{k !} e ^ {- \lambda} + 2 M M _ {0} \sum k \frac {\lambda^ {k}}{k !} e ^ {- \lambda} + M ^ {2} \sum k ^ {2} \frac {\lambda^ {k}}{k !} e ^ {- \lambda}
$$

其中

$$
M _ {0} ^ {2} \sum \frac {\lambda^ {k}}{k !} e ^ {- \lambda} = M _ {0} ^ {2}
$$

$$
2 M M _ {0} \sum k \frac {\lambda^ {k}}{k !} e ^ {- \lambda} = 2 M M _ {0} \lambda
$$

特殊地，有

$$
\sum k ^ {2} \frac {\lambda^ {k}}{k !} = \sum k \frac {\lambda^ {k}}{(k - 1) !} = \sum \frac {k}{k - 1} \times \frac {\lambda^ {k}}{(k - 2) !} = \lambda^ {2} \sum \frac {\lambda^ {k - 2}}{(k - 2) !} + \lambda \sum \frac {\lambda^ {k - 1}}{(k - 1) !} = e ^ {\lambda} (\lambda^ {2} + \lambda)
$$

由此有

$$
M ^ {2} \sum k ^ {2} \frac {\lambda^ {k}}{k !} e ^ {- \lambda} = M ^ {2} (\lambda^ {2} + \lambda)
$$

# CHECKPOINT

0.5 PTS

$$
M ^ {2} \sum k ^ {2} \frac {\lambda^ {k}}{k !} e ^ {- \lambda} = M ^ {2} (\lambda^ {2} + \lambda)
$$

因此有

$$
\sum x _ {k} M _ {k} ^ {2} = M _ {0} ^ {2} + 2 M M _ {0} \lambda + M ^ {2} (\lambda^ {2} + \lambda)
$$

# CHECKPOINT

1 PTS

$$
\sum x _ {k} M _ {k} ^ {2} = M _ {0} ^ {2} + 2 M M _ {0} \lambda + M ^ {2} (\lambda^ {2} + \lambda)
$$

因此得到

$$
\frac {X _ {w}}{X _ {n}} = 1 + \frac {\lambda M ^ {2}}{(M _ {0} + M \lambda) ^ {2}}
$$

# CHECKPOINT

2 PTS

$$
\frac {X _ {w}}{X _ {n}} = 1 + \frac {\lambda M ^ {2}}{(M _ {0} + M \lambda) ^ {2}}
$$

$\frac{X_w}{X_n}$  的值能够体现聚合物分子量分布，其值越小分布越均匀

# CHECKPOINT

1 PTS

$\frac{X_{n}}{X_{n}}$  越小聚合物分子量分布越均匀

将题目中各个数据代入计算，得到各选项对应值的  $\frac{X_w}{X_n} - 1$  的值分别为  $B = 0.03628; C = 0.03698; D = 0.03049; E = 0.03266; F = 0.02493; G = 0.02730; I = 0.01943; J = 0.01952; K = 0.01893; L = 0.01910; M = 0.01858$ ;

选项L的值最小，为0.01858