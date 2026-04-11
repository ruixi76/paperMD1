"""
主图编排

基于Agent的个性化科研伴侣：文献雷达系统
多源采集 → 合并去重 → 向量过滤 → 三维评分 → 简报生成 → 邮件推送
"""
from langgraph.graph import StateGraph, END, START
from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
)
from graphs.nodes.fetch_arxiv_node import fetch_arxiv_node
from graphs.nodes.fetch_pubmed_node import fetch_pubmed_node
from graphs.nodes.fetch_scholar_node import fetch_scholar_node
from graphs.nodes.merge_papers_node import merge_papers_node
from graphs.nodes.embed_filter_node import embed_filter_node
from graphs.nodes.agent_analysis_node import agent_analysis_node
from graphs.nodes.generate_briefing_node import generate_briefing_node
from graphs.nodes.send_email_node import send_email_node


# ========== 构建主图 ==========

builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)

# ---------- 添加节点 ----------

# 数据采集层（并行）
builder.add_node("fetch_arxiv", fetch_arxiv_node)
builder.add_node("fetch_pubmed", fetch_pubmed_node)
builder.add_node("fetch_scholar", fetch_scholar_node)

# 合并去重
builder.add_node("merge_papers", merge_papers_node)

# 向量相似度过滤
builder.add_node("embed_filter", embed_filter_node)

# 三维评分 + DOI溯源（Agent节点）
builder.add_node("agent_analysis", agent_analysis_node, metadata={
    "type": "agent",
    "llm_cfg": "config/agent_analysis_llm_cfg.json"
})

# 个性化简报生成（Agent节点）
builder.add_node("generate_briefing", generate_briefing_node, metadata={
    "type": "agent",
    "llm_cfg": "config/generate_briefing_llm_cfg.json"
})

# 邮件推送
builder.add_node("send_email", send_email_node)

# ---------- 添加边 ----------

# 并行入口：START → 三个数据采集节点
builder.add_edge(START, "fetch_arxiv")
builder.add_edge(START, "fetch_pubmed")
builder.add_edge(START, "fetch_scholar")

# 并行汇聚：三个采集节点 → 合并去重
builder.add_edge(["fetch_arxiv", "fetch_pubmed", "fetch_scholar"], "merge_papers")

# 顺序处理链
builder.add_edge("merge_papers", "embed_filter")
builder.add_edge("embed_filter", "agent_analysis")
builder.add_edge("agent_analysis", "generate_briefing")
builder.add_edge("generate_briefing", "send_email")
builder.add_edge("send_email", END)

# ---------- 编译图 ----------

main_graph = builder.compile()
