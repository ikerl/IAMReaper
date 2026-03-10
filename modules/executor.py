"""AWS CLI executor with comprehensive error handling."""

import subprocess
import json
import time
import shutil
from dataclasses import dataclass
from typing import Any


@dataclass
class CommandResult:
    """Result of an AWS CLI command execution."""
    command: str
    description: str
    success: bool
    stdout: str
    stderr: str
    return_code: int
    duration_ms: float
    error_type: str | None = None
    data: Any = None


class AWSExecutor:
    """Executes AWS CLI commands with comprehensive error detection."""

    def __init__(self, region: str = "us-east-1", profile_name: str = None):
        """Initialize the executor with optional default region and profile."""
        self.region = region
        self.profile_name = profile_name
        self.aws_cli_path = shutil.which("aws")

    def _detect_error_type(self, stderr: str, return_code: int) -> str | None:
        """Detect the type of error based on stderr and return code."""
        if return_code == 0:
            return None

        stderr_lower = stderr.lower()

        if "access denied" in stderr_lower or "accessdenied" in stderr_lower:
            return "access_denied"
        elif "throttling" in stderr_lower or "throttlingexception" in stderr_lower:
            return "throttling"
        elif "nosuch" in stderr_lower or "not found" in stderr_lower:
            return "not_found"
        elif "invalidclienttokenid" in stderr_lower or "SignatureDoesNotMatch" in stderr_lower:
            return "invalid_credential"
        elif "expired" in stderr_lower or "token" in stderr_lower:
            return "expired_token"
        elif "validationerror" in stderr_lower or "invalid" in stderr_lower:
            return "validation_error"
        elif return_code == 1:
            return "command_failed"

        return "unknown_error"

    def execute(
        self,
        command: str,
        description: str = "",
        parse_json: bool = True
    ) -> CommandResult:
        """
        Execute an AWS CLI command and return a structured result.

        Args:
            command: The full AWS CLI command to execute
            description: Human-readable description of the command
            parse_json: Whether to attempt parsing stdout as JSON

        Returns:
            CommandResult with all execution details
        """
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        logger.info(f"Executing command: {command}")
        
        # Auto-add profile to AWS commands if set
        if self.profile_name and command.startswith("aws "):
            # Only add if not already present
            if "--profile" not in command:
                command = f"{command} --profile {self.profile_name}"
                logger.info(f"Added profile to command: {command}")
        
        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )

            duration_ms = (time.time() - start_time) * 1000

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            return_code = result.returncode

            success = return_code == 0
            error_type = self._detect_error_type(stderr, return_code) if not success else None

            data = None
            if parse_json and stdout:
                try:
                    data = json.loads(stdout)
                    # Format any nested JSON strings in the response
                    data = self._format_nested_json(data)
                except json.JSONDecodeError:
                    data = stdout

            return CommandResult(
                command=command,
                description=description,
                success=success,
                stdout=stdout,
                stderr=stderr,
                return_code=return_code,
                duration_ms=round(duration_ms, 2),
                error_type=error_type,
                data=data
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.time() - start_time) * 1000
            return CommandResult(
                command=command,
                description=description,
                success=False,
                stdout="",
                stderr="Command timed out after 120 seconds",
                return_code=-1,
                duration_ms=round(duration_ms, 2),
                error_type="timeout"
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return CommandResult(
                command=command,
                description=description,
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                duration_ms=round(duration_ms, 2),
                error_type="exception"
            )

    @property
    def profile_arg(self) -> str:
        """Return the profile CLI argument if a profile is set."""
        if self.profile_name:
            return f"--profile {self.profile_name}"
        return ""
    
    def _format_nested_json(self, data):
        """Recursively format any nested JSON strings in the data."""
        import json
        
        if isinstance(data, dict):
            return {key: self._format_nested_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._format_nested_json(item) for item in data]
        elif isinstance(data, str):
            # Try to parse as JSON and format it
            try:
                parsed = json.loads(data)
                return json.dumps(parsed, indent=2)
            except (json.JSONDecodeError, TypeError):
                return data
        return data

    def build_aws_command(self, service: str, operation: str, **kwargs) -> str:
        """Build a complete AWS CLI command with profile only (region comes from profile)."""
        cmd_parts = ["aws", service, operation]
        
        for key, value in kwargs.items():
            cli_key = key.replace("_", "-")
            if isinstance(value, bool) and value:
                cmd_parts.append(f"--{cli_key}")
            elif isinstance(value, list):
                for v in value:
                    cmd_parts.append(f"--{cli_key}")
                    cmd_parts.append(str(v))
            else:
                cmd_parts.append(f"--{cli_key}")
                cmd_parts.append(str(value))
        
        # Add profile only (region is obtained from profile credentials)
        if self.profile_name:
            cmd_parts.extend(["--profile", self.profile_name])
        
        return " ".join(cmd_parts)

    def execute_aws(
        self,
        service: str,
        operation: str,
        description: str = "",
        **kwargs
    ) -> CommandResult:
        """Execute an AWS CLI command with service and operation (region from profile)."""
        # Extract parse_json from kwargs (it's a Python parameter, not AWS CLI option)
        parse_json = kwargs.pop('parse_json', True)
        
        cmd_parts = ["aws", service, operation]

        for key, value in kwargs.items():
            # Convert snake_case to hyphens for CLI
            cli_key = key.replace("_", "-")
            if isinstance(value, bool) and value:
                cmd_parts.append(f"--{cli_key}")
            elif isinstance(value, list):
                for v in value:
                    cmd_parts.append(f"--{cli_key}")
                    cmd_parts.append(str(v))
            else:
                cmd_parts.append(f"--{cli_key}")
                cmd_parts.append(str(value))

        # Add profile only (region is obtained from profile credentials)
        if self.profile_name:
            cmd_parts.extend(["--profile", self.profile_name])

        command = " ".join(cmd_parts)
        return self.execute(command, description, parse_json=parse_json)
