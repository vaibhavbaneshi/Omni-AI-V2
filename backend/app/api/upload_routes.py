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

@router.post("/upload")

async def upload_document(
    file: UploadFile = File(...)
):

    file_path = os.path.join(
        UPLOAD_DIR,
        file.filename
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