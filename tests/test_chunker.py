"""
测试代码分块器
"""
import pytest
from pathlib import Path
from src.indexer.parser import CodeParser
from src.indexer.chunker import CodeChunker, CodeChunk


class TestCodeChunker:
    def test_create_chunk_id(self):
        chunker = CodeChunker()
        chunk_id = chunker._generate_chunk_id("/path/to/file.py", "function", "my_function", 10)
        assert "file" in chunk_id
        assert "function" in chunk_id
    
    def test_chunk_python_file(self, temp_dir):
        code = '''
def func_a():
    """Function A"""
    pass

class MyClass:
    def method_b(self):
        pass
'''
        file_path = temp_dir / "test.py"
        file_path.write_text(code)
        
        parser = CodeParser(supported_languages=["python"])
        parsed = parser.parse_file(str(file_path))
        
        chunker = CodeChunker()
        chunks = chunker.chunk_file(parsed)
        
        assert len(chunks) >= 1
    
    def test_chunk_to_document(self):
        chunk = CodeChunk(
            chunk_id="test_func",
            content="def test(): pass",
            file_path="test.py",
            language="python",
            start_line=1,
            end_line=1,
            entity_type="function",
            entity_name="test",
            docstring="Test function",
        )
        
        doc = chunk.to_document()
        assert "def test()" in doc


class TestCodeChunk:
    def test_to_dict(self):
        chunk = CodeChunk(
            chunk_id="test",
            content="code",
            file_path="test.py",
            language="python",
            start_line=1,
            end_line=10,
            entity_type="function",
        )
        
        d = chunk.to_dict()
        assert d["chunk_id"] == "test"
        assert d["content"] == "code"
