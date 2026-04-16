"""
Memory Manager - 两层记忆架构
- MEMORY.md: 长期记忆（项目知识、用户偏好、经验教训）
- Daily Logs: 每日交互记录
"""
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from loguru import logger
import json


@dataclass
class MemorySection:
    """记忆段落"""
    title: str
    content: str
    priority: int = 0  # 越小优先级越高


class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, memory_dir: str = "./memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        (self.memory_dir / "daily").mkdir(exist_ok=True)
        (self.memory_dir / "wiki").mkdir(exist_ok=True)
        
        self.long_term_memory_path = self.memory_dir / "MEMORY.md"
    
    def load_memory(self) -> str:
        """加载记忆内容到上下文"""
        sections = []
        
        # 1. 加载长期记忆
        long_term = self._load_long_term_memory()
        if long_term:
            sections.append(f"[Long-term Memory]\n{long_term}")
        
        # 2. 加载最近2天的日志
        for days_ago in [0, 1]:
            daily = self._load_daily_log(days_ago)
            if daily:
                date_str = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                sections.append(f"[Daily Log {date_str}]\n{daily}")
        
        return "\n\n---\n\n".join(sections)
    
    def _load_long_term_memory(self) -> Optional[str]:
        """加载长期记忆文件"""
        if self.long_term_memory_path.exists():
            content = self.long_term_memory_path.read_text(encoding="utf-8")
            # 过滤掉Markdown标题，只保留内容
            lines = content.split("\n")
            return "\n".join(lines)
        return None
    
    def _load_daily_log(self, days_ago: int = 0) -> Optional[str]:
        """加载每日日志"""
        date = datetime.now() - timedelta(days=days_ago)
        log_path = self.memory_dir / "daily" / f"{date.strftime('%Y-%m-%d')}.md"
        if log_path.exists():
            return log_path.read_text(encoding="utf-8")
        return None
    
    def append_daily_log(self, content: str, session_id: Optional[str] = None):
        """追加到每日日志"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = self.memory_dir / "daily" / f"{today}.md"
        
        timestamp = datetime.now().strftime("%H:%M")
        entry = f"\n## {timestamp}"
        if session_id:
            entry += f" [{session_id[:8]}]"
        entry += f"\n{content}\n"
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
        
        logger.info(f"Appended to daily log: {log_path}")
    
    def update_long_term_memory(self, section: str, content: str):
        """更新长期记忆的某个段落"""
        if not self.long_term_memory_path.exists():
            self._create_default_memory()
        
        current = self.long_term_memory_path.read_text(encoding="utf-8")
        
        # 查找段落并更新
        lines = current.split("\n")
        section_start = -1
        for i, line in enumerate(lines):
            if line.strip() == f"## {section}":
                section_start = i
                break
        
        if section_start >= 0:
            # 找到下一个段落开始
            next_section = len(lines)
            for i in range(section_start + 1, len(lines)):
                if lines[i].startswith("## "):
                    next_section = i
                    break
            
            # 替换内容
            new_lines = lines[:section_start+1] + [content] + lines[next_section:]
            self.long_term_memory_path.write_text("\n".join(new_lines), encoding="utf-8")
        else:
            # 添加新段落
            with open(self.long_term_memory_path, "a", encoding="utf-8") as f:
                f.write(f"\n## {section}\n{content}\n")
        
        logger.info(f"Updated long-term memory section: {section}")
    
    def _create_default_memory(self):
        """创建默认的MEMORY.md"""
        default_content = """# MEMORY.md - CodeRAG-Agent 长期记忆

## 项目知识
_待补充_

## 用户偏好
_待补充_

## 经验教训
_待补充_
"""
        self.long_term_memory_path.write_text(default_content, encoding="utf-8")
    
    def record_interaction(self, query: str, answer: str, sources: List[Dict] = None):
        """记录一次交互"""
        entry = f"**用户**: {query}\n**回答**: {answer[:200]}..."
        if sources:
            entry += f"\n**来源**: {len(sources)}个代码片段"
        self.append_daily_log(entry)
    
    def learn_preference(self, preference: str, value: str):
        """学习用户偏好"""
        self.update_long_term_memory("用户偏好", f"- {preference}: {value}")
        logger.info(f"Learned preference: {preference} = {value}")
    
    def record_lesson(self, lesson: str):
        """记录经验教训"""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        content = f"- {timestamp}: {lesson}"
        self.update_long_term_memory("经验教训", content)


# 使用示例
if __name__ == "__main__":
    manager = MemoryManager("./memory")
    
    # 加载记忆
    memory = manager.load_memory()
    print("Loaded memory:")
    print(memory[:500] if memory else "No memory found")
    
    # 记录交互
    manager.record_interaction(
        "找到用户认证的代码",
        "认证代码在 src/auth/login.py:45-89",
        [{"file_path": "src/auth/login.py", "start_line": 45}]
    )
