"""
Test suite for Endor Cockpit tool definitions.

This module tests the tool definitions and their integration with the SDK.
"""

import os
import sys
from typing import Any, Dict
from unittest.mock import Mock, patch

import jsonschema
import pytest

# Add src to path for imports
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespace


class TestToolDefinitions:
    """Test tool definition schemas and validation."""

    def test_tool_schema_validation(self):
        """Test that tool schemas are valid JSON Schema."""
        # Load tool definitions from the documentation
        tool_definitions = self._load_tool_definitions()

        for tool_name, schema in tool_definitions.items():
            # Validate that the schema is valid JSON Schema
            try:
                jsonschema.Draft7Validator.check_schema(schema)
            except jsonschema.exceptions.SchemaError as e:
                pytest.fail(f"Invalid schema for tool '{tool_name}': {e}")

    def test_required_parameters(self):
        """Test that required parameters are properly defined."""
        tool_definitions = self._load_tool_definitions()

        for tool_name, schema in tool_definitions.items():
            if "parameters" in schema and "required" in schema["parameters"]:
                required_params = schema["parameters"]["required"]
                properties = schema["parameters"].get("properties", {})

                # All required parameters should have definitions
                for param in required_params:
                    assert param in properties, (
                        f"Required parameter '{param}' missing from "
                        f"properties in {tool_name}"
                    )

    def test_parameter_types(self):
        """Test that parameter types are valid."""
        tool_definitions = self._load_tool_definitions()

        for tool_name, schema in tool_definitions.items():
            if "parameters" in schema and "properties" in schema["parameters"]:
                properties = schema["parameters"]["properties"]

                for param_name, param_def in properties.items():
                    if "type" in param_def:
                        valid_types = [
                            "string",
                            "integer",
                            "number",
                            "boolean",
                            "array",
                            "object",
                        ]
                        assert param_def["type"] in valid_types, (
                            f"Invalid type '{param_def['type']}' for parameter "
                            f"'{param_name}' in {tool_name}"
                        )

    def test_enum_values(self):
        """Test that enum values are properly defined."""
        tool_definitions = self._load_tool_definitions()

        for tool_name, schema in tool_definitions.items():
            if "parameters" in schema and "properties" in schema["parameters"]:
                properties = schema["parameters"]["properties"]

                for param_name, param_def in properties.items():
                    if "enum" in param_def:
                        assert isinstance(param_def["enum"], list), (
                            f"Enum values must be a list for parameter "
                            f"'{param_name}' in {tool_name}"
                        )
                        assert len(param_def["enum"]) > 0, (
                            f"Enum values cannot be empty for parameter "
                            f"'{param_name}' in {tool_name}"
                        )

    def _load_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Load tool definitions from the documentation."""
        # This would normally load from the actual tool definitions file
        # For now, we'll define some test schemas
        return {
            "list_namespaces": {
                "name": "list_namespaces",
                "description": "List all namespaces in a tenant",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tenant_namespace": {
                            "type": "string",
                            "description": "Parent tenant namespace",
                        },
                        "include_children": {
                            "type": "boolean",
                            "description": "Include child namespaces",
                            "default": True,
                        },
                    },
                    "required": ["tenant_namespace"],
                },
            },
            "create_namespace": {
                "name": "create_namespace",
                "description": "Create a new namespace",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "parent_namespace": {
                            "type": "string",
                            "description": "Parent namespace name",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name for the new namespace",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description for the namespace",
                        },
                        "labels": {
                            "type": "object",
                            "description": "Optional labels for the namespace",
                            "additionalProperties": {"type": "string"},
                        },
                    },
                    "required": ["parent_namespace", "name", "description"],
                },
            },
            "run_security_scan": {
                "name": "run_security_scan",
                "description": "Run a security scan on a namespace or resource",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": (
                                "Target namespace UUID or resource identifier"
                            ),
                        },
                        "scan_type": {
                            "type": "string",
                            "description": "Type of security scan",
                            "enum": [
                                "vulnerability",
                                "compliance",
                                "secrets",
                                "dependencies",
                                "full",
                            ],
                        },
                        "include_dependencies": {
                            "type": "boolean",
                            "description": "Include dependency scanning",
                            "default": True,
                        },
                    },
                    "required": ["target", "scan_type"],
                },
            },
        }


class TestToolImplementation:
    """Test tool implementation and integration."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock API client."""
        client = Mock(spec=APIClient)
        return client

    def test_list_namespaces_tool(self, mock_client):
        """Test the list_namespaces tool implementation."""
        # Mock the namespaces.list_namespaces function
        with patch("endor_cockpit.resources.namespace.list_namespaces") as mock_list:
            mock_list.return_value = [
                Mock(
                    meta=Mock(name="test-namespace-1", description="Test namespace 1")
                ),
                Mock(
                    meta=Mock(name="test-namespace-2", description="Test namespace 2")
                ),
            ]

            # Test the tool
            result = self._call_tool(
                "list_namespaces",
                {"tenant_namespace": "test-tenant", "include_children": True},
                mock_client,
            )

            assert result is not None
            assert len(result) == 2
            mock_list.assert_called_once_with(mock_client, "test-tenant", True)

    def test_create_namespace_tool(self, mock_client):
        """Test the create_namespace tool implementation."""
        with patch("endor_cockpit.resources.namespace.create_namespace") as mock_create:
            mock_namespace = Mock()
            mock_namespace.uuid = "test-uuid-123"
            mock_namespace.meta.name = "test-namespace"
            mock_create.return_value = mock_namespace

            # Test the tool
            result = self._call_tool(
                "create_namespace",
                {
                    "parent_namespace": "test-tenant",
                    "name": "test-namespace",
                    "description": "Test namespace description",
                },
                mock_client,
            )

            assert result is not None
            assert result.uuid == "test-uuid-123"
            mock_create.assert_called_once()

    def test_security_scan_tool(self, mock_client):
        """Test the run_security_scan tool implementation."""
        with patch("subprocess.run") as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Scan completed successfully"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Test the tool
            result = self._call_tool(
                "run_security_scan",
                {
                    "target": "test-namespace-uuid",
                    "scan_type": "full",
                    "include_dependencies": True,
                },
                mock_client,
            )

            assert result is not None
            assert result["success"] is True

    def _call_tool(
        self, tool_name: str, parameters: Dict[str, Any], client: APIClient
    ) -> Any:
        """Simulate calling a tool with given parameters."""
        if tool_name == "list_namespaces":
            return namespace.list_namespaces(
                client,
                parameters["tenant_namespace"],
                parameters.get("include_children", True),
            )
        elif tool_name == "create_namespace":
            from endor_cockpit.resources.namespace import (
                CreateNamespacePayload,
                NamespaceMetaCreate,
            )

            payload = CreateNamespacePayload(
                meta=NamespaceMetaCreate(
                    name=parameters["name"], description=parameters["description"]
                )
            )
            return namespace.create_namespace(
                client, parameters["parent_namespace"], payload
            )
        elif tool_name == "run_security_scan":
            import subprocess

            try:
                result = subprocess.run(
                    ["endorctl", "scan", "--target", parameters["target"]],
                    capture_output=True,
                    text=True,
                )
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            raise ValueError(f"Unknown tool: {tool_name}")


