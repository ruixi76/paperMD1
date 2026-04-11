"""
向量相似度过滤节点

使用Embedding模型计算论文与用户画像的语义相似度，过滤Top论文
"""
import logging
import math
from typing import List
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import EmbeddingClient

from graphs.state import EmbedFilterInput, EmbedFilterOutput, PaperInfo, UserProfile

logger = logging.getLogger(__name__)

TOP_K = 10  # 保留Top 10论文


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """计算两个向量的余弦相似度（纯Python实现，无需numpy）"""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _build_profile_text(user_profile: UserProfile) -> str:
    """构建用户画像文本用于Embedding"""
    parts = []
    if user_profile.research_directions:
        parts.append("研究方向: " + ", ".join(user_profile.research_directions))
    if user_profile.keywords:
        parts.append("关键词: " + ", ".join(user_profile.keywords))
    if user_profile.preferred_authors:
        parts.append("关注学者: " + ", ".join(user_profile.preferred_authors))
    return " | ".join(parts) if parts else "artificial intelligence, deep learning"


def embed_filter_node(
    state: EmbedFilterInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> EmbedFilterOutput:
    """
    title: 向量相似度过滤
    desc: 使用Embedding模型计算论文与用户科研画像的语义相似度，筛选Top10论文
    integrations: Embedding
    """
    ctx = runtime.context

    if not state.all_papers:
        logger.warning("无论文可供过滤")
        return EmbedFilterOutput(top_papers=[])

    try:
        client = EmbeddingClient()

        # 1. Embed用户画像
        profile_text = _build_profile_text(state.user_profile)
        profile_embedding = client.embed_text(profile_text)

        # 2. 批量Embed论文摘要
        paper_texts = []
        for paper in state.all_papers:
            # 组合标题+摘要作为论文文本
            text = f"{paper.title}. {paper.abstract}" if paper.abstract else paper.title
            paper_texts.append(text[:1000])  # 截断过长文本

        # 分批处理（每批最多50条）
        batch_size = 50
        all_embeddings = []
        for i in range(0, len(paper_texts), batch_size):
            batch = paper_texts[i:i + batch_size]
            batch_embeddings = client.embed_texts(batch)
            all_embeddings.extend(batch_embeddings)

        # 3. 计算余弦相似度并排序
        scored_papers = []
        for idx, paper_embedding in enumerate(all_embeddings):
            similarity = _cosine_similarity(profile_embedding, paper_embedding)
            scored_papers.append((state.all_papers[idx], similarity))

        scored_papers.sort(key=lambda x: x[1], reverse=True)

        # 4. 取Top K
        top_k = min(TOP_K, len(scored_papers))
        top_papers = [paper for paper, score in scored_papers[:top_k]]

        logger.info(f"向量过滤完成: {len(state.all_papers)} → {len(top_papers)} 篇 (相似度范围: {scored_papers[0][1]:.4f} ~ {scored_papers[top_k-1][1]:.4f})")
        return EmbedFilterOutput(top_papers=top_papers)

    except Exception as e:
        logger.error(f"向量过滤失败: {e}，返回全部论文（最多10篇）")
        fallback_papers = state.all_papers[:TOP_K]
        return EmbedFilterOutput(top_papers=fallback_papers)
