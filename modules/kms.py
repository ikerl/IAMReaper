"""AWS KMS enumeration module with multi-region support."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class KMSModule(BaseModule):
    """AWS KMS enumeration module with multi-region support."""

    MODULE_NAME = "kms"
    DISPLAY_NAME = "AWS KMS Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []

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
        """Execute all KMS enumeration checks across all regions."""
        self.commands_executed = []

        # Get available AWS regions
        regions = self._get_regions()

        # Enumerate KMS keys in each region
        for region in regions:
            self._list_keys(region)

        # Describe custom key stores (per region)
        for region in regions:
            self._describe_custom_key_stores(region)

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

    def _get_regions(self) -> list[str]:
        """Get list of available AWS regions."""
        cmd = "aws ec2 describe-regions --query \"Regions[].RegionName\" --output text"
        result = self.executor.execute(cmd, "Get available AWS regions")
        self._add_result(result)

        regions = []
        if result.success and result.data:
            # Result is typically a list of region names
            if isinstance(result.data, list):
                regions = result.data
            elif isinstance(result.data, dict) and "Regions" in result.data:
                regions = [r.get("RegionName") for r in result.data.get("Regions", [])]

        # Default to executor region if no regions found
        if not regions:
            regions = [self.executor.region]

        return regions

    def _list_keys(self, region: str = None) -> dict:
        """List all KMS keys in a region (or default region from profile)."""
        cmd = "aws kms list-keys"
        result = self.executor.execute(cmd, f"List KMS keys")
        self._add_result(result)

        if result.success and result.data:
            keys = result.data.get("Keys", [])
            for key in keys:
                key_id = key.get("KeyId")
                if key_id:
                    # Enumerate details for each key
                    self._describe_key(key_id)
                    self._list_key_policies(key_id)
                    self._list_grants(key_id)

        return result

    def _describe_key(self, key_id: str, region: str = None) -> dict:
        """Describe a specific KMS key."""
        cmd = f'aws kms describe-key --key-id "{key_id}"'
        result = self.executor.execute(cmd, f"Describe KMS key: {key_id}")
        self._add_result(result)
        return result

    def _list_key_policies(self, key_id: str, region: str = None) -> dict:
        """List key policies for a KMS key."""
        cmd = f'aws kms list-key-policies --key-id "{key_id}"'
        result = self.executor.execute(cmd, f"List key policies for: {key_id}")
        self._add_result(result)

        # Get each policy document
        if result.success and result.data:
            policy_names = result.data.get("PolicyNames", [])
            for policy_name in policy_names:
                self._get_key_policy(key_id, policy_name)

        return result

    def _get_key_policy(self, key_id: str, policy_name: str, region: str = None) -> dict:
        """Get key policy document."""
        cmd = f'aws kms get-key-policy --key-id "{key_id}" --policy-name "{policy_name}"'
        result = self.executor.execute(cmd, f"Get key policy: {policy_name} for key: {key_id}")
        self._add_result(result)
        return result

    def _list_grants(self, key_id: str, region: str = None) -> dict:
        """List grants for a KMS key."""
        cmd = f'aws kms list-grants --key-id "{key_id}"'
        result = self.executor.execute(cmd, f"List grants for key: {key_id}")
        self._add_result(result)
        return result

    def _describe_custom_key_stores(self, region: str = None) -> dict:
        """Describe custom key stores."""
        cmd = "aws kms describe-custom-key-stores"
        result = self.executor.execute(cmd, "Describe custom key stores")
        self._add_result(result)
        return result

    def _extract_data(self) -> dict[str, Any]:
        """Extract structured data from command results."""
        data = {
            "regions": {},
            "custom_key_stores": [],
            "total_keys": 0,
            "total_regions": 0
        }

        # Track regions we've seen
        regions_data = {}

        for cmd_result in self.commands_executed:
            cmd = cmd_result.get("command", "")
            result_data = cmd_result.get("data")

            if not result_data or isinstance(result_data, str):
                continue

            # Extract region from command (use executor region as default)
            region = self.executor.region if self.executor.region else "default"

            # Initialize region if not exists
            if region not in regions_data:
                regions_data[region] = {
                    "keys": [],
                    "key_count": 0,
                    "custom_key_stores": []
                }

            # Parse different command results
            if "list-keys" in cmd and "Keys" in result_data:
                keys = result_data.get("Keys", [])
                regions_data[region]["keys"] = keys
                regions_data[region]["key_count"] = len(keys)

            elif "describe-key" in cmd and "KeyMetadata" in result_data:
                key_meta = result_data.get("KeyMetadata", {})
                key_id = key_meta.get("KeyId")
                # Add to region's keys if not already there
                if key_id:
                    existing = regions_data[region].get("keys", [])
                    if not any(k.get("KeyId") == key_id for k in existing):
                        existing.append(key_meta)
                    regions_data[region]["keys"] = existing
                    regions_data[region]["key_count"] = len(existing)

            elif "describe-custom-key-stores" in cmd and "CustomKeyStores" in result_data:
                cks_list = result_data.get("CustomKeyStores", [])
                regions_data[region]["custom_key_stores"] = cks_list
                data["custom_key_stores"].extend(cks_list)

        # Calculate totals
        total_keys = 0
        for region, rdata in regions_data.items():
            total_keys += rdata.get("key_count", 0)

        data["regions"] = regions_data
        data["total_keys"] = total_keys
        data["total_regions"] = len(regions_data)

        return data
