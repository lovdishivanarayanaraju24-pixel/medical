import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

MIGRATIONS = [
    # Version 1: Core database tables
    """
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        dob TEXT,
        gender TEXT,
        contact_info TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        report_type TEXT, -- 'lab', 'prescription', 'discharge', 'other'
        hospital TEXT,
        doctor TEXT,
        report_date TEXT,
        source_file_path TEXT,
        raw_ocr_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER,
        test_name TEXT NOT NULL,
        value REAL,
        unit TEXT,
        reference_range_low REAL,
        reference_range_high REAL,
        flag TEXT, -- 'normal', 'high', 'low', 'critical'
        category TEXT, -- e.g., 'liver', 'kidney', 'blood', etc.
        FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS medications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER,
        medicine_name TEXT NOT NULL,
        dosage TEXT,
        frequency TEXT,
        duration TEXT,
        instructions TEXT,
        FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER,
        vector_blob BLOB NOT NULL,
        model_name TEXT NOT NULL,
        FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
    );
    """,
    # Version 2: Indexing and FTS5 Virtual Table for Fast Keyword Search
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS reports_fts USING fts5(
        report_id UNINDEXED,
        content
    );
    """
]

def get_connection(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def run_migrations(db_path: str):
    logger.info(f"Running migrations on database: {db_path}")
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Create the migration tracker table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_versions (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    
    # Check current version
    cursor.execute("SELECT MAX(version) FROM schema_versions")
    row = cursor.fetchone()
    current_version = row[0] if row[0] is not None else 0
    
    logger.info(f"Current schema version: {current_version}")
    
    for i, migration in enumerate(MIGRATIONS, 1):
        if i > current_version:
            logger.info(f"Applying migration version {i}...")
            try:
                cursor.execute(migration)
                cursor.execute("INSERT INTO schema_versions (version) VALUES (?)", (i,))
                conn.commit()
                logger.info(f"Migration version {i} applied successfully.")
            except Exception as e:
                conn.rollback()
                logger.error(f"Error applying migration version {i}: {e}")
                raise e
    
    conn.close()
    logger.info("Database migrations check completed.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db_dir = os.path.dirname(os.path.abspath(__file__))
    run_migrations(os.path.join(db_dir, "../../../medvault.db"))
