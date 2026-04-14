"""
FastAPI主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config.settings import settings
from .routes import router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.API_TITLE, version="1.0.0", 
                  description="CodeRAG-Agent API - 基于RAG的代码库智能问答系统")
    
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, 
                       allow_methods=["*"], allow_headers=["*"])
    
    app.include_router(router, prefix="/api")
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "CodeRAG-Agent"}
    
    @app.get("/")
    async def root():
        return {"service": "CodeRAG-Agent", "version": settings.API_VERSION, "docs": "/docs"}
    
    return app


app = create_app()


def run_server():
    uvicorn.run("src.api.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=False)
