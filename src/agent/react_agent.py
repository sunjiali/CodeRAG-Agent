"""
ReAct Agent实现 - 思考-行动-观察循环
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import json

from config.settings import settings
from .tools import CodeTools, ToolResult


class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class ReActStep:
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict] = None
    observation: Optional[str] = None
    is_final: bool = False


@dataclass
class AgentResponse:
    answer: str
    sources: List[Dict] = field(default_factory=list)
    steps: List[ReActStep] = field(default_factory=list)
    state: AgentState = AgentState.FINISHED
    confidence: float = 0.0


class ReActAgent:
    """ReAct Agent - 思考-行动-观察循环"""
    
    def __init__(self, tools: CodeTools, model_name: str = "gpt-4-turbo-preview", max_steps: int = 10, verbose: bool = True):
        self.tools = tools
        self.model_name = model_name
        self.max_steps = max_steps
        self.verbose = verbose
        self._init_llm()
    
    def _init_llm(self):
        try:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(model=self.model_name, temperature=0.7, api_key=settings.OPENAI_API_KEY)
            logger.info(f"Initialized LLM: {self.model_name}")
        except ImportError:
            logger.warning("LangChain not installed")
            self.llm = None
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        if self.llm:
            try:
                response = self.llm.invoke(prompt)
                return response.content
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
        return None
    
    def _parse_llm_response(self, response: str) -> Optional[Dict]:
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            else:
                json_str = response
            return json.loads(json_str.strip())
        except json.JSONDecodeError:
            return None
    
    def run(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """运行Agent回答问题"""
        steps = []
        step_count = 0
        all_sources = []
        
        # 简单的ReAct实现：搜索 + 分析
        if self.verbose:
            logger.info(f"Starting ReAct for query: {query}")
        
        # 步骤1: 搜索代码
        step_count += 1
        search_result = self.tools.execute_tool("search_code", query=query)
        
        if search_result.success and search_result.result:
            all_sources = search_result.result.get("results", [])[:5]
        
        step = ReActStep(
            step_number=step_count,
            thought=f"我需要搜索与'{query}'相关的代码",
            action="search_code",
            action_input={"query": query},
            observation=f"找到 {len(all_sources)} 个相关代码片段",
        )
        steps.append(step)
        
        # 步骤2: 分析代码
        if all_sources:
            step_count += 1
            code = all_sources[0].get("content", "")[:500]
            analyze_result = self.tools.execute_tool("analyze_code", code=code)
            
            step = ReActStep(
                step_number=step_count,
                thought="分析找到的代码以理解其功能",
                action="analyze_code",
                observation=str(analyze_result.result)[:200] if analyze_result.success else "分析失败",
                is_final=True,
            )
            steps.append(step)
        
        # 生成答案
        answer = self._generate_answer(query, steps, all_sources)
        confidence = min(0.5 + len(all_sources) * 0.1, 1.0) if all_sources else 0.3
        
        return AgentResponse(
            answer=answer,
            sources=all_sources,
            steps=steps,
            state=AgentState.FINISHED,
            confidence=confidence,
        )
    
    def _generate_answer(self, query: str, steps: List[ReActStep], sources: List[Dict]) -> str:
        """生成最终答案"""
        answer_parts = []
        
        if sources:
            answer_parts.append("根据代码分析，以下是问题的答案：\n")
            
            for i, source in enumerate(sources[:3], 1):
                path = source.get("file_path", "")
                lines = f"{source.get('start_line', 0)}-{source.get('end_line', 0)}"
                content = source.get("content", "")[:300]
                
                answer_parts.append(f"**来源 {i}**: `{path}:{lines}`")
                answer_parts.append(f"```\n{content}...\n```\n")
        
        if steps:
            final_thoughts = [s.thought for s in steps if s.thought]
            if final_thoughts:
                answer_parts.append("\n**分析过程**:")
                answer_parts.append(final_thoughts[-1][:500])
        
        return "\n".join(answer_parts) if answer_parts else "抱歉，未能找到相关信息。"
