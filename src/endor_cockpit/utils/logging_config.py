"""Centralized logging configuration."""

import logging
import os

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python < 3.11


def setup_logging(module_name: str = "endor_cockpit") -> logging.Logger:
    """Setup logging from pyproject.toml configuration."""
    try:
        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
            log_config = config.get("tool", {}).get("logging", {})
            module_config = log_config.get(module_name, {})

            level = os.getenv("LOG_LEVEL") or module_config.get(
                "level", log_config.get("level", "INFO")
            )
            format_str = module_config.get(
                "format", log_config.get("format", "%(levelname)s - %(message)s")
            )

        logging.basicConfig(level=level, format=format_str)
        return logging.getLogger(module_name)
    except Exception:
        logging.basicConfig(level="INFO")
        return logging.getLogger(module_name)
