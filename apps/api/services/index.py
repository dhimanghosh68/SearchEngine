from elasticsearch import AsyncElasticsearch


INDEX_NAME = "documents"


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


async def create_index(client: AsyncElasticsearch) -> None:
    exists = await client.indices.exists(index=INDEX_NAME)

    if not exists:
        await client.indices.create(
            index=INDEX_NAME,
            mappings=DOCUMENT_MAPPING,
        )
