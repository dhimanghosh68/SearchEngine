from elasticsearch import AsyncElasticsearch

from apps.api.config.settings import INDEX_NAME

DOCUMENT_SETTINGS = {
    "analysis": {
        "analyzer": {
            "document_text": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": [
                    "lowercase",
                ],
            },
        },
    },
}

DOCUMENT_MAPPING = {
    "properties": {
        "title": {
            "type": "text",
            "analyzer": "document_text",
            "fields": {
                "keyword": {
                    "type": "keyword",
                    "ignore_above": 512,
                },
            },
        },
        "url": {
            "type": "keyword",
        },
        "description": {
            "type": "text",
            "analyzer": "document_text",
        },
        "content": {
            "type": "text",
            "analyzer": "document_text",
        },
    }
}


def initial_index_name() -> str:
    return f"{INDEX_NAME}_v1"


async def create_index(client: AsyncElasticsearch) -> None:
    alias_exists = await client.indices.exists_alias(
        name=INDEX_NAME,
    )

    if alias_exists:
        return

    physical_index_exists = await client.indices.exists(
        index=INDEX_NAME,
    )

    if physical_index_exists:
        raise RuntimeError(
            f"Index '{INDEX_NAME}' exists as a physical index "
            "but is not configured as the application alias"
        )

    index_name = initial_index_name()

    index_exists = await client.indices.exists(
        index=index_name,
    )

    if not index_exists:
        await client.indices.create(
            index=index_name,
            settings=DOCUMENT_SETTINGS,
            mappings=DOCUMENT_MAPPING,
        )

    await client.indices.put_alias(
        index=index_name,
        name=INDEX_NAME,
        is_write_index=True,
    )
