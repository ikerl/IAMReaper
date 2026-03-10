"""Database initialization and schema."""

import sqlite3
import os
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "iamreaper.db"


def get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create projects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            profile_name TEXT NOT NULL UNIQUE,
            description TEXT,
            aws_access_key_id TEXT NOT NULL,
            aws_access_secret TEXT NOT NULL,
            aws_region TEXT NOT NULL DEFAULT 'us-east-1',
            aws_session_token TEXT,
            is_active BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    
    # Create runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            module_name TEXT NOT NULL,
            status TEXT DEFAULT 'running',
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            summary_success INTEGER DEFAULT 0,
            summary_failed INTEGER DEFAULT 0,
            summary_access_denied INTEGER DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    
    # Create commands table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            command TEXT NOT NULL,
            description TEXT,
            success BOOLEAN NOT NULL,
            stdout TEXT,
            stderr TEXT,
            return_code INTEGER,
            duration_ms REAL,
            error_type TEXT,
            data TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (run_id) REFERENCES runs(id)
        )
    """)
    
    # Create indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_commands_run 
        ON commands(run_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_commands_success 
        ON commands(success)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_runs_project 
        ON runs(project_id)
    """)
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {DB_PATH}")


def get_db():
    """Get database path."""
    return DB_PATH