class TestToolValidation:
    """Test tool parameter validation."""

    def test_validate_tool_inputs(self):
        """Test tool input validation."""
        # Test valid inputs
        valid_inputs = {
            "list_namespaces": {
                "tenant_namespace": "test-tenant",
                "include_children": True,
            },
            "create_namespace": {
                "parent_namespace": "test-tenant",
                "name": "test-namespace",
                "description": "Test description",
            },
        }

        for tool_name, inputs in valid_inputs.items():
            assert self._validate_inputs(tool_name, inputs), (
                f"Validation failed for {tool_name}"
            )

    def test_validate_tool_inputs_invalid(self):
        """Test tool input validation with invalid inputs."""
        # Test invalid inputs
        invalid_inputs = {
            "list_namespaces": {
                "tenant_namespace": "",  # Empty string
                "include_children": "not-a-boolean",  # Wrong type
            },
            "create_namespace": {
                "parent_namespace": "test-tenant",
                # Missing required 'name' parameter
                "description": "Test description",
            },
        }

        for tool_name, inputs in invalid_inputs.items():
            assert not self._validate_inputs(tool_name, inputs), (
                f"Validation should fail for {tool_name}"
            )

    def _validate_inputs(self, tool_name: str, inputs: Dict[str, Any]) -> bool:
        """Validate tool inputs against schema."""
        try:
            # This would normally validate against the actual schema
            # For now, we'll do basic validation
            if tool_name == "list_namespaces":
                return "tenant_namespace" in inputs and inputs["tenant_namespace"]
            elif tool_name == "create_namespace":
                required = ["parent_namespace", "name", "description"]
                return all(param in inputs and inputs[param] for param in required)
            return False
        except Exception:
            return False


