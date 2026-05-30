from app.services.documents_services import chunk_text


def test_chunk_text_deduplicates_and_filters_short_chunks():
    text = "Short.\n\n" + ("This is a meaningful chunk about retrieval. " * 40)
    chunks = chunk_text(text)
    assert chunks
    assert all(len(chunk) >= 32 for chunk in chunks)
    assert len(chunks) < 80


def test_chunk_text_respects_max_chunks(monkeypatch):
    monkeypatch.setenv("INGEST_MAX_CHUNKS", "5")
    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    text = "Paragraph one with enough content to index. " * 200
    chunks = chunk_text(text)
    assert len(chunks) <= 5
