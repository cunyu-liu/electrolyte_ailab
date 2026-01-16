cmake_minimum_required(VERSION 3.1)

project(surge)

set(CMAKE_C_STANDARD 99)

include_directories(${PROJECT_SOURCE_DIR}/include)
include_directories(${PROJECT_SOURCE_DIR}/libnauty)
include_directories(/usr/include)

# 解决struct tms结构体问题（全局设置）
add_definitions(-DHAVE_SYS_TIMES_H)
add_definitions(-DSTDC_HEADERS)

# 为 macOS 添加 __linux__ 宏（全局设置）
add_definitions(-D__linux__)

# 添加libnauty库
add_subdirectory(libnauty)

# 添加surge可执行文件
add_executable(surge ${PROJECT_SOURCE_DIR}/src/surge.c ${PROJECT_SOURCE_DIR}/src/geng.c ${PROJECT_SOURCE_DIR}/src/planarity.c)
set(EXECUTABLE_OUTPUT_PATH ${PROJECT_SOURCE_DIR}/bin)

# surge特定的宏定义（只应用于surge目标）
target_compile_definitions(surge PRIVATE 
    -DGENG_MAIN=geng_main
    -DOUTPROC=surgeproc
    -DSURGEPLUGIN="plugin.c"
    -DPRUNE=surgeprune
    -DWORDSIZE=32
    -DMAXN=WORDSIZE
)

# 链接libnauty库
target_link_libraries(surge nautyW1)