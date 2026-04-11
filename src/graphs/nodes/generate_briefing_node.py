"""
个性化简报生成节点

根据分析结果和用户画像，生成个性化Markdown简报
"""
import json
import logging
import os
from datetime import datetime
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.runtime_ctx.context import new_context

from graphs.state import GenerateBriefingInput, GenerateBriefingOutput, UserProfile

logger = logging.getLogger(__name__)


def generate_briefing_node(
    state: GenerateBriefingInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> GenerateBriefingOutput:
    """
    title: 个性化简报生成
    desc: 根据分析结果和用户画像维度，生成个性化HTML格式科研简报
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

    # 渲染用户提示词
    up_tpl = Template(up)
    user_prompt = up_tpl.render({
        "analysis_result": state.analysis_result,
        "research_directions": ", ".join(state.user_profile.research_directions)
    })

    # 调用大模型
    try:
        llm_ctx = new_context(method="invoke")
        client = LLMClient(ctx=llm_ctx)

        messages = [
            SystemMessage(content=sp),
            HumanMessage(content=user_prompt)
        ]

        response = client.invoke(
            messages=messages,
            model=llm_config.get("model", "doubao-seed-2-0-lite-260215"),
            temperature=llm_config.get("temperature", 0.7),
            max_completion_tokens=llm_config.get("max_completion_tokens", 8192),
            thinking=llm_config.get("thinking", "disabled")
        )

        # 安全获取文本内容
        content = response.content
        if isinstance(content, str):
            briefing_html = content.strip()
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            briefing_html = "".join(text_parts).strip()
        else:
            briefing_html = str(content)

        # 生成邮件主题
        today = datetime.now().strftime("%Y年%m月%d日")
        directions = ", ".join(state.user_profile.research_directions[:2])
        email_subject = f"📡 文献雷达 | {directions} | {today}"

        logger.info(f"简报生成完成，内容长度: {len(briefing_html)}")
        return GenerateBriefingOutput(content=briefing_html, email_subject=email_subject)

    except Exception as e:
        logger.error(f"简报生成失败: {e}")
        today = datetime.now().strftime("%Y年%m月%d日")
        email_subject = f"📡 文献雷达 | {today}"
        fallback_content = f"<p>简报生成过程中遇到问题，请稍后重试。错误信息: {str(e)}</p>"
        return GenerateBriefingOutput(content=fallback_content, email_subject=email_subject)
