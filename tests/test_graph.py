"""
测试LangGraph工作流
"""
import pytest
from unittest.mock import Mock
from src.agent.graph import IntentType, ReviewDecision, GraphState, CodeRAGGraph


class TestGraphState:
    def test_initial_state(self):
        state = GraphState(
            query="test query",
            codebase_path="/path/to/code",
        )
        assert state.query == "test query"
        assert state.intent is None


class TestCodeRAGGraph:
    @pytest.fixture
    def mock_vector_store(self):
        mock = Mock()
        mock.get_collection_info.return_value = {"name": "test", "count": 0}
        return mock
    
    def test_graph_initialization(self, mock_vector_store):
        graph = CodeRAGGraph(vector_store=mock_vector_store, verbose=False)
        assert graph.verbose is False
    
    def test_get_graph_diagram(self, mock_vector_store):
        graph = CodeRAGGraph(vector_store=mock_vector_store, verbose=False)
        diagram = graph.get_graph_diagram()
        assert "classify_intent" in diagram
        assert "search_code" in diagram
