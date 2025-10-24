#!/usr/bin/env python3
"""
Drift Analyzer - Robust drift detection between spec, class, and actual API

Usage: python drift_analyzer.py -r <resource> [options]

Features:
- Graceful degradation when only 1-3 sources available
- Smart sampling of X instances to model diverse outputs
- Flexible endpoint resolution with multiple naming conventions
- Markdown output for documentation
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import finding, namespace, package_version, policy, project, repository, repository_version


class DriftAnalyzer:
    """Robust drift analyzer for spec vs class vs API with graceful degradation."""
    
    def __init__(self, namespace: Optional[str] = None):
        self.namespace = namespace or os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")
        self.client = APIClient()
        self.resource_modules = {
            "Project": project,
            "Finding": finding,
            "Namespace": namespace,
            "PackageVersion": package_version,
            "Policy": policy,
            "Repository": repository,
            "RepositoryVersion": repository_version,
        }
    
    def analyze_drift(self, resource_type: str, max_instances: int = 10, endpoint_override: Optional[str] = None) -> Dict[str, Any]:
        """Analyze drift between spec, class, and API with enhanced sampling."""
        print(f"🔍 Analyzing drift for {resource_type}")
        print("=" * 60)
        
        results = {
            "resource_type": resource_type,
            "pydantic_fields": self._get_pydantic_fields(resource_type),
            "api_spec_fields": self._get_api_spec_fields(resource_type),
            "api_actual_fields": self._get_api_actual_fields(resource_type, max_instances, endpoint_override)
        }
        
        return results
    
    def _get_pydantic_fields(self, resource_type: str) -> Dict[str, Any]:
        """Get fields from Pydantic class implementation."""
        print(f"🏗️  Checking Pydantic fields...")
        
        try:
            resource_module = self.resource_modules.get(resource_type)
            if not resource_module:
                return {"error": f"No module found for {resource_type}"}
            
            resource_class = getattr(resource_module, resource_type, None)
            if not resource_class:
                return {"error": f"No {resource_type} class found"}
            
            fields = self._extract_pydantic_fields(resource_class, "")
            
            print(f"✅ Found {len(fields)} Pydantic fields")
            return {"fields": fields, "example": str(resource_class)[:100] + "..."}
            
        except Exception as e:
            print(f"❌ Pydantic analysis failed: {e}")
            return {"error": str(e)}
    
    def _extract_pydantic_fields(self, pydantic_class: Any, prefix: str) -> Dict[str, Any]:
        """Recursively extract fields from Pydantic class."""
        fields = {}
        
        if not hasattr(pydantic_class, 'model_fields'):
            return fields
        
        for field_name, field_info in pydantic_class.model_fields.items():
            field_path = f"{prefix}.{field_name}" if prefix else field_name
            
            fields[field_path] = {
                "type": str(field_info.annotation),
                "required": field_info.is_required(),
                "default": getattr(field_info, 'default', None)
            }
            
            # Recursively check nested classes
            field_type = field_info.annotation
            if hasattr(field_type, 'model_fields'):
                nested_fields = self._extract_pydantic_fields(field_type, field_path)
                fields.update(nested_fields)
        
        return fields
    
    def _resolve_endpoint(self, resource_type: str, endpoint_override: Optional[str] = None) -> str:
        """Try multiple endpoint patterns with fallback."""
        if endpoint_override:
            return endpoint_override
        
        # Try multiple conventions
        resource_lower = resource_type.lower()
        candidates = [
            f"v1/namespaces/{self.namespace}/{resource_lower}s",  # projects
            f"v1/namespaces/{self.namespace}/{self._to_kebab_case(resource_type)}s",  # identity-providers
            f"v1/namespaces/{self.namespace}/{resource_lower}",  # singular
            f"v1/namespaces/{self.namespace}/{self._to_snake_case(resource_type)}s",  # package_versions
        ]
        
        for endpoint in candidates:
            if self._test_endpoint(endpoint):
                print(f"✅ Found working endpoint: {endpoint}")
                return endpoint
        
        # Return first candidate with warning
        print(f"⚠️  Using fallback endpoint: {candidates[0]}")
        return candidates[0]
    
    def _to_kebab_case(self, text: str) -> str:
        """Convert IdentityProvider -> identity-provider"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', text)
        return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()
    
    def _to_snake_case(self, text: str) -> str:
        """Convert IdentityProvider -> identity_provider"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _test_endpoint(self, endpoint: str) -> bool:
        """Test if an endpoint is accessible."""
        try:
            response = self.client.session.get(
                f"{self.client.base_url}/{endpoint.lstrip('/')}",
                headers=self.client.default_headers
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _get_api_spec_fields(self, resource_type: str) -> Dict[str, Any]:
        """Get fields from API spec (OpenAPI/Swagger)."""
        print(f"📋 Checking API spec fields...")
        
        try:
            # Try to load OpenAPI spec
            openapi_file = Path(__file__).parent.parent / "external_docs/openapi-swagger.json"
            
            if not openapi_file.exists():
                return {"error": "OpenAPI spec file not found"}
            
            import json
            with open(openapi_file, 'r') as f:
                spec = json.load(f)
            
            # Find the resource in the spec
            resource_name = resource_type.lower()
            paths = spec.get("paths", {})
            
            # Look for list endpoint
            list_endpoint = None
            for path, methods in paths.items():
                if f"/{resource_name}s" in path and "get" in methods:
                    list_endpoint = path
                    break
            
            if not list_endpoint:
                return {"error": f"No list endpoint found for {resource_type}"}
            
            # Get response schema - handle both Swagger 2.0 and OpenAPI 3.0
            get_method = paths[list_endpoint]["get"]
            responses = get_method.get("responses", {})
            success_response = responses.get("200", {})
            
            # Handle Swagger 2.0 format
            if "schema" in success_response:
                schema = success_response["schema"]
                # If it's a reference, resolve it
                if "$ref" in schema:
                    schema = self._resolve_schema_reference(spec, schema["$ref"])
            # Handle OpenAPI 3.0 format
            elif "content" in success_response:
                content = success_response.get("content", {})
                json_content = content.get("application/json", {})
                schema = json_content.get("schema", {})
            else:
                return {"error": "No schema found in response"}
            
            # Extract fields from schema
            fields = self._extract_schema_fields(schema, "", spec)
            
            print(f"✅ Found {len(fields)} API spec fields")
            return {"fields": fields, "example": f"GET {list_endpoint}"}
            
        except Exception as e:
            print(f"❌ API spec analysis failed: {e}")
            return {"error": str(e)}
    
    def _resolve_schema_reference(self, spec: Dict[str, Any], ref_path: str) -> Dict[str, Any]:
        """Resolve a schema reference in Swagger 2.0 format."""
        if not ref_path.startswith("#/definitions/"):
            return {}
        
        definition_name = ref_path.split("/")[-1]
        definitions = spec.get("definitions", {})
        return definitions.get(definition_name, {})
    
    def _extract_schema_fields(self, schema: Dict[str, Any], prefix: str, spec: Dict[str, Any] = None) -> Dict[str, Any]:
        """Recursively extract fields from OpenAPI/Swagger schema."""
        fields = {}
        
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                field_path = f"{prefix}.{prop_name}" if prefix else prop_name
                
                # Handle Swagger 2.0 $ref references
                if "$ref" in prop_schema:
                    # Resolve the reference
                    ref_schema = self._resolve_schema_reference(spec, prop_schema["$ref"])
                    if ref_schema:
                        # Extract fields from the referenced schema
                        nested_fields = self._extract_schema_fields(ref_schema, field_path, spec)
                        fields.update(nested_fields)
                        # Also add the field itself
                        fields[field_path] = {
                            "type": "object",
                            "required": prop_name in schema.get("required", []),
                            "description": prop_schema.get("description", "")
                        }
                else:
                    # Regular field
                    fields[field_path] = {
                        "type": prop_schema.get("type", "unknown"),
                        "required": prop_name in schema.get("required", []),
                        "description": prop_schema.get("description", "")
                    }
                    
                    # Recursively check nested objects
                    if prop_schema.get("type") == "object" and "properties" in prop_schema:
                        nested_fields = self._extract_schema_fields(prop_schema, field_path, spec)
                        fields.update(nested_fields)
        
        return fields
    
    def _get_api_actual_fields(self, resource_type: str, max_instances: int = 10, endpoint_override: Optional[str] = None) -> Dict[str, Any]:
        """Get fields from actual API call with multi-instance sampling."""
        print(f"🌐 Checking actual API fields (sampling {max_instances} instances)...")
        
        try:
            # Resolve endpoint with flexible naming
            endpoint = self._resolve_endpoint(resource_type, endpoint_override)
            
            response = self.client.session.get(
                f"{self.client.base_url}/{endpoint.lstrip('/')}",
                headers=self.client.default_headers
            )
            
            if response.status_code != 200:
                return {"error": f"API call failed: {response.status_code} - {response.text}"}
            
            data = response.json()
            
            # Extract entities
            entities = data.get("list", [])
            if not entities:
                entities = data.get("data", [])
            if not entities:
                return {"error": f"No {resource_type} entities found in API response"}
            
            # Limit to max_instances
            if isinstance(entities, list):
                entities = entities[:max_instances]
            else:
                entities = [entities]
            
            # Analyze field variance across instances
            field_occurrences = defaultdict(int)
            field_types = defaultdict(set)
            field_examples = defaultdict(list)
            
            for entity in entities:
                fields = self._extract_api_fields(entity, "")
                for field_name, field_info in fields.items():
                    field_occurrences[field_name] += 1
                    field_types[field_name].add(field_info['type'])
                    if len(field_examples[field_name]) < 3:  # Keep first 3 examples
                        field_examples[field_name].append(field_info.get('value', 'N/A'))
            
            # Build enhanced field map with consistency info
            enhanced_fields = {}
            for field_name in field_occurrences:
                occurrence_count = field_occurrences[field_name]
                consistency = (occurrence_count / len(entities)) * 100
                
                if consistency == 100:
                    status = "always_present"
                elif consistency >= 80:
                    status = "usually_present"
                elif consistency >= 20:
                    status = "sometimes_present"
                else:
                    status = "rarely_present"
                
                enhanced_fields[field_name] = {
                    "type": list(field_types[field_name])[0] if field_types[field_name] else "unknown",
                    "consistency": f"{consistency:.0f}%",
                    "status": status,
                    "appears_in": f"{occurrence_count}/{len(entities)} instances",
                    "examples": field_examples[field_name]
                }
            
            print(f"✅ Found {len(enhanced_fields)} actual API fields across {len(entities)} instances")
            return {
                "fields": enhanced_fields, 
                "instance_count": len(entities),
                "example": str(entities[0])[:100] + "..."
            }
            
        except Exception as e:
            print(f"❌ API call failed: {e}")
            return {"error": str(e)}
    
    def _extract_api_fields(self, obj: Any, prefix: str) -> Dict[str, Any]:
        """Recursively extract fields from API response."""
        fields = {}
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                field_path = f"{prefix}.{key}" if prefix else key
                
                fields[field_path] = {
                    "type": type(value).__name__,
                    "value": str(value)[:50] + "..." if len(str(value)) > 50 else str(value),
                    "is_none": value is None
                }
                
                # Recursively process nested objects (limit depth)
                if isinstance(value, dict) and len(str(value)) < 500:
                    nested_fields = self._extract_api_fields(value, field_path)
                    fields.update(nested_fields)
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    # Process first item in list
                    nested_fields = self._extract_api_fields(value[0], f"{field_path}[0]")
                    fields.update(nested_fields)
        
        return fields
    
    def print_drift_analysis(self, results: Dict[str, Any], output_format: str = "text", output_file: Optional[str] = None) -> None:
        """Print the drift analysis results with graceful degradation."""
        if output_format == "markdown":
            self.print_markdown_output(results, output_file)
            return
        
        # Check available sources
        available_sources = []
        if "error" not in results["pydantic_fields"]:
            available_sources.append("pydantic")
        if "error" not in results["api_spec_fields"]:
            available_sources.append("spec")
        if "error" not in results["api_actual_fields"]:
            available_sources.append("api")
        
        if not available_sources:
            print("❌ ERROR: No data sources available")
            return
        
        print(f"\n{'='*80}")
        print(f"📊 DRIFT ANALYSIS: {results['resource_type']}")
        print(f"✅ Available sources: {', '.join(available_sources)}")
        print(f"{'='*80}")
        
        # Adapt analysis based on available sources
        if len(available_sources) == 1:
            print("⚠️  Limited analysis: Only 1 source available")
            self._print_single_source_analysis(results, available_sources[0])
        elif len(available_sources) == 2:
            print("📊 Partial analysis: Comparing 2 sources")
            self._print_dual_source_analysis(results, available_sources)
        else:
            print("✅ Complete analysis: All 3 sources available")
            self._print_full_drift_analysis(results)
    
    def _print_single_source_analysis(self, results: Dict[str, Any], source: str) -> None:
        """Print analysis when only one source is available."""
        if source == "pydantic":
            self._print_pydantic_section(results["pydantic_fields"])
        elif source == "spec":
            self._print_spec_section(results["api_spec_fields"])
        elif source == "api":
            self._print_api_section(results["api_actual_fields"])
    
    def _print_dual_source_analysis(self, results: Dict[str, Any], sources: List[str]) -> None:
        """Print analysis when two sources are available."""
        for source in sources:
            if source == "pydantic":
                self._print_pydantic_section(results["pydantic_fields"])
            elif source == "spec":
                self._print_spec_section(results["api_spec_fields"])
            elif source == "api":
                self._print_api_section(results["api_actual_fields"])
        
        # Compare the two available sources
        self._compare_two_sources(results, sources)
    
    def _print_full_drift_analysis(self, results: Dict[str, Any]) -> None:
        """Print complete analysis when all three sources are available."""
        # 1. Pydantic Fields
        self._print_pydantic_section(results["pydantic_fields"])
        
        # 2. API Spec Fields
        self._print_spec_section(results["api_spec_fields"])
        
        # 3. Actual API Fields
        self._print_api_section(results["api_actual_fields"])
        
        # 4. Full Drift Analysis
        print(f"\n🔍 DRIFT ANALYSIS:")
        print(f"-" * 40)
        self._analyze_drift(results)
    
    def _print_pydantic_section(self, pydantic_data: Dict[str, Any]) -> None:
        """Print Pydantic fields section."""
        print(f"\n🏗️  PYDANTIC FIELDS:")
        print(f"-" * 40)
        if "error" in pydantic_data:
            print(f"❌ {pydantic_data['error']}")
        else:
            fields = pydantic_data["fields"]
            print(f"✅ Found {len(fields)} fields")
            for field_name, field_info in fields.items():
                print(f"   - {field_name}: {field_info['type']} (required: {field_info['required']})")
    
    def _print_spec_section(self, spec_data: Dict[str, Any]) -> None:
        """Print API spec fields section."""
        print(f"\n📋 API SPEC FIELDS:")
        print(f"-" * 40)
        if "error" in spec_data:
            print(f"❌ {spec_data['error']}")
        else:
            fields = spec_data["fields"]
            print(f"✅ Found {len(fields)} fields")
            for field_name, field_info in fields.items():
                print(f"   - {field_name}: {field_info['type']} (required: {field_info['required']})")
    
    def _print_api_section(self, api_data: Dict[str, Any]) -> None:
        """Print actual API fields section."""
        print(f"\n🌐 ACTUAL API FIELDS:")
        print(f"-" * 40)
        if "error" in api_data:
            print(f"❌ {api_data['error']}")
        else:
            fields = api_data["fields"]
            instance_count = api_data.get("instance_count", 1)
            print(f"✅ Found {len(fields)} fields across {instance_count} instances")
            for field_name, field_info in fields.items():
                consistency = field_info.get('consistency', 'N/A')
                status = field_info.get('status', 'unknown')
                print(f"   - {field_name}: {field_info['type']} ({consistency} - {status})")
    
    def _compare_two_sources(self, results: Dict[str, Any], sources: List[str]) -> None:
        """Compare two available sources."""
        print(f"\n🔍 COMPARISON: {' vs '.join(sources).upper()}")
        print(f"-" * 40)
        
        # Get field sets for comparison
        source1_fields = set()
        source2_fields = set()
        
        if sources[0] == "pydantic" and "fields" in results["pydantic_fields"]:
            source1_fields = set(results["pydantic_fields"]["fields"].keys())
        elif sources[0] == "spec" and "fields" in results["api_spec_fields"]:
            source1_fields = set(results["api_spec_fields"]["fields"].keys())
        elif sources[0] == "api" and "fields" in results["api_actual_fields"]:
            source1_fields = set(results["api_actual_fields"]["fields"].keys())
        
        if sources[1] == "pydantic" and "fields" in results["pydantic_fields"]:
            source2_fields = set(results["pydantic_fields"]["fields"].keys())
        elif sources[1] == "spec" and "fields" in results["api_spec_fields"]:
            source2_fields = set(results["api_spec_fields"]["fields"].keys())
        elif sources[1] == "api" and "fields" in results["api_actual_fields"]:
            source2_fields = set(results["api_actual_fields"]["fields"].keys())
        
        # Calculate differences
        only_in_source1 = source1_fields - source2_fields
        only_in_source2 = source2_fields - source1_fields
        common_fields = source1_fields & source2_fields
        
        print(f"📊 Field counts:")
        print(f"   - {sources[0].title()}: {len(source1_fields)}")
        print(f"   - {sources[1].title()}: {len(source2_fields)}")
        print(f"   - Common: {len(common_fields)}")
        
        if only_in_source1:
            print(f"\n📤 Only in {sources[0].title()} ({len(only_in_source1)}):")
            for field in only_in_source1:
                print(f"   - {field}")
        
        if only_in_source2:
            print(f"\n📥 Only in {sources[1].title()} ({len(only_in_source2)}):")
            for field in only_in_source2:
                print(f"   - {field}")
    
    def _analyze_drift(self, results: Dict[str, Any]) -> None:
        """Analyze drift between the three sources."""
        pydantic_fields = set()
        spec_fields = set()
        api_fields = set()
        
        # Collect field names
        if "fields" in results["pydantic_fields"]:
            pydantic_fields = set(results["pydantic_fields"]["fields"].keys())
        
        if "fields" in results["api_spec_fields"]:
            spec_fields = set(results["api_spec_fields"]["fields"].keys())
        
        if "fields" in results["api_actual_fields"]:
            api_fields = set(results["api_actual_fields"]["fields"].keys())
        
        # Calculate overlaps and differences
        pydantic_spec_overlap = pydantic_fields & spec_fields
        pydantic_api_overlap = pydantic_fields & api_fields
        spec_api_overlap = spec_fields & api_fields
        all_three_overlap = pydantic_fields & spec_fields & api_fields
        
        print(f"📊 Field counts:")
        print(f"   - Pydantic: {len(pydantic_fields)}")
        print(f"   - API Spec: {len(spec_fields)}")
        print(f"   - Actual API: {len(api_fields)}")
        print(f"   - All three: {len(all_three_overlap)}")
        
        # Show drift
        if len(pydantic_fields) > 0 and len(api_fields) > 0:
            only_in_pydantic = pydantic_fields - api_fields
            only_in_api = api_fields - pydantic_fields
            
            if only_in_pydantic:
                print(f"\n📤 Only in Pydantic ({len(only_in_pydantic)}):")
                for field in only_in_pydantic:
                    print(f"   - {field}")
            
            if only_in_api:
                print(f"\n📥 Only in API ({len(only_in_api)}):")
                for field in only_in_api:
                    print(f"   - {field}")
        
        # Summary
        if len(all_three_overlap) == 0:
            print(f"\n⚠️  WARNING: No fields match between all three sources!")
        elif len(all_three_overlap) < min(len(pydantic_fields), len(api_fields)) * 0.5:
            print(f"\n⚠️  WARNING: Significant drift detected!")
        else:
            print(f"\n✅ Good alignment between sources")
    
    def print_markdown_output(self, results: Dict[str, Any], output_file: Optional[str] = None) -> None:
        """Generate markdown documentation."""
        md = f"""# Drift Analysis: {results['resource_type']}

