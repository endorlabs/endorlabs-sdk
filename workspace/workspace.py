#!/usr/bin/env python3
"""
Simple workspace for Endor Cockpit API experimentation.
"""

import os
import sys

# Add src to path for imports FIRST
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespace


def main():
