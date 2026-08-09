from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.services.search import SearchService


def test_root():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "search-engine-api"


def test_document_validation():
    with TestClient(app) as client:
        response = client.post(
            "/documents",
            json={
                "title": "",
                "url": "https://example.com/test",
                "description": "",
                "content": "",
            },
        )

    assert response.status_code == 422


def test_invalid_url():
    with TestClient(app) as client:
        response = client.post(
            "/documents",
            json={
                "title": "Invalid",
                "url": "not-a-url",
                "description": "",
                "content": "",
            },
        )

    assert response.status_code == 422


def test_search_query_validation():
    with TestClient(app) as client:
        response = client.get("/search")

    assert response.status_code == 422


def test_search_pagination_validation():
    with TestClient(app) as client:
        response = client.get("/search?q=python&page=0")

    assert response.status_code == 422


def test_search_limit_validation():
    with TestClient(app) as client:
        response = client.get("/search?q=python&limit=101")

    assert response.status_code == 422


def test_document_id_canonicalization():
    assert (
        SearchService.document_id("HTTPS://EXAMPLE.COM/test/")
        == "https://example.com/test"
    )

    assert (
        SearchService.document_id("https://example.com/")
        == "https://example.com/"
    )

    assert (
        SearchService.document_id("http://example.com:80/test")
        == "http://example.com/test"
    )

    assert (
        SearchService.document_id("https://example.com:443/test")
        == "https://example.com/test"
    )

    assert (
        SearchService.document_id("https://example.com:8080/test")
        == "https://example.com:8080/test"
    )


def test_invalid_document_id_url():
    try:
        SearchService.document_id("not-a-url")
    except ValueError as exc:
        assert str(exc) == "Invalid URL"
    else:
        raise AssertionError("Expected ValueError")


def test_invalid_document_id_port():
    try:
        SearchService.document_id("https://example.com:invalid/test")
    except ValueError as exc:
        assert str(exc) == "Invalid URL port"
    else:
        raise AssertionError("Expected ValueError")


def test_search_response_mapping():
    service = SearchService()

    response = {
        "hits": {
            "total": {"value": 2},
            "hits": [
                {
                    "_id": "doc-1",
                    "_score": 3.5,
                    "_source": {
                        "title": "Python",
                        "url": "https://example.com/python",
                        "description": "Python description",
                        "content": "Python content",
                    },
                    "highlight": {
                        "title": ["<mark>Python</mark>"],
                    },
                },
            ],
        }
    }

    async def fake_search(**kwargs):
        return response

    with patch.object(
        service._client(),
        "search",
        new=AsyncMock(side_effect=fake_search),
    ):
        import asyncio

        result = asyncio.run(service.search("python"))

    assert result["query"] == "python"
    assert result["page"] == 1
    assert result["limit"] == 10
    assert result["total"] == 2
    assert result["results"][0]["id"] == "doc-1"
    assert result["results"][0]["score"] == 3.5
    assert result["results"][0]["highlight"]["title"] == [
        "<mark>Python</mark>"
    ]
