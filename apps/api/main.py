import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config.settings import CORS_ORIGINS
from apps.api.schemas.document import (
    BulkDocumentResponse,
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    SearchResponse,
)
from apps.api.services.index import create_index
from apps.api.services.search import SearchService


search_service = SearchService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    for attempt in range(1, 11):
        try:
            client = search_service._client()

            if not await client.ping():
                raise RuntimeError("Elasticsearch ping failed")

            await create_index(client)

            print(
                f"Elasticsearch ready on startup "
                f"(attempt {attempt}/10)"
            )
            break

        except Exception as exc:
            if attempt == 10:
                raise RuntimeError(
                    "Elasticsearch did not become ready after "
                    "10 startup attempts"
                ) from exc

            delay = min(2 ** (attempt - 1), 5)

            print(
                f"Elasticsearch not ready "
                f"(attempt {attempt}/10): {exc}"
            )
            print(f"Retrying in {delay}s...")
            await asyncio.sleep(delay)

    yield

    await search_service.close()


app = FastAPI(
    title="SearchEngine API",
    version="0.3.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "search-engine-api"}


@app.get("/health")
async def health() -> dict[str, str]:
    elasticsearch_ok = await search_service.ping()

    return {
        "status": "ok",
        "elasticsearch": "ok" if elasticsearch_ok else "error",
    }


@app.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(document: DocumentCreate):
    try:
        document_id = await search_service.index_document(document)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "id": document_id,
        **document.model_dump(mode="json"),
        "url": str(document.url),
    }


@app.get(
    "/documents",
    response_model=DocumentListResponse,
)
async def list_documents(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    return await search_service.list_documents(
        page=page,
        limit=limit,
    )


@app.get(
    "/documents/{document_id:path}",
    response_model=DocumentResponse,
)
async def get_document(document_id: str):
    document = await search_service.get_document(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return document


@app.put(
    "/documents/{document_id:path}",
    response_model=DocumentResponse,
)
async def update_document(
    document_id: str,
    document: DocumentUpdate,
):
    try:
        updated = await search_service.update_document(
            document_id,
            document,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return updated


@app.delete(
    "/documents/{document_id:path}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(document_id: str):
    deleted = await search_service.delete_document(document_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )


@app.post(
    "/documents/bulk",
    response_model=BulkDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_documents(
    documents: list[DocumentCreate],
):
    if not documents:
        raise HTTPException(
            status_code=400,
            detail="At least one document is required",
        )

    if len(documents) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Maximum 1000 documents per request",
        )

    try:
        ids = await search_service.bulk_index(documents)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        "count": len(ids),
        "ids": ids,
    }


@app.get(
    "/search",
    response_model=SearchResponse,
)
async def search(
    q: str = Query(min_length=1, max_length=500),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
):
    return await search_service.search(
        query=q,
        limit=limit,
        page=page,
    )
