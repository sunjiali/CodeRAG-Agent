"""
数据库连接和操作模块
"""
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager


class DatabaseError(Exception):
    """数据库异常"""
    pass


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
    
    def connect(self) -> None:
        if self._connection:
            return
        try:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as e:
            raise DatabaseError(f"连接失败: {e}")
    
    @contextmanager
    def transaction(self):
        self.connect()
        try:
            yield self._connection
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise
    
    def execute(self, sql: str, params: Optional[Tuple] = None, fetch: bool = False):
        self.connect()
        try:
            cursor = self._connection.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            if fetch:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            
            self._connection.commit()
            return None
        except sqlite3.Error as e:
            raise DatabaseError(f"执行失败: {e}")
    
    def create_table(self, table_name: str, columns: Dict[str, str]) -> None:
        col_defs = [f"{name} {dtype}" for name, dtype in columns.items()]
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)})"
        self.execute(sql)
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        columns = list(data.keys())
        placeholders = ["?"] * len(columns)
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        self.connect()
        cursor = self._connection.cursor()
        cursor.execute(sql, tuple(data.values()))
        self._connection.commit()
        return cursor.lastrowid


if __name__ == "__main__":
    db = DatabaseManager(":memory:")
    db.create_table("users", {"id": "INTEGER PRIMARY KEY", "username": "TEXT", "email": "TEXT"})
    user_id = db.insert("users", {"username": "alice", "email": "alice@example.com"})
    print(f"插入用户ID: {user_id}")
