# Coze Workflow Project

基于 LangGraph 和 Coze 平台的工作流/Agent 项目，支持流式执行、HTTP 服务和多种运行模式。

## 项目结构

```
.
├── src/                    # 源代码目录
│   ├── main.py            # 主入口文件
│   ├── graphs/            # LangGraph 工作流定义
│   │   ├── graph.py       # 图结构定义
│   │   ├── state.py       # 状态管理
│   │   └── nodes/         # 节点实现
│   ├── agents/            # Agent 实现
│   ├── tools/             # 工具函数
│   ├── storage/           # 存储层
│   └── utils/             # 通用工具
├── scripts/               # 脚本目录
│   ├── local_run.sh       # 本地运行脚本
│   ├── http_run.sh        # HTTP 服务启动脚本
│   ├── setup.sh           # 环境安装脚本
│   └── ...
├── assets/                # 资源文件
├── config/                # 配置文件
├── pyproject.toml         # 项目依赖配置
└── requirements.txt       # pip 依赖列表
```

## 环境要求

- Python >= 3.12
- uv (推荐) 或 pip

## 快速开始

### 1. 安装依赖

使用 uv（推荐）:
```bash
bash scripts/setup.sh
```

或手动安装:
```bash
# 使用 uv
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置环境变量

项目需要以下环境变量:
- `COZE_WORKSPACE_PATH`: 项目工作目录路径
- `COZE_PROJECT_ENV`: 运行环境 (DEV/PROD)
- `COZE_SECRET_TOKEN`: API 认证密钥
- `TRIGGER_API_KEY`: HTTP Trigger 认证密钥

## 运行方式

### 本地运行

#### 运行完整工作流
```bash
bash scripts/local_run.sh -m flow
```

带输入参数:
```bash
bash scripts/local_run.sh -m flow -i '{"text": "你好"}'
```

#### 运行单个节点
```bash
bash scripts/local_run.sh -m node -n <节点名称>
```

示例:
```bash
bash scripts/local_run.sh -m node -n node_1 -i '{"text": "测试"}'
```

#### 运行 Agent
```bash
bash scripts/local_run.sh -m agent
```

### HTTP 服务

启动 HTTP 服务:
```bash
bash scripts/http_run.sh -p 8000
```

自定义端口:
```bash
bash scripts/http_run.sh -p 5000
```

### 命令行参数说明

`local_run.sh` 参数:
- `-m <模式>`: 运行模式 (http, flow, node, agent)
- `-n <节点 ID>`: 节点名称 (仅在 node 模式下需要)
- `-i <输入 JSON>`: 输入数据，支持 JSON 字符串或纯文本
- `-h`: 显示帮助信息

`http_run.sh` 参数:
- `-p <端口>`: HTTP 服务端口 (默认：8000)
- `-h`: 显示帮助信息

## 核心特性

- **LangGraph 支持**: 基于 LangGraph 构建复杂的工作流和状态机
- **流式执行**: 支持流式输出，实时反馈执行进度
- **HTTP API**: 提供 FastAPI 驱动的 RESTful API 接口
- **SSE 支持**: Server-Sent Events 实时推送
- **日志系统**: 完善的日志记录和错误追踪
- **错误分类**: 自动错误分类和处理
- **多模式运行**: 支持本地调试、HTTP 服务等多种运行模式

## 开发指南

### 添加新节点

在 `src/graphs/nodes/` 目录下创建新的节点文件:

```python
def my_node(state: dict) -> dict:
    # 节点逻辑
    return {"result": "value"}
```

### 修改工作流

编辑 `src/graphs/graph.py` 定义新的工作流结构。

### 添加工具

在 `src/tools/` 目录下添加工具函数供节点使用。

## 技术栈

- **Python**: 3.12+
- **LangGraph**: 工作流编排
- **FastAPI**: HTTP 服务框架
- **Coze SDK**: Coze 平台集成
- **uv**: 现代化的 Python 包管理器

## 许可证

本项目遵循内部使用许可。

## 常见问题

### Q: 如何查看日志？
A: 日志文件位于配置的日志目录，可通过 `COZE_LOG_LEVEL` 调整日志级别。

### Q: HTTP 服务无法启动？
A: 检查端口是否被占用，确认 `COZE_SECRET_TOKEN` 等环境变量已正确配置。

### Q: 如何调试单个节点？
A: 使用 `local_run.sh -m node -n <节点名>` 运行特定节点进行测试。
