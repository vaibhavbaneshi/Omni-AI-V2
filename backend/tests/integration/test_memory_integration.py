"""Integration tests — user memory CRUD."""

def test_memory_crud(auth_client):
    create = auth_client.post(
        "/memory?content=Prefers+dark+mode&category=preference&importance=0.8",
        headers=auth_client.auth_headers,
    )
    assert create.status_code == 200
    memory_id = create.json()["id"]

    listing = auth_client.get("/memory", headers=auth_client.auth_headers)
    assert listing.status_code == 200
    memories = listing.json()["memories"]
    assert any(item["id"] == memory_id for item in memories)

    deleted = auth_client.delete(
        f"/memory/{memory_id}",
        headers=auth_client.auth_headers,
    )
    assert deleted.status_code == 200

    listing_after = auth_client.get("/memory", headers=auth_client.auth_headers)
    assert all(item["id"] != memory_id for item in listing_after.json()["memories"])


def test_delete_missing_memory_returns_404(auth_client):
    response = auth_client.delete("/memory/99999", headers=auth_client.auth_headers)
    assert response.status_code == 404
