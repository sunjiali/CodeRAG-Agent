"""
代码解析器 - 使用Tree-sitter解析代码AST
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from loguru import logger

try:
    from tree_sitter_languages import get_language, get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


@dataclass
class CodeEntity:
    """代码实体（函数、类、方法等）"""
    name: str
    entity_type: str
    file_path: str
    start_line: int
    end_line: int
    code: str
    docstring: str = ""
    parameters: List[str] = field(default_factory=list)
    language: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "code": self.code,
            "docstring": self.docstring,
            "parameters": self.parameters,
            "language": self.language,
        }


@dataclass
class ParsedFile:
    """解析后的文件"""
    file_path: str
    language: str
    entities: List[CodeEntity] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    raw_content: str = ""


class CodeParser:
    """代码解析器 - 使用Tree-sitter解析代码AST"""
    
    EXTENSION_MAP = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".go": "go", ".java": "java", ".rs": "rust",
    }
    
    def __init__(self, supported_languages: Optional[List[str]] = None):
        self.supported_languages = supported_languages or ["python", "javascript", "go"]
        self._parsers: Dict[str, Any] = {}
        
        if TREE_SITTER_AVAILABLE:
            for lang in self.supported_languages:
                try:
                    self._parsers[lang] = get_parser(lang)
                except Exception as e:
                    logger.warning(f"Failed to init parser for {lang}: {e}")
    
    def get_language(self, file_path: str) -> Optional[str]:
        suffix = Path(file_path).suffix.lower()
        return self.EXTENSION_MAP.get(suffix)
    
    def parse_file(self, file_path: str) -> Optional[ParsedFile]:
        path = Path(file_path)
        if not path.exists():
            return None
        
        language = self.get_language(file_path)
        if not language:
            return None
        
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return None
        
        parsed_file = ParsedFile(
            file_path=file_path,
            language=language,
            raw_content=content,
        )
        
        if TREE_SITTER_AVAILABLE and language in self._parsers:
            parsed_file = self._parse_with_tree_sitter(parsed_file, language)
        else:
            parsed_file = self._parse_with_regex(parsed_file, language)
        
        return parsed_file
    
    def _parse_with_tree_sitter(self, parsed_file: ParsedFile, language: str) -> ParsedFile:
        parser = self._parsers[language]
        tree = parser.parse(bytes(parsed_file.raw_content, "utf8"))
        lines = parsed_file.raw_content.split("\n")
        
        def traverse(node, parent_type=None):
            node_type = str(node.type)
            
            if language == "python":
                if node_type in ("function_definition", "async_function_definition"):
                    name = self._get_node_text(node, lines, "name") or "anonymous"
                    params = self._extract_python_params(node, lines)
                    docstring = self._extract_python_docstring(node, lines)
                    parsed_file.entities.append(CodeEntity(
                        name=name,
                        entity_type="function",
                        file_path=parsed_file.file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        code=self._get_node_text(node, lines),
                        docstring=docstring,
                        parameters=params,
                        language=language,
                    ))
                elif node_type == "class_definition":
                    name = self._get_node_text(node, lines, "name") or "Unknown"
                    parsed_file.entities.append(CodeEntity(
                        name=name,
                        entity_type="class",
                        file_path=parsed_file.file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        code=self._get_node_text(node, lines),
                        language=language,
                    ))
            elif language == "javascript":
                if node_type in ("function_declaration", "arrow_function"):
                    name = self._get_js_function_name(node, lines)
                    parsed_file.entities.append(CodeEntity(
                        name=name,
                        entity_type="function",
                        file_path=parsed_file.file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        code=self._get_node_text(node, lines),
                        language=language,
                    ))
                elif node_type == "class_declaration":
                    name = self._get_node_text(node, lines, "identifier") or "Unknown"
                    parsed_file.entities.append(CodeEntity(
                        name=name,
                        entity_type="class",
                        file_path=parsed_file.file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        code=self._get_node_text(node, lines),
                        language=language,
                    ))
            
            for child in node.children:
                traverse(child, node_type)
        
        traverse(tree.root_node)
        parsed_file.imports = self._extract_imports(parsed_file.raw_content, language)
        return parsed_file
    
    def _get_node_text(self, node, lines: List[str], child_name: Optional[str] = None) -> str:
        if child_name:
            for child in node.children:
                if hasattr(child, 'type') and child.type == child_name:
                    start, end = child.start_point, child.end_point
                    if start[0] == end[0]:
                        return lines[start[0]][start[1]:end[1]]
                    return "\n".join(lines[start[0]:end[0]+1])
        
        start, end = node.start_point, node.end_point
        if start[0] == end[0]:
            return lines[start[0]][start[1]:end[1]]
        return "\n".join(lines[start[0]:end[0]+1])
    
    def _get_js_function_name(self, node, lines: List[str]) -> str:
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child, lines)
        return "anonymous"
    
    def _extract_python_params(self, node, lines: List[str]) -> List[str]:
        params = []
        for child in node.children:
            if child.type == "arguments":
                for c in child.children:
                    if c.type == "identifier":
                        params.append(self._get_node_text(c, lines))
        return params
    
    def _extract_python_docstring(self, node, lines: List[str]) -> str:
        for child in node.children:
            if child.type == "block":
                if child.children:
                    first_stmt = child.children[0]
                    if first_stmt.type == "expression_statement":
                        expr = first_stmt.children[0]
                        if expr.type == "string":
                            text = self._get_node_text(expr, lines)
                            if text.startswith('"""') or text.startswith("'''"):
                                text = text[3:-3]
                            return text.strip()
        return ""
    
    def _extract_imports(self, content: str, language: str) -> List[str]:
        imports = []
        for line in content.split("\n"):
            line = line.strip()
            if language == "python":
                if line.startswith("import ") or line.startswith("from "):
                    imports.append(line)
            elif language == "javascript":
                if line.startswith("import ") or line.startswith("require("):
                    imports.append(line)
        return imports
    
    def _parse_with_regex(self, parsed_file: ParsedFile, language: str) -> ParsedFile:
        content = parsed_file.raw_content
        
        if language == "python":
            func_pattern = r'def\s+(\w+)\s*\([^)]*\)(?:->\s*[\w\[\],\s]+)?:'
            for match in re.finditer(func_pattern, content):
                parsed_file.entities.append(CodeEntity(
                    name=match.group(1),
                    entity_type="function",
                    file_path=parsed_file.file_path,
                    start_line=content[:match.start()].count('\n') + 1,
                    end_line=content[:match.end()].count('\n') + 1,
                    code=match.group(0),
                    language=language,
                ))
            
            class_pattern = r'class\s+(\w+)(?:\([^)]*\))?:'
            for match in re.finditer(class_pattern, content):
                parsed_file.entities.append(CodeEntity(
                    name=match.group(1),
                    entity_type="class",
                    file_path=parsed_file.file_path,
                    start_line=content[:match.start()].count('\n') + 1,
                    end_line=content[:match.end()].count('\n') + 1,
                    code=match.group(0),
                    language=language,
                ))
        
        return parsed_file
    
    def parse_directory(self, directory: str, recursive: bool = True) -> List[ParsedFile]:
        path = Path(directory)
        if not path.exists():
            return []
        
        parsed_files = []
        for file_path in path.rglob("*") if recursive else path.glob("*"):
            if file_path.is_file():
                language = self.get_language(str(file_path))
                if language and language in self.supported_languages:
                    parsed = self.parse_file(str(file_path))
                    if parsed:
                        parsed_files.append(parsed)
        
        logger.info(f"Parsed {len(parsed_files)} files from {directory}")
        return parsed_files
