# %%
from dotenv import load_dotenv

load_dotenv()

from typing import Annotated
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.graph.message import add_messages
from deepagents.backends import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, BaseMessage

print("✅ 环境准备完成")

# %%
model = ChatOpenAI(
    model="deepseek-v4-pro",
    model_kwargs={"extra_body": {"thinking": {"type": "disabled"}}}
)

backend = FilesystemBackend(root_dir='../examples-data', virtual_mode=True)

# %%
EDITOR_SYSTEM_PROMPT = """\
你是 Markdown 文档目录结构整理专家。修改 md 文件内容时只能使用 Edit 工具，不管有多少处需要改，禁止用 sed、Python 脚本等任何批量替换方式。

## 工作流程（必须按顺序执行）

### 第一步：提取标题结构（不要读整个文件！）

**强烈建议使用 Grep 工具**，用正则表达式 `^#+\\s` 提取文件中所有以 # 开头的标题行。这会返回所有标题行及其行号，速度快、不占上下文。
- 如果文件开头有 TOC 目录块（以 `- [` 或 `* [` 开头的列表），用 Read 只读文件开头的 ~30-50 行即可获取 TOC 结构。
- **不要一次性 Read 整个文件**。如果文件很长（>100行），只 Read 你需要的局部区域。

### 第二步：比对分析

将 Grep 提取到的标题结构与 TOC（如果有）进行比对，列出问题清单：
- 层级错位（如 ## 应该是 ###）
- 未在 TOC 中出现的小标题误用了 #
- 正文缺失 TOC 中的某级标题
- TOC 本身有层级跳跃、编号不连续等错误

### 第三步：逐项修改

用 Edit 工具逐个修正每个问题。**每次只修改一处**，修改完确认无误再进行下一处。

### 第四步：复核

修改完成后，再次用 Grep 提取标题树，核对确认所有问题已修正。

## 修改规则

**核心校验基准**：正文前若有自带 TOC 目录，以 TOC 的层级结构和编号形式为基准，反向校对并修正正文标题。但 TOC 本身可能有明显错误（如层级跳跃、编号不连续、漏掉明显章节），遇到此类情况应按合理逻辑一并修正 TOC，不要盲从。

- **标题绝对层级正确**：正文中最高层级的章节标题必须从 `#` 开始（一个 #），次高层级为 `##`（两个 #），以此类推。不允许整体偏移（如全文最高章节标题用了 `##` 而非 `#`，导致所有标题都比应有层级多一个 #）。若有 TOC 则以 TOC 的层级为准，但需一并检查 TOC 本身是否也存在整体偏移。
- **层级逐级递进**：标题层级必须逐级递进，不允许跳跃（如 `#` 直接跳到 `###`）。
- **降级封面标题**：正文开头的文档封面大标题（如 # XX方案）不是章节，降级为 **加粗**。
- **降级"目录"二字所在行**：正文中字面为「目录」的一行（如 ## 目录）不是章节标题，降级为 **加粗**。
- **补充缺失标题**：TOC 中有但正文未被解析为标题的章节（如仅加粗或遗漏 #），按 TOC 层级手动补充为 # 正文标题。
- **降级非 TOC 小标题**：正文内更细碎的编号（如"一、""1、""（1）"等），若未在 TOC 中出现，一律不用 # 标题，改为 **加粗**。
- **清理格式**：去除残余锚点标记（[]{#_Toc...} 等），# 与标题文字之间保留一个半角空格。
"""

edit_agent = create_agent(
    model,
    system_prompt=EDITOR_SYSTEM_PROMPT,
    middleware=[FilesystemMiddleware(backend=backend)],
)

# %%
AUDITOR_SYSTEM_PROMPT = """\
你是一个 Markdown 文档结构审计员。你的任务是检查经过标题修正后的 Markdown 文件是否完全符合规范。

## 工作流程

### 第一步：提取标题结构
**强烈建议使用 Grep 工具**，用正则表达式 `^#+\\s` 提取文件中所有标题行。这样可以快速获取全貌而不需要读整个文件。
- 如果文件开头有 TOC 目录块，用 Read 只读文件前 30-50 行。
- **不要一次性 Read 整个文件**，除非文件非常短（<50行）。
- 如需检查具体行内容，用 Read 指定 offset 和 limit 只读相关区域。

### 第二步：逐项审计

逐项检查以下规则，任何一项不通过即为不合格：

1. **标题层级合理**：正文中最高层级的章节标题必须从 `#` 开始，不允许整体偏移（如全文最高章节标题用了 `##` 而非 `#`）。若有 TOC，正文标题层级应与 TOC 一致，但 TOC 本身有明显错误（层级跳跃、整体偏移、编号不连续等）时，TOC 和正文应已被一并修正而非照搬错误；若无 TOC，标题层级必须逐级递进（# → ## → ###），不允许跳跃。
2. **封面标题降级**：正文开头的文档封面大标题（如 # XX方案）不是章节，必须已降级为 **加粗**。
3. **"目录"行降级**：正文中字面为「目录」的一行（如 ## 目录）不是章节标题，必须已降级为 **加粗**。
4. **非 TOC 小标题降级**：正文内更细碎的编号（如"一、""1、""（1）"等），若未在 TOC 中出现（或无 TOC 时不属于正经章节），必须已改为 **加粗**，而非 # 标题。
5. **锚点清理**：是否已去除所有残余锚点标记（如 {#_Toc...}、[]{#...} 等）？
6. **标题格式**：# 与标题文字之间是否保留了一个半角空格？

## 输出要求（严格遵守）

**通过时**：你的整个回复必须是且仅是以下 4 个字符，不得有任何其他内容（包括换行）：

PASS

**不通过时**：明确指出：
- 哪条规则未通过
- 具体哪些行有问题
- 应该如何修正

注意：不通过时你的回复中绝对不能出现 "PASS" 这个词。"""

