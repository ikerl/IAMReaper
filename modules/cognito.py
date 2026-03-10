"""AWS Cognito enumeration module for identity and user pool discovery."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class CognitoModule(BaseModule):
    """AWS Cognito enumeration module for identity pools and user pools."""

    MODULE_NAME = "cognito"
    DISPLAY_NAME = "AWS Cognito Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.identity_pools: list[dict] = []
        self.user_pools: list[dict] = []

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
        """Execute all Cognito enumeration checks."""
        self.commands_executed = []
        self.identity_pools = []
        self.user_pools = []

        # ========== Identity Pools (Cognito Identity) ==========
        # List all identity pools
        self._list_identity_pools()

        # For each identity pool, get details
        for pool in self.identity_pools:
            pool_id = pool.get("IdentityPoolId")
            if pool_id:
                # Describe identity pool
                self._describe_identity_pool(pool_id)
                
                # Get identity pool roles
                self._get_identity_pool_roles(pool_id)
                
                # List identities in the pool
                self._list_identities(pool_id)

        # ========== User Pools (Cognito IDP) ==========
        # List all user pools
        self._list_user_pools()

        # For each user pool, enumerate details
        for pool in self.user_pools:
            pool_id = pool.get("Id")
            if pool_id:
                # List users in the pool
                self._list_users(pool_id)
                
                # List groups in the pool
                self._list_groups(pool_id)
                
                # List app clients
                self._list_user_pool_clients(pool_id)
                
                # List identity providers
                self._list_identity_providers(pool_id)
                
                # Get MFA config
                self._get_user_pool_mfa_config(pool_id)
                
                # Get risk configuration
                self._describe_risk_configuration(pool_id)
                
                # List user import jobs
                self._list_user_import_jobs(pool_id)

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
            "identity_pools": [],
            "user_pools": [],
            "total_identity_pools": 0,
            "total_user_pools": 0
        }

        # Extract identity pools
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws cognito-identity list-identity-pools") and cmd["success"]:
                if cmd.get("data") and "IdentityPools" in cmd["data"]:
                    self.identity_pools = cmd["data"]["IdentityPools"]
                    data["identity_pools"] = self.identity_pools
                    data["total_identity_pools"] = len(self.identity_pools)

            elif cmd["command"].startswith("aws cognito-idp list-user-pools") and cmd["success"]:
                if cmd.get("data") and "UserPools" in cmd["data"]:
                    self.user_pools = cmd["data"]["UserPools"]
                    data["user_pools"] = self.user_pools
                    data["total_user_pools"] = len(self.user_pools)

        return data

    # ==================== Identity Pools (Cognito Identity) ====================

    def _list_identity_pools(self) -> None:
        """List all Cognito identity pools."""
        command = "aws cognito-identity list-identity-pools --max-results 60"
        description = "List all Cognito identity pools"
        result = self.executor.execute_aws(
            "cognito-identity",
            "list-identity-pools",
            description,
            MaxResults=60
        )
        self._add_result(result)

    def _describe_identity_pool(self, identity_pool_id: str) -> None:
        """Describe a specific identity pool."""
        command = f'aws cognito-identity describe-identity-pool --identity-pool-id "{identity_pool_id}"'
        description = f"Describe identity pool: {identity_pool_id}"
        result = self.executor.execute_aws(
            "cognito-identity",
            "describe-identity-pool",
            description,
            IdentityPoolId=identity_pool_id
        )
        self._add_result(result)

    def _get_identity_pool_roles(self, identity_pool_id: str) -> None:
        """Get roles for an identity pool."""
        command = f'aws cognito-identity get-identity-pool-roles --identity-pool-id "{identity_pool_id}"'
        description = f"Get identity pool roles: {identity_pool_id}"
        result = self.executor.execute_aws(
            "cognito-identity",
            "get-identity-pool-roles",
            description,
            IdentityPoolId=identity_pool_id
        )
        self._add_result(result)

    def _list_identities(self, identity_pool_id: str, max_results: int = 60) -> None:
        """List identities in an identity pool."""
        command = f'aws cognito-identity list-identities --identity-pool-id "{identity_pool_id}" --max-results {max_results}'
        description = f"List identities in pool: {identity_pool_id}"
        result = self.executor.execute_aws(
            "cognito-identity",
            "list-identities",
            description,
            IdentityPoolId=identity_pool_id,
            MaxResults=max_results
        )
        self._add_result(result)
        
        # If successful, try to get dataset info for each identity
        if result.success and result.data and "Identities" in result.data:
            for identity in result.data.get("Identities", []):
                identity_id = identity.get("IdentityId")
                if identity_id:
                    self._list_datasets(identity_pool_id, identity_id)

    # ==================== Cognito Sync (Datasets) ====================

    def _list_datasets(self, identity_pool_id: str, identity_id: str) -> None:
        """List datasets for an identity."""
        command = f'aws cognito-sync list-datasets --identity-pool-id "{identity_pool_id}" --identity-id "{identity_id}"'
        description = f"List datasets for identity: {identity_id}"
        result = self.executor.execute_aws(
            "cognito-sync",
            "list-datasets",
            description,
            IdentityPoolId=identity_pool_id,
            IdentityId=identity_id
        )
        self._add_result(result)
        
        # If successful, get details for each dataset
        if result.success and result.data and "Datasets" in result.data:
            for dataset in result.data.get("Datasets", []):
                dataset_name = dataset.get("DatasetName")
                if dataset_name:
                    self._describe_dataset(identity_pool_id, identity_id, dataset_name)
                    self._list_records(identity_pool_id, identity_id, dataset_name)

    def _describe_dataset(self, identity_pool_id: str, identity_id: str, dataset_name: str) -> None:
        """Describe a specific dataset."""
        command = f'aws cognito-sync describe-dataset --identity-pool-id "{identity_pool_id}" --identity-id "{identity_id}" --dataset-name "{dataset_name}"'
        description = f"Describe dataset: {dataset_name}"
        result = self.executor.execute_aws(
            "cognito-sync",
            "describe-dataset",
            description,
            IdentityPoolId=identity_pool_id,
            IdentityId=identity_id,
            DatasetName=dataset_name
        )
        self._add_result(result)

    def _list_records(self, identity_pool_id: str, identity_id: str, dataset_name: str) -> None:
        """List records in a dataset."""
        command = f'aws cognito-sync list-records --identity-pool-id "{identity_pool_id}" --identity-id "{identity_id}" --dataset-name "{dataset_name}"'
        description = f"List records in dataset: {dataset_name}"
        result = self.executor.execute_aws(
            "cognito-sync",
            "list-records",
            description,
            IdentityPoolId=identity_pool_id,
            IdentityId=identity_id,
            DatasetName=dataset_name
        )
        self._add_result(result)

    # ==================== User Pools (Cognito IDP) ====================

    def _list_user_pools(self) -> None:
        """List all Cognito user pools."""
        command = "aws cognito-idp list-user-pools --max-results 60"
        description = "List all Cognito user pools"
        result = self.executor.execute_aws(
            "cognito-idp",
            "list-user-pools",
            description,
            MaxResults=60
        )
        self._add_result(result)

    def _list_users(self, user_pool_id: str) -> None:
        """List users in a user pool."""
        command = f'aws cognito-idp list-users --user-pool-id "{user_pool_id}"'
        description = f"List users in user pool: {user_pool_id}"
        result = self.executor.execute_aws(
            "cognito-idp",
            "list-users",
            description,
            UserPoolId=user_pool_id
        )
        self._add_result(result)

    def _list_groups(self, user_pool_id: str) -> None:
        """List groups in a user pool."""
        command = f'aws cognito-idp list-groups --user-pool-id "{user_pool_id}"'
        description = f"List groups in user pool: {user_pool_id}"
        result = self.executor.execute_aws(
            "cognito-idp",
            "list-groups",
            description,
            UserPoolId=user_pool_id
        )
        self._add_result(result)
        
        # If successful, get users in each group
        if result.success and result.data and "Groups" in result.data:
            for group in result.data.get("Groups", []):
                group_name = group.get("GroupName")
                if group_name:
                    self._list_users_in_group(user_pool_id, group_name)

    def _list_users_in_group(self, user_pool_id: str, group_name: str) -> None:
        """List users in a specific group."""
        command = f'aws cognito-idp list-users-in-group --user-pool-id "{user_pool_id}" --group-name "{group_name}"'
        description = f"List users in group: {group_name}"
        result = self.executor.execute_aws(
            "cognito-idp",
            "list-users-in-group",
            description,
            UserPoolId=user_pool_id,
            GroupName=group_name
        )
        self._add_result(result)

    def _list_user_pool_clients(self, user_pool_id: str) -> None:
        """List app clients in a user pool."""
        command = f'aws cognito-idp list-user-pool-clients --user-pool-id "{user_pool_id}"'
        description = f"List user pool clients: {user_pool_id}"
        result = self.executor.execute_aws(
            "cognito-idp",
            "list-user-pool-clients",
            description,
            UserPoolId=user_pool_id
        )
        self._add_result(result)

    def _list_identity_providers(self, user_pool_id: str) -> None:
        """List identity providers configured for a user pool."""
        command = f'aws cognito-idp list-identity-providers --user-pool-id "{user_pool_id}"'
        description = f"List identity providers: {user_pool_id}"
        result = self.executor.execute_aws(
            "cognito-idp",
            "list-identity-providers",
            description,
            UserPoolId=user_pool_id
        )
        self._add_result(result)

    def _list_user_import_jobs(self, user_pool_id: str) -> None:
        """List user import jobs for a user pool."""
        command = f'aws cognito-idp list-user-import-jobs --user-pool-id "{user_pool_id}" --max-results 60'
        description = f"List user import jobs: {user_pool_id}"
        result = self.executor.execute_aws(
            "cognito-idp",
            "list-user-import-jobs",
            description,
            UserPoolId=user_pool_id,
            MaxResults=60
        )
        self._add_result(result)

    def _get_user_pool_mfa_config(self, user_pool_id: str) -> None:
        """Get MFA configuration for a user pool."""
        command = f'aws cognito-idp get-user-pool-mfa-config --user-pool-id "{user_pool_id}"'
        description = f"Get user pool MFA config: {user_pool_id}"
        result = self.executor.execute_aws(
            "cognito-idp",
            "get-user-pool-mfa-config",
            description,
            UserPoolId=user_pool_id
        )
        self._add_result(result)

    def _describe_risk_configuration(self, user_pool_id: str) -> None:
        """Get risk configuration for a user pool."""
        command = f'aws cognito-idp describe-risk-configuration --user-pool-id "{user_pool_id}"'
        description = f"Get risk configuration: {user_pool_id}"
        result = self.executor.execute_aws(
            "cognito-idp",
            "describe-risk-configuration",
            description,
            UserPoolId=user_pool_id
        )
        self._add_result(result)
