#!/bin/bash

set -e
# 导出环境变量

WORK_DIR="${COZE_WORKSPACE_PATH:-.}"
PORT=8000

# ========== 项目环境变量配置 ==========
# HTTP Trigger 认证密钥：引用 Coze 平台配置的 Secret Token 环境变量
# 请在 Coze 平台「项目设置 → 环境变量」中添加：
#   Key: COZE_SECRET_TOKEN
#   Value: 你的个人访问令牌 (pat_...)
export TRIGGER_API_KEY="${COZE_SECRET_TOKEN:-}"
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
