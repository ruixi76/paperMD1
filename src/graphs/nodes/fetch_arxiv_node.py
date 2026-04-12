"""
ArXiv论文抓取节点

通过ArXiv API获取最新论文
"""
import json
import logging
import math
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import List
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import FetchArxivInput, FetchArxivOutput, PaperInfo, UserProfile

logger = logging.getLogger(__name__)

ARXIV_API_BASE = "http://export.arxiv.org/api/query"

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _build_arxiv_query(user_profile: UserProfile) -> str:
    """根据用户画像构建ArXiv搜索查询"""
    keywords = user_profile.keywords
    if not keywords:
        keywords = ["artificial intelligence", "deep learning"]
    # 构建查询: all:keyword1 OR all:keyword2
    query_parts = [f'all:{kw.strip()}' for kw in keywords if kw.strip()]
    if not query_parts:
        query_parts = ["all:artificial intelligence"]
    return " OR ".join(query_parts)


def _parse_arxiv_entry(entry) -> PaperInfo:
    """解析单个ArXiv条目"""
    title_elem = entry.find("atom:title", ATOM_NS)
    title = title_elem.text.strip().replace("\n", " ") if title_elem is not None and title_elem.text else ""

    summary_elem = entry.find("atom:summary", ATOM_NS)
    abstract = summary_elem.text.strip().replace("\n", " ") if summary_elem is not None and summary_elem.text else ""

    authors = []
    for author_elem in entry.findall("atom:author", ATOM_NS):
        name_elem = author_elem.find("atom:name", ATOM_NS)
        if name_elem is not None and name_elem.text:
            authors.append(name_elem.text.strip())

    doi_elem = entry.find("arxiv:doi", ATOM_NS)
    doi = doi_elem.text.strip() if doi_elem is not None and doi_elem.text else ""

    url = ""
    code_url = ""
    for link_elem in entry.findall("atom:link", ATOM_NS):
        link_title = link_elem.get("title", "")
        link_href = link_elem.get("href", "")
        if link_title == "html":
            url = link_href
        elif link_title == "related" and "github.com" in link_href.lower():
            code_url = link_href
    if not url:
        id_elem = entry.find("atom:id", ATOM_NS)
        url = id_elem.text.strip() if id_elem is not None and id_elem.text else ""

    # 尝试从摘要中提取GitHub链接
    if not code_url and abstract:
        import re
        github_match = re.search(r'(https?://github\.com/[\w\-]+/[\w\-]+)', abstract)
        if github_match:
            code_url = github_match.group(1)

    published_elem = entry.find("atom:published", ATOM_NS)
    publish_date = published_elem.text.strip()[:10] if published_elem is not None and published_elem.text else ""

    categories = []
    for cat_elem in entry.findall("atom:category", ATOM_NS):
        term = cat_elem.get("term", "")
        if term:
            categories.append(term)

    return PaperInfo(
        title=title,
        abstract=abstract,
        authors=authors,
        doi=doi,
        url=url,
        source="arxiv",
        publish_date=publish_date,
        categories=categories,
        code_url=code_url
    )


def fetch_arxiv_node(
    state: FetchArxivInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> FetchArxivOutput:
    """
    title: ArXiv论文抓取
    desc: 通过ArXiv API获取最新论文，支持关键词搜索和日期排序
    integrations: ArXiv API
    """
    ctx = runtime.context

    try:
        query = _build_arxiv_query(state.user_profile)
        params = urllib.parse.urlencode({
            "search_query": query,
            "start": 0,
            "max_results": 20,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        })
        url = f"{ARXIV_API_BASE}?{params}"

        logger.info(f"ArXiv API请求: {url}")

        req = urllib.request.Request(url, headers={"User-Agent": "LiteratureRadar/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        papers = []
        for entry in root.findall("atom:entry", ATOM_NS):
            try:
                paper = _parse_arxiv_entry(entry)
                if paper.title:
                    papers.append(paper)
            except Exception as e:
                logger.warning(f"解析ArXiv条目失败: {e}")
                continue

        logger.info(f"ArXiv抓取成功: {len(papers)} 篇论文")
        return FetchArxivOutput(arxiv_papers=papers)

    except Exception as e:
        logger.error(f"ArXiv抓取失败: {e}")
        return FetchArxivOutput(arxiv_papers=[])
