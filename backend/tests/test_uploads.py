from app.core.upload_validation import PDF_MAGIC


def test_pdf_magic_constant():
    assert PDF_MAGIC == b"%PDF"
