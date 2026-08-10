from __future__ import annotations

from typing import AsyncIterator

import httpx

from apps.api.platform.contracts import NetworkResponse


class HttpNetworkClient:
    def __init__(
        self,
        *,
        timeout: float = 30.0,
    ) -> None:
        self.timeout = timeout

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> NetworkResponse:
        client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        )

        try:
            response = await client.send(
                client.build_request(
                    "GET",
                    url,
                    headers=headers,
                ),
                stream=True,
            )

            async def body() -> AsyncIterator[bytes]:
                try:
                    async for chunk in response.aiter_bytes():
                        yield chunk
                finally:
                    await response.aclose()
                    await client.aclose()

            return NetworkResponse(
                status_code=response.status_code,
                headers={
                    key.lower(): value
                    for key, value in response.headers.items()
                },
                body=body(),
            )

        except Exception:
            await client.aclose()
            raise

