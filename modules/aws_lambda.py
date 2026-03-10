"""AWS Lambda enumeration module for function discovery and security assessment."""

import json
from datetime import datetime
from typing import Any

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class LambdaModule(BaseModule):
    """AWS Lambda enumeration module for function discovery and security assessment."""

    MODULE_NAME = "lambda"
    DISPLAY_NAME = "AWS Lambda Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.functions: list[dict] = []

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
        """Execute all Lambda enumeration checks."""
        self.commands_executed = []
        self.functions = []

        # Get account settings
        self._get_account_settings()

        # List all Lambda functions
        self._list_functions()

        # Enumerate each function for detailed info
        for func in self.functions:
            function_name = func.get("FunctionName")
            if function_name:
                # Get function details
                self._get_function(function_name)

                # Get function configuration
                self._get_function_configuration(function_name)

                # Get event invoke configs
                self._list_function_event_invoke_configs(function_name)

                # Get Lambda URL configs
                self._list_function_url_configs(function_name)
                self._get_function_url_config(function_name)

                # Get policy (permissions to invoke)
                self._get_policy(function_name)

                # Get versions
                self._list_versions_by_function(function_name)

                # Get aliases
                self._list_aliases(function_name)

        # List layers
        self._list_layers()

        # List event source mappings
        self._list_event_source_mappings()

        # List code signing configs
        self._list_code_signing_configs()

        # Get function code signing config details
        self._list_functions_by_code_signing_config()

        # Build summary
        summary = self._summarize_commands(self.commands_executed)

        return {
            "module": self.MODULE_NAME,
            "display_name": self.DISPLAY_NAME,
            "executed_at": datetime.utcnow().isoformat() + "Z",
            "commands_executed": self.commands_executed,
            "summary": summary,
            "data": {
                "functions": self.functions,
                "total_functions": len(self.functions)
            }
        }

    def _get_account_settings(self) -> None:
        """Get Lambda account settings."""
        result = self.executor.execute_aws(
            "lambda",
            "get-account-settings",
            "Get Lambda account settings"
        )
        self._add_result(result)

    def _list_functions(self) -> None:
        """List all Lambda functions."""
        result = self.executor.execute_aws(
            "lambda",
            "list-functions",
            "List all Lambda functions",
            parse_json=True
        )
        self._add_result(result)
        
        # Extract functions for later enumeration
        if result.success and result.data:
            functions_list = result.data.get("Functions", [])
            self.functions = functions_list

    def _get_function(self, function_name: str) -> None:
        """Get detailed information about a Lambda function."""
        result = self.executor.execute_aws(
            "lambda",
            "get-function",
            f"Get function details: {function_name}",
            function_name=function_name
        )
        self._add_result(result)

    def _get_function_configuration(self, function_name: str) -> None:
        """Get Lambda function configuration."""
        result = self.executor.execute_aws(
            "lambda",
            "get-function-configuration",
            f"Get function configuration: {function_name}",
            function_name=function_name
        )
        self._add_result(result)

    def _list_function_event_invoke_configs(self, function_name: str) -> None:
        """List function event invoke configurations."""
        result = self.executor.execute_aws(
            "lambda",
            "list-function-event-invoke-configs",
            f"List event invoke configs: {function_name}",
            function_name=function_name
        )
        self._add_result(result)

    def _list_function_url_configs(self, function_name: str) -> None:
        """List Lambda function URL configurations."""
        result = self.executor.execute_aws(
            "lambda",
            "list-function-url-configs",
            f"List function URL configs: {function_name}",
            function_name=function_name
        )
        self._add_result(result)

    def _get_function_url_config(self, function_name: str) -> None:
        """Get Lambda function URL configuration."""
        result = self.executor.execute_aws(
            "lambda",
            "get-function-url-config",
            f"Get function URL config: {function_name}",
            function_name=function_name
        )
        self._add_result(result)

    def _get_policy(self, function_name: str) -> None:
        """Get Lambda policy (who can invoke the function)."""
        result = self.executor.execute_aws(
            "lambda",
            "get-policy",
            f"Get function policy: {function_name}",
            function_name=function_name
        )
        self._add_result(result)

    def _list_versions_by_function(self, function_name: str) -> None:
        """List all versions of a Lambda function."""
        result = self.executor.execute_aws(
            "lambda",
            "list-versions-by-function",
            f"List function versions: {function_name}",
            function_name=function_name
        )
        self._add_result(result)

    def _list_aliases(self, function_name: str) -> None:
        """List all aliases of a Lambda function."""
        result = self.executor.execute_aws(
            "lambda",
            "list-aliases",
            f"List function aliases: {function_name}",
            function_name=function_name
        )
        self._add_result(result)

    def _list_layers(self) -> None:
        """List all Lambda layers."""
        result = self.executor.execute_aws(
            "lambda",
            "list-layers",
            "List all Lambda layers"
        )
        self._add_result(result)

    def _list_layer_versions(self, layer_name: str) -> None:
        """List all versions of a Lambda layer."""
        result = self.executor.execute_aws(
            "lambda",
            "list-layer-versions",
            f"List layer versions: {layer_name}",
            layer_name=layer_name
        )
        self._add_result(result)

    def _get_layer_version(self, layer_name: str, version_number: int) -> None:
        """Get specific Lambda layer version details."""
        result = self.executor.execute_aws(
            "lambda",
            "get-layer-version",
            f"Get layer version: {layer_name} v{version_number}",
            layer_name=layer_name,
            version_number=version_number
        )
        self._add_result(result)

    def _get_layer_version_by_arn(self, arn: str) -> None:
        """Get Lambda layer version by ARN."""
        result = self.executor.execute_aws(
            "lambda",
            "get-layer-version-by-arn",
            f"Get layer version by ARN: {arn}",
            arn=arn
        )
        self._add_result(result)

    def _list_event_source_mappings(self) -> None:
        """List all Lambda event source mappings."""
        result = self.executor.execute_aws(
            "lambda",
            "list-event-source-mappings",
            "List all Lambda event source mappings"
        )
        self._add_result(result)

    def _list_code_signing_configs(self) -> None:
        """List all Lambda code signing configurations."""
        result = self.executor.execute_aws(
            "lambda",
            "list-code-signing-configs",
            "List all Lambda code signing configs"
        )
        self._add_result(result)

    def _list_functions_by_code_signing_config(self) -> None:
        """List functions by code signing config."""
        # First get code signing configs
        result = self.executor.execute_aws(
            "lambda",
            "list-code-signing-configs",
            "List code signing configs for function enumeration"
        )
        self._add_result(result)
        
        # If we have configs, enumerate functions by each
        if result.success and result.data:
            configs = result.data.get("CodeSigningConfigs", [])
            for config in configs:
                config_arn = config.get("CodeSigningConfigArn")
                if config_arn:
                    func_result = self.executor.execute_aws(
                        "lambda",
                        "list-functions-by-code-signing-config",
                        f"List functions by code signing config: {config_arn}",
                        code_signing_config_arn=config_arn
                    )
                    self._add_result(func_result)
