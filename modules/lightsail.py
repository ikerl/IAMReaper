"""AWS Lightsail enumeration module for Lightsail resources discovery and security assessment."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class LightsailModule(BaseModule):
    """AWS Lightsail enumeration module for instance, database, disk, and network resource discovery."""

    MODULE_NAME = "lightsail"
    DISPLAY_NAME = "AWS Lightsail Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.instances: list[dict] = []
        self.databases: list[dict] = []
        self.disks: list[dict] = []

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
        """Execute all Lightsail enumeration checks."""
        self.commands_executed = []
        self.instances = []
        self.databases = []
        self.disks = []

        # ========== Instances ==========
        self._get_instances()
        
        # Get port states for each instance
        for instance in self.instances:
            instance_name = instance.get("name")
            if instance_name:
                self._get_instance_port_states(instance_name)

        # ========== Databases ==========
        self._get_relational_databases()
        
        # Get parameters for each database
        for database in self.databases:
            db_name = database.get("name")
            if db_name:
                self._get_relational_database_parameters(db_name)
        
        self._get_relational_database_snapshots()

        # ========== Disks & Snapshots ==========
        self._get_disks()
        self._get_instance_snapshots()
        self._get_disk_snapshots()

        # ========== Networking ==========
        self._get_load_balancers()
        self._get_static_ips()
        self._get_key_pairs()

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

    # ==================== Instances ====================

    def _get_instances(self) -> dict:
        """Get all Lightsail instances."""
        cmd = "aws lightsail get-instances"
        result = self.executor.execute(cmd, "Get all Lightsail instances (aws lightsail get-instances)")
        self._add_result(result)
        
        # Parse instances from response
        if result.success and result.data:
            instances_data = result.data.get("instances", [])
            for instance in instances_data:
                self.instances.append({
                    "name": instance.get("name"),
                    "arn": instance.get("arn"),
                    "supportCode": instance.get("supportCode"),
                    "location": instance.get("location"),
                    "resourceType": instance.get("resourceType"),
                    "createdAt": instance.get("createdAt"),
                    "blueprintId": instance.get("blueprintId"),
                    "blueprintName": instance.get("blueprintName"),
                    "bundleId": instance.get("bundleId"),
                    "platform": instance.get("platform"),
                    "state": instance.get("state"),
                    "tags": instance.get("tags", []),
                    "ipAddressType": instance.get("ipAddressType"),
                    "ipv6Addresses": instance.get("ipv6Addresses", []),
                    "isStaticIp": instance.get("isStaticIp"),
                    "privateIpAddress": instance.get("privateIpAddress"),
                    "publicIpAddress": instance.get("publicIpAddress")
                })
        
        return result

    def _get_instance_port_states(self, instance_name: str) -> dict:
        """Get open ports for a specific instance."""
        cmd = f"aws lightsail get-instance-port-states --instance-name {instance_name}"
        result = self.executor.execute(cmd, f"Get instance port states: {instance_name}")
        self._add_result(result)
        return result

    # ==================== Databases ====================

    def _get_relational_databases(self) -> dict:
        """Get all Lightsail relational databases."""
        cmd = "aws lightsail get-relational-databases"
        result = self.executor.execute(cmd, "Get all Lightsail relational databases (aws lightsail get-relational-databases)")
        self._add_result(result)
        
        # Parse databases from response
        if result.success and result.data:
            databases_data = result.data.get("relationalDatabases", [])
            for db in databases_data:
                self.databases.append({
                    "name": db.get("name"),
                    "arn": db.get("arn"),
                    "supportCode": db.get("supportCode"),
                    "location": db.get("location"),
                    "resourceType": db.get("resourceType"),
                    "createdAt": db.get("createdAt"),
                    "engine": db.get("engine"),
                    "engineVersion": db.get("engineVersion"),
                    "masterDatabaseName": db.get("masterDatabaseName"),
                    "masterUsername": db.get("masterUsername"),
                    "state": db.get("state"),
                    "backupRetentionEnabled": db.get("backupRetentionEnabled"),
                    "pendingMaintenanceActions": db.get("pendingMaintenanceActions", []),
                    "tags": db.get("tags", []),
                    "caCertificateIdentifier": db.get("caCertificateIdentifier"),
                    "masterEndpoint": db.get("masterEndpoint"),
                    "pendingCloudUpdate": db.get("pendingCloudUpdate")
                })
        
        return result

    def _get_relational_database_snapshots(self) -> dict:
        """Get all Lightsail relational database snapshots."""
        cmd = "aws lightsail get-relational-database-snapshots"
        result = self.executor.execute(cmd, "Get all Lightsail relational database snapshots (aws lightsail get-relational-database-snapshots)")
        self._add_result(result)
        return result

    def _get_relational_database_parameters(self, database_name: str = None) -> dict:
        """Get parameters for a specific Lightsail relational database."""
        if not database_name:
            return None
        cmd = f"aws lightsail get-relational-database-parameters --relational-database-name {database_name}"
        result = self.executor.execute(cmd, f"Get relational database parameters: {database_name}")
        self._add_result(result)
        return result

    # ==================== Disks & Snapshots ====================

    def _get_disks(self) -> dict:
        """Get all Lightsail disks."""
        cmd = "aws lightsail get-disks"
        result = self.executor.execute(cmd, "Get all Lightsail disks (aws lightsail get-disks)")
        self._add_result(result)
        
        # Parse disks from response
        if result.success and result.data:
            disks_data = result.data.get("disks", [])
            for disk in disks_data:
                self.disks.append({
                    "name": disk.get("name"),
                    "arn": disk.get("arn"),
                    "supportCode": disk.get("supportCode"),
                    "location": disk.get("location"),
                    "resourceType": disk.get("resourceType"),
                    "createdAt": disk.get("createdAt"),
                    "sizeInGb": disk.get("sizeInGb"),
                    "state": disk.get("state"),
                    "tags": disk.get("tags", []),
                    "isAttached": disk.get("isAttached"),
                    "attachmentState": disk.get("attachmentState"),
                    "gbInUse": disk.get("gbInUse")
                })
        
        return result

    def _get_instance_snapshots(self) -> dict:
        """Get all Lightsail instance snapshots."""
        cmd = "aws lightsail get-instance-snapshots"
        result = self.executor.execute(cmd, "Get all Lightsail instance snapshots (aws lightsail get-instance-snapshots)")
        self._add_result(result)
        return result

    def _get_disk_snapshots(self) -> dict:
        """Get all Lightsail disk snapshots."""
        cmd = "aws lightsail get-disk-snapshots"
        result = self.executor.execute(cmd, "Get all Lightsail disk snapshots (aws lightsail get-disk-snapshots)")
        self._add_result(result)
        return result

    # ==================== Networking ====================

    def _get_load_balancers(self) -> dict:
        """Get all Lightsail load balancers."""
        cmd = "aws lightsail get-load-balancers"
        result = self.executor.execute(cmd, "Get all Lightsail load balancers (aws lightsail get-load-balancers)")
        self._add_result(result)
        return result

    def _get_static_ips(self) -> dict:
        """Get all Lightsail static IPs."""
        cmd = "aws lightsail get-static-ips"
        result = self.executor.execute(cmd, "Get all Lightsail static IPs (aws lightsail get-static-ips)")
        self._add_result(result)
        return result

    def _get_key_pairs(self) -> dict:
        """Get all Lightsail key pairs."""
        cmd = "aws lightsail get-key-pairs"
        result = self.executor.execute(cmd, "Get all Lightsail key pairs (aws lightsail get-key-pairs)")
        self._add_result(result)
        return result

    # ==================== Data Extraction ====================

    def _extract_data(self) -> dict[str, Any]:
        """Extract structured data from command results."""
        data = {
            "instances": self.instances,
            "total_instances": len(self.instances),
            "databases": self.databases,
            "total_databases": len(self.databases),
            "disks": self.disks,
            "total_disks": len(self.disks),
            "load_balancers": [],
            "static_ips": [],
            "key_pairs": []
        }

        # Extract load balancers from command results
        for cmd in self.commands_executed:
            if cmd["command"] == "aws lightsail get-load-balancers" and cmd["success"] and cmd.get("data"):
                data["load_balancers"] = cmd["data"].get("loadBalancers", [])
                break

        # Extract static IPs from command results
        for cmd in self.commands_executed:
            if cmd["command"] == "aws lightsail get-static-ips" and cmd["success"] and cmd.get("data"):
                data["static_ips"] = cmd["data"].get("staticIps", [])
                break

        # Extract key pairs from command results
        for cmd in self.commands_executed:
            if cmd["command"] == "aws lightsail get-key-pairs" and cmd["success"] and cmd.get("data"):
                data["key_pairs"] = cmd["data"].get("keyPairs", [])
                break

        # Count running instances
        running_instances = sum(1 for i in self.instances if i.get("state", {}).get("name") == "running")
        data["running_instances"] = running_instances

        # Count available databases
        available_databases = sum(1 for db in self.databases if db.get("state") == "available")
        data["available_databases"] = available_databases

        # Count available disks
        available_disks = sum(1 for d in self.disks if d.get("state") == "available")
        data["available_disks"] = available_disks

        return data
