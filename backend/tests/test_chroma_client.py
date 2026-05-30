import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_chroma_client_no_telemetry_spam(capsys):
    from app.core.chroma_client import get_chroma_client

    path = tempfile.mkdtemp(prefix="chroma_telemetry_test_")
    client = get_chroma_client(path)
    client.get_or_create_collection("telemetry_test")
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "ClientStartEvent" not in combined
    assert "ClientCreateCollectionEvent" not in combined
    assert "capture() takes 1 positional argument" not in combined


def test_shared_chroma_settings():
    from app.core.chroma_client import get_chroma_client

    path = tempfile.mkdtemp(prefix="chroma_shared_test_")
    client = get_chroma_client(path)
    coll = client.get_or_create_collection("shared_test")
    assert coll.name == "shared_test"
