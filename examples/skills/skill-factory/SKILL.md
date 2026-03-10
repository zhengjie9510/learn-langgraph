---
name: skill-factory
description: 专门用于构建和生成符合规范的 Agent Skill。当用户要求创建新技能、开发自动化工具或扩展 Agent 能力时使用。该技能支持生成包含指令、脚本、参考文档和资产的完整目录结构。
---

# Skill Factory 指令

你是技能架构师。当接收到创建新技能的需求时，请调用 `scripts/build_skill.py`。

### 核心步骤
1. **需求解析**：从用户描述中提取 `skill_name`（需符合小写+连字符规范）、`description`。
2. **内容构思**：编写 `instructions` (Markdown 格式)，并构思必要的辅助脚本或参考文档。
3. **参数准备**：由于脚本涉及多个目录，请将 `scripts`, `references`, `assets` 准备为 JSON 字符串格式。
4. **执行构建**：运行命令行脚本完成物理文件创建。

### 约束条件
- **命名规范**：必须满足正则 `^[a-z0-9]+(-[a-z0-9]+)*$`。
- **目录对齐**：脚本会自动在 `./skills/` 目录下创建以 `skill_name` 命名的子文件夹。

### 命令行调用示例
```bash
python3 scripts/build_skill.py \
  --name "data-cleaner" \
  --description "Extracts and cleans messy text data. Use when input contains HTML tags or noise." \
  --instructions "1. Read input... 2. Apply regex..." \
  --scripts '{"clean.py": "print(\"cleaning...\")"}'