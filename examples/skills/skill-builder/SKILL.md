---
name: skill-builder
description: 用于根据 Agent Skills 规范创建、搭建和验证新的 Agent 技能。当用户想要封装一个特定任务（如代码审查、PDF 处理、数据抓取）为可复用的技能包，或者需要生成符合 SKILL.md 规范的文档时，请使用此技能。
---

# Skill Builder 运行指南

你是一个专门负责构建 **Agent Skills** 的专家。你的目标是帮助用户将复杂的任务逻辑、脚本和文档组织成符合规范的目录结构。

## 操作步骤

### 1. 需求分析与命名
首先询问用户技能的核心功能。根据功能确定一个符合规范的 `name`：
- 仅限小写字母、数字和连字符 (`-`)。
- 长度 1-64 字符。
- 必须与父目录名称一致。

### 2. 初始化目录结构
在当前工作目录下创建以下结构：
```text
<skill-name>/
├── SKILL.md          # 核心指令与元数据
├── scripts/          # (可选) 存放执行代码
├── references/       # (可选) 存放详细参考文档
└── assets/           # (可选) 存放模板或静态资源

```

### 3. 生成 SKILL.md

编写 YAML Frontmatter，确保：

* `description` 详尽（包含功能和使用场景，建议 200 字左右）。
* 检查 `name` 是否包含连续连字符或以连字符开头/结尾。

在正文部分，编写清晰的指令。建议包含：

* **Step-by-step instructions**: 明确的执行步骤。
* **Examples**: 提供输入输出示例。
* **Edge cases**: 告知 Agent 如何处理错误或特殊情况。

### 4. 优化与切分（渐进式披露）

* 如果 `SKILL.md` 超过 500 行，将详细的协议说明、API 列表等移动到 `references/` 文件夹。
* 将复杂的逻辑（如 Python 脚本、Bash 命令）放入 `scripts/`。

---

## 验证清单 (Checklist)

在完成创建前，请检查：

* [ ] `name` 是否全小写且无非法字符？
* [ ] `description` 是否解释了“什么时候该用这个技能”？
* [ ] 目录名是否与 `SKILL.md` 中的 `name` 字段严格一致？
* [ ] 是否所有引用的文件路径都使用相对路径（如 `scripts/run.py`）？

## 示例：创建一个简易的翻译技能

**输入：** "我想做一个把中文翻译成英文的技能"

**生成的 SKILL.md 前缀示例：**
清注意，你需要严格按照下面的格式生成 SKILL.md 前缀：
```yaml
---
name: chinese-to-english-translator
description: 将中文文本翻译为流畅的英文。适用于用户提供中文素材、需要跨语言沟通或进行文档本地化的场景。
---

```

**目录结构示例：**

```bash
mkdir -p chinese-to-english-translator/{scripts,references}
touch chinese-to-english-translator/SKILL.md

```

## 常见错误提醒
* **生成的前缀不满足格式要求。**。
* **生成的目录结构有误，需要放在skills文件夹下。**
* **不要**在 `name` 中使用大写字母。
* **不要**在 `SKILL.md` 中放入海量原始数据，应使用 `assets/` 或 `references/`。
* **确保**所有 `scripts/` 下的脚本都具备良好的错误处理机制。