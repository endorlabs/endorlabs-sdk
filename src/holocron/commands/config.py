"""
Config command implementation for Holocron.

Handles configuration display and validation.
"""

import json

from ..config import HolocronConfig, HolocronConfigError, load_config, validate_config


def config_command(args):
    """Execute the config command."""
    try:
        if args.subcommand == "show":
            _show_config(args)
        elif args.subcommand == "validate":
            _validate_config(args)
        else:
            print(f"Unknown config subcommand: {args.subcommand}")
            return
    except HolocronConfigError as e:
        print(f"Configuration error: {e}")
        return
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return


def _show_config(args):
    """Show current configuration."""
    try:
        config = load_config()

        if args.format == "json":
            _show_config_json(config)
        else:
            _show_config_text(config)

    except Exception as e:
        print(f"Failed to load configuration: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()


def _show_config_json(config: HolocronConfig):
    """Show configuration in JSON format."""
    config_dict = {
        "db_path": config.db_path,
        "manifest_path": config.manifest_path,
        "default_collection": config.default_collection,
        "embedding_model": config.embedding_model,
        "paths": {
            "include_dirs": config.paths.include_dirs,
            "exclude_dirs": config.paths.exclude_dirs,
        },
        "external_docs": {
            "openapi_url_template": config.external_docs.openapi_url_template
            if config.external_docs
            else None,
            "openapi_output": config.external_docs.openapi_output
            if config.external_docs
            else None,
            "sitemap_url": config.external_docs.sitemap_url
            if config.external_docs
            else None,
            "sitemap_output": config.external_docs.sitemap_output
            if config.external_docs
            else None,
            "user_docs_output": config.external_docs.user_docs_output
            if config.external_docs
            else None,
            "max_age_days": config.external_docs.max_age_days
            if config.external_docs
            else None,
        },
        "content_types": {
            name: {
                "name": ct_config.name,
                "patterns": ct_config.patterns,
                "extensions": ct_config.extensions,
                "chunk_size": ct_config.chunk_size,
                "overlap": ct_config.overlap,
                "delimiters": ct_config.delimiters,
                "preserve_structure": ct_config.preserve_structure,
                "preserve_complete_sections": ct_config.preserve_complete_sections,
                "split_by_endpoints": ct_config.split_by_endpoints,
            }
            for name, ct_config in config.content_types.items()
        },
    }

    print(json.dumps(config_dict, indent=2))


def _show_config_text(config: HolocronConfig):
    """Show configuration in human-readable format."""
    print("Holocron Configuration")
    print("=" * 50)

    print(f"Database Path: {config.db_path}")
    print(f"Manifest Path: {config.manifest_path}")
    print(f"Default Collection: {config.default_collection}")
    print(f"Embedding Model: {config.embedding_model}")

    print("\nPaths:")
    print(f"  Include Directories: {config.paths.include_dirs}")
    print(f"  Exclude Directories: {config.paths.exclude_dirs}")

    print("\nExternal Documentation:")
    if config.external_docs:
        print(f"  OpenAPI URL Template: {config.external_docs.openapi_url_template}")
        print(f"  OpenAPI Output: {config.external_docs.openapi_output}")
        print(f"  Sitemap URL: {config.external_docs.sitemap_url}")
        print(f"  Sitemap Output: {config.external_docs.sitemap_output}")
        print(f"  User Docs Output: {config.external_docs.user_docs_output}")
        print(f"  Max Age Days: {config.external_docs.max_age_days}")
    else:
        print("  Not configured (external docs settings moved to collections)")

    print("\nContent Types:")
    for name, ct_config in config.content_types.items():
        print(f"  {name}:")
        print(f"    Name: {ct_config.name}")
        print(f"    Patterns: {ct_config.patterns}")
        if ct_config.extensions:
            print(f"    Extensions: {ct_config.extensions}")
        print(f"    Chunk Size: {ct_config.chunk_size}")
        print(f"    Overlap: {ct_config.overlap}")
        print(f"    Delimiters: {ct_config.delimiters}")
        print(f"    Preserve Structure: {ct_config.preserve_structure}")
        print(f"    Preserve Complete Sections: {ct_config.preserve_complete_sections}")
        if ct_config.split_by_endpoints:
            print(f"    Split By Endpoints: {ct_config.split_by_endpoints}")


def _validate_config(args):
    """Validate configuration."""
    try:
        config = load_config()
        warnings = validate_config(config)

        if not warnings:
            print("✅ Configuration is valid")
        else:
            print("⚠️  Configuration has warnings:")
            for content_type, warning in warnings.items():
                print(f"  {content_type}: {warning}")

    except Exception as e:
        print(f"❌ Configuration is invalid: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
