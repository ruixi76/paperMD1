"""
PubMed文献抓取节点

通过PubMed E-utilities API获取医学文献
"""
import json
import logging
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import List
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import FetchPubmedInput, FetchPubmedOutput, PaperInfo, UserProfile

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _build_pubmed_query(user_profile: UserProfile) -> str:
    """根据用户画像构建PubMed搜索查询"""
    keywords = user_profile.keywords
    directions = user_profile.research_directions

    search_terms = []
    for kw in keywords:
        kw_stripped = kw.strip()
        if kw_stripped:
            search_terms.append(f'"{kw_stripped}"[Title/Abstract]')

    # 如果有研究方向，补充医学相关方向词
    for direction in directions:
        d_stripped = direction.strip()
        if d_stripped and "医学" in d_stripped or "medical" in d_stripped.lower():
            search_terms.append('"medical imaging"[MeSH Terms]')
            search_terms.append('"deep learning"[Title/Abstract]')

    if not search_terms:
        search_terms = ['"artificial intelligence"[MeSH Terms]']

    return " OR ".join(search_terms)


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
        parts = []
        if year is not None and year.text:
            parts.append(year.text.strip())
        if month is not None and month.text:
            parts.append(month.text.strip())
        if day is not None and day.text:
            parts.append(day.text.strip())
        publish_date = "-".join(parts)

    pmid_elem = article.find(".//PMID")
    pmid = pmid_elem.text.strip() if pmid_elem is not None and pmid_elem.text else ""
    if pmid and not doi:
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

    return PaperInfo(
        title=title,
        abstract=abstract,
        authors=authors,
        doi=doi,
        url=url,
        source="pubmed",
        publish_date=publish_date,
        categories=["medicine"]
    )


def fetch_pubmed_node(
    state: FetchPubmedInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> FetchPubmedOutput:
    """
    title: PubMed文献抓取
    desc: 通过PubMed E-utilities API获取医学领域最新文献
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

        logger.info(f"PubMed抓取成功: {len(papers)} 篇文献")
        return FetchPubmedOutput(pubmed_papers=papers)

    except Exception as e:
        logger.error(f"PubMed抓取失败: {e}")
        return FetchPubmedOutput(pubmed_papers=[])
