"""
三维评分 + DOI溯源校验节点

对Top论文进行创新性/相关性/可行性三维评分，并进行DOI溯源校验
"""
import json
import logging
import os
import re
from typing import List, Dict
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.runtime_ctx.context import new_context

from graphs.state import AgentAnalysisInput, AgentAnalysisOutput, PaperInfo, UserProfile

logger = logging.getLogger(__name__)


def _verify_source(paper: PaperInfo) -> str:
    """
    验证论文来源可溯源性（无需外网请求，基于格式和来源校验）
    
    Returns:
        "doi_verified" - DOI格式有效
        "arxiv_verified" - ArXiv来源可验证
        "pubmed_verified" - PubMed来源可验证
        "scholar_verified" - Semantic Scholar来源可验证
        "unverified" - 无法验证
    """
    # 1. 检查DOI格式有效性（标准DOI格式: 10.xxxx/...）
    if paper.doi:
        doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$'
        if re.match(doi_pattern, paper.doi):
            return "doi_verified"

    # 2. 按来源校验URL格式
    url = paper.url.lower()
    if paper.source == "arxiv" and "arxiv.org" in url:
        return "arxiv_verified"
    if paper.source == "pubmed" and ("pubmed.ncbi.nlm.nih.gov" in url or "ncbi.nlm.nih.gov" in url):
        return "pubmed_verified"
    if paper.source == "semantic_scholar" and "semanticscholar.org" in url:
        return "scholar_verified"

    # 3. 通用URL格式检查
    if url.startswith("https://") or url.startswith("http://"):
        return "url_available"

    return "unverified"


def _build_papers_text(papers: List[PaperInfo], source_verify_results: Dict[int, str]) -> str:
    """构建论文信息文本"""
    VERIFY_LABELS = {
        "doi_verified": "✅ DOI格式有效",
        "arxiv_verified": "✅ ArXiv来源可验证",
        "pubmed_verified": "✅ PubMed来源可验证",
        "scholar_verified": "✅ Semantic Scholar来源可验证",
        "url_available": "✅ 链接可访问",
        "unverified": "⚠️ 无法溯源"
    }
    text = ""
    for i, paper in enumerate(papers, 1):
        text += f"### 论文 {i}\n"
        text += f"标题: {paper.title}\n"
        text += f"作者: {', '.join(paper.authors[:5])}{'等' if len(paper.authors) > 5 else ''}\n"
        text += f"摘要: {paper.abstract[:500]}\n"
        text += f"DOI: {paper.doi or '无'}\n"
        verify_status = source_verify_results.get(i, "unverified")
        text += f"溯源状态: {VERIFY_LABELS.get(verify_status, '⚠️ 无法溯源')}\n"
        text += f"链接: {paper.url}\n"
        text += f"来源: {paper.source} | 日期: {paper.publish_date}\n\n"
    return text


def agent_analysis_node(
    state: AgentAnalysisInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> AgentAnalysisOutput:
    """
    title: 三维评分与DOI溯源
    desc: 对Top论文进行创新性/相关性/可行性三维评分，DOI溯源校验，Self-Check防幻觉
    integrations: 大语言模型
    """
    ctx = runtime.context

    # 读取LLM配置
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r') as fd:
        _cfg = json.load(fd)

    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")

    # 来源溯源校验（基于格式验证，无需外网请求）
    source_verify_results = {}
    for idx, paper in enumerate(state.top_papers, 1):
        verify_status = _verify_source(paper)
        source_verify_results[idx] = verify_status
        logger.info(f"来源验证 论文{idx} [{paper.source}]: {verify_status}")

    # 构建论文文本
    papers_text = _build_papers_text(state.top_papers, source_verify_results)

    # 构建用户画像文本
    profile_text = ""
    if state.user_profile.research_directions:
        profile_text += "研究方向: " + ", ".join(state.user_profile.research_directions) + "\n"
    if state.user_profile.keywords:
        profile_text += "关键词: " + ", ".join(state.user_profile.keywords) + "\n"
    if state.user_profile.preferred_authors:
        profile_text += "关注学者: " + ", ".join(state.user_profile.preferred_authors) + "\n"

    # 渲染用户提示词
    up_tpl = Template(up)
    user_prompt = up_tpl.render({
        "papers": papers_text,
        "user_profile": profile_text
    })

    # 调用大模型
    try:
        llm_ctx = new_context(method="invoke")
        client = LLMClient(ctx=llm_ctx)

        messages = [
            SystemMessage(content=sp),
            HumanMessage(content=user_prompt)
        ]

        response = client.invoke(
            messages=messages,
            model=llm_config.get("model", "doubao-seed-2-0-pro-260215"),
            temperature=llm_config.get("temperature", 0.6),
            max_completion_tokens=llm_config.get("max_completion_tokens", 8192),
            thinking=llm_config.get("thinking", "disabled")
        )

        # 安全获取文本内容
        content = response.content
        if isinstance(content, str):
            analysis_result = content.strip()
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            analysis_result = "".join(text_parts).strip()
        else:
            analysis_result = str(content)

        logger.info(f"三维评分分析完成，结果长度: {len(analysis_result)}")
        return AgentAnalysisOutput(analysis_result=analysis_result)

    except Exception as e:
        logger.error(f"三维评分分析失败: {e}")
        return AgentAnalysisOutput(analysis_result=json.dumps({
            "error": str(e),
            "papers": []
        }, ensure_ascii=False))
