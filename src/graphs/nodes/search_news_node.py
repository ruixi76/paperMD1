"""
新闻搜索节点

搜索AI行业最新新闻
"""
import logging
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import SearchClient
from coze_coding_utils.runtime_ctx.context import new_context

from graphs.state import SearchNewsInput, SearchNewsOutput

logger = logging.getLogger(__name__)


def search_news_node(
    state: SearchNewsInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SearchNewsOutput:
    """
    title: 新闻搜索
    desc: 搜索AI行业最新新闻，获取标题、链接和摘要
    integrations: Web Search
    """
    ctx = runtime.context
    
    try:
        # 创建搜索客户端
        search_ctx = new_context(method="search.news")
        client = SearchClient(ctx=search_ctx)
        
        # 执行搜索，限制返回10条最新新闻
        response = client.web_search_with_summary(
            query=state.search_query,
            count=10
        )
        
        # 提取新闻列表
        news_list = []
        if response.web_items:
            for item in response.web_items:
                news_item = {
                    "title": item.title or "",
                    "url": item.url or "",
                    "snippet": item.snippet or "",
                    "site_name": item.site_name or "",
                    "publish_time": item.publish_time or ""
                }
                news_list.append(news_item)
        
        logger.info(f"成功搜索到 {len(news_list)} 条新闻")
        
        return SearchNewsOutput(news_list=news_list)
        
    except Exception as e:
        logger.error(f"新闻搜索失败: {str(e)}")
        return SearchNewsOutput(news_list=[])
