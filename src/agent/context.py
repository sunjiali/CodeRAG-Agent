"""
Context Assembler - 优先级上下文组装

基于Token预算，按优先级组装上下文内容
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import IntEnum
from loguru import logger


class Priority(IntEnum):
    """上下文优先级（数值越小优先级越高）"""
    SYSTEM_PROMPT = 0      # 系统提示
    AGENTS_MD = 1          # 行为规范
    MEMORY = 2             # 长期记忆
    TOOL_SCHEMAS = 3       # 活跃工具模式
    RAG_RESULTS = 4        # RAG检索结果
    RECENT_MESSAGES = 5    # 最近对话
    SKILL_MENU = 6         # 技能菜单
    DAILY_LOGS = 7         # 每日日志


@dataclass
class ContextSection:
    """上下文段落"""
    priority: int
    name: str
    content: str
    token_count: int = 0
    
    def __post_init__(self):
        if self.token_count == 0:
            self.token_count = estimate_tokens(self.content)


def estimate_tokens(text: str) -> int:
    """估算token数量（简化版：~4字符=1 token）"""
    return len(text) // 4


class ContextAssembler:
    """上下文组装器"""
    
    def __init__(
        self,
        max_tokens: int = 128_000,
        reserve_for_response: int = 8_000,
    ):
        self.max_tokens = max_tokens
        self.reserve_for_response = reserve_for_response
        self.available_tokens = max_tokens - reserve_for_response
        self.sections: List[ContextSection] = []
    
    def add(
        self,
        priority: int,
        name: str,
        content: str,
    ):
        """添加上下文段落"""
        if not content:
            return
        
        section = ContextSection(
            priority=priority,
            name=name,
            content=content,
        )
        self.sections.append(section)
        logger.debug(f"Added context section: {name} ({section.token_count} tokens)")
    
    def add_system_prompt(self, content: str):
        """添加系统提示"""
        self.add(Priority.SYSTEM_PROMPT, "System Prompt", content)
    
    def add_agents_md(self, content: str):
        """添加行为规范"""
        self.add(Priority.AGENTS_MD, "AGENTS.md", content)
    
    def add_memory(self, content: str):
        """添加长期记忆"""
        self.add(Priority.MEMORY, "Memory", content)
    
    def add_tool_schemas(self, schemas: List[Dict]):
        """添加工具模式"""
        import json
        content = json.dumps(schemas, indent=2, ensure_ascii=False)
        self.add(Priority.TOOL_SCHEMAS, "Tool Schemas", content)
    
    def add_rag_results(self, results: List[Dict]):
        """添加RAG检索结果"""
        sections = []
        for i, r in enumerate(results, 1):
            file_path = r.get("file_path", "unknown")
            start_line = r.get("start_line", 0)
            content = r.get("content", "")
            sections.append(f"### Result {i}: {file_path}:{start_line}\n```\n{content}\n```")
        
        self.add(Priority.RAG_RESULTS, "RAG Results", "\n\n".join(sections))
    
    def add_messages(self, messages: List[Dict]):
        """添加对话历史"""
        sections = []
        for msg in messages[-20:]:  # 最多保留最近20条
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "system":
                continue  # 系统消息单独处理
            sections.append(f"[{role.upper()}]: {content[:500]}")  # 截断长内容
        
        self.add(Priority.RECENT_MESSAGES, "Conversation", "\n".join(sections))
    
    def add_skill_menu(self, menu: str):
        """添加技能菜单"""
        self.add(Priority.SKILL_MENU, "Skill Menu", menu)
    
    def build(self) -> str:
        """构建最终上下文"""
        # 按优先级排序
        self.sections.sort(key=lambda s: s.priority)
        
        # 计算token预算
        used_tokens = 0
        included_sections = []
        
        for section in self.sections:
            if used_tokens + section.token_count <= self.available_tokens:
                included_sections.append(section)
                used_tokens += section.token_count
            else:
                logger.warning(
                    f"Context budget exceeded, skipping: {section.name} "
                    f"(would add {section.token_count} tokens)"
                )
        
        # 组装上下文
        context_parts = []
        for section in included_sections:
            context_parts.append(f"[{section.name}]\n{section.content}")
        
        final_context = "\n\n---\n\n".join(context_parts)
        
        logger.info(
            f"Context assembled: {len(included_sections)} sections, "
            f"{used_tokens}/{self.available_tokens} tokens"
        )
        
        return final_context
    
    def build_messages(self) -> List[Dict]:
        """构建消息列表格式（用于LLM API调用）"""
        context = self.build()
        return [{"role": "system", "content": context}]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_sections": len(self.sections),
            "total_tokens": sum(s.token_count for s in self.sections),
            "available_tokens": self.available_tokens,
            "sections_detail": [
                {"name": s.name, "priority": s.priority, "tokens": s.token_count}
                for s in sorted(self.sections, key=lambda x: x.priority)
            ]
        }
    
    def compress_if_needed(self, target_tokens: int = None) -> bool:
        """如果超出预算，压缩上下文"""
        target = target_tokens or self.available_tokens
        current_tokens = sum(s.token_count for s in self.sections)
        
        if current_tokens <= target:
            return False
        
        # 压缩策略：从低优先级开始截断
        for section in sorted(self.sections, key=lambda s: -s.priority):
            if current_tokens <= target:
                break
            
            if section.token_count > 100:
                # 截断到50%
                original = section.content
                truncate_at = len(original) // 2
                section.content = original[:truncate_at] + "\n...[truncated]"
                old_tokens = section.token_count
                section.token_count = estimate_tokens(section.content)
                current_tokens -= (old_tokens - section.token_count)
                logger.info(f"Compressed section: {section.name}")
        
        return True


# 使用示例
if __name__ == "__main__":
    assembler = ContextAssembler(max_tokens=4000, reserve_for_response=500)
    
    # 添加各部分
    assembler.add_system_prompt("You are a code assistant.")
    assembler.add_agents_md("# AGENTS.md\n- Be concise\n- Cite sources")
    assembler.add_memory("# Memory\n- User prefers Python")
    
    # 模拟RAG结果
    assembler.add_rag_results([
        {"file_path": "src/main.py", "start_line": 10, "content": "def main():\n    print('hello')"},
        {"file_path": "src/utils.py", "start_line": 5, "content": "def helper():\n    return 42"},
    ])
    
    # 构建
    context = assembler.build()
    print("=== Assembled Context ===")
    print(context)
    print("\n=== Stats ===")
    print(assembler.get_stats())
