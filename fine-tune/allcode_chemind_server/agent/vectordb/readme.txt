执行建议
先在一个终端运行 python step1_cpu_parser.py。你会看到 CPU 占用率飙升，风扇狂转。

等待解析完成（或者解析一部分后），在另一个终端运行 python step2_gpu_loader.py。

对于 30 万文件，建议把 Config.OUTPUT_DIR 放在 SSD 上，否则写入小文件会成为瓶颈。