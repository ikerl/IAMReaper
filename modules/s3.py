"""AWS S3 enumeration module for bucket discovery and security assessment."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class S3Module(BaseModule):
    """AWS S3 enumeration module for bucket discovery and security assessment."""

    MODULE_NAME = "s3"
    DISPLAY_NAME = "AWS S3 Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.buckets: list[dict] = []

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
        """Execute all S3 enumeration checks."""
        self.commands_executed = []
        self.buckets = []

        # List all S3 buckets
        self._list_buckets()
        
        # Get S3 bucket details using list-buckets (more detailed)
        self._list_buckets_detailed()

        # For each bucket, enumerate details
        for bucket in self.buckets:
            bucket_name = bucket.get("Name")
            if bucket_name:
                # Get bucket ACL
                self._get_bucket_acl(bucket_name)
                
                # Get bucket policy
                self._get_bucket_policy(bucket_name)
                
                # Get bucket policy status (check if public)
                self._get_bucket_policy_status(bucket_name)
                
                # Get bucket versioning status
                self._get_bucket_versioning(bucket_name)
                
                # Get bucket location (region)
                self._get_bucket_location(bucket_name)
                
                # List objects in bucket (limited to first 1000)
                self._list_objects(bucket_name)
                
                # List object versions
                self._list_object_versions(bucket_name)
                
                # Get bucket public access block
                self._get_bucket_public_access_block(bucket_name)
                
                # Get bucket tags
                self._get_bucket_tagging(bucket_name)
                
                # Get bucket encryption
                self._get_bucket_encryption(bucket_name)
                
                # Get bucket lifecycle configuration
                self._get_bucket_lifecycle(bucket_name)
                
                # Get bucket cors configuration
                self._get_bucket_cors(bucket_name)
                
                # Get bucket website configuration
                self._get_bucket_website(bucket_name)

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

    def _list_buckets(self) -> dict:
        """List all S3 buckets using aws s3 ls."""
        cmd = "aws s3 ls"
        result = self.executor.execute(cmd, "List all S3 buckets (aws s3 ls)")
        self._add_result(result)
        
        # Parse the output to extract bucket names
        if result.success and result.stdout:
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split()
                    if len(parts) >= 3:
                        # Format: 2024-01-15 10:30:00 bucket-name
                        bucket_name = parts[-1]
                        self.buckets.append({"Name": bucket_name})
        
        return result

    def _list_buckets_detailed(self) -> dict:
        """List all S3 buckets with details using aws s3api list-buckets."""
        cmd = "aws s3api list-buckets"
        result = self.executor.execute(cmd, "List all S3 buckets with details (aws s3api list-buckets)")
        self._add_result(result)
        
        # Parse and merge bucket information
        if result.success and result.data:
            buckets_data = result.data.get("Buckets", [])
            existing_names = {b.get("Name") for b in self.buckets}
            
            for bucket in buckets_data:
                bucket_name = bucket.get("Name")
                if bucket_name and bucket_name not in existing_names:
                    self.buckets.append(bucket)
                elif bucket_name:
                    # Update existing bucket with more details
                    for existing in self.buckets:
                        if existing.get("Name") == bucket_name:
                            existing.update(bucket)
                            break
        
        return result

    def _get_bucket_acl(self, bucket_name: str) -> dict:
        """Get bucket ACL."""
        cmd = f"aws s3api get-bucket-acl --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket ACL: {bucket_name}")
        self._add_result(result)
        return result

    def _get_object_acl(self, bucket_name: str, key: str) -> dict:
        """Get object ACL."""
        cmd = f"aws s3api get-object-acl --bucket {bucket_name} --key \"{key}\""
        result = self.executor.execute(cmd, f"Get object ACL: {key} in bucket {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_policy(self, bucket_name: str) -> dict:
        """Get bucket policy."""
        cmd = f"aws s3api get-bucket-policy --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket policy: {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_policy_status(self, bucket_name: str) -> dict:
        """Get bucket policy status (check if public)."""
        cmd = f"aws s3api get-bucket-policy-status --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket policy status (public access): {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_versioning(self, bucket_name: str) -> dict:
        """Get bucket versioning status."""
        cmd = f"aws s3api get-bucket-versioning --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket versioning: {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_location(self, bucket_name: str) -> dict:
        """Get bucket location (region)."""
        cmd = f"aws s3api get-bucket-location --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket location: {bucket_name}")
        self._add_result(result)
        return result

    def _list_objects(self, bucket_name: str) -> dict:
        """List objects in bucket."""
        cmd = f"aws s3api list-objects-v2 --bucket {bucket_name} --max-keys 1000"
        result = self.executor.execute(cmd, f"List objects in bucket: {bucket_name}")
        self._add_result(result)
        
        # If objects found, try to get ACL for some objects
        if result.success and result.data:
            objects = result.data.get("Contents", [])
            # Get ACL for first 5 objects (to avoid too many API calls)
            for obj in objects[:5]:
                key = obj.get("Key")
                if key:
                    self._get_object_acl(bucket_name, key)
        
        return result

    def _list_object_versions(self, bucket_name: str) -> dict:
        """List object versions in bucket."""
        cmd = f"aws s3api list-object-versions --bucket {bucket_name} --max-keys 1000"
        result = self.executor.execute(cmd, f"List object versions in bucket: {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_public_access_block(self, bucket_name: str) -> dict:
        """Get bucket public access block configuration."""
        cmd = f"aws s3api get-public-access-block --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get public access block: {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_tagging(self, bucket_name: str) -> dict:
        """Get bucket tags."""
        cmd = f"aws s3api get-bucket-tagging --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket tagging: {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_encryption(self, bucket_name: str) -> dict:
        """Get bucket encryption configuration."""
        cmd = f"aws s3api get-bucket-encryption --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket encryption: {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_lifecycle(self, bucket_name: str) -> dict:
        """Get bucket lifecycle configuration."""
        cmd = f"aws s3api get-bucket-lifecycle-configuration --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket lifecycle: {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_cors(self, bucket_name: str) -> dict:
        """Get bucket CORS configuration."""
        cmd = f"aws s3api get-bucket-cors --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket CORS: {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_website(self, bucket_name: str) -> dict:
        """Get bucket website configuration."""
        cmd = f"aws s3api get-bucket-website --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket website config: {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_replication(self, bucket_name: str) -> dict:
        """Get bucket replication configuration."""
        cmd = f"aws s3api get-bucket-replication --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket replication: {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_ownership_controls(self, bucket_name: str) -> dict:
        """Get bucket ownership controls."""
        cmd = f"aws s3api get-bucket-ownership-controls --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket ownership controls: {bucket_name}")
        self._add_result(result)
        return result

    def _get_bucket_intelligent_tiering(self, bucket_name: str) -> dict:
        """Get bucket intelligent tiering configuration."""
        cmd = f"aws s3api get-bucket-intelligent-tiering-configuration --bucket {bucket_name}"
        result = self.executor.execute(cmd, f"Get bucket intelligent tiering: {bucket_name}")
        self._add_result(result)
        return result

    def _extract_data(self) -> dict[str, Any]:
        """Extract structured data from command results."""
        data = {
            "buckets": [],
            "total_buckets": 0,
            "public_buckets": [],
            "encrypted_buckets": [],
            "versioned_buckets": [],
            "buckets_with_policies": [],
            "buckets_with_public_access": []
        }

        # Extract bucket information from results
        bucket_details = {}

        for cmd_result in self.commands_executed:
            cmd = cmd_result.get("command", "")
            result_data = cmd_result.get("data")
            success = cmd_result.get("success", False)

            if not result_data or isinstance(result_data, str):
                continue

            # Extract bucket name from command
            bucket_name = None
            if "--bucket" in cmd:
                parts = cmd.split("--bucket")
                if len(parts) > 1:
                    bucket_name = parts[-1].strip().split()[0]

            if not bucket_name:
                continue

            # Initialize bucket details if not exists
            if bucket_name not in bucket_details:
                bucket_details[bucket_name] = {
                    "name": bucket_name,
                    "acl": None,
                    "policy": None,
                    "policy_status": None,
                    "versioning": None,
                    "location": None,
                    "public_access_block": None,
                    "tags": None,
                    "encryption": None,
                    "lifecycle": None,
                    "cors": None,
                    "website": None,
                    "replication": None,
                    "ownership_controls": None,
                    "objects": [],
                    "object_count": 0,
                    "is_public": False,
                    "is_encrypted": False,
                    "has_versioning": False
                }

            # Parse different command results
            if "get-bucket-acl" in cmd and "Grants" in result_data:
                bucket_details[bucket_name]["acl"] = result_data

            elif "get-bucket-policy" in cmd and "Policy" in result_data:
                bucket_details[bucket_name]["policy"] = result_data
                data["buckets_with_policies"].append(bucket_name)

            elif "get-bucket-policy-status" in cmd and "PolicyStatus" in result_data:
                status = result_data.get("PolicyStatus", {})
                is_public = status.get("IsPublic", False)
                bucket_details[bucket_name]["policy_status"] = status
                bucket_details[bucket_name]["is_public"] = is_public
                if is_public:
                    data["public_buckets"].append(bucket_name)
                    data["buckets_with_public_access"].append(bucket_name)

            elif "get-bucket-versioning" in cmd and "Status" in result_data:
                status = result_data.get("Status")
                if status == "Enabled":
                    bucket_details[bucket_name]["versioning"] = status
                    bucket_details[bucket_name]["has_versioning"] = True
                    data["versioned_buckets"].append(bucket_name)

            elif "get-bucket-location" in cmd:
                location = result_data.get("LocationConstraint")
                bucket_details[bucket_name]["location"] = location

            elif "get-public-access-block" in cmd and "PublicAccessBlockConfiguration" in result_data:
                config = result_data.get("PublicAccessBlockConfiguration", {})
                bucket_details[bucket_name]["public_access_block"] = config

            elif "get-bucket-tagging" in cmd and "TagSet" in result_data:
                bucket_details[bucket_name]["tags"] = result_data.get("TagSet", [])

            elif "get-bucket-encryption" in cmd and "ServerSideEncryptionConfiguration" in result_data:
                bucket_details[bucket_name]["encryption"] = result_data
                bucket_details[bucket_name]["is_encrypted"] = True
                data["encrypted_buckets"].append(bucket_name)

            elif "get-bucket-lifecycle-configuration" in cmd and "Rules" in result_data:
                bucket_details[bucket_name]["lifecycle"] = result_data

            elif "get-bucket-cors" in cmd and "CORSRules" in result_data:
                bucket_details[bucket_name]["cors"] = result_data

            elif "get-bucket-website" in cmd and "IndexDocument" in result_data:
                bucket_details[bucket_name]["website"] = result_data

            elif "list-objects-v2" in cmd and "Contents" in result_data:
                objects = result_data.get("Contents", [])
                bucket_details[bucket_name]["objects"] = objects
                bucket_details[bucket_name]["object_count"] = len(objects)

        # Convert to list
        data["buckets"] = list(bucket_details.values())
        data["total_buckets"] = len(data["buckets"])

        return data
