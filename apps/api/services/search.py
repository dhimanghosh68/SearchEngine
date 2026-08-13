from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

from elasticsearch import AsyncElasticsearch, NotFoundError

from apps.api.schemas.document import DocumentCreate, DocumentUpdate


class SearchService:
    def __init__(
        self,
        *,
        elasticsearch_url: str = "http://127.0.0.1:9200",
        index_name: str = "documents",
    ) -> None:
        self.elasticsearch_url = elasticsearch_url
        self.index_name = index_name
        self.client: AsyncElasticsearch | None = None

    def _client(self) -> AsyncElasticsearch:
        if self.client is None:
            self.client = AsyncElasticsearch(self.elasticsearch_url)
        return self.client

    @staticmethod
    def document_id(url: Any) -> str:
        url = str(url)

        try:
            parsed = urlsplit(url)
        except ValueError as exc:
            if "port" in str(exc).lower():
                raise ValueError("Invalid URL port") from exc
            raise ValueError("Invalid URL") from exc

        if parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError("Invalid URL")

        if not parsed.netloc:
            raise ValueError("Invalid URL")

        try:
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Invalid URL port") from exc

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL")

        scheme = parsed.scheme.lower()
        netloc = hostname.lower()

        if port is not None:
            default_port = 80 if scheme == "http" else 443
            if port != default_port:
                netloc = f"{netloc}:{port}"

        # Preserve "/" for the root URL while removing
        # trailing slashes from non-root paths.
        path = parsed.path or "/"

        if path != "/":
            path = path.rstrip("/")

        return urlunsplit(
            (
                scheme,
                netloc,
                path,
                parsed.query,
                "",
            )
        )

    async def ping(self) -> bool:
        return bool(await self._client().ping())

    async def close(self) -> None:
        if self.client is not None:
            await self.client.close()
            self.client = None

    @staticmethod
    def _map_search_hit(hit: dict[str, Any]) -> dict[str, Any]:
        source = dict(hit.get("_source") or {})

        return {
            "id": hit.get("_id"),
            "score": hit.get("_score"),
            **source,
            "highlight": hit.get("highlight", {}),
        }

    async def search(
        self,
        query: str,
        *,
        page: int = 1,
        limit: int = 10,
    ) -> dict[str, Any]:
        if page < 1:
            raise ValueError("page must be greater than or equal to 1")

        if limit < 1:
            raise ValueError("limit must be greater than or equal to 1")

        from_ = (page - 1) * limit

        response = await self._client().search(
            index=self.index_name,
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
            from_=from_,
            size=limit,
            track_total_hits=True,
        )

        hits = response.get("hits", {})
        total = hits.get("total", 0)

        if isinstance(total, dict):
            total = total.get("value", 0)

        return {
            "query": query,
            "page": page,
            "limit": limit,
            "total": total,
            "results": [
                self._map_search_hit(hit)
                for hit in hits.get("hits", [])
            ],
        }

    async def list_documents(
        self,
        *,
        page: int = 1,
        limit: int = 10,
    ) -> dict[str, Any]:
        if page < 1:
            raise ValueError("page must be greater than or equal to 1")

        if limit < 1:
            raise ValueError("limit must be greater than or equal to 1")

        from_ = (page - 1) * limit

        response = await self._client().search(
            index=self.index_name,
            from_=from_,
            size=limit,
            query={"match_all": {}},
            track_total_hits=True,
        )

        hits = response.get("hits", {})
        total = hits.get("total", 0)

        if isinstance(total, dict):
            total = total.get("value", 0)

        results = [
            {
                "id": hit.get("_id"),
                **(hit.get("_source") or {}),
            }
            for hit in hits.get("hits", [])
        ]

        return {
            "page": page,
            "limit": limit,
            "total": total,
            "results": results,
        }

    async def get_document(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        try:
            response = await self._client().get(
                index=self.index_name,
                id=document_id,
            )
        except NotFoundError:
            return None

        return {
            "id": response.get("_id", document_id),
            **(response.get("_source") or {}),
        }

    async def index_document(
        self,
        document: DocumentCreate,
        *,
        document_id: str | None = None,
    ) -> dict[str, Any]:
        body = document.model_dump(exclude_none=True)

        if document_id is None:
            document_id = self.document_id(document.url)

        response = await self._client().index(
            index=self.index_name,
            id=document_id,
            document=body,
            refresh="wait_for",
        )

        return {
            "id": response["_id"],
            **body,
        }

    async def update_document(
        self,
        document_id: str,
        document: DocumentUpdate,
    ) -> dict[str, Any] | None:
        body = document.model_dump(
            exclude_none=True,
            exclude_unset=True,
        )

        if not body:
            return await self.get_document(document_id)

        try:
            await self._client().update(
                index=self.index_name,
                id=document_id,
                doc=body,
                refresh="wait_for",
            )
        except NotFoundError:
            return None

        return await self.get_document(document_id)

    async def delete_document(
        self,
        document_id: str,
    ) -> bool:
        try:
            await self._client().delete(
                index=self.index_name,
                id=document_id,
                refresh="wait_for",
            )
        except NotFoundError:
            return False

        return True

    async def bulk_index(
        self,
        documents: list[DocumentCreate],
    ) -> list[str]:
        if not documents:
            return []

        operations: list[dict[str, Any]] = []
        document_ids: list[str] = []

        for document in documents:
            document_id = self.document_id(document.url)
            document_ids.append(document_id)

            operations.append(
                {
                    "index": {
                        "_index": self.index_name,
                        "_id": document_id,
                    }
                }
            )
            operations.append(
                document.model_dump(exclude_none=True)
            )

        response = await self._client().bulk(
            operations=operations,
            refresh="wait_for",
        )

        if response.get("errors"):
            failed = [
                item
                for item in response.get("items", [])
                if item.get("index", {}).get("error")
            ]

            raise RuntimeError(
                f"Bulk indexing failed for {len(failed)} document(s)"
            )

        return document_ids
