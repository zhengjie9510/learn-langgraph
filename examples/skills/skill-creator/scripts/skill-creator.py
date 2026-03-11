import os
import re
import argparse


def create_simple_skill(
        skill_name: str,
        description: str,
        instructions: str,
        script_name: str = None,
        script_content: str = None
) -> str:
    # --- 核心修复：中文友好的转义还原 ---
    def safe_decode(text: str) -> str:
        if not text:
            return ""
        # 仅手动还原最核心的转义符，不触碰编码，彻底避免中文乱码
        return text.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace("\\'", "'")

    # 还原指令和代码内容
    instructions = safe_decode(instructions)
    script_content = safe_decode(script_content)

    # 1. 基础校验
    pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"
    if not re.match(pattern, skill_name):
        return f"❌ 名字不合规: '{skill_name}'。仅限小写字母、数字和连字符 (-)"

    # 2. 确定路径
    base_path = os.path.join("./skills", skill_name)

    try:
        os.makedirs(base_path, exist_ok=True)

        # 3. 写入说明文档 (SKILL.md)
        skill_md = f"""---
name: {skill_name}
description: {description}
---

# {skill_name} 指令

{instructions.strip()}
"""
        with open(os.path.join(base_path, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(skill_md)

        # 4. 写入脚本
        if script_name and script_content:
            script_dir = os.path.join(base_path, "scripts")
            os.makedirs(script_dir, exist_ok=True)
            with open(os.path.join(script_dir, script_name), "w", encoding="utf-8") as f:
                f.write(script_content)

        return f"✅ 成功！Skill 已写入并修复中文格式: {base_path}"

    except Exception as e:
        return f"❌ 写入失败: {str(e)}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Skill Builder (Chinese Friendly)")
    parser.add_argument("--name", required=True)
    parser.add_argument("--desc", required=True)
    parser.add_argument("--inst", required=True)
    parser.add_argument("--s_name", help="脚本文件名")
    parser.add_argument("--s_content", help="脚本内容")

    args = parser.parse_args()

    result = create_simple_skill(
        skill_name=args.name,
        description=args.desc,
        instructions=args.inst,
        script_name=args.s_name,
        script_content=args.s_content
    )
    print(result)
