"""
API路由定义
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from config.settings import settings
from src.agent.graph import CodeRAGGraph
from src.agent.tools import CodeTools
from src.indexer.parser import CodeParser
from src.indexer.chunker import CodeChunker
from src.indexer.embedder import CodeEmbedder
from src.retriever.vector_store import VectorStoreManager
from src.retriever.hybrid_search import HybridSearch


router = APIRouter()


class IndexRequest(BaseModel):
    codebase_path: str
    recursive: bool = True


class QueryRequest(BaseModel):
    query: str
    codebase_path: str = ""


_vector_store: Optional[VectorStoreManager] = None
_embedder: Optional[CodeEmbedder] = None


def get_vector_store() -> VectorStoreManager:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreManager(persist_directory=str(settings.CHROMA_DIR), 
                                           collection_name=settings.CHROMA_COLLECTION_NAME)
    return _vector_store


def get_embedder() -> CodeEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = CodeEmbedder(provider="openai")
    return _embedder


@router.post("/index")
async def index_codebase(request: IndexRequest):
    """索引代码库"""
    try:
        codebase_path = Path(request.codebase_path)
        if not codebase_path.exists():
            raise HTTPException(status_code=404, detail="Codebase path not found")
        
        parser = CodeParser()
        parsed_files = parser.parse_directory(str(codebase_path), recursive=request.recursive)
        
        if not parsed_files:
            return {"status": "warning", "files_indexed": 0, "chunks_created": 0, "message": "No supported code files found"}
        
        chunker = CodeChunker(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
        chunks = chunker.chunk_files(parsed_files)
        
        embedder = get_embedder()
        embeddings = embedder.embed_code_chunks(chunks)
        
        vector_store = get_vector_store()
        vector_store.add_chunks(chunks, embeddings)
        
        return {"status": "success", "files_indexed": len(parsed_files), "chunks_created": len(chunks), "message": "Indexed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_codebase(request: QueryRequest):
    """查询代码库"""
    try:
        graph = CodeRAGGraph(vector_store=get_vector_store(), verbose=settings.AGENT_VERBOSE)
        result = graph.run(query=request.query, codebase_path=request.codebase_path)
        return result
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """获取统计信息"""
    try:
        vector_store = get_vector_store()
        return {"collection": vector_store.get_collection_info()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
