#!/bin/bash

set -e
# 导出环境变量

WORK_DIR="${COZE_WORKSPACE_PATH:-.}"
PORT=8000

# ========== 项目环境变量配置 ==========
# HTTP Trigger 认证密钥
export COZE_SECRET_TOKEN="pat_OaCeTBcACFZIxfjIDIokMn1TvVqFoerrUA64Ena8PJVpVBEwmeA6ehDtYCOHIRJQ"
export TRIGGER_API_KEY="${COZE_SECRET_TOKEN}"
# ========================================

usage() {
  echo "用法: $0 -p <端口>"
}

while getopts "p:h" opt; do
  case "$opt" in
    p)
      PORT="$OPTARG"
      ;;
    h)
      usage
      exit 0
      ;;
    \?)
      echo "无效选项: -$OPTARG"
      usage
      exit 1
      ;;
  esac
done


python ${WORK_DIR}/src/main.py -m http -p $PORT
