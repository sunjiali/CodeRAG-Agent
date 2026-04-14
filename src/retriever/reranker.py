"""
重排序模块 - 使用Cross-Encoder对检索结果进行精排
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

from .vector_store import SearchResult


@dataclass
class RerankedResult:
    """重排序后的结果"""
    chunk_id: str
    content: str
    file_path: str
    start_line: int
    end_line: int
    original_score: float
    rerank_score: float
    entity_type: str
    entity_name: Optional[str] = None
    docstring: str = ""
    metadata: Dict[str, Any] = None


class Reranker:
    """重排序器"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", device: str = "cpu"):
        self.model_name = model_name
        self._model = None
        self._load_model()
    
    def _load_model(self):
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(model_name=self.model_name, max_length=512, device=self.device)
            logger.info(f"Loaded Cross-Encoder: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed")
        except Exception as e:
            logger.error(f"Failed to load Cross-Encoder: {e}")
    
    def rerank(self, query: str, results: List[SearchResult], top_k: int = 5) -> List[RerankedResult]:
        if not results:
            return []
        
        if self._model is None:
            return [
                RerankedResult(
                    chunk_id=r.chunk_id, content=r.content, file_path=r.file_path,
                    start_line=r.start_line, end_line=r.end_line,
                    original_score=r.score, rerank_score=r.score,
                    entity_type=r.entity_type, entity_name=r.entity_name,
                    docstring=r.docstring, metadata=r.metadata,
                )
                for r in results[:top_k]
            ]
        
        try:
            pairs = []
            for r in results:
                text = r.content
                if r.docstring:
                    text = f"{r.docstring}\n\n{text}"
                pairs.append((query, text))
            
            scores = self._model.predict(pairs)
            
            reranked = []
            for r, score in zip(results, scores):
                reranked.append(RerankedResult(
                    chunk_id=r.chunk_id, content=r.content, file_path=r.file_path,
                    start_line=r.start_line, end_line=r.end_line,
                    original_score=r.score, rerank_score=float(score),
                    entity_type=r.entity_type, entity_name=r.entity_name,
                    docstring=r.docstring, metadata=r.metadata,
                ))
            
            reranked.sort(key=lambda x: x.rerank_score, reverse=True)
            return reranked[:top_k]
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return [
                RerankedResult(
                    chunk_id=r.chunk_id, content=r.content, file_path=r.file_path,
                    start_line=r.start_line, end_line=r.end_line,
                    original_score=r.score, rerank_score=r.score,
                    entity_type=r.entity_type, entity_name=r.entity_name,
                    docstring=r.docstring, metadata=r.metadata,
                )
                for r in results[:top_k]
            ]
