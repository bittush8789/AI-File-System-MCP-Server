import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = "d:/File-system/backend/database/metadata.db"

# Ensure the database directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # files table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # search_history table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # generated_docs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_name TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # chat_history table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()

# Initialize DB on import
init_db()

# DB Helper functions
def register_file(file_path: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
        INSERT INTO files (file_path, created_at, updated_at) 
        VALUES (?, ?, ?)
        ON CONFLICT(file_path) DO UPDATE SET updated_at = ?
        """, (file_path, now, now, now))
        conn.commit()

def remove_file(file_path: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files WHERE file_path = ?", (file_path,))
        conn.commit()

def log_search(query: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO search_history (query) VALUES (?)", (query,))
        conn.commit()

def log_generated_doc(document_name: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO generated_docs (document_name) VALUES (?)", (document_name,))
        conn.commit()

def log_chat(question: str, response: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_history (question, response) VALUES (?, ?)", (question, response))
        conn.commit()

def get_chat_history(limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, question, response, timestamp FROM chat_history ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_search_history(limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, query, timestamp FROM search_history ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_all_files() -> List[str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM files")
        return [row["file_path"] for row in cursor.fetchall()]
