"""AWS CodeBuild enumeration module for build project and security assessment."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class CodeBuildModule(BaseModule):
    """AWS CodeBuild enumeration module for build project discovery and security assessment."""

    MODULE_NAME = "codebuild"
    DISPLAY_NAME = "AWS CodeBuild Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.projects: list[dict] = []
        self.builds: list[str] = []
        self.build_batches: list[str] = []
        self.reports: list[str] = []

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
        """Execute all CodeBuild enumeration checks."""
        self.commands_executed = []
        self.projects = []
        self.builds = []
        self.build_batches = []
        self.reports = []

        # List source credentials
        self._list_source_credentials()

        # List shared projects
        self._list_shared_projects()

        # List projects
        self._list_projects()

        # Get detailed information for each project
        for project in self.projects:
            project_name = project.get("name")
            if project_name:
                self._batch_get_projects(project_name)

        # List builds
        self._list_builds()

        # List builds for each project
        for project in self.projects:
            project_name = project.get("name")
            if project_name:
                self._list_builds_for_project(project_name)

        # List build batches
        self._list_build_batches()

        # List build batches for each project
        for project in self.projects:
            project_name = project.get("name")
            if project_name:
                self._list_build_batches_for_project(project_name)

        # List reports
        self._list_reports()

        # Get test cases for each report
        for report_arn in self.reports:
            self._describe_test_cases(report_arn)

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

    def _list_source_credentials(self) -> None:
        """List source credentials for CodeBuild."""
        result = self.executor.execute_aws(
            service="codebuild",
            operation="list-source-credentials",
            description="List source credentials for CodeBuild"
        )
        self._add_result(result)

    def _list_shared_projects(self) -> None:
        """List shared CodeBuild projects."""
        result = self.executor.execute_aws(
            service="codebuild",
            operation="list-shared-projects",
            description="List shared CodeBuild projects"
        )
        self._add_result(result)
        if result.success and result.data:
            projects = result.data.get("projects", [])
            for p in projects:
                if p not in [proj.get("name") for proj in self.projects]:
                    self.projects.append({"name": p})

    def _list_projects(self) -> None:
        """List CodeBuild projects."""
        result = self.executor.execute_aws(
            service="codebuild",
            operation="list-projects",
            description="List CodeBuild projects"
        )
        self._add_result(result)
        if result.success and result.data:
            projects = result.data.get("projects", [])
            for p in projects:
                if p not in [proj.get("name") for proj in self.projects]:
                    self.projects.append({"name": p})

    def _batch_get_projects(self, project_name: str) -> None:
        """Get detailed information for CodeBuild projects."""
        result = self.executor.execute_aws(
            service="codebuild",
            operation="batch-get-projects",
            description=f"Get details for CodeBuild project: {project_name}",
            names=[project_name]
        )
        self._add_result(result)
        
        # Extract sensitive information from project details
        if result.success and result.data:
            projects = result.data.get("projects", [])
            for proj in projects:
                # Check for environment variables with secrets
                env_vars = proj.get("environment", {}).get("environmentVariables", [])
                sensitive_env = []
                for env in env_vars:
                    env_name = env.get("name", "").upper()
                    # Common secret/env var patterns
                    if any(secret in env_name for secret in ["SECRET", "TOKEN", "KEY", "PASSWORD", "CREDENTIAL", "PRIVATE"]):
                        sensitive_env.append({
                            "name": env.get("name"),
                            "type": env.get("type", "PLAINTEXT"),
                            "value_present": bool(env.get("value"))
                        })
                
                # Update project with sensitive env var info
                for existing_proj in self.projects:
                    if existing_proj.get("name") == project_name:
                        existing_proj.update({
                            "arn": proj.get("arn"),
                            "description": proj.get("description"),
                            "source_type": proj.get("source", {}).get("type"),
                            "environment_type": proj.get("environment", {}).get("type"),
                            "service_role": proj.get("serviceRole"),
                            "encryption_key": proj.get("encryptionKey"),
                            "has_sensitive_env_vars": len(sensitive_env) > 0,
                            "sensitive_env_vars": sensitive_env,
                            "vpc_config": proj.get("vpcConfig"),
                            "logs_config": proj.get("logsConfig")
                        })
                        break

    def _list_builds(self) -> None:
        """List CodeBuild builds."""
        result = self.executor.execute_aws(
            service="codebuild",
            operation="list-builds",
            description="List CodeBuild builds"
        )
        self._add_result(result)
        if result.success and result.data:
            self.builds = result.data.get("ids", [])

    def _list_builds_for_project(self, project_name: str) -> None:
        """List builds for a specific CodeBuild project."""
        result = self.executor.execute_aws(
            service="codebuild",
            operation="list-builds-for-project",
            description=f"List builds for CodeBuild project: {project_name}",
            project_name=project_name
        )
        self._add_result(result)

    def _list_build_batches(self) -> None:
        """List CodeBuild batch builds."""
        result = self.executor.execute_aws(
            service="codebuild",
            operation="list-build-batches",
            description="List CodeBuild batch builds"
        )
        self._add_result(result)
        if result.success and result.data:
            self.build_batches = result.data.get("ids", [])

    def _list_build_batches_for_project(self, project_name: str) -> None:
        """List batch builds for a specific CodeBuild project."""
        result = self.executor.execute_aws(
            service="codebuild",
            operation="list-build-batches-for-project",
            description=f"List batch builds for CodeBuild project: {project_name}",
            project_name=project_name
        )
        self._add_result(result)

    def _list_reports(self) -> None:
        """List CodeBuild test reports."""
        result = self.executor.execute_aws(
            service="codebuild",
            operation="list-reports",
            description="List CodeBuild test reports"
        )
        self._add_result(result)
        if result.success and result.data:
            reports = result.data.get("reports", [])
            for report_arn in reports:
                if report_arn not in self.reports:
                    self.reports.append(report_arn)

    def _describe_test_cases(self, report_arn: str) -> None:
        """Get test cases for a CodeBuild report."""
        result = self.executor.execute_aws(
            service="codebuild",
            operation="describe-test-cases",
            description=f"Get test cases for CodeBuild report: {report_arn}",
            reportArn=report_arn
        )
        self._add_result(result)

    def _extract_data(self) -> dict[str, Any]:
        """Extract enumerated data for summary."""
        return {
            "source_credentials": self._get_source_credentials(),
            "projects": self.projects,
            "total_projects": len(self.projects),
            "projects_with_sensitive_env": len([p for p in self.projects if p.get("has_sensitive_env_vars")]),
            "builds": self.builds,
            "total_builds": len(self.builds),
            "build_batches": self.build_batches,
            "total_build_batches": len(self.build_batches),
            "reports": self.reports,
            "total_reports": len(self.reports)
        }

    def _get_source_credentials(self) -> list[dict]:
        """Extract source credentials from command results."""
        for cmd in self.commands_executed:
            if cmd.get("command", "").endswith("list-source-credentials") and cmd.get("success"):
                data = cmd.get("data", {})
                return data.get("sourceCredentialsInfos", [])
        return []
