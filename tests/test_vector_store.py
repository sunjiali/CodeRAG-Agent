"""
测试向量存储
"""
import pytest
from src.indexer.chunker import CodeChunk
from src.indexer.embedder import EmbeddingResult


class TestVectorStoreManager:
    @pytest.fixture
    def vector_store(self, temp_dir):
        from src.retriever.vector_store import VectorStoreManager
        store = VectorStoreManager(persist_directory=str(temp_dir / "chroma"), collection_name="test_collection")
        yield store
        store.reset()
    
    @pytest.fixture
    def sample_chunks(self):
        return [
            CodeChunk(
                chunk_id="chunk_1",
                content="def hello(): print('hello')",
                file_path="test.py",
                language="python",
                start_line=1,
                end_line=2,
                entity_type="function",
                entity_name="hello",
            ),
        ]
    
    @pytest.fixture
    def sample_embeddings(self, sample_chunks):
        return [
            EmbeddingResult(
                chunk_id=c.chunk_id,
                embedding=[0.1] * 1536,
                model="test",
                dimension=1536,
                metadata={},
            )
            for c in sample_chunks
        ]
    
    def test_init(self, temp_dir):
        from src.retriever.vector_store import VectorStoreManager
        store = VectorStoreManager(persist_directory=str(temp_dir), collection_name="test")
        assert store.collection_name == "test"
    
    def test_add_chunks(self, vector_store, sample_chunks, sample_embeddings):
        result = vector_store.add_chunks(sample_chunks, sample_embeddings)
        assert result is True


class TestSearchResult:
    def test_to_dict(self):
        from src.retriever.vector_store import SearchResult
        result = SearchResult(
            chunk_id="test",
            content="code",
            file_path="test.py",
            start_line=1,
            end_line=10,
            score=0.95,
            entity_type="function",
            entity_name="test_func",
        )
        
        d = result.to_dict()
        assert d["chunk_id"] == "test"
        assert d["score"] == 0.95
