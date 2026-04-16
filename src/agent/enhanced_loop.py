"""
Enhanced Agent Loop - 优化的Agent循环

改进点：
1. 循环检测
2. 错误恢复
3. 流式输出
4. Turn预算管理
"""
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import time
import json

from config.settings import settings
from .tools import CodeTools, ToolResult
from .memory import MemoryManager
from .context import ContextAssembler, Priority


class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    FINISHED = "finished"
    ERROR = "error"
    STUCK = "stuck"  # 新增：检测到循环


@dataclass
class LoopMetrics:
    """循环度量"""
    turn_count: int = 0
    total_tokens: int = 0
    tool_calls: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)


class EnhancedAgentLoop:
    """增强的Agent循环"""
    
    def __init__(
        self,
        tools: CodeTools,
        memory_manager: Optional[MemoryManager] = None,
        model_name: str = "gpt-4-turbo-preview",
        max_turns: int = 15,
        loop_detection_window: int = 3,
        verbose: bool = True,
    ):
        self.tools = tools
        self.memory = memory_manager or MemoryManager()
        self.model_name = model_name
        self.max_turns = max_turns
        self.loop_detection_window = loop_detection_window
        self.verbose = verbose
        
        self.state = AgentState.IDLE
        self.metrics = LoopMetrics()
        self._init_llm()
    
    def _init_llm(self):
        """初始化LLM"""
        try:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=self.model_name,
                temperature=0.7,
                api_key=settings.OPENAI_API_KEY,
            )
            logger.info(f"Initialized LLM: {self.model_name}")
        except ImportError:
            logger.warning("LangChain not installed")
            self.llm = None
    
    def detect_loop(self, messages: List[Dict]) -> bool:
        """检测是否陷入循环"""
        recent_calls = []
        
        for msg in messages[-self.loop_detection_window * 2:]:
            if msg.get("role") == "assistant" and "tool_calls" in msg:
                for call in msg["tool_calls"]:
                    tool_name = call.get("function", {}).get("name", "")
                    tool_args = call.get("function", {}).get("arguments", "")
                    recent_calls.append((tool_name, tool_args[:50]))  # 只取前50字符
        
        if len(recent_calls) >= self.loop_detection_window:
            # 检查最近N次调用是否完全相同
            last_n = recent_calls[-self.loop_detection_window:]
            if len(set(last_n)) == 1:
                logger.warning(f"Loop detected: same tool call repeated {self.loop_detection_window} times")
                return True
        
        return False
    
    def build_context(
        self,
        query: str,
        messages: List[Dict],
        rag_results: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """构建上下文"""
        assembler = ContextAssembler(
            max_tokens=128_000,
            reserve_for_response=8_000,
        )
        
        # 1. 系统提示
        system_prompt = self._get_system_prompt()
        assembler.add_system_prompt(system_prompt)
        
        # 2. AGENTS.md行为规范
        agents_md = self._load_agents_md()
        if agents_md:
            assembler.add_agents_md(agents_md)
        
        # 3. 长期记忆
        memory = self.memory.load_memory()
        if memory:
            assembler.add_memory(memory)
        
        # 4. 工具模式
        tool_schemas = self._get_tool_schemas()
        assembler.add_tool_schemas(tool_schemas)
        
        # 5. RAG结果
        if rag_results:
            assembler.add_rag_results(rag_results)
        
        # 6. 对话历史
        assembler.add_messages(messages)
        
        # 压缩如果需要
        assembler.compress_if_needed()
        
        return assembler.build_messages()
    
    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """你是一个代码库智能助手，帮助用户理解、搜索、分析代码。

你可以使用以下工具：
- search_code: 语义搜索代码
- read_file: 读取文件内容
- analyze_code: 分析代码逻辑

回答原则：
1. 先理解用户真实意图
2. 引用代码时标注文件路径和行号
3. 不确定时说明置信度
4. 简洁明了，避免冗长
"""
    
    def _load_agents_md(self) -> Optional[str]:
        """加载AGENTS.md"""
        from pathlib import Path
        agents_path = Path("AGENTS.md")
        if agents_path.exists():
            return agents_path.read_text(encoding="utf-8")
        return None
    
    def _get_tool_schemas(self) -> List[Dict]:
        """获取工具模式"""
        return [
            {
                "name": "search_code",
                "description": "语义搜索代码库，返回相关代码片段",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索查询"},
                        "top_k": {"type": "integer", "description": "返回结果数量", "default": 5}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "read_file",
                "description": "读取指定文件的内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"}
                    },
                    "required": ["path"]
                }
            }
        ]
    
    def run(
        self,
        query: str,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """运行Agent循环"""
        self.state = AgentState.THINKING
        self.metrics = LoopMetrics()
        
        messages = [{"role": "user", "content": query}]
        
        try:
            for turn in range(self.max_turns):
                self.metrics.turn_count = turn + 1
                self.state = AgentState.THINKING
                
                # 循环检测
                if self.detect_loop(messages):
                    self.state = AgentState.STUCK
                    return {
                        "answer": "检测到执行循环，已自动终止。请尝试重新描述您的问题。",
                        "state": self.state.value,
                        "metrics": self._get_metrics(),
                    }
                
                # 构建上下文
                context_messages = self.build_context(query, messages)
                
                # 调用LLM
                if self.verbose:
                    logger.info(f"Turn {turn + 1}: Calling LLM...")
                
                response = self.llm.invoke(context_messages + messages)
                assistant_msg = response.content
                
                # 添加助手消息
                messages.append({"role": "assistant", "content": assistant_msg})
                
                # 检查是否有工具调用
                if hasattr(response, "tool_calls") and response.tool_calls:
                    self.state = AgentState.ACTING
                    
                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        
                        self.metrics.tool_calls.append(tool_name)
                        
                        if self.verbose:
                            logger.info(f"Tool call: {tool_name}({tool_args})")
                        
                        # 执行工具
                        result = self._execute_tool(tool_name, tool_args)
                        
                        # 添加工具结果
                        messages.append({
                            "role": "tool",
                            "content": str(result),
                        })
                    
                    self.state = AgentState.OBSERVING
                    continue
                
                # 没有工具调用，任务完成
                self.state = AgentState.FINISHED
                
                # 记录到记忆
                self.memory.record_interaction(query, assistant_msg)
                
                return {
                    "answer": assistant_msg,
                    "state": self.state.value,
                    "metrics": self._get_metrics(),
                    "turns": turn + 1,
                }
            
            # 超过最大轮数
            logger.warning(f"Max turns ({self.max_turns}) reached")
            self.state = AgentState.ERROR
            
            return {
                "answer": "任务执行超时，请尝试简化问题或分步骤提问。",
                "state": self.state.value,
                "metrics": self._get_metrics(),
            }
            
        except Exception as e:
            self.state = AgentState.ERROR
            self.metrics.errors.append(str(e))
            logger.error(f"Agent loop error: {e}")
            
            return {
                "answer": f"执行出错: {str(e)}",
                "state": self.state.value,
                "metrics": self._get_metrics(),
                "error": str(e),
            }
    
    def run_stream(
        self,
        query: str,
        context: Optional[Dict] = None,
    ) -> Generator[str, None, None]:
        """流式运行Agent循环"""
        self.state = AgentState.THINKING
        messages = [{"role": "user", "content": query}]
        
        try:
            for turn in range(self.max_turns):
                # 构建上下文
                context_messages = self.build_context(query, messages)
                
                # 流式调用LLM
                for chunk in self.llm.stream(context_messages + messages):
                    if chunk.content:
                        yield chunk.content
                
                # 检查是否完成
                # ... (简化版，完整版需要处理工具调用)
                break
                
        except Exception as e:
            yield f"\n[Error]: {str(e)}"
    
    def _execute_tool(self, name: str, args: Dict) -> Any:
        """执行工具"""
        try:
            if name == "search_code":
                return self.tools.search(args.get("query", ""), args.get("top_k", 5))
            elif name == "read_file":
                return self.tools.read_file(args.get("path", ""))
            else:
                return f"Unknown tool: {name}"
        except Exception as e:
            logger.error(f"Tool execution error: {name} - {e}")
            return f"Tool error: {str(e)}"
    
    def _get_metrics(self) -> Dict:
        """获取度量信息"""
        return {
            "turn_count": self.metrics.turn_count,
            "tool_calls": self.metrics.tool_calls,
            "errors": self.metrics.errors,
            "duration": time.time() - self.metrics.start_time,
        }


# 使用示例
if __name__ == "__main__":
    from .tools import CodeTools
    
    tools = CodeTools()
    agent = EnhancedAgentLoop(tools=tools, verbose=True)
    
    result = agent.run("找到处理用户认证的代码")
    print("Answer:", result["answer"])
    print("State:", result["state"])
    print("Metrics:", result["metrics"])
