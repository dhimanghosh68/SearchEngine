from apps.api.core.application import create_application_runtime
from apps.api.platform.contracts import RuntimePaths


def test_application_runtime_is_composed():
    application = create_application_runtime(
        elasticsearch_url="http://127.0.0.1:9200",
        index_name="documents",
        paths=RuntimePaths(
            config="config",
            data="data",
            cache="cache",
            logs="logs",
            runtime="runtime",
        ),
    )

    assert application.runtime.capabilities is not None
    assert application.runtime.policy is not None
    assert application.config.service_name == "search-engine"
    assert application.config.elasticsearch_url == (
        "http://127.0.0.1:9200"
    )
    assert application.config.index_name == "documents"
    assert application.metadata is not None
    assert application.downloads is not None
