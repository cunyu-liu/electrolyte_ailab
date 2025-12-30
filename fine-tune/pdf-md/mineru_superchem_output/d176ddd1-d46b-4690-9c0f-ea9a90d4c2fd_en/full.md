# Question

Isothermal Titration Calorimetry (ITC) is a classical thermodynamic method for determining biomolecular interactions, renowned as the "gold standard" for biomolecular interaction studies due to its high sensitivity and accuracy. Da Congming discovered in experiments that two chemically synthesized small molecules,  $A$  and  $B$ , can inhibit the function of enzyme  $E$ . Anxious, he planned to directly use ITC to measure and compare the binding abilities of the two molecules to the enzyme, conducting the following experiments:

1. Titration of  $15\mu M$  protein  $E$  directly with  $250\mu MA$ . The fitting results yielded a stoichiometry ratio of  $n = 1$ ,  $\Delta H = -7.6 \, kcal \cdot mol^{-1}$ , but failed to fit  $K_{d}$ .  
2. Titration of  $15\mu M$  protein  $E$  directly with  $250\mu B$ . The fitting results yielded  $n = 1$ ,  $\Delta H = 7.3\, kcal\cdot mol^{-1}$ ,  $K_{d} = 0.41\, \mu M$ .  
3. Mixing a 10-fold excess of  $B$  with  $15\mu M \, E$ , and then titrating with  $250\mu M \, A$ . Under these conditions, the measured values were  $n = 0.87$ ,  $\Delta H = -4.8 \, kcal \cdot mol^{-1}$ ,  $K_{d} = 15.5 \, nM$ .

Based on the above information, which of the following options is most likely the binding constant  $K_{a}$  of  $A$  and  $E$ ?

A.  $2.36 \times 10^{9}$  
B.  $2.42 \times 10^{9}$  
C.  $2.28 \times 10^{10}$  
D.  $2.37 \times 10^{10}$  
E.  $3.94 \times 10^{10}$  
F.  $3.94 \times 10^{11}$

G. Insufficient information to calculate.

# Answer

Correct Answer: G

# Detailed Explanation

This question examines the common competition analysis method in ITC analysis. When the binding between a protein and a small molecule is too strong, the ITC method may not be able to accurately fit  $K_{d}$  due to sharp signal spikes. A feasible approach to solving this problem is to reduce the protein concentration to decrease the c-value. However, when the protein concentration is too low, the ITC heat signal will be masked by noise, making it impossible to obtain an accurate titration curve. Therefore, competing with a known inhibitor and then titrating the complex has become an effective analytical method.

Considering a side reaction caused by  $B$ , it is easy to write the side reaction coefficient caused by  $B$  as  $\alpha_{B} = \frac{[E] + [EB]}{[E]} = 1 + \frac{B}{K_{d}^{B}}$ . The true  $K_{d}$  of  $A$  is  $K_{app} \times \alpha_{B} = 4.2 \times 10^{-11}M$ , so  $K_{a} = 2.37 \times 10^{10}$ . At this time, option C is satisfied.

# CHECKPOINT

1 PTS

If A and B conform to the competition model, then  $K_{a}^{A} = 2.37\times 10^{10}$

However, it should be noted that the question does not specify whether there is a competitive relationship between small molecules  $A$  and  $B$ . We can focus on the  $\Delta H$  values in the ITC experiment. The binding of  $A$  has  $\Delta H = -7.6kcal \cdot mol^{-1}$ , and the binding of  $B$  has  $\Delta H = 7.3kcal \cdot mol^{-1}$ . If the two have a competitive relationship, then the reaction formula is  $EB \longrightarrow B + E$ ,  $E + A \longrightarrow EA$ , and the theoretical  $\Delta H = -7.3 + (-7.6) = -14.9kcal \cdot mol^{-1}$ . The measured  $\Delta H = -4.8kcal \cdot mol^{-1}$  indicates that the binding of  $B$  has a weak effect on the thermal effect of  $A$ , which is obviously inconsistent with the competition model. A more reasonable explanation is that the two have a synergistic effect. The binding of molecule  $B$  causes a certain large conformational change in the protein, which affects the binding of  $A$  at another site, resulting in a change in the thermal effect and a weakening of the binding, which can be measured by ITC. Therefore, it is

obviously incorrect to directly apply the ITC formula for competitive binding. The impatient and clever student did not verify the competitive relationship between the two compounds before performing the ITC experiment. This is unscientific, so the  $K_{d}$  of  $A$  cannot be calculated in this question.

# CHECKPOINT

1 PTS

The thermal effect data in ITC indicate that the two molecules should not conform to the competition model, so it cannot be calculated