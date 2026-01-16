import math
import os
import subprocess
import time
import shutil
import argparse

def get_H_num(num_C: int, num_O: int):
    all_H_nums = []
    if num_C != 0:
        max_H = num_C * 2 + 2
    else:
        print("Number of C can't equal zero!")
        return 0
    for num_H in range(max_H, -1, -2):
        all_H_nums.append(num_H)
    return all_H_nums


def set_root():
    os.makedirs(f'test_gdb', exist_ok=True)
    os.makedirs(f'test_info', exist_ok=True)
    return os.path.abspath(f'test_gdb'), os.path.abspath(f'test_info')


def set_sub_workbase(formula: str, gdb_path: str, info_path: str):
    os.chdir(gdb_path)
    os.makedirs(formula)
    sub_gdb_path = os.path.abspath(formula)
    os.chdir(info_path)
    os.makedirs(formula)
    sub_info_path = os.path.abspath(formula)
    return sub_gdb_path, sub_info_path


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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', help="Number of nodes")
    args = parser.parse_args()
    num_sum_CO = int(args.n)

    start_time = time.time()
    with open("log", 'a') as f:
        f.write(f"Nodes: {num_sum_CO}")
        f.write('\n')
        f.write(time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time())))
        f.write('\n')

    cwd_ = os.getcwd()
    surge_path = '../bin/surge'
    surge_path = os.path.abspath(surge_path)
    print(surge_path)
    cmdline_list = [surge_path, '-S', '-Y', '-B1,2,3,4,5,6,7,8,9']

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

    gdb_path, info_path = set_root()
    symbol_list = ['C', 'O', 'H']
    for num_C in range(num_sum_CO, min_C - 1, -1):
        num_O = num_sum_CO - num_C
        print(time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time())))
        a_CO_formular = get_formular(num_list=[num_C, num_O], symbol_list=symbol_list)
        sub_gdb_path, sub_info_path = set_sub_workbase(formula=a_CO_formular, gdb_path=gdb_path, info_path=info_path)
        all_H_nums = get_H_num(num_C=num_C, num_O=num_O)
        for a_H_num in all_H_nums:
            start_time = time.time()
            #################### Start Run ####################
            if a_H_num == 0:
                a_formula = a_CO_formular
            else:
                a_formula = a_CO_formular + 'H' + str(a_H_num)
            
            cmdline_list.append(a_formula)
            smi_file = a_formula + '.smi'
            cmdline_list.append('-o' + smi_file)
            os.chdir(sub_gdb_path)
            out = subprocess.run(cmdline_list, shell=True, capture_output=True)
            del cmdline_list[-2:]
            #################### Post-process ####################
            if out.returncode != 0:
                continue
            if os.stat(smi_file).st_size == 0:
                os.remove(smi_file)
                continue
            os.chdir(sub_info_path)
            with open(a_formula, 'wb') as f:
                f.write(out.stderr)
            end_time = time.time()
            duration = round(end_time - start_time, 2)
            with open(a_formula, 'a') as f:
                f.write('\nTime:\n'+str(duration)+'s\n')
        os.chdir(cwd_)
        if len(os.listdir(sub_gdb_path)) == 0:
            shutil.rmtree(sub_gdb_path)
            shutil.rmtree(sub_info_path)

    with open("log", 'a') as f:
        f.write("--- Count: %s seconds ---" % (time.time() - start_time))
        f.write('\n')
        f.write(time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time())))
        f.write('\n')
        f.write('\n')

if __name__ == '__main__':
    main()