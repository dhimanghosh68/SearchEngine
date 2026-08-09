from fastapi import FastAPI, HTTPException, Query
from contextlib import asynccontextmanager


from apps.api.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    SearchResponse,
)
from apps.api.services.index import create_index
from apps.api.services.search import SearchService


search_service = SearchService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_index(search_service.client)

    yield

    await search_service.close()


app = FastAPI(
    title="SearchEngine API",
    version="0.2.0",
    lifespan=lifespan,
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
)
async def create_document(document: DocumentCreate):
    document_id = await search_service.index_document(document)

    return {
        "id": document_id,
        **document.model_dump(),
    }

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
