"""AWS EC2 Enumeration Module."""

import base64
import json
from datetime import datetime
from typing import Any

from modules.base import BaseModule
from modules.executor import AWSExecutor


class EC2Module(BaseModule):
    """AWS EC2 enumeration module."""

    MODULE_NAME = "ec2"
    DISPLAY_NAME = "AWS EC2 Enumeration"

    def __init__(self, executor: AWSExecutor):
        """Initialize the EC2 module with an AWS executor."""
        super().__init__(executor)
        self.commands_executed: list[dict] = []

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
        """Execute all EC2 enumeration checks."""
        self.commands_executed = []

        # Get EC2 instances
        self._describe_instances()
        self._describe_instance_status()

        # Get instance user data
        self._get_user_data()

        # Instance profiles
        self._list_instance_profiles()

        # Get tags
        self._describe_tags()

        # Get volumes
        self._describe_volumes()
        self._describe_volume_status()

        # Get snapshots
        self._describe_snapshots()

        # Scheduled instances
        self._describe_scheduled_instances()

        # Get custom images
        self._describe_images()

        # Get Elastic IPs
        self._describe_addresses()

        # Get console output (requires instance ID, skip for general enumeration)

        # Get VPN customer gateways
        self._describe_customer_gateways()
        self._describe_vpn_gateways()
        self._describe_vpn_connections()

        # Client VPN endpoints
        self._describe_client_vpn_endpoints()

        # Launch Templates
        self._describe_launch_templates()

        # Autoscaling
        self._describe_auto_scaling_groups()
        self._describe_auto_scaling_instances()
        self._describe_launch_configurations()
        self._describe_as_load_balancer_target_groups()
        self._describe_as_load_balancers()

        # Conversion tasks
        self._describe_conversion_tasks()
        self._describe_import_image_tasks()

        # Bundle tasks
        self._describe_bundle_tasks()

        # Classic link instances
        self._describe_classic_link_instances()

        # Dedicated hosts
        self._describe_hosts()

        # SSH Key pairs
        self._describe_key_pairs()

        # Networking - VPC components
        self._describe_vpcs()
        self._describe_subnets()
        self._describe_route_tables()
        self._describe_network_acls()
        self._describe_security_groups()
        self._describe_network_interfaces()
        self._describe_internet_gateways()
        self._describe_nat_gateways()
        self._describe_vpc_peering_connections()

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

    def _describe_instances(self) -> None:
        """Get all EC2 instances."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-instances",
            "List all EC2 instances",
            parse_json=True
        )
        self._add_result(result)

    def _describe_instance_status(self) -> None:
        """Get status of EC2 instances."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-instance-status",
            "Get status of running EC2 instances",
            parse_json=True
        )
        self._add_result(result)

    def _get_user_data(self) -> None:
        """Get user data from each EC2 instance."""
        # First get instances
        instances_result = self.executor.execute_aws(
            "ec2",
            "describe-instances",
            "List all EC2 instances for user data extraction",
            parse_json=True
        )
        self._add_result(instances_result)

        if not instances_result.success or not instances_result.data:
            return

        # Extract instance IDs
        instance_ids = []
        try:
            reservations = instances_result.data.get("Reservations", [])
            for reservation in reservations:
                for instance in reservation.get("Instances", []):
                    instance_ids.append(instance.get("InstanceId"))
        except (KeyError, TypeError):
            return

        # Get user data for each instance
        for instance_id in instance_ids[:10]:  # Limit to 10 instances
            if not instance_id:
                continue
            result = self.executor.execute_aws(
                "ec2",
                "describe-instance-attribute",
                f"Get user data for instance {instance_id}",
                instance_id=instance_id,
                attribute="userData"
            )
            if result.success and result.data:
                # Decode base64 user data
                try:
                    user_data_value = result.data.get("UserData", {}).get("Value")
                    if user_data_value:
                        decoded = base64.b64decode(user_data_value).decode("utf-8", errors="ignore")
                        result.decoded_user_data = decoded
                except Exception:
                    pass
            self._add_result(result)

    def _list_instance_profiles(self) -> None:
        """List IAM instance profiles."""
        result = self.executor.execute_aws(
            "iam",
            "list-instance-profiles",
            "List all IAM instance profiles",
            parse_json=True
        )
        self._add_result(result)

    def _describe_tags(self) -> None:
        """Get all EC2 tags."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-tags",
            "List all EC2 tags",
            parse_json=True
        )
        self._add_result(result)

    def _describe_volumes(self) -> None:
        """Get all EC2 volumes."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-volumes",
            "List all EC2 volumes",
            parse_json=True
        )
        self._add_result(result)

    def _describe_volume_status(self) -> None:
        """Get status of EC2 volumes."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-volume-status",
            "Get status of EC2 volumes",
            parse_json=True
        )
        self._add_result(result)

    def _describe_snapshots(self) -> None:
        """Get snapshots owned by self."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-snapshots",
            "List EC2 snapshots owned by self",
            owners=["self"],
            parse_json=True
        )
        self._add_result(result)

    def _describe_scheduled_instances(self) -> None:
        """Get scheduled EC2 instances."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-scheduled-instances",
            "List scheduled EC2 instances",
            parse_json=True
        )
        self._add_result(result)

    def _describe_images(self) -> None:
        """Get custom EC2 images."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-images",
            "List custom EC2 images (self-owned)",
            Owners=["self"],
            parse_json=True
        )
        self._add_result(result)

    def _describe_addresses(self) -> None:
        """Get Elastic IP addresses."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-addresses",
            "List Elastic IP addresses",
            parse_json=True
        )
        self._add_result(result)

    def _describe_customer_gateways(self) -> None:
        """Get VPN customer gateways."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-customer-gateways",
            "List VPN customer gateways",
            parse_json=True
        )
        self._add_result(result)

    def _describe_vpn_gateways(self) -> None:
        """Get VPN gateways."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-vpn-gateways",
            "List VPN gateways",
            parse_json=True
        )
        self._add_result(result)

    def _describe_vpn_connections(self) -> None:
        """Get VPN connections."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-vpn-connections",
            "List VPN connections",
            parse_json=True
        )
        self._add_result(result)

    def _describe_client_vpn_endpoints(self) -> None:
        """Get Client VPN endpoints."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-client-vpn-endpoints",
            "List Client VPN endpoints",
            parse_json=True
        )
        self._add_result(result)

    def _describe_launch_templates(self) -> None:
        """Get EC2 launch templates."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-launch-templates",
            "List EC2 launch templates",
            parse_json=True
        )
        self._add_result(result)

    def _describe_auto_scaling_groups(self) -> None:
        """Get Auto Scaling groups."""
        result = self.executor.execute_aws(
            "autoscaling",
            "describe-auto-scaling-groups",
            "List Auto Scaling groups",
            parse_json=True
        )
        self._add_result(result)

    def _describe_auto_scaling_instances(self) -> None:
        """Get Auto Scaling instances."""
        result = self.executor.execute_aws(
            "autoscaling",
            "describe-auto-scaling-instances",
            "List Auto Scaling instances",
            parse_json=True
        )
        self._add_result(result)

    def _describe_launch_configurations(self) -> None:
        """Get launch configurations."""
        result = self.executor.execute_aws(
            "autoscaling",
            "describe-launch-configurations",
            "List launch configurations",
            parse_json=True
        )
        self._add_result(result)

    def _describe_as_load_balancer_target_groups(self) -> None:
        """Get Auto Scaling load balancer target groups."""
        result = self.executor.execute_aws(
            "autoscaling",
            "describe-load-balancer-target-groups",
            "List Auto Scaling load balancer target groups",
            parse_json=True
        )
        self._add_result(result)

    def _describe_as_load_balancers(self) -> None:
        """Get Auto Scaling load balancers."""
        result = self.executor.execute_aws(
            "autoscaling",
            "describe-load-balancers",
            "List Auto Scaling load balancers",
            parse_json=True
        )
        self._add_result(result)

    def _describe_conversion_tasks(self) -> None:
        """Get conversion tasks."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-conversion-tasks",
            "List VM conversion tasks",
            parse_json=True
        )
        self._add_result(result)

    def _describe_import_image_tasks(self) -> None:
        """Get import image tasks."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-import-image-tasks",
            "List import image tasks",
            parse_json=True
        )
        self._add_result(result)

    def _describe_bundle_tasks(self) -> None:
        """Get bundle tasks."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-bundle-tasks",
            "List bundle tasks",
            parse_json=True
        )
        self._add_result(result)

    def _describe_classic_link_instances(self) -> None:
        """Get ClassicLink instances."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-classic-link-instances",
            "List ClassicLink instances",
            parse_json=True
        )
        self._add_result(result)

    def _describe_hosts(self) -> None:
        """Get dedicated hosts."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-hosts",
            "List dedicated hosts",
            parse_json=True
        )
        self._add_result(result)

    def _describe_key_pairs(self) -> None:
        """Get SSH key pairs."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-key-pairs",
            "List SSH key pairs",
            parse_json=True
        )
        self._add_result(result)

    def _describe_vpcs(self) -> None:
        """Get VPCs."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-vpcs",
            "List VPCs",
            parse_json=True
        )
        self._add_result(result)

    def _describe_subnets(self) -> None:
        """Get subnets."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-subnets",
            "List subnets",
            parse_json=True
        )
        self._add_result(result)

    def _describe_route_tables(self) -> None:
        """Get route tables."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-route-tables",
            "List route tables",
            parse_json=True
        )
        self._add_result(result)

    def _describe_network_acls(self) -> None:
        """Get network ACLs."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-network-acls",
            "List network ACLs",
            parse_json=True
        )
        self._add_result(result)

    def _describe_security_groups(self) -> None:
        """Get security groups."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-security-groups",
            "List security groups",
            parse_json=True
        )
        self._add_result(result)

    def _describe_network_interfaces(self) -> None:
        """Get network interfaces."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-network-interfaces",
            "List network interfaces",
            parse_json=True
        )
        self._add_result(result)

    def _describe_internet_gateways(self) -> None:
        """Get internet gateways."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-internet-gateways",
            "List internet gateways",
            parse_json=True
        )
        self._add_result(result)

    def _describe_nat_gateways(self) -> None:
        """Get NAT gateways."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-nat-gateways",
            "List NAT gateways",
            parse_json=True
        )
        self._add_result(result)

    def _describe_vpc_peering_connections(self) -> None:
        """Get VPC peering connections."""
        result = self.executor.execute_aws(
            "ec2",
            "describe-vpc-peering-connections",
            "List VPC peering connections",
            parse_json=True
        )
        self._add_result(result)

    def _extract_data(self) -> dict[str, Any]:
        """Extract structured data from command results."""
        data = {
            "instances": [],
            "total_instances": 0,
            "running_instances": 0,
            "volumes": [],
            "total_volumes": 0,
            "snapshots": [],
            "total_snapshots": 0,
            "buckets": [],
            "total_buckets": 0,
            "key_pairs": [],
            "vpcs": [],
            "subnets": [],
            "security_groups": [],
            "internet_gateways": [],
            "nat_gateways": [],
            "elastic_ips": [],
            "vpn_connections": [],
            "client_vpn_endpoints": [],
            "instance_profiles": [],
            "images": [],
            "scheduled_instances": [],
            "launch_templates": [],
            "auto_scaling_groups": [],
            "auto_scaling_instances": [],
            "launch_configurations": [],
            "as_target_groups": [],
            "as_load_balancers": []
        }

        for cmd in self.commands_executed:
            if not cmd.get("success") or not cmd.get("data"):
                continue

            d = cmd.get("data", {})

            # Instances
            if "describe-instances" in cmd.get("command", ""):
                try:
                    instances = []
                    for reservation in d.get("Reservations", []):
                        instances.extend(reservation.get("Instances", []))
                    data["instances"] = instances
                    data["total_instances"] = len(instances)
                    data["running_instances"] = sum(
                        1 for i in instances if i.get("State", {}).get("Name") == "running"
                    )
                except (KeyError, TypeError):
                    pass

            # Volumes
            elif "describe-volumes" in cmd.get("command", ""):
                data["volumes"] = d.get("Volumes", [])
                data["total_volumes"] = len(data["volumes"])

            # Snapshots
            elif "describe-snapshots" in cmd.get("command", ""):
                data["snapshots"] = d.get("Snapshots", [])
                data["total_snapshots"] = len(data["snapshots"])

            # Key pairs
            elif "describe-key-pairs" in cmd.get("command", ""):
                data["key_pairs"] = d.get("KeyPairs", [])

            # VPCs
            elif "describe-vpcs" in cmd.get("command", ""):
                data["vpcs"] = d.get("Vpcs", [])

            # Subnets
            elif "describe-subnets" in cmd.get("command", ""):
                data["subnets"] = d.get("Subnets", [])

            # Security groups
            elif "describe-security-groups" in cmd.get("command", ""):
                data["security_groups"] = d.get("SecurityGroups", [])

            # Internet gateways
            elif "describe-internet-gateways" in cmd.get("command", ""):
                data["internet_gateways"] = d.get("InternetGateways", [])

            # NAT gateways
            elif "describe-nat-gateways" in cmd.get("command", ""):
                data["nat_gateways"] = d.get("NatGateways", [])

            # Elastic IPs
            elif "describe-addresses" in cmd.get("command", ""):
                data["elastic_ips"] = d.get("Addresses", [])

            # VPN connections
            elif "describe-vpn-connections" in cmd.get("command", ""):
                data["vpn_connections"] = d.get("VpnConnections", [])

            # Instance profiles
            elif "list-instance-profiles" in cmd.get("command", ""):
                data["instance_profiles"] = d.get("InstanceProfiles", [])

            # Custom images
            elif "describe-images" in cmd.get("command", ""):
                data["images"] = d.get("Images", [])

            # Scheduled instances
            elif "describe-scheduled-instances" in cmd.get("command", ""):
                data["scheduled_instances"] = d.get("ScheduledInstanceSet", [])

            # Client VPN endpoints
            elif "describe-client-vpn-endpoints" in cmd.get("command", ""):
                data["client_vpn_endpoints"] = d.get("ClientVpnEndpoints", [])

            # Launch templates
            elif "describe-launch-templates" in cmd.get("command", ""):
                data["launch_templates"] = d.get("LaunchTemplates", [])

            # Auto Scaling groups
            elif "describe-auto-scaling-groups" in cmd.get("command", ""):
                data["auto_scaling_groups"] = d.get("AutoScalingGroups", [])

            # Auto Scaling instances
            elif "describe-auto-scaling-instances" in cmd.get("command", ""):
                data["auto_scaling_instances"] = d.get("AutoScalingInstances", [])

            # Launch configurations
            elif "describe-launch-configurations" in cmd.get("command", ""):
                data["launch_configurations"] = d.get("LaunchConfigurations", [])

            # AS Load balancer target groups
            elif "describe-load-balancer-target-groups" in cmd.get("command", ""):
                data["as_target_groups"] = d.get("LoadBalancerTargetGroups", [])

            # AS Load balancers
            elif "describe-load-balancers" in cmd.get("command", "") and "autoscaling" in cmd.get("command", ""):
                data["as_load_balancers"] = d.get("LoadBalancers", [])

        return data
