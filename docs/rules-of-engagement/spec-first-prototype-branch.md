# Spec-First Prototype Branch Runbook

Prototype branch: `prototype/spec-first-sync-thin-slice`

This runbook captures the baseline and preservation boundaries for the
spec-first prototype effort.

## Baseline Capture

The prototype branch starts from the current registry-driven SDK architecture
and keeps existing public behavior intact unless explicitly called out.

Baseline expectations:

- `endorlabs.APIClient` remains the transport/auth/session owner.
- `endorlabs.Client` remains the primary consumer entrypoint.
- Existing resource facades and convenience UX stay available.
- Existing demo and workflow flows continue to run.

## Preserved Components

The following components are preserved as reusable and still valid:

- `src/endorlabs/api_client.py`: authentication, retry, redaction, pagination.
- `src/endorlabs/client_surface.py`: client construction and facade attachment.
- `src/endorlabs/_demo/demo_cli.py`: runbook/demo walkthrough UX.

## Prototype-Only Additions

This prototype introduces a thin slice for spec-first resource parity without
attempting a full migration in one step:

- first-class vulnerability and malware resources
- first-class query resources for vulnerability/malware query endpoints
- release/parity workflow alignment for generated surfaces

## Explicit Non-Goals

- full facade rewrite across all resources
- removal of existing convenience methods (`lookup`, `tag`, `untag`, etc.)
- auth/transport rewrites
