from fastapi import APIRouter, HTTPException

from app.database import get_connection
from app.services.comparison import compare_paragraphs

router = APIRouter(prefix="/api", tags=["Plagiarism Detection"])


@router.post("/compare/{document_id}")
def compare_document(document_id: int):
    connection = get_connection()

    try:
        target_document = connection.execute(
            "SELECT * FROM documents WHERE id = ?",
            (document_id,)
        ).fetchone()

        if not target_document:
            raise HTTPException(
                status_code=404,
                detail="Document not found."
            )

        target_paragraphs = connection.execute(
            """
            SELECT id, paragraph_number, content
            FROM paragraphs
            WHERE document_id = ?
            ORDER BY paragraph_number
            """,
            (document_id,)
        ).fetchall()

        source_paragraphs = connection.execute(
            """
            SELECT
                p.id,
                p.document_id,
                p.paragraph_number,
                p.content,
                d.filename
            FROM paragraphs p
            JOIN documents d ON d.id = p.document_id
            WHERE p.document_id != ?
            ORDER BY p.document_id, p.paragraph_number
            """,
            (document_id,)
        ).fetchall()

        if not source_paragraphs:
            return {
                "message": "Upload another document to enable comparison.",
                "document_id": document_id,
                "compared_documents": 0,
                "matched_paragraphs": 0,
                "matches": []
            }

        results = compare_paragraphs(
            [dict(row) for row in target_paragraphs],
            [dict(row) for row in source_paragraphs]
        )

        connection.execute(
            "DELETE FROM matches WHERE document_id = ?",
            (document_id,)
        )

        for result in results:
            source_url = f"local://document/{result['source_document_id']}"

            connection.execute(
                """
                INSERT OR IGNORE INTO sources
                (title, url, source_type, extracted_text)
                VALUES (?, ?, 'local_document', ?)
                """,
                (
                    result["source_filename"],
                    source_url,
                    result["source_text"]
                )
            )

            source = connection.execute(
                "SELECT id FROM sources WHERE url = ?",
                (source_url,)
            ).fetchone()

            connection.execute(
                """
                INSERT INTO matches (
                    document_id,
                    paragraph_id,
                    source_id,
                    match_type,
                    lexical_score,
                    matched_text,
                    source_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    result["paragraph_id"],
                    source["id"],
                    "exact" if result["similarity"] == 100 else "near_exact",
                    result["similarity"] / 100,
                    result["matched_text"],
                    result["source_text"]
                )
            )

        connection.commit()

        matched_sources = len({
            result["source_document_id"] for result in results
        })

        average_similarity = (
            round(
                sum(item["similarity"] for item in results) / len(results),
                2
            )
            if results else 0
        )

        return {
            "message": "Local document comparison completed.",
            "document_id": document_id,
            "filename": target_document["filename"],
            "compared_documents": len({
                row["document_id"] for row in source_paragraphs
            }),
            "matched_paragraphs": len(results),
            "matching_source_documents": matched_sources,
            "average_match_similarity": average_similarity,
            "matches": results
        }

    finally:
        connection.close()