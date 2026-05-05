# Coze Workflow Project - 文献雷达系统

基于 LangGraph 和 Coze 平台的企业级科研工作流/Agent 项目，实现多源学术文献采集、智能分析、个性化简报生成与邮件推送。本项目旨在提供一套高效、可扩展的 AI 工作流解决方案，帮助科研人员自动化追踪最新研究进展。

## 核心优势

- **多源采集**: 并行抓取 ArXiv、PubMed、Semantic Scholar 三大权威学术数据库
- **智能过滤**: 基于向量相似度的个性化推荐，自动去重合并
- **AI 分析**: LLM 驱动的三维评分系统（相关性、创新性、影响力）+ DOI 溯源
- **生产就绪**: 内置 HTTP API、SSE 实时推送、错误处理和日志追踪，适合生产环境部署
- **灵活扩展**: 模块化节点设计，支持快速添加新数据源、分析工具和自定义工作流

## 项目结构

```
.
├── src/                    # 源代码目录
│   ├── main.py            # 主入口文件（HTTP 服务/本地运行）
│   ├── graphs/            # LangGraph 工作流定义
│   │   ├── graph.py       # 图结构编排（多源采集→合并→过滤→分析→简报→邮件）
│   │   ├── state.py       # 状态管理（TypedDict + Pydantic 模型）
│   │   └── nodes/         # 节点实现
│   │       ├── fetch_arxiv_node.py      # ArXiv 论文抓取
│   │       ├── fetch_pubmed_node.py     # PubMed 论文抓取
│   │       ├── fetch_scholar_node.py    # Semantic Scholar 抓取
│   │       ├── merge_papers_node.py     # 合并去重
│   │       ├── embed_filter_node.py     # 向量相似度过滤
│   │       ├── agent_analysis_node.py   # LLM 三维评分分析
│   │       ├── generate_briefing_node.py # 个性化简报生成
│   │       └── send_email_node.py       # 邮件推送
│   ├── agents/            # Agent 实现
│   ├── tools/             # 工具函数
│   ├── storage/           # 存储层
│   └── utils/             # 通用工具
├── config/                # LLM 配置文件
│   ├── agent_analysis_llm_cfg.json    # 分析 Agent 配置
│   ├── generate_briefing_llm_cfg.json # 简报生成 Agent 配置
│   └── extract_news_llm_cfg.json      # 新闻提取配置
├── scripts/               # 脚本目录
│   ├── local_run.sh       # 本地运行脚本
│   ├── http_run.sh        # HTTP 服务启动脚本
│   ├── setup.sh           # 环境安装脚本
│   └── ...
├── assets/                # 资源文件
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

### 项目架构概述

本项目采用 **LangGraph** 构建多阶段科研工作流，整体流程为：

```
START → [并行] fetch_arxiv, fetch_pubmed, fetch_scholar 
      → merge_papers → embed_filter → agent_analysis 
      → generate_briefing → send_email → END
```

每个节点都是独立的函数模块，通过 `GlobalState` 共享状态数据。

### 核心概念

#### 1. 状态管理 (State)

项目使用 **Pydantic BaseModel** 定义类型安全的状态结构（`src/graphs/state.py`）:

- **GlobalState**: 全局工作流状态，包含用户配置、各阶段论文列表、分析结果等
- **GraphInput/GraphOutput**: 工作流的输入输出 schema
- **节点 Input/Output**: 每个节点都有明确的输入输出模型，便于类型检查和文档化

关键状态字段：
- `user_profile`: 用户科研画像（研究方向、关键词、关注学者）
- `arxiv_papers/pubmed_papers/scholar_papers`: 并行抓取结果
- `all_papers`: 合并去重后的全部论文
- `top_papers`: 向量过滤后的高相关度论文
- `analysis_result`: LLM 三维评分分析结果（JSON 格式）
- `content/email_subject`: 最终生成的简报内容和邮件主题

#### 2. 节点 (Nodes)

每个节点是一个异步或同步函数，遵循以下签名：

```python
async def node_name(state: NodeInput, config: RunnableConfig, runtime: Runtime) -> NodeOutput:
    """节点文档字符串"""
    # 业务逻辑
    return NodeOutput(...)
```

**节点分类**：
- **数据采集层**: `fetch_arxiv_node`, `fetch_pubmed_node`, `fetch_scholar_node`（并行执行）
- **数据处理层**: `merge_papers_node`（去重）, `embed_filter_node`（向量相似度过滤）
- **AI 分析层**: `agent_analysis_node`（LLM 三维评分）, `generate_briefing_node`（简报生成）
- **输出层**: `send_email_node`（邮件推送）

### 添加新节点

#### 步骤 1: 创建节点文件

在 `src/graphs/nodes/` 目录下创建新文件，例如 `fetch_new_source_node.py`:

```python
"""
新数据源抓取节点

功能描述
"""
import logging
from typing import List
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from graphs.state import FetchNewSourceInput, FetchNewSourceOutput, PaperInfo, UserProfile

