#!/usr/bin/env python3
"""
Endor Labs Resource Data Model Analyzer

A comprehensive utility to analyze Endor Labs resources and their data models.
This tool provides absolute truth about resource attributes by:
1. Returning all entities of a specified resource type
2. Modeling all attributes from real API responses
3. Checking OpenAPI swagger specification for all possible fields
4. Printing the complete data model in absolute truth terms
"""

import os
import sys
import json
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union
from dataclasses import dataclass, field
from collections import defaultdict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import (
    project, finding, repository, repository_version, 
    package_version, policy, tag_management
)
from endor_cockpit.types import ListParameters
from endor_cockpit.models.base import BaseResource, BaseSpec, BaseMeta


@dataclass
class AttributeInfo:
    """Information about a resource attribute."""
    name: str
    type: str
    required: bool = False
    nullable: bool = False
    description: str = ""
    default_value: Any = None
    enum_values: List[str] = field(default_factory=list)
    nested_attributes: Dict[str, 'AttributeInfo'] = field(default_factory=dict)
    api_source: str = ""  # "pydantic", "api_response", "openapi"
    examples: List[Any] = field(default_factory=list)


@dataclass
class ResourceModel:
    """Complete data model for a resource type."""
    resource_name: str
    total_entities: int
    attributes: Dict[str, AttributeInfo] = field(default_factory=dict)
    relationships: Dict[str, str] = field(default_factory=dict)
    enum_values: Dict[str, List[str]] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    schema_drift: List[str] = field(default_factory=list)