auditor_agent = create_agent(
    model,
    system_prompt=AUDITOR_SYSTEM_PROMPT,
    middleware=[FilesystemMiddleware(backend=backend)]
)


# %%
class AgentState(BaseModel):
    """工作流状态。

    messages 的设计思路：
    - 初始传入 HumanMessage(task)
    - editor_node 只把 agent 的**最后一条结论**追加到 messages（tool call 历史不进 state）
    - auditor_node 把审计反馈以 HumanMessage(name="Auditor", ...) 追加到 messages
    - editor_node 重试时直接以 state.messages 作为输入，自然看到审计反馈，无需拼接字符串
    """
    task: str = ""
    messages: Annotated[list[BaseMessage], add_messages] = Field(
        default_factory=list
    )
    is_valid: bool = False
    attempts: int = 0
    audit_feedback: str = ""


def editor_node(state: AgentState) -> dict:
    """编辑节点：调用 agent 修改 MD 文件。

    只把 agent 的最后一条消息（结论）写入 state.messages，
    避免 tool call/tool result 等大量中间消息污染 state。
    重试时 state.messages 中已有 [HumanMessage(task), ..., HumanMessage(Auditor, feedback)]，
    agent 自然理解上下文。
    """
    attempts = state.attempts + 1

    result = edit_agent.invoke({"messages": list(state.messages)})

    return {
        "messages": [result["messages"][-1]],  # 只保留结论
        "attempts": attempts,
    }


def auditor_node(state: AgentState) -> dict:
    """审计节点：调用审计 agent 检查修改后的文件。

    审计不通过时，把反馈包装为 HumanMessage(name="Auditor", ...) 追加到 messages，
    editor 重试时会自然看到这条消息。
    """
    audit_result = auditor_agent.invoke(
        {"messages": [HumanMessage(content=f"背景：编辑 agent 刚完成了以下任务——{state.task}\n\n请审计这个 Markdown 文件的标题结构。")]}
    )
    audit_feedback = audit_result["messages"][-1].content.strip()

    if audit_feedback == "PASS":
        return {"is_valid": True, "audit_feedback": audit_feedback}
    else:
        feedback_msg = HumanMessage(
            name="Auditor",
            content=(
                f"你的修改未通过审计。审计员的反馈是：\n{audit_feedback}\n"
                f"请根据反馈修正，确保所有规则通过！"
            )
        )
        return {
            "is_valid": False,
            "audit_feedback": audit_feedback,
            "messages": [feedback_msg],
        }


def fail_node(state: AgentState) -> dict:
    """失败节点：超过最大重试次数仍未通过审计时抛出异常"""
    raise RuntimeError(
        f"❌ 经过 {state.attempts} 次修改仍未通过审计。\n"
        f"最后一次审计反馈：\n{state.audit_feedback}"
    )


def should_continue(state: AgentState) -> str:
    """路由判断：PASS → END，失败且 <3 次 → 重试，>=3 次 → 抛出异常"""
    if state.is_valid:
        return END
    if state.attempts >= 3:
        return "fail_node"
    return "editor"


# %%
builder = StateGraph(AgentState)

builder.add_node("editor", editor_node)
builder.add_node("auditor", auditor_node)
builder.add_node("fail_node", fail_node)

builder.add_edge(START, "editor")
builder.add_edge("editor", "auditor")
builder.add_conditional_edges(
    "auditor",
    should_continue,
    {
        "editor": "editor",
        "fail_node": "fail_node",
        END: END
    }
)

workflow = builder.compile()

# %%
task = "修正 layout-parser-paper.md 的标题结构。"

final_state = None
for step in workflow.stream(
    {"task": task, "messages": [HumanMessage(content=task)]},
    stream_mode="values",
):
    final_state = step
    if step.get("is_valid"):
        print("✅ 审计通过！")
    elif step.get("audit_feedback") and not step.get("is_valid"):
        preview = step["audit_feedback"][:500]
        print(f"📋 第 {step.get('attempts', '?')} 次审计未通过：\n{preview}...")
