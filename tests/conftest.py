"""
测试配置和fixtures
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_python_code() -> str:
    return '''
"""
Sample module for testing
"""
import os
from typing import List

class UserManager:
    """User management class"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def add_user(self, user_id: str, name: str) -> bool:
        """Add a user"""
        return True
    
    def get_user(self, user_id: str):
        """Get user info"""
        return None

def authenticate(username: str, password: str) -> bool:
    """Authenticate user"""
    return len(password) >= 6
'''


@pytest.fixture
def sample_codebase(temp_dir, sample_python_code) -> Path:
    py_dir = temp_dir / "py"
    py_dir.mkdir()
    (py_dir / "user.py").write_text(sample_python_code)
    (py_dir / "__init__.py").write_text("")
    return temp_dir
