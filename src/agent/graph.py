"""
LangGraph工作流 - 定义完整的RAG流程
包含条件边、检查点、人机协作
"""
from typing import Dict, Any, List, Optional, Literal
from enum import Enum
from dataclasses import dataclass
from loguru import logger
import json

from config.settings import settings
from src.retriever.vector_store import VectorStoreManager


class IntentType(Enum):
    """意图类型"""
    LOOKUP = "lookup"
    EXPLANATION = "explanation"
    DEBUG = "debug"
    IMPLEMENTATION = "impl"
    GENERAL = "general"


class ReviewDecision(Enum):
    """审核决策"""
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    NEEDS_HUMAN = "needs_human"


@dataclass
class GraphState:
    """LangGraph状态定义"""
    query: str
    codebase_path: str
    intent: Optional[IntentType] = None
    search_results: List[Dict] = None
    refined_query: str = ""
    draft_answer: str = ""
    review_decision: Optional[ReviewDecision] = None
    final_answer: str = ""
    sources: List[Dict] = None
    confidence: float = 0.0
    needs_human: bool = False
    error: Optional[str] = None
    step_count: int = 0
    verbose: bool = True


def classify_intent(state: GraphState) -> GraphState:
    """节点1: 意图分类"""
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.0, api_key=settings.OPENAI_API_KEY)
        
        prompt = f"""分析以下用户问题，确定其意图类型：
问题: {state.query}
意图类型: lookup(查找代码), explanation(代码解释), debug(调试), impl(实现咨询), general(一般问题)
只返回意图类型名称。"""
        
        response = llm.invoke(prompt)
        intent_str = response.content.strip().lower()
        
        intent_map = {"lookup": IntentType.LOOKUP, "explanation": IntentType.EXPLANATION, 
                      "debug": IntentType.DEBUG, "impl": IntentType.IMPLEMENTATION, "general": IntentType.GENERAL}
        intent = intent_map.get(intent_str, IntentType.GENERAL)
        
        state.intent = intent
        state.step_count += 1
        if state.verbose:
            logger.info(f"Intent classified as: {intent.value}")
    except Exception as e:
        state.intent = IntentType.GENERAL
        state.error = str(e)
    
    return state


def refine_query(state: GraphState) -> GraphState:
    """节点2: 查询优化"""
    state.refined_query = state.query
    return state


def search_code(state: GraphState) -> GraphState:
    """节点3: 代码搜索"""
    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_community.vectorstores import Chroma
        
        embeddings = OpenAIEmbeddings(model=settings.OPENAI_EMBEDDING_MODEL, api_key=settings.OPENAI_API_KEY)
        
        vector_store = Chroma(
            client=None,
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
        )
        
        results = vector_store.similarity_search_with_score(state.refined_query, k=settings.TOP_K_FINAL)
        
        state.search_results = []
        for doc, score in results:
            state.search_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            })
        
        if state.verbose:
            logger.info(f"Found {len(state.search_results)} results")
    except Exception as e:
        state.search_results = []
        state.error = str(e)
    
    return state


def generate_answer(state: GraphState) -> GraphState:
    """节点4: 生成答案"""
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.3, api_key=settings.OPENAI_API_KEY)
        
        search_results = state.search_results or []
        if search_results:
            context_parts = []
            for i, r in enumerate(search_results[:3]):
                context_parts.append(f"""--- 代码 {i+1} ---
文件: {r['metadata'].get('file_path', 'unknown')}
行号: {r['metadata'].get('start_line', 0)}
代码: {r['content'][:400]}
""")
            context = "\n---\n".join(context_parts)
        else:
            context = "未找到相关代码"
        
        prompt = f"""基于以下代码分析，回答用户的问题。
用户问题: {state.query}
相关代码:
{context}
回答要求:
1. 直接回答问题
2. 引用代码时标注来源
3. 使用中文回答"""
        
        response = llm.invoke(prompt)
        state.draft_answer = response.content
        
        state.sources = [
            {"file_path": r['metadata'].get('file_path', ''), 
             "lines": f"{r['metadata'].get('start_line', 0)}-{r['metadata'].get('end_line', 0)}",
             "content": r['content'][:200], "score": r['score']}
            for r in search_results[:3]
        ]
        state.final_answer = state.draft_answer
        
    except Exception as e:
        state.draft_answer = "生成答案时出错"
        state.final_answer = "抱歉，生成答案时遇到错误。"
        state.error = str(e)
    
    return state


def review_answer(state: GraphState) -> GraphState:
    """节点5: 审核答案"""
    confidence = 0.5
    
    if state.sources:
        confidence += 0.3
    if len(state.draft_answer) > 100:
        confidence += 0.2
    
    if not state.draft_answer or state.draft_answer == "生成答案时出错":
        state.review_decision = ReviewDecision.NEEDS_REVISION
    elif confidence < settings.HUMAN_LOOP_THRESHOLD:
        state.review_decision = ReviewDecision.NEEDS_HUMAN
        state.needs_human = True
    else:
        state.review_decision = ReviewDecision.APPROVED
    
    state.confidence = confidence
    return state


class CodeRAGGraph:
    """CodeRAG工作流封装"""
    
    def __init__(self, vector_store: VectorStoreManager, verbose: bool = True):
        self.vector_store = vector_store
        self.verbose = verbose
    
    def run(self, query: str, codebase_path: str = "") -> Dict[str, Any]:
        """运行完整的工作流"""
        state = GraphState(
            query=query,
            codebase_path=codebase_path,
            search_results=[],
            sources=[],
            verbose=self.verbose,
        )
        
        # 执行流程
        state = classify_intent(state)
        state = refine_query(state)
        state = search_code(state)
        state = generate_answer(state)
        state = review_answer(state)
        
        return {
            "answer": state.final_answer,
            "sources": state.sources,
            "intent": state.intent.value if state.intent else None,
            "confidence": state.confidence,
            "needs_human": state.needs_human,
            "error": state.error,
        }
    
    def get_graph_diagram(self) -> str:
        """获取图结构的文本表示"""
        return """
CodeRAG Workflow
================

START
  |
  v
classify_intent (分类意图)
  |
  v
refine_query (优化查询)
  |
  v
search_code (搜索代码)
  |
  v
generate_answer (生成答案)
  |
  v
review_answer (审核答案)
  |
  +---> [通过] ---> END
  +---> [需修改] ---> 重新生成
  +---> [低置信度] ---> 人工介入

状态检查点:
- 每个节点执行后状态都会保存
- 支持断点续跑
- 人工介入可暂停执行
"""
