"""AWS EventBridge Scheduler enumeration module for schedule and schedule group discovery."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class EventBridgeSchedulerModule(BaseModule):
    """AWS EventBridge Scheduler enumeration module for schedule and schedule group discovery."""

    MODULE_NAME = "eventbridge"
    DISPLAY_NAME = "AWS EventBridge Scheduler Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.schedules: list[dict] = []
        self.schedule_groups: list[dict] = []

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
        """Execute all EventBridge Scheduler enumeration checks."""
        self.commands_executed = []
        self.schedules = []
        self.schedule_groups = []

        # List all EventBridge Scheduler schedule groups
        self._list_schedule_groups()

        # List all EventBridge Scheduler schedules
        self._list_schedules()

        # For each schedule, get detailed information
        for schedule in self.schedules:
            schedule_name = schedule.get("Name")
            if schedule_name:
                self._get_schedule(schedule_name)

        # For each schedule group, get detailed information
        for group in self.schedule_groups:
            group_name = group.get("Name")
            if group_name:
                self._get_schedule_group(group_name)
                # List tags for the schedule group
                self._list_tags_for_resource(group.get("Arn"))

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
        """Extract enumerated data from commands executed."""
        data = {
            "schedules": self.schedules,
            "schedule_groups": self.schedule_groups,
            "total_schedules": len(self.schedules),
            "total_schedule_groups": len(self.schedule_groups)
        }

        return data

    def _list_schedules(self) -> None:
        """List all EventBridge Scheduler schedules."""
        result = self.executor.execute_aws(
            service="scheduler",
            operation="list-schedules",
            description="List all EventBridge Scheduler schedules"
        )

        self._add_result(result)

        if result.success and result.data:
            schedules = result.data.get("Schedules", [])
            for schedule in schedules:
                self.schedules.append(schedule)

    def _list_schedule_groups(self) -> None:
        """List all EventBridge Scheduler schedule groups."""
        result = self.executor.execute_aws(
            service="scheduler",
            operation="list-schedule-groups",
            description="List all EventBridge Scheduler schedule groups"
        )

        self._add_result(result)

        if result.success and result.data:
            groups = result.data.get("ScheduleGroups", [])
            for group in groups:
                self.schedule_groups.append(group)

    def _get_schedule(self, schedule_name: str) -> None:
        """Describe a specific schedule to retrieve more details."""
        result = self.executor.execute_aws(
            service="scheduler",
            operation="get-schedule",
            description=f"Get schedule details for {schedule_name}",
            name=schedule_name
        )

        self._add_result(result)

        # Update the schedule entry with full details if successful
        if result.success and result.data:
            for schedule in self.schedules:
                if schedule.get("Name") == schedule_name:
                    schedule.update(result.data)
                    break

    def _get_schedule_group(self, group_name: str) -> None:
        """Describe a specific schedule group."""
        result = self.executor.execute_aws(
            service="scheduler",
            operation="get-schedule-group",
            description=f"Get schedule group details for {group_name}",
            name=group_name
        )

        self._add_result(result)

        # Update the schedule group entry with full details if successful
        if result.success and result.data:
            for group in self.schedule_groups:
                if group.get("Name") == group_name:
                    group.update(result.data)
                    break

    def _list_tags_for_resource(self, resource_arn: str) -> None:
        """List tags for a specific schedule or schedule group."""
        if not resource_arn:
            return
            
        result = self.executor.execute_aws(
            service="scheduler",
            operation="list-tags-for-resource",
            description=f"List tags for resource {resource_arn}",
            resource_arn=resource_arn
        )

        self._add_result(result)

    def get_module_info(self) -> dict[str, str]:
        """Get module metadata."""
        return {
            "name": self.MODULE_NAME,
            "display_name": self.DISPLAY_NAME,
            "description": "Enumerate EventBridge Scheduler schedules and schedule groups"
        }
