#!/usr/bin/env python3
"""Quick script to list projects and findings for visualization."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import project, finding
from endor_cockpit.types import ListParameters

namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan")

client = APIClient()

print("=" * 80)
print("PROJECTS")
print("=" * 80)
projects = project.list_projects(client, namespace)
print(f"Found {len(projects)} projects\n")
project_uuids = []
for i, p in enumerate(projects[:5], 1):
    name = p.meta.name if p.meta else "Unknown"
    print(f"{i}. {name}")
    print(f"   UUID: {p.uuid}\n")
    project_uuids.append(p.uuid)

if len(projects) > 5:
    print(f"... and {len(projects) - 5} more projects\n")

# Print first project UUID for easy copy-paste
if project_uuids:
    print("=" * 80)
    print("FIRST PROJECT UUID (for testing):")
    print(project_uuids[0])
    print("=" * 80)

print("=" * 80)
print("FINDINGS")
print("=" * 80)
findings = finding.list_findings(client, namespace, ListParameters(page_size=5))
print(f"Found {len(findings)} findings (showing first 5)\n")
for i, f in enumerate(findings[:5], 1):
    name = f.meta.name if f.meta else "Unknown"
    level = f.spec.level.value if f.spec and f.spec.level else "N/A"
    project_uuid = f.spec.project_uuid if f.spec else "N/A"
    print(f"{i}. {name}")
    print(f"   UUID: {f.uuid}")
    print(f"   Level: {level}")
    print(f"   Project UUID: {project_uuid}\n")

