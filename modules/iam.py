"""AWS IAM enumeration module with all specified commands."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class IAMModule(BaseModule):
    """Comprehensive IAM enumeration module."""

    MODULE_NAME = "iam"
    DISPLAY_NAME = "AWS IAM Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []

    def _build_cmd(self, service: str, operation: str, **kwargs) -> str:
        """Build AWS CLI command with profile and region."""
        return self.executor.build_aws_command(service, operation, **kwargs)

    def _add_profile(self, cmd: str) -> str:
        """Add profile to command if set."""
        if self.executor.profile_name:
            return f"{cmd} --profile {self.executor.profile_name}"
        return cmd

    def _add_result(self, result: CommandResult) -> None:
        """Add a command result to the executed commands list."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Debug: log if this is a policy version command
        if 'get-policy-version' in result.command:
            logger.info(f"DEBUG: Adding get-policy-version command: {result.command}")
        
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
        """Execute all IAM enumeration checks."""
        self.commands_executed = []

        # Get caller identity (current user info)
        self._get_caller_identity()

        # Get account authorization details (comprehensive snapshot)
        self._get_account_authorization_details()

        # List users
        self._list_users()

        # List groups
        self._list_groups()

        # List roles
        self._list_roles()

        # List policies
        self._list_policies()

        # Enumerate providers
        self._list_saml_providers()
        self._list_open_id_connect_providers()

        # Password policy and MFA
        self._get_account_password_policy()
        self._list_mfa_devices()
        
        # List instance profiles
        self._list_instance_profiles()

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

    def _get_account_authorization_details(self) -> dict:
        """Get comprehensive IAM authorization details."""
        cmd = self._build_cmd("iam", "get-account-authorization-details")
        result = self.executor.execute(cmd, "Get account authorization details - complete IAM snapshot")
        self._add_result(result)
        return result

    def _get_caller_identity(self) -> dict:
        """Get caller identity (current user info)."""
        cmd = "aws sts get-caller-identity"
        result = self.executor.execute(cmd, "Get caller identity - current user info")
        self._add_result(result)
        return result

    def _list_users(self) -> dict:
        """List all IAM users."""
        cmd = self._build_cmd("iam", "list-users")
        result = self.executor.execute(cmd, "List all IAM users")
        self._add_result(result)

        if result.success and result.data:
            users = result.data.get("Users", [])
            for user in users:
                username = user.get("UserName")
                if username:
                    self._enumerate_user(username)

        return result

    def _enumerate_user(self, username: str) -> None:
        """Enumerate a specific user's IAM details."""
        # Get user metadata
        cmd = f'aws iam get-user --user-name "{username}"'
        result = self.executor.execute(cmd, f'Get user metadata: {username}')
        self._add_result(result)

        # List access keys
        cmd = f'aws iam list-access-keys --user-name "{username}"'
        result = self.executor.execute(cmd, f'List access keys for: {username}')
        self._add_result(result)

        # List SSH public keys
        cmd = f'aws iam list-ssh-public-keys --user-name "{username}"'
        result = self.executor.execute(cmd, f'List SSH public keys for: {username}')
        self._add_result(result)

        # Get SSH public keys details
        if result.success and result.data:
            ssh_keys = result.data.get("SSHPublicKeys", [])
            for ssh_key in ssh_keys:
                key_id = ssh_key.get("SSHPublicKeyId")
                if key_id:
                    cmd = f'aws iam get-ssh-public-key --user-name "{username}" --ssh-public-key-id "{key_id}" --encoding SSH'
                    result = self.executor.execute(cmd, f'Get SSH public key: {key_id}')
                    self._add_result(result)

        # List service-specific credentials
        cmd = f'aws iam list-service-specific-credentials --user-name "{username}"'
        result = self.executor.execute(cmd, f'List service-specific credentials for: {username}')
        self._add_result(result)

        # List user policies (inline)
        cmd = f'aws iam list-user-policies --user-name "{username}"'
        result = self.executor.execute(cmd, f'List inline policies for user: {username}')
        self._add_result(result)

        # Get inline policy details
        if result.success and result.data:
            policies = result.data.get("PolicyNames", [])
            for policy_name in policies:
                cmd = f'aws iam get-user-policy --user-name "{username}" --policy-name "{policy_name}"'
                result = self.executor.execute(cmd, f'Get inline policy: {policy_name}')
                self._add_result(result)

        # List attached user policies (managed)
        cmd = f'aws iam list-attached-user-policies --user-name "{username}"'
        result = self.executor.execute(cmd, f'List attached policies for user: {username}')
        self._add_result(result)

    def _list_groups(self) -> dict:
        """List all IAM groups."""
        cmd = "aws iam list-groups"
        result = self.executor.execute(cmd, "List all IAM groups")
        self._add_result(result)

        if result.success and result.data:
            groups = result.data.get("Groups", [])
            for group in groups:
                group_name = group.get("GroupName")
                if group_name:
                    self._enumerate_group(group_name)

        return result

    def _enumerate_group(self, group_name: str) -> None:
        """Enumerate a specific group's IAM details."""
        # Get group details
        cmd = f'aws iam get-group --group-name "{group_name}"'
        result = self.executor.execute(cmd, f'Get group details: {group_name}')
        self._add_result(result)

        # List group policies (inline)
        cmd = f'aws iam list-group-policies --group-name "{group_name}"'
        result = self.executor.execute(cmd, f'List inline policies for group: {group_name}')
        self._add_result(result)

        # Get inline policy details
        if result.success and result.data:
            policies = result.data.get("PolicyNames", [])
            for policy_name in policies:
                cmd = f'aws iam get-group-policy --group-name "{group_name}" --policy-name "{policy_name}"'
                result = self.executor.execute(cmd, f'Get inline policy: {policy_name}')
                self._add_result(result)

        # List attached group policies (managed)
        cmd = f'aws iam list-attached-group-policies --group-name "{group_name}"'
        result = self.executor.execute(cmd, f'List attached policies for group: {group_name}')
        self._add_result(result)

    def _list_roles(self) -> dict:
        """List all IAM roles."""
        cmd = "aws iam list-roles"
        result = self.executor.execute(cmd, "List all IAM roles")
        self._add_result(result)

        if result.success and result.data:
            roles = result.data.get("Roles", [])
            for role in roles:
                role_name = role.get("RoleName")
                if role_name:
                    self._enumerate_role(role_name)

        return result

    def _enumerate_role(self, role_name: str) -> None:
        """Enumerate a specific role's IAM details."""
        # Get role details
        cmd = f'aws iam get-role --role-name "{role_name}"'
        result = self.executor.execute(cmd, f'Get role details: {role_name}')
        self._add_result(result)

        # List role policies (inline)
        cmd = f'aws iam list-role-policies --role-name "{role_name}"'
        result = self.executor.execute(cmd, f'List inline policies for role: {role_name}')
        self._add_result(result)

        # Get inline policy details
        if result.success and result.data:
            policies = result.data.get("PolicyNames", [])
            for policy_name in policies:
                cmd = f'aws iam get-role-policy --role-name "{role_name}" --policy-name "{policy_name}"'
                result = self.executor.execute(cmd, f'Get inline policy: {policy_name}')
                self._add_result(result)

        # List attached role policies (managed)
        cmd = f'aws iam list-attached-role-policies --role-name "{role_name}"'
        result = self.executor.execute(cmd, f'List attached policies for role: {role_name}')
        self._add_result(result)

    def _list_policies(self) -> dict:
        """List all IAM policies."""
        # List all policies (Local scope, only attached)
        cmd = "aws iam list-policies --scope Local --only-attached"
        result = self.executor.execute(cmd, "List all attached IAM policies (Local scope)")
        self._add_result(result)

        # Get policy details for each policy
        if result.success and result.data:
            policies = result.data.get("Policies", [])
            for policy in policies:
                policy_arn = policy.get("Arn")
                if policy_arn:
                    self._get_policy_details(policy_arn)

        return result

    def _get_policy_details(self, policy_arn: str) -> None:
        """Get detailed information about a policy."""
        # Get policy
        cmd = f'aws iam get-policy --policy-arn "{policy_arn}"'
        result = self.executor.execute(cmd, f'Get policy details: {policy_arn}')
        self._add_result(result)

        # List policy versions
        cmd = f'aws iam list-policy-versions --policy-arn "{policy_arn}"'
        result = self.executor.execute(cmd, f'List policy versions: {policy_arn}')
        self._add_result(result)

        # Get ALL policy versions (not just default)
        if result.success and result.data:
            versions = result.data.get("Versions", [])
            for version in versions:
                version_id = version.get("VersionId")
                if version_id:
                    cmd = f'aws iam get-policy-version --policy-arn "{policy_arn}" --version-id "{version_id}"'
                    result = self.executor.execute(cmd, f'Get policy version: {version_id}')
                    self._add_result(result)

    def _list_saml_providers(self) -> dict:
        """List all SAML providers."""
        cmd = "aws iam list-saml-providers"
        result = self.executor.execute(cmd, "List all SAML providers")
        self._add_result(result)

        # Get details for each provider
        if result.success and result.data:
            providers = result.data.get("SAMLProviderList", [])
            for provider in providers:
                arn = provider.get("Arn")
                if arn:
                    cmd = f'aws iam get-saml-provider --saml-provider-arn "{arn}"'
                    result = self.executor.execute(cmd, f'Get SAML provider: {arn}')
                    self._add_result(result)

        return result

    def _list_open_id_connect_providers(self) -> dict:
        """List all OpenID Connect providers."""
        cmd = "aws iam list-open-id-connect-providers"
        result = self.executor.execute(cmd, "List all OpenID Connect providers")
        self._add_result(result)

        # Get details for each provider
        if result.success and result.data:
            providers = result.data.get("OpenIDConnectProviderList", [])
            for provider in providers:
                arn = provider.get("Arn")
                if arn:
                    cmd = f'aws iam get-open-id-connect-provider --open-id-connect-provider-arn "{arn}"'
                    result = self.executor.execute(cmd, f'Get OIDC provider: {arn}')
                    self._add_result(result)

        return result

    def _get_account_password_policy(self) -> dict:
        """Get account password policy."""
        cmd = "aws iam get-account-password-policy"
        result = self.executor.execute(cmd, "Get account password policy")
        self._add_result(result)
        return result

    def _list_mfa_devices(self) -> dict:
        """List all MFA devices."""
        cmd = "aws iam list-mfa-devices"
        result = self.executor.execute(cmd, "List MFA devices")
        self._add_result(result)

        # List virtual MFA devices
        cmd = "aws iam list-virtual-mfa-devices"
        result = self.executor.execute(cmd, "List virtual MFA devices")
        self._add_result(result)

        return result

    def _list_instance_profiles(self) -> dict:
        """List all IAM instance profiles."""
        cmd = "aws iam list-instance-profiles"
        result = self.executor.execute(cmd, "List IAM instance profiles")
        self._add_result(result)
        
        return result

    def _extract_data(self) -> dict[str, Any]:
        """Extract structured data from command results."""
        data = {
            "users": [],
            "groups": [],
            "roles": [],
            "policies": [],
            "saml_providers": [],
            "oidc_providers": [],
            "password_policy": None,
            "mfa_devices": []
        }

        for cmd_result in self.commands_executed:
            cmd = cmd_result.get("command", "")
            result_data = cmd_result.get("data")

            if not result_data or isinstance(result_data, str):
                continue

            if "list-users" in cmd and "Users" in result_data:
                data["users"] = result_data.get("Users", [])
            elif "list-groups" in cmd and "Groups" in result_data:
                data["groups"] = result_data.get("Groups", [])
            elif "list-roles" in cmd and "Roles" in result_data:
                data["roles"] = result_data.get("Roles", [])
            elif "list-policies" in cmd and "Policies" in result_data:
                data["policies"] = result_data.get("Policies", [])
            elif "list-saml-providers" in cmd and "SAMLProviderList" in result_data:
                data["saml_providers"] = result_data.get("SAMLProviderList", [])
            elif "list-open-id-connect" in cmd and "OpenIDConnectProviderList" in result_data:
                data["oidc_providers"] = result_data.get("OpenIDConnectProviderList", [])
            elif "get-account-password-policy" in cmd:
                data["password_policy"] = result_data.get("PasswordPolicy", {})
            elif "list-mfa-devices" in cmd:
                data["mfa_devices"] = result_data.get("MFADevices", [])

        return data
