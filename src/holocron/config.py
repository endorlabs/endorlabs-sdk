"""
Holocron Configuration System

Provides type-safe configuration loading and validation for the Holocron
knowledge base system. Supports environment variable interpolation and
extensible content type definitions.
"""

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python < 3.11


class HolocronConfigError(Exception):
    """Custom exception for Holocron configuration errors."""

    pass


@dataclass
class CollectionConfig:
    """Configuration for a collection with simple array-based criteria."""

    name: str
    chunk_size: int = 1000
    overlap: int = 200
    delimiters: List[str] = None
    preserve_structure: bool = True
    preserve_complete_sections: bool = True
    split_by_endpoints: bool = False
    # Simple array-based criteria
    path_patterns: List[str] = None
    file_extensions: List[str] = None
    not_path_patterns: List[str] = None
    # External docs config (for endor_user_docs collection)
    openapi_url_template: Optional[str] = None
    openapi_output: Optional[str] = None
    sitemap_url: Optional[str] = None
    sitemap_output: Optional[str] = None
    user_docs_output: Optional[str] = None
    max_age_days: int = 7

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.delimiters is None:
            self.delimiters = []

        if self.path_patterns is None:
            self.path_patterns = []

        if self.file_extensions is None:
            self.file_extensions = []

        if self.not_path_patterns is None:
            self.not_path_patterns = []

        if self.chunk_size <= 0:
            raise HolocronConfigError(
                f"chunk_size must be positive, got {self.chunk_size}"
            )

        if self.overlap < 0:
            raise HolocronConfigError(
                f"overlap must be non-negative, got {self.overlap}"
            )

        if self.overlap >= self.chunk_size:
            raise HolocronConfigError(
                (
                    f"overlap ({self.overlap}) must be less than "
                    f"chunk_size ({self.chunk_size})"
                )
            )

        # Validate that at least one criteria type is provided
        if (
            not self.path_patterns
            and not self.file_extensions
            and not self.not_path_patterns
        ):
            raise HolocronConfigError(
                (
                    "At least one criteria type (path_patterns, file_extensions, "
                    "not_path_patterns) must be provided"
                )
            )

    def to_content_type_config(self) -> "ContentTypeConfig":
        """Convert CollectionConfig to ContentTypeConfig for backward compatibility."""
        # Convert simple arrays to criteria format
        criteria = []

        # Add path patterns
        for pattern in self.path_patterns:
            criteria.append({"type": "path_pattern", "value": pattern})

        # Add file extensions
        for ext in self.file_extensions:
            criteria.append({"type": "file_extension", "value": ext})

        # Add not path patterns
        for pattern in self.not_path_patterns:
            criteria.append({"type": "not_path_pattern", "value": pattern})

        return ContentTypeConfig(
            name=self.name,
            chunk_size=self.chunk_size,
            overlap=self.overlap,
            delimiters=self.delimiters,
            preserve_structure=self.preserve_structure,
            preserve_complete_sections=self.preserve_complete_sections,
            split_by_endpoints=self.split_by_endpoints,
            criteria=criteria,
        )


@dataclass
class ContentTypeConfig:
    """Configuration for a specific content type (legacy support)."""

    name: str
    patterns: List[str] = None
    extensions: Optional[List[str]] = None
    chunk_size: int = 1000
    overlap: int = 200
    delimiters: List[str] = None
    preserve_structure: bool = True
    preserve_complete_sections: bool = True
    split_by_endpoints: bool = False
    # New robust detection fields
    collection_name: Optional[str] = None
    criteria: List[Dict[str, str]] = None
    criteria_rst: List[Dict[str, str]] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.delimiters is None:
            self.delimiters = []

        if self.patterns is None:
            self.patterns = []

        if self.criteria is None:
            self.criteria = []

        if self.criteria_rst is None:
            self.criteria_rst = []

        if self.chunk_size <= 0:
            raise HolocronConfigError(
                f"chunk_size must be positive, got {self.chunk_size}"
            )

        if self.overlap < 0:
            raise HolocronConfigError(
                f"overlap must be non-negative, got {self.overlap}"
            )

        if self.overlap >= self.chunk_size:
            raise HolocronConfigError(
                (
                    f"overlap ({self.overlap}) must be less than "
                    f"chunk_size ({self.chunk_size})"
                )
            )

        # Validate that either patterns or criteria are provided
        if not self.patterns and not self.criteria and not self.criteria_rst:
            raise HolocronConfigError("Either patterns or criteria must be provided")


