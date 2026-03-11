# %%
import shlex
import subprocess
from pathlib import Path
from typing import Callable
from dotenv import load_dotenv
from skills_ref import to_prompt
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.messages import SystemMessage
from langchain_core.messages import HumanMessage
from langchain_community.tools import ShellTool
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

load_dotenv()


# %%
@tool
def get_skill_instruction(skill_name: str) -> str:
    """获取指定技能的详细指令及脚本清单。"""
    base = Path("./skills") / skill_name
    file = base / "SKILL.md"

    if not file.exists():
        return f"错误：找不到技能 {skill_name}"

    content = file.read_text(encoding="utf-8")
    body = content.split("---")[-1].strip()

    scripts = [f.name for f in (base / "scripts").glob("*") if f.is_file()]
    script_info = f"\n\n📂 **可用脚本**: {', '.join(scripts)}" if scripts else "\n\n📂 **可用脚本**: 无"

    return (
        f"# {skill_name} 详情\n"
        f"📍 **技能路径**: `{base}`\n\n"
        f"{body}"
        f"{script_info}"
    )


@wrap_model_call
def add_context(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    skills_root = Path("./skills")
    skill_paths = [p for p in skills_root.iterdir() if p.is_dir() and (p / "SKILL.md").exists()]
    skills_catalog = to_prompt(skill_paths)
    system_prompt = f"""
# Role
你是一个功能强大的通用人工智能助手。为了更高效、精准地完成复杂任务，你拥有访问“专用技能库”的权限。

# 技能目录 (Skill Catalog)
以下是你当前可以调用的扩展技能列表。每个技能包含名称和核心功能简述：

{skills_catalog}

# 核心操作逻辑 (Operating Logic)
当你处理用户请求时，请遵循以下决策流程：

1. **意图匹配**：判断用户需求是否落在上述 [技能目录] 的覆盖范围内。
2. **按需检索**：如果你决定使用某个技能，**严禁凭经验盲目猜测其操作细节**。你必须立即调用工具 `get_skill_instruction(skill_name)` 来获取该技能的“详细操作手册”。
3. **知识利用**：
    - 阅读手册中提供的执行步骤、参数规范及约束条件。
    - 如果手册中提到需要运行特定的脚本（通常位于 `skills/技能名/scripts/`），请严格按照说明执行对应的命令行操作。
4. **组合执行**：你可以根据任务复杂度，依次检索并利用多个技能来构建完整的解决方案。

# 行为约束
- **先读后做**：在未获取详细指令前，不得尝试调用该技能目录下的任何脚本或文件。
- **路径感知**：使用相对于当前工作目录的完整路径。
- **Shell 转义安全 (重要)**：
    - 当使用 `run_shell_command` 执行包含复杂参数（如 JSON）的命令时，**必须**使用单引号 `'` 包裹整个 JSON 字符串。
    - 在单引号包裹的 JSON 内部，**必须**使用双引号 `"` 来界定键和值。
    - 示例正确格式：`--scripts '{{"main.py": "print(1)"}}'`
- **结果导向**：利用技能解决问题后，简洁反馈结果。
"""
    system_message = SystemMessage(content=system_prompt)
    return handler(request.override(system_message=system_message))


# %%
agent = create_agent(ChatOpenAI(model="qwen-plus"), tools=[get_skill_instruction, ShellTool()],
                     middleware=[add_context])
from IPython.display import Image, display

# %%
user_query = "帮我创建一个可以获取时间的技能。"

inputs = {"messages": [HumanMessage(content=user_query)]}

for output in agent.stream(inputs, config={"recursion_limit": 20}, stream_mode="values"):
    output["messages"][-1].pretty_print()
# %%
user_query = "现在几点了"

inputs = {"messages": [HumanMessage(content=user_query)]}

for output in agent.stream(inputs, config={"recursion_limit": 10}, stream_mode="values"):
    output["messages"][-1].pretty_print()
