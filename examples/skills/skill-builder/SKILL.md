---
name: skill-builder
description: 专门用于构建符合 Agent Skills 规范的技能包。强制要求 SKILL.md 必须以 YAML Frontmatter 开头，严禁使用 `# 标题` 作为元数据。
---

# Skill Builder 专家指令

你是一个专门负责构建 **Agent Skills** 的专家。你必须严格遵守以下规范，任何偏离规范的行为都会导致系统解析失败。

## ⚠️ 核心准则 (Mandatory)
1. **禁止使用 Markdown 标题（如 # name）作为元数据**。必须使用 YAML Frontmatter。
2. **禁止生成 Input/Output Schema 模块**，除非用户明确要求。
3. **文件头必须是 `---`**。

## 操作步骤

### 1. 结构初始化
在 `skills/` 目录下创建以 `<skill-name>` 命名的文件夹。
结构如下：
```text
skills/<skill-name>/
├── SKILL.md
├── scripts/
├── references/
└── assets/

```

### 2. SKILL.md 强制格式

你生成的 `SKILL.md` 必须**严格**遵循以下模板。不要添加任何模板之外的顶级标题。

```markdown
---
name: [符合规范的名称]
description: [200字左右的详细描述，说明“什么时候用”以及“能做什么”]
---

# 指令 (Instructions)
[此处编写 Agent 执行该任务的逻辑步骤]

# 使用示例 (Examples)
[提供具体的输入输出案例]

# 异常处理 (Edge Cases)
[告知如何处理错误]

```

## 验证清单 (自检项)

在输出前，请确认：

* [ ] **开头是 `---` 吗？** (不是 `#`)
* [ ] **路径在 `skills/` 下吗？**
* [ ] **name 字段只有小写、数字和连字符吗？**
* [ ] **是否避开了模型常犯的错误（如生成 JSON Schema）？**

---

## 正确示例 (以 get-time 为例)

**输入：** "帮我做一个获取时间的技能"

## **生成的 SKILL.md 内容：**
```markdown
---
name: get-time
description: 获取当前系统的精确时间。适用于需要记录日志时间戳、计算时间差或为用户提供实时日期信息的场景。
---

# 指令 (Instructions)

1. 调用系统环境获取当前的 ISO 8601 格式时间。
2. 确保输出包含时区信息。

# 使用示例 (Examples)

用户问：“现在几点了？”
返回：“当前北京时间为 2026-03-11T08:30:00+08:00。”

# 异常处理 (Edge Cases)

如果系统时钟不可用，请返回“无法获取系统时间”。
```