# Question

Three-dimensional crystals possess translational symmetry in all three directions. However, there exists a class of structures, including quasicrystals, that disrupt this property due to complex reasons. As crystallographers delved deeper, it was discovered that these structures restore translational symmetry when viewed from a higher-dimensional perspective, hence they are referred to as higher-dimensional crystals. Compound  $\mathbf{A}$  is a common  $(3 + 1)D$  crystal with the composition (TTF)  $\mathrm{I}_{0.7 + x}(0 < x < 0.1)$ , where TTF (tetrathiafulvalene) and I exhibit the same periodicity along the  $a$  and  $b$  directions, while their periodicities differ along the  $c$  direction, resulting in a "vernier caliper"-like structure in this direction. If the ratio  $c_{\mathrm{T}} / c_{\mathrm{TT}}$  is approximately considered an integer ratio, the combined superstructure possesses a conventional unit cell.

The known superstructure cell parameters of  $\mathbf{A}$  are  $a = 4.815\mathrm{nm}$ ,  $b = 1.605\mathrm{nm}$ ,  $c \approx 2.500\mathrm{nm}$ ,  $\beta = 91.50^{\circ}$ . If any lattice point of the two substructures is placed at the  $(0,0,0)$  position in the superstructure, then TTF lattice points are located at  $(1/3,0,0)$ ,  $(5/6,1/2,0)$ ,  $(0,0,1/7)$ , while I lattice points are located at  $(1/6,0,14/15)$ ,  $(0,1/2,9/10)$ ,  $(0,0,1/5)$  (minor variations in the coordinates of TTF and I can be neglected).

Based on the above information, determine the lattice types of the TTF and I substructures (if only the  $b$ -direction is centered, it can be denoted as  $B$ -centered, using the superstructure coordinate system as reference).

A. TTF substructure: A-centered monoclinic; I substructure: A-centered monoclinic  
B. TTF substructure: A-centered monoclinic; I substructure: B-centered monoclinic  
C. TTF substructure: A-centered monoclinic; I substructure: C-centered monoclinic  
D. TTF substructure: B-centered monoclinic; I substructure: A-centered monoclinic

E. TTF substructure: B-centered monoclinic; I substructure: B-centered monoclinic  
F. TTF substructure: B-centered monoclinic; I substructure: C-centered monoclinic  
G. TTF substructure: C-centered monoclinic; I substructure: A-centered monoclinic  
H. TTF substructure: C-centered monoclinic; I substructure: B-centered monoclinic  
I. TTF substructure: C-centered monoclinic; I substructure: C-centered monoclinic

# Answer

Correct Answer: G

# Detailed Explanation

Analysis of the TTF Substructure

Known TTF lattice point coordinates (with the supercell as the reference frame):

The translation vectors of the TTF lattice are  $(0,0,0)$ ,  $(1/3,0,0)$ ,  $(5/6,1/2,0)$ ,  $(0,0,1/7)$

# CHECKPOINT

1 PTS

The translation vectors of the TTF lattice are  $(0,0,0)$ ,  $(1/3,0,0)$ ,  $(5/6,1/2,0)$ ,  $(0,0,1/7)$

These points are all lattice points in the TTF lattice. Therefore, the vector difference between them must also be a translation vector of the TTF lattice.

Finding translation vectors in the a, b directions:

The vector from  $P_0$  to  $P_1$  is  $v_1 = P_1 - P_0 = (1/3, 0, 0)$ . This indicates that  $(1/3, 0, 0)$  is a translation vector.

Then, its integer multiples are also translation vectors, such as  $2 * v_{1} = (2/3, 0, 0)$  and  $3 * v_{1} = (1, 0, 0)$ .

The vector from  $P_0$  to  $P_2$  is  $v_{2} = P_{2} - P_{0} = (5 / 6,1 / 2,0)$

Now we have two translation vectors  $v_{1}$  and  $v_{2}$  in the ab plane.

Calculate  $v_{2} - v_{1} = (5 / 6, 1 / 2, 0) - (1 / 3, 0, 0) = (5 / 6 - 2 / 6, 1 / 2, 0) = (3 / 6, 1 / 2, 0) = (1 / 2, 1 / 2, 0)$ .

# CHECKPOINT

1 PTS

There exists a translation vector  $(1/2, 1/2, 0)$  in the TTF lattice

We have derived a new translation vector  $t = (1/2, 1/2, 0)$ . This vector is exactly the centering vector of the C-centered lattice.

# CHECKPOINT

1 PTS

C-center corresponds to the translation vector  $(1/2, 1/2, 0)$

In addition to translations along the supercell basis vector directions (such as  $(1,0,0)$ , etc.), the TTF substructure's lattice also contains an additional translation symmetry of  $(1/2,1/2,0)$ .

This means that the TTF substructure is C-centered with respect to the supercell. Since the superstructure is monoclinic, the TTF substructure is C-centered monoclinic.

# CHECKPOINT

1 PTS

The TTF substructure is C-centered monoclinic

Analysis of the I Substructure

Known translation vectors:

$$
u _ {1} = (1 / 6, 0, 1 4 / 1 5), u _ {2} = (0, 1 / 2, 9 / 1 0), u _ {3} = (0, 0, 1 / 5)
$$

# CHECKPOINT

1 PTS

The translation vectors of the I lattice are  $(0,0,0),(1/3,0,0),(5/6,1/2,0),(0,0,1/7)$

The basis vectors of the I substructure can be written as a linear combination of the supercell basis vectors. Let the

basis vectors of the I substructure be  $a^{\prime},b^{\prime},c^{\prime}$  then:

$a^\prime = m_{11}a + m_{12}b + m_{13}cb^\prime = m_{21}a + m_{22}b + m_{23}cc^\prime = m_{31}a + m_{32}b + m_{33}c.$  The given lattice point

coordinates  $(u,v,w)$  must be an integer multiple linear combination of these basis vectors.

$(1/6, 0, 14/15), (0, 1/2, 9/10), (0, 0, 1/5)$  are all translation vectors. We hope to find whether there exists a

translation vector  $t = (p,q,r) + n_1a' + n_2b' + n_3c'$ , where  $(p,q,r)$  is one of  $(1/2,1/2,0), (1/2,0,1/2)$ , or

$(0,1 / 2,1 / 2)$  Note that  $u_{2} = (0,1 / 2,9 / 10)$

$u_{2} - (0,1 / 2,1 / 2) = (0,0,9 / 10 - 1 / 2) = (0,0,4 / 10) = (0,0,2 / 5) = 2*(0,0,1 / 5).$  Therefore,

$u_{2} - 2*u_{3} = (0,1 / 2,1 / 2)$ . Since  $u_{2}$  and  $u_{3}$  are both translation vectors of the I lattice, their integer multiple

linear combination  $(u_{2} - 2*u_{3})$  is also a translation vector of the I lattice.

# CHECKPOINT

1 PTS

An integer multiple linear combination of translation vectors is also a translation vector

We have derived the translation vector  $t = (0, 1/2, 1/2)$ .

# CHECKPOINT

1 PTS

There exists a translation vector  $(0,1 / 2,1 / 2)$  in the I lattice

This vector is exactly the centering vector of the A-centered lattice.

# CHECKPOINT

1 PTS

A-center corresponds to the translation vector  $(0,1 / 2,1 / 2)$

The lattice of the I substructure contains a translation symmetry of  $(0,1 / 2,1 / 2)$ .

This means that the I substructure is A-centered with respect to the supercell. Since the superstructure is monoclinic, the I substructure is A-centered monoclinic.

# CHECKPOINT

1 PTS

The I substructure is A-centered monoclinic