from pathlib import Path
from skills_ref import to_prompt

# 1. 扫描所有包含 SKILL.md 的子目录
skills_root = Path("./skills")
skill_paths = [p for p in skills_root.iterdir() if p.is_dir() and (p / "SKILL.md").exists()]

# 2. 生成标准 Prompt 块
# 这里的 prompt 会包含所有技能的 name 和 description (XML 或 Markdown 格式)
skills_catalog = to_prompt(skill_paths)
print(skills_catalog)

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
- **路径感知**：在执行脚本或引用资产时，请确保使用相对于当前工作目录的完整路径（例如 `python3 skills/pdf-parser/scripts/main.py`）。
- **结果导向**：利用技能提供的信息解决问题后，请以自然、简洁的方式向用户反馈结果，无需过多强调背后的技能读取细节（除非用户询问）。
"""


def get_skill_instruction(skill_name: str) -> str:
    """
    根据技能名称，从本地技能库中检索并返回详细的操作手册和指令。

    参数:
    - skill_name: 技能的唯一标识符（文件夹名），例如 'pdf-parser'。

    返回:
    - 字符串内容：包含技能的详细 Markdown 指令。如果技能不存在，返回错误提示。
    """
    # 1. 设定技能根目录（建议设为配置项或环境变量）
    SKILLS_DIR = Path("./skills")

    # 2. 构建目标文件路径
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"

    # 3. 检查文件是否存在
    if not skill_file.exists():
        return f"❌ 错误：技能 '{skill_name}' 不存在于技能库中。请检查名称是否正确。"

    try:
        # 4. 读取文件内容
        content = skill_file.read_text(encoding="utf-8")

        # 5. 提取操作指令 (剥离 YAML Frontmatter)
        # 规范要求 Frontmatter 由 --- 包围
        if content.startswith("---"):
            parts = content.split("---", 2)  # 分割成 ['', 'metadata', 'body']
            if len(parts) >= 3:
                instruction_body = parts[2].strip()
            else:
                instruction_body = content.strip()
        else:
            instruction_body = content.strip()

        # 6. (可选) 扫描并附带 scripts 目录下的文件名清单，增强模型的感知
        scripts_dir = SKILLS_DIR / skill_name / "scripts"
        scripts_info = ""
        if scripts_dir.exists() and scripts_dir.is_dir():
            files = [f.name for f in scripts_dir.iterdir() if f.is_file()]
            if files:
                scripts_info = f"\n\n### 可用脚本列表 (位于 {scripts_dir}/):\n- " + "\n- ".join(files)

        return f"## 技能详情: {skill_name}\n\n{instruction_body}{scripts_info}"

    except Exception as e:
        return f"❌ 读取技能时发生异常: {str(e)}"
