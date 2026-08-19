cmake_minimum_required(VERSION 3.22.1)
project(goar_terminal_bridge C)

add_library(goar_terminal_jni SHARED goar_terminal_jni.c)
find_library(log-lib log)
target_link_libraries(goar_terminal_jni ${log-lib})
