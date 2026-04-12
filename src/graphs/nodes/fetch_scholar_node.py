"""
Semantic Scholar论文抓取节点

通过Semantic Scholar API获取太赫兹/电子工程领域文献，全文搜索GitHub代码链接
"""
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from typing import List, Optional
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import FetchScholarInput, FetchScholarOutput, PaperInfo, UserProfile

logger = logging.getLogger(__name__)

SCHOLAR_API_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"

GITHUB_PATTERN = re.compile(r'(https?://github\.com/[\w\-]+/[\w\-\.]+)')


def _search_github_in_text(text: str) -> str:
    """从文本中搜索GitHub链接，返回第一个匹配"""
    if not text:
        return ""
    match = GITHUB_PATTERN.search(text)
    return match.group(1) if match else ""


def _fetch_page_text(url: str, timeout: int = 10) -> str:
    """抓取网页全文内容（用于搜索GitHub链接）"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LiteratureRadar/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _build_scholar_query(user_profile: UserProfile) -> str:
    """根据用户画像构建Semantic Scholar搜索查询"""
    keywords = user_profile.keywords
    directions = user_profile.research_directions

    search_terms = [kw.strip() for kw in keywords if kw.strip()]

    for direction in directions:
        d = direction.strip().lower()
        if "太赫兹" in d or "terahertz" in d:
            search_terms.extend(["terahertz imaging", "terahertz detection"])
        if "域自适应" in d or "domain adaptation" in d:
            search_terms.extend(["domain adaptation", "transfer learning"])
        if "医学" in d or "medical" in d:
            search_terms.extend(["medical image analysis", "clinical AI"])

    if not search_terms:
        search_terms = ["artificial intelligence", "deep learning"]

    return " ".join(search_terms[:5])


def _enrich_code_url(paper: PaperInfo) -> PaperInfo:
    """
    全文搜索GitHub代码链接
    优先级：已有code_url > 摘要搜索 > Semantic Scholar论文页面全文搜索
    """
    # 1. 已有则直接返回
    if paper.code_url:
        return paper

    # 2. 摘要搜索
    code_url = _search_github_in_text(paper.abstract)
    if code_url:
        return PaperInfo(**{**paper.model_dump(), "code_url": code_url})

    # 3. Semantic Scholar论文页面全文搜索
    if paper.url:
        page_text = _fetch_page_text(paper.url, timeout=8)
        code_url = _search_github_in_text(page_text)
        if code_url:
            logger.info(f"Scholar全文搜索到GitHub: {paper.title[:40]}... → {code_url}")
            return PaperInfo(**{**paper.model_dump(), "code_url": code_url})

    return paper


def _parse_scholar_paper(paper_data: dict) -> PaperInfo:
    """解析单个Semantic Scholar论文"""
    title = paper_data.get("title", "")
    abstract = paper_data.get("abstract", "")
    if abstract is None:
        abstract = ""

    authors = []
    for author_obj in paper_data.get("authors", []):
        name = author_obj.get("name", "")
        if name:
            authors.append(name)

    external_ids = paper_data.get("externalIds", {}) or {}
    doi = external_ids.get("DOI", "")
    if doi is None:
        doi = ""

    url = paper_data.get("url", "")
    if not url and doi:
        url = f"https://doi.org/{doi}"

    publish_date = paper_data.get("publicationDate", "")
    if publish_date is None:
        publish_date = ""

    # 从摘要中提取GitHub代码链接
    code_url = _search_github_in_text(abstract)

    return PaperInfo(
        title=title,
        abstract=abstract,
        authors=authors,
        doi=doi,
        url=url,
        source="semantic_scholar",
        publish_date=publish_date,
        categories=[],
        code_url=code_url
    )


def fetch_scholar_node(
    state: FetchScholarInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> FetchScholarOutput:
    """
    title: Semantic Scholar文献抓取
    desc: 通过Semantic Scholar API获取工程与物理领域最新文献，全文搜索GitHub代码链接
    integrations: Semantic Scholar API
    """
    ctx = runtime.context

    try:
        query = _build_scholar_query(state.user_profile)
        params = urllib.parse.urlencode({
            "query": query,
            "limit": 20,
            "fields": "title,abstract,authors,externalIds,url,publicationDate"
        })
        url = f"{SCHOLAR_API_BASE}?{params}"

        logger.info(f"Semantic Scholar API请求: {url}")

        req = urllib.request.Request(url, headers={"User-Agent": "LiteratureRadar/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

        papers = []
        for paper_data in data.get("data", []):
            try:
                paper = _parse_scholar_paper(paper_data)
                if paper.title:
                    papers.append(paper)
            except Exception as e:
                logger.warning(f"解析Semantic Scholar论文失败: {e}")
                continue

        # 全文搜索GitHub链接（对无code_url的论文补充搜索）
        enriched_papers = []
        for paper in papers:
            if paper.code_url:
                enriched_papers.append(paper)
            else:
                enriched_papers.append(_enrich_code_url(paper))

        code_count = sum(1 for p in enriched_papers if p.code_url)
        logger.info(f"Semantic Scholar抓取成功: {len(enriched_papers)} 篇论文, {code_count} 篇含代码链接")
        return FetchScholarOutput(scholar_papers=enriched_papers)

    except Exception as e:
        logger.error(f"Semantic Scholar抓取失败: {e}")
        return FetchScholarOutput(scholar_papers=[])