@dataclass
class PathConfig:
    """Configuration for file path management."""

    include_dirs: List[str]
    exclude_dirs: List[str]

    def __post_init__(self):
        """Validate path configuration."""
        if not self.include_dirs:
            raise HolocronConfigError("include_dirs cannot be empty")

        # Normalize paths
        self.include_dirs = [os.path.normpath(path) for path in self.include_dirs]
        self.exclude_dirs = [os.path.normpath(path) for path in self.exclude_dirs]


@dataclass
class ExternalDocsConfig:
    """Configuration for external documentation downloads."""

    openapi_url_template: str
    openapi_output: str
    sitemap_url: str
    sitemap_output: str
    user_docs_output: str
    max_age_days: int = 7

    def __post_init__(self):
        """Validate external docs configuration."""
        if self.max_age_days <= 0:
            raise HolocronConfigError(
                f"max_age_days must be positive, got {self.max_age_days}"
            )

        # Normalize output paths
        self.openapi_output = os.path.normpath(self.openapi_output)
        self.sitemap_output = os.path.normpath(self.sitemap_output)
        self.user_docs_output = os.path.normpath(self.user_docs_output)


@dataclass
class HolocronConfig:
    """Main Holocron configuration."""

    db_path: str
    manifest_path: str
    default_collection: str
    embedding_model: str
    paths: PathConfig
    collections: Dict[str, CollectionConfig]
    # Legacy support
    external_docs: ExternalDocsConfig = None
    content_types: Dict[str, ContentTypeConfig] = None
    collection_mapping: Dict[str, str] = None

    def __post_init__(self):
        """Validate main configuration."""
        if not self.default_collection:
            raise HolocronConfigError("default_collection cannot be empty")

        if not self.embedding_model:
            raise HolocronConfigError("embedding_model cannot be empty")

        # Normalize paths
        self.db_path = os.path.normpath(self.db_path)
        self.manifest_path = os.path.normpath(self.manifest_path)


def _interpolate_env_vars(value: str) -> str:
    """Interpolate environment variables in string values."""
    if not isinstance(value, str):
        return value

    # Pattern to match {VAR_NAME} or {VAR_NAME:default}
    pattern = r"\{([A-Z_][A-Z0-9_]*)(?::([^}]*))?\}"

    def replace_var(match):
        var_name = match.group(1)
        default = match.group(2) if match.group(2) is not None else ""
        return os.getenv(var_name, default)

    return re.sub(pattern, replace_var, value)


