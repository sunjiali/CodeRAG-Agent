"""
Agent工具定义 - 定义Agent可用的工具
"""
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from src.retriever.vector_store import SearchResult, VectorStoreManager
from src.retriever.hybrid_search import HybridSearch
from src.retriever.reranker import Reranker
from src.indexer.embedder import CodeEmbedder


class ToolType(Enum):
    """工具类型"""
    SEARCH = "search"
    ANALYZE = "analyze"
    READ = "read"
    LIST = "list"


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0


class CodeSearchTool:
    """代码搜索工具"""
    
    def __init__(self, hybrid_search: HybridSearch, reranker: Optional[Reranker] = None, top_k: int = 10):
        self.hybrid_search = hybrid_search
        self.reranker = reranker
        self.top_k = top_k
    
    def __call__(self, query: str, top_k: Optional[int] = None) -> Dict[str, Any]:
        import time
        start_time = time.time()
        
        try:
            k = top_k or self.top_k
            results = self.hybrid_search.search(query, top_k=k * 2)
            
            search_results = []
            for r in results[:k]:
                search_results.append(SearchResult(
                    chunk_id=r.chunk_id,
                    content=r.content,
                    file_path=r.file_path,
                    start_line=r.start_line,
                    end_line=r.end_line,
                    score=r.combined_score,
                    entity_type=r.entity_type,
                    entity_name=r.entity_name,
                    docstring=r.docstring,
                    metadata=r.metadata,
                ))
            
            return {
                "query": query,
                "count": len(search_results),
                "results": [r.to_dict() for r in search_results],
                "execution_time": time.time() - start_time,
            }
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"query": query, "count": 0, "results": [], "error": str(e)}


class CodeAnalyzeTool:
    """代码分析工具"""
    
    def __call__(self, code: str, context: Optional[str] = None) -> Dict[str, Any]:
        try:
            import re
            analysis = {
                "lines": len(code.split("\n")),
                "functions": re.findall(r'def\s+(\w+)\s*\(', code) + re.findall(r'function\s+(\w+)\s*\(', code),
                "classes": re.findall(r'class\s+(\w+)', code),
                "complexity_estimate": min(code.count("if") + code.count("for") + code.count("while") + 1, 10),
            }
            if context:
                analysis["context"] = context
            return analysis
        except Exception as e:
            return {"error": str(e)}


class ListEntitiesTool:
    """列出代码实体工具"""
    
    def __init__(self, vector_store: VectorStoreManager):
        self.vector_store = vector_store
    
    def __call__(self, entity_type: Optional[str] = None, file_path: Optional[str] = None, top_k: int = 20) -> Dict[str, Any]:
        try:
            results = self.vector_store._collection.get(include=["metadatas"])
            
            entities = []
            for i, metadata in enumerate(results["metadatas"]):
                if entity_type and metadata.get("entity_type") != entity_type:
                    continue
                if file_path and file_path not in metadata.get("file_path", ""):
                    continue
                
                entities.append({
                    "chunk_id": results["ids"][i],
                    "name": metadata.get("entity_name", ""),
                    "type": metadata.get("entity_type", ""),
                    "file_path": metadata.get("file_path", ""),
                    "lines": f"{metadata.get('start_line', 0)}-{metadata.get('end_line', 0)}",
                })
            
            return {"count": len(entities), "entities": entities[:top_k]}
        except Exception as e:
            return {"count": 0, "entities": [], "error": str(e)}


class CodeTools:
    """代码工具集"""
    
    def __init__(self, vector_store: VectorStoreManager, embedder: CodeEmbedder,
                 hybrid_search: Optional[HybridSearch] = None, reranker: Optional[Reranker] = None):
        self.vector_store = vector_store
        self.embedder = embedder
        self.reranker = reranker
        
        if hybrid_search is None:
            hybrid_search = HybridSearch(vector_store=vector_store, embedder=embedder)
        self.hybrid_search = hybrid_search
        
        self._tools = {
            "search_code": CodeSearchTool(hybrid_search=self.hybrid_search, reranker=reranker),
            "analyze_code": CodeAnalyzeTool(),
            "list_entities": ListEntitiesTool(vector_store),
        }
    
    def get_tool(self, name: str):
        return self._tools.get(name)
    
    def get_all_tools(self) -> List:
        return list(self._tools.values())
    
    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        import time
        start_time = time.time()
        
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(tool_name=name, success=False, error=f"Tool not found: {name}")
        
        try:
            result = tool(**kwargs)
            return ToolResult(tool_name=name, success=True, result=result, execution_time=time.time() - start_time)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(tool_name=name, success=False, error=str(e), execution_time=time.time() - start_time)
