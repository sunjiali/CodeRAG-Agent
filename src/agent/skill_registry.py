"""
Skill Registry - 技能注册与动态加载

实现按需加载工具，节省Token
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from loguru import logger
import json


@dataclass
class Skill:
    """技能定义"""
    name: str
    description: str
    doc: str  # SKILL.md 内容
    tools: List[Dict] = field(default_factory=list)
    handlers: Dict[str, Callable] = field(default_factory=dict)
    loaded: bool = False


class SkillRegistry:
    """技能注册表"""
    
    def __init__(self, skills_dir: str = "./skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        self._catalog: Dict[str, Skill] = {}
        self._active: Dict[str, Skill] = {}
        
        self._scan_skills()
    
    def _scan_skills(self):
        """扫描技能目录"""
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            
            # 解析SKILL.md
            doc = skill_md.read_text(encoding="utf-8")
            description = self._extract_description(doc)
            
            # 查找schema.json
            schemas = []
            schema_file = skill_dir / "schema.json"
            if schema_file.exists():
                schemas = json.loads(schema_file.read_text(encoding="utf-8"))
            
            self._catalog[skill_dir.name] = Skill(
                name=skill_dir.name,
                description=description,
                doc=doc,
                tools=schemas,
            )
        
        logger.info(f"Scanned {len(self._catalog)} skills: {list(self._catalog.keys())}")
    
    def _extract_description(self, doc: str) -> str:
        """从SKILL.md提取描述（第一个标题后的内容）"""
        lines = doc.split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return "Unknown skill"
    
    def get_menu(self) -> str:
        """生成技能菜单"""
        lines = ["Available skills (use load_skill to activate):\n"]
        
        for name, skill in sorted(self._catalog.items()):
            status = " [loaded]" if name in self._active else ""
            lines.append(f"- {name}: {skill.description}{status}")
        
        return "\n".join(lines)
    
    def load_skill(self, name: str) -> str:
        """加载技能"""
        if name not in self._catalog:
            return f"Error: Unknown skill '{name}'. Check the skill menu."
        
        if name in self._active:
            return f"Skill '{name}' is already loaded."
        
        skill = self._catalog[name]
        self._active[name] = skill
        skill.loaded = True
        
        tool_names = [t.get("name", "unknown") for t in skill.tools]
        
        logger.info(f"Loaded skill '{name}' with {len(skill.tools)} tools")
        
        return (
            f"Loaded skill '{name}' with {len(skill.tools)} tools: "
            f"{', '.join(tool_names)}\n\n"
            f"Documentation:\n{skill.doc[:1000]}"  # 只返回前1000字符
        )
    
    def unload_skill(self, name: str) -> str:
        """卸载技能"""
        if name not in self._active:
            return f"Skill '{name}' is not loaded."
        
        del self._active[name]
        self._catalog[name].loaded = False
        
        logger.info(f"Unloaded skill '{name}'")
        return f"Unloaded skill '{name}'."
    
    def get_active_schemas(self) -> List[Dict]:
        """获取当前活跃工具的模式"""
        schemas = []
        
        for skill in self._active.values():
            schemas.extend(skill.tools)
        
        # 添加元工具
        schemas.append({
            "name": "load_skill",
            "description": "Load a skill by name to activate its tools. Available skills: " + 
                          ", ".join(self._catalog.keys()),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Skill name from the menu"
                    }
                },
                "required": ["name"]
            }
        })
        
        schemas.append({
            "name": "unload_skill",
            "description": "Unload a skill to free context space",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Skill name to unload"
                    }
                },
                "required": ["name"]
            }
        })
        
        return schemas
    
    def dispatch(self, tool_name: str, arguments: Dict) -> str:
        """分发工具调用"""
        # 处理元工具
        if tool_name == "load_skill":
            return self.load_skill(arguments.get("name", ""))
        if tool_name == "unload_skill":
            return self.unload_skill(arguments.get("name", ""))
        
        # 查找工具处理器
        for skill in self._active.values():
            if tool_name in skill.handlers:
                try:
                    return str(skill.handlers[tool_name](**arguments))
                except Exception as e:
                    return f"Error: {type(e).__name__}: {e}"
        
        return f"Error: Tool '{tool_name}' not found. Is the skill loaded?"
    
    def register_handler(self, skill_name: str, tool_name: str, handler: Callable):
        """注册工具处理器"""
        if skill_name in self._catalog:
            self._catalog[skill_name].handlers[tool_name] = handler
            logger.debug(f"Registered handler: {skill_name}.{tool_name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_skills": len(self._catalog),
            "active_skills": len(self._active),
            "active_tools": sum(len(s.tools) for s in self._active.values()),
            "catalog": list(self._catalog.keys()),
            "active": list(self._active.keys()),
        }


# 使用示例
if __name__ == "__main__":
    registry = SkillRegistry("./skills")
    
    # 显示菜单
    print("=== Skill Menu ===")
    print(registry.get_menu())
    
    # 加载技能
    print("\n=== Load code_search ===")
    result = registry.load_skill("code_search")
    print(result[:500])
    
    # 获取活跃工具
    print("\n=== Active Schemas ===")
    schemas = registry.get_active_schemas()
    print(f"Total: {len(schemas)} tools")
    for s in schemas:
        print(f"  - {s.get('name')}")
    
    # 统计
    print("\n=== Stats ===")
    print(registry.get_stats())
