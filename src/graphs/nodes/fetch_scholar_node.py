"""
Semantic Scholar论文抓取节点

通过Semantic Scholar API获取太赫兹/电子工程领域文献
"""
import json
import logging
import time
import urllib.parse
import urllib.request
from typing import List
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import FetchScholarInput, FetchScholarOutput, PaperInfo, UserProfile

logger = logging.getLogger(__name__)

SCHOLAR_API_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"


def _build_scholar_query(user_profile: UserProfile) -> str:
    """根据用户画像构建Semantic Scholar搜索查询"""
    keywords = user_profile.keywords
    directions = user_profile.research_directions

    search_terms = [kw.strip() for kw in keywords if kw.strip()]

    # 补充研究方向相关关键词
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
    code_url = ""
    if abstract:
        import re
        github_match = re.search(r'(https?://github\.com/[\w\-]+/[\w\-]+)', abstract)
        if github_match:
            code_url = github_match.group(1)

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
    desc: 通过Semantic Scholar API获取工程与物理领域最新文献
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

        logger.info(f"Semantic Scholar抓取成功: {len(papers)} 篇论文")
        return FetchScholarOutput(scholar_papers=papers)

    except Exception as e:
        logger.error(f"Semantic Scholar抓取失败: {e}")
        return FetchScholarOutput(scholar_papers=[])
