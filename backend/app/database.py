
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "plagx.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = get_connection()

    connection.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            extracted_text TEXT,
            language TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS paragraphs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            paragraph_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (document_id)
                REFERENCES documents(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT UNIQUE,
            source_type TEXT NOT NULL,
            extracted_text TEXT,
            retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            paragraph_id INTEGER,
            source_id INTEGER,
            match_type TEXT NOT NULL,
            lexical_score REAL DEFAULT 0,
            semantic_score REAL DEFAULT 0,
            matched_text TEXT,
            source_text TEXT,
            FOREIGN KEY (document_id)
                REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (paragraph_id)
                REFERENCES paragraphs(id) ON DELETE SET NULL,
            FOREIGN KEY (source_id)
                REFERENCES sources(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            overall_score REAL DEFAULT 0,
            report_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id)
                REFERENCES documents(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS search_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            results_count INTEGER DEFAULT 0,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    connection.commit()
    connection.close()
