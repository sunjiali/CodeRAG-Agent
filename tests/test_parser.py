"""
测试代码解析器
"""
import pytest
from pathlib import Path
from src.indexer.parser import CodeParser, CodeEntity


class TestCodeParser:
    def test_get_language(self):
        parser = CodeParser()
        assert parser.get_language("test.py") == "python"
        assert parser.get_language("test.js") == "javascript"
        assert parser.get_language("test.go") == "go"
        assert parser.get_language("test.txt") is None
    
    def test_parse_python_file(self, temp_dir):
        code = '''
def hello():
    """Say hello"""
    print("Hello")

class MyClass:
    def method(self):
        pass
'''
        file_path = temp_dir / "test.py"
        file_path.write_text(code)
        
        parser = CodeParser(supported_languages=["python"])
        parsed = parser.parse_file(str(file_path))
        
        assert parsed is not None
        assert parsed.language == "python"
    
    def test_parse_nonexistent_file(self):
        parser = CodeParser()
        parsed = parser.parse_file("/nonexistent/file.py")
        assert parsed is None
    
    def test_parse_directory(self, sample_codebase):
        parser = CodeParser(supported_languages=["python"])
        parsed_files = parser.parse_directory(str(sample_codebase))
        assert len(parsed_files) >= 1


class TestCodeEntity:
    def test_to_dict(self):
        entity = CodeEntity(
            name="test_func",
            entity_type="function",
            file_path="/path/to/file.py",
            start_line=10,
            end_line=20,
            code="def test_func(): pass",
        )
        
        d = entity.to_dict()
        assert d["name"] == "test_func"
        assert d["entity_type"] == "function"
        assert d["start_line"] == 10
