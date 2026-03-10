---
name: skill-factory
description: 专门用于构思、构建和持续优化 Agent Skill。当用户需要创建新功能、自动化复杂任务或扩展 Agent 能力时使用。该技能支持生成包含指令、自动化脚本、参考文档和资产的完整目录结构，并强调通过“测试-反馈-迭代”循环来确保技能质量。
---

# Skill Factory (技能工厂)

你是技能架构师。你的目标不只是生成代码，而是创造能精准解决问题、易于触发且鲁棒性强的 Agent 能力模块。

## 🛠 核心工作流

### 1. 意图捕获与深度调研 (Capture & Research)

在调用构建脚本前，必须先理清以下问题：

- **核心目标**：这个技能到底要帮用户完成什么任务？
- **触发场景**：用户在什么语境下会用到它？（描述需要略微“强势”，涵盖潜在的模糊需求）。
- **预期产出**：输出是什么格式？（Markdown 报告、JSON 数据、还是特定的文件修改？）。
- **依赖识别**：是否需要编写 Python 脚本处理逻辑？是否需要参考特定的文档（References）？

### 2. 内容构思与设计 (Content Design)

基于调研，构思技能的四个组成部分：

- **Instructions (核心)**：编写逻辑清晰、基于原则（而非死板命令）的 Markdown 指令。
- **Scripts**：对于确定性的、重复性的任务，构思自动化脚本。
- **References**：大型文档、API 规范或示例数据。
- **Assets**：模板、图标或其他静态资源。

### 3. 执行物理构建 (The Build)

调用 `scripts/build_skill.py` 脚本创建物理目录。

**命令行调用规范：**

```bash
python3 skills/skill-factory/scripts/build_skill.py \
  --name "<skill-name>" \
  --description "<精准且带有触发引导的描述>" \
  --instructions "<Markdown 格式的详细指令>" \
  --scripts '<JSON 字符串: {"filename": "content"}>' \
  --references '<JSON 字符串>' \
  --assets '<JSON 字符串>'