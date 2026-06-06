from app.services.citation_service import format_cited_context, normalize_citation


def test_normalize_citation_adds_stable_metadata():
    source = {
        "title": "Architecture",
        "source": "AWS_Architecture.pdf",
        "chunk": "Use private subnets for application services.",
        "metadata": {
            "document_id": "12",
            "chunk_index": 47,
            "page_number": 5,
        },
    }

    normalized = normalize_citation(source, 0)

    assert normalized["metadata"]["citation_id"] == "S1"
    assert normalized["metadata"]["document_name"] == "AWS_Architecture.pdf"
    assert normalized["metadata"]["page_number"] == 5
    assert normalized["metadata"]["chunk_id"] == "12:47"
    assert "p.5" in normalized["metadata"]["source_reference"]


def test_format_cited_context_prefixes_chunks():
    chunks = format_cited_context(
        [
            {
                "source": "AWS_Architecture.pdf",
                "chunk": "Use private subnets for application services.",
                "metadata": {"page_number": 12, "chunk_index": 47},
            }
        ]
    )

    assert chunks == [
        "[S1] Document: AWS_Architecture.pdf | Page: 12 | Chunk: AWS_Architecture.pdf:47\n"
        "Use private subnets for application services."
    ]
