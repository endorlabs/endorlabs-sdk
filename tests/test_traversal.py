"""Test cases for namespace traversal utilities.

Tests create_traverse_params and create_namespace_scoped_params
returning ListParameters.
"""

from endorlabs.types import ListParameters
from endorlabs.utils.traversal import (
    create_namespace_scoped_params,
    create_traverse_params,
)


class TestCreateTraverseParams:
    """Tests for create_traverse_params."""

    def test_returns_list_parameters(self) -> None:
        params = create_traverse_params()
        assert isinstance(params, ListParameters)

    def test_traverse_true(self) -> None:
        params = create_traverse_params()
        assert params.traverse is True

    def test_filter_set(self) -> None:
        params = create_traverse_params(filter_expr="spec.level==CRITICAL")
        assert params.filter == "spec.level==CRITICAL"

    def test_page_size_set_when_provided(self) -> None:
        params = create_traverse_params(page_size=50)
        assert params.page_size == 50

    def test_page_size_none_when_not_provided(self) -> None:
        params = create_traverse_params()
        assert params.page_size is None

    def test_kwargs_passed(self) -> None:
        params = create_traverse_params(mask="meta.name")
        assert params.mask == "meta.name"


class TestCreateNamespaceScopedParams:
    """Tests for create_namespace_scoped_params."""

    def test_returns_list_parameters(self) -> None:
        params = create_namespace_scoped_params()
        assert isinstance(params, ListParameters)

    def test_traverse_false(self) -> None:
        params = create_namespace_scoped_params()
        assert params.traverse is False

    def test_filter_set(self) -> None:
        params = create_namespace_scoped_params(filter_expr="spec.project_uuid==x")
        assert params.filter == "spec.project_uuid==x"

    def test_page_size_set_when_provided(self) -> None:
        params = create_namespace_scoped_params(page_size=100)
        assert params.page_size == 100

    def test_page_size_none_when_not_provided(self) -> None:
        params = create_namespace_scoped_params()
        assert params.page_size is None