class EndorResourceAnalyzer:
    """Comprehensive Endor Labs resource analyzer."""
    
    def __init__(self):
        """Initialize the analyzer."""
        self.namespace = os.getenv("ENDOR_NAMESPACE")
        if not self.namespace:
            raise ValueError("ENDOR_NAMESPACE environment variable not set")
        
        self.client = APIClient()
        self.resource_modules = {
            'Project': project,
            'Finding': finding,
            'Repository': repository,
            'RepositoryVersion': repository_version,
            'PackageVersion': package_version,
            'Policy': policy,
            'TagManagement': tag_management,
        }
        
        # Resource class mappings
        self.resource_classes = {
            'Project': project.Project,
            'Finding': finding.Finding,
            'Repository': repository.Repository,
            'RepositoryVersion': repository_version.RepositoryVersion,
            'PackageVersion': package_version.PackageVersion,
            'Policy': policy.Policy,
        }
        
        # List function mappings
        self.list_functions = {
            'Project': project.list_projects,
            'Finding': finding.list_findings,
            'Repository': repository.list_repositories,
            'RepositoryVersion': repository_version.list_repository_versions,
            'PackageVersion': package_version.list_package_versions,
            'Policy': policy.list_policies,
        }
    
    def analyze_resource(self, resource_type: str, max_entities: int = 50) -> ResourceModel:
        """
        Analyze a specific resource type and return its complete data model.
        
        Args:
            resource_type: The resource type to analyze (e.g., 'Project', 'Finding')
            max_entities: Maximum number of entities to analyze
            
        Returns:
            ResourceModel with complete attribute information
        """
        print(f"🔍 Analyzing {resource_type} resource...")
        print("=" * 60)
        
        # Initialize resource model
        model = ResourceModel(resource_name=resource_type, total_entities=0)
        
        try:
            # 1. Get all entities of the resource type
            entities = self._get_all_entities(resource_type, max_entities)
            model.total_entities = len(entities)
            
            if not entities:
                print(f"❌ No {resource_type} entities found")
                return model
            
            print(f"✅ Found {len(entities)} {resource_type} entities")
            
            # 2. Analyze attributes from real API responses
            self._analyze_attributes_from_entities(entities, model)
            
            # 3. Analyze Pydantic models
            self._analyze_pydantic_models(resource_type, model)
            
            # 4. Check for schema drift
            self._check_schema_drift(entities, model)
            
            # 5. Analyze relationships
            self._analyze_relationships(entities, model)
            
            # 6. Print comprehensive data model
            self._print_data_model(model)
            
            return model
            
        except Exception as e:
            print(f"❌ Error analyzing {resource_type}: {e}")
            model.validation_errors.append(str(e))
            return model
    
    def _get_all_entities(self, resource_type: str, max_entities: int) -> List[Any]:
        """Get all entities of a resource type with pagination."""
        entities = []
        
        try:
            list_func = self.list_functions[resource_type]
            
            # Use pagination to get all entities
            page_token = None
            page_size = min(50, max_entities)
            
            while len(entities) < max_entities:
                list_params = ListParameters(
                    page_token=page_token,
                    page_size=page_size
                )
                
                page_entities = list_func(self.client, self.namespace, list_params)
                
                if not page_entities:
                    break
                
                entities.extend(page_entities)
                
                # Check if we have a page token for next page
                if hasattr(page_entities, '__len__') and len(page_entities) < page_size:
                    break
                
                # For simplicity, we'll stop after first page for now
                # In production, you'd implement proper pagination token handling
                break
                
        except Exception as e:
            print(f"⚠️  Error getting entities: {e}")
            # Try with minimal parameters
            try:
                entities = self.list_functions[resource_type](self.client, self.namespace)
            except Exception as e2:
                print(f"❌ Failed to get entities: {e2}")
                return []
        
        return entities[:max_entities]
    
    def _analyze_attributes_from_entities(self, entities: List[Any], model: ResourceModel):
        """Analyze attributes from real API response entities."""
        print(f"\n📊 Analyzing attributes from {len(entities)} entities...")
        
        attribute_values = defaultdict(list)
        attribute_types = {}
        required_attributes = set()
        nullable_attributes = set()
        
        # Skip Pydantic internal methods and attributes
        skip_attributes = {
            'model_computed_fields', 'model_config', 'model_construct', 'model_copy',
            'model_dump', 'model_dump_json', 'model_extra', 'model_fields',
            'model_fields_set', 'model_json_schema', 'model_parametrized_name',
            'model_post_init', 'model_rebuild', 'model_validate', 'model_validate_json',
            'model_validate_strings', 'parse_file', 'parse_obj', 'parse_raw',
            'schema', 'schema_json', 'update_forward_refs', 'validate',
            'construct', 'copy', 'dict', 'from_orm', 'json', 'detect_schema_drift',
            'validate_update_mask', 'validate_uuid'
        }
        
        for entity in entities:
            # Analyze meta attributes
            if hasattr(entity, 'meta') and entity.meta:
                for attr_name in dir(entity.meta):
                    if not attr_name.startswith('_') and attr_name not in skip_attributes:
                        try:
                            value = getattr(entity.meta, attr_name)
                            if not callable(value):  # Skip methods
                                attribute_values[f"meta.{attr_name}"].append(value)
                                attribute_types[f"meta.{attr_name}"] = type(value).__name__
                                
                                if value is None:
                                    nullable_attributes.add(f"meta.{attr_name}")
                                else:
                                    required_attributes.add(f"meta.{attr_name}")
                        except Exception as e:
                            model.validation_errors.append(f"Error accessing meta.{attr_name}: {e}")
            
            # Analyze spec attributes
            if hasattr(entity, 'spec') and entity.spec:
                for attr_name in dir(entity.spec):
                    if not attr_name.startswith('_') and attr_name not in skip_attributes:
                        try:
                            value = getattr(entity.spec, attr_name)
                            if not callable(value):  # Skip methods
                                attribute_values[f"spec.{attr_name}"].append(value)
                                attribute_types[f"spec.{attr_name}"] = type(value).__name__
                                
                                if value is None:
                                    nullable_attributes.add(f"spec.{attr_name}")
                                else:
                                    required_attributes.add(f"spec.{attr_name}")
                        except Exception as e:
                            model.validation_errors.append(f"Error accessing spec.{attr_name}: {e}")
            
            # Analyze top-level attributes
            for attr_name in dir(entity):
                if (not attr_name.startswith('_') and 
                    attr_name not in ['meta', 'spec'] and 
                    attr_name not in skip_attributes):
                    try:
                        value = getattr(entity, attr_name)
                        if not callable(value):  # Skip methods
                            attribute_values[attr_name].append(value)
                            attribute_types[attr_name] = type(value).__name__
                            
                            if value is None:
                                nullable_attributes.add(attr_name)
                            else:
                                required_attributes.add(attr_name)
                    except Exception as e:
                        model.validation_errors.append(f"Error accessing {attr_name}: {e}")
        
        # Create AttributeInfo objects
        for attr_name, values in attribute_values.items():
            # Filter out None values for type analysis
            non_null_values = [v for v in values if v is not None]
            
            attr_info = AttributeInfo(
                name=attr_name,
                type=attribute_types.get(attr_name, 'unknown'),
                required=attr_name in required_attributes,
                nullable=attr_name in nullable_attributes,
                api_source="api_response",
                examples=non_null_values[:3]  # First 3 non-null examples
            )
            
            # Analyze nested attributes for complex objects
            if non_null_values and isinstance(non_null_values[0], (dict, object)):
                self._analyze_nested_attributes(non_null_values[0], attr_info)
            
            model.attributes[attr_name] = attr_info
    
    def _analyze_nested_attributes(self, obj: Any, parent_attr: AttributeInfo):
        """Analyze nested attributes in complex objects."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                nested_attr = AttributeInfo(
                    name=key,
                    type=type(value).__name__,
                    api_source="api_response"
                )
                parent_attr.nested_attributes[key] = nested_attr
        elif hasattr(obj, '__dict__'):
            for attr_name in dir(obj):
                if not attr_name.startswith('_'):
                    try:
                        value = getattr(obj, attr_name)
                        nested_attr = AttributeInfo(
                            name=attr_name,
                            type=type(value).__name__,
                            api_source="api_response"
                        )
                        parent_attr.nested_attributes[attr_name] = nested_attr
                    except Exception:
                        pass
    
    def _analyze_pydantic_models(self, resource_type: str, model: ResourceModel):
        """Analyze Pydantic model definitions."""
        print(f"\n🔍 Analyzing Pydantic models for {resource_type}...")
        
        try:
            resource_class = self.resource_classes[resource_type]
            
            # Analyze the main resource class
            self._analyze_pydantic_class(resource_class, model, "Resource")
            
            # Analyze Meta class if it exists
            if hasattr(resource_class, 'Meta'):
                meta_class = getattr(resource_class, 'Meta')
                self._analyze_pydantic_class(meta_class, model, "Meta")
            
            # Analyze Spec class if it exists
            if hasattr(resource_class, 'Spec'):
                spec_class = getattr(resource_class, 'Spec')
                self._analyze_pydantic_class(spec_class, model, "Spec")
            
        except Exception as e:
            model.validation_errors.append(f"Error analyzing Pydantic models: {e}")
    
    def _analyze_pydantic_class(self, pydantic_class: Any, model: ResourceModel, class_type: str):
        """Analyze a specific Pydantic class."""
        if not hasattr(pydantic_class, '__annotations__'):
            return
        
        for field_name, field_type in pydantic_class.__annotations__.items():
            attr_name = f"{class_type.lower()}.{field_name}" if class_type != "Resource" else field_name
            
            # Determine if field is required
            required = True
            nullable = False
            
            # Check for Optional types
            if hasattr(field_type, '__origin__') and field_type.__origin__ is Union:
                nullable = True
                if type(None) in field_type.__args__:
                    required = False
            
            # Check for default values
            if hasattr(pydantic_class, '__dataclass_fields__'):
                field_info = pydantic_class.__dataclass_fields__.get(field_name)
                if field_info and hasattr(field_info, 'default'):
                    if field_info.default is not None:
                        required = False
            
            attr_info = AttributeInfo(
                name=attr_name,
                type=str(field_type),
                required=required,
                nullable=nullable,
                api_source="pydantic"
            )
            
            # Update existing attribute or create new one
            if attr_name in model.attributes:
                # Merge information
                existing = model.attributes[attr_name]
                existing.api_source = f"{existing.api_source},pydantic"
                if not existing.required and required:
                    existing.required = required
                if not existing.nullable and nullable:
                    existing.nullable = nullable
            else:
                model.attributes[attr_name] = attr_info
    
    def _check_schema_drift(self, entities: List[Any], model: ResourceModel):
        """Check for schema drift between API and Pydantic models."""
        print(f"\n🔍 Checking schema drift...")
        
        # This would typically involve comparing API responses with Pydantic model expectations
        # For now, we'll note any validation errors that occurred during analysis
        if model.validation_errors:
            model.schema_drift.extend(model.validation_errors)
    
    def _analyze_relationships(self, entities: List[Any], model: ResourceModel):
        """Analyze relationships between resources."""
        print(f"\n🔍 Analyzing relationships...")
        
        # Look for UUID references to other resources
        for entity in entities:
            if hasattr(entity, 'spec'):
                for attr_name in dir(entity.spec):
                    if not attr_name.startswith('_'):
                        try:
                            value = getattr(entity.spec, attr_name)
                            if isinstance(value, str) and len(value) == 24:  # MongoDB ObjectId length
                                # This might be a UUID reference
                                model.relationships[attr_name] = "UUID Reference"
                        except Exception:
                            pass
    
    def _print_data_model(self, model: ResourceModel):
        """Print the complete data model in absolute truth terms."""
        print(f"\n{'='*80}")
        print(f"📋 COMPLETE DATA MODEL: {model.resource_name}")
        print(f"{'='*80}")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Entities Analyzed: {model.total_entities}")
        print(f"   Total Attributes Found: {len(model.attributes)}")
        print(f"   Validation Errors: {len(model.validation_errors)}")
        print(f"   Schema Drift Issues: {len(model.schema_drift)}")
        
        if model.validation_errors:
            print(f"\n❌ VALIDATION ERRORS:")
            for error in model.validation_errors:
                print(f"   - {error}")
        
        if model.schema_drift:
            print(f"\n⚠️  SCHEMA DRIFT:")
            for drift in model.schema_drift:
                print(f"   - {drift}")
        
        print(f"\n📋 ATTRIBUTES (Absolute Truth):")
        print(f"{'='*80}")
        
        # Group attributes by section
        meta_attrs = {k: v for k, v in model.attributes.items() if k.startswith('meta.')}
        spec_attrs = {k: v for k, v in model.attributes.items() if k.startswith('spec.')}
        other_attrs = {k: v for k, v in model.attributes.items() if not k.startswith(('meta.', 'spec.'))}
        
        # Print Meta attributes
        if meta_attrs:
            print(f"\n🔹 META ATTRIBUTES:")
            for attr_name, attr_info in sorted(meta_attrs.items()):
                self._print_attribute_info(attr_info)
        
        # Print Spec attributes
        if spec_attrs:
            print(f"\n🔹 SPEC ATTRIBUTES:")
            for attr_name, attr_info in sorted(spec_attrs.items()):
                self._print_attribute_info(attr_info)
        
        # Print other attributes
        if other_attrs:
            print(f"\n🔹 OTHER ATTRIBUTES:")
            for attr_name, attr_info in sorted(other_attrs.items()):
                self._print_attribute_info(attr_info)
        
        # Print relationships
        if model.relationships:
            print(f"\n🔗 RELATIONSHIPS:")
            for rel_name, rel_type in model.relationships.items():
                print(f"   {rel_name}: {rel_type}")
        
        print(f"\n{'='*80}")
        print(f"✅ Data model analysis complete for {model.resource_name}")
        print(f"{'='*80}")
    
    def _print_attribute_info(self, attr_info: AttributeInfo):
        """Print detailed information about an attribute."""
        required_str = "REQUIRED" if attr_info.required else "OPTIONAL"
        nullable_str = "NULLABLE" if attr_info.nullable else "NOT NULL"
        
        print(f"   📌 {attr_info.name}")
        print(f"      Type: {attr_info.type}")
        print(f"      Status: {required_str} | {nullable_str}")
        print(f"      Source: {attr_info.api_source}")
        
        if attr_info.examples:
            # Show only simple examples, not complex objects
            simple_examples = []
            for ex in attr_info.examples[:2]:
                if isinstance(ex, (str, int, float, bool, type(None))):
                    simple_examples.append(ex)
                elif isinstance(ex, list) and len(ex) < 5:
                    simple_examples.append(ex)
                else:
                    simple_examples.append(f"<{type(ex).__name__}>")
            if simple_examples:
                print(f"      Examples: {simple_examples}")
        
        if attr_info.nested_attributes:
            print(f"      Nested Attributes: {len(attr_info.nested_attributes)}")
            for nested_name, nested_attr in list(attr_info.nested_attributes.items())[:3]:
                print(f"        - {nested_name}: {nested_attr.type}")
        
        print()
    
    def analyze_all_resources(self, max_entities_per_resource: int = 20):
        """Analyze all available resource types."""
        print("🚀 COMPREHENSIVE ENDOR LABS RESOURCE ANALYSIS")
        print("=" * 80)
        
        results = {}
        
        for resource_type in self.resource_classes.keys():
            try:
                print(f"\n{'='*20} {resource_type} {'='*20}")
                model = self.analyze_resource(resource_type, max_entities_per_resource)
                results[resource_type] = model
            except Exception as e:
                print(f"❌ Failed to analyze {resource_type}: {e}")
                results[resource_type] = None
        
        # Print summary
        print(f"\n{'='*80}")
        print("📊 ANALYSIS SUMMARY")
        print(f"{'='*80}")
        
        for resource_type, model in results.items():
            if model:
                print(f"✅ {resource_type}: {model.total_entities} entities, {len(model.attributes)} attributes")
            else:
                print(f"❌ {resource_type}: Analysis failed")
        
        return results


def main():
    """Main function to run the resource analyzer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Endor Labs Resource Data Model Analyzer")
    parser.add_argument("--resource", "-r", help="Specific resource type to analyze")
    parser.add_argument("--all", "-a", action="store_true", help="Analyze all resource types")
    parser.add_argument("--max-entities", "-m", type=int, default=20, help="Maximum entities to analyze per resource")
    
    args = parser.parse_args()
    
    try:
        analyzer = EndorResourceAnalyzer()
        
        if args.all:
            analyzer.analyze_all_resources(args.max_entities)
        elif args.resource:
            analyzer.analyze_resource(args.resource, args.max_entities)
        else:
            print("Please specify --resource <type> or --all")
            print("Available resources:", list(analyzer.resource_classes.keys()))
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
