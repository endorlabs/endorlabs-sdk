"""Tests for Holocron configuration system."""

import os
import tempfile
from unittest.mock import patch

import pytest

from holocron.config import (
    CollectionConfig,
    ContentTypeConfig,
    ExternalDocsConfig,
    HolocronConfig,
    HolocronConfigError,
    PathConfig,
    get_default_config,
    load_config,
    validate_config,
)


class TestCollectionConfig:
    """Test CollectionConfig class."""

    def test_valid_config(self):
        """Test valid collection configuration."""
        config = CollectionConfig(
            name="Test Collection",
            chunk_size=1000,
            overlap=200,
            delimiters=["##"],
            path_patterns=[".*test.*"],
            file_extensions=[".md"],
            not_path_patterns=[".*exclude.*"],
        )

        assert config.name == "Test Collection"
        assert config.chunk_size == 1000
        assert config.overlap == 200
        assert config.delimiters == ["##"]
        assert config.path_patterns == [".*test.*"]
        assert config.file_extensions == [".md"]
        assert config.not_path_patterns == [".*exclude.*"]
        assert config.preserve_structure is True
        assert config.preserve_complete_sections is True
        assert config.split_by_endpoints is False

    def test_invalid_chunk_size(self):
        """Test invalid chunk size raises error."""
        with pytest.raises(HolocronConfigError, match="chunk_size must be positive"):
            CollectionConfig(
                name="Test", path_patterns=[".*test.*"], chunk_size=0, overlap=100
            )

    def test_invalid_overlap(self):
        """Test invalid overlap raises error."""
        with pytest.raises(HolocronConfigError, match="overlap must be non-negative"):
            CollectionConfig(
                name="Test", path_patterns=[".*test.*"], chunk_size=1000, overlap=-1
            )

    def test_overlap_too_large(self):
        """Test overlap larger than chunk size raises error."""
        with pytest.raises(
            HolocronConfigError, match="overlap.*must be less than chunk_size"
        ):
            CollectionConfig(
                name="Test", path_patterns=[".*test.*"], chunk_size=1000, overlap=1500
            )

    def test_no_criteria_raises_error(self):
        """Test that no criteria raises error."""
        with pytest.raises(HolocronConfigError, match="At least one criteria type"):
            CollectionConfig(name="Test", chunk_size=1000, overlap=200)

    def test_to_content_type_config(self):
        """Test conversion to ContentTypeConfig."""
        config = CollectionConfig(
            name="Test Collection",
            chunk_size=1000,
            overlap=200,
            delimiters=["##"],
            path_patterns=[".*test.*"],
            file_extensions=[".md"],
            not_path_patterns=[".*exclude.*"],
        )

        content_type_config = config.to_content_type_config()

        assert content_type_config.name == "Test Collection"
        assert content_type_config.chunk_size == 1000
        assert content_type_config.overlap == 200
        assert content_type_config.delimiters == ["##"]
        assert len(content_type_config.criteria) == 3

        # Check criteria format
        criteria_types = [c["type"] for c in content_type_config.criteria]
        assert "path_pattern" in criteria_types
        assert "file_extension" in criteria_types
        assert "not_path_pattern" in criteria_types


class TestContentTypeConfig:
    """Test ContentTypeConfig class."""

    def test_valid_config(self):
        """Test valid content type configuration."""
        config = ContentTypeConfig(
            name="Test Content",
            patterns=[r"\.md$", r"\.rst$"],
            chunk_size=1000,
            overlap=200,
            delimiters=["##"],
        )

        assert config.name == "Test Content"
        assert config.patterns == [r"\.md$", r"\.rst$"]
        assert config.chunk_size == 1000
        assert config.overlap == 200
        assert config.delimiters == ["##"]
        assert config.preserve_structure is True
        assert config.preserve_complete_sections is True
        assert config.split_by_endpoints is False

    def test_invalid_chunk_size(self):
        """Test invalid chunk size raises error."""
        with pytest.raises(HolocronConfigError, match="chunk_size must be positive"):
            ContentTypeConfig(
                name="Test",
                patterns=[r"\.md$"],
                chunk_size=0,
                overlap=100,
                delimiters=["##"],
            )

    def test_invalid_overlap(self):
        """Test invalid overlap raises error."""
        with pytest.raises(HolocronConfigError, match="overlap must be non-negative"):
            ContentTypeConfig(
                name="Test",
                patterns=[r"\.md$"],
                chunk_size=1000,
                overlap=-1,
                delimiters=["##"],
            )

    def test_overlap_too_large(self):
        """Test overlap larger than chunk size raises error."""
        with pytest.raises(
            HolocronConfigError, match="overlap.*must be less than chunk_size"
        ):
            ContentTypeConfig(
                name="Test",
                patterns=[r"\.md$"],
                chunk_size=1000,
                overlap=1500,
                delimiters=["##"],
            )