## Overview
This analysis compares field definitions across three sources:
- **Pydantic Models**: Current implementation in code
- **API Specification**: OpenAPI schema definition  
- **Actual API Response**: Real data from API calls

## Pydantic Fields
{self._format_pydantic_markdown(results['pydantic_fields'])}

## API Specification
{self._format_spec_markdown(results['api_spec_fields'])}

## Actual API Response
{self._format_api_markdown(results['api_actual_fields'])}

## Drift Summary
{self._format_drift_markdown(results)}
"""
        
        if output_file:
            Path(output_file).write_text(md, encoding='utf-8')
            print(f"📄 Markdown output saved to: {output_file}")
        else:
            print(md)
    
    def _format_pydantic_markdown(self, pydantic_data: Dict[str, Any]) -> str:
        """Format Pydantic fields for markdown."""
        if "error" in pydantic_data:
            return f"**Error**: {pydantic_data['error']}"
        
        fields = pydantic_data["fields"]
        if not fields:
            return "No fields found"
        
        md = f"**Found {len(fields)} fields**\n\n"
        md += "| Field | Type | Required |\n"
        md += "|-------|------|----------|\n"
        
        for field_name, field_info in fields.items():
            required = "Yes" if field_info['required'] else "No"
            md += f"| `{field_name}` | `{field_info['type']}` | {required} |\n"
        
        return md
    
    def _format_spec_markdown(self, spec_data: Dict[str, Any]) -> str:
        """Format API spec fields for markdown."""
        if "error" in spec_data:
            return f"**Error**: {spec_data['error']}"
        
        fields = spec_data["fields"]
        if not fields:
            return "No fields found"
        
        md = f"**Found {len(fields)} fields**\n\n"
        md += "| Field | Type | Required |\n"
        md += "|-------|------|----------|\n"
        
        for field_name, field_info in fields.items():
            required = "Yes" if field_info['required'] else "No"
            md += f"| `{field_name}` | `{field_info['type']}` | {required} |\n"
        
        return md
    
    def _format_api_markdown(self, api_data: Dict[str, Any]) -> str:
        """Format actual API fields for markdown."""
        if "error" in api_data:
            return f"**Error**: {api_data['error']}"
        
        fields = api_data["fields"]
        if not fields:
            return "No fields found"
        
        instance_count = api_data.get("instance_count", 1)
        md = f"**Found {len(fields)} fields across {instance_count} instances**\n\n"
        md += "| Field | Type | Consistency | Status |\n"
        md += "|-------|------|-------------|--------|\n"
        
        for field_name, field_info in fields.items():
            consistency = field_info.get('consistency', 'N/A')
            status = field_info.get('status', 'unknown')
            md += f"| `{field_name}` | `{field_info['type']}` | {consistency} | {status} |\n"
        
        return md
    
    def _format_drift_markdown(self, results: Dict[str, Any]) -> str:
        """Format drift analysis for markdown."""
        # Get field sets
        pydantic_fields = set()
        spec_fields = set()
        api_fields = set()
        
        if "fields" in results["pydantic_fields"]:
            pydantic_fields = set(results["pydantic_fields"]["fields"].keys())
        if "fields" in results["api_spec_fields"]:
            spec_fields = set(results["api_spec_fields"]["fields"].keys())
        if "fields" in results["api_actual_fields"]:
            api_fields = set(results["api_actual_fields"]["fields"].keys())
        
        # Calculate overlaps
        all_three_overlap = pydantic_fields & spec_fields & api_fields
        pydantic_api_overlap = pydantic_fields & api_fields
        only_in_pydantic = pydantic_fields - api_fields
        only_in_api = api_fields - pydantic_fields
        
        md = f"""### Field Counts
