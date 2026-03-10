import os
import re
import json
import argparse
from typing import Optional, Dict


def create_agent_skill(
        skill_name: str,
        description: str,
        instructions: str,
        scripts: Optional[Dict[str, str]] = None,
        references: Optional[Dict[str, str]] = None,
        assets: Optional[Dict[str, str]] = None
) -> str:
    # 1. 严格校验
    pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"
    if not re.match(pattern, skill_name) or len(skill_name) > 64:
        return f"❌ 校验失败: skill_name '{skill_name}' 不合规。"

    if not (1 <= len(description) <= 1024):
        return "❌ 校验失败: description 长度必须在 1-1024 字符之间。"

    # 2. 设定根路径（默认输出到当前目录下的 skills 文件夹）
    base_path = os.path.join("./skills", skill_name)

    try:
        # 创建主目录
        os.makedirs(base_path, exist_ok=True)

        # 3. 写入 SKILL.md (带 YAML frontmatter)
        skill_md_content = f"""---
name: {skill_name}
description: {description}
---

# {skill_name}

{instructions.strip()}
"""
        with open(os.path.join(base_path, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(skill_md_content)

        # 4. 写入子目录及文件
        sub_dirs = {
            "scripts": scripts,
            "references": references,
            "assets": assets
        }

        for dir_name, content_dict in sub_dirs.items():
            if content_dict:
                dir_path = os.path.join(base_path, dir_name)
                os.makedirs(dir_path, exist_ok=True)
                for file_name, content in content_dict.items():
                    with open(os.path.join(dir_path, file_name), "w", encoding="utf-8") as f:
                        f.write(content)

        return f"✅ 成功！Agent Skill 已完整写入至: {base_path}"

    except Exception as e:
        return f"❌ 写入失败: {str(e)}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Skill Builder CLI")
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--instructions", required=True)
    # 接受 JSON 字符串作为输入
    parser.add_argument("--scripts", type=str, default='{}')
    parser.add_argument("--references", type=str, default='{}')
    parser.add_argument("--assets", type=str, default='{}')

    args = parser.parse_args()

    # 解析 JSON 字典
    try:
        res = create_agent_skill(
            skill_name=args.name,
            description=args.description,
            instructions=args.instructions,
            scripts=json.loads(args.scripts),
            references=json.loads(args.references),
            assets=json.loads(args.assets)
        )
        print(res)
    except json.JSONDecodeError:
        print("❌ 错误: scripts/references/assets 参数必须是合法的 JSON 字符串")