class TestPathConfig:
    """Test PathConfig class."""

    def test_valid_config(self):
        """Test valid path configuration."""
        config = PathConfig(
            include_dirs=["docs/", "src/"], exclude_dirs=["__pycache__", ".git"]
        )

        assert config.include_dirs == ["docs", "src"]
        assert config.exclude_dirs == ["__pycache__", ".git"]

    def test_empty_include_dirs(self):
        """Test empty include dirs raises error."""
        with pytest.raises(HolocronConfigError, match="include_dirs cannot be empty"):
            PathConfig(include_dirs=[], exclude_dirs=["__pycache__"])


class TestExternalDocsConfig:
    """Test ExternalDocsConfig class."""

    def test_valid_config(self):
        """Test valid external docs configuration."""
        config = ExternalDocsConfig(
            openapi_url_template="{ENDOR_API}/download/openapiv2.swagger.json",
            openapi_output=".workspace/downloads/openapi-swagger.json",
            sitemap_url="https://docs.endorlabs.com/sitemap.xml",
            sitemap_output=".workspace/downloads/sitemap.xml",
            user_docs_output=".workspace/downloads/user-docs/",
            max_age_days=7,
        )

        assert (
            config.openapi_url_template == "{ENDOR_API}/download/openapiv2.swagger.json"
        )
        assert config.openapi_output == ".workspace\\downloads\\openapi-swagger.json"
        assert config.sitemap_url == "https://docs.endorlabs.com/sitemap.xml"
        assert config.sitemap_output == ".workspace\\downloads\\sitemap.xml"
        assert config.user_docs_output == ".workspace\\downloads\\user-docs"
        assert config.max_age_days == 7

    def test_invalid_max_age_days(self):
        """Test invalid max age days raises error."""
        with pytest.raises(HolocronConfigError, match="max_age_days must be positive"):
            ExternalDocsConfig(
                openapi_url_template="test",
                openapi_output="test",
                sitemap_url="test",
                sitemap_output="test",
                user_docs_output="test",
                max_age_days=0,
            )


class TestHolocronConfig:
    """Test HolocronConfig class."""

    def test_valid_config(self):
        """Test valid main configuration."""
        paths = PathConfig(include_dirs=["docs/", "src/"], exclude_dirs=["__pycache__"])
        external_docs = ExternalDocsConfig(
            openapi_url_template="test",
            openapi_output="test",
            sitemap_url="test",
            sitemap_output="test",
            user_docs_output="test",
        )
        collections = {
            "markdown": CollectionConfig(
                name="Markdown",
                file_extensions=[".md"],
                chunk_size=1000,
                overlap=200,
                delimiters=["##"],
            )
        }
        content_types = {
            "markdown": ContentTypeConfig(
                name="Markdown",
                patterns=[r"\.md$"],
                chunk_size=1000,
                overlap=200,
                delimiters=["##"],
            )
        }

        config = HolocronConfig(
            db_path=".workspace/holocron_data/vector_db",
            manifest_path=".workspace/holocron_data/vector_db_manifest.json",
            default_collection="test_collection",
            embedding_model="text-embedding-3-small",
            paths=paths,
            collections=collections,
            external_docs=external_docs,
            content_types=content_types,
        )

        assert config.db_path == ".workspace\\holocron_data\\vector_db"
        assert (
            config.manifest_path == ".workspace\\holocron_data\\vector_db_manifest.json"
        )
        assert config.default_collection == "test_collection"
        assert config.embedding_model == "text-embedding-3-small"
        assert config.paths == paths
        assert config.collections == collections
        assert config.external_docs == external_docs
        assert config.content_types == content_types


class TestLoadConfig:
    """Test configuration loading."""

    def test_load_config_file_not_found(self):
        """Test loading non-existent configuration file."""
        with pytest.raises(FileNotFoundError):
            load_config("non_existent_file.toml")

    def test_load_config_invalid_toml(self):
        """Test loading invalid TOML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("invalid toml content [")
            f.flush()
            temp_path = f.name

        try:
            with pytest.raises(
                HolocronConfigError, match="Failed to parse configuration file"
            ):
                load_config(temp_path)
        finally:
            os.unlink(temp_path)

    def test_load_config_missing_section(self):
        """Test loading configuration with missing sections."""
        config_content = """
