"""AWS RDS enumeration module with all specified commands."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class RDSModule(BaseModule):
    """AWS RDS enumeration module."""

    MODULE_NAME = "rds"
    DISPLAY_NAME = "AWS RDS Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.db_clusters: list[dict] = []
        self.db_instances: list[dict] = []
        self.db_proxies: list[dict] = []

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
        """Execute all RDS enumeration checks."""
        self.commands_executed = []
        self.db_clusters = []
        self.db_instances = []
        self.db_proxies = []

        # Get DB clusters
        self._describe_db_clusters()
        self._describe_db_cluster_endpoints()
        
        # Get cluster snapshots
        self._describe_db_cluster_snapshots()
        
        # Get DB instances
        self._describe_db_instances()
        
        # Get DB security groups
        self._describe_db_security_groups()
        
        # Get automated backups
        self._describe_db_instance_automated_backups()
        
        # Get snapshots
        self._describe_db_snapshots()
        
        # Get public snapshots
        self._describe_db_public_snapshots()
        
        # Get proxies (must run first to get proxy names for targets)
        self._describe_db_proxy_endpoints()
        
        # Get proxy target groups and targets (only if we have proxies)
        if self.db_proxies:
            self._describe_db_proxy_target_groups()
            self._describe_db_proxy_targets()

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
        data = {
            "db_clusters": self.db_clusters,
            "db_instances": self.db_instances,
            "cluster_snapshots": [],
            "db_snapshots": [],
            "public_snapshots": [],
            "db_security_groups": [],
            "automated_backups": [],
            "db_proxies": [],
            "total_clusters": len(self.db_clusters),
            "total_instances": len(self.db_instances)
        }

        # Extract cluster snapshots
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws rds describe-db-cluster-snapshots"):
                if cmd["success"] and cmd["data"]:
                    data["cluster_snapshots"] = cmd["data"].get("DBClusterSnapshots", [])
                break

        # Extract DB snapshots
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws rds describe-db-snapshots --snapshot-type public"):
                if cmd["success"] and cmd["data"]:
                    data["public_snapshots"] = cmd["data"].get("DBSnapshots", [])
                break

        # Extract DB snapshots
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws rds describe-db-snapshots --include-public"):
                if cmd["success"] and cmd["data"]:
                    data["db_snapshots"] = cmd["data"].get("DBSnapshots", [])
                break

        # Extract DB security groups
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws rds describe-db-security-groups"):
                if cmd["success"] and cmd["data"]:
                    data["db_security_groups"] = cmd["data"].get("DBSecurityGroups", [])
                break

        # Extract automated backups
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws rds describe-db-instance-automated-backups"):
                if cmd["success"] and cmd["data"]:
                    data["automated_backups"] = cmd["data"].get("AutomatedBackups", [])
                break

        return data

    # ==================== CLUSTERS ====================

    def _describe_db_clusters(self) -> None:
        """Describe all DB clusters."""
        cmd = "aws rds describe-db-clusters"
        result = self.executor.execute(cmd, "Describe all DB clusters")
        self._add_result(result)

        # Store clusters for later enumeration
        if result.success and result.data:
            clusters = result.data.get("DBClusters", [])
            self.db_clusters = clusters
            for cluster in clusters:
                cluster_id = cluster.get("DBClusterIdentifier")
                if cluster_id:
                    self._describe_db_cluster_backtracks(cluster_id)

    def _describe_db_cluster_endpoints(self) -> None:
        """Describe DB cluster endpoints."""
        cmd = "aws rds describe-db-cluster-endpoints"
        result = self.executor.execute(cmd, "Describe DB cluster endpoints")
        self._add_result(result)

    def _describe_db_cluster_backtracks(self, cluster_identifier: str) -> None:
        """Describe DB cluster backtracks."""
        cmd = f"aws rds describe-db-cluster-backtracks --db-cluster-identifier {cluster_identifier}"
        result = self.executor.execute(
            cmd,
            f"Describe DB cluster backtracks for: {cluster_identifier}"
        )
        self._add_result(result)

    # ==================== CLUSTER SNAPSHOTS ====================

    def _describe_db_cluster_snapshots(self) -> None:
        """Describe DB cluster snapshots."""
        cmd = "aws rds describe-db-cluster-snapshots"
        result = self.executor.execute(cmd, "Describe DB cluster snapshots")
        self._add_result(result)

    # ==================== DB INSTANCES ====================

    def _describe_db_instances(self) -> None:
        """Describe DB instances."""
        cmd = "aws rds describe-db-instances"
        result = self.executor.execute(cmd, "Describe DB instances")
        self._add_result(result)

        # Store instances for later enumeration
        if result.success and result.data:
            instances = result.data.get("DBInstances", [])
            self.db_instances = instances

    def _describe_db_security_groups(self) -> None:
        """Describe DB security groups."""
        cmd = "aws rds describe-db-security-groups"
        result = self.executor.execute(cmd, "Describe DB security groups")
        self._add_result(result)

    # ==================== BACKUPS ====================

    def _describe_db_instance_automated_backups(self) -> None:
        """Describe DB instance automated backups."""
        cmd = "aws rds describe-db-instance-automated-backups"
        result = self.executor.execute(cmd, "Describe DB instance automated backups")
        self._add_result(result)

    # ==================== SNAPSHOTS ====================

    def _describe_db_snapshots(self) -> None:
        """Describe DB snapshots (including public)."""
        cmd = "aws rds describe-db-snapshots --include-public"
        result = self.executor.execute(cmd, "Describe DB snapshots (including public)")
        self._add_result(result)

    def _describe_db_public_snapshots(self) -> None:
        """Describe public DB snapshots."""
        cmd = "aws rds describe-db-snapshots --snapshot-type public"
        result = self.executor.execute(cmd, "Describe public DB snapshots")
        self._add_result(result)

    # ==================== PROXIES ====================

    def _describe_db_proxy_endpoints(self) -> None:
        """Describe DB proxy endpoints."""
        cmd = "aws rds describe-db-proxy-endpoints"
        result = self.executor.execute(cmd, "Describe DB proxy endpoints")
        self._add_result(result)

        # Store proxies for later enumeration
        if result.success and result.data:
            endpoints = result.data.get("DBProxyEndpoints", [])
            # Get unique proxy names from endpoints
            proxy_names = set()
            for endpoint in endpoints:
                proxy_name = endpoint.get("DBProxyName")
                if proxy_name:
                    proxy_names.add(proxy_name)
            # Also try to get proxies directly
            proxies_cmd = "aws rds describe-db-proxies"
            proxies_result = self.executor.execute(proxies_cmd, "Describe DB proxies")
            self._add_result(proxies_result)
            if proxies_result.success and proxies_result.data:
                for proxy in proxies_result.data.get("DBProxies", []):
                    proxy_names.add(proxy.get("DBProxyName"))
            self.db_proxies = list(proxy_names)

    def _describe_db_proxy_target_groups(self) -> None:
        """Describe DB proxy target groups."""
        if not self.db_proxies:
            # Skip if no proxies available - this command requires --db-proxy-name
            return
        
        # Run for each known proxy
        for proxy_name in self.db_proxies:
            cmd = f"aws rds describe-db-proxy-target-groups --db-proxy-name {proxy_name}"
            result = self.executor.execute(
                cmd, 
                f"Describe DB proxy target groups for proxy: {proxy_name}"
            )
            self._add_result(result)

    def _describe_db_proxy_targets(self) -> None:
        """Describe DB proxy targets."""
        if not self.db_proxies:
            # Skip if no proxies available - this command requires --db-proxy-name
            return
        
        # Run for each known proxy
        for proxy_name in self.db_proxies:
            cmd = f"aws rds describe-db-proxy-targets --db-proxy-name {proxy_name}"
            result = self.executor.execute(
                cmd, 
                f"Describe DB proxy targets for proxy: {proxy_name}"
            )
            self._add_result(result)
