"""
工作流状态定义

AI新闻自动推送工作流状态结构
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class GlobalState(BaseModel):
    """全局状态定义"""
    # 用户配置
    to_email: str = Field(default="", description="收件人邮箱地址")
    search_query: str = Field(default="AI 人工智能 行业新闻", description="新闻搜索关键词")
    
    # 中间数据
    raw_news: List[dict] = Field(default_factory=list, description="搜索返回的原始新闻列表")
    formatted_news: str = Field(default="", description="格式化后的新闻内容（用于发送邮件）")


class GraphInput(BaseModel):
    """工作流输入定义"""
    to_email: str = Field(..., description="收件人邮箱地址")
    search_query: str = Field(default="AI 人工智能 行业新闻", description="新闻搜索关键词")


class GraphOutput(BaseModel):
    """工作流输出定义"""
    success: bool = Field(..., description="是否执行成功")
    message: str = Field(..., description="执行结果消息")
    news_count: int = Field(default=0, description="处理的新闻数量")


class SearchNewsInput(BaseModel):
    """新闻搜索节点输入"""
    search_query: str = Field(..., description="搜索关键词")


class SearchNewsOutput(BaseModel):
    """新闻搜索节点输出"""
    news_list: List[dict] = Field(default_factory=list, description="新闻列表，每条包含title、url、snippet")


class ExtractKeyNewsInput(BaseModel):
    """关键内容提取节点输入"""
    news_list: List[dict] = Field(..., description="原始新闻列表")


class ExtractKeyNewsOutput(BaseModel):
    """关键内容提取节点输出"""
    content: str = Field(..., description="格式化后的新闻内容（Markdown格式，用于发送邮件）")
    email_subject: str = Field(..., description="邮件主题")


class SendEmailInput(BaseModel):
    """发送邮件节点输入"""
    to_email: str = Field(..., description="收件人邮箱")
    email_subject: str = Field(..., description="邮件主题")
    content: str = Field(..., description="邮件内容")


class SendEmailOutput(BaseModel):
    """发送邮件节点输出"""
    success: bool = Field(..., description="是否发送成功")
    message: str = Field(..., description="发送结果消息")
