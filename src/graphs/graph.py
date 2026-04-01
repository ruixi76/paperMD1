"""
主图编排

AI新闻自动推送工作流
每天早上8点自动抓取AI行业新闻，提取三条最关键的内容发送到用户邮箱
"""
from langgraph.graph import StateGraph, END
from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
    SearchNewsInput,
    SearchNewsOutput,
    ExtractKeyNewsInput,
    ExtractKeyNewsOutput,
    SendEmailInput,
    SendEmailOutput
)
from graphs.nodes.search_news_node import search_news_node
from graphs.nodes.extract_key_news_node import extract_key_news_node
from graphs.nodes.send_email_node import send_email_node


def should_continue(state: GlobalState) -> bool:
    """
    title: 是否继续执行
    desc: 判断是否有搜索结果，决定是否继续执行后续节点
    """
    return len(state.raw_news) > 0


def build_graph():
    """构建主图"""
    builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)
    
    # 添加节点
    builder.add_node("search_news", search_news_node)
    builder.add_node("extract_key_news", extract_key_news_node, metadata={
        "type": "agent",
        "llm_cfg": "config/extract_news_llm_cfg.json"
    })
    builder.add_node("send_email", send_email_node)
    
    # 设置入口点
    builder.set_entry_point("search_news")
    
    # 添加边
    builder.add_edge("search_news", "extract_key_news")
    builder.add_edge("extract_key_news", "send_email")
    builder.add_edge("send_email", END)
    
    # 编译图
    return builder.compile()


def run_workflow(to_email: str, search_query: str = "AI 人工智能 行业新闻") -> dict:
    """
    执行工作流
    
    Args:
        to_email: 收件人邮箱
        search_query: 搜索关键词
        
    Returns:
        执行结果
    """
    # 初始化输入
    graph_input = GraphInput(
        to_email=to_email,
        search_query=search_query
    )
    
    # 编译后的图
    main_graph = build_graph()
    
    # 执行工作流
    result = main_graph.invoke(graph_input)
    
    return {
        "success": len(result.get("raw_news", [])) > 0 and "formatted_news" in result,
        "message": f"成功处理 {len(result.get('raw_news', []))} 条新闻并发送邮件",
        "news_count": len(result.get("raw_news", []))
    }


# 创建全局图实例
main_graph = build_graph()
