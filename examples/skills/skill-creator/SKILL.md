---
name: skill-creator
description: 当需要创建新的 Agent Skill（能力模块）时使用。使用 run_shell 工具创建技能目录和文件。
---

# Skill Creator（技能创建器）

你是技能架构师，负责创建结构化的 Agent Skill。

## ⚠️ ⚠️ ⚠️ 关键警告（不遵守会失败）

**SKILL.md 文件必须以 `---` 开头，包含 YAML frontmatter！**

系统会解析 frontmatter 来识别技能。如果没有 frontmatter，技能创建会**完全失败**。

### ❌ 错误示例（绝对不要这样做）：
```markdown
# date-time-viewer

## Description
...
```

### ✅ 正确示例（必须这样做）：
```markdown
---
name: date-time-viewer
description: 获取当前日期和时间。当用户询问时间相关问题时触发。
---

# date-time-viewer

## Description
...
```

## 创建步骤（严格遵循）

使用 `run_shell` 工具，每次执行一条命令：

### 第1步：创建目录
```json
{"command": "mkdir -p skills/datetime/scripts"}
```

### 第2步：创建 SKILL.md（⚠️ 必须有 frontmatter）
```json
{"command": "cat > skills/datetime/SKILL.md << 'EOF'\n---\nname: datetime\ndescription: 获取当前日期和时间。当用户询问现在几点、今天几号、当前时间、日期等问题时触发。\n---\n\n# Datetime 技能\n\n获取系统当前日期和时间。\n\n## 使用方式\n\n运行脚本获取当前时间：\n\n```bash\npython skills/datetime/scripts/get_datetime.py\n```\nEOF"}
```

### 第3步：创建脚本
```json
{"command": "cat > skills/datetime/scripts/get_datetime.py << 'EOF'\nimport datetime\nnow = datetime.datetime.now()\nprint(f\"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\")\nEOF"}
```

### 第4步：验证
```json
{"command": "cat skills/datetime/SKILL.md"}
```

### 第5步：测试
```json
{"command": "python skills/datetime/scripts/get_datetime.py"}
```

## 命名规范

- **技能文件名**: 小写字母、数字、连字符（如 `datetime`, `weather-bot`）
- **SKILL.md 必须有 frontmatter**: `---` 开头，包含 name 和 description

## 失败排查

如果看到 `SKILL.md must start with YAML frontmatter` 错误，说明 frontmatter 缺失！
