import uuid
import zipfile
from io import BytesIO
from pathlib import Path

import fitz
from docx import Document
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.database import get_connection, BASE_DIR

router = APIRouter(prefix="/api", tags=["Documents"])

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def extract_pdf(data):
    text = ""

    with fitz.open(stream=data, filetype="pdf") as pdf:
        for page in pdf:
            text += page.get_text() + "\n"

    return text


def extract_docx(data):
    document = Document(BytesIO(data))

    paragraphs = [p.text for p in document.paragraphs]

    for table in document.tables:
        for row in table.rows:
            paragraphs.append(" ".join(cell.text for cell in row.cells))

    return "\n".join(paragraphs)


def extract_txt(data):
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="TXT file must use UTF-8 encoding."
        )


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    original_name = Path(file.filename or "").name
    extension = Path(original_name).suffix.lower()

    if not original_name or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX, and TXT files are supported."
        )

    data = await file.read(MAX_FILE_SIZE + 1)

    if not data:
        raise HTTPException(status_code=400, detail="The file is empty.")

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size must not exceed 10 MB."
        )

    if extension == ".pdf":
        if not data.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="Invalid PDF file.")
        extracted_text = extract_pdf(data)

    elif extension == ".docx":
        if not zipfile.is_zipfile(BytesIO(data)):
            raise HTTPException(status_code=400, detail="Invalid DOCX file.")

        try:
            extracted_text = extract_docx(data)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Could not read the DOCX file."
            )

    else:
        extracted_text = extract_txt(data)

    extracted_text = extracted_text.replace("\x00", "").strip()

    if not extracted_text:
        raise HTTPException(
            status_code=400,
            detail="No readable text found in the document."
        )

    paragraph_list = [
        paragraph.strip()
        for paragraph in extracted_text.splitlines()
        if paragraph.strip()
    ]

    stored_name = f"{uuid.uuid4().hex}{extension}"
    stored_path = UPLOAD_DIR / stored_name

    stored_path.write_bytes(data)

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO documents (filename, file_type, extracted_text)
            VALUES (?, ?, ?)
            """,
            (original_name, extension[1:], extracted_text)
        )

        document_id = cursor.lastrowid

        for number, paragraph in enumerate(paragraph_list, start=1):
            connection.execute(
                """
                INSERT INTO paragraphs
                (document_id, paragraph_number, content)
                VALUES (?, ?, ?)
                """,
                (document_id, number, paragraph)
            )

        connection.commit()

    except Exception:
        connection.rollback()
        stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="Could not save the document."
        )

    finally:
        connection.close()

    return {
        "message": "Document uploaded successfully.",
        "document_id": document_id,
        "filename": original_name,
        "file_type": extension[1:],
        "paragraph_count": len(paragraph_list),
        "character_count": len(extracted_text),
        "preview": extracted_text[:500]
    }