"""
向量存储管理器 - 使用ChromaDB管理向量存储
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from loguru import logger

from config.settings import settings
from src.indexer.chunker import CodeChunk
from src.indexer.embedder import EmbeddingResult


@dataclass
class SearchResult:
    """搜索结果"""
    chunk_id: str
    content: str
    file_path: str
    start_line: int
    end_line: int
    score: float
    entity_type: str
    entity_name: Optional[str] = None
    docstring: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "score": self.score,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "docstring": self.docstring,
            "metadata": self.metadata,
        }


class VectorStoreManager:
    """向量存储管理器"""
    
    def __init__(self, persist_directory: Optional[str] = None, collection_name: str = "code_rag"):
        self.persist_directory = persist_directory or str(settings.CHROMA_DIR)
        self.collection_name = collection_name
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        self._init_chromadb()
    
    def _init_chromadb(self):
        try:
            import chromadb
            from chromadb.config import Settings
            
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            self._collection = self._client.get_or_create_collection(name=self.collection_name)
            logger.info(f"Initialized ChromaDB: {self.collection_name}")
        except ImportError:
            logger.error("ChromaDB not installed")
            self._client = None
            self._collection = None
    
    @property
    def count(self) -> int:
        return self._collection.count() if self._collection else 0
    
    def add_chunks(self, chunks: List[CodeChunk], embeddings: List[EmbeddingResult]) -> bool:
        if not self._collection:
            return False
        
        if len(chunks) != len(embeddings):
            return False
        
        try:
            ids, documents, metadatas, embeddings_list = [], [], [], []
            
            for chunk, embedding in zip(chunks, embeddings):
                ids.append(chunk.chunk_id)
                documents.append(chunk.to_document())
                metadatas.append({
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "entity_type": chunk.entity_type,
                    "entity_name": chunk.entity_name or "",
                    "language": chunk.language,
                    "docstring": chunk.docstring,
                    "content": chunk.content,
                })
                embeddings_list.append(embedding.embedding)
            
            self._collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings_list)
            logger.info(f"Added {len(chunks)} chunks")
            return True
        except Exception as e:
            logger.error(f"Failed to add chunks: {e}")
            return False
    
    def search(self, query: str, query_embedding: List[float], top_k: int = 10,
               filter_metadata: Optional[Dict] = None) -> List[SearchResult]:
        if not self._collection:
            return []
        
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"]
            )
            
            search_results = []
            if results["ids"] and results["ids"][0]:
                for i, chunk_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i]
                    score = 1 - distance
                    
                    search_results.append(SearchResult(
                        chunk_id=chunk_id,
                        content=metadata.get("content", ""),
                        file_path=metadata.get("file_path", ""),
                        start_line=metadata.get("start_line", 0),
                        end_line=metadata.get("end_line", 0),
                        score=score,
                        entity_type=metadata.get("entity_type", ""),
                        entity_name=metadata.get("entity_name") or None,
                        docstring=metadata.get("docstring", ""),
                        metadata=metadata,
                    ))
            return search_results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def reset(self) -> bool:
        if not self._client:
            return False
        try:
            self._client.delete_collection(self.collection_name)
            self._collection = self._client.get_or_create_collection(name=self.collection_name)
            logger.info("Vector store reset")
            return True
        except Exception as e:
            logger.error(f"Reset failed: {e}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        if not self._collection:
            return {}
        return {"name": self.collection_name, "count": self.count}
