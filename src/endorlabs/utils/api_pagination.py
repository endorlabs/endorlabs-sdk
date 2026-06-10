"""Raw API list pagination helpers for workflow modules."""

from __future__ import annotations

from typing import Any

from endorlabs.api_client import APIClient


def extract_objects(resp_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract objects list from standard Endor API response."""
    if isinstance(resp_data, dict) and "list" in resp_data:
        list_data = resp_data["list"]
        if isinstance(list_data, dict) and "objects" in list_data:
            return list_data["objects"] or []
    return []


def paginate_raw(
    api_client: APIClient,
    url: str,
    params: dict[str, str],
    max_pages: int | None = None,
) -> list[dict[str, Any]]:
    """Paginate a raw API list call, returning all objects.

    ``max_pages`` of ``None`` or ``0`` fetches until the API reports no next page.
    """
    all_objects: list[dict[str, Any]] = []
    current_params = dict(params)
    page_limit = None if not max_pages or max_pages <= 0 else max_pages
    pages_fetched = 0

    while True:
        resp = api_client.get(url, params=current_params)
        data = resp.json()
        objects = extract_objects(data)
        all_objects.extend(objects)
        pages_fetched += 1

        next_token = None
        next_page_id = None
        if isinstance(data, dict) and "list" in data:
            list_data = data["list"]
            if isinstance(list_data, dict) and "response" in list_data:
                resp_meta = list_data["response"]
                next_token = resp_meta.get("next_page_token")
                next_page_id = resp_meta.get("next_page_id")

        if next_page_id:
            current_params["list_parameters.page_id"] = str(next_page_id)
        elif next_token:
            current_params["list_parameters.page_token"] = str(next_token)
        else:
            break

        if page_limit is not None and pages_fetched >= page_limit:
            break

    return all_objects
