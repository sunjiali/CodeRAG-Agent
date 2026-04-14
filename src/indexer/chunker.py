"""
代码分块器 - 将代码切分为适合检索的小块
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

from .parser import ParsedFile, CodeEntity


@dataclass
class CodeChunk:
    """代码块"""
    chunk_id: str
    content: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    entity_type: str
    entity_name: Optional[str] = None
    docstring: str = ""
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "file_path": self.file_path,
            "language": self.language,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "docstring": self.docstring,
            "dependencies": self.dependencies,
        }
    
    def to_document(self) -> str:
        doc_parts = []
        if self.docstring:
            doc_parts.append(f"Documentation:\n{self.docstring}")
        doc_parts.append(f"Code:\n{self.content}")
        if self.dependencies:
            doc_parts.append(f"Dependencies: {', '.join(self.dependencies)}")
        return "\n\n".join(doc_parts)


class CodeChunker:
    """代码分块器 - 按函数/类切分，保留上下文"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_file(self, parsed_file: ParsedFile) -> List[CodeChunk]:
        chunks = []
        file_imports = parsed_file.imports
        
        for entity in parsed_file.entities:
            content = entity.code
            if len(content) < 30:
                continue
            
            chunk_id = self._generate_chunk_id(
                parsed_file.file_path, entity.entity_type, entity.name, entity.start_line
            )
            
            chunks.append(CodeChunk(
                chunk_id=chunk_id,
                content=content,
                file_path=parsed_file.file_path,
                language=parsed_file.language,
                start_line=entity.start_line,
                end_line=entity.end_line,
                entity_type=entity.entity_type,
                entity_name=entity.name,
                docstring=entity.docstring,
                dependencies=self._extract_dependencies(content, file_imports),
                metadata={"parameters": entity.parameters},
            ))
        
        if not chunks and parsed_file.raw_content.strip():
            chunks.append(self._create_chunk_from_file(parsed_file))
        
        return chunks
    
    def _create_chunk_from_file(self, parsed_file: ParsedFile) -> CodeChunk:
        return CodeChunk(
            chunk_id=self._generate_chunk_id(parsed_file.file_path, "module", Path(parsed_file.file_path).stem, 1),
            content=parsed_file.raw_content[:self.chunk_size],
            file_path=parsed_file.file_path,
            language=parsed_file.language,
            start_line=1,
            end_line=len(parsed_file.raw_content.split("\n")),
            entity_type="module",
            entity_name=Path(parsed_file.file_path).stem,
            dependencies=parsed_file.imports,
        )
    
    def _generate_chunk_id(self, file_path: str, entity_type: str, entity_name: str, start_line: int) -> str:
        safe_name = entity_name.replace(" ", "_").replace("/", "_")
        file_name = Path(file_path).stem
        return f"{file_name}_{entity_type}_{safe_name}_L{start_line}"
    
    def _extract_dependencies(self, content: str, file_imports: List[str]) -> List[str]:
        deps = set()
        for imp in file_imports:
            if "from" in imp:
                module = imp.split("from")[1].strip().split()[0].strip('"\'')
                deps.add(module)
            elif "import" in imp:
                module = imp.replace("import", "").strip().split(".")[0]
                deps.add(module)
        return list(deps)
    
    def chunk_files(self, parsed_files: List[ParsedFile]) -> List[CodeChunk]:
        all_chunks = []
        for parsed_file in parsed_files:
            chunks = self.chunk_file(parsed_file)
            all_chunks.extend(chunks)
        logger.info(f"Created {len(all_chunks)} total chunks from {len(parsed_files)} files")
        return all_chunks
