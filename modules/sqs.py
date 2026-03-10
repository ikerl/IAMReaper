"""AWS SQS (Simple Queue Service) enumeration module for queue discovery and security assessment."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class SQSModule(BaseModule):
    """AWS SQS enumeration module for queue discovery and security assessment."""

    MODULE_NAME = "sqs"
    DISPLAY_NAME = "AWS SQS Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.queues: list[dict] = []

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
        """Execute all SQS enumeration checks."""
        self.commands_executed = []
        self.queues = []

        # List all SQS queues
        self._list_queues()

        # For each queue, get detailed attributes
        for queue in self.queues:
            queue_url = queue.get("QueueUrl", "")
            if queue_url:
                self._get_queue_attributes(queue_url)

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
            "queues": self.queues,
            "total_queues": len(self.queues)
        }

        return data

    def _list_queues(self) -> None:
        """List all SQS queues."""
        result = self.executor.execute_aws(
            service="sqs",
            operation="list-queues",
            description="List all SQS queues"
        )

        self._add_result(result)

        if result.success and result.data:
            # Handle both old and new AWS CLI output formats
            queue_urls = result.data.get("QueueUrls", []) or result.data.get("QueueURLs", [])
            for queue_url in queue_urls:
                # Extract queue name from URL
                queue_name = queue_url.split("/")[-1] if "/" in queue_url else queue_url
                self.queues.append({
                    "QueueUrl": queue_url,
                    "QueueName": queue_name
                })

    def _get_queue_attributes(self, queue_url: str) -> None:
        """Get queue attributes for a specific queue."""
        result = self.executor.execute_aws(
            service="sqs",
            operation="get-queue-attributes",
            description=f"Get queue attributes for {queue_url}",
            queue_url=queue_url,
            attribute_names=["All"]
        )

        self._add_result(result)

        # Update the queue entry with attributes if successful
        if result.success and result.data:
            for queue in self.queues:
                if queue.get("QueueUrl") == queue_url:
                    queue["Attributes"] = result.data.get("Attributes", {})
                    break

    def get_module_info(self) -> dict[str, str]:
        """Get module metadata."""
        return {
            "name": self.MODULE_NAME,
            "display_name": self.DISPLAY_NAME,
            "description": "Enumerate SQS queues and their attributes"
        }
