"""AWS Secrets Manager enumeration module."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class SecretsManagerModule(BaseModule):
    """AWS Secrets Manager enumeration module."""

    MODULE_NAME = "secretsmanager"
    DISPLAY_NAME = "AWS Secrets Manager Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.secrets_data: dict[str, Any] = {
            "secrets": [],
            "secret_details": [],
            "secret_versions": {},
            "resource_policies": {}
        }

    def _build_cmd(self, service: str, operation: str, **kwargs) -> str:
        """Build AWS CLI command with profile and region."""
        return self.executor.build_aws_command(service, operation, **kwargs)

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
        """Execute all Secrets Manager enumeration checks."""
        self.commands_executed = []
        self.secrets_data = {
            "secrets": [],
            "secret_details": [],
            "secret_versions": {},
            "resource_policies": {}
        }

        # List all secrets
        self._list_secrets()

        # Get details and values for each secret
        secrets = self.secrets_data.get("secrets", [])
        for secret in secrets:
            secret_name = secret.get("Name", "")
            if secret_name:
                # Get secret metadata
                self._describe_secret(secret_name)
                
                # Get secret value
                self._get_secret_value(secret_name)
                
                # Get secret versions
                self._list_secret_version_ids(secret_name)
                
                # Get resource policy
                self._get_resource_policy(secret_name)

        # Generate summary
        summary = self._summarize_commands(self.commands_executed)

        return {
            "module": self.MODULE_NAME,
            "display_name": self.DISPLAY_NAME,
            "executed_at": datetime.utcnow().isoformat() + "Z",
            "commands_executed": self.commands_executed,
            "summary": summary,
            "data": self.secrets_data
        }

    def _list_secrets(self) -> None:
        """List all secrets in the account."""
        cmd = self._build_cmd("secretsmanager", "list-secrets")
        
        result = self.executor.execute_aws(
            service="secretsmanager",
            operation="list-secrets",
            description="List all secrets"
        )
        
        self._add_result(result)
        
        if result.success and result.data:
            secrets_list = result.data.get("SecretList", [])
            self.secrets_data["secrets"] = secrets_list
            self.secrets_data["total_secrets"] = len(secrets_list)

    def _describe_secret(self, secret_name: str) -> None:
        """Get metadata for a specific secret."""
        result = self.executor.execute_aws(
            service="secretsmanager",
            operation="describe-secret",
            description=f"Describe secret: {secret_name}",
            secret_id=secret_name
        )
        
        self._add_result(result)
        
        if result.success and result.data:
            self.secrets_data["secret_details"].append({
                "name": secret_name,
                "details": result.data
            })

    def _get_secret_value(self, secret_name: str, version_id: str = None) -> None:
        """Get secret value."""
        kwargs = {"secret_id": secret_name}
        if version_id:
            kwargs["version_id"] = version_id
            desc = f"Get secret value: {secret_name} (version: {version_id})"
        else:
            desc = f"Get secret value: {secret_name}"
        
        result = self.executor.execute_aws(
            service="secretsmanager",
            operation="get-secret-value",
            description=desc,
            **kwargs
        )
        
        self._add_result(result)
        
        # Note: We don't store the actual secret value in results for security
        # Just mark that we successfully retrieved it

    def _list_secret_version_ids(self, secret_name: str) -> None:
        """List all version IDs for a secret."""
        result = self.executor.execute_aws(
            service="secretsmanager",
            operation="list-secret-version-ids",
            description=f"List secret versions: {secret_name}",
            secret_id=secret_name
        )
        
        self._add_result(result)
        
        if result.success and result.data:
            versions = result.data.get("Versions", [])
            self.secrets_data["secret_versions"][secret_name] = versions
            
            # Also get values for each version (except AWSCURRENT and AWSPREVIOUS)
            for version in versions:
                version_id = version.get("VersionId", "")
                # Only get value if it's not the current or previous stage
                # to avoid retrieving too many values
                if version_id and "AWSCURRENT" not in str(version.get("VersionStages", [])):
                    self._get_secret_value(secret_name, version_id)

    def _get_resource_policy(self, secret_name: str) -> None:
        """Get resource policy for a secret."""
        result = self.executor.execute_aws(
            service="secretsmanager",
            operation="get-resource-policy",
            description=f"Get resource policy: {secret_name}",
            secret_id=secret_name
        )
        
        self._add_result(result)
        
        if result.success and result.data:
            policy = result.data.get("ResourcePolicy", "")
            if policy:
                try:
                    policy_json = json.loads(policy)
                    self.secrets_data["resource_policies"][secret_name] = policy_json
                except json.JSONDecodeError:
                    self.secrets_data["resource_policies"][secret_name] = policy
