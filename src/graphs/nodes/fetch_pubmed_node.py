"""
PubMed文献抓取节点

通过PubMed E-utilities API获取医学文献，全文搜索GitHub代码链接
"""
import json
import logging
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Optional
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import FetchPubmedInput, FetchPubmedOutput, PaperInfo, UserProfile

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

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


def _build_pubmed_query(user_profile: UserProfile) -> str:
    """根据用户画像构建PubMed搜索查询"""
    keywords = user_profile.keywords
    directions = user_profile.research_directions

    search_terms = []
    for kw in keywords:
        kw_stripped = kw.strip()
        if kw_stripped:
            search_terms.append(f'"{kw_stripped}"[Title/Abstract]')

    for direction in directions:
        d_stripped = direction.strip()
        if d_stripped and "医学" in d_stripped or "medical" in d_stripped.lower():
            search_terms.append('"medical imaging"[MeSH Terms]')
            search_terms.append('"deep learning"[Title/Abstract]')

    if not search_terms:
        search_terms = ['"artificial intelligence"[MeSH Terms]']

    return " OR ".join(search_terms)


def _enrich_code_url(paper: PaperInfo) -> PaperInfo:
    """
    全文搜索GitHub代码链接
    优先级：已有code_url > 摘要搜索 > PubMed文章页面全文搜索
    """
    # 1. 已有则直接返回
    if paper.code_url:
        return paper

    # 2. 摘要搜索
    code_url = _search_github_in_text(paper.abstract)
    if code_url:
        return PaperInfo(**{**paper.model_dump(), "code_url": code_url})

    # 3. PubMed文章页面全文搜索
    if paper.url:
        page_text = _fetch_page_text(paper.url, timeout=8)
        code_url = _search_github_in_text(page_text)
        if code_url:
            logger.info(f"PubMed全文搜索到GitHub: {paper.title[:40]}... → {code_url}")
            return PaperInfo(**{**paper.model_dump(), "code_url": code_url})

    return paper


def _parse_pubmed_article(article) -> PaperInfo:
    """解析单个PubMed文章"""
    title_elem = article.find(".//ArticleTitle")
    title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

    # 合并多段Abstract
    abstract_parts = []
    for abs_text in article.findall(".//AbstractText"):
        text = abs_text.text
        if text:
            label = abs_text.get("Label", "")
            if label:
                abstract_parts.append(f"{label}: {text.strip()}")
            else:
                abstract_parts.append(text.strip())
    abstract = " ".join(abstract_parts)

    authors = []
    for author in article.findall(".//Author"):
        last = author.find("LastName")
        fore = author.find("ForeName")
        parts = []
        if fore is not None and fore.text:
            parts.append(fore.text.strip())
        if last is not None and last.text:
            parts.append(last.text.strip())
        if parts:
            authors.append(" ".join(parts))

    doi = ""
    for article_id in article.findall(".//ArticleId"):
        if article_id.get("IdType") == "doi":
            doi = article_id.text.strip() if article_id.text else ""
            break

    url = f"https://pubmed.ncbi.nlm.nih.gov/" if not doi else f"https://doi.org/{doi}"

    pub_date_elem = article.find(".//PubDate")
    publish_date = ""
    if pub_date_elem is not None:
        year = pub_date_elem.find("Year")
        month = pub_date_elem.find("Month")
        day = pub_date_elem.find("Day")
        date_parts = []
        if year is not None and year.text:
            date_parts.append(year.text.strip())
        if month is not None and month.text:
            date_parts.append(month.text.strip())
        if day is not None and day.text:
            date_parts.append(day.text.strip())
        publish_date = "-".join(date_parts)

    pmid_elem = article.find(".//PMID")
    pmid = pmid_elem.text.strip() if pmid_elem is not None and pmid_elem.text else ""
    if pmid and not doi:
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

    # 从摘要中提取GitHub代码链接
    code_url = _search_github_in_text(abstract)

    return PaperInfo(
        title=title,
        abstract=abstract,
        authors=authors,
        doi=doi,
        url=url,
        source="pubmed",
        publish_date=publish_date,
        categories=["medicine"],
        code_url=code_url
    )


def fetch_pubmed_node(
    state: FetchPubmedInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> FetchPubmedOutput:
    """
    title: PubMed文献抓取
    desc: 通过PubMed E-utilities API获取医学领域最新文献，全文搜索GitHub代码链接
    integrations: PubMed API
    """
    ctx = runtime.context

    try:
        query = _build_pubmed_query(state.user_profile)

        # Step 1: 搜索获取PMID列表
        search_params = urllib.parse.urlencode({
            "db": "pubmed",
            "term": query,
            "retmax": 20,
            "sort": "date",
            "retmode": "json"
        })
        search_url = f"{ESEARCH_URL}?{search_params}"
        logger.info(f"PubMed ESearch请求: {search_url}")

        req = urllib.request.Request(search_url, headers={"User-Agent": "LiteratureRadar/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            search_data = json.loads(response.read().decode("utf-8"))

        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            logger.info("PubMed搜索无结果")
            return FetchPubmedOutput(pubmed_papers=[])

        # Step 2: 获取论文详情
        fetch_params = urllib.parse.urlencode({
            "db": "pubmed",
            "id": ",".join(pmids[:20]),
            "retmode": "xml"
        })
        fetch_url = f"{EFETCH_URL}?{fetch_params}"
        logger.info(f"PubMed EFetch请求: {fetch_url}")

        req = urllib.request.Request(fetch_url, headers={"User-Agent": "LiteratureRadar/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        papers = []
        for article in root.findall(".//PubmedArticle"):
            try:
                paper = _parse_pubmed_article(article)
                if paper.title:
                    papers.append(paper)
            except Exception as e:
                logger.warning(f"解析PubMed文章失败: {e}")
                continue

        # 全文搜索GitHub链接（对无code_url的论文补充搜索）
        enriched_papers = []
        for paper in papers:
            if paper.code_url:
                enriched_papers.append(paper)
            else:
                enriched_papers.append(_enrich_code_url(paper))

        code_count = sum(1 for p in enriched_papers if p.code_url)
        logger.info(f"PubMed抓取成功: {len(enriched_papers)} 篇文献, {code_count} 篇含代码链接")
        return FetchPubmedOutput(pubmed_papers=enriched_papers)

    except Exception as e:
        logger.error(f"PubMed抓取失败: {e}")
        return FetchPubmedOutput(pubmed_papers=[])
