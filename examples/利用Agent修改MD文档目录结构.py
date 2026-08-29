import sys
from typing import Annotated

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from deepagents.backends import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemMiddleware

load_dotenv()

model = ChatOpenAI(
    model="deepseek-v4-flash",
    model_kwargs={"extra_body": {"thinking": {"type": "disabled"}}},
    temperature=0.2,
)

backend = FilesystemBackend(
    root_dir="../examples-data",
    virtual_mode=True,
)

EDITOR_SYSTEM_PROMPT = """\
你是 Markdown 文档目录结构整理专家。修改文件只能用 Edit 工具。

## 工作流程
1. **提取标题**：使用 Grep 命令提取出文件中的所有 Markdown 标题及行号。如果文件开头有 TOC 目录，Read 前 100 行即可，不要一次性读整个文件，也不要尝试读取全部内容，文件可能很大。
2. **比对分析**：将标题与 TOC 对比，找出层级错位、遗漏、多余 # 等问题。
3. **逐项修改**：用 Edit 逐处修正，**只改标题行本身**，不要把标题下面的正文内容也放进 old_string/new_string。
4. **复核**：改完再用 Grep 提取一遍，确认全部修正。

## 修改规则
- **标题绝对层级**：最高章节必须从 `#` 开始，禁止整体偏移或跳跃（如 `#` 直接到 `###`）。
- **降级非章节标题**：正文开头的封面大标题和字面为「目录」的行不是章节，降级为 **加粗**。
- **降级非 TOC 小标题**：正文中更细碎的编号（未在 TOC 中出现），改为 **加粗**。
- **补充缺失标题**：TOC 中有但正文遗漏 # 的章节，补上 # 标题。
- **清理格式**：去除锚点标记，`#` 与标题文字间保留一个半角空格。

注意：如果你收到了 Auditor（审计员）的反馈，请严格按照其指出的具体行号和问题进行针对性修复。
"""

editor_agent = create_agent(
    model,
    system_prompt=EDITOR_SYSTEM_PROMPT,
    middleware=[FilesystemMiddleware(backend=backend)],
)

AUDITOR_SYSTEM_PROMPT = """\
你是 Markdown 文档结构审计员。

你处于 Editor -> Auditor 的工作流中。
当你被调用时，当前 message 会明确给出需要审计的 Markdown 文件和任务背景；只依据这条 message 工作，
不要假设或查阅任何历史会话记录。
你只负责检查文件，不要修改文件。

## 工作流程
1. 从当前 message 中确定目标 Markdown 文件。
2. 用 Grep 提取所有标题行。
3. 检查结构：
   - `#` 一级、`##` 二级、`###` 三级，以此类推
   - 最高章节从 `#` 开始
   - 层级逐级递进，不跳跃（如 `#` 直接到 `###`）
   - `#` 与文字间有空格

## 输出

通过：回复末尾包含 `[AUDIT_PASS]`
不通过：指出具体行号和问题，回复末尾包含 `[AUDIT_FAIL]`
"""

auditor_agent = create_agent(
    model,
    system_prompt=AUDITOR_SYSTEM_PROMPT,
    middleware=[FilesystemMiddleware(backend=backend)],
)


class AgentState(BaseModel):
    """工作流状态：messages 承载 Editor 对话；不接入 checkpointer，单次运行即起即止。"""

    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    is_valid: bool = False
    attempts: int = 0
    audit_feedback: str = ""


def auditor_node(state: AgentState) -> dict:
    """审计并评估：计数、审计、打回逻辑全部收敛在本节点内。"""
    attempts = state.attempts + 1

    original_request = state.messages[0].content
    audit_message = HumanMessage(
        content=(
            "请执行一次独立的 Markdown 结构审计。\n\n"
            f"原始任务（用于确定目标文件）：{original_request}\n\n"
            f"Editor 已完成第 {attempts} 次修改，请直接检查上述目标文件。"
        )
    )
    result = auditor_agent.invoke({"messages": [audit_message]})
    feedback = result["messages"][-1].content.strip()

    if "[AUDIT_PASS]" in feedback:
        return {"attempts": attempts, "is_valid": True, "audit_feedback": feedback}

    retry_message = HumanMessage(
        name="Auditor",
        content=(
            f"第 {attempts} 次修改未通过审计。\n\n"
            f"审计反馈：\n{feedback}\n\n"
            "请严格按照上面的具体行号和问题，使用工具修复目标 Markdown 文件。"
        ),
    )
    return {
        "attempts": attempts,
        "is_valid": False,
        "audit_feedback": feedback,
        "messages": [retry_message],
    }


def should_continue(state: AgentState) -> str:
    if state.is_valid:
        return END

    if state.attempts >= 3:
        return "fail"

    return "editor"


def fail_node(state: AgentState) -> dict:
    raise RuntimeError(
        f"经过 {state.attempts} 次修改仍未通过审计，流程终止。\n"
        f"最后一次反馈：\n{state.audit_feedback}"
    )


builder = StateGraph(AgentState)

builder.add_node("editor", editor_agent)
builder.add_node("auditor", auditor_node)
builder.add_node("fail", fail_node)

builder.add_edge(START, "editor")
builder.add_edge("editor", "auditor")

builder.add_conditional_edges(
    "auditor",
    should_continue,
    {
        "editor": "editor",
        "fail": "fail",
        END: END,
    },
)

workflow = builder.compile()


def main(md_file: str) -> None:
    """运行 Editor -> Auditor 循环，直到审计通过或重试次数用尽，逐步打印过程。"""
    print(f"📄 目标文件：{md_file}\n")

    try:
        for chunk in workflow.stream(
                {"messages": [HumanMessage(content=f"请检查并修正 Markdown 文件 `{md_file}` 的标题层级结构。")]},
                stream_mode="values",
                version="v2",
                subgraphs=True
        ):
            ns = chunk.get("ns") or ()
            print(ns[0].split(":")[0] if ns else "root")
            message = chunk["data"].messages[-1]  # data 是 AgentState(pydantic)，不是 dict
            message.pretty_print()

    except RuntimeError as e:
        print(f"\n💥 流程终止：{e}")
        return

    print("\n🎉 审计通过，流程结束。")


if __name__ == "__main__":
    md_file = "layout-parser-paper.md"
    main(md_file)
