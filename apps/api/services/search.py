from typing import Any
from urllib.parse import urlparse

from elasticsearch import AsyncElasticsearch, NotFoundError

from apps.api.config.settings import ELASTICSEARCH_URL, INDEX_NAME

from apps.api.schemas.document import DocumentCreate, DocumentUpdate




class SearchService:
    def __init__(self) -> None:
        self.client: AsyncElasticsearch | None = None

    def _client(self) -> AsyncElasticsearch:
        if self.client is None:
            self.client = AsyncElasticsearch(ELASTICSEARCH_URL)
        return self.client

    async def ping(self) -> bool:
        return await self._client().ping()

    async def close(self) -> None:
        if self.client is not None:
            await self.client.close()
            self.client = None

    @staticmethod
    def document_id(url: str) -> str:
        parsed = urlparse(str(url))

        scheme = parsed.scheme.lower()
        hostname = (parsed.hostname or "").lower()

        if scheme not in {"http", "https"} or not hostname:
            raise ValueError("Invalid URL")

        try:
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Invalid URL port") from exc

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
        document_id = self.document_id(str(document.url))

        await self._client().index(
            index=INDEX_NAME,
            id=document_id,
            document={
                **document.model_dump(mode="json"),
                "url": str(document.url),
            },
            refresh="wait_for",
        )

        return document_id

    async def update_document(
        self,
        document_id: str,
        document: DocumentUpdate,
    ) -> dict[str, Any] | None:
        try:
            current = await self._client().get(
                index=INDEX_NAME,
                id=document_id,
            )
        except NotFoundError:
            return None

        new_id = self.document_id(str(document.url))

        if new_id != document_id:
            await self._client().delete(
                index=INDEX_NAME,
                id=document_id,
                refresh="wait_for",
            )

        await self._client().index(
            index=INDEX_NAME,
            id=new_id,
            document={
                **document.model_dump(mode="json"),
                "url": str(document.url),
            },
            refresh="wait_for",
        )

        return {
            "id": new_id,
            **document.model_dump(mode="json"),
            "url": str(document.url),
        }

    async def get_document(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        try:
            response = await self._client().get(
                index=INDEX_NAME,
                id=document_id,
            )
        except NotFoundError:
            return None

        return {
            "id": response["_id"],
            **response["_source"],
        }

    async def delete_document(
        self,
        document_id: str,
    ) -> bool:
        try:
            await self._client().delete(
                index=INDEX_NAME,
                id=document_id,
                refresh="wait_for",
            )
        except NotFoundError:
            return False

        return True

    async def list_documents(
        self,
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        offset = (page - 1) * limit

        response = await self._client().search(
            index=INDEX_NAME,
            from_=offset,
            size=limit,
            track_total_hits=True,
            query={"match_all": {}},
            sort=[
                {"url": "asc"},            ],
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
                    **hit["_source"],
                }
            )

        return {
            "page": page,
            "limit": limit,
            "total": total_count,
            "results": results,
        }

    async def bulk_index(
        self,
        documents: list[DocumentCreate],
    ) -> list[str]:
        operations: list[dict[str, Any]] = []
        ids: list[str] = []

        for document in documents:
            document_id = self.document_id(str(document.url))
            ids.append(document_id)

            operations.append(
                {
                    "index": {
                        "_index": INDEX_NAME,
                        "_id": document_id,
                    }
                }
            )
            operations.append(
                {
                    **document.model_dump(mode="json"),
                    "url": str(document.url),
                }
            )

        if operations:
            response = await self._client().bulk(
                operations=operations,
                refresh="wait_for",
            )

            if response.get("errors"):
                failures = []

                for item in response.get("items", []):
                    result = item.get("index", {})
                    if "error" in result:
                        failures.append(result["error"])

                raise RuntimeError(
                    f"Bulk indexing failed for {len(failures)} document(s)"
                )

        return ids

    async def search(
        self,
        query: str,
        limit: int = 10,
        page: int = 1,
    ) -> dict[str, Any]:
        offset = (page - 1) * limit

        response = await self._client().search(
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
