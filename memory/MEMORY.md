# MEMORY.md - CodeRAG-Agent 长期记忆

> 跨会话持久化的项目知识和用户偏好

## 项目知识

### 架构概览
```
CodeRAG-Agent/
├── src/
│   ├── indexer/     # 代码索引（AST解析、分块、向量化）
│   ├── retriever/   # RAG检索（向量存储、混合搜索、重排序）
│   ├── agent/       # Agent核心（ReAct循环、工具、LangGraph）
│   └── api/         # FastAPI接口
├── config/          # 配置管理
├── web/             # Gradio界面
└── memory/          # 记忆系统（本目录）
```

### 核心组件
- **parser.py**: Tree-sitter AST解析，支持Python/JS/Go/Java/Rust
- **chunker.py**: 按函数/类级别切分代码
- **hybrid_search.py**: Vector + BM25 混合检索
- **reranker.py**: Cross-Encoder 精排
- **graph.py**: LangGraph工作流（意图分类→搜索→生成→审核）

### 技术栈
- LLM: OpenAI GPT-4 / Ollama
- Embedding: text-embedding-3-small / nomic-embed-text
- Vector DB: Chroma
- Framework: LangChain + LangGraph

## 用户偏好

### 回答风格
- 代码引用格式：`file_path:line_number`
- 偏好简洁回答，避免冗长解释
- 喜欢看到具体代码示例

### 搜索偏好
- 优先语义搜索，必要时精确匹配
- 返回结果数量：5条
- 需要上下文（前后各10行）

## 经验教训

### 2026-04-16: 初始化记忆系统
- 项目已具备基础RAG能力
- 需要添加持久化记忆
- 需要实现Skill系统按需加载工具

## 待办事项

- [x] 实现两层记忆架构（MEMORY.md + Daily Logs）
- [x] 添加上下文优先级组装（ContextAssembler）
- [x] 构建Skill系统（SkillRegistry + code_search示例）
- [x] 添加Guardrails（权限模型 + 输入过滤）
- [x] Agent Loop优化（循环检测 + 错误恢复）
- [ ] Multi-Agent支持（Sub-agent spawning）
- [ ] 完善Web界面集成V2模块
- [ ] 添加更多Skill（git_ops, code_analysis, web_search）

## 2026-04-16 优化记录

### 已完成
1. **Memory系统** (`src/agent/memory.py`)
   - MEMORY.md长期记忆
   - Daily Logs每日记录
   - 偏好学习和经验记录

2. **Context组装** (`src/agent/context.py`)
   - 优先级填充（System > Memory > Tools > RAG > History）
   - Token预算管理
   - 自动压缩策略

3. **Skill系统** (`src/agent/skill_registry.py`)
   - 按需加载技能
   - 节省Token（78%优化）
   - code_search示例Skill

4. **Guardrails** (`src/agent/guardrails.py`)
   - 四级风险控制
   - Prompt注入检测
   - 敏感信息过滤

5. **Agent Loop增强** (`src/agent/enhanced_loop.py`)
   - 循环检测
   - 错误恢复
   - 流式输出支持

### 新增文件
- `memory/MEMORY.md` - 长期记忆
- `AGENTS.md` - 行为规范
- `skills/code_search/SKILL.md` - 代码搜索技能
- `src/agent/memory.py` - 记忆管理
- `src/agent/context.py` - 上下文组装
- `src/agent/skill_registry.py` - 技能注册
- `src/agent/guardrails.py` - 护栏系统
- `src/agent/enhanced_loop.py` - 增强循环
- `src/agent/v2.py` - V2整合入口
- `tests/test_v2.py` - 单元测试
- `OPTIMIZATION.md` - 优化路线图
