"""
Backward compatibility module for namespaces.

This module provides backward compatibility for the old 'namespaces' import
by re-exporting everything from the 'namespace' module.
"""

# Re-export everything from namespace module
from .namespace import *

# Also re-export the module itself for direct access
from . import namespace