logger = logging.getLogger(__name__)


async def fetch_new_source_node(
    state: FetchNewSourceInput,
    config: RunnableConfig,
    runtime: Runtime
) -> FetchNewSourceOutput:
    """
    从新数据源抓取论文
    
    Args:
        state: 节点输入（包含 user_profile）
        config: LangChain 运行配置
        runtime: LangGraph 运行时
        
    Returns:
        包含论文列表的输出对象
    """
    user_profile = state.user_profile
    logger.info(f"开始从新数据源抓取，关键词：{user_profile.keywords}")
    
    papers: List[PaperInfo] = []
    
    # TODO: 实现具体抓取逻辑
    # 示例：调用 API 或爬虫
    for keyword in user_profile.keywords:
        # 模拟抓取
        paper = PaperInfo(
            title=f"Example Paper about {keyword}",
            abstract="...",
            source="new_source",
            url="https://example.com/paper"
        )
        papers.append(paper)
    
    logger.info(f"抓取完成，共获取 {len(papers)} 篇论文")
    return FetchNewSourceOutput(new_source_papers=papers)
```

#### 步骤 2: 定义输入输出模型

在 `src/graphs/state.py` 中添加节点的 Input/Output 模型：

```python
class FetchNewSourceInput(BaseModel):
    """新数据源抓取节点输入"""
    user_profile: UserProfile = Field(..., description="用户科研画像")


class FetchNewSourceOutput(BaseModel):
    """新数据源抓取节点输出"""
    new_source_papers: List[PaperInfo] = Field(
        default_factory=list, 
        description="新数据源论文列表"
    )
```

并在 `GlobalState` 中添加对应字段：

```python
class GlobalState(BaseModel):
    # ... 现有字段 ...
    new_source_papers: List[PaperInfo] = Field(
        default_factory=list, 
        description="新数据源论文列表"
    )
```

#### 步骤 3: 注册节点到工作流

编辑 `src/graphs/graph.py`：

```python
from graphs.nodes.fetch_new_source_node import fetch_new_source_node

# 添加节点
builder.add_node("fetch_new_source", fetch_new_source_node)

# 添加到并行采集组（如果需要）
builder.add_edge(START, "fetch_new_source")
builder.add_edge(["fetch_arxiv", "fetch_pubmed", "fetch_scholar", "fetch_new_source"], "merge_papers")
```

**注意事项**：
- 节点函数必须是可调用对象（函数或类方法）
- 使用 `async/await` 处理 IO 密集型操作
- 添加充分的日志记录便于调试
- 捕获异常并返回有意义的错误信息

### 修改工作流编排

编辑 `src/graphs/graph.py` 调整节点连接关系：

```python
from langgraph.graph import StateGraph, END, START
from graphs.state import GlobalState, GraphInput, GraphOutput

builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)

# 添加节点
builder.add_node("node_a", node_a_func)
builder.add_node("node_b", node_b_func)

# 设置入口
builder.add_edge(START, "node_a")

# 顺序连接
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", END)

# 编译
main_graph = builder.compile()
```

#### 并行执行

多个节点可以从同一个起点并行执行：

```python
builder.add_edge(START, ["node_a", "node_b", "node_c"])
builder.add_edge(["node_a", "node_b", "node_c"], "merge_node")
```

#### 条件分支

根据状态动态选择下一个节点：

```python
def route_by_score(state: GlobalState) -> str:
    if len(state.top_papers) > 10:
        return "high_volume"
    return "low_volume"

