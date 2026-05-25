from app.services.retrieval_cache import cache_retrieval_result, get_retrieval_cache


def test_retrieval_cache_roundtrip():
    cache_retrieval_result(
        query="cache test",
        user_id=1,
        workspace_id="default",
        collection_id=None,
        value="cached-context",
    )
    cached = get_retrieval_cache(
        query="cache test",
        user_id=1,
        workspace_id="default",
        collection_id=None,
    )
    assert cached == "cached-context"
