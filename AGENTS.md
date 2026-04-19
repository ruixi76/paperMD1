# 基于Agent的个性化科研伴侣：文献雷达系统

## 项目概述
- **名称**: 文献雷达 (Literature Radar)
- **功能**: 多源采集科研文献 → 全文搜索GitHub代码 → 向量相似度过滤 → 三维评分+DOI溯源+代码可用性 → 固定配额(2高+3推荐+5关注) → 个性化简报 → 邮件推送

## 工作流结构 (DAG)
```
                       ┌─ fetch_arxiv ──┐
START ─────────────────┼─ fetch_pubmed ─┼──→ merge_papers ──→ embed_filter ──→ agent_analysis ──→ generate_briefing ──→ send_email ──→ END
                       └─ fetch_scholar─┘
     [并行3路采集]         [合并去重]     [向量过滤]      [三维评分]        [简报生成]        [邮件推送]
```

### 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 配置文件 |
|-------|---------|------|---------|---------|
| fetch_arxiv | `nodes/fetch_arxiv_node.py` | task | ArXiv API抓取+全文搜索GitHub链接 | - |
| fetch_pubmed | `nodes/fetch_pubmed_node.py` | task | PubMed E-utilities抓取+全文搜索GitHub链接 | - |
| fetch_scholar | `nodes/fetch_scholar_node.py` | task | Semantic Scholar API抓取+全文搜索GitHub链接 | - |
| merge_papers | `nodes/merge_papers_node.py` | task | 合并三源论文+标题相似度去重 | - |
| embed_filter | `nodes/embed_filter_node.py` | task | Embedding向量相似度过滤Top15 | - |
| agent_analysis | `nodes/agent_analysis_node.py` | agent | 三维评分+DOI溯源+代码可用性+固定配额(2+3+5) | `config/agent_analysis_llm_cfg.json` |
| generate_briefing | `nodes/generate_briefing_node.py` | agent | 个性化HTML简报生成 | `config/generate_briefing_llm_cfg.json` |
| send_email | `nodes/send_email_node.py` | task | HTML格式邮件推送 | - |

**类型说明**: task(任务节点) / agent(大模型) / condition(条件分支) / looparray(列表循环) / loopcond(条件循环)

## 核心架构

### 三维评分体系
| 维度 | 英文 | 评分范围 | 说明 |
|------|------|---------|------|
| 创新性 | Innovation | 1-10 | 方法/理论新颖程度 |
| 相关性 | Relevance | 1-10 | 与用户研究方向契合度 |
| 可行性 | Feasibility | 1-10 | 代码/数据可复现性 |

### 优先级分类（固定配额）
| 优先级 | 数量 | 条件 |
|-------|------|------|
| 🔴 HIGH | 2篇 | 总分≥24且相关性≥8，有代码优先 |
| 🟡 RECOMMENDED | 3篇 | 总分18-23或相关性≥7，有代码优先 |
| 🟢 WATCH | 5篇 | 总分<18但有创新亮点 |

### GitHub代码链接搜索
- 每篇论文搜索优先级：已有code_url → 摘要正则 → ArXiv HTML全文/ PubMed文章页/ Scholar论文页
- 有无代码纳入优先级评估（有代码的论文优先级上调一档）

### 防幻觉机制
1. **来源溯源校验**: 格式校验+来源URL验证（DOI格式/ArXiv/PubMed/Scholar来源）
2. **Self-Check**: LLM自检评分是否与原文摘要一致
3. **禁止编造**: SP中明确约束仅基于摘要评分

## 状态定义

### 全局状态 (GlobalState)
| 字段 | 类型 | 说明 |
|-----|------|------|
| to_email | str | 收件人邮箱 |
| user_profile | UserProfile | 用户科研画像 |
| arxiv_papers | List[PaperInfo] | ArXiv论文列表 |
| pubmed_papers | List[PaperInfo] | PubMed论文列表 |
| scholar_papers | List[PaperInfo] | Semantic Scholar论文列表 |
| all_papers | List[PaperInfo] | 合并去重后论文 |
| top_papers | List[PaperInfo] | 向量过滤后Top论文 |
| analysis_result | str | 三维评分分析结果 |
| content | str | 简报HTML内容 |
| email_subject | str | 邮件主题 |

### 图输入 (GraphInput)
| 字段 | 类型 | 说明 |
|-----|------|------|
| to_email | str | 收件人邮箱 |
| user_profile | UserProfile | 用户科研画像（研究方向+关键词+关注学者） |

### 图输出 (GraphOutput)
| 字段 | 类型 | 说明 |
|-----|------|------|
| success | bool | 是否执行成功 |
| message | str | 执行结果消息 |
| papers_count | int | 论文总数 |
| top_papers_count | int | 筛选后论文数 |

## 技能使用
- 节点`fetch_arxiv`使用 **ArXiv API** - 抓取CS/AI领域论文
- 节点`fetch_pubmed`使用 **PubMed API** - 抓取医学影像文献
- 节点`fetch_scholar`使用 **Semantic Scholar API** - 抓取工程/物理文献
- 节点`embed_filter`使用 **Embedding** - 向量相似度计算与过滤
- 节点`agent_analysis`使用 **大语言模型** - 三维评分+DOI溯源+Self-Check
- 节点`generate_briefing`使用 **大语言模型** - 个性化HTML简报生成
- 节点`send_email`使用 **Email** - SMTP邮件推送

## 调用方式

### HTTP Trigger（推荐）
```bash
# POST /run （Coze平台部署域名可用）
curl -X POST http://9rhxdv55k2.coze.site/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer my-secret-key-2024" \
  -d '{
    "to_email": "user@example.com",
    "user_profile": {
      "research_directions": ["域自适应", "太赫兹", "医学图像处理"],
      "keywords": ["domain adaptation", "terahertz imaging", "medical image segmentation"],
      "preferred_authors": []
    }
  }'
```

**认证说明**：
- `/run` 端点已集成 Bearer Token 认证（智能策略）
- 通过环境变量 `TRIGGER_API_KEY` 配置密钥（在 `scripts/http_run.sh` 中设置）
- **无 Authorization 头** → 放行（兼容 Coze 平台内部调用）
- **有 Authorization 头** → 必须验证 Bearer Token 有效性
- 未设置 `TRIGGER_API_KEY` 时跳过所有认证（开发模式）

**请求参数**：
| 字段 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| to_email | string | ✅ | 收件人邮箱地址 |
| user_profile.research_directions | array | ✅* | 研究方向列表 |
| user_profile.keywords | array | ✅* | 搜索关键词列表 |
| user_profile.preferred_authors | array | - | 关注学者列表 |

> *research_directions 和 keywords 至少需提供一个

### Python调用
```python
from graphs.graph import main_graph
from graphs.state import GraphInput, UserProfile

graph_input = GraphInput(
    to_email="user@example.com",
    user_profile=UserProfile(
        research_directions=["域自适应", "太赫兹", "医学图像处理"],
        keywords=["domain adaptation", "terahertz imaging", "medical image segmentation"],
        preferred_authors=[]
    )
)

result = main_graph.invoke(graph_input)
```

### 定时触发（每日8点）
通过外部调度系统（如cron）每日8:00调用上述代码实现定时推送。