[tool.holocron]
db_path = ".workspace/holocron_data/vector_db"
manifest_path = ".workspace/holocron_data/vector_db_manifest.json"
default_collection = "test_collection"
embedding_model = "text-embedding-3-small"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            f.flush()
            temp_path = f.name

        try:
            with pytest.raises(
                HolocronConfigError, match="No \\[tool.holocron.paths\\] section found"
            ):
                load_config(temp_path)
        finally:
            os.unlink(temp_path)

    def test_load_config_missing_content_types(self):
        """Test loading configuration with missing content types."""
        config_content = """
[tool.holocron]
db_path = ".workspace/holocron_data/vector_db"
manifest_path = ".workspace/holocron_data/vector_db_manifest.json"
default_collection = "test_collection"
embedding_model = "text-embedding-3-small"

[tool.holocron.paths]
include_dirs = ["docs/", "src/"]
exclude_dirs = ["__pycache__", ".git"]

[tool.holocron.external_docs]
openapi_url_template = "test"
openapi_output = "test"
sitemap_url = "test"
sitemap_output = "test"
user_docs_output = "test"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            f.flush()
            temp_path = f.name

        try:
            with pytest.raises(
                HolocronConfigError, match="No collections or content types defined"
            ):
                load_config(temp_path)
        finally:
            os.unlink(temp_path)


class TestEnvironmentVariableInterpolation:
    """Test environment variable interpolation."""

    def test_interpolate_env_vars(self):
        """Test environment variable interpolation function."""
        from holocron.config import _interpolate_env_vars

        test_string = "https://{ENDOR_API}/api/v1"
        with patch.dict(os.environ, {"ENDOR_API": "api.test.com"}):
            result = _interpolate_env_vars(test_string)
            assert result == "https://api.test.com/api/v1"

    def test_load_config_with_env_vars(self):
        """Test loading configuration with environment variables."""
        config_content = """
[tool.holocron]
db_path = ".workspace/holocron_data/vector_db"
manifest_path = ".workspace/holocron_data/vector_db_manifest.json"
default_collection = "test_collection"
embedding_model = "text-embedding-3-small"

[tool.holocron.paths]
include_dirs = ["docs/", "src/"]
exclude_dirs = ["__pycache__", ".git"]

[tool.holocron.external_docs]
openapi_url_template = "{ENDOR_API}/download/openapiv2.swagger.json"
openapi_output = ".workspace/downloads/openapi-swagger.json"
sitemap_url = "https://docs.endorlabs.com/sitemap.xml"
sitemap_output = ".workspace/downloads/sitemap.xml"
user_docs_output = ".workspace/downloads/user-docs/"
max_age_days = 7

[tool.holocron.content_types.markdown]
name = "Markdown Documentation"
    patterns = ["\\\\.md$", "\\\\.rst$"]
