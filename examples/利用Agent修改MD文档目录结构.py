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

EDITOR_SYSTEM_PROMPT = """
你是 Markdown 文档目录结构整理专家。修改文件只能用 Edit 工具。

## 工具说明

* Grep 仅支持字面量匹配，不支持正则表达式。
* **提取 Markdown 标题时，Grep 的 pattern 固定使用 `# `。**
* 禁止使用 `^#`、`^##`、`^#{1,6}`、`.*#` 等任何正则形式。
* 正确示例：`Grep(pattern="# ", path=目标文件, output_mode="content")`
* 如果没有匹配结果，也不要改用正则；应先确认文件路径是否正确。

## 工作流程

1. **提取标题**：使用 Grep，并固定以 `# ` 作为 pattern，提取包含 Markdown 标题的候选行及行号。文件可能很大，不要一次性读取全文。
2. **判断结构**：检查文件开头是否存在 TOC。存在可靠 TOC 时优先参考 TOC；没有 TOC 或 TOC 不完整时，根据标题编号、上下文和全文标题规律判断正确层级。
3. **逐项修改**：用 Edit 逐处修正，**只改标题行本身**，不要修改正文内容。
4. **复核**：修改完成后再次使用 Grep，并固定以 `# ` 作为 pattern，检查标题结构是否合理且一致。

## 修改规则

* **标题绝对层级**：真正的最高章节从 `#` 开始，子章节逐级递进，禁止无理由跳级（如 `#` 直接到 `###`）。
* **同级保持一致**：明显属于同一级别的章节，应使用相同数量的 `#`。
* **综合判断层级**：TOC 是重要参考但不是必须条件；没有 TOC 时，根据章节编号、标题规律及上下文判断。
* **不要盲从原始层级**：MinerU 生成的 `#` 层级可能有误，只能作为参考。
* **降级非章节标题**：封面大标题、字面为「目录」的标题等不属于正文章节的内容，不应作为一级章节；需要保留强调时可改为加粗。
* **补充缺失标题**：正文中明显属于章节标题但遗漏 `#` 时，在有充分依据的情况下补充正确层级。
* **清理格式**：去除标题中的锚点标记，`#` 与标题文字之间保留一个半角空格。
* **最小修改**：只修正确定存在问题的标题，不要改写标题文字或正文。

最终目标：使 Markdown 的标题结构逻辑一致，并能够稳定按照一级标题 `# ` 拆分为完整章节。

注意：如果收到 Auditor 的反馈，请根据其指出的具体行号和问题进行针对性修复。
"""

editor_agent = create_agent(
    model,
    system_prompt=EDITOR_SYSTEM_PROMPT,
    middleware=[FilesystemMiddleware(backend=backend)],
)

AUDITOR_SYSTEM_PROMPT = """\
你是 Markdown 文档结构审计员。

你处于 Editor -> Auditor 的工作流中。
你只负责检查文件，不要修改文件。

## 工具说明

* Grep 仅支持字面量匹配，不支持正则表达式。
* **提取 Markdown 标题时，Grep 的 pattern 固定使用 `# `。**
* 禁止使用 `^#`、`^##`、`^#{1,6}`、`.*#` 等任何正则形式。
* 正确示例：`Grep(pattern="# ", path=目标文件, output_mode="content")`
* 如果没有匹配结果，也不要改用正则；应先确认文件路径是否正确。

## 工作流程

1. 从当前 message 中确定目标 Markdown 文件。
2. 使用 Grep 提取所有 Markdown 标题及行号。
3. 检查标题结构是否合理、一致，并能够稳定按照一级标题 `# ` 拆分章节。

## 检查规则

* 真正的最高章节应从 `#` 开始。
* 子章节应逐级递进，禁止无理由跳级，例如 `#` 直接到 `###`。
* 明显属于同一级别的章节应使用相同数量的 `#`。
* 如果标题带有明显章节编号，应检查编号关系与 Markdown 层级是否基本一致，例如 `1`、`1.1`、`1.1.1` 应逐级递进。
* 不应将封面标题、「目录」等明显非正文章节内容作为一级章节。
* `#` 与标题文字之间必须保留一个半角空格。
* MinerU 原始标题层级可能存在错误，不要因为当前 Markdown 语法合法就直接判定通过。
* 不要求必须存在 TOC；如果存在 TOC，可以作为辅助判断依据。

重点检查：按照 `# ` 拆分文件后，每个一级标题是否能够代表合理、完整的大章节。

## 输出

通过：简要说明检查结果，回复末尾包含 `[AUDIT_PASS]`

不通过：指出具体行号、当前问题以及建议的正确层级，回复末尾包含 `[AUDIT_FAIL]`
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
