import math
import os
import subprocess


def get_H_num(num_C: int,  num_O: int):
    all_seq = []
    if num_C != 0:
        max_HF = num_C * 2 + 2
    else:
        print("Number of C can't equal zero!")
        return 0
    for num_HF in range(max_HF, -1, -2):
        for num_H in range(num_HF + 1):
            num_F = num_HF - num_H
            all_seq.append([num_C, num_O, num_F, num_H])
    return all_seq

def get_formular(num_list: list, symbol_list: list):
    a_formula = ''
    for idx, a_num in enumerate(num_list):
        if a_num == 0:
            continue
        if a_num == 1:
            a_formula = a_formula + symbol_list[idx]
        else:
            a_formula = a_formula + symbol_list[idx] + str(a_num)
    return a_formula

tracker = 0
num_sum_CO = 2
min_C = 1
if num_sum_CO >=1 and num_sum_CO <= 5:
    min_C = 1
elif num_sum_CO >5 and num_sum_CO <= 8:
    min_C = 2
elif num_sum_CO >8 and num_sum_CO <= 11:
    min_C = 3
elif num_sum_CO >11 and num_sum_CO <= 14:
    min_C = 4
elif num_sum_CO >14 and num_sum_CO <= 17:
    min_C = 5

symbol_list = ['C', 'O', 'F', 'H']
for num_C in range(num_sum_CO, min_C - 1, -1):
    num_O = num_sum_CO - num_C
    all_seq = get_H_num(num_C=num_C, num_O=num_O)
    for a_seq in all_seq:
        a_formula = get_formular(num_list=a_seq, symbol_list=symbol_list)
        print(a_formula)
        tracker = tracker + 1
print(f'Tracker is {tracker}.')