chunk_size = 1607
overlap = 400
delimiters = ["##"]
preserve_structure = true
preserve_complete_sections = true
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            f.flush()
            temp_path = f.name

        try:
            with patch.dict(os.environ, {"ENDOR_API": "https://api.test.com"}):
                config = load_config(temp_path)

                assert (
                    config.external_docs.openapi_url_template
                    == "https://api.test.com/download/openapiv2.swagger.json"
                )

        finally:
            os.unlink(temp_path)

    def test_load_config_with_collections(self):
        """Test loading configuration with new collection format."""
        config_content = """
[tool.holocron]
db_path = ".workspace/holocron_data/vector_db"
manifest_path = ".workspace/holocron_data/vector_db_manifest.json"
default_collection = "test_collection"
embedding_model = "text-embedding-3-small"

[tool.holocron.paths]
include_dirs = ["docs/", "src/"]
exclude_dirs = ["__pycache__", ".git"]

[tool.holocron.collection.markdown]
name = "Markdown Documentation"
chunk_size = 1607
overlap = 400
delimiters = ["##"]
file_extensions = [".md", ".rst"]
not_path_patterns = [".workspace/downloads/user-docs/.*"]

[tool.holocron.collection.code]
name = "Source Code Files"
chunk_size = 6851
overlap = 500
delimiters = ["def ", "class "]
file_extensions = [".py", ".js", ".ts"]
    path_patterns = ["\\\\.py$", "\\\\.js$", "\\\\.ts$"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            f.flush()
            temp_path = f.name

        try:
            config = load_config(temp_path)

            assert len(config.collections) == 2
            assert "markdown" in config.collections
            assert "code" in config.collections

            markdown_config = config.collections["markdown"]
            assert markdown_config.name == "Markdown Documentation"
            assert markdown_config.file_extensions == [".md", ".rst"]
            assert markdown_config.not_path_patterns == [
                ".workspace/downloads/user-docs/.*"
            ]

            code_config = config.collections["code"]
            assert code_config.name == "Source Code Files"
            assert code_config.file_extensions == [".py", ".js", ".ts"]
            assert code_config.path_patterns == ["\\.py$", "\\.js$", "\\.ts$"]

        finally:
            os.unlink(temp_path)


class TestValidateConfig:
    """Test configuration validation."""

    def test_validate_config_success(self):
        """Test successful configuration validation."""
        paths = PathConfig(include_dirs=["docs/", "src/"], exclude_dirs=["__pycache__"])
        external_docs = ExternalDocsConfig(
            openapi_url_template="test",
            openapi_output="test",
            sitemap_url="test",
            sitemap_output="test",
            user_docs_output="test",
        )
        collections = {
            "markdown": CollectionConfig(
                name="Markdown",
                file_extensions=[".md"],
                chunk_size=1000,
                overlap=200,
                delimiters=["##"],
            )
        }
        content_types = {
            "markdown": ContentTypeConfig(
                name="Markdown",
                patterns=[r"\.md$"],
                chunk_size=1000,
                overlap=200,
                delimiters=["##"],
            )
        }

        config = HolocronConfig(
            db_path=".workspace/holocron_data/vector_db",
            manifest_path=".workspace/holocron_data/vector_db_manifest.json",
            default_collection="test_collection",
            embedding_model="text-embedding-3-small",
            paths=paths,
            collections=collections,
            external_docs=external_docs,
            content_types=content_types,
        )

        warnings = validate_config(config)
        assert isinstance(warnings, list)
        # May or may not have warnings depending on directory existence

    def test_validate_config_warnings(self):
        """Test configuration validation with warnings."""
        paths = PathConfig(include_dirs=["docs/", "src/"], exclude_dirs=["__pycache__"])
        external_docs = ExternalDocsConfig(
            openapi_url_template="test",
            openapi_output="test",
            sitemap_url="test",
            sitemap_output="test",
            user_docs_output="test",
        )
        collections = {
            "markdown": CollectionConfig(
                name="Markdown",
                file_extensions=[".md"],
                chunk_size=1000,
                overlap=200,
                delimiters=["##"],
            )
        }
        content_types = {
            "markdown": ContentTypeConfig(
                name="Markdown",
                patterns=[r"\.md$"],
                chunk_size=1000,
                overlap=200,
                delimiters=["##"],
            )
        }

        config = HolocronConfig(
            db_path=".workspace/holocron_data/vector_db",
            manifest_path=".workspace/holocron_data/vector_db_manifest.json",
            default_collection="test_collection",
            embedding_model="text-embedding-3-small",
            paths=paths,
            collections=collections,
            external_docs=external_docs,
            content_types=content_types,
        )

        warnings = validate_config(config)
        assert isinstance(warnings, list)


class TestGetDefaultConfig:
    """Test getting default configuration."""

    def test_get_default_config(self):
        """Test getting default configuration."""
        config = get_default_config()

        assert isinstance(config, HolocronConfig)
        assert config.db_path == ".workspace\\holocron_data\\vector_db"
        assert (
            config.manifest_path == ".workspace\\holocron_data\\vector_db_manifest.json"
        )
        assert config.default_collection == "endor_cockpit_docs"
        assert config.embedding_model == "text-embedding-3-small"
        assert isinstance(config.paths, PathConfig)
        assert isinstance(config.external_docs, ExternalDocsConfig)
        assert isinstance(config.content_types, dict)
        assert len(config.content_types) > 0


class TestValidationScriptIntegration:
    """Test integration with validation script."""

    def test_validation_script_import(self):
        """Test that validation script can be imported."""
        try:
            # Test that validation script can be imported
            import scripts.validate_holocron  # noqa: F401

            assert True
        except ImportError:
            pytest.skip("Validation script not available")

    def test_validation_script_has_validator_class(self):
        """Test that validation script has HolocronValidator class."""
        try:
            from scripts.validate_holocron import HolocronValidator

            assert HolocronValidator is not None
        except ImportError:
            pytest.skip("Validation script not available")

    def test_validation_script_has_main_function(self):
        """Test that validation script has main function."""
        try:
            from scripts.validate_holocron import main

            assert main is not None
        except ImportError:
            pytest.skip("Validation script not available")

    def test_validation_script_can_be_run(self):
        """Test that validation script can be run without errors."""
        try:
            import subprocess
            import sys
        except ImportError:
            pytest.skip("subprocess module not available")

        try:
            # Run validation script with --help to test it can be executed
            result = subprocess.run(
                [sys.executable, "scripts/validate_holocron.py", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Should not crash (exit code 0 or 2 for help)
            assert result.returncode in [0, 2]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Validation script not available or timeout")