builder.add_conditional_edges(
    source="embed_filter",
    condition=route_by_score,
    mapping={
        "high_volume": "summarize_node",
        "low_volume": "direct_send_node"
    }
)
```

### 配置 LLM Agent

Agent 节点需要配置文件（`config/*.json`）:

```json
{
  "model": "coze-api",
  "bot_id": "your_bot_id",
  "system_prompt": "你是一个科研助手，负责分析论文的相关性、创新性和影响力...",
  "temperature": 0.7,
  "max_tokens": 4096
}
```

在节点中加载配置：

```python
import json
from pathlib import Path

def load_llm_config(config_name: str) -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / config_name
    with open(config_path) as f:
        return json.load(f)
```

### 添加工具函数

在 `src/tools/` 目录下创建可复用的工具：

```python
# src/tools/paper_utils.py
import logging
import hashlib

logger = logging.getLogger(__name__)


def generate_paper_id(paper: PaperInfo) -> str:
    """基于 DOI 或标题生成唯一 ID"""
    if paper.doi:
        return hashlib.md5(paper.doi.encode()).hexdigest()[:12]
    return hashlib.md5(paper.title.encode()).hexdigest()[:12]


def deduplicate_papers(papers: List[PaperInfo]) -> List[PaperInfo]:
    """基于 DOI 或标题去重"""
    seen_ids = set()
    unique = []
    for paper in papers:
        paper_id = generate_paper_id(paper)
        if paper_id not in seen_ids:
            seen_ids.add(paper_id)
            unique.append(paper)
    logger.info(f"去重：{len(papers)} → {len(unique)}")
    return unique
```

在节点中使用：

```python
from src.tools.paper_utils import deduplicate_papers

def merge_papers_node(state: MergePapersInput) -> MergePapersOutput:
    all_papers = state.arxiv_papers + state.pubmed_papers + state.scholar_papers
    deduped = deduplicate_papers(all_papers)
    return MergePapersOutput(all_papers=deduped)
```

### 调试技巧

#### 1. 启用详细日志

```bash
export COZE_LOG_LEVEL=DEBUG
bash scripts/local_run.sh -m flow
```

#### 2. 单步执行工作流

```python
from graphs.graph import main_graph

input_data = {
    "to_email": "test@example.com",
    "user_profile": {
        "research_directions": ["深度学习"],
        "keywords": ["transformer", "attention mechanism"]
    }
}

# 查看每一步输出
for event in main_graph.stream(input_data, stream_mode="updates"):
    print(f"节点更新：{event}")
```

#### 3. 可视化工作流

```python
from graphs.graph import main_graph

# 生成 Mermaid 流程图
graph_png = main_graph.get_graph().draw_mermaid_png()
with open("workflow.png", "wb") as f:
    f.write(graph_png)
```

或使用在线 Mermaid 渲染器：

```python
print(main_graph.get_graph().draw_mermaid())
```

#### 4. 测试单个节点

```bash
# 运行特定节点（需要节点支持独立运行）
bash scripts/local_run.sh -m node -n fetch_arxiv -i '{"user_profile": {"keywords": ["deep learning"]}}'
```

### 最佳实践

- **类型安全**: 始终使用 Pydantic 模型定义输入输出，避免字典魔法键
- **错误隔离**: 每个节点内部捕获异常，防止单点故障导致整个工作流失败
- **日志规范**: 使用 `logging` 模块，记录关键决策点和外部调用
- **幂等性**: 确保节点可以重复执行而不产生副作用
- **配置分离**: API 密钥、模型参数等放入环境变量或配置文件
- **文档完整**: 为每个节点编写清晰的 docstring，说明输入输出和业务逻辑
- **单元测试**: 为核心工具函数和节点逻辑编写测试用例

### API 端点说明

启动 HTTP 服务后可用以下端点：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/run` | POST | 同步执行工作流 |
| `/api/stream` | POST | 流式执行（SSE） |
| `/health` | GET | 健康检查 |

**请求示例**：

```bash
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_SECRET_TOKEN" \
  -d '{
    "to_email": "user@example.com",
    "user_profile": {
      "research_directions": ["域自适应"],
      "keywords": ["domain adaptation", "few-shot learning"]
    }
  }'
```

## 技术栈

- **Python**: 3.12+
- **LangGraph**: 工作流编排和状态机管理
- **FastAPI**: 高性能 HTTP 服务框架
- **Coze SDK**: Coze 平台集成（Bot、LLM API）
- **Pydantic**: 数据验证和类型安全
- **uv**: 现代化的 Python 包管理器
- **cozeloop**: Coze Loop 运行时支持

## 许可证

本项目遵循内部使用许可。

## 常见问题

### Q: 如何查看日志？
A: 日志文件位于配置的日志目录，可通过 `COZE_LOG_LEVEL` 调整日志级别。

### Q: HTTP 服务无法启动？
A: 检查端口是否被占用，确认 `COZE_SECRET_TOKEN` 等环境变量已正确配置。

### Q: 如何调试单个节点？
A: 使用 `local_run.sh -m node -n <节点名>` 运行特定节点进行测试。

### Q: 如何添加新的数据源？
A: 
1. 在 `src/graphs/nodes/` 创建新的抓取节点
2. 在 `src/graphs/state.py` 定义输入输出模型和 GlobalState 字段
3. 在 `src/graphs/graph.py` 注册节点并添加到工作流

### Q: 向量相似度过滤如何工作？
A: `embed_filter_node` 使用嵌入模型将用户研究方向和论文摘要转换为向量，计算余弦相似度，返回最相关的 Top N 篇论文。

### Q: 如何自定义 LLM 分析维度？
A: 修改 `config/agent_analysis_llm_cfg.json` 中的 system prompt，调整评分维度和输出格式。

### Q: 邮件发送失败怎么办？
A: 检查 SMTP 服务器配置、发件人凭据和网络连接。错误信息会记录在日志中。

## 贡献指南

欢迎提交 Issue 和 Pull Request！在提交前请确保：

1. 代码通过现有测试
2. 新增功能附带单元测试
3. 更新相关文档
4. 遵循项目代码风格（PEP 8）
