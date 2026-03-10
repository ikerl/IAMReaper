"""AWS EFS enumeration module with all specified commands."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class EFSModule(BaseModule):
    """AWS EFS enumeration module."""

    MODULE_NAME = "efs"
    DISPLAY_NAME = "AWS EFS Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.file_systems: list[dict] = []

    def _add_result(self, result: CommandResult) -> None:
        """Add a command result to the executed commands list."""
        self.commands_executed.append({
            "command": result.command,
            "description": result.description,
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.return_code,
            "duration_ms": result.duration_ms,
            "error_type": result.error_type,
            "data": result.data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    def run_all(self) -> dict[str, Any]:
        """Execute all EFS enumeration checks."""
        self.commands_executed = []
        self.file_systems = []

        # List file systems
        self._describe_file_systems()

        # Get access points
        self._describe_access_points()

        # Get replication configurations
        self._describe_replication_configurations()

        # Generate summary
        summary = self._summarize_commands(self.commands_executed)

        return {
            "module": self.MODULE_NAME,
            "display_name": self.DISPLAY_NAME,
            "executed_at": datetime.utcnow().isoformat() + "Z",
            "commands_executed": self.commands_executed,
            "summary": summary,
            "data": self._extract_data()
        }

    def _extract_data(self) -> dict[str, Any]:
        """Extract structured data from executed commands."""
        data = {
            "file_systems": self.file_systems,
            "access_points": [],
            "replication_configurations": [],
            "total_file_systems": len(self.file_systems)
        }

        # Extract access points
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws efs describe-access-points"):
                if cmd["success"] and cmd["data"]:
                    data["access_points"] = cmd["data"].get("AccessPoints", [])
                break

        # Extract replication configurations
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws efs describe-replication-configurations"):
                if cmd["success"] and cmd["data"]:
                    data["replication_configurations"] = cmd["data"].get("Replications", [])
                break

        return data

    # ==================== FILE SYSTEMS ====================

    def _describe_file_systems(self) -> None:
        """Describe all EFS file systems."""
        cmd = "aws efs describe-file-systems"
        result = self.executor.execute(cmd, "Describe all EFS file systems")
        self._add_result(result)

        # Store file systems for later enumeration
        if result.success and result.data:
            items = result.data.get("FileSystems", [])
            self.file_systems = items
            for fs in items:
                fs_id = fs.get("FileSystemId")
                if fs_id:
                    self._describe_file_system_policy(fs_id)
                    self._describe_mount_targets(fs_id)

    def _describe_file_system_policy(self, file_system_id: str) -> None:
        """Describe file system policy."""
        cmd = f"aws efs describe-file-system-policy --file-system-id {file_system_id}"
        result = self.executor.execute(
            cmd,
            f"Describe file system policy for: {file_system_id}"
        )
        self._add_result(result)

    def _describe_mount_targets(self, file_system_id: str) -> None:
        """Describe mount targets for a file system."""
        cmd = f"aws efs describe-mount-targets --file-system-id {file_system_id}"
        result = self.executor.execute(
            cmd,
            f"Describe mount targets for: {file_system_id}"
        )
        self._add_result(result)

        # Get security groups for each mount target
        if result.success and result.data:
            mount_targets = result.data.get("MountTargets", [])
            for mt in mount_targets:
                mt_id = mt.get("MountTargetId")
                if mt_id:
                    self._describe_mount_target_security_groups(mt_id)

    def _describe_mount_target_security_groups(self, mount_target_id: str) -> None:
        """Describe security groups for a mount target."""
        cmd = f"aws efs describe-mount-target-security-groups --mount-target-id {mount_target_id}"
        result = self.executor.execute(
            cmd,
            f"Describe security groups for mount target: {mount_target_id}"
        )
        self._add_result(result)

        # Describe security groups in EC2
        if result.success and result.data:
            sg_ids = result.data.get("SecurityGroups", [])
            for sg_id in sg_ids:
                self._describe_security_group(sg_id)

    def _describe_security_group(self, security_group_id: str) -> None:
        """Describe an EC2 security group."""
        cmd = f"aws ec2 describe-security-groups --group-ids {security_group_id}"
        result = self.executor.execute(
            cmd,
            f"Describe security group: {security_group_id}"
        )
        self._add_result(result)

    # ==================== ACCESS POINTS ====================

    def _describe_access_points(self) -> None:
        """Describe all EFS access points."""
        cmd = "aws efs describe-access-points"
        result = self.executor.execute(cmd, "Describe all EFS access points")
        self._add_result(result)

    # ==================== REPLICATION ====================

    def _describe_replication_configurations(self) -> None:
        """Describe replication configurations."""
        cmd = "aws efs describe-replication-configurations"
        result = self.executor.execute(cmd, "Describe replication configurations")
        self._add_result(result)
