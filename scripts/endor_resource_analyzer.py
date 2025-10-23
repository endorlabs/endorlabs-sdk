#!/usr/bin/env python3
"""
Endor Labs Resource Data Model Analyzer - Simplified Version

A simplified utility to analyze Endor Labs resources using closest match endpoint discovery.
This tool finds the closest matching endpoint for a given resource type using Levenshtein distance.
"""

import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set, Union

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import (
    finding,
    package_version,
    policy,
    project,
    repository,
    repository_version,
)
from endor_cockpit.types import ListParameters
from endor_cockpit.utils.model_validation import (
    get_immutable_fields,
    get_mutable_fields,
    safe_serialize,
)
from endor_cockpit.utils.schema_drift import SchemaDriftDetector


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_closest_endpoint_match(target_resource: str, available_endpoints: List[str]) -> tuple[str, int]:
    """Find the closest endpoint match using Levenshtein distance."""
    if not available_endpoints:
        return target_resource, 0

    min_distance = float('inf')
    closest_endpoint = target_resource

    for endpoint in available_endpoints:
        distance = levenshtein_distance(target_resource, endpoint)
        if distance < min_distance:
            min_distance = distance
            closest_endpoint = endpoint

    return closest_endpoint, int(min_distance)


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
    nested_attributes: Dict[str, "AttributeInfo"] = field(default_factory=dict)
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
    """Endor Labs resource analyzer with simplified endpoint matching and comprehensive analysis."""

    def __init__(self, enable_raw_api: bool = True):
        """Initialize the analyzer."""
        self.namespace = os.getenv("ENDOR_NAMESPACE")
        if not self.namespace:
            raise ValueError("ENDOR_NAMESPACE environment variable not set")

        self.client = APIClient()
        self.enable_raw_api = enable_raw_api

        # SDK resource mappings (for known resources)
        self.resource_modules = {
            "Project": project,
            "Finding": finding,
            "Repository": repository,
            "RepositoryVersion": repository_version,
            "PackageVersion": package_version,
            "Policy": policy,
        }

        # Resource class mappings
        self.resource_classes = {
            "Project": project.Project,
            "Finding": finding.Finding,
            "Repository": repository.Repository,
            "RepositoryVersion": repository_version.RepositoryVersion,
            "PackageVersion": package_version.PackageVersion,
            "Policy": policy.Policy,
        }

        # List function mappings
        self.list_functions = {
            "Project": project.list_projects,
            "Finding": finding.list_findings,
            "Repository": repository.list_repositories,
            "RepositoryVersion": repository_version.list_repository_versions,
            "PackageVersion": package_version.list_package_versions,
            "Policy": policy.list_policies,
        }

        # Raw API resource discovery
        self.discovered_resources = set()
        self.raw_api_resources = {}

        # Load OpenAPI endpoints and schemas for matching
        self.openapi_endpoints = self._load_openapi_endpoints()
        self.openapi_schemas = self._load_openapi_schemas()

    def _load_openapi_endpoints(self) -> List[str]:
        """Load all valid endpoints from OpenAPI specification."""
        import json
        from pathlib import Path

        openapi_file = Path(__file__).parent.parent.parent.parent / "external_docs/openapi-swagger.json"
        if not openapi_file.exists():
            print("⚠️  OpenAPI spec not found, using fallback endpoint patterns")
            return []

        try:
            with open(openapi_file, 'r') as f:
                spec = json.load(f)

            endpoints = []
            paths = spec.get("paths", {})

            for path in paths:
                # Extract resource names from paths like /v1/namespaces/{...}/resource-name
                if "/v1/namespaces/" in path and path.count("/") >= 4:
                    # Extract the last part after the last slash
                    resource_name = path.split("/")[-1]
                    if resource_name and not resource_name.startswith("{"):
                        endpoints.append(resource_name)

            # Remove duplicates and sort
            endpoints = sorted(list(set(endpoints)))
            print(f"📋 Loaded {len(endpoints)} OpenAPI endpoints for matching")
            return endpoints

        except Exception as e:
            print(f"⚠️  Error loading OpenAPI spec: {e}")
            return []

    def _load_openapi_schemas(self) -> dict:
        """Load OpenAPI schemas from the specification."""
        import json
        from pathlib import Path

        openapi_file = Path(__file__).parent.parent.parent.parent / "external_docs/openapi-swagger.json"
        if not openapi_file.exists():
            return {}

        try:
            with open(openapi_file, 'r') as f:
                spec = json.load(f)

            schemas = spec.get("components", {}).get("schemas", {})
            print(f"✅ Loaded {len(schemas)} OpenAPI schemas")
            return schemas
        except Exception as e:
            print(f"❌ Error loading OpenAPI schemas: {e}")
            return {}

    def find_closest_endpoint(self, resource_type: str) -> tuple[str, int]:
        """Find the closest matching endpoint for a resource type."""
        print(f"🔍 Finding closest endpoint match for: {resource_type}")

        if not self.openapi_endpoints:
            # Fallback to simple pattern
            fallback_endpoint = f"v1/namespaces/{self.namespace}/{resource_type.lower()}"
            print(f"⚠️  No OpenAPI endpoints available, using fallback: {fallback_endpoint}")
            return fallback_endpoint, 0

        # Find closest match using Levenshtein distance
        closest_endpoint, distance = find_closest_endpoint_match(
            resource_type.lower(), self.openapi_endpoints
        )

        # Construct full endpoint URL
        full_endpoint = f"v1/namespaces/{self.namespace}/{closest_endpoint}"

        print(f"📊 Closest match: {closest_endpoint} (distance: {distance})")
        print(f"🔗 Full endpoint: {full_endpoint}")

        return full_endpoint, distance

    def test_endpoint(self, endpoint: str) -> bool:
        """Test if an endpoint is accessible."""
        try:
            response = self.client.get(endpoint)
            return response.status_code == 200
        except Exception:
            return False

    def analyze_resource(
        self, resource_type: str, max_entities: int = 50, use_raw_api: bool = False
    ) -> ResourceModel:
        """
        Analyze a specific resource type and return its complete data model.

        Args:
            resource_type: The resource type to analyze (e.g., 'Project', 'Finding')
            max_entities: Maximum number of entities to analyze
            use_raw_api: Force use of raw API instead of SDK

        Returns:
            ResourceModel with complete attribute information
        """
        print(f"🔍 Analyzing {resource_type} resource...")
        print("=" * 60)

        # Check if resource is in SDK or needs raw API
        if use_raw_api or resource_type not in self.resource_classes:
            print(f"📡 Using raw API for unmapped resource: {resource_type}")
            return self.analyze_unmapped_resource(resource_type, max_entities)

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

    def analyze_unmapped_resource(
        self, resource_type: str, max_entities: int = 50
    ) -> ResourceModel:
        """Analyze a resource type that's not in the SDK using raw API calls."""
        print(f"🔍 Analyzing unmapped resource: {resource_type}")
        print("=" * 60)

        # Initialize resource model
        model = ResourceModel(resource_name=resource_type, total_entities=0)

        try:
            # Get entities using raw API with simplified endpoint matching
            entities = self._get_raw_api_entities(resource_type, max_entities)
            model.total_entities = len(entities)

            if not entities:
                print(f"❌ No {resource_type} entities found")
                return model

            print(f"✅ Found {len(entities)} {resource_type} entities")

            # Analyze attributes from raw JSON data
            self._analyze_raw_json_attributes(entities, model)

            # Check for relationships in raw data
            self._analyze_raw_relationships(entities, model)

            # Integrate with API spec for enhanced analysis
            self._integrate_api_spec(model)

            # Print comprehensive data model
            self._print_data_model(model)

            return model

        except Exception as e:
            print(f"❌ Error analyzing {resource_type}: {e}")
            model.validation_errors.append(str(e))
            return model

    def _get_raw_api_entities(
        self, resource_type: str, max_entities: int
    ) -> List[Dict]:
        """Get entities using raw API calls with simplified endpoint matching."""
        entities = []

        try:
            # Use simplified endpoint matching
            endpoint, distance = self.find_closest_endpoint(resource_type)

            print(f"   🔍 Using endpoint: {endpoint}")
            print(f"   📊 Levenshtein distance: {distance}")

            response = self.client.get(endpoint)
            print(f"   📊 Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                # Handle response format (following SDK pattern)
                if "list" in data and "objects" in data["list"]:
                    entities = data["list"]["objects"]
                    print(f"   ✅ Found {len(entities)} entities in list.objects")
                elif isinstance(data, list):
                    entities = data
                    print(f"   ✅ Found {len(entities)} entities in direct list")
                elif "resources" in data:
                    entities = data["resources"]
                    print(f"   ✅ Found {len(entities)} entities in resources")
                elif "data" in data:
                    entities = data["data"]
                    print(f"   ✅ Found {len(entities)} entities in data")
                else:
                    entities = [data]
                    print("   ✅ Found 1 entity in root object")
            else:
                print(f"   ❌ Request failed with status {response.status_code}")
                if hasattr(response, "text"):
                    print(f"   📄 Response text: {response.text[:200]}...")

            if not entities:
                print(f"❌ No entities found for {resource_type}")
                return []

            # Limit to max_entities
            return entities[:max_entities]

        except Exception as e:
            print(f"❌ Error getting raw API entities: {e}")
            return []

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
                    page_size=page_size,
                    filter=None,
                    mask=None,
                    sort_field=None,
                    sort_order=None,
                    count=None,
                    include_child_namespaces=None,
                    from_date=None,
                    to_date=None,
                )

                page_entities = list_func(self.client, self.namespace, list_params)

                if not page_entities:
                    break

                entities.extend(page_entities)

                # Check if we have a page token for next page
                if hasattr(page_entities, "__len__") and len(page_entities) < page_size:
                    break

                # For simplicity, we'll stop after first page for now
                # In production, you'd implement proper pagination token handling
                break

        except Exception as e:
            print(f"⚠️  Error getting entities: {e}")
            # Try with minimal parameters
            try:
                entities = self.list_functions[resource_type](
                    self.client, self.namespace
                )
            except Exception as e2:
                print(f"❌ Failed to get entities: {e2}")
                return []

        return entities[:max_entities]

    def _analyze_raw_json_attributes(self, entities: List[Dict], model: ResourceModel):
        """Analyze attributes from raw JSON entities using existing validation utilities."""
        print(f"\n📊 Analyzing attributes from {len(entities)} raw JSON entities...")

        attribute_values = defaultdict(list)
        attribute_types = {}
        required_attributes = set()
        nullable_attributes = set()

        for entity in entities:
            try:
                # Use existing safe serialization for consistent handling
                serialized_entity = safe_serialize(entity)

                # Recursively analyze JSON structure
                self._analyze_json_object(
                    serialized_entity,
                    "",
                    attribute_values,
                    attribute_types,
                    required_attributes,
                    nullable_attributes,
                )
            except Exception as e:
                model.validation_errors.append(f"Entity serialization error: {e}")

        # Create AttributeInfo objects with enhanced mutability analysis
        resource_type = model.resource_name.lower()
        mutable_fields = get_mutable_fields(resource_type)
        immutable_fields = get_immutable_fields(resource_type)

        for attr_name, values in attribute_values.items():
            # Filter out None values for type analysis
            non_null_values = [v for v in values if v is not None]

            # Determine mutability using existing utilities
            is_mutable = attr_name in mutable_fields
            is_immutable = attr_name in immutable_fields

            attr_info = AttributeInfo(
                name=attr_name,
                type=attribute_types.get(attr_name, "unknown"),
                required=attr_name in required_attributes,
                nullable=attr_name in nullable_attributes,
                api_source="raw_api",
                examples=non_null_values[:3],  # First 3 non-null examples
            )

            # Add mutability information from existing utilities
            if is_mutable:
                attr_info.description += " [MUTABLE]"
            elif is_immutable:
                attr_info.description += " [IMMUTABLE]"

            # Analyze nested attributes for complex objects
            if non_null_values and isinstance(non_null_values[0], (dict, list)):
                self._analyze_nested_attributes(non_null_values[0], attr_info)

            model.attributes[attr_name] = attr_info

    def _analyze_json_object(
        self,
        obj: Any,
        prefix: str,
        attribute_values: Dict,
        attribute_types: Dict,
        required_attributes: Set,
        nullable_attributes: Set,
    ):
        """Recursively analyze JSON object structure."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key

                attribute_values[full_key].append(value)
                attribute_types[full_key] = type(value).__name__

                if value is None:
                    nullable_attributes.add(full_key)
                else:
                    required_attributes.add(full_key)

                # Recursively analyze nested objects
                if isinstance(value, (dict, list)):
                    self._analyze_json_object(
                        value,
                        full_key,
                        attribute_values,
                        attribute_types,
                        required_attributes,
                        nullable_attributes,
                    )

        elif isinstance(obj, list) and obj:
            # Analyze first item in list to understand structure
            self._analyze_json_object(
                obj[0],
                f"{prefix}[0]",
                attribute_values,
                attribute_types,
                required_attributes,
                nullable_attributes,
            )

    def _analyze_raw_relationships(self, entities: List[Dict], model: ResourceModel):
        """Analyze relationships in raw JSON data."""
        print("\n🔍 Analyzing relationships in raw data...")

        # Look for UUID patterns and common relationship fields
        uuid_pattern = r"^[0-9a-f]{24}$"  # MongoDB ObjectId pattern
        relationship_fields = [
            "uuid",
            "id",
            "parent_uuid",
            "project_uuid",
            "repository_uuid",
            "target_uuid",
            "source_uuid",
            "related_uuid",
            "owner_uuid",
            "created_by",
            "updated_by",
            "assigned_to",
            "user_uuid",
        ]

        for entity in entities:
            self._find_relationships_in_object(
                entity, "", model, uuid_pattern, relationship_fields
            )

    def _find_relationships_in_object(
        self,
        obj: Any,
        prefix: str,
        model: ResourceModel,
        uuid_pattern: str,
        relationship_fields: List[str],
    ):
        """Find relationship patterns in JSON object."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key

                # Check if this looks like a relationship field
                if key.lower() in relationship_fields or (
                    isinstance(value, str) and re.match(uuid_pattern, value)
                ):
                    model.relationships[full_key] = "UUID Reference"

                # Recursively check nested objects
                if isinstance(value, (dict, list)):
                    self._find_relationships_in_object(
                        value, full_key, model, uuid_pattern, relationship_fields
                    )

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._find_relationships_in_object(
                    item, f"{prefix}[{i}]", model, uuid_pattern, relationship_fields
                )

    def _analyze_attributes_from_entities(
        self, entities: List[Any], model: ResourceModel
    ):
        """Analyze attributes from real API response entities."""
        print(f"\n📊 Analyzing attributes from {len(entities)} entities...")

        attribute_values = defaultdict(list)
        attribute_types = {}
        required_attributes = set()
        nullable_attributes = set()

        skip_attributes = self._get_skip_attributes()

        for entity in entities:
            self._analyze_entity_attributes(
                entity, skip_attributes, attribute_values,
                attribute_types, required_attributes, nullable_attributes, model
            )

        self._create_attribute_info_objects(
            attribute_values, attribute_types, required_attributes,
            nullable_attributes, model
        )

    def _get_skip_attributes(self) -> set:
        """Get set of Pydantic internal methods and attributes to skip."""
        return {
            "model_computed_fields",
            "model_config",
            "model_construct",
            "model_copy",
            "model_dump",
            "model_dump_json",
            "model_extra",
            "model_fields",
            "model_fields_set",
            "model_json_schema",
            "model_parametrized_name",
            "model_post_init",
            "model_rebuild",
            "model_validate",
            "model_validate_json",
            "model_validate_strings",
            "parse_file",
            "parse_obj",
            "parse_raw",
            "schema",
            "schema_json",
            "update_forward_refs",
            "validate",
            "construct",
            "copy",
            "dict",
            "from_orm",
            "json",
            "detect_schema_drift",
            "validate_update_mask",
            "validate_uuid",
        }

    def _analyze_entity_attributes(
        self, entity: Any, skip_attributes: set, attribute_values: dict,
        attribute_types: dict, required_attributes: set,
        nullable_attributes: set, model: ResourceModel
    ):
        """Analyze attributes for a single entity using class-based field access."""
        # Analyze meta attributes
        if hasattr(entity, "meta") and entity.meta:
            self._analyze_section_attributes(
                entity.meta, "meta", skip_attributes, attribute_values,
                attribute_types, required_attributes, nullable_attributes, model
            )

        # Analyze spec attributes
        if hasattr(entity, "spec") and entity.spec:
            self._analyze_section_attributes(
                entity.spec, "spec", skip_attributes, attribute_values,
                attribute_types, required_attributes, nullable_attributes, model
            )

        # Analyze top-level attributes using class-based field access
        self._analyze_top_level_attributes(
            entity, skip_attributes, attribute_values, attribute_types,
            required_attributes, nullable_attributes, model
        )

    def _analyze_section_attributes(
        self, section_obj: Any, section_name: str, skip_attributes: set,
        attribute_values: dict, attribute_types: dict, required_attributes: set,
        nullable_attributes: set, model: ResourceModel
    ):
        """Analyze attributes in a specific section (meta/spec) using safe field access."""
        # Use model_dump() for Pydantic models to avoid deprecation warnings
        if hasattr(section_obj, 'model_dump'):
            try:
                section_dict = section_obj.model_dump()
                for attr_name, value in section_dict.items():
                    if attr_name not in skip_attributes:
                        full_attr_name = f"{section_name}.{attr_name}"
                        attribute_values[full_attr_name].append(value)
                        attribute_types[full_attr_name] = type(value).__name__

                        if value is None:
                            nullable_attributes.add(full_attr_name)
                        else:
                            required_attributes.add(full_attr_name)
            except Exception as e:
                model.validation_errors.append(f"Error serializing {section_name}: {e}")
        else:
            # Fallback to dir() for non-Pydantic objects
            for attr_name in dir(section_obj):
                if (
                    not attr_name.startswith("_")
                    and attr_name not in skip_attributes
                ):
                    try:
                        value = getattr(section_obj, attr_name)
                        if not callable(value):  # Skip methods
                            full_attr_name = f"{section_name}.{attr_name}"
                            attribute_values[full_attr_name].append(value)
                            attribute_types[full_attr_name] = type(value).__name__

                            if value is None:
                                nullable_attributes.add(full_attr_name)
                            else:
                                required_attributes.add(full_attr_name)
                    except Exception as e:
                        model.validation_errors.append(
                            f"Error accessing {section_name}.{attr_name}: {e}"
                        )

    def _analyze_top_level_attributes(
        self, entity: Any, skip_attributes: set, attribute_values: dict,
        attribute_types: dict, required_attributes: set,
        nullable_attributes: set, model: ResourceModel
    ):
        """Analyze top-level attributes of an entity using safe field access."""
        # Use model_dump() for Pydantic models to avoid deprecation warnings
        if hasattr(entity, 'model_dump'):
            try:
                entity_dict = entity.model_dump()
                for attr_name, value in entity_dict.items():
                    if (
                        attr_name not in ["meta", "spec"]
                        and attr_name not in skip_attributes
                    ):
                        attribute_values[attr_name].append(value)
                        attribute_types[attr_name] = type(value).__name__

                        if value is None:
                            nullable_attributes.add(attr_name)
                        else:
                            required_attributes.add(attr_name)
            except Exception as e:
                model.validation_errors.append(f"Error serializing entity: {e}")
        else:
            # Fallback to dir() for non-Pydantic objects
            for attr_name in dir(entity):
                if (
                    not attr_name.startswith("_")
                    and attr_name not in ["meta", "spec"]
                    and attr_name not in skip_attributes
                ):
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
                        model.validation_errors.append(
                            f"Error accessing {attr_name}: {e}"
                        )

    def _create_attribute_info_objects(
        self, attribute_values: dict, attribute_types: dict,
        required_attributes: set, nullable_attributes: set, model: ResourceModel
    ):
        """Create AttributeInfo objects from analyzed attributes using existing utilities."""

        # Get mutability information using existing utilities
        resource_type = model.resource_name.lower()
        mutable_fields = get_mutable_fields(resource_type)
        immutable_fields = get_immutable_fields(resource_type)

        for attr_name, values in attribute_values.items():
            # Filter out None values for type analysis
            non_null_values = [v for v in values if v is not None]

            # Determine mutability using existing utilities
            is_mutable = attr_name in mutable_fields
            is_immutable = attr_name in immutable_fields

            attr_info = AttributeInfo(
                name=attr_name,
                type=attribute_types.get(attr_name, "unknown"),
                required=attr_name in required_attributes,
                nullable=attr_name in nullable_attributes,
                api_source="api_response",
                examples=non_null_values[:3],  # First 3 non-null examples
            )

            # Add mutability information from existing utilities
            if is_mutable:
                attr_info.description += " [MUTABLE]"
            elif is_immutable:
                attr_info.description += " [IMMUTABLE]"

            # Analyze nested attributes for complex objects
            if non_null_values and isinstance(non_null_values[0], (dict, object)):
                self._analyze_nested_attributes(non_null_values[0], attr_info)

            model.attributes[attr_name] = attr_info

    def _analyze_nested_attributes(self, obj: Any, parent_attr: AttributeInfo):
        """Analyze nested attributes in complex objects."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                nested_attr = AttributeInfo(
                    name=key, type=type(value).__name__, api_source="api_response"
                )
                parent_attr.nested_attributes[key] = nested_attr
        elif hasattr(obj, "__dict__"):
            for attr_name in dir(obj):
                if not attr_name.startswith("_"):
                    try:
                        value = getattr(obj, attr_name)
                        nested_attr = AttributeInfo(
                            name=attr_name,
                            type=type(value).__name__,
                            api_source="api_response",
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
            if hasattr(resource_class, "Meta"):
                meta_class = resource_class.Meta
                self._analyze_pydantic_class(meta_class, model, "Meta")

            # Analyze Spec class if it exists
            if hasattr(resource_class, "Spec"):
                spec_class = resource_class.Spec
                self._analyze_pydantic_class(spec_class, model, "Spec")

        except Exception as e:
            model.validation_errors.append(f"Error analyzing Pydantic models: {e}")

    def _analyze_pydantic_class(
        self, pydantic_class: Any, model: ResourceModel, class_type: str
    ):
        """Analyze a specific Pydantic class using safe field access."""
        if not hasattr(pydantic_class, "__annotations__"):
            return

        try:
            for field_name, field_type in pydantic_class.__annotations__.items():
                attr_name = self._get_attribute_name(field_name, class_type)
                required, nullable = self._determine_field_properties(
                    field_type, pydantic_class, field_name
                )

                attr_info = AttributeInfo(
                    name=attr_name,
                    type=str(field_type),
                    required=required,
                    nullable=nullable,
                    api_source="pydantic",
                )

                self._update_or_create_attribute(attr_name, attr_info, model)
        except Exception as e:
            model.validation_errors.append(f"Error analyzing Pydantic class {class_type}: {e}")

    def _get_attribute_name(self, field_name: str, class_type: str) -> str:
        """Get the attribute name based on field name and class type."""
        return (
            f"{class_type.lower()}.{field_name}"
            if class_type != "Resource"
            else field_name
        )

    def _determine_field_properties(
        self, field_type: Any, pydantic_class: Any, field_name: str
    ) -> tuple[bool, bool]:
        """Determine if a field is required and nullable."""
        required = True
        nullable = False

        # Check for Optional types
        if hasattr(field_type, "__origin__") and field_type.__origin__ is Union:
            nullable = True
            if type(None) in field_type.__args__:
                required = False

        # Check for default values
        if hasattr(pydantic_class, "__dataclass_fields__"):
            field_info = pydantic_class.__dataclass_fields__.get(field_name)
            if field_info and hasattr(field_info, "default"):
                if field_info.default is not None:
                    required = False

        return required, nullable

    def _update_or_create_attribute(
        self, attr_name: str, attr_info: AttributeInfo, model: ResourceModel
    ):
        """Update existing attribute or create new one."""
        if attr_name in model.attributes:
            # Merge information
            existing = model.attributes[attr_name]
            existing.api_source = f"{existing.api_source},pydantic"
            if not existing.required and attr_info.required:
                existing.required = attr_info.required
            if not existing.nullable and attr_info.nullable:
                existing.nullable = attr_info.nullable
        else:
            model.attributes[attr_name] = attr_info

    def _check_schema_drift(self, entities: List[Any], model: ResourceModel):
        """Check for schema drift using existing SchemaDriftDetector utilities."""
        print("\n🔍 Checking schema drift...")

        # Use existing schema drift detection utilities
        for entity in entities:
            try:
                # Convert entity to dict for drift detection
                if hasattr(entity, 'model_dump'):
                    entity_dict = entity.model_dump()
                elif hasattr(entity, 'dict'):
                    entity_dict = entity.dict()
                else:
                    entity_dict = entity

                # Use existing drift detection
                unknown_fields = SchemaDriftDetector.extract_unknown_fields(
                    entity_dict,
                    set(entity_dict.keys()),
                    f"{model.resource_name}.entity"
                )

                if unknown_fields:
                    model.schema_drift.append(f"Unknown fields detected: {list(unknown_fields.keys())}")

            except Exception as e:
                model.schema_drift.append(f"Schema drift detection error: {e}")

        # Also include validation errors
        if model.validation_errors:
            model.schema_drift.extend(model.validation_errors)

    def _analyze_relationships(self, entities: List[Any], model: ResourceModel):
        """Analyze relationships between resources."""
        print("\n🔍 Analyzing relationships...")

        # Look for UUID references to other resources
        for entity in entities:
            if hasattr(entity, "spec"):
                for attr_name in dir(entity.spec):
                    if not attr_name.startswith("_"):
                        try:
                            value = getattr(entity.spec, attr_name)
                            if (
                                isinstance(value, str) and len(value) == 24
                            ):  # MongoDB ObjectId length
                                # This might be a UUID reference
                                model.relationships[attr_name] = "UUID Reference"
                        except Exception:
                            pass

    def _print_data_model(self, model: ResourceModel):
        """Print the complete data model in absolute truth terms."""
        self._print_model_header(model)
        self._print_model_summary(model)
        self._print_validation_errors(model)
        self._print_schema_drift(model)
        self._print_attributes_section(model)
        self._print_relationships(model)
        self._print_model_footer(model)

    def _print_model_header(self, model: ResourceModel):
        """Print the model header."""
        print(f"\n{'=' * 80}")
        print(f"📋 COMPLETE DATA MODEL: {model.resource_name}")
        print(f"{'=' * 80}")

    def _print_model_summary(self, model: ResourceModel):
        """Print the model summary with actionable insights."""
        print("\n📊 SUMMARY:")
        print(f"   Total Entities Analyzed: {model.total_entities}")
        print(f"   Total Attributes Found: {len(model.attributes)}")
        print(f"   Validation Errors: {len(model.validation_errors)}")
        print(f"   Schema Drift Issues: {len(model.schema_drift)}")

        # Add actionable insights
        self._print_actionable_insights(model)

    def _print_actionable_insights(self, model: ResourceModel):
        """Print actionable insights and recommendations."""
        print("\n🎯 ACTIONABLE INSIGHTS:")

        # Check for field mismatches with research suggestions
        field_mismatches = self._check_field_mismatches(model)
        if field_mismatches:
            print("   ⚠️  FIELD MISMATCHES DETECTED:")
            for mismatch in field_mismatches:
                print(f"      - {mismatch['field']}: {mismatch['description']}")
                print(f"        🔍 RESEARCH: {mismatch['research_suggestion']}")
                print(f"        📋 VALIDATE: {mismatch['validation_step']}")

        # Check for API spec integration opportunities
        api_spec_opportunities = self._check_api_spec_opportunities(model)
        if api_spec_opportunities:
            print("   🔍 API SPEC INTEGRATION OPPORTUNITIES:")
            for opportunity in api_spec_opportunities:
                print(f"      - {opportunity}")

        # Check for schema drift with research suggestions
        if model.schema_drift:
            print("   📋 SCHEMA DRIFT RECOMMENDATIONS:")
            for drift in model.schema_drift:
                print(f"      - {drift}")
                print("        🔍 RESEARCH: Check API documentation for field definition")
                print("        📋 VALIDATE: Test field in real API calls before modeling")

    def _check_field_mismatches(self, model: ResourceModel) -> List[dict]:
        """Check for field mismatches between Pydantic and API with research suggestions."""
        mismatches = []

        # Check for fields that are required in Pydantic but optional in API
        for attr_name, attr_info in model.attributes.items():
            if attr_info.api_source == "pydantic" and not attr_info.nullable:
                # This field is required in Pydantic model
                # Check if API actually makes it optional
                if "optional" in attr_info.description.lower() or "nullable" in attr_info.description.lower():
                    mismatches.append({
                        'field': attr_name,
                        'description': "API says optional, Pydantic is required",
                        'research_suggestion': f"Check API documentation for {attr_name} field requirements",
                        'validation_step': f"Test {attr_name} field with null/empty values in real API calls"
                    })

        # Check for fields that exist in API but not in Pydantic
        for attr_name, attr_info in model.attributes.items():
            if attr_info.api_source == "api_response" and attr_name not in [a for a in model.attributes.keys() if model.attributes[a].api_source == "pydantic"]:
                mismatches.append({
                    'field': attr_name,
                    'description': "API says present, Pydantic is unmodeled",
                    'research_suggestion': f"Research {attr_name} field in API documentation and OpenAPI spec",
                    'validation_step': f"Verify {attr_name} field is consistently present in API responses"
                })

        # Check for type mismatches
        for attr_name, attr_info in model.attributes.items():
            if attr_info.api_source == "pydantic":
                # Simple heuristic: check if type seems wrong based on common patterns
                if attr_info.type == "str" and "id" in attr_name.lower() and "uuid" in attr_name.lower():
                    mismatches.append({
                        'field': attr_name,
                        'description': f"API says UUID, Pydantic is {attr_info.type}",
                        'research_suggestion': f"Check if {attr_name} should be UUID type in Pydantic model",
                        'validation_step': f"Validate {attr_name} field format in API responses"
                    })

        return mismatches

    def _check_api_spec_opportunities(self, model: ResourceModel) -> List[str]:
        """Check for opportunities to integrate with API specifications."""
        opportunities = []

        # Look for complex types that could be modeled from API spec
        for attr_name, attr_info in model.attributes.items():
            if attr_info.type in ["dict", "Dict", "object", "Object"]:
                opportunities.append(
                    f"Complex type '{attr_name}' - research API spec for proper modeling"
                )
            elif attr_info.enum_values:
                opportunities.append(
                    f"Enum field '{attr_name}' has {len(attr_info.enum_values)} values - validate against API spec"
                )
            elif attr_info.type in ["list", "List"] and "id" in attr_name.lower():
                opportunities.append(
                    f"List field '{attr_name}' - research if should be List[UUID] or List[str]"
                )

        return opportunities

    def _integrate_api_spec(self, model: ResourceModel):
        """Integrate with OpenAPI specification for enhanced analysis."""
        if not self.openapi_schemas:
            print("\n🔍 API SPEC INTEGRATION: No OpenAPI schemas available")
            return

        print("\n🔍 API SPEC INTEGRATION:")

        # Look for matching schemas in OpenAPI spec
        resource_name_lower = model.resource_name.lower()
        matching_schemas = []

        for schema_name, schema_def in self.openapi_schemas.items():
            if resource_name_lower in schema_name.lower() or schema_name.lower() in resource_name_lower:
                matching_schemas.append((schema_name, schema_def))

        if matching_schemas:
            print(f"   Found {len(matching_schemas)} matching schemas in API spec:")
            for schema_name, schema_def in matching_schemas:
                print(f"   📋 Schema: {schema_name}")

                # Analyze schema properties
                properties = schema_def.get("properties", {})
                if properties:
                    print(f"      Properties: {len(properties)}")
                    for prop_name, prop_def in list(properties.items())[:5]:  # Show first 5
                        prop_type = prop_def.get("type", "unknown")
                        required = prop_name in schema_def.get("required", [])
                        print(f"        - {prop_name}: {prop_type} {'(required)' if required else '(optional)'}")

                # Check for complex types that could be modeled
                self._analyze_complex_types_in_schema(schema_name, schema_def, model)
        else:
            print("   No matching schemas found in API spec")
            print("   💡 RESEARCH: Check if resource name matches API schema naming conventions")

    def _analyze_complex_types_in_schema(self, schema_name: str, schema_def: dict, model: ResourceModel):
        """Analyze complex types in OpenAPI schema for modeling opportunities."""
        properties = schema_def.get("properties", {})

        for prop_name, prop_def in properties.items():
            prop_type = prop_def.get("type", "unknown")

            if prop_type == "object" and "properties" in prop_def:
                # Nested object - could be modeled as separate class
                nested_props = prop_def.get("properties", {})
                print(f"      🔍 Complex type '{prop_name}' has {len(nested_props)} nested properties")
                print(f"         🔍 RESEARCH: Check if {prop_name} should be a separate Pydantic model")
                print(f"         📋 VALIDATE: Test {prop_name} structure in real API responses")

            elif prop_type == "array" and "items" in prop_def:
                # Array type - check if items are complex
                items_def = prop_def.get("items", {})
                if items_def.get("type") == "object":
                    print(f"      🔍 Array '{prop_name}' contains complex objects")
                    print(f"         🔍 RESEARCH: Check if {prop_name} items should be List[SomeModel]")
                    print(f"         📋 VALIDATE: Test {prop_name} array structure in API responses")
                elif items_def.get("type") == "string" and "enum" in items_def:
                    print(f"      🔍 Array '{prop_name}' contains enum strings")
                    print(f"         🔍 RESEARCH: Check if {prop_name} should be List[EnumType]")
                    print("         📋 VALIDATE: Verify enum values in API responses")

    def _print_validation_errors(self, model: ResourceModel):
        """Print validation errors if any."""
        if model.validation_errors:
            print("\n❌ VALIDATION ERRORS:")
            for error in model.validation_errors:
                print(f"   - {error}")

    def _print_schema_drift(self, model: ResourceModel):
        """Print schema drift issues if any."""
        if model.schema_drift:
            print("\n⚠️  SCHEMA DRIFT:")
            for drift in model.schema_drift:
                print(f"   - {drift}")

    def _print_attributes_section(self, model: ResourceModel):
        """Print the attributes section."""
        print("\n📋 ATTRIBUTES (Absolute Truth):")
        print(f"{'=' * 80}")

        # Group attributes by section
        meta_attrs = {
            k: v for k, v in model.attributes.items() if k.startswith("meta.")
        }
        spec_attrs = {
            k: v for k, v in model.attributes.items() if k.startswith("spec.")
        }
        other_attrs = {
            k: v
            for k, v in model.attributes.items()
            if not k.startswith(("meta.", "spec."))
        }

        self._print_attribute_group("META ATTRIBUTES", meta_attrs)
        self._print_attribute_group("SPEC ATTRIBUTES", spec_attrs)
        self._print_attribute_group("OTHER ATTRIBUTES", other_attrs)

    def _print_attribute_group(self, group_name: str, attributes: dict):
        """Print a group of attributes."""
        if attributes:
            print(f"\n🔹 {group_name}:")
            for _attr_name, attr_info in sorted(attributes.items()):
                self._print_attribute_info(attr_info)

    def _print_relationships(self, model: ResourceModel):
        """Print relationships if any."""
        if model.relationships:
            print("\n🔗 RELATIONSHIPS:")
            for rel_name, rel_type in model.relationships.items():
                print(f"   {rel_name}: {rel_type}")

    def _print_model_footer(self, model: ResourceModel):
        """Print the model footer."""
        print(f"\n{'=' * 80}")
        print(f"✅ Data model analysis complete for {model.resource_name}")
        print(f"{'=' * 80}")

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
            for nested_name, nested_attr in list(attr_info.nested_attributes.items())[
                :3
            ]:
                print(f"        - {nested_name}: {nested_attr.type}")

        print()

    def discover_available_resources(self) -> List[str]:
        """Discover all available resource types via raw API calls."""
        if not self.enable_raw_api:
            return list(self.resource_classes.keys())

        print("🔍 Discovering available resource types via raw API...")
        discovered = set()

        # Common resource types to try
        common_resources = [
            "Project",
            "Finding",
            "Repository",
            "RepositoryVersion",
            "PackageVersion",
            "Policy",
            "Metric",
            "Namespace",
            "User",
            "Organization",
            "Scan",
            "Report",
            "Template",
            "Workflow",
            "Action",
            "Event",
            "Log",
            "Configuration",
            "Setting",
            "Permission",
            "Role",
            "Team",
            "Invitation",
        ]

        for resource_type in common_resources:
            try:
                # Use simplified endpoint matching
                endpoint, distance = self.find_closest_endpoint(resource_type)

                response = self.client.get(endpoint)
                if response.status_code == 200:
                    data = response.json()
                    if "resources" in data and len(data["resources"]) > 0:
                        discovered.add(resource_type)
                        self.raw_api_resources[resource_type] = {
                            "endpoint": endpoint,
                            "sample_data": data["resources"][0]
                            if data["resources"]
                            else None,
                        }
                        print(
                            f"   ✅ {resource_type}: "
                            f"{len(data['resources'])} entities found (distance: {distance})"
                        )
                    else:
                        print(f"   ⚪ {resource_type}: No entities found")
                else:
                    print(f"   ❌ {resource_type}: API error {response.status_code}")
            except Exception as e:
                print(f"   ❌ {resource_type}: {str(e)}")

        # Add known SDK resources
        discovered.update(self.resource_classes.keys())
        self.discovered_resources = discovered

        print(f"\n📊 Discovered {len(discovered)} resource types:")
        for resource in sorted(discovered):
            status = "SDK" if resource in self.resource_classes else "Raw API"
            print(f"   - {resource} ({status})")

        return sorted(discovered)

    def analyze_all_resources(
        self, max_entities_per_resource: int = 20, include_unmapped: bool = False
    ):
        """Analyze all available resource types."""
        print("🚀 COMPREHENSIVE ENDOR LABS RESOURCE ANALYSIS")
        print("=" * 80)

        results = {}

        # Get all available resources
        if include_unmapped and self.enable_raw_api:
            print("🔍 Discovering all available resources...")
            available_resources = self.discover_available_resources()
        else:
            available_resources = list(self.resource_classes.keys())

        for resource_type in available_resources:
            try:
                print(f"\n{'=' * 20} {resource_type} {'=' * 20}")

                # Determine if we should use raw API
                use_raw_api = (
                    include_unmapped
                    and resource_type not in self.resource_classes
                    and self.enable_raw_api
                )

                model = self.analyze_resource(
                    resource_type, max_entities_per_resource, use_raw_api
                )
                results[resource_type] = model
            except Exception as e:
                print(f"❌ Failed to analyze {resource_type}: {e}")
                results[resource_type] = None

        # Print summary
        print(f"\n{'=' * 80}")
        print("📊 ANALYSIS SUMMARY")
        print(f"{'=' * 80}")

        for resource_type, model in results.items():
            if model:
                source = (
                    "Raw API" if resource_type not in self.resource_classes else "SDK"
                )
                print(
                    f"✅ {resource_type} ({source}): "
                    f"{model.total_entities} entities, "
                    f"{len(model.attributes)} attributes"
                )
            else:
                print(f"❌ {resource_type}: Analysis failed")

        return results

    def add_resource_type(self, resource_name: str, resource_module, resource_class, list_function):
        """Add a new resource type to the analyzer for easy extension."""
        self.resource_modules[resource_name] = resource_module
        self.resource_classes[resource_name] = resource_class
        self.list_functions[resource_name] = list_function
        print(f"✅ Added resource type: {resource_name}")

    def get_supported_resource_types(self) -> List[str]:
        """Get list of all supported resource types."""
        return list(self.resource_classes.keys())

    def get_resource_mutability_info(self, resource_type: str) -> Dict[str, List[str]]:
        """Get mutability information for a resource type using existing utilities."""
        return {
            "mutable": get_mutable_fields(resource_type.lower()),
            "immutable": get_immutable_fields(resource_type.lower())
        }


def main():
    """Main function to run the resource analyzer."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Endor Labs Resource Data Model Analyzer"
    )
    parser.add_argument("--resource", "-r", help="Specific resource type to analyze")
    parser.add_argument(
        "--all", "-a", action="store_true", help="Analyze all resource types"
    )
    parser.add_argument(
        "--discover",
        "-d",
        action="store_true",
        help="Discover all available resource types",
    )
    parser.add_argument(
        "--max-entities",
        "-m",
        type=int,
        default=20,
        help="Maximum entities to analyze per resource",
    )
    parser.add_argument(
        "--raw-api", action="store_true", help="Force use of raw API instead of SDK"
    )
    parser.add_argument(
        "--include-unmapped",
        "-u",
        action="store_true",
        help="Include unmapped resources (requires --all)",
    )
    parser.add_argument(
        "--disable-raw-api", action="store_true", help="Disable raw API discovery"
    )
    parser.add_argument(
        "--endpoint-only", action="store_true", help="Only find closest endpoint (simplified mode)"
    )

    args = parser.parse_args()

    try:
        analyzer = EndorResourceAnalyzer(enable_raw_api=not args.disable_raw_api)

        if args.endpoint_only and args.resource:
            # Simplified mode: just find closest endpoint
            endpoint, distance = analyzer.find_closest_endpoint(args.resource)

            # Test the endpoint
            print(f"\n🧪 Testing endpoint: {endpoint}")
            if analyzer.test_endpoint(endpoint):
                print("✅ Endpoint is accessible!")
            else:
                print("❌ Endpoint is not accessible")
                print(f"📊 Closest Levenshtein distance: {distance}")

            return 0

        elif args.discover:
            print("🔍 DISCOVERING ALL AVAILABLE RESOURCES")
            print("=" * 50)
            resources = analyzer.discover_available_resources()
            print(f"\n📊 Found {len(resources)} resource types:")
            for resource in resources:
                status = "SDK" if resource in analyzer.resource_classes else "Raw API"
                print(f"   - {resource} ({status})")

        elif args.all:
            analyzer.analyze_all_resources(args.max_entities, args.include_unmapped)
        elif args.resource:
            analyzer.analyze_resource(
                args.resource, args.max_entities, args.raw_api
            )
        else:
            print("Please specify one of:")
            print("  --resource <type>     : Analyze specific resource")
            print("  --all                 : Analyze all SDK resources")
            print(
                "  --all --include-unmapped : Analyze all resources "
                "(including unmapped)"
            )
            print("  --discover            : Discover available resources")
            print("  --endpoint-only       : Just find closest endpoint (simplified)")
            print("\nAvailable SDK resources:", list(analyzer.resource_classes.keys()))

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
