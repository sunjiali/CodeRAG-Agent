"""
CodeRAG-Agent V2 - 整合所有优化模块

新特性：
1. Memory系统 (MEMORY.md + Daily Logs)
2. Context优先级组装
3. Skill动态加载
4. Guardrails护栏
5. Agent Loop优化（循环检测、错误恢复）
"""
from typing import Dict, Any, Optional, List
from loguru import logger
from pathlib import Path

from config.settings import settings
from src.agent.memory import MemoryManager
from src.agent.context import ContextAssembler, Priority
from src.agent.skill_registry import SkillRegistry
from src.agent.guardrails import Guardrails, RiskLevel
from src.agent.enhanced_loop import EnhancedAgentLoop
from src.agent.tools import CodeTools
from src.retriever.hybrid_search import HybridSearch
from src.retriever.reranker import Reranker


class CodeRAGAgentV2:
    """CodeRAG-Agent V2 - 优化版"""
    
    def __init__(
        self,
        codebase_path: str = ".",
        skills_dir: str = "./skills",
        memory_dir: str = "./memory",
        verbose: bool = True,
    ):
        self.codebase_path = Path(codebase_path)
        self.verbose = verbose
        
        # 初始化组件
        logger.info("Initializing CodeRAG-Agent V2...")
        
        # 1. 记忆系统
        self.memory = MemoryManager(memory_dir)
        
        # 2. 技能注册表
        self.skills = SkillRegistry(skills_dir)
        
        # 3. 护栏系统
        self.guardrails = Guardrails(
            allowed_paths=[f"{codebase_path}/**"]
        )
        
        # 4. 检索系统
        self._init_retriever()
        
        # 5. 工具
        self.tools = CodeTools()
        
        # 6. Agent循环
        self.agent_loop = EnhancedAgentLoop(
            tools=self.tools,
            memory_manager=self.memory,
            verbose=verbose,
        )
        
        logger.info("CodeRAG-Agent V2 initialized successfully")
    
    def _init_retriever(self):
        """初始化检索系统"""
        try:
            from src.retriever.vector_store import VectorStoreManager
            from src.indexer.embedder import CodeEmbedder
            
            self.embedder = CodeEmbedder()
            self.vector_store = VectorStoreManager()
            self.hybrid_search = HybridSearch(
                vector_store=self.vector_store,
                embedder=self.embedder,
            )
            self.reranker = Reranker()
            
            logger.info("Retriever initialized")
        except Exception as e:
            logger.warning(f"Retriever initialization failed: {e}")
            self.hybrid_search = None
            self.reranker = None
    
    def query(
        self,
        question: str,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        处理用户查询
        
        Args:
            question: 用户问题
            context: 额外上下文
            
        Returns:
            包含answer、sources、metrics的字典
        """
        # 1. 清理输入
        question = self.guardrails.sanitize_input(question)
        
        logger.info(f"Query: {question[:100]}...")
        
        # 2. 检索相关代码
        rag_results = []
        if self.hybrid_search:
            try:
                results = self.hybrid_search.search(question, top_k=10)
                
                # 重排序
                if self.reranker and results:
                    results = self.reranker.rerank(question, results, top_k=5)
                
                rag_results = [r.__dict__ if hasattr(r, '__dict__') else r for r in results]
                
                if self.verbose:
                    logger.info(f"Retrieved {len(rag_results)} code chunks")
            except Exception as e:
                logger.error(f"Search failed: {e}")
        
        # 3. 运行Agent
        result = self.agent_loop.run(question, context)
        
        # 4. 清理输出
        result["answer"] = self.guardrails.sanitize_output(result["answer"])
        
        # 5. 添加来源
        result["sources"] = rag_results[:3]  # 只返回前3个来源
        
        # 6. 学习用户偏好（如果适用）
        self._maybe_learn_preference(question, result["answer"])
        
        return result
    
    def query_stream(
        self,
        question: str,
        context: Optional[Dict] = None,
    ):
        """流式查询"""
        question = self.guardrails.sanitize_input(question)
        
        yield from self.agent_loop.run_stream(question, context)
    
    def load_skill(self, skill_name: str) -> str:
        """加载技能"""
        return self.skills.load_skill(skill_name)
    
    def unload_skill(self, skill_name: str) -> str:
        """卸载技能"""
        return self.skills.unload_skill(skill_name)
    
    def get_skill_menu(self) -> str:
        """获取技能菜单"""
        return self.skills.get_menu()
    
    def get_memory_summary(self) -> str:
        """获取记忆摘要"""
        return self.memory.load_memory()
    
    def _maybe_learn_preference(self, query: str, answer: str):
        """从交互中学习偏好"""
        # 简单规则：检测特定模式
        if "详细" in query or "详细" in answer:
            self.memory.learn_preference("回答风格", "偏好详细解释")
        elif "简洁" in query or "简单" in query:
            self.memory.learn_preference("回答风格", "偏好简洁回答")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "skills": self.skills.get_stats(),
            "memory": {
                "has_long_term": (Path("./memory/MEMORY.md")).exists(),
                "has_recent_logs": len(list(Path("./memory/daily").glob("*.md"))) > 0,
            },
            "guardrails": {
                "denied_actions": len(self.guardrails.get_denied_actions()),
            },
        }


# 便捷函数
def create_agent(
    codebase_path: str = ".",
    verbose: bool = True,
) -> CodeRAGAgentV2:
    """创建Agent实例"""
    return CodeRAGAgentV2(
        codebase_path=codebase_path,
        verbose=verbose,
    )


# 使用示例
if __name__ == "__main__":
    agent = create_agent(verbose=True)
    
    # 显示技能菜单
    print("=== Skill Menu ===")
    print(agent.get_skill_menu())
    
    # 加载技能
    print("\n=== Load Skill ===")
    print(agent.load_skill("code_search"))
    
    # 查询
    print("\n=== Query ===")
    result = agent.query("找到处理用户认证的代码")
    print(f"Answer: {result['answer'][:200]}...")
    print(f"Sources: {len(result['sources'])} chunks")
    print(f"Turns: {result.get('turns', 'N/A')}")
    
    # 统计
    print("\n=== Stats ===")
    print(agent.get_stats())
