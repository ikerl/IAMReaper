"""AWS ECS enumeration module with all specified commands."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class ECSModule(BaseModule):
    """AWS ECS enumeration module."""

    MODULE_NAME = "ecs"
    DISPLAY_NAME = "AWS ECS Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.clusters: list[dict] = []
        self.task_definitions: list[dict] = []

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
        """Execute all ECS enumeration checks."""
        self.commands_executed = []
        self.clusters = []
        self.task_definitions = []

        # List clusters
        self._list_clusters()

        # List task definition families
        self._list_task_definition_families()

        # List task definitions
        self._list_task_definitions()

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
            "clusters": self.clusters,
            "task_definition_families": [],
            "task_definitions": self.task_definitions,
            "total_clusters": len(self.clusters),
            "total_task_definitions": len(self.task_definitions)
        }

        # Extract task definition families
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws ecs list-task-definition-families"):
                if cmd["success"] and cmd["data"]:
                    data["task_definition_families"] = cmd["data"].get("families", [])
                break

        return data

    # ==================== CLUSTERS ====================

    def _list_clusters(self) -> None:
        """List all ECS clusters."""
        cmd = "aws ecs list-clusters"
        result = self.executor.execute(cmd, "List all ECS clusters")
        self._add_result(result)

        # Store clusters for later enumeration
        if result.success and result.data:
            cluster_arns = result.data.get("clusterArns", [])
            if cluster_arns:
                # Extract cluster names from ARNs
                cluster_names = [arn.split("/")[-1] for arn in cluster_arns]
                self._describe_clusters(cluster_names)

    def _describe_clusters(self, cluster_names: list[str]) -> None:
        """Describe ECS clusters in detail."""
        if not cluster_names:
            return

        # Describe each cluster individually
        for cluster_name in cluster_names:
            cmd = f"aws ecs describe-clusters --clusters {cluster_name}"
            result = self.executor.execute(cmd, f"Describe ECS cluster: {cluster_name}")
            self._add_result(result)

            # Store cluster for later enumeration
            if result.success and result.data:
                cluster_details = result.data.get("clusters", [])
                for cluster in cluster_details:
                    cluster_name = cluster.get("clusterName")
                    if cluster_name:
                        self.clusters.append(cluster)
                        # Enumerate cluster resources
                        self._list_container_instances(cluster_name)
                        self._list_services(cluster_name)
                        self._list_tasks(cluster_name)

    # ==================== CONTAINER INSTANCES ====================

    def _list_container_instances(self, cluster_name: str) -> None:
        """List container instances in a cluster."""
        cmd = f"aws ecs list-container-instances --cluster {cluster_name}"
        result = self.executor.execute(
            cmd,
            f"List container instances in cluster: {cluster_name}"
        )
        self._add_result(result)

        # Describe container instances
        if result.success and result.data:
            container_instance_arns = result.data.get("containerInstanceArns", [])
            if container_instance_arns:
                self._describe_container_instances(cluster_name, container_instance_arns)

    def _describe_container_instances(self, cluster_name: str, container_instance_arns: list[str]) -> None:
        """Describe container instances in detail."""
        if not container_instance_arns:
            return

        # Describe in batches
        for i in range(0, len(container_instance_arns), 100):
            batch = container_instance_arns[i:i + 100]
            instances_arg = " ".join(batch)
            cmd = f"aws ecs describe-container-instances --cluster {cluster_name} --container-instances {instances_arg}"
            result = self.executor.execute(
                cmd,
                f"Describe container instances in cluster: {cluster_name}"
            )
            self._add_result(result)

    # ==================== SERVICES ====================

    def _list_services(self, cluster_name: str) -> None:
        """List services in a cluster."""
        cmd = f"aws ecs list-services --cluster {cluster_name}"
        result = self.executor.execute(
            cmd,
            f"List services in cluster: {cluster_name}"
        )
        self._add_result(result)

        # Describe services
        if result.success and result.data:
            service_arns = result.data.get("serviceArns", [])
            if service_arns:
                # Extract service names from ARNs
                service_names = [arn.split("/")[-1] for arn in service_arns]
                self._describe_services(cluster_name, service_names)

    def _describe_services(self, cluster_name: str, service_names: list[str]) -> None:
        """Describe services in detail."""
        if not service_names:
            return

        # Describe in batches (max 10 per call)
        for i in range(0, len(service_names), 10):
            batch = service_names[i:i + 10]
            services_arg = " ".join(batch)
            cmd = f"aws ecs describe-services --cluster {cluster_name} --services {services_arg}"
            result = self.executor.execute(
                cmd,
                f"Describe services in cluster: {cluster_name}"
            )
            self._add_result(result)

            # Get task sets for each service
            for service in batch:
                self._describe_task_sets(cluster_name, service)

    def _describe_task_sets(self, cluster_name: str, service_name: str) -> None:
        """Describe task sets for a service."""
        cmd = f"aws ecs describe-task-sets --cluster {cluster_name} --service {service_name}"
        result = self.executor.execute(
            cmd,
            f"Describe task sets for service: {service_name}"
        )
        self._add_result(result)

    # ==================== TASKS ====================

    def _list_tasks(self, cluster_name: str) -> None:
        """List tasks in a cluster."""
        cmd = f"aws ecs list-tasks --cluster {cluster_name}"
        result = self.executor.execute(
            cmd,
            f"List tasks in cluster: {cluster_name}"
        )
        self._add_result(result)

        # Describe tasks
        if result.success and result.data:
            task_arns = result.data.get("taskArns", [])
            if task_arns:
                # Extract task IDs from ARNs
                task_ids = [arn.split("/")[-1] for arn in task_arns]
                self._describe_tasks(cluster_name, task_ids)

    def _describe_tasks(self, cluster_name: str, task_ids: list[str]) -> None:
        """Describe tasks in detail."""
        if not task_ids:
            return

        # Describe in batches (max 100 per call)
        for i in range(0, len(task_ids), 100):
            batch = task_ids[i:i + 100]
            tasks_arg = " ".join(batch)
            cmd = f"aws ecs describe-tasks --cluster {cluster_name} --tasks {tasks_arg}"
            result = self.executor.execute(
                cmd,
                f"Describe tasks in cluster: {cluster_name}"
            )
            self._add_result(result)

    # ==================== TASK DEFINITIONS ====================

    def _list_task_definition_families(self) -> None:
        """List all task definition families."""
        cmd = "aws ecs list-task-definition-families"
        result = self.executor.execute(cmd, "List all ECS task definition families")
        self._add_result(result)

    def _list_task_definitions(self) -> None:
        """List all task definitions."""
        cmd = "aws ecs list-task-definitions"
        result = self.executor.execute(cmd, "List all ECS task definitions")
        self._add_result(result)

        # Store task definitions for later enumeration
        if result.success and result.data:
            task_definition_arns = result.data.get("taskDefinitionArns", [])
            for arn in task_definition_arns:
                # Extract family and version from ARN
                # arn:aws:ecs:region:account:task-definition/family:version
                parts = arn.split("/")
                if len(parts) >= 2:
                    family_version = parts[-1]
                    if ":" in family_version:
                        family, version = family_version.split(":")
                        self.task_definitions.append({
                            "arn": arn,
                            "family": family,
                            "version": version
                        })
                        # Get full task definition details
                        self._describe_task_definition(family, version)

    def _describe_task_definition(self, family: str, version: str) -> None:
        """Describe a task definition (look for env vars and secrets)."""
        cmd = f"aws ecs describe-task-definition --task-definition {family}:{version}"
        result = self.executor.execute(
            cmd,
            f"Describe task definition: {family}:{version}"
        )
        self._add_result(result)
