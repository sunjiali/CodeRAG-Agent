"""
代码嵌入器 - 将代码块转换为向量表示
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import hashlib
from loguru import logger

from config.settings import settings


@dataclass
class EmbeddingResult:
    """嵌入结果"""
    chunk_id: str
    embedding: List[float]
    model: str
    dimension: int
    metadata: Dict[str, Any]


class CodeEmbedder:
    """代码嵌入器"""
    
    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        self.provider = provider
        
        if provider == "openai":
            self._init_openai(model)
        else:
            self._dimension = 1536
            self._model_name = "mock"
    
    def _init_openai(self, model: Optional[str]):
        try:
            from langchain_openai import OpenAIEmbeddings
            self._embeddings = OpenAIEmbeddings(
                model=model or settings.OPENAI_EMBEDDING_MODEL,
            )
            self._dimension = settings.EMBEDDING_DIMENSION
            self._model_name = model or settings.OPENAI_EMBEDDING_MODEL
            logger.info(f"Initialized OpenAI embedder: {self._model_name}")
        except ImportError:
            logger.warning("LangChain not available, using mock embeddings")
            self._embeddings = None
            self._dimension = 1536
            self._model_name = "mock"
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    def embed(self, text: str) -> List[float]:
        if self._embeddings:
            return self._embeddings.embed_query(text)
        return self._mock_embedding(text)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self._embeddings:
            return self._embeddings.embed_documents(texts)
        return [self._mock_embedding(text) for text in texts]
    
    def _mock_embedding(self, text: str) -> List[float]:
        import random
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        random.seed(hash_val)
        return [random.uniform(-1, 1) for _ in range(self._dimension)]
    
    def embed_code_chunks(self, chunks: List[Any]) -> List[EmbeddingResult]:
        documents = [chunk.to_document() for chunk in chunks]
        embeddings = self.embed_batch(documents)
        
        results = []
        for chunk, embedding in zip(chunks, embeddings):
            results.append(EmbeddingResult(
                chunk_id=chunk.chunk_id,
                embedding=embedding,
                model=self.model_name,
                dimension=self.dimension,
                metadata={
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "entity_type": chunk.entity_type,
                    "entity_name": chunk.entity_name,
                },
            ))
        return results
