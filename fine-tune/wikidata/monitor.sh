#!/bin/bash

# 配置项
SCRIPT_PATH="/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/wikidata/getWiki.py"
LOG_PATH="/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/wikidata/crawler.log"
MONITOR_LOG="/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/wikidata/monitor.log"

while true
do
    # 检查进程是否存在 (排除 grep 进程本身)
    count=$(ps -ef | grep "$SCRIPT_PATH" | grep -v "grep" | wc -l)

    if [ $count -eq 0 ]; then
        echo "[$(date)] 警告：爬虫进程已停止，正在尝试重启..." >> "$MONITOR_LOG"
        # 执行启动命令
        nohup python -u "$SCRIPT_PATH" >> "$LOG_PATH" 2>&1 &
        echo "[$(date)] 消息：爬虫已重启。" >> "$MONITOR_LOG"
    else
        # 进程正常，记录心跳（可选）
        echo "[$(date)] 状态：爬虫运行中..." >> "$MONITOR_LOG"
    fi

    # 每隔 60 秒检查一次
    sleep 6
done