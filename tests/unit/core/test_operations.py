"""Test cases for operations re-exports.

Ensures the operations facade re-exports callables from resources
and guards against accidental removal.
"""


def test_operations_list_findings_is_callable() -> None:
    """Operations re-exports list_findings as a callable."""
    from endorlabs.operations import list_findings

    assert callable(list_findings)


def test_operations_list_namespaces_is_callable() -> None:
    """Operations re-exports list_namespaces as a callable."""
    from endorlabs.operations import list_namespaces

    assert callable(list_namespaces)


def test_operations_list_policies_is_callable() -> None:
    """Operations re-exports list_policies as a callable."""
    from endorlabs.operations import list_policies

    assert callable(list_policies)


def test_operations_list_projects_is_callable() -> None:
    """Operations re-exports list_projects as a callable."""
    from endorlabs.operations import list_projects

    assert callable(list_projects)
