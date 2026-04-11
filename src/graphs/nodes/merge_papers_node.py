"""
论文合并去重节点

合并三个数据源的论文，并按标题去重
"""
import logging
from typing import List
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import MergePapersInput, MergePapersOutput, PaperInfo

logger = logging.getLogger(__name__)


def _normalize_title(title: str) -> str:
    """标准化标题用于去重比较"""
    normalized = title.lower().strip()
    # 移除多余空白
    import re
    normalized = re.sub(r'\s+', ' ', normalized)
    # 移除标点
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized


def _titles_are_similar(title1: str, title2: str) -> bool:
    """判断两个标题是否相似（简单词级Jaccard相似度）"""
    norm1 = _normalize_title(title1)
    norm2 = _normalize_title(title2)

    if norm1 == norm2:
        return True

    words1 = set(norm1.split())
    words2 = set(norm2.split())

    if not words1 or not words2:
        return False

    intersection = words1 & words2
    union = words1 | words2

    jaccard = len(intersection) / len(union)
    return jaccard >= 0.8


def merge_papers_node(
    state: MergePapersInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> MergePapersOutput:
    """
    title: 论文合并去重
    desc: 合并ArXiv、PubMed、Semantic Scholar三个数据源的论文，按标题相似度去重
    """
    ctx = runtime.context

    # 合并所有论文
    all_papers = []
    all_papers.extend(state.arxiv_papers)
    all_papers.extend(state.pubmed_papers)
    all_papers.extend(state.scholar_papers)

    logger.info(f"合并前总数: {len(all_papers)} 篇 (ArXiv:{len(state.arxiv_papers)}, PubMed:{len(state.pubmed_papers)}, Scholar:{len(state.scholar_papers)})")

    # 按标题相似度去重
    unique_papers: List[PaperInfo] = []
    seen_titles: List[str] = []

    for paper in all_papers:
        if not paper.title:
            continue

        is_duplicate = False
        for seen_title in seen_titles:
            if _titles_are_similar(paper.title, seen_title):
                is_duplicate = True
                break

        if not is_duplicate:
            unique_papers.append(paper)
            seen_titles.append(_normalize_title(paper.title))

    logger.info(f"去重后总数: {len(unique_papers)} 篇")
    return MergePapersOutput(all_papers=unique_papers)
