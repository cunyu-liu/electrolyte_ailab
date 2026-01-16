import os

# def read_in_chunks(filePath, chunk_size=1024*1024):
#     """
#     Lazy function (generator) to read a file piece by piece.
#     Default chunk size: 1M
#     You can set your own chunk size 
#     """
#     file_object = open(filePath)
#     while True:
#         chunk_data = file_object.read(chunk_size)
#         if not chunk_data:
#             break
#         yield chunk_data

# count = 0
# path = '.\\test_gdb\\C4O10\\C4O10H10.smi'

# for chunk in read_in_chunks('.\\test_gdb\\C4O10\\1'):
#     print(len(list(chunk)))
#     print(list(chunk))
#     count+=1
# print(count)

def iter_count(file_name):
    from itertools import (takewhile, repeat)
    buffer = 1024 * 1024
    with open(file_name) as f:
        buf_gen = takewhile(lambda x: x, (f.read(buffer) for _ in repeat(None)))
        return sum(buf.count('\n') for buf in buf_gen)

print(iter_count('.\\test_gdb\\C4O10\\C4O10H10.smi'))