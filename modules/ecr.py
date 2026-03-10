"""AWS ECR (Elastic Container Registry) enumeration module."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class ECRModule(BaseModule):
    """AWS ECR enumeration module for container registry discovery and security assessment."""

    MODULE_NAME = "ecr"
    DISPLAY_NAME = "AWS ECR Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.repositories: list[dict] = []

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
        """Execute all ECR enumeration checks."""
        self.commands_executed = []
        self.repositories = []

        # Get registry information
        self._describe_registry()

        # List all ECR repositories
        self._describe_repositories()

        # Get registry policy
        self._get_registry_policy()

        # Get public ECR repositories (if available)
        self._describe_public_repositories()

        # For each repository, enumerate details
        for repo in self.repositories:
            repo_name = repo.get("repositoryName")
            if repo_name:
                # Get repository policy
                self._get_repository_policy(repo_name)

                # List images in repository
                self._list_images(repo_name)

                # Describe images in repository
                self._describe_images(repo_name)

                # Get image replication status for first image if available
                image_details = self._get_first_image_digest(repo_name)
                if image_details:
                    # Get image replication status
                    self._describe_image_replication_status(repo_name, image_details)
                    
                    # Get image scan findings
                    self._describe_image_scan_findings(repo_name, image_details)

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

    def _describe_registry(self) -> dict:
        """Get ECR registry information."""
        cmd = "aws ecr describe-registry"
        result = self.executor.execute(cmd, "Get ECR registry information (aws ecr describe-registry)")
        self._add_result(result)
        return result

    def _describe_repositories(self) -> dict:
        """List all ECR repositories."""
        cmd = "aws ecr describe-repositories"
        result = self.executor.execute(cmd, "List all ECR repositories (aws ecr describe-repositories)")
        self._add_result(result)

        # Parse repositories
        if result.success and result.data:
            self.repositories = result.data.get("repositories", [])

        return result

    def _get_registry_policy(self) -> dict:
        """Get registry policy."""
        cmd = "aws ecr get-registry-policy"
        result = self.executor.execute(cmd, "Get ECR registry policy (aws ecr get-registry-policy)")
        self._add_result(result)
        return result

    def _describe_public_repositories(self) -> dict:
        """List public ECR repositories (ECR Public)."""
        cmd = "aws ecr-public describe-repositories"
        result = self.executor.execute(cmd, "List public ECR repositories (aws ecr-public describe-repositories)")
        self._add_result(result)
        return result

    def _get_repository_policy(self, repository_name: str) -> dict:
        """Get repository policy."""
        cmd = f"aws ecr get-repository-policy --repository-name {repository_name}"
        result = self.executor.execute(cmd, f"Get repository policy: {repository_name}")
        self._add_result(result)
        return result

    def _list_images(self, repository_name: str) -> dict:
        """List images in repository."""
        cmd = f"aws ecr list-images --repository-name {repository_name}"
        result = self.executor.execute(cmd, f"List images in repository: {repository_name}")
        self._add_result(result)
        return result

    def _describe_images(self, repository_name: str) -> dict:
        """Describe images in repository."""
        cmd = f"aws ecr describe-images --repository-name {repository_name}"
        result = self.executor.execute(cmd, f"Describe images in repository: {repository_name}")
        self._add_result(result)
        return result

    def _get_first_image_digest(self, repository_name: str) -> str:
        """Get the image digest of the first image in the repository."""
        cmd = f"aws ecr list-images --repository-name {repository_name}"
        result = self.executor.execute(cmd, f"List images in repository: {repository_name}")
        if result.success and result.data:
            image_ids = result.data.get("imageIds", [])
            if image_ids:
                # Return the first imageDigest if available
                for img in image_ids:
                    if "imageDigest" in img:
                        return img["imageDigest"]
        return None

    def _describe_image_replication_status(self, repository_name: str, image_digest: str) -> dict:
        """Describe image replication status."""
        cmd = f"aws ecr describe-image-replication-status --repository-name {repository_name} --image-id imageDigest={image_digest}"
        result = self.executor.execute(cmd, f"Get image replication status: {repository_name}")
        self._add_result(result)
        return result

    def _describe_image_scan_findings(self, repository_name: str, image_digest: str) -> dict:
        """Describe image scan findings."""
        cmd = f"aws ecr describe-image-scan-findings --repository-name {repository_name} --image-id imageDigest={image_digest}"
        result = self.executor.execute(cmd, f"Get image scan findings: {repository_name}")
        self._add_result(result)
        return result

    def _describe_pull_through_cache_rules(self, repository_name: str = None) -> dict:
        """Describe pull-through cache rules."""
        if repository_name:
            cmd = f"aws ecr describe-pull-through-cache-rules --repository-name {repository_name}"
        else:
            cmd = "aws ecr describe-pull-through-cache-rules"
        result = self.executor.execute(cmd, "Get pull-through cache rules")
        self._add_result(result)
        return result

    def _extract_data(self) -> dict[str, Any]:
        """Extract structured data from command results."""
        data = {
            "repositories": [],
            "total_repositories": 0,
            "public_repositories": [],
            "repositories_with_policy": [],
            "repositories_with_lifecycle": [],
            "registry": None,
            "registry_policy": None,
            "public_repositories_list": []
        }

        # Extract registry information
        for cmd_result in self.commands_executed:
            cmd = cmd_result.get("command", "")
            result_data = cmd_result.get("data")
            success = cmd_result.get("success", False)

            if not result_data or isinstance(result_data, str):
                continue

            # Registry info
            if "describe-registry" in cmd:
                data["registry"] = result_data

            # Registry policy
            elif "get-registry-policy" in cmd and "policyText" in result_data:
                data["registry_policy"] = result_data

            # Public repositories
            elif "ecr-public describe-repositories" in cmd:
                public_repos = result_data.get("repositories", [])
                data["public_repositories_list"] = public_repos
                for pub_repo in public_repos:
                    data["public_repositories"].append(pub_repo.get("repositoryName"))

            # Repository-specific data
            repo_name = None
            if "--repository-name" in cmd:
                parts = cmd.split("--repository-name")
                if len(parts) > 1:
                    repo_name = parts[-1].strip().split()[0]

            if not repo_name:
                continue

            # Repository policy
            if "get-repository-policy" in cmd and "policyText" in result_data:
                if repo_name not in data["repositories_with_policy"]:
                    data["repositories_with_policy"].append(repo_name)

            # Lifecycle policy
            elif "get-repository-lifecycle-policy" in cmd and "lifecyclePolicyText" in result_data:
                if repo_name not in data["repositories_with_lifecycle"]:
                    data["repositories_with_lifecycle"].append(repo_name)

        # Extract repository information from describe-repositories
        for cmd_result in self.commands_executed:
            cmd = cmd_result.get("command", "")
            result_data = cmd_result.get("data")
            success = cmd_result.get("success", False)

            if not result_data or isinstance(result_data, str):
                continue

            if "describe-repositories" in cmd and "repositories" in result_data:
                for repo in result_data.get("repositories", []):
                    repo_name = repo.get("repositoryName")
                    if repo_name:
                        data["repositories"].append({
                            "name": repo_name,
                            "arn": repo.get("repositoryArn"),
                            "uri": repo.get("repositoryUri"),
                            "created_at": repo.get("createdAt"),
                            "image_tag_mutability": repo.get("imageTagMutability"),
                            "image_scanning_configuration": repo.get("imageScanningConfiguration"),
                            "encryption_configuration": repo.get("encryptionConfiguration")
                        })

        data["total_repositories"] = len(data["repositories"])

        return data
