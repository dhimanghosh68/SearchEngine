from typing import Any
from urllib.parse import urlparse

from elasticsearch import AsyncElasticsearch

from apps.api.schemas.document import DocumentCreate


ELASTICSEARCH_URL = "http://127.0.0.1:9200"
INDEX_NAME = "documents"


class SearchService:
    def __init__(self) -> None:
        self.client = AsyncElasticsearch(ELASTICSEARCH_URL)

    async def ping(self) -> bool:
        return await self.client.ping()

    async def close(self) -> None:
        await self.client.close()

    @staticmethod
    def document_id(url: str) -> str:
        parsed = urlparse(url)

        scheme = parsed.scheme.lower()
        hostname = (parsed.hostname or "").lower()

        if not scheme or not hostname:
            raise ValueError("Invalid URL")

        port = parsed.port

        if port and not (
            (scheme == "http" and port == 80)
            or (scheme == "https" and port == 443)
        ):
            hostname = f"{hostname}:{port}"

        path = parsed.path.rstrip("/")

        if not path:
            path = "/"

        canonical = f"{scheme}://{hostname}{path}"

        if parsed.query:
            canonical += f"?{parsed.query}"

        return canonical

    async def index_document(
        self,
        document: DocumentCreate,
    ) -> str:
        document_id = self.document_id(document.url)

        await self.client.index(
            index=INDEX_NAME,
            id=document_id,
            document=document.model_dump(),
            refresh="wait_for",
        )

        return document_id

    async def search(
        self,
        query: str,
        limit: int = 10,
        page: int = 1,
    ) -> dict[str, Any]:
        offset = (page - 1) * limit

        response = await self.client.search(
            index=INDEX_NAME,
            from_=offset,
            size=limit,
            track_total_hits=True,
            query={
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^3",
                        "description^2",
                        "content",
                    ],
                }
            },
            highlight={
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
                "fields": {
                    "title": {},
                    "description": {},
                    "content": {
                        "fragment_size": 200,
                        "number_of_fragments": 2,
                    },
                },
            },
        )

        total = response["hits"]["total"]

        if isinstance(total, dict):
            total_count = total["value"]
        else:
            total_count = total

        results = []

        for hit in response["hits"]["hits"]:
            results.append(
                {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "title": hit["_source"]["title"],
                    "url": hit["_source"]["url"],
                    "description": hit["_source"]["description"],
                    "content": hit["_source"]["content"],
                    "highlight": hit.get("highlight", {}),
                }
            )

        return {
            "query": query,
            "page": page,
            "limit": limit,
            "total": total_count,
            "results": results,
        }
