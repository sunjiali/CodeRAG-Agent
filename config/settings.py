"""
配置文件 - CodeRAG-Agent
"""
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_ROOT: Path = Field(default=Path(__file__).parent.parent)
    DATA_DIR: Path = Field(default=PROJECT_ROOT / "data")
    CHROMA_DIR: Path = Field(default=DATA_DIR / "chroma_db")
    CACHE_DIR: Path = Field(default=DATA_DIR / "cache")
    
    # LLM配置
    LLM_PROVIDER: str = Field(default="openai")
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = Field(default="gpt-4-turbo-preview")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    OPENAI_TEMPERATURE: float = Field(default=0.7)
    OPENAI_MAX_TOKENS: int = Field(default=2000)
    
    # Ollama配置
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="llama2")
    OLLAMA_EMBEDDING_MODEL: str = Field(default="nomic-embed-text")
    
    # 向量数据库配置
    CHROMA_COLLECTION_NAME: str = Field(default="code_rag")
    EMBEDDING_DIMENSION: int = Field(default=1536)
    
    # RAG配置
    TOP_K_VECTOR: int = Field(default=10)
    TOP_K_BM25: int = Field(default=10)
    TOP_K_FINAL: int = Field(default=5)
    RERANK_MODEL: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    SIMILARITY_THRESHOLD: float = Field(default=0.5)
    
    # 代码解析配置
    SUPPORTED_LANGUAGES: List[str] = Field(default=["python", "javascript", "go", "java", "rust"])
    CHUNK_SIZE: int = Field(default=500)
    CHUNK_OVERLAP: int = Field(default=50)
    
    # Agent配置
    MAX_REACT_STEPS: int = Field(default=10)
    AGENT_VERBOSE: bool = Field(default=True)
    ENABLE_HUMAN_LOOP: bool = Field(default=True)
    HUMAN_LOOP_THRESHOLD: float = Field(default=0.3)
    
    # API配置
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    
    # Web配置
    WEB_HOST: str = Field(default="0.0.0.0")
    WEB_PORT: int = Field(default=7860)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def ensure_directories():
    for dir_path in [settings.DATA_DIR, settings.CHROMA_DIR, settings.CACHE_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


ensure_directories()
