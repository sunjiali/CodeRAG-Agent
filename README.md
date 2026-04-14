# CodeRAG-Agent

**基于 RAG + ReAct + LangGraph 的代码库智能问答系统**

*为字节跳动 Agent 架构工程师面试准备的实战项目*

## 核心特性

### 🚀 RAG 全链路
- **代码解析**: Tree-sitter AST 解析，支持多语言
- **语义分块**: 按函数/类级别切分
- **混合检索**: Vector + BM25 组合
- **重排序**: Cross-Encoder 精排

### 🧠 ReAct 循环
- Thought → Action → Observation
- 动态工具选择，多步推理

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
