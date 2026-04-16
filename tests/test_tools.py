"""
测试工具
"""
from src.agent.tools import ToolResult, CodeAnalyzeTool


class TestToolResult:
    def test_success_result(self):
        result = ToolResult(tool_name="test", success=True, result={"data": "test"}, execution_time=0.5)
        assert result.success is True
        assert result.result == {"data": "test"}
        assert result.error is None
    
    def test_error_result(self):
        result = ToolResult(tool_name="test", success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"


class TestCodeAnalyzeTool:
    def test_analyze_function(self):
        tool = CodeAnalyzeTool()
        code = '''
def hello(name):
    """Say hello"""
    return f"Hello, {name}"
'''
        result = tool._analyze(code)
        assert "error" not in result
        assert len(result.get("functions", [])) >= 1
    
    def test_estimate_complexity(self):
        tool = CodeAnalyzeTool()
        simple = "def foo(): pass"
        assert tool._estimate_complexity(simple) == 1
