cmake_minimum_required(VERSION 3.22)

project(surge)

set(CMAKE_C_STANDARD 99)

include_directories(${PROJECT_SOURCE_DIR}/libnauty)

add_definitions(-DGENG_MAIN=geng_main)
add_definitions(-DOUTPROC=surgeproc)
add_definitions(-DPRUNE=surgeprune)
add_definitions(-DPRUNE=surgepreprune)
add_definitions(-DWORDSIZE=32)
add_definitions(-DMAXN=WORDSIZE)


add_executable(surge ${PROJECT_SOURCE_DIR}/src/surge.c ${PROJECT_SOURCE_DIR}/src/geng.c ${PROJECT_SOURCE_DIR}/src/planarity.c)
set(EXECUTABLE_OUTPUT_PATH ${PROJECT_SOURCE_DIR}/bin)

target_link_libraries(surge ${PROJECT_SOURCE_DIR}/libnauty/nautyW1.a)