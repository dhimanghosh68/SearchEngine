import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config.settings import (
    CORS_ORIGINS,
    ELASTICSEARCH_URL,
    INDEX_NAME,
)
from apps.api.core.application import create_application_runtime
from apps.api.core.lifecycle import shutdown, startup
from apps.api.platform.contracts import RuntimePaths
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


def create_runtime_paths() -> RuntimePaths:
    return RuntimePaths(
        config="config",
        data="data",
        cache="cache",
        logs="logs",
        runtime="runtime",
    )


def get_search_service(request: Request) -> SearchService:
    return request.app.state.application.search


@asynccontextmanager
async def lifespan(app: FastAPI):
    paths = create_runtime_paths()

    application = create_application_runtime(
        elasticsearch_url=ELASTICSEARCH_URL,
        index_name=INDEX_NAME,
        paths=paths,
    )

    app.state.application = application
    app.state.runtime = application.runtime
    app.state.config = application.config
    app.state.metadata = application.metadata
    app.state.search = application.search
    app.state.downloads = application.downloads

    filesystem = application.runtime.capabilities.filesystem

    startup_result = await startup(
        filesystem,
        paths,
    )

    app.state.startup_result = startup_result

    if startup_result.recovery_required:
        print(
            "Previous SearchEngine runtime did not shut down cleanly; "
            "recovery state recorded."
        )

    search_service = application.search

    try:
        for attempt in range(1, 11):
            try:
                client = search_service._client()

                if not await client.ping():
                    raise RuntimeError("Elasticsearch ping failed")

                await create_index(
                    client,
                    index_name=application.config.index_name,
                )

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

    finally:
        await search_service.close()

        await shutdown(
            filesystem,
            paths,
            startup_result.state,
        )


app = FastAPI(
    title="SearchEngine API",
    version="0.4.0",
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
async def health(
    search_service: SearchService = Depends(get_search_service),
) -> dict[str, str]:
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
async def create_document(
    document: DocumentCreate,
    search_service: SearchService = Depends(get_search_service),
):
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
    search_service: SearchService = Depends(get_search_service),
):
    return await search_service.list_documents(
        page=page,
        limit=limit,
    )


@app.get(
    "/documents/{document_id:path}",
    response_model=DocumentResponse,
)
async def get_document(
    document_id: str,
    search_service: SearchService = Depends(get_search_service),
):
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
    search_service: SearchService = Depends(get_search_service),
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
async def delete_document(
    document_id: str,
    search_service: SearchService = Depends(get_search_service),
):
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
    search_service: SearchService = Depends(get_search_service),
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
    search_service: SearchService = Depends(get_search_service),
):
    return await search_service.search(
        query=q,
        limit=limit,
        page=page,
    )
