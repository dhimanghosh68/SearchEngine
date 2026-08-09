from typing import Any

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

    async def index_document(
        self,
        document: DocumentCreate,
    ) -> str:
        response = await self.client.index(
            index=INDEX_NAME,
            document=document.model_dump(),
            refresh="wait_for",
        )

        return response["_id"]

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        response = await self.client.search(
            index=INDEX_NAME,
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
            size=limit,
        )

        results = []

        for hit in response["hits"]["hits"]:
            results.append(
                {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    **hit["_source"],
                }
            )

        return results