- **Pydantic**: {len(pydantic_fields)} fields
- **API Spec**: {len(spec_fields)} fields  
- **Actual API**: {len(api_fields)} fields
- **All Three**: {len(all_three_overlap)} fields

### Drift Analysis
"""
        
        if len(all_three_overlap) == 0:
            md += "⚠️ **WARNING**: No fields match between all three sources!\n"
        elif len(all_three_overlap) < min(len(pydantic_fields), len(api_fields)) * 0.5:
            md += "⚠️ **WARNING**: Significant drift detected!\n"
        else:
            md += "✅ **Good alignment** between sources\n"
        
        if only_in_pydantic:
            md += f"\n### Fields Only in Pydantic ({len(only_in_pydantic)})\n"
            for field in only_in_pydantic:
                md += f"- `{field}`\n"
        
        if only_in_api:
            md += f"\n### Fields Only in API ({len(only_in_api)})\n"
            for field in only_in_api:
                md += f"- `{field}`\n"
        
        return md


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Robust drift analyzer for spec vs class vs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python drift_analyzer.py -r Project
  python drift_analyzer.py -r Finding --max-instances 5
  python drift_analyzer.py -r IdentityProvider --endpoint "v1/namespaces/{ns}/identity-providers"
  python drift_analyzer.py -r Project --output markdown --output-file project_drift.md
        """
    )
    
    parser.add_argument("-r", "--resource", required=True, help="Resource type to analyze (e.g., Project, Finding)")
    parser.add_argument("--max-instances", type=int, default=10, help="Number of instances to fetch for analysis (default: 10)")
    parser.add_argument("--endpoint", help="Override API endpoint (e.g., 'v1/namespaces/{ns}/identity-providers')")
    parser.add_argument("--output", choices=["text", "markdown"], default="text", help="Output format (default: text)")
    parser.add_argument("--output-file", help="Save markdown output to file")
    parser.add_argument("--namespace", help="Override namespace (default: from ENDOR_NAMESPACE env)")
    
    args = parser.parse_args()
    
    try:
        analyzer = DriftAnalyzer(namespace=args.namespace)
        results = analyzer.analyze_drift(
            args.resource, 
            max_instances=args.max_instances,
            endpoint_override=args.endpoint
        )
        analyzer.print_drift_analysis(
            results, 
            output_format=args.output,
            output_file=args.output_file
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
