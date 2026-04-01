# AI新闻自动推送工作流

## 项目概述
- **名称**: AI News Daily Digest
- **功能**: 每天早上自动抓取AI行业新闻，提取三条最关键的内容发送到用户邮箱

## 工作流结构
```
search_news → extract_key_news → send_email → END
```

### 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 配置文件 |
|-------|---------|------|---------|---------|
| search_news | `nodes/search_news_node.py` | task | 搜索AI行业最新新闻 | - |
| extract_key_news | `nodes/extract_key_news_node.py` | agent | 提取3条最关键内容并格式化 | `config/extract_news_llm_cfg.json` |
| send_email | `nodes/send_email_node.py` | task | 发送邮件到用户邮箱 | - |

**类型说明**: task(任务节点) / agent(大模型) / condition(条件分支) / looparray(列表循环) / loopcond(条件循环)

## 状态定义

### 全局状态 (GlobalState)
| 字段 | 类型 | 说明 |
|-----|------|------|
| to_email | str | 收件人邮箱地址 |
| search_query | str | 搜索关键词 |
| raw_news | List[dict] | 搜索返回的原始新闻列表 |
| formatted_news | str | 格式化后的新闻内容 |

### 图输入 (GraphInput)
| 字段 | 类型 | 说明 |
|-----|------|------|
| to_email | str | 收件人邮箱地址 |
| search_query | str | 搜索关键词（可选，默认"AI 人工智能 行业新闻"） |

### 图输出 (GraphOutput)
| 字段 | 类型 | 说明 |
|-----|------|------|
| success | bool | 是否执行成功 |
| message | str | 执行结果消息 |
| news_count | int | 处理的新闻数量 |

## 技能使用
- 节点`search_news`使用技能 **Web Search** - 搜索AI行业最新新闻
- 节点`extract_key_news`使用技能 **大语言模型** - 提取关键内容和格式化
- 节点`send_email`使用技能 **Email** - 发送邮件

## 调用方式

### Python调用
```python
from graphs.graph import main_graph, GraphInput

# 初始化输入
graph_input = GraphInput(
    to_email="user@example.com",
    search_query="AI 人工智能 行业新闻"
)

# 执行工作流
result = main_graph.invoke(graph_input)

# 获取结果
print(result)
```

### 定时触发（每日8点）
通过外部调度系统（如cron）调用上述Python代码即可实现每日定时推送。
