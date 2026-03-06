"""Paginator for iterating over paginated ServiceTrade API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional

if TYPE_CHECKING:
    from .client import ServicetradeClient


class Paginator:
    """Iterate over paginated API endpoints.

    Usage:
        paginator = Paginator(client, "/job", "jobs")
        for item in paginator:
            print(item)
    """

    def __init__(
        self,
        client: ServicetradeClient,
        path: str,
        items_key: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._client = client
        self._path = path
        self._items_key = items_key
        self._params = dict(params) if params else {}

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        page = 1
        total_pages = 1  # assume at least one page

        while page <= total_pages:
            params = {**self._params, "page": page}
            response = self._client.get(self._path, params=params)

            if not isinstance(response, dict):
                return

            total_pages = response.get("totalPages", 1)
            items: List[Dict[str, Any]] = response.get(self._items_key, [])

            yield from items

            page += 1
