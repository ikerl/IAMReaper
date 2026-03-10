"""AWS API Gateway enumeration module with all specified commands."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class APIGatewayModule(BaseModule):
    """AWS API Gateway enumeration module."""

    MODULE_NAME = "apigateway"
    DISPLAY_NAME = "AWS API Gateway Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        self.rest_apis: list[dict] = []
        self.usage_plans: list[dict] = []
        self.http_apis: list[dict] = []

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
        """Execute all API Gateway enumeration checks."""
        self.commands_executed = []
        self.rest_apis = []
        self.usage_plans = []
        self.http_apis = []

        # Generic account info (REST API)
        self._get_account_info()
        self._get_domain_names()
        self._get_usage_plans()
        self._get_vpc_links()
        self._get_client_certificates()

        # HTTP API v2 generic info
        self._get_http_api_domain_names()
        self._get_http_api_vpc_links()

        # Enumerate REST APIs
        self._list_rest_apis()

        # Enumerate HTTP APIs (v2)
        self._list_http_apis()

        # Enumerate API keys
        self._get_api_keys()

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
            "account": None,
            "domain_names": [],
            "usage_plans": [],
            "vpc_links": [],
            "client_certificates": [],
            "rest_apis": self.rest_apis,
            "http_apis": self.http_apis,
            "api_keys": [],
            "total_apis": len(self.rest_apis) + len(self.http_apis),
            "total_usage_plans": len(self.usage_plans)
        }

        # Extract account info
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws apigateway get-account"):
                if cmd["success"] and cmd["data"]:
                    data["account"] = cmd["data"]
                break

        # Extract domain names
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws apigateway get-domain-names"):
                if cmd["success"] and cmd["data"]:
                    data["domain_names"] = cmd["data"].get("domainNames", [])
                break

        # Extract usage plans
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws apigateway get-usage-plans"):
                if cmd["success"] and cmd["data"]:
                    data["usage_plans"] = cmd["data"].get("items", [])
                break

        # Extract VPC links
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws apigateway get-vpc-links"):
                if cmd["success"] and cmd["data"]:
                    data["vpc_links"] = cmd["data"].get("items", [])
                break

        # Extract client certificates
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws apigateway get-client-certificates"):
                if cmd["success"] and cmd["data"]:
                    data["client_certificates"] = cmd["data"].get("items", [])
                break

        # Extract API keys
        for cmd in self.commands_executed:
            if cmd["command"].startswith("aws apigateway get-api-keys"):
                if cmd["success"] and cmd["data"]:
                    data["api_keys"] = cmd["data"].get("items", [])
                break

        return data

    # ==================== GENERIC INFO ====================

    def _get_account_info(self) -> None:
        """Get API Gateway account information."""
        cmd = "aws apigateway get-account"
        result = self.executor.execute(cmd, "Get API Gateway account information")
        self._add_result(result)

    def _get_domain_names(self) -> None:
        """Get custom domain names."""
        cmd = "aws apigateway get-domain-names"
        result = self.executor.execute(cmd, "Get custom domain names")
        self._add_result(result)

    def _get_usage_plans(self) -> None:
        """Get all usage plans."""
        cmd = "aws apigateway get-usage-plans"
        result = self.executor.execute(cmd, "Get all usage plans")
        self._add_result(result)

        # Store usage plans for later enumeration
        if result.success and result.data:
            items = result.data.get("items", [])
            self.usage_plans = items
            for plan in items:
                plan_id = plan.get("id")
                if plan_id:
                    self._get_usage_plan_keys(plan_id)
                    self._get_usage(plan_id)

    def _get_vpc_links(self) -> None:
        """Get VPC links."""
        cmd = "aws apigateway get-vpc-links"
        result = self.executor.execute(cmd, "Get VPC links")
        self._add_result(result)

    def _get_client_certificates(self) -> None:
        """Get client certificates."""
        cmd = "aws apigateway get-client-certificates"
        result = self.executor.execute(cmd, "Get client certificates")
        self._add_result(result)

    # ==================== REST APIs ====================

    def _list_rest_apis(self) -> None:
        """List all REST APIs."""
        cmd = "aws apigateway get-rest-apis"
        result = self.executor.execute(cmd, "List all REST APIs")
        self._add_result(result)

        # Store APIs for later enumeration
        if result.success and result.data:
            items = result.data.get("items", [])
            self.rest_apis = items
            for api in items:
                api_id = api.get("id")
                if api_id:
                    self._enumerate_api(api_id)

    def _enumerate_api(self, api_id: str) -> None:
        """Enumerate all details for a specific API."""
        self._get_stages(api_id)
        self._get_resources(api_id)
        self._get_authorizers(api_id)
        self._get_models(api_id)
        self._get_gateway_responses(api_id)
        self._get_request_validators(api_id)
        self._get_deployments(api_id)

    def _get_stages(self, api_id: str) -> None:
        """Get stages for a REST API."""
        cmd = f"aws apigateway get-stages --rest-api-id {api_id}"
        result = self.executor.execute(cmd, f"Get stages for API: {api_id}")
        self._add_result(result)

    def _get_resources(self, api_id: str) -> None:
        """Get resources for a REST API."""
        cmd = f"aws apigateway get-resources --rest-api-id {api_id}"
        result = self.executor.execute(cmd, f"Get resources for API: {api_id}")
        self._add_result(result)

        # Enumerate methods for each resource
        if result.success and result.data:
            items = result.data.get("items", [])
            for resource in items:
                resource_id = resource.get("id")
                if resource_id and "resourceMethods" in resource:
                    methods = resource["resourceMethods"]
                    for http_method in methods.keys():
                        if http_method not in ("ANY",):  # Skip catch-all
                            self._get_method(api_id, resource_id, http_method)

    def _get_method(self, api_id: str, resource_id: str, http_method: str) -> None:
        """Get method details (authorizers, API key required)."""
        cmd = f"aws apigateway get-method --http-method {http_method} --rest-api-id {api_id} --resource-id {resource_id}"
        result = self.executor.execute(
            cmd, 
            f"Get method {http_method} for resource {resource_id} in API {api_id}"
        )
        self._add_result(result)

    def _get_authorizers(self, api_id: str) -> None:
        """Get authorizers for a REST API."""
        cmd = f"aws apigateway get-authorizers --rest-api-id {api_id}"
        result = self.executor.execute(cmd, f"Get authorizers for API: {api_id}")
        self._add_result(result)

    def _get_models(self, api_id: str) -> None:
        """Get models for a REST API."""
        cmd = f"aws apigateway get-models --rest-api-id {api_id}"
        result = self.executor.execute(cmd, f"Get models for API: {api_id}")
        self._add_result(result)

    def _get_gateway_responses(self, api_id: str) -> None:
        """Get gateway responses for a REST API."""
        cmd = f"aws apigateway get-gateway-responses --rest-api-id {api_id}"
        result = self.executor.execute(cmd, f"Get gateway responses for API: {api_id}")
        self._add_result(result)

    def _get_request_validators(self, api_id: str) -> None:
        """Get request validators for a REST API."""
        cmd = f"aws apigateway get-request-validators --rest-api-id {api_id}"
        result = self.executor.execute(cmd, f"Get request validators for API: {api_id}")
        self._add_result(result)

    def _get_deployments(self, api_id: str) -> None:
        """Get deployments for a REST API."""
        cmd = f"aws apigateway get-deployments --rest-api-id {api_id}"
        result = self.executor.execute(cmd, f"Get deployments for API: {api_id}")
        self._add_result(result)

    # ==================== API KEYS ====================

    def _get_api_keys(self) -> None:
        """Get all API keys with values."""
        cmd = "aws apigateway get-api-keys --include-value"
        result = self.executor.execute(cmd, "Get all API keys with values")
        self._add_result(result)

    def _get_api_key(self, api_key_id: str) -> None:
        """Get a specific API key with value."""
        cmd = f"aws apigateway get-api-key --api-key {api_key_id} --include-value"
        result = self.executor.execute(cmd, f"Get API key: {api_key_id}")
        self._add_result(result)

    # ==================== USAGE PLANS ====================

    def _get_usage_plan_keys(self, usage_plan_id: str) -> None:
        """Get API keys for a usage plan."""
        cmd = f"aws apigateway get-usage-plan-keys --usage-plan-id {usage_plan_id}"
        result = self.executor.execute(
            cmd, 
            f"Get usage plan keys for plan: {usage_plan_id}"
        )
        self._add_result(result)

    def _get_usage_plan_key(self, usage_plan_id: str, key_id: str) -> None:
        """Get a specific usage plan key."""
        cmd = f"aws apigateway get-usage-plan-key --usage-plan-id {usage_plan_id} --key-id {key_id}"
        result = self.executor.execute(
            cmd, 
            f"Get usage plan key {key_id} for plan {usage_plan_id}"
        )
        self._add_result(result)

    def _get_usage(self, usage_plan_id: str) -> None:
        """Get usage data for a usage plan."""
        # Get last 30 days of usage
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now().replace(day=1) if datetime.now().month > 1 
                     else datetime(datetime.now().year - 1, 12, 1)).strftime("%Y-%m-%d")
        
        cmd = f"aws apigateway get-usage --usage-plan-id {usage_plan_id} --start-date {start_date} --end-date {end_date}"
        result = self.executor.execute(
            cmd, 
            f"Get usage data for plan: {usage_plan_id}"
        )
        self._add_result(result)

    # ==================== HTTP APIs (v2) ====================

    def _list_http_apis(self) -> None:
        """List all HTTP APIs (v2)."""
        cmd = "aws apigatewayv2 get-apis"
        result = self.executor.execute(cmd, "List all HTTP APIs (v2)")
        self._add_result(result)

        # Store HTTP APIs for later enumeration
        if result.success and result.data:
            items = result.data.get("Items", [])
            self.http_apis = items
            for api in items:
                api_id = api.get("ApiId")
                if api_id:
                    self._enumerate_http_api(api_id)

    def _enumerate_http_api(self, api_id: str) -> None:
        """Enumerate all details for a specific HTTP API."""
        self._get_http_api(api_id)
        self._get_http_api_stages(api_id)
        self._get_http_api_routes(api_id)
        self._get_http_api_deployments(api_id)
        self._get_http_api_integrations(api_id)
        self._get_http_api_authorizers(api_id)
        self._get_http_api_models(api_id)

    def _get_http_api(self, api_id: str) -> None:
        """Get details for an HTTP API."""
        cmd = f"aws apigatewayv2 get-api --api-id {api_id}"
        result = self.executor.execute(cmd, f"Get HTTP API details: {api_id}")
        self._add_result(result)

    def _get_http_api_stages(self, api_id: str) -> None:
        """Get stages for an HTTP API."""
        cmd = f"aws apigatewayv2 get-stages --api-id {api_id}"
        result = self.executor.execute(cmd, f"Get stages for HTTP API: {api_id}")
        self._add_result(result)

    def _get_http_api_routes(self, api_id: str) -> None:
        """Get routes for an HTTP API."""
        cmd = f"aws apigatewayv2 get-routes --api-id {api_id}"
        result = self.executor.execute(cmd, f"Get routes for HTTP API: {api_id}")
        self._add_result(result)

        # Get details for each route
        if result.success and result.data:
            items = result.data.get("Items", [])
            for route in items:
                route_id = route.get("RouteId")
                if route_id:
                    self._get_http_api_route(api_id, route_id)

    def _get_http_api_route(self, api_id: str, route_id: str) -> None:
        """Get route details for an HTTP API."""
        cmd = f"aws apigatewayv2 get-route --api-id {api_id} --route-id {route_id}"
        result = self.executor.execute(
            cmd,
            f"Get route {route_id} for HTTP API: {api_id}"
        )
        self._add_result(result)

    def _get_http_api_deployments(self, api_id: str) -> None:
        """Get deployments for an HTTP API."""
        cmd = f"aws apigatewayv2 get-deployments --api-id {api_id}"
        result = self.executor.execute(cmd, f"Get deployments for HTTP API: {api_id}")
        self._add_result(result)

    def _get_http_api_deployment(self, api_id: str, deployment_id: str) -> None:
        """Get deployment details for an HTTP API."""
        cmd = f"aws apigatewayv2 get-deployment --api-id {api_id} --deployment-id {deployment_id}"
        result = self.executor.execute(
            cmd,
            f"Get deployment {deployment_id} for HTTP API: {api_id}"
        )
        self._add_result(result)

    def _get_http_api_integrations(self, api_id: str) -> None:
        """Get integrations for an HTTP API."""
        cmd = f"aws apigatewayv2 get-integrations --api-id {api_id}"
        result = self.executor.execute(cmd, f"Get integrations for HTTP API: {api_id}")
        self._add_result(result)

    def _get_http_api_authorizers(self, api_id: str) -> None:
        """Get authorizers for an HTTP API."""
        cmd = f"aws apigatewayv2 get-authorizers --api-id {api_id}"
        result = self.executor.execute(cmd, f"Get authorizers for HTTP API: {api_id}")
        self._add_result(result)

        # Get details for each authorizer
        if result.success and result.data:
            items = result.data.get("Items", [])
            for authorizer in items:
                authorizer_id = authorizer.get("AuthorizerId")
                if authorizer_id:
                    self._get_http_api_authorizer(api_id, authorizer_id)

    def _get_http_api_authorizer(self, api_id: str, authorizer_id: str) -> None:
        """Get authorizer details for an HTTP API."""
        cmd = f"aws apigatewayv2 get-authorizer --api-id {api_id} --authorizer-id {authorizer_id}"
        result = self.executor.execute(
            cmd,
            f"Get authorizer {authorizer_id} for HTTP API: {api_id}"
        )
        self._add_result(result)

    def _get_http_api_models(self, api_id: str) -> None:
        """Get models for an HTTP API."""
        cmd = f"aws apigatewayv2 get-models --api-id {api_id}"
        result = self.executor.execute(cmd, f"Get models for HTTP API: {api_id}")
        self._add_result(result)

    # ==================== HTTP API Domain Names (v2) ====================

    def _get_http_api_domain_names(self) -> None:
        """Get domain names for HTTP API (v2)."""
        cmd = "aws apigatewayv2 get-domain-names"
        result = self.executor.execute(cmd, "Get HTTP API domain names")
        self._add_result(result)

        # Get details for each domain
        if result.success and result.data:
            items = result.data.get("Items", [])
            for domain in items:
                domain_name = domain.get("DomainName")
                if domain_name:
                    self._get_http_api_domain_name(domain_name)
                    self._get_http_api_mappings(domain_name)

    def _get_http_api_domain_name(self, domain_name: str) -> None:
        """Get domain name details for HTTP API."""
        cmd = f"aws apigatewayv2 get-domain-name --domain-name {domain_name}"
        result = self.executor.execute(
            cmd,
            f"Get domain name details: {domain_name}"
        )
        self._add_result(result)

    def _get_http_api_mappings(self, domain_name: str) -> None:
        """Get API mappings for a domain name."""
        # This requires knowing the API ID, so we'll try to get mappings per API
        for api in self.http_apis:
            api_id = api.get("ApiId")
            if api_id:
                cmd = f"aws apigatewayv2 get-api-mappings --api-id {api_id} --domain-name {domain_name}"
                result = self.executor.execute(
                    cmd,
                    f"Get API mappings for domain {domain_name} and API {api_id}"
                )
                self._add_result(result)

    # ==================== HTTP API VPC Links (v2) ====================

    def _get_http_api_vpc_links(self) -> None:
        """Get VPC links for HTTP API (v2)."""
        cmd = "aws apigatewayv2 get-vpc-links"
        result = self.executor.execute(cmd, "Get HTTP API VPC links")
        self._add_result(result)
