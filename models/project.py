"""Project model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Project:
    """Modelo de Proyecto."""
    
    id: Optional[int] = None
    name: str = ""
    profile_name: str = ""
    description: str = ""
    aws_access_key_id: str = ""
    aws_access_secret: str = ""
    aws_region: str = "us-east-1"
    aws_session_token: Optional[str] = None
    is_active: bool = False
    created_at: str = ""
    updated_at: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Create Project from dictionary."""
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            profile_name=data.get("profile_name", ""),
            description=data.get("description", ""),
            aws_access_key_id=data.get("aws_access_key_id", ""),
            aws_access_secret=data.get("aws_access_secret", ""),
            aws_region=data.get("aws_region", "us-east-1"),
            aws_session_token=data.get("aws_session_token"),
            is_active=bool(data.get("is_active", 0)),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", "")
        )
    
    def to_dict(self, mask_credentials: bool = True) -> dict:
        """Convierte a diccionario."""
        result = {
            "id": self.id,
            "name": self.name,
            "profile_name": self.profile_name,
            "description": self.description,
            "aws_region": self.aws_region,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
        if mask_credentials:
            result["aws_access_key_id"] = self.aws_access_key_id[:4] + "****" if self.aws_access_key_id else ""
            result["aws_access_secret"] = "****" if self.aws_access_secret else ""
        else:
            result["aws_access_key_id"] = self.aws_access_key_id
            result["aws_access_secret"] = self.aws_access_secret
            result["aws_session_token"] = self.aws_session_token
        
        return result
