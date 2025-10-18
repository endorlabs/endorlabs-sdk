"""
Test the actual tool schemas from the documentation.

This module tests the tool definitions loaded from the docs/agents/tool-definitions.md file.
"""

import json
import pytest
import jsonschema
from typing import Dict, Any, List
import re
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


class TestToolSchemaValidation:
    """Test validation of tool schemas from documentation."""
    
    def test_extract_tool_schemas_from_docs(self):
        """Extract and validate tool schemas from the documentation."""
        tool_schemas = self._extract_tool_schemas_from_docs()
        
        assert len(tool_schemas) > 0, "No tool schemas found in documentation"
        
        for tool_name, schema in tool_schemas.items():
            # Validate JSON Schema
            try:
                jsonschema.Draft7Validator.check_schema(schema)
            except jsonschema.exceptions.SchemaError as e:
                pytest.fail(f"Invalid JSON Schema for tool '{tool_name}': {e}")
    
    def test_tool_schema_structure(self):
        """Test that tool schemas have the correct structure."""
        tool_schemas = self._extract_tool_schemas_from_docs()
        
        for tool_name, schema in tool_schemas.items():
            # Required fields
            assert "name" in schema, f"Tool '{tool_name}' missing 'name' field"
            assert "description" in schema, f"Tool '{tool_name}' missing 'description' field"
            assert "parameters" in schema, f"Tool '{tool_name}' missing 'parameters' field"
            
            # Parameter structure
            params = schema["parameters"]
            assert "type" in params, f"Tool '{tool_name}' parameters missing 'type'"
            assert params["type"] == "object", f"Tool '{tool_name}' parameters type should be 'object'"
            
            if "properties" in params:
                assert isinstance(params["properties"], dict), f"Tool '{tool_name}' properties should be a dict"
            
            if "required" in params:
                assert isinstance(params["required"], list), f"Tool '{tool_name}' required should be a list"
    
    def test_parameter_validation(self):
        """Test parameter definitions in tool schemas."""
        tool_schemas = self._extract_tool_schemas_from_docs()
        
        for tool_name, schema in tool_schemas.items():
            params = schema.get("parameters", {})
            properties = params.get("properties", {})
            required = params.get("required", [])
            
            # All required parameters should have definitions
            for param_name in required:
                assert param_name in properties, f"Required parameter '{param_name}' missing from properties in {tool_name}"
            
            # Validate parameter definitions
            for param_name, param_def in properties.items():
                if "type" in param_def:
                    valid_types = ["string", "integer", "number", "boolean", "array", "object"]
                    assert param_def["type"] in valid_types, f"Invalid type '{param_def['type']}' for parameter '{param_name}' in {tool_name}"
                
                if "enum" in param_def:
                    assert isinstance(param_def["enum"], list), f"Enum values must be a list for parameter '{param_name}' in {tool_name}"
                    assert len(param_def["enum"]) > 0, f"Enum values cannot be empty for parameter '{param_name}' in {tool_name}"
    
    def test_tool_naming_convention(self):
        """Test that tool names follow naming conventions."""
        tool_schemas = self._extract_tool_schemas_from_docs()
        
        for tool_name, schema in tool_schemas.items():
            # Tool names should be snake_case
            assert re.match(r'^[a-z][a-z0-9_]*$', tool_name), f"Tool name '{tool_name}' should be snake_case"
            
            # Tool names should be descriptive
            assert len(tool_name) > 3, f"Tool name '{tool_name}' should be descriptive"
    
    def test_tool_descriptions(self):
        """Test that tool descriptions are meaningful."""
        tool_schemas = self._extract_tool_schemas_from_docs()
        
        for tool_name, schema in tool_schemas.items():
            description = schema.get("description", "")
            assert len(description) > 10, f"Tool '{tool_name}' description should be meaningful"
            # Description should be meaningful (relaxed check)
            assert len(description) > 5, f"Tool '{tool_name}' description should be meaningful"
    
    def _extract_tool_schemas_from_docs(self) -> Dict[str, Dict[str, Any]]:
        """Extract tool schemas from the documentation file."""
        docs_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'agents', 'tool-definitions.md')
        
        if not os.path.exists(docs_path):
            pytest.skip("Tool definitions documentation not found")
        
        with open(docs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract JSON schemas from the markdown
        schemas = {}
        
        # Find JSON code blocks
        json_pattern = r'```json\n(.*?)\n```'
        json_blocks = re.findall(json_pattern, content, re.DOTALL)
        
        for json_block in json_blocks:
            try:
                schema = json.loads(json_block)
                if "name" in schema and "parameters" in schema:
                    schemas[schema["name"]] = schema
            except json.JSONDecodeError:
                continue
        
        return schemas


class TestToolSchemaExamples:
    """Test tool schema examples and usage patterns."""
    
    def test_tool_usage_examples(self):
        """Test that tool usage examples are valid."""
        tool_schemas = self._extract_tool_schemas_from_docs()
        
        # Test examples for common tools
        examples = {
            "list_namespaces": {
                "tenant_namespace": "example-tenant",
                "include_children": True
            },
            "create_namespace": {
                "parent_namespace": "example-tenant",
                "name": "example-namespace",
                "description": "Example namespace created by agent"
            },
            "run_security_scan": {
                "target": "example-namespace-uuid",
                "scan_type": "full",
                "include_dependencies": True
            }
        }
        
        for tool_name, example_params in examples.items():
            if tool_name in tool_schemas:
                schema = tool_schemas[tool_name]
                self._validate_example_against_schema(schema, example_params)
    
    def test_tool_parameter_combinations(self):
        """Test various parameter combinations for tools."""
        tool_schemas = self._extract_tool_schemas_from_docs()
        
        for tool_name, schema in tool_schemas.items():
            params = schema.get("parameters", {})
            properties = params.get("properties", {})
            required = params.get("required", [])
            
            # Test with only required parameters
            minimal_params = {}
            for param in required:
                param_def = properties.get(param, {})
                if param_def.get("type") == "string" and "enum" in param_def:
                    minimal_params[param] = param_def["enum"][0]
                elif param_def.get("type") == "array":
                    minimal_params[param] = []
                elif param_def.get("type") == "object":
                    minimal_params[param] = {}
                else:
                    minimal_params[param] = "test-value"
            self._validate_example_against_schema(schema, minimal_params)
            
            # Test with all parameters
            all_params = {}
            for param_name, param_def in properties.items():
                if param_def.get("type") == "string":
                    # Use enum value if available
                    if "enum" in param_def:
                        all_params[param_name] = param_def["enum"][0]
                    else:
                        all_params[param_name] = "test-value"
                elif param_def.get("type") == "boolean":
                    all_params[param_name] = True
                elif param_def.get("type") == "integer":
                    all_params[param_name] = 1
                elif param_def.get("type") == "array":
                    # Handle array items based on schema
                    items_schema = param_def.get("items", {})
                    if items_schema.get("type") == "object":
                        all_params[param_name] = [{"action": "test", "condition": "test", "effect": "test"}]
                    else:
                        all_params[param_name] = ["test-item"]
                elif param_def.get("type") == "object":
                    all_params[param_name] = {"key": "value"}
            
            self._validate_example_against_schema(schema, all_params)
    
    def _extract_tool_schemas_from_docs(self) -> Dict[str, Dict[str, Any]]:
        """Extract tool schemas from the documentation file."""
        docs_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'agents', 'tool-definitions.md')
        
        if not os.path.exists(docs_path):
            pytest.skip("Tool definitions documentation not found")
        
        with open(docs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract JSON schemas from the markdown
        schemas = {}
        
        # Find JSON code blocks
        json_pattern = r'```json\n(.*?)\n```'
        json_blocks = re.findall(json_pattern, content, re.DOTALL)
        
        for json_block in json_blocks:
            try:
                schema = json.loads(json_block)
                if "name" in schema and "parameters" in schema:
                    schemas[schema["name"]] = schema
            except json.JSONDecodeError:
                continue
        
        return schemas
    
    def _validate_example_against_schema(self, schema: Dict[str, Any], example_params: Dict[str, Any]) -> None:
        """Validate example parameters against a tool schema."""
        try:
            # Create a validator for the schema
            validator = jsonschema.Draft7Validator(schema["parameters"])
            
            # Validate the example parameters
            validator.validate(example_params)
        except jsonschema.exceptions.ValidationError as e:
            pytest.fail(f"Example parameters invalid for tool '{schema['name']}': {e}")
        except jsonschema.exceptions.SchemaError as e:
            pytest.fail(f"Invalid schema for tool '{schema['name']}': {e}")


class TestToolIntegration:
    """Test tool integration with the SDK."""
    
    def test_tool_schema_consistency(self):
        """Test that tool schemas are consistent with SDK functions."""
        tool_schemas = self._extract_tool_schemas_from_docs()
        
        # Check that tool names match expected SDK functions
        expected_tools = [
            "list_namespaces",
            "create_namespace", 
            "get_namespace",
            "delete_namespace",
            "list_policies",
            "create_policy",
            "run_security_scan",
            "get_scan_results",
            "list_security_findings"
        ]
        
        for expected_tool in expected_tools:
            if expected_tool in tool_schemas:
                schema = tool_schemas[expected_tool]
                assert "name" in schema, f"Tool '{expected_tool}' missing name"
                assert "description" in schema, f"Tool '{expected_tool}' missing description"
                assert "parameters" in schema, f"Tool '{expected_tool}' missing parameters"
    
    def test_tool_parameter_types(self):
        """Test that tool parameter types are appropriate."""
        tool_schemas = self._extract_tool_schemas_from_docs()
        
        for tool_name, schema in tool_schemas.items():
            params = schema.get("parameters", {})
            properties = params.get("properties", {})
            
            for param_name, param_def in properties.items():
                # Check that parameter types make sense
                if param_def.get("type") == "string":
                    # String parameters should have descriptions
                    assert "description" in param_def, f"String parameter '{param_name}' in {tool_name} should have description"
                
                elif param_def.get("type") == "boolean":
                    # Boolean parameters should have default values
                    assert "default" in param_def, f"Boolean parameter '{param_name}' in {tool_name} should have default value"
                
                elif param_def.get("type") == "array":
                    # Array parameters should specify item types
                    assert "items" in param_def, f"Array parameter '{param_name}' in {tool_name} should specify item type"
    
    def _extract_tool_schemas_from_docs(self) -> Dict[str, Dict[str, Any]]:
        """Extract tool schemas from the documentation file."""
        docs_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'agents', 'tool-definitions.md')
        
        if not os.path.exists(docs_path):
            pytest.skip("Tool definitions documentation not found")
        
        with open(docs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract JSON schemas from the markdown
        schemas = {}
        
        # Find JSON code blocks
        json_pattern = r'```json\n(.*?)\n```'
        json_blocks = re.findall(json_pattern, content, re.DOTALL)
        
        for json_block in json_blocks:
            try:
                schema = json.loads(json_block)
                if "name" in schema and "parameters" in schema:
                    schemas[schema["name"]] = schema
            except json.JSONDecodeError:
                continue
        
        return schemas


if __name__ == "__main__":
    pytest.main([__file__])
