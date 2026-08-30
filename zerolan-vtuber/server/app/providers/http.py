"""共享 httpx.AsyncClient 单例连接池（§3：全局单例，禁止 requests）。"""

import httpx

_client: httpx.AsyncClient | None = None


def get_shared_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
    return _client


async def close_shared_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