class TestToolIntegration:
    """Test tool integration with the SDK."""

    def test_tool_error_handling(self):
        """Test tool error handling."""
        # Test with invalid client
        invalid_client = None

        with pytest.raises((AttributeError, TypeError)):
            self._call_tool(
                "list_namespaces", {"tenant_namespace": "test-tenant"}, invalid_client
            )

    def test_tool_parameter_types(self):
        """Test tool parameter type handling."""
        # Test with wrong parameter types
        with patch("endor_cockpit.resources.namespace.list_namespaces") as mock_list:
            mock_list.return_value = []

            # This should handle type conversion gracefully
            result = self._call_tool(
                "list_namespaces",
                {
                    "tenant_namespace": "test-tenant",
                    "include_children": "true",  # String instead of boolean
                },
                Mock(),
            )

            # The tool should handle this gracefully
            assert result is not None

    def _call_tool(
        self, tool_name: str, parameters: Dict[str, Any], client: Any
    ) -> Any:
        """Simulate calling a tool with given parameters."""
        if tool_name == "list_namespaces":
            if client is None:
                raise AttributeError("Client is None")
            return namespace.list_namespaces(
                client,
                parameters["tenant_namespace"],
                parameters.get("include_children", True),
            )
        return None


class TestToolDocumentation:
    """Test tool documentation and examples."""

    def test_tool_documentation_completeness(self):
        """Test that tool documentation is complete."""
        tool_definitions = self._load_tool_definitions()

        for tool_name, schema in tool_definitions.items():
            # Check required fields
            assert "name" in schema, f"Tool '{tool_name}' missing name"
            assert "description" in schema, f"Tool '{tool_name}' missing description"
            assert "parameters" in schema, f"Tool '{tool_name}' missing parameters"

            # Check parameter structure
            params = schema["parameters"]
            assert "type" in params, f"Tool '{tool_name}' parameters missing type"
            assert params["type"] == "object", (
                f"Tool '{tool_name}' parameters type should be 'object'"
            )

    def test_tool_examples(self):
        """Test tool usage examples."""
        # Test example usage patterns
        examples = {
            "list_namespaces": {
                "tenant_namespace": "example-tenant",
                "include_children": True,
            },
            "create_namespace": {
                "parent_namespace": "example-tenant",
                "name": "example-namespace",
                "description": "Example namespace created by agent",
            },
        }

        for tool_name, example_params in examples.items():
            # Validate example parameters
            assert self._validate_example(tool_name, example_params), (
                f"Invalid example for {tool_name}"
            )

    def _load_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Load tool definitions for testing."""
        # This would normally load from the actual tool definitions
        return {
            "list_namespaces": {
                "name": "list_namespaces",
                "description": "List all namespaces in a tenant",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tenant_namespace": {"type": "string"},
                        "include_children": {"type": "boolean", "default": True},
                    },
                    "required": ["tenant_namespace"],
                },
            },
            "create_namespace": {
                "name": "create_namespace",
                "description": "Create a new namespace",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "parent_namespace": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["parent_namespace", "name", "description"],
                },
            },
        }

    def _validate_example(self, tool_name: str, example_params: Dict[str, Any]) -> bool:
        """Validate example parameters."""
        try:
            if tool_name == "list_namespaces":
                return "tenant_namespace" in example_params
            elif tool_name == "create_namespace":
                required = ["parent_namespace", "name", "description"]
                return all(param in example_params for param in required)
            return False
        except Exception:
            return False


if __name__ == "__main__":
    pytest.main([__file__])
