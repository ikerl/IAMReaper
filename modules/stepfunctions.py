"""AWS Step Functions enumeration module for state machine discovery and security assessment."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class StepFunctionsModule(BaseModule):
    """AWS Step Functions enumeration module for state machine discovery and security assessment."""

    MODULE_NAME = "stepfunctions"
    DISPLAY_NAME = "AWS Step Functions Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.state_machines: list[dict] = []
        self.activities: list[dict] = []

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
        """Execute all Step Functions enumeration checks."""
        self.commands_executed = []
        self.state_machines = []
        self.activities = []

        # List state machines
        self._list_state_machines()

        # Get details for each state machine
        for sm in self.state_machines:
            state_machine_arn = sm.get("stateMachineArn", "")
            if state_machine_arn:
                self._describe_state_machine(state_machine_arn)
                self._list_state_machine_versions(state_machine_arn)
                self._list_tags_for_resource(state_machine_arn)
                self._list_executions(state_machine_arn)

        # List all state machine aliases (no ARN filter - lists all aliases in account)
        self._list_state_machine_aliases()

        # List activities
        self._list_activities()

        # Get details for each activity
        for activity in self.activities:
            activity_arn = activity.get("activityArn", "")
            if activity_arn:
                self._describe_activity(activity_arn)

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
            "state_machines": self.state_machines,
            "total_state_machines": len(self.state_machines),
            "activities": self.activities,
            "total_activities": len(self.activities)
        }

        return data

    # ==================== State Machines ====================

    def _list_state_machines(self) -> None:
        """List all Step Functions state machines."""
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="list-state-machines",
            description="List all Step Functions state machines"
        )

        self._add_result(result)

        if result.success and result.data:
            state_machines = result.data.get("stateMachines", [])
            for sm in state_machines:
                self.state_machines.append({
                    "stateMachineArn": sm.get("stateMachineArn", ""),
                    "name": sm.get("name", ""),
                    "type": sm.get("type", ""),
                    "creationDate": str(sm.get("creationDate", ""))
                })

    def _describe_state_machine(self, state_machine_arn: str) -> None:
        """Retrieve information about the specified state machine."""
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="describe-state-machine",
            description=f"Describe state machine {state_machine_arn}",
            state_machine_arn=state_machine_arn
        )

        self._add_result(result)

    def _list_state_machine_versions(self, state_machine_arn: str) -> None:
        """List versions for the specified state machine."""
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="list-state-machine-versions",
            description=f"List state machine versions for {state_machine_arn}",
            state_machine_arn=state_machine_arn
        )

        self._add_result(result)

    def _list_state_machine_aliases(self, state_machine_arn: str = None) -> None:
        """List aliases for the specified state machine."""
        kwargs = {}
        if state_machine_arn:
            kwargs["state_machine_arn"] = state_machine_arn
        
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="list-state-machine-aliases",
            description=f"List state machine aliases",
            **kwargs
        )

        self._add_result(result)

    def _describe_state_machine_alias(self, state_machine_alias_arn: str) -> None:
        """Retrieve information about the specified state machine alias."""
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="describe-state-machine-alias",
            description=f"Describe state machine alias {state_machine_alias_arn}",
            state_machine_alias_arn=state_machine_alias_arn
        )

        self._add_result(result)

    def _list_executions(self, state_machine_arn: str, status_filter: str = None) -> None:
        """List executions of a state machine."""
        kwargs = {
            "state_machine_arn": state_machine_arn
        }
        
        if status_filter:
            kwargs["status_filter"] = status_filter

        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="list-executions",
            description=f"List executions for state machine {state_machine_arn}",
            **kwargs
        )

        self._add_result(result)

        # If executions found, get details for each
        if result.success and result.data:
            executions = result.data.get("executions", [])
            for execution in executions:
                execution_arn = execution.get("executionArn", "")
                if execution_arn:
                    # Get state machine for execution
                    self._describe_state_machine_for_execution(execution_arn)
                    # Get execution details
                    self._describe_execution(execution_arn)
                    # Get execution history
                    self._get_execution_history(execution_arn)
                    # List map runs
                    self._list_map_runs(execution_arn)

    def _describe_execution(self, execution_arn: str) -> None:
        """Retrieve information about a state machine execution."""
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="describe-execution",
            description=f"Describe execution {execution_arn}",
            execution_arn=execution_arn
        )

        self._add_result(result)

    def _describe_state_machine_for_execution(self, execution_arn: str) -> None:
        """Retrieve information about the state machine associated with the specified execution."""
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="describe-state-machine-for-execution",
            description=f"Describe state machine for execution {execution_arn}",
            execution_arn=execution_arn
        )

        self._add_result(result)

    def _get_execution_history(self, execution_arn: str, reverse_order: bool = True, include_execution_data: bool = False) -> None:
        """Retrieve the history of the specified execution as a list of events."""
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="get-execution-history",
            description=f"Get execution history for {execution_arn}",
            execution_arn=execution_arn,
            reverse_order=reverse_order,
            include_execution_data=include_execution_data
        )

        self._add_result(result)

    def _list_tags_for_resource(self, resource_arn: str) -> None:
        """List tags for the specified Step Functions resource."""
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="list-tags-for-resource",
            description=f"List tags for resource {resource_arn}",
            resource_arn=resource_arn
        )

        self._add_result(result)

    # ==================== Activities ====================

    def _list_activities(self) -> None:
        """List existing activities."""
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="list-activities",
            description="List all Step Functions activities"
        )

        self._add_result(result)

        if result.success and result.data:
            activities = result.data.get("activities", [])
            for activity in activities:
                self.activities.append({
                    "activityArn": activity.get("activityArn", ""),
                    "name": activity.get("name", ""),
                    "creationDate": str(activity.get("creationDate", ""))
                })

    def _describe_activity(self, activity_arn: str) -> None:
        """Retrieve information about the specified activity."""
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="describe-activity",
            description=f"Describe activity {activity_arn}",
            activity_arn=activity_arn
        )

        self._add_result(result)

    # ==================== Map Runs ====================

    def _list_map_runs(self, execution_arn: str) -> None:
        """List map runs of an execution."""
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="list-map-runs",
            description=f"List map runs for execution {execution_arn}",
            execution_arn=execution_arn
        )

        self._add_result(result)

        # If map runs found, get details for each
        if result.success and result.data:
            map_runs = result.data.get("mapRuns", [])
            for map_run in map_runs:
                map_run_arn = map_run.get("mapRunArn", "")
                if map_run_arn:
                    self._describe_map_run(map_run_arn)

    def _describe_map_run(self, map_run_arn: str) -> None:
        """Provide information about the configuration, progress and results of a Map Run."""
        result = self.executor.execute_aws(
            service="stepfunctions",
            operation="describe-map-run",
            description=f"Describe map run {map_run_arn}",
            map_run_arn=map_run_arn
        )

        self._add_result(result)
