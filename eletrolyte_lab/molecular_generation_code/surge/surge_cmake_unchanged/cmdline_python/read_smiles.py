import os

count = 0
path = ".\\test_gdb"
dir = os.listdir(path)
print(dir)
for i in dir:
    file = os.listdir(path + '\\' + i)
    for j in file:
        print(path + '\\' + i + '\\' + j)
        with open(path + '\\' + i + '\\' + j, 'r') as f1:
            for line in f1.readlines():  
                count+=1
print(count)