# Code Search Skill

> 语义搜索代码库的核心技能

## When to Use

- 用户询问某个函数/类的实现位置
- 需要查找特定功能的代码
- 理解代码架构和调用关系
- 查找某个概念或模式的实现

## Available Tools

### `search_code`
语义搜索代码块，返回相关度最高的代码片段。

**参数**:
- `query` (str): 搜索查询，可以是自然语言描述
- `top_k` (int): 返回结果数量，默认5

**返回**:
```json
{
  "results": [
    {
      "content": "代码内容",
      "file_path": "src/module.py",
      "start_line": 42,
      "end_line": 67,
      "score": 0.89,
      "entity_type": "function",
      "entity_name": "process_data"
    }
  ]
}
```

### `search_by_name`
按函数名/类名精确搜索。

**参数**:
- `name` (str): 函数名或类名
- `entity_type` (str, optional): "function" | "class" | "method"

### `search_by_pattern`
正则模式搜索代码。

**参数**:
- `pattern` (str): 正则表达式模式

## Conventions

1. **搜索前**：理解用户意图，必要时拆分为多个搜索
2. **搜索时**：优先使用语义搜索，精确匹配用名称搜索
3. **结果展示**：
   - 标注文件路径和行号
   - 提供上下文（前后各10行）
   - 说明代码作用

## Examples

### Example 1: 查找认证代码
```
用户: "找到处理用户认证的代码"

步骤:
1. search_code("user authentication login")
2. 分析返回结果的entity_type
3. 如果是类，用search_by_name精确获取

输出:
找到认证相关代码在 `src/auth/login.py:45-89`
```

### Example 2: 查找特定函数
```
用户: "UserService类在哪里"

步骤:
1. search_by_name("UserService", entity_type="class")
2. 如果没找到，search_code("UserService")

输出:
UserService类位于 `src/services/user.py:15-120`
```

### Example 3: 理解调用关系
```
用户: "这个函数被哪些地方调用"

步骤:
1. 获取函数名
2. search_by_pattern("function_name\\(")
3. 过滤非调用场景

输出:
`process_data()` 被以下位置调用:
- src/api/routes.py:34
- src/jobs/scheduler.py:89
```

## Tips

- 语义搜索对自然语言友好，但可能漏掉精确匹配
- 名称搜索快速准确，但需要知道确切名称
- 模式搜索灵活但需要理解正则
- 组合使用效果最佳
