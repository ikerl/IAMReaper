"""AWS ELB (Elastic Load Balancer) Enumeration Module."""

import json
from datetime import datetime
from typing import Any

from modules.base import BaseModule
from modules.executor import AWSExecutor


class ELBModule(BaseModule):
    """AWS Elastic Load Balancer enumeration module."""

    MODULE_NAME = "elb"
    DISPLAY_NAME = "AWS ELB Enumeration"

    def __init__(self, executor: AWSExecutor):
        """Initialize the ELB module with an AWS executor."""
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.elb_arns: list[str] = []
        self.elb_names: list[str] = []

    def _add_result(self, result) -> None:
        """Add command result to the list."""
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
        """Execute all ELB enumeration checks."""
        self.commands_executed = []
        self.elb_arns = []
        self.elb_names = []

        # Classic ELB (ELBv1)
        self._describe_load_balancers_classic()

        # ELBv2 (Application, Network, Gateway)
        self._describe_load_balancers_v2()
        self._describe_listeners_v2()

        # Summary
        summary = self._summarize_commands(self.commands_executed)
        return {
            "module": self.MODULE_NAME,
            "display_name": self.DISPLAY_NAME,
            "executed_at": datetime.utcnow().isoformat() + "Z",
            "commands_executed": self.commands_executed,
            "summary": summary,
            "data": self._extract_data()
        }

    def _describe_load_balancers_classic(self) -> None:
        """Get all Classic Load Balancers."""
        result = self.executor.execute_aws(
            "elb",
            "describe-load-balancers",
            "List all Classic Load Balancers",
            parse_json=True
        )
        self._add_result(result)

        # Extract ELB names for detailed queries
        if result.success and result.data:
            try:
                self.elb_names = [
                    lb.get("LoadBalancerName")
                    for lb in result.data.get("LoadBalancerDescriptions", [])
                    if lb.get("LoadBalancerName")
                ]
            except (KeyError, TypeError):
                pass

    def _describe_load_balancers_v2(self) -> None:
        """Get all Application/Network/Gateway Load Balancers (ELBv2)."""
        result = self.executor.execute_aws(
            "elbv2",
            "describe-load-balancers",
            "List all Application/Network/Gateway Load Balancers",
            parse_json=True
        )
        self._add_result(result)

        # Extract ELB ARNs for detailed queries
        if result.success and result.data:
            try:
                self.elb_arns = [
                    lb.get("LoadBalancerArn")
                    for lb in result.data.get("LoadBalancers", [])
                    if lb.get("LoadBalancerArn")
                ]
            except (KeyError, TypeError):
                pass

    def _describe_listeners_v2(self) -> None:
        """Get listeners for each ELBv2."""
        for arn in self.elb_arns[:20]:  # Limit to 20 ELBs
            if not arn:
                continue
            result = self.executor.execute_aws(
                "elbv2",
                "describe-listeners",
                f"Get listeners for ELBv2 {arn}",
                LoadBalancerArn=arn,
                parse_json=True
            )
            self._add_result(result)

    def _extract_data(self) -> dict[str, Any]:
        """Extract structured data from command results."""
        data = {
            "classic_load_balancers": [],
            "total_classic_lbs": 0,
            "internet_facing_classic_lbs": [],
            "internal_classic_lbs": [],
            "v2_load_balancers": [],
            "total_v2_lbs": 0,
            "internet_facing_v2_lbs": [],
            "internal_v2_lbs": [],
            "application_lbs": [],
            "network_lbs": [],
            "gateway_lbs": [],
            "listeners": []
        }

        for cmd in self.commands_executed:
            if not cmd.get("success") or not cmd.get("data"):
                continue

            d = cmd.get("data", {})

            # Classic ELB
            if "describe-load-balancers" in cmd.get("command", "") and "elbv2" not in cmd.get("command", ""):
                try:
                    lbs = d.get("LoadBalancerDescriptions", [])
                    data["classic_load_balancers"] = lbs
                    data["total_classic_lbs"] = len(lbs)

                    # Separate internet-facing and internal
                    for lb in lbs:
                        scheme = lb.get("Scheme", "")
                        if "internet-facing" in scheme:
                            data["internet_facing_classic_lbs"].append(lb)
                        else:
                            data["internal_classic_lbs"].append(lb)
                except (KeyError, TypeError):
                    pass

            # ELBv2
            elif "describe-load-balancers" in cmd.get("command", "") and "elbv2" in cmd.get("command", ""):
                try:
                    lbs = d.get("LoadBalancers", [])
                    data["v2_load_balancers"] = lbs
                    data["total_v2_lbs"] = len(lbs)

                    # Separate by type and scheme
                    for lb in lbs:
                        lb_type = lb.get("Type", "")
                        scheme = lb.get("Scheme", "")

                        if lb_type == "application":
                            data["application_lbs"].append(lb)
                        elif lb_type == "network":
                            data["network_lbs"].append(lb)
                        elif lb_type == "gateway":
                            data["gateway_lbs"].append(lb)

                        if "internet-facing" in scheme:
                            data["internet_facing_v2_lbs"].append(lb)
                        else:
                            data["internal_v2_lbs"].append(lb)
                except (KeyError, TypeError):
                    pass

            # ELBv2 listeners
            elif "describe-listeners" in cmd.get("command", ""):
                try:
                    listeners = d.get("Listeners", [])
                    data["listeners"].extend(listeners)
                except (KeyError, TypeError):
                    pass

        return data
