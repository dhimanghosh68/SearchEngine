import os


ELASTICSEARCH_URL = os.getenv(
    "ELASTICSEARCH_URL",
    "http://127.0.0.1:9200",
)

INDEX_NAME = os.getenv(
    "ELASTICSEARCH_INDEX",
    "documents",
)
