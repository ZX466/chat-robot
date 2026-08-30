"""百度 access_token：异步获取 + 缓存 + 过期自动刷新（§4.2 迁移点）。

原实现：ZerolanLiveRobot/pipeline/utils/baidu_auth.py（requests 同步、无过期管理）。
"""

import asyncio
import time

import httpx
from loguru import logger

from ..http import get_shared_client

TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
_DEFAULT_EXPIRES_IN = 2592000  # 百度默认 30 天


class BaiduTokenError(RuntimeError):
    """获取或刷新百度 access_token 失败。"""


class BaiduTokenManager:
    """线程安全的 token 缓存：并发调用共用一次刷新（asyncio.Lock）。"""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        *,
        client: httpx.AsyncClient | None = None,
        refresh_margin: int = 60,
    ) -> None:
        if not api_key or not secret_key:
            raise ValueError("Baidu api_key and secret_key must be provided")
        self._api_key = api_key
        self._secret_key = secret_key
        self._client = client or get_shared_client()
        self._owns_client = client is None
        self._refresh_margin = refresh_margin
        self._lock = asyncio.Lock()
        self._token: str | None = None
        self._expires_at: float = 0.0

    async def get_token(self) -> str:
        async with self._lock:
            expires_at = self._expires_at - self._refresh_margin
            if self._token is not None and time.monotonic() < expires_at:
                return self._token
            await self._refresh()
            assert self._token is not None
            return self._token

    def invalidate(self) -> None:
        """强制下次调用刷新（例如收到 110/111 token 失效错误码时）。"""
        self._token = None
        self._expires_at = 0.0

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _refresh(self) -> None:
        response = await self._client.post(
            TOKEN_URL,
            params={
                "grant_type": "client_credentials",
                "client_id": self._api_key,
                "client_secret": self._secret_key,
            },
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise BaiduTokenError(
                f"Failed to get Baidu access token: {data.get('error_description') or data}"
            )
        expires_in = int(data.get("expires_in", _DEFAULT_EXPIRES_IN))
        self._token = str(token)
        self._expires_at = time.monotonic() + expires_in
        logger.debug("Baidu access_token refreshed, expires_in={}s", expires_in)
