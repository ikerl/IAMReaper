"""AWS DynamoDB enumeration module for table discovery and security assessment."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class DynamoDBModule(BaseModule):
    """AWS DynamoDB enumeration module for table discovery and security assessment."""

    MODULE_NAME = "dynamodb"
    DISPLAY_NAME = "AWS DynamoDB Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.tables: list[str] = []

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
        """Execute all DynamoDB enumeration checks."""
        self.commands_executed = []
        self.tables = []

        # List all DynamoDB tables
        self._list_tables()

        # Describe endpoints
        self._describe_endpoints()

        # List backups
        self._list_backups()

        # List global tables
        self._list_global_tables()

        # List exports
        self._list_exports()

        # For each table, enumerate details
        for table_name in self.tables:
            # Get table metadata
            self._describe_table(table_name)

            # Check if point in time recovery is enabled
            self._describe_continuous_backups(table_name)

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
            "tables": self.tables,
            "backups": [],
            "global_tables": [],
            "exports": [],
            "endpoints": {}
        }

        # Extract table information
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws dynamodb list-tables") and cmd["success"]:
                if cmd.get("data") and "TableNames" in cmd["data"]:
                    self.tables = cmd["data"]["TableNames"]

            elif cmd["command"].startswith("aws dynamodb describe-endpoints") and cmd["success"]:
                if cmd.get("data"):
                    data["endpoints"] = cmd["data"]

            elif cmd["command"].startswith("aws dynamodb list-backups") and cmd["success"]:
                if cmd.get("data") and "BackupSummaries" in cmd["data"]:
                    data["backups"] = cmd["data"]["BackupSummaries"]

            elif cmd["command"].startswith("aws dynamodb list-global-tables") and cmd["success"]:
                if cmd.get("data") and "GlobalTables" in cmd["data"]:
                    data["global_tables"] = cmd["data"]["GlobalTables"]

            elif cmd["command"].startswith("aws dynamodb list-exports") and cmd["success"]:
                if cmd.get("data") and "ExportSummaries" in cmd["data"]:
                    data["exports"] = cmd["data"]["ExportSummaries"]

        return data

    def _list_tables(self) -> None:
        """List all DynamoDB tables."""
        result = self.executor.execute_aws(
            "dynamodb",
            "list-tables",
            "List all DynamoDB tables"
        )
        self._add_result(result)

        # Store tables for further enumeration
        if result.success and result.data and "TableNames" in result.data:
            self.tables = result.data["TableNames"]

    def _describe_table(self, table_name: str) -> None:
        """Get metadata information for a specific table."""
        result = self.executor.execute_aws(
            "dynamodb",
            "describe-table",
            f"Describe table: {table_name}",
            table_name=table_name
        )
        self._add_result(result)

    def _describe_continuous_backups(self, table_name: str) -> None:
        """Check if point in time recovery is enabled for a table."""
        result = self.executor.execute_aws(
            "dynamodb",
            "describe-continuous-backups",
            f"Describe continuous backups for table: {table_name}",
            table_name=table_name
        )
        self._add_result(result)

    def _list_backups(self) -> None:
        """List all DynamoDB backups."""
        result = self.executor.execute_aws(
            "dynamodb",
            "list-backups",
            "List all DynamoDB backups"
        )
        self._add_result(result)

    def _describe_backup(self, backup_arn: str) -> None:
        """Describe a specific backup."""
        result = self.executor.execute_aws(
            "dynamodb",
            "describe-backup",
            f"Describe backup: {backup_arn}",
            backup_arn=backup_arn
        )
        self._add_result(result)

    def _list_global_tables(self) -> None:
        """List all DynamoDB global tables."""
        result = self.executor.execute_aws(
            "dynamodb",
            "list-global-tables",
            "List all DynamoDB global tables"
        )
        self._add_result(result)

    def _describe_global_table(self, global_table_name: str) -> None:
        """Describe a specific global table."""
        result = self.executor.execute_aws(
            "dynamodb",
            "describe-global-table",
            f"Describe global table: {global_table_name}",
            global_table_name=global_table_name
        )
        self._add_result(result)

    def _list_exports(self) -> None:
        """List all DynamoDB exports."""
        result = self.executor.execute_aws(
            "dynamodb",
            "list-exports",
            "List all DynamoDB exports"
        )
        self._add_result(result)

    def _describe_export(self, export_arn: str) -> None:
        """Describe a specific export."""
        result = self.executor.execute_aws(
            "dynamodb",
            "describe-export",
            f"Describe export: {export_arn}",
            export_arn=export_arn
        )
        self._add_result(result)

    def _describe_endpoints(self) -> None:
        """Describe DynamoDB endpoints."""
        result = self.executor.execute_aws(
            "dynamodb",
            "describe-endpoints",
            "Describe DynamoDB endpoints"
        )
        self._add_result(result)
