# CodeRAG-Agent

**基于 RAG + ReAct + LangGraph 的代码库智能问答系统（V2 优化版）**

## V2 新特性 🚀

### 📝 Memory 系统
- **MEMORY.md**: 长期记忆（项目知识、用户偏好、经验教训）
- **Daily Logs**: 每日交互记录
- **跨会话持久化**: Agent能记住你的偏好

### 🎯 Context 优先级组装
```
System Prompt → AGENTS.md → Memory → Tools → RAG Results → History
```
- Token预算管理
- 智能压缩策略
- 不超出上下文窗口

### 🔧 Skill 动态加载
```python
# 按需加载技能，节省78% Token
agent.load_skill("code_search")
agent.load_skill("git_ops")
```

### 🛡️ Guardrails 护栏
- 四级风险控制（Low → Medium → High → Critical）
- Prompt注入检测
- 敏感信息过滤

### 🔄 Agent Loop 优化
- 循环检测（防止无限重复）
- 错误恢复机制
- 流式输出支持

---

## 核心特性

### 🚀 RAG 全链路
- **代码解析**: Tree-sitter AST 解析，支持多语言
- **语义分块**: 按函数/类级别切分
- **混合检索**: Vector + BM25 组合
- **重排序**: Cross-Encoder 精排

### 🧠 ReAct 循环
- Thought → Action → Observation
- 动态工具选择，多步推理
- **V2新增**: 循环检测 + 错误恢复

### ⚙️ LangGraph 工作流
```
START → classify_intent → search_code → generate_answer → review → END
```
- ✅ 条件边路由
- ✅ 状态检查点
- ✅ 人机协作

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY

# 运行 Web 界面
cd web
python app.py

# 或运行 API
cd src/api
python main.py
```

## 项目结构

```
CodeRAG-Agent/
├── config/settings.py     # 配置
├── src/
│   ├── indexer/           # 代码索引
│   │   ├── parser.py      # AST解析
│   │   ├── chunker.py     # 分块
│   │   └── embedder.py    # 向量化
│   ├── retriever/         # RAG检索
│   │   ├── vector_store.py
│   │   ├── hybrid_search.py
│   │   └── reranker.py
│   ├── agent/             # Agent模块
│   │   ├── tools.py
│   │   ├── react_agent.py
│   │   └── graph.py       # LangGraph
│   └── api/               # FastAPI
├── web/app.py             # Gradio界面
└── tests/                 # 测试
```

## 测试

```bash
pytest tests/ -v
```

## License

MIT
