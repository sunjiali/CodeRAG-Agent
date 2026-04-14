"""
Web界面 - Gradio实现
"""
import sys
from pathlib import Path
import gradio as gr

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.agent.graph import CodeRAGGraph
from src.agent.tools import CodeTools
from src.indexer.parser import CodeParser
from src.indexer.chunker import CodeChunker
from src.indexer.embedder import CodeEmbedder
from src.retriever.vector_store import VectorStoreManager


def get_vector_store():
    return VectorStoreManager(persist_directory=str(settings.CHROMA_DIR), collection_name=settings.CHROMA_COLLECTION_NAME)


def get_embedder():
    return CodeEmbedder(provider="openai")


def index_codebase(codebase_path: str, status_callback=None) -> str:
    try:
        path = Path(codebase_path)
        if not path.exists():
            return f"路径不存在: {codebase_path}"
        
        if status_callback:
            status_callback("解析代码文件...")
        
        parser = CodeParser()
        parsed_files = parser.parse_directory(str(path), recursive=True)
        
        if not parsed_files:
            return "未找到支持的代码文件"
        
        if status_callback:
            status_callback(f"解析了 {len(parsed_files)} 个文件，正在分块...")
        
        chunker = CodeChunker(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
        chunks = chunker.chunk_files(parsed_files)
        
        if status_callback:
            status_callback(f"创建了 {len(chunks)} 个代码块，正在向量化...")
        
        embedder = get_embedder()
        embeddings = embedder.embed_code_chunks(chunks)
        
        if status_callback:
            status_callback("存入向量数据库...")
        
        vector_store = get_vector_store()
        vector_store.add_chunks(chunks, embeddings)
        
        return f"索引完成！\n文件数: {len(parsed_files)}\n代码块: {len(chunks)}"
    except Exception as e:
        return f"索引失败: {str(e)}"


def query_codebase(query: str) -> tuple:
    try:
        graph = CodeRAGGraph(vector_store=get_vector_store(), verbose=True)
        result = graph.run(query=query)
        
        answer = result.get("answer", "抱歉，未找到相关信息。")
        sources = result.get("sources", [])
        
        sources_md = ""
        if sources:
            for i, src in enumerate(sources, 1):
                sources_md += f"**{i}. {src.get('file_path', 'unknown')}** (行 {src.get('lines', '0-0')})\n```\n{src.get('content', '')[:300]}...\n```\n\n"
        
        return answer, sources_md
    except Exception as e:
        return f"查询失败: {str(e)}", ""


def create_gradio_interface():
    with gr.Blocks(title="CodeRAG-Agent", theme=gr.themes.Soft()) as app:
        gr.Markdown("# CodeRAG-Agent\n基于RAG + ReAct + LangGraph的代码库智能问答系统")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 代码库设置")
                codebase_path = gr.Textbox(label="代码库路径", placeholder="/path/to/codebase")
                index_btn = gr.Button("索引代码库", variant="primary")
                index_status = gr.Textbox(label="状态", interactive=False)
            
            with gr.Column(scale=2):
                gr.Markdown("### 智能问答")
                query_input = gr.Textbox(label="输入问题", placeholder="例如：这个项目如何处理用户认证？", lines=3)
                ask_btn = gr.Button("提问", variant="primary")
                answer_output = gr.Markdown(label="回答")
                
                with gr.Accordion("引用的代码片段", open=False):
                    sources_output = gr.Markdown()
        
        index_btn.click(fn=index_codebase, inputs=[codebase_path], outputs=[index_status])
        ask_btn.click(fn=query_codebase, inputs=[query_input], outputs=[answer_output, sources_output])
    
    return app


def main():
    app = create_gradio_interface()
    print(f"CodeRAG-Agent Web界面启动中...\n访问地址: http://{settings.WEB_HOST}:{settings.WEB_PORT}")
    app.launch(server_name=settings.WEB_HOST, server_port=settings.WEB_PORT, share=False)


if __name__ == "__main__":
    main()
