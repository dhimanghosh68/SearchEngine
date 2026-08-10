from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.services.search import SearchService
from apps.api.schemas.document import DocumentCreate


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

def test_list_documents_mapping():
    service = SearchService()

    response = {
        "hits": {
            "total": {"value": 2},
            "hits": [
                {
                    "_id": "doc-1",
                    "_source": {
                        "title": "Python",
                        "url": "https://example.com/python",
                        "description": "Python description",
                        "content": "Python content",
                    },
                },
                {
                    "_id": "doc-2",
                    "_source": {
                        "title": "FastAPI",
                        "url": "https://example.com/fastapi",
                        "description": "FastAPI description",
                        "content": "FastAPI content",
                    },
                },
            ],
        }
    }

    async def fake_search(**kwargs):
        assert kwargs["from_"] == 20
        assert kwargs["size"] == 20
        assert kwargs["track_total_hits"] is True
        return response

    with patch.object(
        service._client(),
        "search",
        new=AsyncMock(side_effect=fake_search),
    ):
        import asyncio

        result = asyncio.run(
            service.list_documents(page=2, limit=20)
        )

    assert result["page"] == 2
    assert result["limit"] == 20
    assert result["total"] == 2
    assert result["results"][0]["id"] == "doc-1"
    assert result["results"][1]["id"] == "doc-2"


def test_get_document_mapping():
    service = SearchService()

    response = {
        "_id": "doc-1",
        "_source": {
            "title": "Python",
            "url": "https://example.com/python",
            "description": "Python description",
            "content": "Python content",
        },
    }

    with patch.object(
        service._client(),
        "get",
        new=AsyncMock(return_value=response),
    ):
        import asyncio

        result = asyncio.run(
            service.get_document("doc-1")
        )

    assert result is not None
    assert result["id"] == "doc-1"
    assert result["title"] == "Python"
    assert result["url"] == "https://example.com/python"


def test_get_missing_document_returns_none():
    from elasticsearch import NotFoundError

    service = SearchService()

    error = NotFoundError(
        message="Document not found",
        meta={},
        body={},
    )

    with patch.object(
        service._client(),
        "get",
        new=AsyncMock(side_effect=error),
    ):
        import asyncio

        result = asyncio.run(
            service.get_document("missing")
        )

    assert result is None


def test_delete_document_success():
    service = SearchService()

    with patch.object(
        service._client(),
        "delete",
        new=AsyncMock(return_value={}),
    ) as mock_delete:
        import asyncio

        result = asyncio.run(
            service.delete_document("doc-1")
        )

    assert result is True
    mock_delete.assert_awaited_once()


def test_delete_missing_document_returns_false():
    from elasticsearch import NotFoundError

    service = SearchService()

    error = NotFoundError(
        message="Document not found",
        meta={},
        body={},
    )

    with patch.object(
        service._client(),
        "delete",
        new=AsyncMock(side_effect=error),
    ):
        import asyncio

        result = asyncio.run(
            service.delete_document("missing")
        )

    assert result is False


def test_bulk_index_success():
    service = SearchService()

    documents = [
        DocumentCreate(
            title="Python",
            url="https://example.com/python",
            description="Python description",
            content="Python content",
        ),
        DocumentCreate(
            title="FastAPI",
            url="https://example.com/fastapi",
            description="FastAPI description",
            content="FastAPI content",
        ),
    ]

    with patch.object(
        service._client(),
        "bulk",
        new=AsyncMock(
            return_value={
                "errors": False,
                "items": [],
            }
        ),
    ) as mock_bulk:
        import asyncio

        result = asyncio.run(
            service.bulk_index(documents)
        )

    assert result == [
        "https://example.com/python",
        "https://example.com/fastapi",
    ]

    mock_bulk.assert_awaited_once()


def test_bulk_index_failure():
    service = SearchService()

    documents = [
        DocumentCreate(
            title="Python",
            url="https://example.com/python",
            description="Python description",
            content="Python content",
        )
    ]

    with patch.object(
        service._client(),
        "bulk",
        new=AsyncMock(
            return_value={
                "errors": True,
                "items": [
                    {
                        "index": {
                            "error": {
                                "type": "mapper_parsing_exception",
                                "reason": "Invalid field",
                            }
                        }
                    }
                ],
            }
        ),
    ):
        import asyncio

        try:
            asyncio.run(
                service.bulk_index(documents)
            )
        except RuntimeError as exc:
            assert "Bulk indexing failed" in str(exc)
        else:
            raise AssertionError(
                "Expected RuntimeError"
            )

def test_initial_index_name():
    from apps.api.services.index import initial_index_name

    assert initial_index_name() == "documents_v1"


def test_create_index_preserves_existing_alias():
    import asyncio
    from unittest.mock import AsyncMock

    from apps.api.services.index import create_index

    client = AsyncMock()
    client.indices.exists_alias = AsyncMock(return_value=True)

    asyncio.run(create_index(client))

    client.indices.exists_alias.assert_awaited_once_with(
        name="documents",
    )
    client.indices.exists.assert_not_awaited()
    client.indices.create.assert_not_awaited()
    client.indices.put_alias.assert_not_awaited()


