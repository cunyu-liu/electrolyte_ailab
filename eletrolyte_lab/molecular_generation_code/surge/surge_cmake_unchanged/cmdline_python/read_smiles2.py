import os

def iter_count(file_name):
    from itertools import (takewhile, repeat)
    buffer = 1024 * 1024
    with open(file_name) as f:
        buf_gen = takewhile(lambda x: x, (f.read(buffer) for _ in repeat(None)))
        return sum(buf.count('\n') for buf in buf_gen)

count = 0
path = ".\\test_gdb"
dir = os.listdir(path)
print(dir)
for i in dir:
    file = os.listdir(path + '\\' + i)
    for j in file:
        print(path + '\\' + i + '\\' + j)
        count += iter_count(path + '\\' + i + '\\' + j)
    
print(count)

222 6757 1741