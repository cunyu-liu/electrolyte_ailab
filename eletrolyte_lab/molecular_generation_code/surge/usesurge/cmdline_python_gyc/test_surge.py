
import os
import subprocess

surge_path = '../bin/surge'
surge_path = os.path.abspath(surge_path)
cmdline_list = [surge_path, '-S', '-Y', '-B1,2,3,4,5,6,7,8,9', 'C6H12O', '-otest.smi']
out = subprocess.run(cmdline_list)
# print(out.returncode)
# print(out.stderr)
# with open('info', 'wb') as f:
#     f.write(out.stderr)


# import subprocess

# def call_surge():
#     # 定义要执行的命令和参数
#     cmd = "../bin/surge"
#     args = ["-S", "-Y", "-B1,2,3,4,5,6,7,8,9", "C6H12O", "-otest.smi"]

#     # 使用subprocess调用命令
#     subprocess.run([cmd] + args)

# if __name__ == "__main__":
#     call_surge()
