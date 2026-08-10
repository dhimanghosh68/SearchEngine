import httpx
import pytest

from apps.api.platform.adapters.http import HttpNetworkClient


@pytest.mark.asyncio
async def test_http_network_client_returns_response_and_stream():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.headers["range"] == "bytes=5-"

        return httpx.Response(
            206,
            headers={
                "Content-Range": "bytes 5-9/10",
                "Content-Length": "5",
            },
            content=b"world",
        )

    transport = httpx.MockTransport(handler)

    client = HttpNetworkClient()

    original = httpx.AsyncClient

    class TestClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            kwargs["transport"] = transport
            super().__init__(**kwargs)

    import apps.api.platform.adapters.http as http_adapter

    http_adapter.httpx.AsyncClient = TestClient

    try:
        response = await client.get(
            "https://example.com/file.bin",
            headers={"Range": "bytes=5-"},
        )

        assert response.status_code == 206
        assert response.headers["content-range"] == (
            "bytes 5-9/10"
        )

        chunks = [
            chunk
            async for chunk in response.body
        ]

        assert b"".join(chunks) == b"world"
    finally:
        http_adapter.httpx.AsyncClient = original
