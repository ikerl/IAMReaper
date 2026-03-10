"""Run model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Run:
    """Modelo de Ejecución."""
    
    id: Optional[int] = None
    project_id: int = 0
    module_name: str = ""
    status: str = "running"
    started_at: str = ""
    completed_at: Optional[str] = None
    summary_success: int = 0
    summary_failed: int = 0
    summary_access_denied: int = 0
    
    @classmethod
    def from_dict(cls, data: dict) -> "Run":
        """Create Run from dictionary."""
        return cls(
            id=data.get("id"),
            project_id=data.get("project_id", 0),
            module_name=data.get("module_name", ""),
            status=data.get("status", "running"),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at"),
            summary_success=data.get("summary_success", 0),
            summary_failed=data.get("summary_failed", 0),
            summary_access_denied=data.get("summary_access_denied", 0)
        )
    
    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "module_name": self.module_name,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary_success": self.summary_success,
            "summary_failed": self.summary_failed,
            "summary_access_denied": self.summary_access_denied,
            "total": self.summary_success + self.summary_failed
        }
