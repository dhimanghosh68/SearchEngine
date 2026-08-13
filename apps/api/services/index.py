from __future__ import annotations

from elasticsearch import AsyncElasticsearch

DEFAULT_INDEX_NAME = "documents"
INITIAL_INDEX_SUFFIX = "_v1"

DOCUMENT_SETTINGS = {
    "number_of_shards": 1,
    "number_of_replicas": 0,
}

DOCUMENT_MAPPING = {
    "properties": {
        "title": {
            "type": "text",
        },
        "url": {
            "type": "keyword",
        },
        "description": {
            "type": "text",
        },
        "content": {
            "type": "text",
        },
    }
}


def initial_index_name(
    index_name: str = DEFAULT_INDEX_NAME,
) -> str:
    return f"{index_name}{INITIAL_INDEX_SUFFIX}"


async def create_index(
    client: AsyncElasticsearch,
    *,
    index_name: str = DEFAULT_INDEX_NAME,
) -> None:
    initial_name = initial_index_name(index_name)

    # If the logical name is already an alias, preserve it.
    if await client.indices.exists_alias(name=index_name):
        return

    # The logical name cannot safely be both a physical index and
    # the alias we expect to manage.
    if await client.indices.exists(index_name):
        raise RuntimeError(
            f"Index name '{index_name}' exists as a physical index"
        )

    # Reuse an already-created versioned index.
    if not await client.indices.exists(initial_name):
        await client.indices.create(
            index=initial_name,
            settings=DOCUMENT_SETTINGS,
            mappings=DOCUMENT_MAPPING,
        )

    await client.indices.put_alias(
        index=initial_name,
        name=index_name,
        is_write_index=True,
    )
