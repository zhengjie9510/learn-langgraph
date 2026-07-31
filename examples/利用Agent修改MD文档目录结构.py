from typing import Annotated
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.graph.message import add_messages
from deepagents.backends import FilesystemBackend
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, BaseMessage
from deepagents.middleware.filesystem import FilesystemMiddleware

load_dotenv()

model = ChatOpenAI(
    model="deepseek-v4-pro",
    model_kwargs={"extra_body": {"thinking": {"type": "disabled"}}},
    temperature=0.2
)

backend = FilesystemBackend(root_dir="../examples-data", virtual_mode=True)

EDITOR_SYSTEM_PROMPT = """\
你是 Markdown 文档目录结构整理专家。修改文件只能用 Edit 工具。

## 工作流程
1. **提取标题**：使用 Grep 命令提取出文件中的所有 Markdown 标题及行号。如果文件开头有 TOC 目录，Read 前 100 行即可。不要一次性读整个文件。
2. **比对分析**：将标题与 TOC 对比，找出层级错位、遗漏、多余 # 等问题。
3. **逐项修改**：用 Edit 逐处修正，每改一处确认无误再改下一处。
4. **复核**：改完再用 Grep 提取一遍，确认全部修正。

## 修改规则
- **标题绝对层级**：最高章节必须从 `#` 开始，禁止整体偏移或跳跃（如 `#` 直接到 `###`）。
- **降级非章节标题**：正文开头的封面大标题和字面为「目录」的行不是章节，降级为 **加粗**。
- **降级非 TOC 小标题**：正文中更细碎的编号（未在 TOC 中出现），改为 **加粗**。
- **补充缺失标题**：TOC 中有但正文遗漏 # 的章节，补上 # 标题。
- **清理格式**：去除锚点标记，`#` 与标题文字间保留一个半角空格。

注意：如果你收到了 Auditor (审计员) 的反馈，请务必严格按照其指出的具体行号和问题进行针对性修复！
"""

edit_agent = create_agent(
    model,
    system_prompt=EDITOR_SYSTEM_PROMPT,
    middleware=[FilesystemMiddleware(backend=backend)],
)

AUDITOR_SYSTEM_PROMPT = """\
你是 Markdown 文档结构审计员。用工具检查文件的标题结构是否符合基本规范。

## 工作流程

1. 用 Grep 提取所有标题行。
2. 检查结构：
   - `#` 一级、`##` 二级、`###` 三级，以此类推
   - 最高章节从 `#` 开始，层级逐级递进，不跳跃（如 `#` 直接到 `###`）
   - `#` 与文字间有空格

## 输出

通过：回复末尾包含 `[AUDIT_PASS]`
不通过：指出具体行号和问题，末尾包含 `[AUDIT_FAIL]`
"""

auditor_agent = create_agent(
    model,
    system_prompt=AUDITOR_SYSTEM_PROMPT,
    middleware=[FilesystemMiddleware(backend=backend)],
)


class AgentState(BaseModel):
    task: str = ""
    target_file: str = ""  # 明确目标文件
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    is_valid: bool = False
    attempts: int = 0
    audit_feedback: str = ""


def editor_node(state: AgentState) -> dict:
    """调用编辑 Agent，正确处理消息历史切片"""
    print(f"✏️ [Editor] 正在进行第 {state.attempts + 1} 次修改...")

    result = edit_agent.invoke({"messages": state.messages})

    input_message_count = len(state.messages)
    new_messages = result["messages"][input_message_count:]

    if not new_messages:
        new_messages = [result["messages"][-1]]

    return {
        "messages": new_messages,
        "attempts": state.attempts + 1,
    }


def auditor_node(state: AgentState) -> dict:
    """调用审计 Agent，使用严格的结构化标记判断"""
    print("🔍 [Auditor] 正在审计文件结构...")

    audit_prompt = (
        f"背景：编辑 agent 刚刚修改了文件（任务：{state.task}）。\n"
        f"请严格审计该文件。如果存在问题，请指出具体行号。"
    )

    result = auditor_agent.invoke({
        "messages": [HumanMessage(content=audit_prompt)]
    })

    feedback = result["messages"][-1].content.strip()

    if "[AUDIT_PASS]" in feedback:
        return {"is_valid": True, "audit_feedback": feedback}

    print("❌ [Auditor] 审计未通过，打回重改。")

    retry_message = HumanMessage(
        name="Auditor",
        content=(
            f"你的修改未通过审计 (这是第 {state.attempts} 次尝试)。\n"
            f"以下是审计员的反馈：\n{feedback}\n\n"
            f"请立刻使用工具修正上述具体问题。"
        )
    )

    return {
        "is_valid": False,
        "audit_feedback": feedback,
        "messages": [retry_message],
    }


def fail_node(state: AgentState) -> dict:
    raise RuntimeError(f"🚨 经过 {state.attempts} 次修改仍未通过审计，流程终止。最后一次反馈：\n{state.audit_feedback}")


def should_continue(state: AgentState) -> str:
    if state.is_valid:
        return END
    if state.attempts >= 3:
        return "fail_node"
    return "editor"


builder = StateGraph(AgentState)
builder.add_node("editor", editor_node)
builder.add_node("auditor", auditor_node)
builder.add_node("fail_node", fail_node)

builder.add_edge(START, "editor")
builder.add_edge("editor", "auditor")
builder.add_conditional_edges("auditor", should_continue, {
    "editor": "editor",
    "fail_node": "fail_node",
    END: END,
})

workflow = builder.compile()

if __name__ == "__main__":
    md_file = "广西管道公司管道主干线地质灾害专业排查及风险评估项目地质灾害专业排查及风险评估报告(审改版).md"
    task_desc = f"修正 {md_file} 的标题结构。"

    initial_state = {
        "task": task_desc,
        "target_file": md_file,
        "messages": [HumanMessage(content=task_desc)]
    }

    for step in workflow.stream(initial_state, stream_mode="updates"):
        if "auditor" in step:
            if step["auditor"].get("is_valid"):
                print("\n✅ 最终结果：审计通过！文件修改完成。")
            else:
                print(f"\n📋 审计反馈:\n{step['auditor']['audit_feedback']}")
