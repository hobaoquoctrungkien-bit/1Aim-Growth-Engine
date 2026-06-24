import sqlite3


def create_knowledge_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        document_no TEXT,
        document_type TEXT,
        issuing_authority TEXT,
        issue_date TEXT,
        effective_date TEXT,
        expiry_date TEXT,
        status TEXT,
        category TEXT,
        source_url TEXT,
        file_path TEXT,
        summary TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        article_no TEXT,
        clause_no TEXT,
        heading TEXT,
        content TEXT,
        keywords TEXT,
        embedding TEXT,
        status TEXT DEFAULT 'Approved',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(document_id) REFERENCES knowledge_documents(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        customer TEXT,
        commodity TEXT,
        hs_code TEXT,
        country TEXT,
        problem TEXT,
        solution TEXT,
        legal_basis TEXT,
        risk_notes TEXT,
        attachments TEXT,
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_document_tags (
        document_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        PRIMARY KEY(document_id, tag_id),
        FOREIGN KEY(document_id) REFERENCES knowledge_documents(id),
        FOREIGN KEY(tag_id) REFERENCES knowledge_tags(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_sops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        purpose TEXT,
        procedure_steps TEXT,
        checklist TEXT,
        related_documents TEXT,
        related_cases TEXT,
        category TEXT,
        status TEXT DEFAULT 'Active',
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_intelligence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intelligence_type TEXT NOT NULL,
        title TEXT NOT NULL,
        entity_name TEXT,
        country TEXT,
        lane TEXT,
        commodity TEXT,
        hs_code TEXT,
        summary TEXT,
        details TEXT,
        source TEXT,
        source_type TEXT,
        source_id INTEGER,
        confidence TEXT DEFAULT 'Medium',
        tags TEXT,
        status TEXT DEFAULT 'Active',
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS compliance_product_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT NOT NULL UNIQUE,
        description TEXT,
        managing_authority TEXT,
        status TEXT DEFAULT 'Active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS compliance_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_group_id INTEGER,
        rule_title TEXT NOT NULL,
        rule_type TEXT,
        legal_document_id INTEGER,
        article_no TEXT,
        clause_no TEXT,
        appendix_no TEXT,
        table_no TEXT,
        content TEXT,
        required_documents TEXT,
        managing_authority TEXT,
        effective_date TEXT,
        approval_status TEXT DEFAULT 'pending_review',
        confidence_score TEXT,
        source_chunk_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(product_group_id) REFERENCES compliance_product_groups(id),
        FOREIGN KEY(legal_document_id) REFERENCES knowledge_documents(id),
        FOREIGN KEY(source_chunk_id) REFERENCES knowledge_chunks(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS compliance_keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_group_id INTEGER,
        keyword TEXT NOT NULL,
        keyword_type TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(product_group_id) REFERENCES compliance_product_groups(id),
        UNIQUE(product_group_id, keyword)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS compliance_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        topic TEXT,
        product_group_id INTEGER,
        summary TEXT,
        interpretation TEXT,
        operational_guidance TEXT,
        risk_notes TEXT,
        related_documents TEXT,
        related_sops TEXT,
        related_cases TEXT,
        approval_status TEXT DEFAULT 'Pending',
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(product_group_id) REFERENCES compliance_product_groups(id)
    )
    """)


def _add_column(cur, table, column_definition):
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column_definition}")
    except sqlite3.OperationalError:
        pass


def migrate_knowledge_tables(cur):
    _add_column(cur, "knowledge_documents", "document_no TEXT")
    _add_column(cur, "knowledge_documents", "document_type TEXT")
    _add_column(cur, "knowledge_documents", "issuing_authority TEXT")
    _add_column(cur, "knowledge_documents", "issue_date TEXT")
    _add_column(cur, "knowledge_documents", "effective_date TEXT")
    _add_column(cur, "knowledge_documents", "expiry_date TEXT")
    _add_column(cur, "knowledge_documents", "status TEXT")
    _add_column(cur, "knowledge_documents", "category TEXT")
    _add_column(cur, "knowledge_documents", "source_url TEXT")
    _add_column(cur, "knowledge_documents", "file_path TEXT")
    _add_column(cur, "knowledge_documents", "summary TEXT")
    _add_column(cur, "knowledge_documents", "related_product_group TEXT")
    _add_column(cur, "knowledge_documents", "approval_status TEXT DEFAULT 'Approved'")
    _add_column(cur, "knowledge_documents", "extracted_text TEXT")
    _add_column(cur, "knowledge_documents", "parser_raw_json TEXT")
    _add_column(cur, "knowledge_documents", "parser_provider TEXT")
    _add_column(cur, "knowledge_documents", "parser_confidence TEXT")
    _add_column(cur, "knowledge_documents", "parser_warnings TEXT")
    _add_column(cur, "knowledge_documents", "metadata_review_status TEXT DEFAULT 'needs_review'")
    _add_column(cur, "knowledge_documents", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    _add_column(cur, "knowledge_chunks", "article_no TEXT")
    _add_column(cur, "knowledge_chunks", "clause_no TEXT")
    _add_column(cur, "knowledge_chunks", "heading TEXT")
    _add_column(cur, "knowledge_chunks", "content TEXT")
    _add_column(cur, "knowledge_chunks", "keywords TEXT")
    _add_column(cur, "knowledge_chunks", "embedding TEXT")
    _add_column(cur, "knowledge_chunks", "status TEXT DEFAULT 'Approved'")
    _add_column(cur, "knowledge_cases", "customer TEXT")
    _add_column(cur, "knowledge_cases", "commodity TEXT")
    _add_column(cur, "knowledge_cases", "hs_code TEXT")
    _add_column(cur, "knowledge_cases", "country TEXT")
    _add_column(cur, "knowledge_cases", "problem TEXT")
    _add_column(cur, "knowledge_cases", "solution TEXT")
    _add_column(cur, "knowledge_cases", "legal_basis TEXT")
    _add_column(cur, "knowledge_cases", "risk_notes TEXT")
    _add_column(cur, "knowledge_cases", "attachments TEXT")
    _add_column(cur, "knowledge_cases", "approval_status TEXT DEFAULT 'Approved'")
    _add_column(cur, "knowledge_cases", "created_by TEXT")
    _add_column(cur, "knowledge_cases", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    _add_column(cur, "knowledge_sops", "purpose TEXT")
    _add_column(cur, "knowledge_sops", "procedure_steps TEXT")
    _add_column(cur, "knowledge_sops", "checklist TEXT")
    _add_column(cur, "knowledge_sops", "related_documents TEXT")
    _add_column(cur, "knowledge_sops", "related_cases TEXT")
    _add_column(cur, "knowledge_sops", "category TEXT")
    _add_column(cur, "knowledge_sops", "status TEXT DEFAULT 'Active'")
    _add_column(cur, "knowledge_sops", "approval_status TEXT DEFAULT 'Approved'")
    _add_column(cur, "knowledge_sops", "created_by TEXT")
    _add_column(cur, "knowledge_sops", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    _add_column(cur, "knowledge_intelligence", "intelligence_type TEXT")
    _add_column(cur, "knowledge_intelligence", "title TEXT")
    _add_column(cur, "knowledge_intelligence", "entity_name TEXT")
    _add_column(cur, "knowledge_intelligence", "country TEXT")
    _add_column(cur, "knowledge_intelligence", "lane TEXT")
    _add_column(cur, "knowledge_intelligence", "commodity TEXT")
    _add_column(cur, "knowledge_intelligence", "hs_code TEXT")
    _add_column(cur, "knowledge_intelligence", "summary TEXT")
    _add_column(cur, "knowledge_intelligence", "details TEXT")
    _add_column(cur, "knowledge_intelligence", "source TEXT")
    _add_column(cur, "knowledge_intelligence", "source_type TEXT")
    _add_column(cur, "knowledge_intelligence", "source_id INTEGER")
    _add_column(cur, "knowledge_intelligence", "confidence TEXT DEFAULT 'Medium'")
    _add_column(cur, "knowledge_intelligence", "tags TEXT")
    _add_column(cur, "knowledge_intelligence", "status TEXT DEFAULT 'Active'")
    _add_column(cur, "knowledge_intelligence", "approval_status TEXT DEFAULT 'Approved'")
    _add_column(cur, "knowledge_intelligence", "created_by TEXT")
    _add_column(cur, "knowledge_intelligence", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    _add_column(cur, "compliance_product_groups", "description TEXT")
    _add_column(cur, "compliance_product_groups", "managing_authority TEXT")
    _add_column(cur, "compliance_product_groups", "status TEXT DEFAULT 'Active'")
    _add_column(cur, "compliance_rules", "appendix_no TEXT")
    _add_column(cur, "compliance_rules", "table_no TEXT")
    _add_column(cur, "compliance_rules", "required_documents TEXT")
    _add_column(cur, "compliance_rules", "approval_status TEXT DEFAULT 'pending_review'")
    _add_column(cur, "compliance_rules", "confidence_score TEXT")
    _add_column(cur, "compliance_rules", "source_chunk_id INTEGER")
    _add_column(cur, "compliance_notes", "topic TEXT")
    _add_column(cur, "compliance_notes", "approval_status TEXT DEFAULT 'Pending'")

