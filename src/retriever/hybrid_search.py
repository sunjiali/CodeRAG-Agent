"""
混合搜索 - 结合向量搜索和BM25
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import math

from .vector_store import SearchResult, VectorStoreManager
from src.indexer.embedder import CodeEmbedder


@dataclass
class HybridSearchResult:
    """混合搜索结果"""
    chunk_id: str
    content: str
    file_path: str
    start_line: int
    end_line: int
    vector_score: float
    bm25_score: float
    combined_score: float
    entity_type: str
    entity_name: Optional[str] = None
    docstring: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SimpleBM25:
    """简化的BM25实现"""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[str] = []
        self.doc_ids: List[str] = []
        self.doc_info: Dict[str, Dict] = {}
        self.avg_doc_len = 0
        self.idf: Dict[str, float] = {}
    
    def _tokenize(self, text: str) -> List[str]:
        import re
        return re.findall(r'\w+', text.lower())
    
    def add_documents(self, documents: List[str], doc_ids: List[str], doc_info: List[Dict]):
        self.documents = documents
        self.doc_ids = doc_ids
        self.avg_doc_len = sum(len(d.split()) for d in documents) / max(len(documents), 1)
        
        doc_freq = {}
        for doc in documents:
            for token in set(self._tokenize(doc)):
                doc_freq[token] = doc_freq.get(token, 0) + 1
        
        n = len(documents)
        for token, df in doc_freq.items():
            self.idf[token] = math.log((n - df + 0.5) / (df + 0.5) + 1)
        
        for doc_id, info in zip(doc_ids, doc_info):
            self.doc_info[doc_id] = info
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float, Dict]]:
        query_tokens = self._tokenize(query)
        scores = {}
        
        for i, doc in enumerate(self.documents):
            doc_tokens = self._tokenize(doc)
            tf = {}
            for token in doc_tokens:
                tf[token] = tf.get(token, 0) + 1
            
            score = 0.0
            for token in query_tokens:
                if token not in self.idf:
                    continue
                term_tf = tf.get(token, 0)
                idf = self.idf[token]
                numerator = term_tf * (self.k1 + 1)
                denominator = term_tf + self.k1 * (1 - self.b + self.b * len(doc_tokens) / max(self.avg_doc_len, 1))
                score += idf * (numerator / denominator)
            
            if score > 0:
                scores[self.doc_ids[i]] = score
        
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(doc_id, score, self.doc_info.get(doc_id, {})) for doc_id, score in sorted_scores[:top_k]]


class HybridSearch:
    """混合搜索器"""
    
    def __init__(self, vector_store: VectorStoreManager, embedder: CodeEmbedder,
                 vector_weight: float = 0.7, bm25_weight: float = 0.3):
        self.vector_store = vector_store
        self.embedder = embedder
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.bm25: Optional[SimpleBM25] = None
        self._bm25_indexed = False
    
    def _ensure_bm25_index(self):
        if self._bm25_indexed:
            return
        
        try:
            if hasattr(self.vector_store._collection, 'get'):
                results = self.vector_store._collection.get(include=["documents", "metadatas"])
                
                if results["ids"]:
                    documents, doc_ids, doc_infos = [], [], []
                    for i, doc_id in enumerate(results["ids"]):
                        metadata = results["metadatas"][i]
                        documents.append(results["documents"][i])
                        doc_ids.append(doc_id)
                        doc_infos.append({
                            "file_path": metadata.get("file_path", ""),
                            "start_line": metadata.get("start_line", 0),
                            "end_line": metadata.get("end_line", 0),
                            "entity_type": metadata.get("entity_type", ""),
                            "content": metadata.get("content", ""),
                        })
                    
                    self.bm25 = SimpleBM25()
                    self.bm25.add_documents(documents, doc_ids, doc_infos)
                    self._bm25_indexed = True
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
    
    def search(self, query: str, top_k: int = 10, filter_metadata: Optional[Dict] = None) -> List[HybridSearchResult]:
        query_embedding = self.embedder.embed(query)
        vector_results = self.vector_store.search(query, query_embedding, top_k * 2, filter_metadata)
        
        self._ensure_bm25_index()
        bm25_results = []
        if self.bm25:
            bm25_results = self.bm25.search(query, top_k * 2)
        
        return self._merge_results(vector_results, bm25_results, top_k)
    
    def _merge_results(self, vector_results: List[SearchResult], bm25_results: List[Tuple], top_k: int) -> List[HybridSearchResult]:
        vector_scores = {r.chunk_id: r.score for r in vector_results}
        bm25_scores = {doc_id: score for doc_id, score, _ in bm25_results}
        bm25_info = {doc_id: info for doc_id, _, info in bm25_results}
        
        all_ids = set(vector_scores.keys()) | set(bm25_scores.keys())
        max_vector = max(vector_scores.values()) if vector_scores else 1.0
        max_bm25 = max(bm25_scores.values()) if bm25_scores else 1.0
        
        results = []
        for chunk_id in all_ids:
            vector_score = vector_scores.get(chunk_id, 0) / max_vector if max_vector else 0
            bm25_score = bm25_scores.get(chunk_id, 0) / max_bm25 if max_bm25 else 0
            combined = self.vector_weight * vector_score + self.bm25_weight * bm25_score
            
            if chunk_id in vector_scores:
                vec_result = next(r for r in vector_results if r.chunk_id == chunk_id)
                metadata = vec_result.metadata or {}
                content = metadata.get("content", vec_result.content)
            else:
                info = bm25_info.get(chunk_id, {})
                metadata = info
                content = info.get("content", "")
            
            results.append(HybridSearchResult(
                chunk_id=chunk_id,
                content=content,
                file_path=metadata.get("file_path", ""),
                start_line=metadata.get("start_line", 0),
                end_line=metadata.get("end_line", 0),
                vector_score=vector_score,
                bm25_score=bm25_score,
                combined_score=combined,
                entity_type=metadata.get("entity_type", ""),
                entity_name=metadata.get("entity_name", ""),
                docstring=metadata.get("docstring", ""),
                metadata=metadata,
            ))
        
        results.sort(key=lambda x: x.combined_score, reverse=True)
        return results[:top_k]
