"""
工作流状态定义

基于Agent的个性化科研伴侣：文献雷达系统
"""
from typing import List, Optional
from pydantic import BaseModel, Field


# ========== 公共数据模型 ==========

class PaperInfo(BaseModel):
    """论文信息"""
    title: str = Field(default="", description="论文标题")
    abstract: str = Field(default="", description="论文摘要")
    authors: List[str] = Field(default_factory=list, description="作者列表")
    doi: str = Field(default="", description="DOI标识符")
    url: str = Field(default="", description="论文链接")
    source: str = Field(default="", description="数据来源：arxiv/pubmed/semantic_scholar")
    publish_date: str = Field(default="", description="发布日期")
    categories: List[str] = Field(default_factory=list, description="学科分类")
    code_url: str = Field(default="", description="代码仓库链接（如GitHub）")


class UserProfile(BaseModel):
    """用户科研画像"""
    research_directions: List[str] = Field(
        default_factory=list,
        description="研究方向列表，如['域自适应','太赫兹','医学图像处理']"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="搜索关键词，如['domain adaptation','terahertz imaging','medical image segmentation']"
    )
    preferred_authors: List[str] = Field(
        default_factory=list,
        description="关注学者列表"
    )


# ========== 全局状态 ==========

class GlobalState(BaseModel):
    """全局状态定义"""
    # 用户配置
    to_email: str = Field(default="", description="收件人邮箱地址")
    user_profile: UserProfile = Field(default_factory=UserProfile, description="用户科研画像")

    # 并行抓取结果
    arxiv_papers: List[PaperInfo] = Field(default_factory=list, description="ArXiv论文列表")
    pubmed_papers: List[PaperInfo] = Field(default_factory=list, description="PubMed论文列表")
    scholar_papers: List[PaperInfo] = Field(default_factory=list, description="Semantic Scholar论文列表")

    # 合并与过滤
    all_papers: List[PaperInfo] = Field(default_factory=list, description="合并去重后的全部论文")
    top_papers: List[PaperInfo] = Field(default_factory=list, description="向量相似度过滤后的Top论文")

    # 分析与输出
    analysis_result: str = Field(default="", description="LLM三维评分分析结果")
    content: str = Field(default="", description="最终简报内容（用于邮件正文）")
    email_subject: str = Field(default="", description="邮件主题")


# ========== 图输入输出 ==========

class GraphInput(BaseModel):
    """工作流输入定义"""
    to_email: str = Field(..., description="收件人邮箱地址")
    user_profile: UserProfile = Field(..., description="用户科研画像")


class GraphOutput(BaseModel):
    """工作流输出定义"""
    success: bool = Field(..., description="是否执行成功")
    message: str = Field(..., description="执行结果消息")
    papers_count: int = Field(default=0, description="抓取的论文总数")
    top_papers_count: int = Field(default=0, description="筛选后的论文数")


# ========== 节点输入输出定义 ==========

# --- 数据采集层 ---

class FetchArxivInput(BaseModel):
    """ArXiv抓取节点输入"""
    user_profile: UserProfile = Field(..., description="用户科研画像")


class FetchArxivOutput(BaseModel):
    """ArXiv抓取节点输出"""
    arxiv_papers: List[PaperInfo] = Field(default_factory=list, description="ArXiv论文列表")


class FetchPubmedInput(BaseModel):
    """PubMed抓取节点输入"""
    user_profile: UserProfile = Field(..., description="用户科研画像")


class FetchPubmedOutput(BaseModel):
    """PubMed抓取节点输出"""
    pubmed_papers: List[PaperInfo] = Field(default_factory=list, description="PubMed论文列表")


class FetchScholarInput(BaseModel):
    """Semantic Scholar抓取节点输入"""
    user_profile: UserProfile = Field(..., description="用户科研画像")


class FetchScholarOutput(BaseModel):
    """Semantic Scholar抓取节点输出"""
    scholar_papers: List[PaperInfo] = Field(default_factory=list, description="Semantic Scholar论文列表")


# --- 合并去重 ---

class MergePapersInput(BaseModel):
    """合并去重节点输入"""
    arxiv_papers: List[PaperInfo] = Field(default_factory=list, description="ArXiv论文列表")
    pubmed_papers: List[PaperInfo] = Field(default_factory=list, description="PubMed论文列表")
    scholar_papers: List[PaperInfo] = Field(default_factory=list, description="Semantic Scholar论文列表")


class MergePapersOutput(BaseModel):
    """合并去重节点输出"""
    all_papers: List[PaperInfo] = Field(default_factory=list, description="合并去重后的全部论文")


# --- 向量相似度过滤 ---

class EmbedFilterInput(BaseModel):
    """向量过滤节点输入"""
    all_papers: List[PaperInfo] = Field(default_factory=list, description="全部论文列表")
    user_profile: UserProfile = Field(..., description="用户科研画像")


class EmbedFilterOutput(BaseModel):
    """向量过滤节点输出"""
    top_papers: List[PaperInfo] = Field(default_factory=list, description="相似度Top论文列表")


# --- 三维评分 + DOI溯源 ---

class AgentAnalysisInput(BaseModel):
    """Agent分析节点输入"""
    top_papers: List[PaperInfo] = Field(default_factory=list, description="Top论文列表")
    user_profile: UserProfile = Field(..., description="用户科研画像")


class AgentAnalysisOutput(BaseModel):
    """Agent分析节点输出"""
    analysis_result: str = Field(default="", description="三维评分分析结果JSON")


# --- 个性化简报生成 ---

class GenerateBriefingInput(BaseModel):
    """简报生成节点输入"""
    analysis_result: str = Field(..., description="分析结果JSON")
    user_profile: UserProfile = Field(..., description="用户科研画像")


class GenerateBriefingOutput(BaseModel):
    """简报生成节点输出"""
    content: str = Field(..., description="简报内容（HTML格式）")
    email_subject: str = Field(..., description="邮件主题")


# --- 发送邮件 ---

class SendEmailInput(BaseModel):
    """发送邮件节点输入"""
    to_email: str = Field(..., description="收件人邮箱")
    email_subject: str = Field(..., description="邮件主题")
    content: str = Field(..., description="邮件内容")


class SendEmailOutput(BaseModel):
    """发送邮件节点输出"""
    success: bool = Field(..., description="是否发送成功")
    message: str = Field(..., description="发送结果消息")
