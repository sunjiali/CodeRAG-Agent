# CodeRAG-Agent 优化路线图

> 基于 Harness Engineering Guide 的系统化优化方案

## 当前状态分析

### 已有优势
- ✅ RAG全链路：Tree-sitter解析 → 语义分块 → 混合检索 → 重排序
- ✅ ReAct循环：Thought → Action → Observation
- ✅ LangGraph工作流：意图分类 → 搜索 → 生成 → 审核
- ✅ 基础工具系统：搜索、分析、读取、列表

### 待优化方向

| 模块 | 当前状态 | 目标状态 |
|-----|---------|---------|
| **Memory** | 无持久化记忆 | MEMORY.md + Daily Logs |
| **Context** | 简单拼接 | 优先级组装 + Token预算 |
| **Tools** | 静态加载 | Skill系统 + 按需加载 |
| **Guardrails** | 无 | 权限模型 + 沙箱 |
| **Agent Loop** | 基础循环 | 循环检测 + 错误恢复 + 流式 |
| **Multi-Agent** | 单Agent | Sub-agent支持 |

---

## 优化阶段规划

### Phase 1: Memory & Context（记忆与上下文）
**优先级：最高 | 预计工作量：2-3天**

#### 1.1 添加MEMORY.md模式
```
memory/
├── MEMORY.md           # 长期记忆（项目知识、用户偏好、经验教训）
├── daily/              # 每日日志
│   └── 2026-04-16.md   # 原始交互记录
└── wiki/               # 结构化知识库
    ├── architecture.md
    └── patterns.md
```

#### 1.2 上下文优先级组装
```python
Context Window (按优先级填充):
┌─────────────────────────────────┐
│  System Prompt        (~500)    │  ← P0: 最高优先级
│  Tool Schemas         (~2000)   │  ← P1: 活跃工具
│  Memory Summary       (~1000)   │  ← P2: 记忆摘要
│  Relevant Code        (~5000)   │  ← P3: RAG检索结果
│  Conversation History (~varies) │  ← P4: 历史对话
└─────────────────────────────────┘
```

#### 1.3 Token预算管理
- 设置最大token限制
- 实现压缩策略（总结旧对话）
- 动态调整上下文窗口

---

### Phase 2: Skill System（技能系统）
**优先级：高 | 预计工作量：3-4天**

#### 2.1 Skill目录结构
```
skills/
├── code_search/
│   ├── SKILL.md          # 使用文档
│   ├── tools.py          # 工具实现
│   └── schema.json       # 工具模式
├── code_analysis/
│   ├── SKILL.md
│   └── ...
├── git_ops/
│   ├── SKILL.md
│   └── ...
└── web_search/
    ├── SKILL.md
    └── ...
```

#### 2.2 SKILL.md格式示例
```markdown
# Code Search Skill

## When to Use
- 用户询问某个函数/类的实现位置
- 需要查找特定功能的代码
- 理解代码架构和调用关系

## Available Tools
- `search_code`: 语义搜索代码块
- `search_by_name`: 按函数/类名精确搜索
- `search_by_pattern`: 正则模式搜索

## Conventions
- 搜索前先理解用户意图
- 返回结果附带上下文（前后10行）
- 标注文件路径和行号

## Examples
1. "找到处理用户认证的代码" → search_code("user authentication")
2. "UserService类在哪里" → search_by_name("UserService")
```

#### 2.3 动态加载机制
```python
SKILL_MENU = """
Available skills (use load_skill to activate):
- code_search: 语义搜索代码库
- code_analysis: 代码理解和分析
- git_ops: Git操作（diff, log, blame）
- web_search: 联网搜索技术文档
"""
```

---

### Phase 3: Agent Loop优化
**优先级：高 | 预计工作量：2天**

#### 3.1 循环检测
```python
def detect_loop(messages: list, window: int = 3) -> bool:
    """检测是否陷入循环（连续相同工具调用）"""
    recent_calls = extract_tool_calls(messages[-window*2:])
    if len(set(recent_calls[-window:])) == 1:
        return True  # 卡住了
    return False
```

#### 3.2 错误恢复机制
- 工具失败时返回明确错误信息
- 模型可以自适应调整策略
- 设置最大重试次数

#### 3.3 流式输出
```python
for chunk in llm.stream(messages):
    yield chunk  # 实时返回给用户
```

---

### Phase 4: Guardrails（护栏）
**优先级：中 | 预计工作量：2天**

#### 4.1 权限模型
```python
RISK_LEVELS = {
    "low": ["read_file", "search_code"],      # 自动批准
    "medium": ["write_file", "run_command"],  # 需确认
    "high": ["delete_file", "git_push"],      # 必须人工批准
}
```

#### 4.2 输入过滤
- 检测prompt注入
- 过滤敏感信息（API Key等）
- 限制文件操作范围

---

### Phase 5: Multi-Agent支持
**优先级：中 | 预计工作量：3-4天**

#### 5.1 Sub-agent spawning
```python
# 主Agent可以委派子任务
subagent = spawn_agent(
    task="深入分析这个模块的调用链",
    tools=["code_search", "code_analysis"],
    model="gpt-4o-mini",  # 用便宜模型做执行
)
```

#### 5.2 任务协调模式
- Leader-Worker: 主Agent分配，子Agent执行
- 并行执行: 多个子Agent同时处理
- 结果聚合: 收集子Agent结果整合

---

### Phase 6: AGENTS.md行为规范
**优先级：中 | 预计工作量：1天**

```markdown
# AGENTS.md - CodeRAG-Agent行为规范

## Role
你是一个代码库智能助手，帮助用户理解、搜索、分析代码。

## Behavior
- 回答前先理解用户真实意图
- 引用代码时标注文件路径和行号
- 不确定时主动询问澄清
- 复杂问题分步骤解决

## Constraints
- 不要修改用户代码（除非明确要求）
- 不要执行可能破坏性的操作
- 涉及敏感信息时请求确认

## Tools
- 优先使用 search_code 语义搜索
- 需要精确匹配时用 search_by_name
- 理解代码时用 analyze_code
```

---

## 实施优先级

| 阶段 | 内容 | 价值 | 工作量 | 优先级 |
|-----|------|------|--------|-------|
| Phase 1 | Memory & Context | ⭐⭐⭐⭐⭐ | 2-3天 | P0 |
| Phase 2 | Skill System | ⭐⭐⭐⭐ | 3-4天 | P1 |
| Phase 3 | Agent Loop | ⭐⭐⭐⭐ | 2天 | P1 |
| Phase 4 | Guardrails | ⭐⭐⭐ | 2天 | P2 |
| Phase 5 | Multi-Agent | ⭐⭐⭐ | 3-4天 | P2 |
| Phase 6 | AGENTS.md | ⭐⭐ | 1天 | P3 |

---

## 快速启动建议

从Phase 1和Phase 3开始：
1. **先加MEMORY.md** - 让Agent能记住用户的偏好和项目知识
2. **优化Agent Loop** - 加循环检测和错误恢复
3. **再建Skill系统** - 按需加载工具

---

## 参考资源
- [Harness Engineering Guide](https://harness-guide.com/)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [OpenClaw Skills Architecture](https://docs.openclaw.ai)
