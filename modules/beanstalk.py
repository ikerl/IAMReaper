"""AWS Elastic Beanstalk enumeration module."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class BeanstalkModule(BaseModule):
    """AWS Elastic Beanstalk enumeration module."""

    MODULE_NAME = "beanstalk"
    DISPLAY_NAME = "AWS Elastic Beanstalk Enumeration"

    # All AWS regions to search for Beanstalk S3 buckets
    REGIONS = [
        "us-east-1", "us-east-2", "us-west-1", "us-west-2",
        "ap-south-1", "ap-south-2", "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
        "ap-southeast-1", "ap-southeast-2", "ap-southeast-3",
        "ca-central-1", "eu-central-1", "eu-central-2",
        "eu-west-1", "eu-west-2", "eu-west-3", "eu-north-1",
        "sa-east-1", "af-south-1", "ap-east-1", "eu-south-1", "eu-south-2",
        "me-south-1", "me-central-1"
    ]

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.applications: list[dict] = []
        self.environments: list[dict] = []
        self.s3_buckets: list[dict] = []
        self.account_id: str = ""

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
        """Execute all Beanstalk enumeration checks."""
        self.commands_executed = []
        self.applications = []
        self.environments = []
        self.s3_buckets = []

        # Get AWS Account ID
        self._get_caller_identity()

        # Search for Beanstalk S3 buckets in all regions
        self._find_beanstalk_buckets()

        # List applications
        self._describe_applications()

        # List application versions
        self._describe_application_versions()

        # List environments
        self._describe_environments()

        # Enumerate each environment
        for env in self.environments:
            env_name = env.get("EnvironmentName")
            if env_name:
                self._describe_configuration_settings(env_name)
                self._describe_environment_resources(env_name)
                self._describe_instances_health(env_name)

        # Get events
        self._describe_events()

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
        return {
            "account_id": self.account_id,
            "applications": self.applications,
            "environments": self.environments,
            "s3_buckets": self.s3_buckets,
            "total_applications": len(self.applications),
            "total_environments": len(self.environments),
            "total_s3_buckets": len(self.s3_buckets)
        }

    # ==================== IDENTITY ====================

    def _get_caller_identity(self) -> None:
        """Get AWS account ID using STS get-caller-identity."""
        cmd = "aws sts get-caller-identity"
        result = self.executor.execute(cmd, "Get AWS account identity")
        self._add_result(result)

        # Store account ID
        if result.success and result.data:
            self.account_id = result.data.get("Account", "")

    # ==================== S3 BUCKETS ====================

    def _find_beanstalk_buckets(self) -> None:
        """Find Beanstalk S3 buckets in all regions."""
        if not self.account_id:
            # Try to get account ID first
            self._get_caller_identity()

        if not self.account_id:
            return

        # Search for buckets in each region
        for region in self.REGIONS:
            bucket_name = f"elasticbeanstalk-{region}-{self.account_id}"
            cmd = f"aws s3 ls s3://{bucket_name} --region {region}"
            result = self.executor.execute(
                cmd,
                f"Check for Beanstalk S3 bucket in {region}"
            )
            self._add_result(result)

            # If bucket exists (command succeeded with output)
            if result.success and result.stdout:
                self.s3_buckets.append({
                    "bucket_name": bucket_name,
                    "region": region,
                    "account_id": self.account_id
                })

    # ==================== APPLICATIONS ====================

    def _describe_applications(self) -> None:
        """List all Beanstalk applications."""
        cmd = "aws elasticbeanstalk describe-applications"
        result = self.executor.execute(cmd, "List all Beanstalk applications")
        self._add_result(result)

        # Store applications
        if result.success and result.data:
            apps = result.data.get("Applications", [])
            for app in apps:
                app_name = app.get("ApplicationName")
                if app_name:
                    self.applications.append(app)

    def _describe_application_versions(self) -> None:
        """List all Beanstalk application versions."""
        cmd = "aws elasticbeanstalk describe-application-versions"
        result = self.executor.execute(
            cmd,
            "List all Beanstalk application versions"
        )
        self._add_result(result)

    # ==================== ENVIRONMENTS ====================

    def _describe_environments(self) -> None:
        """List all Beanstalk environments."""
        cmd = "aws elasticbeanstalk describe-environments"
        result = self.executor.execute(cmd, "List all Beanstalk environments")
        self._add_result(result)

        # Store environments for later enumeration
        if result.success and result.data:
            envs = result.data.get("Environments", [])
            for env in envs:
                env_name = env.get("EnvironmentName")
                if env_name:
                    self.environments.append(env)

    def _describe_configuration_settings(self, environment_name: str) -> None:
        """Describe configuration settings for an environment."""
        # Get application name from environment
        app_name = None
        for env in self.environments:
            if env.get("EnvironmentName") == environment_name:
                app_name = env.get("ApplicationName")
                break

        if not app_name:
            return

        cmd = f"aws elasticbeanstalk describe-configuration-settings --application-name {app_name} --environment-name {environment_name}"
        result = self.executor.execute(
            cmd,
            f"Describe configuration settings for environment: {environment_name}"
        )
        self._add_result(result)

    def _describe_environment_resources(self, environment_name: str) -> None:
        """Describe environment resources (SQS queues, etc.)."""
        cmd = f"aws elasticbeanstalk describe-environment-resources --environment-name {environment_name}"
        result = self.executor.execute(
            cmd,
            f"Describe environment resources for: {environment_name}"
        )
        self._add_result(result)

    def _describe_instances_health(self, environment_name: str) -> None:
        """Describe instances health for an environment."""
        cmd = f"aws elasticbeanstalk describe-instances-health --environment-name {environment_name}"
        result = self.executor.execute(
            cmd,
            f"Describe instances health for environment: {environment_name}"
        )
        self._add_result(result)

    # ==================== EVENTS ====================

    def _describe_events(self) -> None:
        """Describe Beanstalk events."""
        cmd = "aws elasticbeanstalk describe-events"
        result = self.executor.execute(cmd, "List Beanstalk events")
        self._add_result(result)
