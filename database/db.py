"""Database CRUD operations."""

import json
import sqlite3
import os
import configparser
from typing import Optional, List, Dict, Any
from database.schema import get_connection


# ==================== PROJECTS ====================

def create_project(
    name: str,
    profile_name: str,
    aws_access_key_id: str,
    aws_access_secret: str,
    aws_region: str = "us-east-1",
    aws_session_token: Optional[str] = None,
    description: str = ""
) -> int:
    """Create a new project."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO projects (
            name, profile_name, description, 
            aws_access_key_id, aws_access_secret, 
            aws_region, aws_session_token
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, profile_name, description, aws_access_key_id, 
          aws_access_secret, aws_region, aws_session_token))
    
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return project_id


def get_project(project_id: int) -> Optional[Dict]:
    """Get a project by ID."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def get_project_by_name(name: str) -> Optional[Dict]:
    """Get a project by name."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM projects WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def get_all_projects() -> List[Dict]:
    """Get all projects."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM projects ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def update_project(
    project_id: int,
    name: Optional[str] = None,
    profile_name: Optional[str] = None,
    description: Optional[str] = None,
    aws_access_key_id: Optional[str] = None,
    aws_access_secret: Optional[str] = None,
    aws_region: Optional[str] = None,
    aws_session_token: Optional[str] = None,
    is_active: Optional[bool] = None
) -> bool:
    """Update a project."""
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = []
    values = []
    
    if name is not None:
        updates.append("name = ?")
        values.append(name)
    if profile_name is not None:
        updates.append("profile_name = ?")
        values.append(profile_name)
    if description is not None:
        updates.append("description = ?")
        values.append(description)
    if aws_access_key_id is not None:
        updates.append("aws_access_key_id = ?")
        values.append(aws_access_key_id)
    if aws_access_secret is not None:
        updates.append("aws_access_secret = ?")
        values.append(aws_access_secret)
    if aws_region is not None:
        updates.append("aws_region = ?")
        values.append(aws_region)
    if aws_session_token is not None:
        updates.append("aws_session_token = ?")
        values.append(aws_session_token)
    if is_active is not None:
        updates.append("is_active = ?")
        values.append(1 if is_active else 0)
    
    if not updates:
        return False
    
    updates.append("updated_at = datetime('now')")
    values.append(project_id)
    
    query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, values)
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


def set_active_project(project_id: int) -> bool:
    """Set a project as active (and deactivate others)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Deactivate all projects
    cursor.execute("UPDATE projects SET is_active = 0")
    
    # Activate the selected project
    cursor.execute(
        "UPDATE projects SET is_active = 1, updated_at = datetime('now') WHERE id = ?",
        (project_id,)
    )
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


def delete_project(project_id: int) -> bool:
    """Delete a project, its runs/commands, and AWS credentials."""
    # First get the profile_name to remove credentials
    project = get_project(project_id)
    if project:
        profile_name = project.get('profile_name')
        
        # Remove profile from ~/.aws/credentials
        if profile_name:
            _remove_aws_profile(profile_name)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Delete commands for runs of this project
    cursor.execute("""
        DELETE FROM commands 
        WHERE run_id IN (SELECT id FROM runs WHERE project_id = ?)
    """, (project_id,))
    
    # Delete runs for this project
    cursor.execute("DELETE FROM runs WHERE project_id = ?", (project_id,))
    
    # Delete project
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


def _remove_aws_profile(profile_name: str) -> bool:
    """Remove a profile from ~/.aws/credentials."""
    try:
        aws_dir = os.path.expanduser("~/.aws")
        credentials_file = os.path.join(aws_dir, "credentials")
        
        if not os.path.exists(credentials_file):
            return True
        
        # Read existing credentials
        config = configparser.ConfigParser()
        config.read(credentials_file)
        
        # Remove profile if exists
        if config.has_section(profile_name):
            config.remove_section(profile_name)
            
            # Write back
            with open(credentials_file, 'w') as f:
                config.write(f)
        
        return True
    except Exception:
        return False


def get_active_project() -> Optional[Dict]:
    """Get the currently active project."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM projects WHERE is_active = 1")
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


# ==================== RUNS ====================

def create_run(project_id: int, module_name: str) -> int:
    """Create a new run."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO runs (project_id, module_name, status, started_at)
        VALUES (?, ?, 'running', datetime('now'))
    """, (project_id, module_name))
    
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return run_id


def get_run(run_id: int) -> Optional[Dict]:
    """Get a run by ID."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def get_runs_by_project(project_id: int) -> List[Dict]:
    """Get all runs for a project."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM runs 
        WHERE project_id = ? 
        ORDER BY started_at DESC
    """, (project_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_latest_run(project_id: int, module_name: str) -> Optional[Dict]:
    """Get the latest run for a project and module."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM runs 
        WHERE project_id = ? AND module_name = ?
        ORDER BY started_at DESC
        LIMIT 1
    """, (project_id, module_name))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def update_run_summary(
    run_id: int,
    summary_success: int,
    summary_failed: int,
    summary_access_denied: int,
    status: str = "completed"
) -> bool:
    """Update run summary and status."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE runs SET 
            summary_success = ?,
            summary_failed = ?,
            summary_access_denied = ?,
            status = ?,
            completed_at = datetime('now')
        WHERE id = ?
    """, (summary_success, summary_failed, summary_access_denied, status, run_id))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


def delete_run(run_id: int) -> bool:
    """Delete a run and its commands."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Delete commands
    cursor.execute("DELETE FROM commands WHERE run_id = ?", (run_id,))
    
    # Delete run
    cursor.execute("DELETE FROM runs WHERE id = ?", (run_id,))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


# ==================== COMMANDS ====================

def create_command(
    run_id: int,
    command: str,
    description: str,
    success: bool,
    stdout: str = "",
    stderr: str = "",
    return_code: int = 0,
    duration_ms: float = 0.0,
    error_type: Optional[str] = None,
    data: Any = None
) -> int:
    """Create a new command record."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Serialize data to JSON
    data_json = json.dumps(data) if data is not None else None
    
    cursor.execute("""
        INSERT INTO commands (
            run_id, command, description, success,
            stdout, stderr, return_code, duration_ms,
            error_type, data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (run_id, command, description, success, stdout, stderr,
          return_code, duration_ms, error_type, data_json))
    
    command_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return command_id


def get_command(command_id: int) -> Optional[Dict]:
    """Get a command by ID."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM commands WHERE id = ?", (command_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def get_commands_by_run(
    run_id: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0
) -> List[Dict]:
    """Get commands for a run with optional filters."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM commands WHERE run_id = ?"
    params = [run_id]
    
    # Filter by search term (command or description)
    if search:
        query += " AND (command LIKE ? OR description LIKE ?)"
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern])
    
    # Filter by status
    if status == "success":
        query += " AND success = 1"
    elif status == "failed":
        query += " AND success = 0"
    elif status == "access_denied":
        query += " AND error_type = 'access_denied'"
    
    query += " ORDER BY created_at"
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_command_count(
    run_id: int,
    search: Optional[str] = None,
    status: Optional[str] = None
) -> int:
    """Get total count of commands matching filters."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT COUNT(*) FROM commands WHERE run_id = ?"
    params = [run_id]
    
    if search:
        query += " AND (command LIKE ? OR description LIKE ?)"
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern])
    
    if status == "success":
        query += " AND success = 1"
    elif status == "failed":
        query += " AND success = 0"
    elif status == "access_denied":
        query += " AND error_type = 'access_denied'"
    
    cursor.execute(query, params)
    count = cursor.fetchone()[0]
    conn.close()
    
    return count
