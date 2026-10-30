import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compare_paragraphs(target_paragraphs, source_paragraphs):
    results = []

    for target in target_paragraphs:
        target_text = normalize_text(target["content"])

        if len(target_text) < 30:
            continue

        best_match = None
        best_score = 0.0

        for source in source_paragraphs:
            source_text = normalize_text(source["content"])

            if len(source_text) < 30:
                continue

            if target_text == source_text:
                score = 1.0
            else:
                vectorizer = TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    lowercase=True
                )

                try:
                    vectors = vectorizer.fit_transform(
                        [target_text, source_text]
                    )
                    score = float(
                        cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
                    )
                except ValueError:
                    score = 0.0

            if score > best_score:
                best_score = score
                best_match = source

        if best_match and best_score >= 0.30:
            results.append({
                "paragraph_id": target["id"],
                "paragraph_number": target["paragraph_number"],
                "matched_text": target["content"],
                "source_document_id": best_match["document_id"],
                "source_filename": best_match["filename"],
                "source_text": best_match["content"],
                "similarity": round(best_score * 100, 2)
            })

    return results