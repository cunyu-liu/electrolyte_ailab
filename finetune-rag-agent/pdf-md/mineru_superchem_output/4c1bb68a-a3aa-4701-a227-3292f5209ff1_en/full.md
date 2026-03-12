# Question

The polymer prepared by a certain method exhibits a mole fraction and degree of polymerization that follow the following Poisson distribution.

$$
x _ {k} = \frac {\lambda^ {k}}{k !} e ^ {- \lambda}
$$

Where  $x_{k}$  is the ratio of the amount of substance of polymer chains with a degree of polymerization of  $k$  to the total amount of substance of polymer chains,  $k$  is the degree of polymerization, and  $\lambda$  is the reaction ratio of monomer to initiator. Assuming that the relative molecular mass of the polymer is  $M_{k} = M_{0} + kM$ . Then, for the following sets of parameters, the polymer molecular weight distribution that is the most uniform is:  
A. All other options are incorrect  
B.  $\lambda = 25, M_0 = 100, M = 80$  
C.  $\lambda = 25, M_{0} = 100, M = 100$  
D.  $\lambda = 25, M_{0} = 200, M = 55$  
E.  $\lambda = 25, M_0 = 200, M = 75$  
F.  $\lambda = 25, M_0 = 400, M = 60$  
G.  $\lambda = 25, M_0 = 400, M = 76$  
H.  $\lambda = 50, M_0 = 40, M = 55$  
1.  $\lambda = 50, M_0 = 40, M = 65$  
J.  $\lambda = 50, M_0 = 70, M = 50$  
K.  $\lambda = 50, M_0 = 70, M = 60$  
L.  $\lambda = 50, M_0 = 90, M = 48$  
M.  $\lambda = 50, M_0 = 90, M = 57$

# Answer

Correct Answer: L

# Detailed Explanation

The physical quantity that can reflect the molecular weight distribution of a polymer is the ratio of weight-average molecular weight to number-average molecular weight,  $\frac{X_w}{X_n}$ . Therefore, it is necessary to first derive the expression for  $\frac{X_w}{X_n}$ .

# CHECKPOINT

1 PTS

$\frac{X_w}{X_n}$  can reflect the molecular weight distribution of the polymer

According to the definition, we have  $\frac{X_w}{X_n} = \frac{\sum n_k\sum n_kM_k^2}{(\sum n_kM_k)^2} = \frac{\sum x_kM_k^2}{(\sum x_kM_k)^2}$

# CHECKPOINT

1 PTS

$$
\frac {X _ {w}}{X _ {n}} = \frac {\sum x _ {k} M _ {k} ^ {2}}{(\sum x _ {k} M _ {k}) ^ {2}}
$$

Where  $\sum x_{k}M_{k} = M_{0}\sum \frac{\lambda^{k}}{k!} e^{-\lambda} + M\sum k\frac{\lambda^{k}}{k!} e^{-\lambda}$

And we have  $M_0\sum \frac{\lambda^k}{k!} e^{-\lambda} = M_0$

$$
M \sum k \frac {\lambda^ {k}}{k !} e ^ {- \lambda} = M \lambda e ^ {- \lambda} \sum \frac {\lambda^ {k - 1}}{(k - 1) !} = M \lambda
$$

Therefore, we have  $\sum x_{k}M_{k} = M_{0} + M\lambda$

# CHECKPOINT

1 PTS

$$
\sum x _ {k} M _ {k} = M _ {0} + M \lambda
$$

In addition, we have

$$
\sum x _ {k} M _ {k} ^ {2} = M _ {0} ^ {2} \sum \frac {\lambda^ {k}}{k !} e ^ {- \lambda} + 2 M M _ {0} \sum k \frac {\lambda^ {k}}{k !} e ^ {- \lambda} + M ^ {2} \sum k ^ {2} \frac {\lambda^ {k}}{k !} e ^ {- \lambda}
$$

Where

$$
M _ {0} ^ {2} \sum \frac {\lambda^ {k}}{k !} e ^ {- \lambda} = M _ {0} ^ {2}
$$

$$
2 M M _ {0} \sum k \frac {\lambda^ {k}}{k !} e ^ {- \lambda} = 2 M M _ {0} \lambda
$$

Specifically, we have

$$
\sum k ^ {2} \frac {\lambda^ {k}}{k !} = \sum k \frac {\lambda^ {k}}{(k - 1) !} = \sum \frac {k}{k - 1} \times \frac {\lambda^ {k}}{(k - 2) !} = \lambda^ {2} \sum \frac {\lambda^ {k - 2}}{(k - 2) !} + \lambda \sum \frac {\lambda^ {k - 1}}{(k - 1) !} = e ^ {\lambda} (\lambda^ {2} + \lambda)
$$

From this, we have

$$
M ^ {2} \sum k ^ {2} \frac {\lambda^ {k}}{k !} e ^ {- \lambda} = M ^ {2} (\lambda^ {2} + \lambda)
$$

# CHECKPOINT

$$
M ^ {2} \sum k ^ {2} \frac {\lambda^ {k}}{k !} e ^ {- \lambda} = M ^ {2} (\lambda^ {2} + \lambda)
$$

Therefore, we have

$$
\sum x _ {k} M _ {k} ^ {2} = M _ {0} ^ {2} + 2 M M _ {0} \lambda + M ^ {2} (\lambda^ {2} + \lambda)
$$

# CHECKPOINT

$$
\sum x _ {k} M _ {k} ^ {2} = M _ {0} ^ {2} + 2 M M _ {0} \lambda + M ^ {2} (\lambda^ {2} + \lambda)
$$

Therefore, we obtain

$$
\frac {X _ {w}}{X _ {n}} = 1 + \frac {\lambda M ^ {2}}{(M _ {0} + M \lambda) ^ {2}}
$$

# CHECKPOINT

$$
\frac {X _ {w}}{X _ {n}} = 1 + \frac {\lambda M ^ {2}}{(M o + M \lambda) ^ {2}}
$$

The value of  $\frac{X_{\mathrm{w}}}{X_{\mathrm{n}}}$  can reflect the molecular weight distribution of the polymer; the smaller the value, the more uniform the distribution.

# CHECKPOINT

The smaller the  $\frac{X_w}{X_n}$ , the more uniform the molecular weight distribution of the polymer

Substituting the data in the question into the calculation, the values of  $\frac{X_w}{X_n} - 1$  corresponding to each option are  $B = 0.03628$ ;  $C = 0.03698$ ;  $D = 0.03049$ ;  $E = 0.03266$ ;  $F = 0.02493$ ;  $G = 0.02730$ ;  $H = 0.01943$ ;  $I = 0.01952$ ;  $J = 0.01893$ ;  $K = 0.01910$ ;  $L = 0.01858$ ;  $M = 0$ .

The value of option L is the smallest, which is 0.01858

0.5 PTS

1 PTS

2 PTS

1 PTS