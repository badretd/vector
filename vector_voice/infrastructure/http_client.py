"""HTTP client factory with proxy support placeholder."""
from __future__ import annotations

from typing import Any

import requests


class RequestsHttpClientFactory:
    """Build requests.Session objects. Proxy support is a placeholder."""

    def __init__(self, proxy_url: str | None = None) -> None:
        self._proxy_url = proxy_url

    def set_proxy(self, proxy_url: str | None) -> None:
        self._proxy_url = proxy_url

    def create_session(self) -> requests.Session:
        session = requests.Session()
        if self._proxy_url:
            session.proxies = {"http": self._proxy_url, "https": self._proxy_url}
        return session