def _load_content_types(config_data: Dict[str, Any]) -> Dict[str, ContentTypeConfig]:
    """Load content type configurations from TOML data."""
    content_types = {}
    content_types_section = config_data.get("content_types", {})

    for content_type_name, type_config in content_types_section.items():
        # Interpolate environment variables in string values
        processed_config = {}
        for key, value in type_config.items():
            if isinstance(value, str):
                processed_config[key] = _interpolate_env_vars(value)
            elif isinstance(value, list):
                processed_config[key] = [
                    _interpolate_env_vars(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                processed_config[key] = value

        try:
            content_types[content_type_name] = ContentTypeConfig(**processed_config)
        except TypeError as e:
            raise HolocronConfigError(
                f"Invalid configuration for content type '{content_type_name}': {e}"
            ) from e

    return content_types


def _load_collections(holocron_section: Dict[str, Any]) -> Dict[str, CollectionConfig]:
    """Load collection configurations from [tool.holocron.collection.*] sections."""
    collections = {}

    # Look for collection sections
    collection_section = holocron_section.get("collection", {})
    for collection_name, value in collection_section.items():
        # Interpolate environment variables in collection config
        processed_config = {}
        for config_key, config_value in value.items():
            if isinstance(config_value, str):
                processed_config[config_key] = _interpolate_env_vars(config_value)
            elif isinstance(config_value, list):
                processed_config[config_key] = [
                    _interpolate_env_vars(item) if isinstance(item, str) else item
                    for item in config_value
                ]
            else:
                processed_config[config_key] = config_value

        try:
            collections[collection_name] = CollectionConfig(**processed_config)
        except TypeError as e:
            raise HolocronConfigError(
                f"Invalid configuration for collection '{collection_name}': {e}"
            ) from e

    return collections


def _parse_config_file(config_path: str) -> dict:
    """Parse configuration file and return raw data."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        raise HolocronConfigError(f"Failed to parse configuration file: {e}") from e


def _extract_holocron_section(config_data: dict) -> dict:
    """Extract and validate holocron section from config data."""
    holocron_section = config_data.get("tool", {}).get("holocron", {})
    if not holocron_section:
        raise HolocronConfigError("No [tool.holocron] section found in configuration")
    return holocron_section


def _load_main_config(holocron_section: dict) -> dict:
    """Load main configuration with environment variable interpolation."""
    main_config = {}
    excluded_keys = [
        "paths",
        "external_docs",
        "content_types",
        "collection",
        "collection.endor_user_docs",
        "collection.markdown",
        "collection.code",
        "collection.api_spec",
    ]

    for key, value in holocron_section.items():
        if key not in excluded_keys:
            if isinstance(value, str):
                main_config[key] = _interpolate_env_vars(value)
            else:
                main_config[key] = value
    return main_config


def _load_paths_config(holocron_section: dict) -> PathConfig:
    """Load and validate paths configuration."""
    paths_section = holocron_section.get("paths", {})
    if not paths_section:
        raise HolocronConfigError("No [tool.holocron.paths] section found")

    try:
        return PathConfig(**paths_section)
    except TypeError as e:
        raise HolocronConfigError(f"Invalid paths configuration: {e}") from e


def _load_external_docs_config(holocron_section: dict) -> Optional[ExternalDocsConfig]:
    """Load legacy external docs configuration."""
    external_docs_section = holocron_section.get("external_docs", {})
    if not external_docs_section:
        return None

    # Interpolate environment variables
    processed_external_docs = {}
    for key, value in external_docs_section.items():
        if isinstance(value, str):
            processed_external_docs[key] = _interpolate_env_vars(value)
        else:
            processed_external_docs[key] = value

    try:
        return ExternalDocsConfig(**processed_external_docs)
    except TypeError as e:
        raise HolocronConfigError(f"Invalid external_docs configuration: {e}") from e


def load_config(config_path: str = "pyproject.toml") -> HolocronConfig:
    """
    Load Holocron configuration from pyproject.toml.

    Args:
        config_path: Path to configuration file

    Returns:
        HolocronConfig instance with validated configuration

    Raises:
        HolocronConfigError: If configuration is invalid
        FileNotFoundError: If configuration file doesn't exist
    """
    # Parse configuration file
    config_data = _parse_config_file(config_path)
    holocron_section = _extract_holocron_section(config_data)

    # Load configuration sections
    main_config = _load_main_config(holocron_section)
    paths_config = _load_paths_config(holocron_section)
    collections = _load_collections(holocron_section)
    external_docs_config = _load_external_docs_config(holocron_section)
    content_types = _load_content_types(holocron_section)

    # Validate that either collections or content types are defined
    if not collections and not content_types:
        raise HolocronConfigError(
            "No collections or content types defined in configuration"
        )

    # Load legacy collection mapping
    collection_mapping = holocron_section.get("collection", {})

    # Create main config
    try:
        return HolocronConfig(
            paths=paths_config,
            collections=collections,
            external_docs=external_docs_config,
            content_types=content_types,
            collection_mapping=collection_mapping,
            **main_config,
        )
    except TypeError as e:
        raise HolocronConfigError(f"Invalid main configuration: {e}") from e


def _validate_directories(config: HolocronConfig) -> List[str]:
    """Validate directory existence and permissions."""
    warnings = []

    # Check if required directories exist
    for include_dir in config.paths.include_dirs:
        if not os.path.exists(include_dir):
            warnings.append(f"Include directory does not exist: {include_dir}")

    # Check if database directory is writable
    db_dir = os.path.dirname(config.db_path)
    if not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except OSError as e:
            warnings.append(f"Cannot create database directory {db_dir}: {e}")
    elif not os.access(db_dir, os.W_OK):
        warnings.append(f"Database directory is not writable: {db_dir}")

    return warnings


def _validate_collection_configs(config: HolocronConfig) -> List[str]:
    """Validate collection configurations."""
    warnings = []

    for collection_name, collection_config in config.collections.items():
        if collection_config.chunk_size < 100:
            warnings.append(
                f"Collection '{collection_name}' has very small chunk_size "
                f"({collection_config.chunk_size})"
            )

        if collection_config.overlap > collection_config.chunk_size // 2:
            warnings.append(
                f"Collection '{collection_name}' has high overlap ratio "
                f"({collection_config.overlap}/{collection_config.chunk_size})"
            )

    return warnings


def _validate_content_type_configs(config: HolocronConfig) -> List[str]:
    """Validate legacy content type configurations."""
    warnings = []

    if not config.content_types:
        return warnings

    for content_type_name, content_type_config in config.content_types.items():
        if content_type_config.chunk_size < 100:
            warnings.append(
                f"Content type '{content_type_name}' has very small chunk_size "
                f"({content_type_config.chunk_size})"
            )

        if content_type_config.overlap > content_type_config.chunk_size // 2:
            warnings.append(
                f"Content type '{content_type_name}' has high overlap ratio "
                f"({content_type_config.overlap}/{content_type_config.chunk_size})"
            )

    return warnings


def validate_config(config: HolocronConfig) -> List[str]:
    """
    Validate configuration and return list of warnings/errors.

    Args:
        config: HolocronConfig instance to validate

    Returns:
        List of validation messages (empty if valid)
    """
    warnings = []
    warnings.extend(_validate_directories(config))
    warnings.extend(_validate_collection_configs(config))
    warnings.extend(_validate_content_type_configs(config))
    return warnings


def get_default_config() -> HolocronConfig:
    """Get default configuration for testing/fallback."""
    return HolocronConfig(
        db_path=".workspace/holocron_data/vector_db",
        manifest_path=".workspace/holocron_data/vector_db_manifest.json",
        default_collection="endor_cockpit_docs",
        embedding_model="text-embedding-3-small",
        paths=PathConfig(
            include_dirs=["docs/", "src/", "tests/"],
            exclude_dirs=["__pycache__", ".git", "node_modules", "venv", ".venv"],
        ),
        collections={
            "markdown": CollectionConfig(
                name="Internal Markdown Documentation",
                file_extensions=[".md", ".rst"],
                chunk_size=1607,
                overlap=400,
                delimiters=["##"],
            )
        },
        external_docs=ExternalDocsConfig(
            openapi_url_template="{ENDOR_API}/download/openapiv2.swagger.json",
            openapi_output=".workspace/downloads/openapi-swagger.json",
            sitemap_url="https://docs.endorlabs.com/sitemap.xml",
            sitemap_output=".workspace/downloads/sitemap.xml",
            user_docs_output=".workspace/downloads/user-docs/",
            max_age_days=7,
        ),
        content_types={
            "markdown": ContentTypeConfig(
                name="Internal Markdown Documentation",
                patterns=[r"\.md$", r"\.rst$"],
                chunk_size=1607,
                overlap=400,
                delimiters=["##"],
            )
        },
    )
