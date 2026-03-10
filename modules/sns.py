"""AWS SNS (Simple Notification Service) enumeration module for topic and subscription discovery."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class SNSModule(BaseModule):
    """AWS SNS enumeration module for topic and subscription discovery."""

    MODULE_NAME = "sns"
    DISPLAY_NAME = "AWS SNS Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.topics: list[dict] = []
        self.subscriptions: list[dict] = []

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
        """Execute all SNS enumeration checks."""
        self.commands_executed = []
        self.topics = []
        self.subscriptions = []

        # List all SNS topics
        self._list_topics()

        # List all subscriptions
        self._list_subscriptions()

        # For each topic, get subscriptions by topic
        for topic in self.topics:
            topic_arn = topic.get("TopicArn", "")
            if topic_arn:
                self._list_subscriptions_by_topic(topic_arn)
                self._get_data_protection_policy(topic_arn)

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
            "topics": self.topics,
            "subscriptions": self.subscriptions,
            "total_topics": len(self.topics),
            "total_subscriptions": len(self.subscriptions)
        }

        return data

    def _list_topics(self) -> None:
        """List all SNS topics."""
        result = self.executor.execute_aws(
            service="sns",
            operation="list-topics",
            description="List all SNS topics"
        )

        self._add_result(result)

        if result.success and result.data:
            topics = result.data.get("Topics", [])
            for topic in topics:
                self.topics.append(topic)

    def _list_subscriptions(self) -> None:
        """List all SNS subscriptions."""
        result = self.executor.execute_aws(
            service="sns",
            operation="list-subscriptions",
            description="List all SNS subscriptions"
        )

        self._add_result(result)

        if result.success and result.data:
            subscriptions = result.data.get("Subscriptions", [])
            for subscription in subscriptions:
                self.subscriptions.append(subscription)

    def _list_subscriptions_by_topic(self, topic_arn: str) -> None:
        """List subscriptions for a specific topic."""
        result = self.executor.execute_aws(
            service="sns",
            operation="list-subscriptions-by-topic",
            description=f"List subscriptions for topic {topic_arn}",
            topic_arn=topic_arn
        )

        self._add_result(result)

        # Update the topic entry with subscriptions if successful
        if result.success and result.data:
            subscriptions = result.data.get("Subscriptions", [])
            for topic in self.topics:
                if topic.get("TopicArn") == topic_arn:
                    topic["Subscriptions"] = subscriptions
                    break

    def _get_data_protection_policy(self, topic_arn: str) -> None:
        """Get data protection policy for a specific topic."""
        result = self.executor.execute_aws(
            service="sns",
            operation="get-data-protection-policy",
            description=f"Get data protection policy for topic {topic_arn}",
            resource_arn=topic_arn
        )

        self._add_result(result)

        # Update the topic entry with data protection policy if successful
        if result.success and result.data:
            for topic in self.topics:
                if topic.get("TopicArn") == topic_arn:
                    topic["DataProtectionPolicy"] = result.data
                    break

    def get_module_info(self) -> dict[str, str]:
        """Get module metadata."""
        return {
            "name": self.MODULE_NAME,
            "display_name": self.DISPLAY_NAME,
            "description": "Enumerate SNS topics and subscriptions"
        }
