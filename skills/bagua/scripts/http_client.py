from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class HttpSettings:
    timeout: float = 20.0
    retry_count: int = 2
    user_agent: str = "bagua/0.1"


class HttpClient:
    def __init__(self, settings: HttpSettings):
        try:
            import httpx
        except ModuleNotFoundError as error:  # pragma: no cover - environment dependent
            raise RuntimeError("Install dependencies first: python3 -m pip install -r requirements.txt") from error
        self.httpx = httpx
        self.settings = settings
        self.client = httpx.Client(
            timeout=settings.timeout,
            follow_redirects=True,
            headers={"User-Agent": settings.user_agent},
        )

    def close(self) -> None:
        self.client.close()

    def get_json(self, url: str, **kwargs) -> dict:
        response = self._get(url, **kwargs)
        return response.json()

    def get_text(self, url: str, **kwargs) -> str:
        return self._get(url, **kwargs).text

    def post_json(self, url: str, **kwargs) -> dict:
        response = self._request("post", url, **kwargs)
        return response.json()

    def _get(self, url: str, **kwargs):
        return self._request("get", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs):
        last_error: Exception | None = None
        for attempt in range(self.settings.retry_count + 1):
            try:
                response = self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (self.httpx.TimeoutException, self.httpx.HTTPStatusError, self.httpx.TransportError) as error:
                last_error = error
                if attempt >= self.settings.retry_count:
                    break
                time.sleep(0.4 * (attempt + 1))
        raise last_error or RuntimeError(f"GET failed: {url}")
