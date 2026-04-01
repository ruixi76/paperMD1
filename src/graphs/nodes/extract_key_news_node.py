"""
关键内容提取节点

从新闻列表中提取3条最关键的内容并格式化
"""
import os
import json
import logging
from datetime import datetime
from typing import List
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.runtime_ctx.context import new_context

from graphs.state import ExtractKeyNewsInput, ExtractKeyNewsOutput

logger = logging.getLogger(__name__)


def extract_key_news_node(
    state: ExtractKeyNewsInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> ExtractKeyNewsOutput:
    """
    title: 关键内容提取
    desc: 从新闻列表中提取3条最关键的内容，生成Markdown格式摘要
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
    
    # 构建新闻摘要文本
    news_text = ""
    for i, news in enumerate(state.news_list, 1):
        news_text += f"### {i}. {news.get('title', '')}\n"
        news_text += f"来源: {news.get('site_name', '未知')}\n"
        if news.get('publish_time'):
            news_text += f"时间: {news.get('publish_time')}\n"
        news_text += f"摘要: {news.get('snippet', '')}\n"
        news_text += f"链接: {news.get('url', '')}\n\n"
    
    # 使用jinja2模板渲染用户提示词
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({"news_list": news_text})
    
    # 调用大模型
    try:
        llm_ctx = new_context(method="invoke")
        client = LLMClient(ctx=llm_ctx)
        
        messages = [
            SystemMessage(content=sp),
            HumanMessage(content=user_prompt_content)
        ]
        
        response = client.invoke(
            messages=messages,
            model=llm_config.get("model", "doubao-seed-1-8-251228"),
            temperature=llm_config.get("temperature", 0.7),
            max_completion_tokens=llm_config.get("max_completion_tokens", 4096),
            thinking=llm_config.get("thinking", "disabled")
        )
        
        # 安全获取文本内容
        content = response.content
        if isinstance(content, str):
            news_content = content.strip()
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            news_content = "".join(text_parts).strip()
        else:
            news_content = str(content)
        
        logger.info("成功提取关键内容")
        # 生成邮件主题
        today = datetime.now().strftime("%Y年%m月%d日")
        email_subject = f"📬 今日AI行业新闻 TOP 3 - {today}"
        return ExtractKeyNewsOutput(content=news_content, email_subject=email_subject)
        
    except Exception as e:
        logger.error(f"内容提取失败: {str(e)}")
        # 返回错误信息
        today = datetime.now().strftime("%Y年%m月%d日")
        email_subject = f"📬 今日AI行业新闻 TOP 3 - {today}"
        error_msg = f"**今日AI行业新闻摘要**\n\n抱歉，内容提取过程中遇到问题，请稍后重试。\n\n错误信息: {str(e)}"
        return ExtractKeyNewsOutput(content=error_msg, email_subject=email_subject)