def test_create_index_rejects_physical_alias_name_collision():
    import asyncio
    from unittest.mock import AsyncMock

    from apps.api.services.index import create_index

    client = AsyncMock()
    client.indices.exists_alias = AsyncMock(return_value=False)
    client.indices.exists = AsyncMock(return_value=True)

    try:
        asyncio.run(create_index(client))
    except RuntimeError as exc:
        assert "exists as a physical index" in str(exc)
    else:
        raise AssertionError(
            "Expected RuntimeError for physical index collision"
        )


def test_create_index_creates_v1_and_alias():
    import asyncio
    from unittest.mock import AsyncMock

    from apps.api.services.index import (
        DOCUMENT_MAPPING,
        DOCUMENT_SETTINGS,
        create_index,
    )

    client = AsyncMock()
    client.indices.exists_alias = AsyncMock(return_value=False)

    async def exists(index):
        return index == "documents_v1"

    client.indices.exists = AsyncMock(side_effect=exists)

    asyncio.run(create_index(client))

    client.indices.create.assert_not_awaited()

    client.indices.put_alias.assert_awaited_once_with(
        index="documents_v1",
        name="documents",
        is_write_index=True,
    )


def test_create_index_creates_v1_when_missing():
    import asyncio
    from unittest.mock import AsyncMock

    from apps.api.services.index import (
        DOCUMENT_MAPPING,
        DOCUMENT_SETTINGS,
        create_index,
    )

    client = AsyncMock()
    client.indices.exists_alias = AsyncMock(return_value=False)

    async def exists(index):
        return False

    client.indices.exists = AsyncMock(side_effect=exists)

    asyncio.run(create_index(client))

    client.indices.create.assert_awaited_once_with(
        index="documents_v1",
        settings=DOCUMENT_SETTINGS,
        mappings=DOCUMENT_MAPPING,
    )

    client.indices.put_alias.assert_awaited_once_with(
        index="documents_v1",
        name="documents",
        is_write_index=True,
    )

def test_create_index_fresh_install():
    import asyncio
    from unittest.mock import AsyncMock

    from apps.api.services.index import create_index

    client = AsyncMock()

    client.indices.exists_alias = AsyncMock(return_value=False)
    client.indices.exists = AsyncMock(
        side_effect=[False, False]
    )

    asyncio.run(create_index(client))

    client.indices.exists_alias.assert_awaited_once_with(
        name="documents",
    )

    assert client.indices.exists.await_count == 2

    client.indices.create.assert_awaited_once_with(
        index="documents_v1",
        settings=client.indices.create.await_args.kwargs["settings"],
        mappings=client.indices.create.await_args.kwargs["mappings"],
    )

    client.indices.put_alias.assert_awaited_once_with(
        index="documents_v1",
        name="documents",
        is_write_index=True,
    )


def test_create_index_rejects_unaliased_physical_index():
    import asyncio
    from unittest.mock import AsyncMock

    import pytest

    from apps.api.services.index import create_index

    client = AsyncMock()

    client.indices.exists_alias = AsyncMock(return_value=False)
    client.indices.exists = AsyncMock(return_value=True)

    with pytest.raises(
        RuntimeError,
        match="exists as a physical index",
    ):
        asyncio.run(create_index(client))

    client.indices.create.assert_not_awaited()
    client.indices.put_alias.assert_not_awaited()


def test_create_index_reuses_existing_versioned_index():
    import asyncio
    from unittest.mock import AsyncMock

    from apps.api.services.index import create_index

    client = AsyncMock()

    client.indices.exists_alias = AsyncMock(return_value=False)
    client.indices.exists = AsyncMock(
        side_effect=[False, True]
    )

    asyncio.run(create_index(client))

    client.indices.create.assert_not_awaited()

    client.indices.put_alias.assert_awaited_once_with(
        index="documents_v1",
        name="documents",
        is_write_index=True,
    )

def test_create_index_rejects_orphan_physical_index():
    import asyncio
    from unittest.mock import AsyncMock

    from apps.api.services.index import create_index

    client = AsyncMock()

    client.indices.exists_alias = AsyncMock(return_value=False)
    client.indices.exists = AsyncMock(
        side_effect=[True]
    )

    try:
        asyncio.run(create_index(client))
    except RuntimeError as exc:
        assert "exists as a physical index" in str(exc)
    else:
        raise AssertionError(
            "Expected RuntimeError for orphan physical index"
        )

    client.indices.create.assert_not_awaited()
    client.indices.put_alias.assert_not_awaited()


def test_create_index_reuses_existing_initial_index():
    import asyncio
    from unittest.mock import AsyncMock

    from apps.api.services.index import create_index

    client = AsyncMock()

    client.indices.exists_alias = AsyncMock(return_value=False)
    client.indices.exists = AsyncMock(
        side_effect=[False, True]
    )

    asyncio.run(create_index(client))

    client.indices.create.assert_not_awaited()

    client.indices.put_alias.assert_awaited_once_with(
        index="documents_v1",
        name="documents",
        is_write_index=True,
    )
