"""Base module class for AWS enumeration modules."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class BaseModule(ABC):
    """Base class for all AWS enumeration modules."""

    MODULE_NAME: str = "base"
    DISPLAY_NAME: str = "Base Module"

    def __init__(self, executor: 'AWSExecutor'):
        """Initialize the module with an AWS executor."""
        self.executor = executor
        self.results: dict[str, Any] = {}

    @abstractmethod
    def run_all(self) -> dict[str, Any]:
        """Run all enumeration checks for this module."""
        pass

    def get_module_info(self) -> dict[str, Any]:
        """Get module information."""
        return {
            "name": self.MODULE_NAME,
            "display_name": self.DISPLAY_NAME,
            "results": self.results
        }

    def _create_result_entry(
        self,
        command: str,
        description: str,
        success: bool,
        stdout: str = "",
        stderr: str = "",
        return_code: int = -1,
        duration_ms: float = 0.0,
        data: Any = None,
        error_type: str | None = None
    ) -> dict[str, Any]:
        """Create a standardized result entry for a command execution."""
        import json
        
        parsed_data = None
        if stdout:
            try:
                parsed_data = json.loads(stdout)
            except json.JSONDecodeError:
                parsed_data = stdout

        return {
            "command": command,
            "description": description,
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code,
            "duration_ms": duration_ms,
            "error_type": error_type,
            "data": parsed_data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    def _summarize_commands(self, commands: list[dict]) -> dict[str, int]:
        """Summarize command execution results."""
        summary = {
            "total": len(commands),
            "successful": 0,
            "failed": 0,
            "access_denied": 0,
            "other_errors": 0
        }

        for cmd in commands:
            if cmd["success"]:
                summary["successful"] += 1
            else:
                summary["failed"] += 1
                if cmd["error_type"] == "access_denied":
                    summary["access_denied"] += 1
                else:
                    summary["other_errors"] += 1

        return summary
