import os

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)

from app.services.documents_services import (
    process_document
)

router = APIRouter()

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".pdf"}

@router.post("/upload")

async def upload_document(
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided"
        )

    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF uploads are supported"
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    safe_name = os.path.basename(file.filename)
    file_path = os.path.join(
        UPLOAD_DIR,
        safe_name
    )

    with open(file_path, "wb") as f:

        content = await file.read()

        f.write(content)

    try:

        chunk_count = process_document(
            file_path=file_path,
            filename=file.filename
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    return {
        "message": "Document uploaded successfully",
        "chunks_created": chunk_count
    }