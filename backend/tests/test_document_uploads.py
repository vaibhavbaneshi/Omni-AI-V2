import tempfile
from pathlib import Path

import pytest

from app.core.supported_uploads import ALLOWED_EXTENSIONS, SUPPORTED_UPLOADS_LABEL
from app.core.upload_validation import PDF_MAGIC, validate_document_upload
from app.services.document_loaders import DocumentLoadError, load_document


def test_supported_extensions_include_common_formats():
    assert {".pdf", ".txt", ".docx", ".csv", ".xlsx", ".xls"}.issubset(ALLOWED_EXTENSIONS)


def test_supported_uploads_label():
    assert "PDF" in SUPPORTED_UPLOADS_LABEL
    assert "CSV" in SUPPORTED_UPLOADS_LABEL


def test_pdf_magic_constant():
    assert PDF_MAGIC == b"%PDF"


def test_load_txt(tmp_path: Path):
    file_path = tmp_path / "notes.txt"
    file_path.write_text("Hello from a text file.", encoding="utf-8")
    assert load_document(str(file_path)) == "Hello from a text file."


def test_load_csv(tmp_path: Path):
    file_path = tmp_path / "data.csv"
    file_path.write_text("name,score\nAlice,10\nBob,20\n", encoding="utf-8")
    text = load_document(str(file_path))
    assert "Alice" in text
    assert "Bob" in text


def test_load_empty_txt_raises(tmp_path: Path):
    file_path = tmp_path / "empty.txt"
    file_path.write_text("   \n", encoding="utf-8")
    with pytest.raises(DocumentLoadError):
        load_document(str(file_path))


class _FakeUpload:
    def __init__(self, filename: str, content: bytes, content_type: str | None = None):
        self.filename = filename
        self.content_type = content_type
        self._content = content
        self._pos = 0

    async def read(self, size: int = -1) -> bytes:
        if size == -1:
            chunk = self._content[self._pos :]
            self._pos = len(self._content)
            return chunk
        chunk = self._content[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk

    async def seek(self, pos: int) -> None:
        self._pos = pos


@pytest.mark.asyncio
async def test_validate_document_upload_rejects_unknown_extension():
    upload = _FakeUpload("image.png", b"PNG", content_type="image/png")
    with pytest.raises(Exception) as exc:
        await validate_document_upload(upload, max_bytes=1024)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_validate_document_upload_accepts_txt():
    upload = _FakeUpload("notes.txt", b"hello", content_type="text/plain")
    await validate_document_upload(upload, max_bytes=1024)
