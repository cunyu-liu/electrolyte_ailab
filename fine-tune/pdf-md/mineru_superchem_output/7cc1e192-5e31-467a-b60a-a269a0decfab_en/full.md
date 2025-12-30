# Question

Lomefloxacin hydrochloride is a quinolone antibacterial drug that can be used to treat acute and chronic infectious diseases caused by various Gram-positive and Gram-negative bacteria. Now, an adult patient is given lomefloxacin hydrochloride by intravenous infusion at a rate of  $0.200\mathrm{g / h}$ , and the infusion time is  $\mathrm{T} = 1\mathrm{h}$ .

After lomefloxacin hydrochloride enters the body, it quickly diffuses to various parts to reach equilibrium. Therefore, the entire organism can be regarded as a single "compartment". Let  $V_{d}$  be the ratio of the amount of drug in the body to the blood drug concentration at this time, then  $V_{d}$  is equivalent to the volume of the "compartment" (apparent volume of distribution). The metabolism of lomefloxacin hydrochloride in the human body can be regarded as a first-order reaction (rate constant is  $k$ ). The relationship between the concentration of lomefloxacin hydrochloride in plasma  $\mathrm{C}(\mu \mathrm{g / mL})$  and time is shown in the following table.

<table><tr><td>时间(h)</td><td>0.00</td><td>0.50</td><td>1.00</td><td>4.00</td><td>7.00</td><td>11.00</td><td>15.00</td><td>+∞</td></tr><tr><td>C(μg/mL)</td><td>0</td><td>2.54</td><td>4.49</td><td>2.43</td><td>1.49</td><td>0.79</td><td>0.45</td><td>0</td></tr></table>

The following statements are correct (if the calculated result has an error greater than  $3\%$ , the statement is considered incorrect):

1. Using linear fitting, the rate constant of drug metabolism can be calculated as  $\mathrm{k} = 0.163\mathrm{h}^{-1}$  
2. The apparent volume of distribution is  $V_{d} = 45 \, \text{L}$  (to maintain the uniqueness of the results, if you want to substitute the data in the table for calculation, uniformly choose  $t = 1.00 \, \text{h}$ )  
3. If intravenous infusion is continued at the same rate, after a period of time, the blood drug concentration in the patient's body can reach a relatively stable level, which is called the steady-state blood drug concentration  $C_{\mathrm{ss}}$ . Under the conditions of the problem, the drug's  $C_{\mathrm{ss}} = 30.06 \mu \mathrm{g} / \mathrm{mL}$  
4. If the intravenous infusion rate is increased, the time  $t$  for the drug concentration to reach  $90\%$  of the steady-state blood drug concentration will be shorter  
5. Lomefloxacin hydrochloride is more evenly distributed in human body fluids

A. All other options are incorrect  
B. 1,2  
C. 2,3,4  
D. 3,4,5  
E. 1,4,5  
F. 2,5  
G. 2,3,4,5  
H. 1,3,5  
1,2,4,5  
J. 2,3  
K. 1,4  
L. 1,3  
M. 3,5  
N. 3

O. 5  
P. 1

# Answer

Correct Answer: H

# Detailed Explanation

# Statement 1:

For a first-order reaction,  $\ln \mathrm{C} = \ln \mathrm{C}_0 - \mathrm{kt}$ ; therefore, plotting  $\ln \mathrm{C} - t$ , the slope is  $\mathbf{k}$ .

Calculate the logarithm of each C, lnC:

<table><tr><td>Time (h)</td><td>1.00</td><td>4.00</td><td>7.00</td><td>11.00</td><td>15.00</td></tr><tr><td>C(μg/mL)</td><td>4.49</td><td>2.43</td><td>1.49</td><td>0.79</td><td>0.45</td></tr><tr><td>ln C</td><td>1.50185</td><td>0.88789</td><td>0.3988</td><td>-0.23572</td><td>-0.79851</td></tr></table>

Linear regression yields  $\mathrm{k} = 0.163\mathrm{h}^{-1}$ , statement 1 is correct.

CHECKPOINT

2 PTS

$$
\mathrm {k} = 0. 1 6 3 \mathrm {h} ^ {- 1}
$$

# Statement 2:

For the intravenous infusion administration phase, the drug amount in the patient's body changes with time according to:

$$
\mathrm {d C / d t = r - k C}
$$

$$
- \frac {1}{\mathrm {k}} \ln (- \mathrm {k C} + \mathrm {r}) = \mathrm {t} + \mathrm {c}
$$

When  $t = 0$ ,  $C = 0$ ; therefore,  $c = -\frac{1}{k}\ln (r)$

So:  $t = \frac{1}{k} \ln(r) - \frac{1}{k} \ln(-kC + r)$

Simplified:  $\exp (-\mathrm{kt}) = 1 - \frac{\mathrm{kC}}{\mathrm{r}}$

# CHECKPOINT

2 PTS

$$
\exp (- k t) = 1 - \frac {k C}{r}
$$

$$
\exp (- 0. 1 6 3 \mathrm {h} ^ {- 1} \cdot \mathrm {t}) = 1 - \frac {0 . 1 6 3 \mathrm {h} ^ {- 1} \cdot \mathrm {C}}{\mathrm {r}}
$$

Substituting  $t = 1.00 \, \text{h}$ ,  $C = 4.49 \, \mu \text{g/mL}$ , we get:  $r = 4.9 \, \mu \text{g/(mL·h)}$

The apparent volume of distribution is:  $\mathrm{V_d} = 0.200\mathrm{g / h}\div 4.9\mu \mathrm{g / (mL\cdot h)} = 41\mathrm{L}$ , statement 2 is incorrect.

# CHECKPOINT

2 PTS

The apparent volume of distribution is:  $\mathrm{V_d} = 41\mathrm{L}$

# Statement 3:

$\mathrm{C_{ss} = r / k = 4.9~\mu g / (mL\cdot h)\div 0.163~h^{-1} = 30.06~\mu g / mL,}$  statement 3 is correct.

# CHECKPOINT

1 PTS

$$
\mathrm {C _ {s s}} = 3 0. 0 6 \mu \mathrm {g} / \mathrm {m L}
$$

# Statement 4:

From  $\exp(-\mathrm{kt}) = 1 - \frac{\mathrm{kC}}{\mathrm{r}}$  and  $\mathrm{C_{ss} = r / k}$ , we know  $\mathrm{C} = \mathrm{C_{ss}}[1 - \exp(-\mathrm{kt})]$ , so the time  $t$  for the drug concentration to reach  $90\%$  of the steady-state blood drug concentration is only related to  $k$ . Increasing the intravenous infusion rate does not change  $t$ , statement 4 is incorrect.

# CHECKPOINT

1 PTS

The time t for the drug concentration to reach  $90\%$  of the steady-state blood drug concentration is only related to k. Increasing the intravenous infusion rate does not change t

Statement 5: The apparent volume of distribution is  $V_{\mathrm{d}} = 41 \, \mathrm{L}$ , which is comparable to the total body fluid volume, so lomefloxacin hydrochloride is relatively evenly distributed in the human body, statement 5 is correct.

# CHECKPOINT

1 PTS

Lomefloxacin hydrochloride is relatively evenly distributed in the human body

Statements 1, 3, and 5 are correct, choose H