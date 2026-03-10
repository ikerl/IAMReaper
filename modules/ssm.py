"""AWS SSM (Systems Manager) Enumeration Module."""

import json
from datetime import datetime
from typing import Any

from modules.base import BaseModule
from modules.executor import AWSExecutor


class SSMModule(BaseModule):
    """AWS Systems Manager enumeration module."""

    MODULE_NAME = "ssm"
    DISPLAY_NAME = "AWS SSM Enumeration"

    def __init__(self, executor: AWSExecutor):
        """Initialize the SSM module with an AWS executor."""
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.instance_ids: list[str] = []

    def _add_result(self, result) -> None:
        """Add command result to the list."""
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
        """Execute all SSM enumeration checks."""
        self.commands_executed = []
        self.instance_ids = []

        # Get instance information
        self._describe_instance_information()

        # Get parameters
        self._describe_parameters()

        # Get sessions (Active and History)
        self._describe_sessions_active()
        self._describe_sessions_history()

        # Get patch information for instances
        self._get_instance_patches()

        # Get patch states for instances
        self._get_instance_patch_states()

        # Get association status for instances
        self._get_instance_association_status()

        # Summary
        summary = self._summarize_commands(self.commands_executed)
        return {
            "module": self.MODULE_NAME,
            "display_name": self.DISPLAY_NAME,
            "executed_at": datetime.utcnow().isoformat() + "Z",
            "commands_executed": self.commands_executed,
            "summary": summary,
            "data": self._extract_data()
        }

    def _describe_instance_information(self) -> None:
        """Get information about managed instances."""
        result = self.executor.execute_aws(
            "ssm",
            "describe-instance-information",
            "List SSM managed instances",
            parse_json=True
        )
        self._add_result(result)

        # Extract instance IDs for later use
        if result.success and result.data:
            try:
                self.instance_ids = [
                    inst.get("InstanceId")
                    for inst in result.data.get("InstanceInformationList", [])
                    if inst.get("InstanceId")
                ]
            except (KeyError, TypeError):
                pass

    def _describe_parameters(self) -> None:
        """Get parameter information."""
        result = self.executor.execute_aws(
            "ssm",
            "describe-parameters",
            "List SSM parameters",
            parse_json=True
        )
        self._add_result(result)

    def _describe_sessions_active(self) -> None:
        """Get active SSM sessions."""
        result = self.executor.execute_aws(
            "ssm",
            "describe-sessions",
            "List active SSM sessions",
            state="Active",
            parse_json=True
        )
        self._add_result(result)

    def _describe_sessions_history(self) -> None:
        """Get SSM session history."""
        result = self.executor.execute_aws(
            "ssm",
            "describe-sessions",
            "List SSM session history",
            state="History",
            parse_json=True
        )
        self._add_result(result)

    def _get_instance_patches(self) -> None:
        """Get patch information for each instance (limited to 10 instances)."""
        for instance_id in self.instance_ids[:10]:
            if not instance_id:
                continue
            result = self.executor.execute_aws(
                "ssm",
                "describe-instance-patches",
                f"Get patches for instance {instance_id}",
                instance_id=instance_id,
                parse_json=True
            )
            self._add_result(result)

    def _get_instance_patch_states(self) -> None:
        """Get patch states for each instance (limited to 10 instances)."""
        # Limit to 10 instance IDs per call
        instance_ids_chunk = self.instance_ids[:10]
        if not instance_ids_chunk:
            return

        result = self.executor.execute_aws(
            "ssm",
            "describe-instance-patch-states",
            "Get patch states for instances",
            instance_ids=instance_ids_chunk,
            parse_json=True
        )
        self._add_result(result)

    def _get_instance_association_status(self) -> None:
        """Get association status for each instance (limited to 10 instances)."""
        for instance_id in self.instance_ids[:10]:
            if not instance_id:
                continue
            result = self.executor.execute_aws(
                "ssm",
                "describe-instance-associations-status",
                f"Get association status for instance {instance_id}",
                instance_id=instance_id,
                parse_json=True
            )
            self._add_result(result)

    def _extract_data(self) -> dict[str, Any]:
        """Extract structured data from command results."""
        data = {
            "instances": [],
            "total_instances": 0,
            "parameters": [],
            "total_parameters": 0,
            "active_sessions": [],
            "session_history": [],
            "patch_states": [],
            "association_status": []
        }

        for cmd in self.commands_executed:
            if not cmd.get("success") or not cmd.get("data"):
                continue

            d = cmd.get("data", {})

            # Instance information
            if "describe-instance-information" in cmd.get("command", ""):
                try:
                    instances = d.get("InstanceInformationList", [])
                    data["instances"] = instances
                    data["total_instances"] = len(instances)
                except (KeyError, TypeError):
                    pass

            # Parameters
            elif "describe-parameters" in cmd.get("command", ""):
                try:
                    params = d.get("Parameters", [])
                    data["parameters"] = params
                    data["total_parameters"] = len(params)
                except (KeyError, TypeError):
                    pass

            # Active sessions
            elif "describe-sessions" in cmd.get("command", "") and "Active" in str(d):
                try:
                    sessions = d.get("Sessions", [])
                    data["active_sessions"] = sessions
                except (KeyError, TypeError):
                    pass

            # Session history
            elif "describe-sessions" in cmd.get("command", "") and "History" in str(d):
                try:
                    sessions = d.get("Sessions", [])
                    data["session_history"] = sessions
                except (KeyError, TypeError):
                    pass

            # Patch states
            elif "describe-instance-patch-states" in cmd.get("command", ""):
                try:
                    states = d.get("InstancePatchStates", [])
                    data["patch_states"] = states
                except (KeyError, TypeError):
                    pass

            # Association status
            elif "describe-instance-associations-status" in cmd.get("command", ""):
                try:
                    # This returns a list under different keys depending on response
                    associations = d.get("InstanceAssociationStatusInfos", [d])
                    data["association_status"].extend(
                        a for a in associations if a
                    )
                except (KeyError, TypeError):
                    pass

        return data
