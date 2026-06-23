import email
import imaplib
import sqlite3
import smtplib
import re
import socket
import ssl
import time
import uuid
from datetime import date
from datetime import datetime
from datetime import timedelta
from email.message import EmailMessage
from email.header import decode_header
from email.utils import parseaddr
from html import escape, unescape
from pathlib import Path

DB_PATH = Path("data/growth_engine.db")
BACKUP_DIR = Path("data/backups")
MAX_BACKUPS = 30
_BACKUP_CREATED_THIS_PROCESS = False


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_database_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        return None

    backup_path = None
    for _ in range(5):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        candidate_path = BACKUP_DIR / f"growth_engine_{timestamp}.db"
        if not candidate_path.exists():
            backup_path = candidate_path
            break
        time.sleep(1)

    if backup_path is None:
        raise FileExistsError("Could not create a unique timestamped database backup.")

    source = sqlite3.connect(DB_PATH)
    try:
        destination = sqlite3.connect(backup_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()

    prune_database_backups()
    return backup_path


def create_database_backup_once():
    global _BACKUP_CREATED_THIS_PROCESS

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if _BACKUP_CREATED_THIS_PROCESS:
        return None

    backup_path = create_database_backup()
    _BACKUP_CREATED_THIS_PROCESS = True
    return backup_path


def get_database_backups():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(
        BACKUP_DIR.glob("growth_engine_*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def prune_database_backups():
    backups = get_database_backups()
    for backup_path in backups[MAX_BACKUPS:]:
        backup_path.unlink(missing_ok=True)


def get_database_backup_status():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = get_database_backups()
    latest_backup = backups[0] if backups else None

    return {
        "db_size_bytes": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
        "backup_count": len(backups),
        "latest_backup_time": (
            datetime.fromtimestamp(latest_backup.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            if latest_backup
            else ""
        ),
        "latest_backup_name": latest_backup.name if latest_backup else "",
    }


def init_db():
    create_database_backup_once()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        country TEXT,
        type TEXT,
        strength TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS organizations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT DEFAULT 'Other',
        country TEXT,
        province TEXT,
        city TEXT,
        website TEXT,
        local_name TEXT,
        founding_date TEXT,
        anniversary_date TEXT,
        preferred_language TEXT,
        relationship_tone TEXT,
        customer_status TEXT DEFAULT 'Prospect',
        source TEXT,
        membership TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        organization_id INTEGER,
        full_name TEXT NOT NULL,
        name TEXT,
        email TEXT,
        email_status TEXT DEFAULT 'Unknown',
        wechat TEXT,
        whatsapp TEXT,
        phone TEXT,
        title TEXT,
        job_title TEXT,
        source TEXT,
        relationship_status TEXT DEFAULT 'New',
        birthday TEXT,
        preferred_language TEXT,
        preferred_channel TEXT,
        relationship_tone TEXT,
        relationship_score INTEGER DEFAULT 5,
        last_touch_at TEXT,
        last_contacted_at TEXT,
        next_touch_at TEXT,
        next_follow_up_at TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(organization_id) REFERENCES organizations(id),
        FOREIGN KEY(company_id) REFERENCES companies(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER,
        contact_id INTEGER,
        company_name TEXT,
        contact_person TEXT,
        country TEXT,
        city TEXT,
        job_title TEXT,
        phone TEXT,
        email TEXT,
        wechat TEXT,
        whatsapp TEXT,
        membership TEXT,
        source TEXT,
        campaign TEXT,
        lead_status TEXT DEFAULT 'New',
        interest_level TEXT,
        priority_score INTEGER DEFAULT 0,
        action_score INTEGER DEFAULT 0,
        next_action TEXT,
        next_action_date TEXT,
        status TEXT DEFAULT 'New Lead',
        owner TEXT DEFAULT 'admin',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_contacted_at TEXT,
        converted_contact_id INTEGER,
        notes TEXT,
        FOREIGN KEY(organization_id) REFERENCES organizations(id),
        FOREIGN KEY(contact_id) REFERENCES contacts(id),
        FOREIGN KEY(converted_contact_id) REFERENCES contacts(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER,
        contact_id INTEGER,
        opportunity_name TEXT,
        title TEXT NOT NULL,
        route TEXT,
        commodity TEXT,
        volume TEXT,
        cargo_description TEXT,
        origin TEXT,
        destination TEXT,
        weight TEXT,
        container_type TEXT,
        quantity TEXT,
        incoterm TEXT,
        quotation_status TEXT DEFAULT 'Not Started',
        mode TEXT,
        stage TEXT DEFAULT 'Interested',
        trade_lane TEXT,
        service_type TEXT,
        potential_revenue REAL DEFAULT 0,
        potential_profit REAL DEFAULT 0,
        expected_close_date TEXT,
        next_action TEXT,
        next_action_date TEXT,
        notes TEXT,
        status TEXT DEFAULT 'new',
        owner INTEGER,
        inquiry_text TEXT,
        inquiry_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(owner) REFERENCES users(id),
        FOREIGN KEY(organization_id) REFERENCES organizations(id),
        FOREIGN KEY(contact_id) REFERENCES contacts(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS quotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opportunity_id INTEGER,
        quote_no TEXT,
        quote_date TEXT,
        valid_until TEXT,
        currency TEXT DEFAULT 'USD',
        sell_amount REAL,
        status TEXT DEFAULT 'draft',
        template_name TEXT,
        version INTEGER DEFAULT 1,
        parent_quotation_id INTEGER,
        customer_name TEXT,
        contact_name TEXT,
        trade_lane TEXT,
        service_type TEXT,
        payment_terms TEXT,
        prepared_by TEXT,
        approved_at TEXT,
        approved_by TEXT,
        sent_at TEXT,
        owner INTEGER,
        follow_up_date TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(owner) REFERENCES users(id),
        FOREIGN KEY(parent_quotation_id) REFERENCES quotations(id),
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS quotation_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quotation_id INTEGER NOT NULL,
        line_no INTEGER DEFAULT 1,
        description TEXT NOT NULL,
        basis TEXT,
        quantity REAL DEFAULT 1,
        unit_price REAL DEFAULT 0,
        currency TEXT DEFAULT 'USD',
        amount REAL DEFAULT 0,
        cost_amount REAL DEFAULT 0,
        margin_amount REAL DEFAULT 0,
        vendor_name TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(quotation_id) REFERENCES quotations(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS quotation_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name TEXT NOT NULL UNIQUE,
        header_text TEXT,
        footer_text TEXT,
        payment_terms TEXT,
        validity_days INTEGER DEFAULT 14,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vendor_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opportunity_id INTEGER NOT NULL,
        quotation_id INTEGER,
        vendor_type TEXT NOT NULL,
        vendor_name TEXT,
        charge_type TEXT,
        charge_name TEXT NOT NULL,
        basis TEXT,
        currency TEXT DEFAULT 'USD',
        cost_amount REAL DEFAULT 0,
        margin_percent REAL DEFAULT 0,
        margin_amount REAL DEFAULT 0,
        suggested_sell_amount REAL DEFAULT 0,
        transit_time TEXT,
        valid_until TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id),
        FOREIGN KEY(quotation_id) REFERENCES quotations(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        organization_id INTEGER,
        contact_id INTEGER,
        opportunity_id INTEGER,
        quotation_id INTEGER,
        activity_type TEXT,
        description TEXT,
        user TEXT,
        summary TEXT,
        activity_at TEXT DEFAULT CURRENT_TIMESTAMP,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS relationship_occasions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER,
        contact_id INTEGER,
        occasion_type TEXT,
        occasion_name TEXT,
        occasion_date TEXT,
        country TEXT,
        is_recurring INTEGER DEFAULT 1,
        recurrence_rule TEXT,
        preferred_channel TEXT,
        preferred_language TEXT,
        message_tone TEXT,
        reminder_days_before INTEGER DEFAULT 7,
        status TEXT DEFAULT 'Active',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS holiday_library (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country TEXT,
        holiday_name TEXT,
        holiday_date TEXT,
        is_recurring INTEGER DEFAULT 1,
        recurrence_rule TEXT,
        default_message_theme TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS outreach_campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_name TEXT NOT NULL,
        country_filter TEXT,
        membership_filter TEXT,
        lead_status_filter TEXT,
        relationship_status_filter TEXT,
        status TEXT DEFAULT 'Draft',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        approved_at TEXT,
        sent_at TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS outreach_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL,
        lead_id INTEGER,
        organization_id INTEGER,
        contact_id INTEGER,
        email TEXT,
        subject TEXT,
        message_body TEXT,
        message_version INTEGER DEFAULT 1,
        tracking_token TEXT,
        status TEXT DEFAULT 'Draft',
        delivery_status TEXT DEFAULT 'Unknown',
        sent_at TEXT,
        opened_at TEXT,
        replied_at TEXT,
        qualified_at TEXT,
        error_message TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(campaign_id) REFERENCES outreach_campaigns(id),
        FOREIGN KEY(lead_id) REFERENCES leads(id),
        FOREIGN KEY(organization_id) REFERENCES organizations(id),
        FOREIGN KEY(contact_id) REFERENCES contacts(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS processed_reply_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT NOT NULL UNIQUE,
        processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        outreach_message_id INTEGER,
        sender_email TEXT,
        subject TEXT,
        FOREIGN KEY(outreach_message_id) REFERENCES outreach_messages(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS processed_bounce_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT NOT NULL UNIQUE,
        processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        bounced_email TEXT,
        bounce_type TEXT,
        reason TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS outreach_campaign_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name TEXT NOT NULL UNIQUE,
        campaign_name TEXT,
        subject_template TEXT,
        instructions TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS backup_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        commit_hash TEXT,
        branch TEXT,
        status TEXT,
        message TEXT
    )
    """)

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
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id INTEGER,
        opportunity_id INTEGER,
        quotation_id INTEGER,
        task_type TEXT,
        title TEXT NOT NULL,
        channel TEXT,
        campaign_name TEXT,
        due_date TEXT,
        status TEXT DEFAULT 'open',
        priority TEXT DEFAULT 'normal',
        assigned_to INTEGER,
        created_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        FOREIGN KEY(assigned_to) REFERENCES users(id),
        FOREIGN KEY(created_by) REFERENCES users(id)
    )
    """)

    def add_column(table, column_definition):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column_definition}")
        except sqlite3.OperationalError:
            pass

    add_column("tasks", "channel TEXT")
    add_column("tasks", "campaign_name TEXT")
    add_column("contacts", "email_status TEXT DEFAULT 'Unknown'")
    add_column("outreach_campaigns", "country_filter TEXT")
    add_column("outreach_campaigns", "membership_filter TEXT")
    add_column("outreach_campaigns", "lead_status_filter TEXT")
    add_column("outreach_campaigns", "relationship_status_filter TEXT")
    add_column("outreach_campaigns", "subject_template TEXT")
    add_column("outreach_campaigns", "instructions TEXT")
    add_column("outreach_campaigns", "status TEXT DEFAULT 'Draft'")
    add_column("outreach_campaigns", "approved_at TEXT")
    add_column("outreach_campaigns", "sent_at TEXT")
    add_column("outreach_campaigns", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    add_column("outreach_messages", "message_version INTEGER DEFAULT 1")
    add_column("outreach_messages", "tracking_token TEXT")
    add_column("outreach_messages", "delivery_status TEXT DEFAULT 'Unknown'")
    add_column("outreach_messages", "opened_at TEXT")
    add_column("outreach_messages", "replied_at TEXT")
    add_column("outreach_messages", "qualified_at TEXT")
    add_column("outreach_messages", "error_message TEXT")
    add_column("outreach_campaign_templates", "campaign_name TEXT")
    add_column("outreach_campaign_templates", "subject_template TEXT")
    add_column("outreach_campaign_templates", "instructions TEXT")
    add_column("backup_history", "commit_hash TEXT")
    add_column("backup_history", "branch TEXT")
    add_column("backup_history", "status TEXT")
    add_column("backup_history", "message TEXT")
    add_column("knowledge_documents", "document_no TEXT")
    add_column("knowledge_documents", "document_type TEXT")
    add_column("knowledge_documents", "issuing_authority TEXT")
    add_column("knowledge_documents", "issue_date TEXT")
    add_column("knowledge_documents", "effective_date TEXT")
    add_column("knowledge_documents", "expiry_date TEXT")
    add_column("knowledge_documents", "status TEXT")
    add_column("knowledge_documents", "category TEXT")
    add_column("knowledge_documents", "source_url TEXT")
    add_column("knowledge_documents", "file_path TEXT")
    add_column("knowledge_documents", "summary TEXT")
    add_column("knowledge_documents", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    add_column("knowledge_chunks", "article_no TEXT")
    add_column("knowledge_chunks", "clause_no TEXT")
    add_column("knowledge_chunks", "heading TEXT")
    add_column("knowledge_chunks", "content TEXT")
    add_column("knowledge_chunks", "keywords TEXT")
    add_column("knowledge_chunks", "embedding TEXT")
    add_column("knowledge_chunks", "status TEXT DEFAULT 'Approved'")
    add_column("knowledge_cases", "customer TEXT")
    add_column("knowledge_cases", "commodity TEXT")
    add_column("knowledge_cases", "hs_code TEXT")
    add_column("knowledge_cases", "country TEXT")
    add_column("knowledge_cases", "problem TEXT")
    add_column("knowledge_cases", "solution TEXT")
    add_column("knowledge_cases", "legal_basis TEXT")
    add_column("knowledge_cases", "risk_notes TEXT")
    add_column("knowledge_cases", "attachments TEXT")
    add_column("knowledge_cases", "created_by TEXT")
    add_column("knowledge_cases", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    add_column("knowledge_sops", "purpose TEXT")
    add_column("knowledge_sops", "procedure_steps TEXT")
    add_column("knowledge_sops", "checklist TEXT")
    add_column("knowledge_sops", "related_documents TEXT")
    add_column("knowledge_sops", "related_cases TEXT")
    add_column("knowledge_sops", "category TEXT")
    add_column("knowledge_sops", "status TEXT DEFAULT 'Active'")
    add_column("knowledge_sops", "created_by TEXT")
    add_column("knowledge_sops", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    add_column("knowledge_intelligence", "intelligence_type TEXT")
    add_column("knowledge_intelligence", "title TEXT")
    add_column("knowledge_intelligence", "entity_name TEXT")
    add_column("knowledge_intelligence", "country TEXT")
    add_column("knowledge_intelligence", "lane TEXT")
    add_column("knowledge_intelligence", "commodity TEXT")
    add_column("knowledge_intelligence", "hs_code TEXT")
    add_column("knowledge_intelligence", "summary TEXT")
    add_column("knowledge_intelligence", "details TEXT")
    add_column("knowledge_intelligence", "source TEXT")
    add_column("knowledge_intelligence", "source_type TEXT")
    add_column("knowledge_intelligence", "source_id INTEGER")
    add_column("knowledge_intelligence", "confidence TEXT DEFAULT 'Medium'")
    add_column("knowledge_intelligence", "tags TEXT")
    add_column("knowledge_intelligence", "status TEXT DEFAULT 'Active'")
    add_column("knowledge_intelligence", "created_by TEXT")
    add_column("knowledge_intelligence", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    add_column("processed_bounce_messages", "bounced_email TEXT")
    add_column("processed_bounce_messages", "bounce_type TEXT")
    add_column("processed_bounce_messages", "reason TEXT")
    add_column("processed_reply_messages", "outreach_message_id INTEGER")
    add_column("processed_reply_messages", "sender_email TEXT")
    add_column("processed_reply_messages", "subject TEXT")
    add_column("tasks", "assigned_to INTEGER")
    add_column("tasks", "created_by INTEGER")
    add_column("activities", "lead_id INTEGER")
    add_column("activities", "organization_id INTEGER")
    add_column("activities", "description TEXT")
    add_column("activities", "user TEXT")
    add_column("opportunities", "organization_id INTEGER")
    add_column("opportunities", "opportunity_name TEXT")
    add_column("opportunities", "stage TEXT DEFAULT 'Interested'")
    add_column("opportunities", "trade_lane TEXT")
    add_column("opportunities", "service_type TEXT")
    add_column("opportunities", "cargo_description TEXT")
    add_column("opportunities", "origin TEXT")
    add_column("opportunities", "destination TEXT")
    add_column("opportunities", "weight TEXT")
    add_column("opportunities", "container_type TEXT")
    add_column("opportunities", "quantity TEXT")
    add_column("opportunities", "incoterm TEXT")
    add_column("opportunities", "quotation_status TEXT DEFAULT 'Not Started'")
    add_column("opportunities", "potential_revenue REAL DEFAULT 0")
    add_column("opportunities", "potential_profit REAL DEFAULT 0")
    add_column("opportunities", "expected_close_date TEXT")
    add_column("opportunities", "next_action TEXT")
    add_column("opportunities", "next_action_date TEXT")
    add_column("opportunities", "notes TEXT")
    add_column("opportunities", "owner INTEGER")
    add_column("quotations", "owner INTEGER")
    add_column("quotations", "template_name TEXT")
    add_column("quotations", "version INTEGER DEFAULT 1")
    add_column("quotations", "parent_quotation_id INTEGER")
    add_column("quotations", "customer_name TEXT")
    add_column("quotations", "contact_name TEXT")
    add_column("quotations", "trade_lane TEXT")
    add_column("quotations", "service_type TEXT")
    add_column("quotations", "payment_terms TEXT")
    add_column("quotations", "prepared_by TEXT")
    add_column("quotations", "approved_at TEXT")
    add_column("quotations", "approved_by TEXT")
    add_column("quotations", "sent_at TEXT")
    add_column("vendor_rates", "quotation_id INTEGER")
    add_column("vendor_rates", "vendor_type TEXT")
    add_column("vendor_rates", "vendor_name TEXT")
    add_column("vendor_rates", "charge_type TEXT")
    add_column("vendor_rates", "charge_name TEXT")
    add_column("vendor_rates", "basis TEXT")
    add_column("vendor_rates", "currency TEXT DEFAULT 'USD'")
    add_column("vendor_rates", "cost_amount REAL DEFAULT 0")
    add_column("vendor_rates", "margin_percent REAL DEFAULT 0")
    add_column("vendor_rates", "margin_amount REAL DEFAULT 0")
    add_column("vendor_rates", "suggested_sell_amount REAL DEFAULT 0")
    add_column("vendor_rates", "transit_time TEXT")
    add_column("vendor_rates", "valid_until TEXT")
    add_column("vendor_rates", "notes TEXT")
    add_column("vendor_rates", "created_at TEXT DEFAULT CURRENT_TIMESTAMP")
    add_column("vendor_rates", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    add_column("organizations", "type TEXT DEFAULT 'Other'")
    add_column("organizations", "country TEXT")
    add_column("organizations", "province TEXT")
    add_column("organizations", "city TEXT")
    add_column("organizations", "website TEXT")
    add_column("organizations", "local_name TEXT")
    add_column("organizations", "founding_date TEXT")
    add_column("organizations", "anniversary_date TEXT")
    add_column("organizations", "preferred_language TEXT")
    add_column("organizations", "relationship_tone TEXT")
    add_column("organizations", "customer_status TEXT DEFAULT 'Prospect'")
    add_column("organizations", "source TEXT")
    add_column("organizations", "membership TEXT")
    add_column("organizations", "notes TEXT")
    add_column("organizations", "created_at TEXT DEFAULT CURRENT_TIMESTAMP")
    add_column("organizations", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    add_column("contacts", "organization_id INTEGER")
    add_column("contacts", "name TEXT")
    add_column("contacts", "company_name TEXT")
    add_column("contacts", "contact_person TEXT")
    add_column("contacts", "country TEXT")
    add_column("contacts", "city TEXT")
    add_column("contacts", "job_title TEXT")
    add_column("contacts", "whatsapp TEXT")
    add_column("contacts", "membership TEXT")
    add_column("contacts", "relationship_status TEXT DEFAULT 'New'")
    add_column("contacts", "birthday TEXT")
    add_column("contacts", "preferred_language TEXT")
    add_column("contacts", "preferred_channel TEXT")
    add_column("contacts", "relationship_tone TEXT")
    add_column("contacts", "status TEXT DEFAULT 'New Lead'")
    add_column("contacts", "owner TEXT DEFAULT 'admin'")
    add_column("contacts", "last_contacted_at TEXT")
    add_column("contacts", "next_follow_up_at TEXT")
    add_column("leads", "organization_id INTEGER")
    add_column("leads", "contact_id INTEGER")
    add_column("leads", "company_name TEXT")
    add_column("leads", "contact_person TEXT")
    add_column("leads", "country TEXT")
    add_column("leads", "city TEXT")
    add_column("leads", "job_title TEXT")
    add_column("leads", "phone TEXT")
    add_column("leads", "email TEXT")
    add_column("leads", "wechat TEXT")
    add_column("leads", "whatsapp TEXT")
    add_column("leads", "membership TEXT")
    add_column("leads", "source TEXT")
    add_column("leads", "campaign TEXT")
    add_column("leads", "lead_status TEXT DEFAULT 'New'")
    add_column("leads", "interest_level TEXT")
    add_column("leads", "priority_score INTEGER DEFAULT 0")
    add_column("leads", "action_score INTEGER DEFAULT 0")
    add_column("leads", "next_action TEXT")
    add_column("leads", "next_action_date TEXT")
    add_column("leads", "status TEXT DEFAULT 'New Lead'")
    add_column("leads", "owner TEXT DEFAULT 'admin'")
    add_column("leads", "created_at TEXT DEFAULT CURRENT_TIMESTAMP")
    add_column("leads", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    add_column("leads", "last_contacted_at TEXT")
    add_column("leads", "converted_contact_id INTEGER")
    add_column("leads", "notes TEXT")

    cur.execute(
        """
        UPDATE contacts
        SET name = full_name
        WHERE name IS NULL
            AND full_name IS NOT NULL
        """
    )
    cur.execute(
        """
        UPDATE contacts
        SET contact_person = full_name
        WHERE contact_person IS NULL
            AND full_name IS NOT NULL
        """
    )
    cur.execute(
        """
        UPDATE contacts
        SET job_title = title
        WHERE job_title IS NULL
            AND title IS NOT NULL
        """
    )
    cur.execute(
        """
        UPDATE contacts
        SET company_name = (
            SELECT companies.name
            FROM companies
            WHERE companies.id = contacts.company_id
        )
        WHERE company_name IS NULL
            AND company_id IS NOT NULL
        """
    )
    cur.execute(
        """
        UPDATE contacts
        SET relationship_status = CASE
                WHEN status IN ('Qualified Contact', 'Converted') THEN 'Warm'
                WHEN status IN ('Inactive') THEN 'Inactive'
                ELSE COALESCE(relationship_status, 'New')
            END
        WHERE relationship_status IS NULL
            OR relationship_status = ''
        """
    )
    cur.execute(
        """
        UPDATE leads
        SET lead_status = CASE
                WHEN status = 'Converted' THEN 'Converted'
                WHEN status = 'Qualified' THEN 'Qualified'
                ELSE COALESCE(lead_status, 'New')
            END
        WHERE lead_status IS NULL
            OR lead_status = ''
        """
    )
    cur.execute(
        """
        UPDATE contacts
        SET last_contacted_at = last_touch_at
        WHERE last_contacted_at IS NULL
            AND last_touch_at IS NOT NULL
        """
    )
    cur.execute(
        """
        UPDATE opportunities
        SET opportunity_name = title
        WHERE (opportunity_name IS NULL OR opportunity_name = '')
            AND title IS NOT NULL
        """
    )
    cur.execute(
        """
        UPDATE opportunities
        SET stage = CASE
                WHEN LOWER(COALESCE(status, '')) IN ('quote_requested', 'quote requested') THEN 'Quote Requested'
                WHEN LOWER(COALESCE(status, '')) IN ('quote_sent', 'quoted', 'pricing') THEN 'Quoted'
                WHEN LOWER(COALESCE(status, '')) = 'negotiation' THEN 'Negotiation'
                WHEN LOWER(COALESCE(status, '')) = 'won' THEN 'Won'
                WHEN LOWER(COALESCE(status, '')) = 'lost' THEN 'Lost'
                ELSE COALESCE(NULLIF(stage, ''), 'Interested')
            END
        WHERE stage IS NULL
            OR stage = ''
            OR stage = 'new'
        """
    )

    migrate_crm_records(cur)
    seed_holiday_library(cur)
    seed_knowledge_base(cur)
    seed_quotation_templates(cur)
    cur.execute(
        """
        INSERT OR IGNORE INTO app_settings (setting_key, setting_value, updated_at)
        VALUES ('daily_outreach_capacity', '10', CURRENT_TIMESTAMP)
        """
    )

    user_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        cur.execute(
            """
            INSERT INTO users (username, full_name, role, is_active)
            VALUES (?, ?, ?, ?)
            """,
            ("admin", "Kien Ho", "admin", 1),
        )

    admin_user = cur.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        ("admin",),
    ).fetchone()
    admin_user_id = admin_user["id"] if admin_user else None

    if admin_user_id:
        cur.execute(
            """
            UPDATE quotations
            SET owner = ?
            WHERE owner IS NULL
            """,
            (admin_user_id,),
        )

    conn.commit()
    conn.close()


def normalize(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def normalize_domain(value):
    clean = normalize(value)
    clean = clean.replace("https://", "").replace("http://", "")
    clean = clean.replace("www.", "")
    return clean.split("/")[0].strip()


def clean_value(value):
    if value is None:
        return ""
    return str(value).strip()


OPPORTUNITY_STAGES = ["Interested", "Quote Requested", "Quoted", "Negotiation", "Won", "Lost"]


def normalize_opportunity_stage(value):
    clean = clean_value(value)
    if clean in OPPORTUNITY_STAGES:
        return clean
    status_map = {
        "new": "Interested",
        "open": "Interested",
        "active": "Interested",
        "quote_requested": "Quote Requested",
        "quote requested": "Quote Requested",
        "quote_sent": "Quoted",
        "quoted": "Quoted",
        "pricing": "Quoted",
        "negotiation": "Negotiation",
        "won": "Won",
        "lost": "Lost",
    }
    return status_map.get(normalize(clean), "Interested")


def opportunity_status_from_stage(stage):
    stage = normalize_opportunity_stage(stage)
    return {
        "Interested": "new",
        "Quote Requested": "quote_requested",
        "Quoted": "quoted",
        "Negotiation": "negotiation",
        "Won": "won",
        "Lost": "lost",
    }[stage]


def parse_money(value):
    if value in [None, ""]:
        return 0.0
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return 0.0


def calculate_suggested_sell_rate(cost_amount, margin_percent=0, margin_amount=0):
    cost = parse_money(cost_amount)
    percent_margin = cost * parse_money(margin_percent) / 100
    fixed_margin = parse_money(margin_amount)
    total_margin = percent_margin + fixed_margin
    return {
        "cost_amount": round(cost, 2),
        "margin_amount": round(total_margin, 2),
        "suggested_sell_amount": round(cost + total_margin, 2),
    }


def row_value(row, key, default=""):
    if not row or key not in row.keys():
        return default
    value = row[key]
    if value is None:
        return default
    return value


def today_iso():
    return date.today().isoformat()


def days_from_today(days):
    return (date.today() + timedelta(days=days)).isoformat()


def next_action_for_state(lead_status=None, relationship_status=None):
    relationship_status = clean_value(relationship_status)
    lead_status = clean_value(lead_status) or "New"

    if relationship_status == "Active":
        return "Relationship Maintenance"
    if relationship_status == "Warm":
        return "Relationship Nurturing"
    if lead_status == "Contacted":
        return "Follow-up"
    if lead_status in ["Replied", "Qualified"]:
        return "Relationship Nurturing"
    return "Send Introduction"


def parse_iso_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def calculate_priority_score(row):
    country = normalize(row_value(row, "country", ""))
    membership = normalize(row_value(row, "membership", ""))
    relationship_status = clean_value(row_value(row, "relationship_status", "New"))
    lead_status = clean_value(row_value(row, "lead_status", "New"))
    customer_status = clean_value(row_value(row, "customer_status", "Prospect"))
    last_contacted = row_value(row, "last_contacted_at", "")

    score = 0

    if country == "china":
        score += 25
    elif country == "vietnam":
        score += 20
    elif country in ["usa", "united states", "united states of america"]:
        score += 15
    else:
        score += 10

    for network in ["olo", "wca", "jctrans"]:
        if network in membership:
            score += 15

    score += {
        "New": 5,
        "Connected": 10,
        "Introduced": 15,
        "Warm": 25,
        "Active": 30,
    }.get(relationship_status, 0)

    score += {
        "New": 5,
        "Contacted": 10,
        "Replied": 20,
        "Qualified": 30,
    }.get(lead_status, 0)

    last_contact_date = parse_iso_date(last_contacted)
    if not last_contact_date:
        score += 20
    else:
        days_since_contact = (date.today() - last_contact_date).days
        if days_since_contact > 90:
            score += 15
        elif days_since_contact > 30:
            score += 10

    if customer_status == "Customer":
        score += 20
    elif customer_status == "Qualified":
        score += 10

    return min(score, 100)


def calculate_contact_completeness(row):
    fields = ["email", "phone", "wechat", "whatsapp", "job_title"]
    present = sum(1 for field in fields if clean_value(row_value(row, field, "")))
    return round((present / len(fields)) * 100) if fields else 0


def calculate_organization_completeness(row):
    fields = ["website", "membership", "country", "city", "type"]
    present = sum(1 for field in fields if clean_value(row_value(row, field, "")))
    return round((present / len(fields)) * 100) if fields else 0


def calculate_crm_completeness(contact_row=None, organization_row=None):
    contact_score = calculate_contact_completeness(contact_row or {})
    organization_score = calculate_organization_completeness(organization_row or {})
    return {
        "contact_score": contact_score,
        "organization_score": organization_score,
        "overall_score": round((contact_score + organization_score) / 2),
    }


def get_missing_data_checklist(contact_row=None, organization_row=None):
    contact_row = contact_row or {}
    organization_row = organization_row or {}
    contact_fields = [
        ("email", "Email"),
        ("phone", "Phone"),
        ("wechat", "WeChat"),
        ("whatsapp", "WhatsApp"),
        ("job_title", "Job Title"),
    ]
    organization_fields = [
        ("website", "Website"),
        ("membership", "Membership"),
        ("country", "Country"),
        ("city", "City"),
        ("type", "Organization Type"),
    ]

    return {
        "contact": [
            {"field": field, "label": label}
            for field, label in contact_fields
            if not clean_value(row_value(contact_row, field, ""))
        ],
        "organization": [
            {"field": field, "label": label}
            for field, label in organization_fields
            if not clean_value(row_value(organization_row, field, ""))
        ],
    }


def calculate_relationship_health(lead_row=None, contact_row=None, organization_row=None):
    lead_row = lead_row or {}
    contact_row = contact_row or {}
    organization_row = organization_row or {}
    data_quality = calculate_crm_completeness(contact_row, organization_row)

    relationship_status = clean_value(row_value(contact_row, "relationship_status", "New"))
    customer_status = clean_value(row_value(organization_row, "customer_status", "Prospect"))
    last_contacted = row_value(contact_row, "last_contacted_at", "") or row_value(lead_row, "last_contacted_at", "")
    next_follow_up = row_value(contact_row, "next_follow_up_at", "") or row_value(lead_row, "next_action_date", "")

    score = 0
    components = []

    if customer_status == "Customer":
        score += 30
        components.append({"label": "Customer organization", "points": 30})
    elif customer_status == "Qualified":
        score += 20
        components.append({"label": "Qualified organization", "points": 20})
    elif customer_status == "Prospect":
        score += 10
        components.append({"label": "Prospect organization", "points": 10})

    relationship_points = {
        "Active": 30,
        "Warm": 25,
        "Introduced": 15,
        "Connected": 10,
        "New": 5,
    }.get(relationship_status, 0)
    if relationship_points:
        score += relationship_points
        components.append({"label": f"{relationship_status} relationship", "points": relationship_points})

    last_contact_date = parse_iso_date(last_contacted)
    if not last_contact_date:
        components.append({"label": "No last contact date", "points": 0})
    else:
        days_since_contact = (date.today() - last_contact_date).days
        if days_since_contact <= 30:
            score += 20
            components.append({"label": "Contacted within 30 days", "points": 20})
        elif days_since_contact <= 60:
            score += 10
            components.append({"label": "Contacted within 60 days", "points": 10})
        else:
            components.append({"label": "No contact for more than 60 days", "points": 0})

    next_follow_up_date = parse_iso_date(next_follow_up)
    if not next_follow_up_date:
        components.append({"label": "No next follow-up date", "points": 0})
    elif next_follow_up_date < date.today():
        components.append({"label": "Follow-up is overdue", "points": 0})
    else:
        score += 10
        components.append({"label": "Next follow-up scheduled", "points": 10})

    data_quality_points = round(data_quality["overall_score"] * 0.1)
    score += data_quality_points
    components.append({"label": f"Data quality {data_quality['overall_score']}%", "points": data_quality_points})

    score = min(score, 100)
    if score >= 75:
        label = "Healthy"
    elif score >= 50:
        label = "Needs Attention"
    else:
        label = "At Risk"

    return {
        "score": score,
        "label": label,
        "components": components,
        "last_contacted_at": last_contacted,
        "next_follow_up_at": next_follow_up,
    }


def calculate_action_score(row):
    return sum(item["points"] for item in get_action_score_breakdown(row))


def get_action_score_breakdown(row):
    customer_status = clean_value(row_value(row, "customer_status", ""))
    relationship_status = clean_value(row_value(row, "relationship_status", "New"))
    country = normalize(row_value(row, "country", ""))
    membership = normalize(row_value(row, "membership", ""))
    last_contacted = row_value(row, "last_contacted_at", "")

    breakdown = []

    if customer_status == "Customer":
        breakdown.append({"label": "Customer organization", "points": 100})
    else:
        relationship_points = {
            "Active": 80,
            "Warm": 60,
            "Introduced": 40,
            "Connected": 20,
            "New": 0,
        }.get(relationship_status, 0)
        if relationship_points:
            breakdown.append(
                {
                    "label": f"{relationship_status} relationship",
                    "points": relationship_points,
                }
            )

    last_contact_date = parse_iso_date(last_contacted)
    if last_contact_date:
        days_since_contact = (date.today() - last_contact_date).days
        if days_since_contact > 90:
            breakdown.append({"label": "No contact for more than 90 days", "points": 40})
        elif days_since_contact > 60:
            breakdown.append({"label": "No contact for more than 60 days", "points": 30})
        elif days_since_contact > 30:
            breakdown.append({"label": "No contact for more than 30 days", "points": 20})
        elif days_since_contact > 14:
            breakdown.append({"label": "No contact for more than 14 days", "points": 10})

    if country == "china":
        breakdown.append({"label": "China strategic focus", "points": 20})

    for network in ["olo", "wca", "jctrans"]:
        if network in membership:
            breakdown.append({"label": f"{network.upper()} membership", "points": 15})

    return breakdown


def recommended_action_for_row(row):
    customer_status = clean_value(row_value(row, "customer_status", ""))
    relationship_status = clean_value(row_value(row, "relationship_status", ""))
    lead_status = clean_value(row_value(row, "lead_status", "New"))

    if customer_status == "Customer":
        return "Check current business opportunities"
    if relationship_status == "Active":
        return "Maintain relationship"
    if relationship_status == "Warm":
        return "Ask about current Vietnam shipments"
    if relationship_status in ["Connected", "Introduced"]:
        return "Start conversation"
    if lead_status == "New":
        return "Send introduction"
    if lead_status == "Contacted":
        return "Follow up"
    if lead_status in ["Replied", "Qualified"]:
        return "Ask about current Vietnam shipments"
    return next_action_for_state(lead_status, relationship_status)


def refresh_lead_priority_scores():
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT
            leads.id,
            COALESCE(organizations.country, leads.country, '') AS country,
            COALESCE(organizations.membership, leads.membership, '') AS membership,
            COALESCE(contacts.relationship_status, 'New') AS relationship_status,
            COALESCE(leads.lead_status, 'New') AS lead_status,
            COALESCE(contacts.last_contacted_at, leads.last_contacted_at, '') AS last_contacted_at,
            COALESCE(organizations.customer_status, '') AS customer_status,
            COALESCE(leads.priority_score, 0) AS priority_score,
            COALESCE(leads.action_score, 0) AS action_score,
            EXISTS (
                SELECT 1 FROM opportunities
                WHERE opportunities.contact_id = leads.contact_id
                    AND LOWER(COALESCE(opportunities.status, '')) IN ('new', 'open', 'active')
            ) AS has_open_opportunity,
            EXISTS (
                SELECT 1 FROM opportunities
                WHERE opportunities.contact_id = leads.contact_id
                    AND LOWER(COALESCE(opportunities.status, '')) IN ('quote_requested', 'quote requested')
            ) AS has_quote_requested,
            EXISTS (
                SELECT 1 FROM quotations
                LEFT JOIN opportunities ON opportunities.id = quotations.opportunity_id
                WHERE opportunities.contact_id = leads.contact_id
                    AND LOWER(COALESCE(quotations.status, '')) IN ('draft', 'pricing', 'sent')
            ) AS has_pricing
        FROM leads
        LEFT JOIN organizations ON organizations.id = leads.organization_id
        LEFT JOIN contacts ON contacts.id = leads.contact_id
        """
    ).fetchall()

    updated = 0
    for row in rows:
        priority_score = calculate_priority_score(row)
        action_score = calculate_action_score(row)
        if int(row["priority_score"] or 0) == priority_score and int(row["action_score"] or 0) == action_score:
            continue
        cur.execute(
            """
            UPDATE leads
            SET priority_score = ?,
                action_score = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (priority_score, action_score, row["id"]),
        )
        updated += 1

    conn.commit()
    conn.close()
    return updated


def get_daily_outreach_capacity():
    raw_capacity = get_app_setting("daily_outreach_capacity", "10")
    try:
        capacity = int(raw_capacity)
    except (TypeError, ValueError):
        capacity = 10
    return capacity if capacity in [10, 20, 30, 50] else 10


def find_organization(cur, name, country):
    clean_name = clean_value(name)
    clean_domain = normalize_domain("")

    if clean_name:
        organization = cur.execute(
            """
        SELECT id
        FROM organizations
        WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
            AND LOWER(TRIM(COALESCE(country, ''))) = LOWER(TRIM(COALESCE(?, '')))
        LIMIT 1
        """,
            (clean_name, clean_value(country)),
        ).fetchone()
        if organization:
            return organization

    return None


def find_organization_for_record(cur, record):
    organization = find_organization(
        cur,
        record.get("company_name") or record.get("organization_name"),
        record.get("country"),
    )
    if organization:
        return organization

    domain = normalize_domain(record.get("website"))
    if not domain:
        return None

    rows = cur.execute(
        """
        SELECT id, website
        FROM organizations
        WHERE COALESCE(website, '') <> ''
        """
    ).fetchall()
    for row in rows:
        if normalize_domain(row["website"]) == domain:
            return row
    return None


def upsert_organization(cur, lead):
    organization = find_organization_for_record(cur, lead)

    if organization:
        organization_id = organization["id"]
        cur.execute(
            """
            UPDATE organizations
            SET type = COALESCE(NULLIF(?, ''), type),
                province = COALESCE(NULLIF(?, ''), province),
                city = COALESCE(NULLIF(?, ''), city),
                website = COALESCE(NULLIF(?, ''), website),
                local_name = COALESCE(NULLIF(?, ''), local_name),
                membership = COALESCE(NULLIF(?, ''), membership),
                source = COALESCE(NULLIF(?, ''), source),
                customer_status = CASE
                    WHEN NULLIF(?, '') IS NOT NULL THEN ?
                    ELSE customer_status
                END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                lead.get("organization_type"),
                lead.get("province"),
                lead.get("city"),
                lead.get("website"),
                lead.get("local_name"),
                lead.get("membership"),
                lead.get("source"),
                lead.get("customer_status"),
                lead.get("customer_status"),
                organization_id,
            ),
        )
        return organization_id

    cur.execute(
        """
        INSERT INTO organizations (
            name,
            type,
            country,
            province,
            city,
            website,
            local_name,
            customer_status,
            source,
            membership,
            notes,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            lead.get("company_name") or lead.get("organization_name"),
            lead.get("organization_type") or "Other",
            lead.get("country"),
            lead.get("province"),
            lead.get("city"),
            lead.get("website"),
            lead.get("local_name"),
            lead.get("customer_status") or "Prospect",
            lead.get("source"),
            lead.get("membership"),
            lead.get("organization_notes"),
        ),
    )
    return cur.lastrowid


def insert_organization(cur, lead):
    cur.execute(
        """
        INSERT INTO organizations (
            name,
            type,
            country,
            province,
            city,
            website,
            local_name,
            customer_status,
            source,
            membership,
            notes,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            lead.get("company_name") or lead.get("organization_name") or "Unknown Organization",
            lead.get("organization_type") or "Other",
            lead.get("country"),
            lead.get("province"),
            lead.get("city"),
            lead.get("website"),
            lead.get("local_name"),
            lead.get("customer_status") or "Prospect",
            lead.get("source"),
            lead.get("membership"),
            lead.get("organization_notes"),
        ),
    )
    return cur.lastrowid


def find_contact(cur, organization_id, lead):
    email = clean_value(lead.get("email"))
    wechat = clean_value(lead.get("wechat"))
    whatsapp = clean_value(lead.get("whatsapp"))
    contact_name = clean_value(lead.get("contact_person") or lead.get("name"))

    for field, value in [
        ("email", email),
        ("wechat", wechat),
        ("whatsapp", whatsapp),
    ]:
        if value:
            contact = cur.execute(
                f"""
                SELECT id
                FROM contacts
                WHERE LOWER(TRIM(COALESCE({field}, ''))) = LOWER(TRIM(?))
                LIMIT 1
                """,
                (value,),
            ).fetchone()
            if contact:
                return contact

    if organization_id and contact_name:
        return cur.execute(
            """
            SELECT id
            FROM contacts
            WHERE organization_id = ?
                AND LOWER(TRIM(COALESCE(name, contact_person, full_name, ''))) = LOWER(TRIM(?))
            LIMIT 1
            """,
            (organization_id, contact_name),
        ).fetchone()

    return None


def upsert_contact(cur, organization_id, lead):
    contact = find_contact(cur, organization_id, lead)
    contact_name = clean_value(lead.get("contact_person") or lead.get("name"))
    if not contact_name:
        contact_name = clean_value(lead.get("company_name")) or "Unknown Contact"

    if contact:
        contact_id = contact["id"]
        cur.execute(
            """
            UPDATE contacts
            SET organization_id = COALESCE(organization_id, ?),
                full_name = COALESCE(NULLIF(?, ''), full_name),
                name = COALESCE(NULLIF(?, ''), name),
                contact_person = COALESCE(NULLIF(?, ''), contact_person),
                company_name = COALESCE(NULLIF(?, ''), company_name),
                country = COALESCE(NULLIF(?, ''), country),
                city = COALESCE(NULLIF(?, ''), city),
                title = COALESCE(NULLIF(?, ''), title),
                job_title = COALESCE(NULLIF(?, ''), job_title),
                phone = COALESCE(NULLIF(?, ''), phone),
                email = COALESCE(NULLIF(?, ''), email),
                wechat = COALESCE(NULLIF(?, ''), wechat),
                whatsapp = COALESCE(NULLIF(?, ''), whatsapp),
                membership = COALESCE(NULLIF(?, ''), membership),
                source = COALESCE(NULLIF(?, ''), source),
                relationship_status = COALESCE(NULLIF(?, ''), relationship_status, 'New'),
                status = COALESCE(NULLIF(?, ''), status),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                organization_id,
                contact_name,
                contact_name,
                contact_name,
                lead.get("company_name"),
                lead.get("country"),
                lead.get("city"),
                lead.get("job_title"),
                lead.get("job_title"),
                lead.get("phone"),
                lead.get("email"),
                lead.get("wechat"),
                lead.get("whatsapp"),
                lead.get("membership"),
                lead.get("source"),
                lead.get("relationship_status"),
                lead.get("status"),
                contact_id,
            ),
        )
        return contact_id

    cur.execute(
        """
        INSERT INTO contacts (
            organization_id,
            full_name,
            name,
            contact_person,
            company_name,
            country,
            city,
            title,
            job_title,
            phone,
            email,
            wechat,
            whatsapp,
            membership,
            source,
            relationship_status,
            status,
            owner,
            notes,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            organization_id,
            contact_name,
            contact_name,
            contact_name,
            lead.get("company_name"),
            lead.get("country"),
            lead.get("city"),
            lead.get("job_title"),
            lead.get("job_title"),
            lead.get("phone"),
            lead.get("email"),
            lead.get("wechat"),
            lead.get("whatsapp"),
            lead.get("membership"),
            lead.get("source"),
            lead.get("relationship_status") or "New",
            lead.get("status") or "New Lead",
            lead.get("owner") or "admin",
            lead.get("notes"),
        ),
    )
    return cur.lastrowid


def insert_contact(cur, organization_id, lead):
    contact_name = clean_value(lead.get("contact_person") or lead.get("name"))
    if not contact_name:
        contact_name = clean_value(lead.get("company_name")) or "Unknown Contact"

    cur.execute(
        """
        INSERT INTO contacts (
            organization_id,
            full_name,
            name,
            contact_person,
            company_name,
            country,
            city,
            title,
            job_title,
            phone,
            email,
            wechat,
            whatsapp,
            membership,
            source,
            relationship_status,
            status,
            owner,
            notes,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            organization_id,
            contact_name,
            contact_name,
            contact_name,
            lead.get("company_name"),
            lead.get("country"),
            lead.get("city"),
            lead.get("job_title"),
            lead.get("job_title"),
            lead.get("phone"),
            lead.get("email"),
            lead.get("wechat"),
            lead.get("whatsapp"),
            lead.get("membership"),
            lead.get("source"),
            lead.get("relationship_status") or "New",
            lead.get("status") or "New Lead",
            lead.get("owner") or "admin",
            lead.get("notes"),
        ),
    )
    return cur.lastrowid


def lead_exists(cur, organization_id, contact_id, campaign, source=None):
    if source is None:
        return cur.execute(
            """
            SELECT id
            FROM leads
            WHERE organization_id = ?
                AND contact_id = ?
                AND LOWER(TRIM(COALESCE(campaign, ''))) = LOWER(TRIM(COALESCE(?, '')))
            LIMIT 1
            """,
            (organization_id, contact_id, clean_value(campaign)),
        ).fetchone()

    return cur.execute(
        """
        SELECT id
        FROM leads
        WHERE organization_id = ?
            AND contact_id = ?
            AND LOWER(TRIM(COALESCE(source, ''))) = LOWER(TRIM(COALESCE(?, '')))
            AND LOWER(TRIM(COALESCE(campaign, ''))) = LOWER(TRIM(COALESCE(?, '')))
        LIMIT 1
        """,
        (organization_id, contact_id, clean_value(source), clean_value(campaign)),
    ).fetchone()


def insert_lead(cur, organization_id, contact_id, record):
    next_action = record.get("next_action") or "Send first introduction"
    next_action_date = record.get("next_action_date") or days_from_today(1)

    cur.execute(
        """
        INSERT INTO leads (
            organization_id,
            contact_id,
            company_name,
            contact_person,
            country,
            city,
            job_title,
            phone,
            email,
            wechat,
            whatsapp,
            membership,
            source,
            campaign,
            lead_status,
            interest_level,
            next_action,
            next_action_date,
            status,
            owner,
            notes,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            organization_id,
            contact_id,
            record.get("company_name"),
            record.get("contact_person"),
            record.get("country"),
            record.get("city"),
            record.get("job_title"),
            record.get("phone"),
            record.get("email"),
            record.get("wechat"),
            record.get("whatsapp"),
            record.get("membership"),
            record.get("source") or "Quick Capture",
            record.get("campaign"),
            record.get("lead_status") or "New",
            record.get("interest_level"),
            next_action,
            next_action_date,
            record.get("status") or record.get("lead_status") or "New",
            record.get("owner") or "admin",
            record.get("notes"),
        ),
    )
    return cur.lastrowid


def log_crm_activity(
    cur,
    activity_type,
    description,
    lead_id=None,
    organization_id=None,
    contact_id=None,
    opportunity_id=None,
    quotation_id=None,
    user="admin",
):
    cur.execute(
        """
        INSERT INTO activities (
            lead_id,
            organization_id,
            contact_id,
            opportunity_id,
            quotation_id,
            activity_type,
            description,
            summary,
            user,
            activity_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            lead_id,
            organization_id,
            contact_id,
            opportunity_id,
            quotation_id,
            activity_type,
            description,
            description,
            user,
        ),
    )
    return cur.lastrowid


def seed_holiday_library(cur):
    holidays = [
        ("China", "Chinese New Year", "2026-02-17", 1, "manual_yearly", "health, prosperity, and continued cooperation"),
        ("China", "Mid-Autumn Festival", "2026-09-25", 1, "manual_yearly", "reunion, harmony, and success"),
        ("China", "National Day", "2026-10-01", 1, "yearly_mm_dd", "prosperity and success"),
        ("United States", "New Year's Day", "2026-01-01", 1, "yearly_mm_dd", "health, happiness, and success"),
        ("United States", "Thanksgiving", "2026-11-26", 1, "manual_yearly", "gratitude and partnership"),
        ("United States", "Christmas", "2026-12-25", 1, "yearly_mm_dd", "peace, joy, and success"),
        ("United States", "Independence Day", "2026-07-04", 1, "yearly_mm_dd", "celebration and continued success"),
        ("Vietnam", "Lunar New Year", "2026-02-17", 1, "manual_yearly", "health, luck, and prosperity"),
        ("Vietnam", "Mid-Autumn Festival", "2026-09-25", 1, "manual_yearly", "reunion, happiness, and success"),
        ("Vietnam", "National Day", "2026-09-02", 1, "yearly_mm_dd", "prosperity and success"),
        ("Vietnam", "Reunification Day", "2026-04-30", 1, "yearly_mm_dd", "peace and continued growth"),
    ]

    for holiday in holidays:
        exists = cur.execute(
            """
            SELECT id
            FROM holiday_library
            WHERE country = ?
                AND holiday_name = ?
            LIMIT 1
            """,
            (holiday[0], holiday[1]),
        ).fetchone()
        if exists:
            continue
        cur.execute(
            """
            INSERT INTO holiday_library (
                country,
                holiday_name,
                holiday_date,
                is_recurring,
                recurrence_rule,
                default_message_theme,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            holiday,
        )


def seed_knowledge_base(cur):
    tags = [
        "customs",
        "food",
        "animal quarantine",
        "civil cryptography",
        "medical device",
        "battery",
        "DG",
        "CO",
        "customs valuation",
        "DDP",
        "IOR",
        "EOR",
        "FDA",
    ]
    for tag in tags:
        cur.execute("INSERT OR IGNORE INTO knowledge_tags (name) VALUES (?)", (tag,))

    if not cur.execute("SELECT 1 FROM knowledge_documents WHERE title = ?", ("Vietnam Civil Cryptography Import Control - Internal Placeholder",)).fetchone():
        cur.execute(
            """
            INSERT INTO knowledge_documents (
                title,
                document_no,
                document_type,
                issuing_authority,
                status,
                category,
                summary,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                "Vietnam Civil Cryptography Import Control - Internal Placeholder",
                "INTERNAL-KB-CRYPTO-001",
                "Internal SOP Reference",
                "1Aim Logistics",
                "Draft",
                "Import Compliance",
                "Placeholder reference for storing official rules and internal interpretation about civil cryptography import control.",
            ),
        )
        document_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO knowledge_chunks (
                document_id,
                heading,
                content,
                keywords,
                created_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                document_id,
                "Evidence-first compliance answers",
                "For cryptography permit questions, answer only from stored legal documents, SOPs, and approved cases. If evidence is missing, state insufficient information.",
                "civil cryptography, permit, import compliance, Vietnam",
            ),
        )

    if not cur.execute("SELECT 1 FROM knowledge_sops WHERE title = ?", ("Import Cisco Router - Compliance Check",)).fetchone():
        cur.execute(
            """
            INSERT INTO knowledge_sops (
                title,
                purpose,
                procedure_steps,
                checklist,
                related_documents,
                category,
                status,
                created_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'Active', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                "Import Cisco Router - Compliance Check",
                "Guide ops team through initial compliance review before quoting/importing Cisco networking equipment.",
                "1. Confirm model and HS code.\n2. Check whether device includes encryption/security features.\n3. Search Legal Library and Case Library.\n4. Escalate if no supporting evidence exists.",
                "Model confirmed\nHS code checked\nLegal basis attached\nCustomer risk note prepared",
                "INTERNAL-KB-CRYPTO-001",
                "Import Compliance",
            ),
        )

    if not cur.execute("SELECT 1 FROM knowledge_cases WHERE title = ?", ("Cisco switch imported into Vietnam - cryptography permit review",)).fetchone():
        cur.execute(
            """
            INSERT INTO knowledge_cases (
                title,
                customer,
                commodity,
                hs_code,
                country,
                problem,
                solution,
                legal_basis,
                risk_notes,
                created_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                "Cisco switch imported into Vietnam - cryptography permit review",
                "Sample Customer",
                "Cisco switch",
                "",
                "Vietnam",
                "Customer asked whether a Cisco switch required civil cryptography permit before import.",
                "Sample conclusion: do not rely on this case alone. Attach official legal basis before advising customer.",
                "Internal placeholder only. Add official document references before using operationally.",
                "This sample case exists to demonstrate structure. Confidence should remain low until legal basis is added.",
            ),
        )

    intelligence_samples = [
        (
            "Lessons Learned",
            "Quote only after compliance evidence is attached",
            "Internal",
            "Vietnam",
            "",
            "Networking equipment",
            "",
            "Do not send a confident compliance conclusion from memory.",
            "When a shipment involves regulated equipment such as routers, firewalls, food, batteries, medical devices, or cryptography risk, attach legal basis or approved case evidence before quotation.",
            "Internal operating lesson",
            "High",
            "lessons learned, compliance, quotation",
        ),
        (
            "Market Intelligence",
            "China forwarders value Vietnam local execution speed",
            "China network",
            "China",
            "China - Vietnam",
            "General cargo",
            "",
            "China agent outreach should emphasize Vietnam operations response time and customs handling.",
            "For Chinese forwarders, useful positioning includes fast Vietnam customs check, destination handling, DDP feasibility review, and clear exception feedback.",
            "CRM strategy",
            "Medium",
            "market intelligence, China, Vietnam, agents",
        ),
        (
            "Vendor Intelligence",
            "Vendor evaluation should capture lane, strength, and risk",
            "Vendor Network",
            "Vietnam",
            "Vietnam domestic",
            "General cargo",
            "",
            "Vendor notes should separate strengths from risks.",
            "Track response speed, quote accuracy, document discipline, billing behavior, and whether vendor is suitable for urgent jobs or only routine shipments.",
            "Internal vendor standard",
            "Medium",
            "vendor intelligence, operations, risk",
        ),
        (
            "Customer Intelligence",
            "Customer-specific know-how belongs in Knowledge Base",
            "Customer Network",
            "",
            "",
            "",
            "",
            "Store customer preferences, document habits, commodity patterns, and hidden risks.",
            "Customer intelligence should help sales and operations remember what matters for each customer: decision maker, preferred channel, quote style, compliance sensitivity, payment behavior, and historical pain points.",
            "Internal CRM standard",
            "Medium",
            "customer intelligence, relationship, retention",
        ),
        (
            "Shipment History Intelligence",
            "Shipment history should become reusable operations memory",
            "Operations",
            "Vietnam",
            "",
            "",
            "",
            "Past shipment outcomes should help future quotation and risk review.",
            "Capture what happened, what delayed the shipment, which documents were missing, vendor performance, customs notes, final cost variance, and what should be repeated or avoided next time.",
            "Internal operations standard",
            "Medium",
            "shipment history, lessons learned, operations",
        ),
    ]
    for sample in intelligence_samples:
        if cur.execute(
            "SELECT 1 FROM knowledge_intelligence WHERE intelligence_type = ? AND title = ?",
            (sample[0], sample[1]),
        ).fetchone():
            continue
        cur.execute(
            """
            INSERT INTO knowledge_intelligence (
                intelligence_type,
                title,
                entity_name,
                country,
                lane,
                commodity,
                hs_code,
                summary,
                details,
                source,
                confidence,
                tags,
                status,
                created_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            sample,
        )


def seed_quotation_templates(cur):
    cur.execute(
        """
        INSERT OR IGNORE INTO quotation_templates (
            template_name,
            header_text,
            footer_text,
            payment_terms,
            validity_days,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            "Standard Freight Quote",
            "Thank you for your inquiry. Please find our quotation below.",
            "Rates are subject to space, equipment, and final cargo details at booking.",
            "Payment before cargo release unless otherwise agreed.",
            14,
        ),
    )


def migrate_crm_records(cur):
    company_rows = cur.execute("SELECT * FROM companies").fetchall()
    for company in company_rows:
        lead = {
            "company_name": row_value(company, "name"),
            "country": row_value(company, "country"),
            "organization_type": row_value(company, "type") or "Other",
            "organization_notes": row_value(company, "notes"),
        }
        upsert_organization(cur, lead)

    contact_rows = cur.execute("SELECT * FROM contacts").fetchall()
    for contact in contact_rows:
        company_name = row_value(contact, "company_name")
        country = row_value(contact, "country")

        if not company_name and row_value(contact, "company_id"):
            company = cur.execute(
                "SELECT * FROM companies WHERE id = ?",
                (row_value(contact, "company_id"),),
            ).fetchone()
            company_name = row_value(company, "name")
            country = country or row_value(company, "country")

        if company_name and not row_value(contact, "organization_id"):
            organization_id = upsert_organization(
                cur,
                {
                    "company_name": company_name,
                    "country": country,
                    "city": row_value(contact, "city"),
                    "membership": row_value(contact, "membership"),
                    "source": row_value(contact, "source"),
                },
            )
            cur.execute(
                """
                UPDATE contacts
                SET organization_id = ?,
                    name = COALESCE(NULLIF(name, ''), NULLIF(contact_person, ''), full_name),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (organization_id, row_value(contact, "id")),
            )

    lead_rows = cur.execute("SELECT * FROM leads").fetchall()
    for lead_row in lead_rows:
        if row_value(lead_row, "organization_id") and row_value(lead_row, "contact_id"):
            continue

        lead = {
            "company_name": row_value(lead_row, "company_name"),
            "contact_person": row_value(lead_row, "contact_person"),
            "country": row_value(lead_row, "country"),
            "city": row_value(lead_row, "city"),
            "job_title": row_value(lead_row, "job_title"),
            "phone": row_value(lead_row, "phone"),
            "email": row_value(lead_row, "email"),
            "wechat": row_value(lead_row, "wechat"),
            "whatsapp": row_value(lead_row, "whatsapp"),
            "membership": row_value(lead_row, "membership"),
            "source": row_value(lead_row, "source") or "Excel Import",
            "campaign": row_value(lead_row, "campaign") or row_value(lead_row, "source"),
            "notes": row_value(lead_row, "notes"),
        }

        if not lead["company_name"]:
            continue

        organization_id = upsert_organization(cur, lead)
        contact_id = upsert_contact(cur, organization_id, lead)
        lead_status = row_value(lead_row, "lead_status")
        if not lead_status:
            lead_status = "Converted" if row_value(lead_row, "status") == "Converted" else "New"

        cur.execute(
            """
            UPDATE leads
            SET organization_id = ?,
                contact_id = ?,
                source = COALESCE(NULLIF(source, ''), 'Excel Import'),
                campaign = COALESCE(NULLIF(campaign, ''), NULLIF(?, '')),
                lead_status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                organization_id,
                contact_id,
                lead["campaign"],
                lead_status,
                row_value(lead_row, "id"),
            ),
        )


def create_inquiry(inquiry_text):
    today = date.today().isoformat()
    clean_text = inquiry_text.strip()

    conn = get_connection()
    cur = conn.cursor()
    admin_user = cur.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        ("admin",),
    ).fetchone()
    admin_user_id = admin_user["id"] if admin_user else None

    cur.execute(
        """
        INSERT INTO opportunities (title, owner, inquiry_text, status, inquiry_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (clean_text[:80], admin_user_id, clean_text, "new", today),
    )

    opportunity_id = cur.lastrowid

    cur.execute(
        """
        INSERT INTO tasks (
            opportunity_id,
            task_type,
            title,
            due_date,
            status,
            priority,
            assigned_to,
            created_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            opportunity_id,
            "prepare_quote",
            "Prepare quote: " + clean_text[:60],
            today,
            "open",
            "high",
            admin_user_id,
            admin_user_id,
        ),
    )

    cur.execute(
        """
        INSERT INTO activities (opportunity_id, activity_type, summary)
        VALUES (?, ?, ?)
        """,
        (
            opportunity_id,
            "inquiry_received",
            "New inquiry received",
        ),
    )

    conn.commit()
    conn.close()


def create_opportunity(data, user="admin"):
    today = date.today().isoformat()
    clean_record = {key: clean_value(value) for key, value in (data or {}).items()}

    conn = get_connection()
    cur = conn.cursor()
    admin_user = cur.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        ("admin",),
    ).fetchone()
    admin_user_id = admin_user["id"] if admin_user else None

    organization_id = clean_record.get("organization_id") or None
    contact_id = clean_record.get("contact_id") or None

    if clean_record.get("lead_id") and (not organization_id or not contact_id):
        lead = cur.execute(
            """
            SELECT organization_id, contact_id
            FROM leads
            WHERE id = ?
            """,
            (clean_record.get("lead_id"),),
        ).fetchone()
        if lead:
            organization_id = organization_id or lead["organization_id"]
            contact_id = contact_id or lead["contact_id"]

    company_name = clean_record.get("company_name") or clean_record.get("organization")
    if company_name and (not organization_id or not contact_id):
        crm_record = {
            "company_name": company_name,
            "contact_person": clean_record.get("contact_person"),
            "country": clean_record.get("country"),
            "city": clean_record.get("city"),
            "phone": clean_record.get("phone"),
            "email": clean_record.get("email"),
            "source": "Inquiry Intake",
            "campaign": "Inbound Inquiry",
            "relationship_status": "Connected",
            "status": "Inquiry",
            "notes": clean_record.get("raw_text"),
        }
        organization_id = organization_id or upsert_organization(cur, crm_record)
        contact_id = contact_id or upsert_contact(cur, organization_id, crm_record)

    opportunity_name = clean_record.get("opportunity_name") or clean_record.get("subject") or "Inbound Inquiry"
    stage = normalize_opportunity_stage(clean_record.get("stage") or "Interested")
    status = opportunity_status_from_stage(stage)
    inquiry_date = clean_record.get("inquiry_date") or today
    notes = clean_record.get("notes")

    cur.execute(
        """
        INSERT INTO opportunities (
            opportunity_name,
            title,
            organization_id,
            contact_id,
            owner,
            stage,
            status,
            trade_lane,
            service_type,
            route,
            commodity,
            volume,
            cargo_description,
            origin,
            destination,
            weight,
            container_type,
            quantity,
            incoterm,
            quotation_status,
            mode,
            potential_revenue,
            potential_profit,
            expected_close_date,
            next_action,
            next_action_date,
            notes,
            inquiry_text,
            inquiry_date,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            opportunity_name,
            opportunity_name,
            organization_id,
            contact_id,
            admin_user_id,
            stage,
            status,
            clean_record.get("trade_lane"),
            clean_record.get("service_type"),
            clean_record.get("trade_lane") or build_route(clean_record.get("origin"), clean_record.get("destination")),
            clean_record.get("commodity") or clean_record.get("cargo_description"),
            clean_record.get("volume"),
            clean_record.get("cargo_description") or clean_record.get("commodity"),
            clean_record.get("origin"),
            clean_record.get("destination"),
            clean_record.get("weight"),
            clean_record.get("container_type"),
            clean_record.get("quantity"),
            clean_record.get("incoterm"),
            clean_record.get("quotation_status") or "Not Started",
            clean_record.get("mode"),
            parse_money(clean_record.get("potential_revenue")),
            parse_money(clean_record.get("potential_profit")),
            clean_record.get("expected_close_date") or clean_record.get("deadline"),
            clean_record.get("next_action") or "Prepare quotation",
            clean_record.get("next_action_date") or today,
            notes,
            clean_record.get("raw_text"),
            inquiry_date,
        ),
    )
    opportunity_id = cur.lastrowid

    task_id = None
    if clean_record.get("create_prepare_quote_task") in ["1", "true", "True", "yes", "Yes"]:
        cur.execute(
            """
            INSERT INTO tasks (
                opportunity_id,
                task_type,
                title,
                due_date,
                status,
                priority,
                assigned_to,
                created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opportunity_id,
                "prepare_quote",
                "Prepare quote: " + opportunity_name[:60],
                clean_record.get("next_action_date") or today,
                "open",
                "high",
                admin_user_id,
                admin_user_id,
            ),
        )
        task_id = cur.lastrowid

    activity_lines = [
        f"Opportunity created: {opportunity_name}",
        f"Trade lane: {clean_record.get('trade_lane') or '-'}",
        f"Service: {clean_record.get('service_type') or '-'}",
    ]
    if clean_record.get("attachment_folder"):
        activity_lines.append(f"Folder: {clean_record.get('attachment_folder')}")
    if clean_record.get("attachment_files"):
        activity_lines.append("Files: " + clean_record.get("attachment_files"))

    log_crm_activity(
        cur,
        clean_record.get("activity_type") or "Opportunity Update",
        "\n".join(activity_lines),
        organization_id=organization_id,
        contact_id=contact_id,
        opportunity_id=opportunity_id,
        user=user,
    )

    conn.commit()
    conn.close()
    return {
        "opportunity_id": opportunity_id,
        "task_id": task_id,
        "organization_id": organization_id,
        "contact_id": contact_id,
    }


def build_route(origin, destination):
    origin = clean_value(origin)
    destination = clean_value(destination)
    if origin and destination:
        return f"{origin} -> {destination}"
    return origin or destination


def create_inquiry_opportunity(record, user="admin"):
    inquiry_record = dict(record or {})
    inquiry_record["stage"] = inquiry_record.get("stage") or "Quote Requested"
    inquiry_record["activity_type"] = "Inquiry Received"
    inquiry_record["create_prepare_quote_task"] = "1"
    return create_opportunity(inquiry_record, user=user)


def mark_prepare_quote_sent(task_id, follow_up_date, current_user_id=None):
    today = date.today().isoformat()
    quote_no_prefix = date.today().strftime("%y%m")

    conn = get_connection()
    cur = conn.cursor()
    admin_user = cur.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        ("admin",),
    ).fetchone()
    admin_user_id = admin_user["id"] if admin_user else None
    quotation_owner = current_user_id or admin_user_id

    task = cur.execute(
        """
        SELECT tasks.*, opportunities.title AS opportunity_title
        FROM tasks
        LEFT JOIN opportunities ON opportunities.id = tasks.opportunity_id
        WHERE tasks.id = ?
            AND tasks.task_type = ?
            AND tasks.status = ?
        """,
        (task_id, "prepare_quote", "open"),
    ).fetchone()

    if not task:
        conn.close()
        return False

    opportunity_id = task["opportunity_id"]
    opportunity_title = task["opportunity_title"]

    if not opportunity_title:
        opportunity_title = task["title"].replace("Prepare quote: ", "", 1)

    if not opportunity_id:
        cur.execute(
            """
            INSERT INTO opportunities (title, owner, status, inquiry_date)
            VALUES (?, ?, ?, ?)
            """,
            (opportunity_title, task["assigned_to"], "quote_sent", today),
        )
        opportunity_id = cur.lastrowid

    latest_quote = cur.execute(
        """
        SELECT quote_no
        FROM quotations
        WHERE quote_no LIKE ?
        ORDER BY quote_no DESC
        LIMIT 1
        """,
        (quote_no_prefix + "%",),
    ).fetchone()

    if latest_quote and latest_quote["quote_no"]:
        next_quote_number = int(latest_quote["quote_no"][4:]) + 1
    else:
        next_quote_number = 1

    quote_no = quote_no_prefix + f"{next_quote_number:02d}"

    cur.execute(
        """
        INSERT INTO quotations (
            opportunity_id,
            quote_no,
            quote_date,
            currency,
            status,
            owner,
            follow_up_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            opportunity_id,
            quote_no,
            today,
            "USD",
            "sent",
            quotation_owner,
            follow_up_date,
        ),
    )
    quotation_id = cur.lastrowid

    cur.execute(
        """
        UPDATE tasks
        SET status = ?,
            completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        ("closed", task_id),
    )

    cur.execute(
        """
        INSERT INTO tasks (
            opportunity_id,
            quotation_id,
            task_type,
            title,
            due_date,
            status,
            priority,
            assigned_to,
            created_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            opportunity_id,
            quotation_id,
            "quote_follow_up",
            "Follow up quote: " + opportunity_title,
            follow_up_date,
            "open",
            "high",
            task["assigned_to"],
            task["created_by"],
        ),
    )

    cur.execute(
        """
        INSERT INTO activities (
            opportunity_id,
            quotation_id,
            activity_type,
            summary
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            opportunity_id,
            quotation_id,
            "quote_sent",
            "Quote sent: " + opportunity_title,
        ),
    )

    conn.commit()
    conn.close()
    return True


def get_open_tasks():
    conn = get_connection()

    tasks = conn.execute(
        """
        SELECT *
        FROM tasks
        WHERE status = 'open'
        ORDER BY
            CASE priority
                WHEN 'high' THEN 1
                WHEN 'normal' THEN 2
                ELSE 3
            END,
            due_date,
            created_at DESC
        """
    ).fetchall()

    conn.close()
    return tasks


def get_quote_follow_up_tasks():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            tasks.*,
            quotations.quote_no,
            quotations.quote_date,
            quotations.follow_up_date AS quotation_follow_up_date,
            quotations.currency,
            quotations.sell_amount,
            quotations.status AS quotation_status,
            COALESCE(opportunities.opportunity_name, opportunities.title) AS opportunity_title,
            organizations.name AS organization_name,
            contacts.name AS contact_name
        FROM tasks
        LEFT JOIN quotations ON quotations.id = tasks.quotation_id
        LEFT JOIN opportunities ON opportunities.id = tasks.opportunity_id
        LEFT JOIN organizations ON organizations.id = opportunities.organization_id
        LEFT JOIN contacts ON contacts.id = opportunities.contact_id
        WHERE tasks.status = 'open'
            AND tasks.task_type = 'quote_follow_up'
        ORDER BY
            tasks.due_date,
            CASE tasks.priority
                WHEN 'high' THEN 1
                WHEN 'normal' THEN 2
                ELSE 3
            END,
            tasks.created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def complete_quote_follow_up_task(task_id, channel, next_follow_up_date=None, note="", user="admin"):
    clean_channel = clean_value(channel) or "Email"
    clean_note = clean_value(note)
    clean_next_date = clean_value(next_follow_up_date)

    conn = get_connection()
    cur = conn.cursor()
    task = cur.execute(
        """
        SELECT
            tasks.*,
            quotations.quote_no,
            COALESCE(opportunities.opportunity_name, opportunities.title) AS opportunity_title,
            opportunities.organization_id,
            opportunities.contact_id
        FROM tasks
        LEFT JOIN quotations ON quotations.id = tasks.quotation_id
        LEFT JOIN opportunities ON opportunities.id = tasks.opportunity_id
        WHERE tasks.id = ?
            AND tasks.task_type = 'quote_follow_up'
            AND tasks.status = 'open'
        """,
        (task_id,),
    ).fetchone()

    if not task:
        conn.close()
        return False

    cur.execute(
        """
        UPDATE tasks
        SET status = ?,
            channel = ?,
            completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        ("closed", clean_channel, task_id),
    )

    opportunity_title = row_value(task, "opportunity_title", "") or row_value(task, "title", "")
    activity_lines = [
        f"{clean_channel} follow-up completed",
        f"Quote: {row_value(task, 'quote_no', '-')}",
        f"Opportunity: {opportunity_title or '-'}",
    ]
    if clean_note:
        activity_lines.append(f"Note: {clean_note}")
    if clean_next_date:
        activity_lines.append(f"Next follow-up: {clean_next_date}")

    log_crm_activity(
        cur,
        f"Quote Follow-up - {clean_channel}",
        "\n".join(activity_lines),
        organization_id=row_value(task, "organization_id", None),
        contact_id=row_value(task, "contact_id", None),
        opportunity_id=row_value(task, "opportunity_id", None),
        quotation_id=row_value(task, "quotation_id", None),
        user=user,
    )

    if clean_next_date:
        title = "Follow up quote: " + (opportunity_title or row_value(task, "quote_no", "Quotation"))
        cur.execute(
            """
            INSERT INTO tasks (
                contact_id,
                opportunity_id,
                quotation_id,
                task_type,
                title,
                channel,
                due_date,
                status,
                priority,
                assigned_to,
                created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_value(task, "contact_id", None),
                row_value(task, "opportunity_id", None),
                row_value(task, "quotation_id", None),
                "quote_follow_up",
                title,
                clean_channel,
                clean_next_date,
                "open",
                "high",
                row_value(task, "assigned_to", None),
                row_value(task, "created_by", None),
            ),
        )

        if row_value(task, "quotation_id", None):
            cur.execute(
                """
                UPDATE quotations
                SET follow_up_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (clean_next_date, row_value(task, "quotation_id", None)),
            )

    conn.commit()
    conn.close()
    return True


def get_task_counts_by_type():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT task_type, COUNT(*) AS task_count
        FROM tasks
        WHERE status = 'open'
        GROUP BY task_type
        """
    ).fetchall()

    conn.close()
    return {
        row["task_type"]: row["task_count"]
        for row in rows
    }


def get_user_count():
    conn = get_connection()

    user_count = conn.execute(
        """
        SELECT COUNT(*) AS user_count
        FROM users
        """
    ).fetchone()["user_count"]

    conn.close()
    return user_count


def get_app_setting(setting_key, default_value=None):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT setting_value
        FROM app_settings
        WHERE setting_key = ?
        """,
        (setting_key,),
    ).fetchone()

    conn.close()
    if not row:
        return default_value
    return row["setting_value"]


def set_app_setting(setting_key, setting_value):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO app_settings (setting_key, setting_value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(setting_key) DO UPDATE SET
            setting_value = excluded.setting_value,
            updated_at = CURRENT_TIMESTAMP
        """,
        (setting_key, setting_value),
    )

    conn.commit()
    conn.close()


def record_backup_history(commit_hash, branch, status, message):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO backup_history (
            timestamp,
            commit_hash,
            branch,
            status,
            message
        )
        VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?)
        """,
        (commit_hash, branch, status, message),
    )
    conn.commit()
    conn.close()


def get_backup_history(limit=20):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM backup_history
        ORDER BY timestamp DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_last_successful_backup():
    conn = get_connection()
    row = conn.execute(
        """
        SELECT *
        FROM backup_history
        WHERE status = 'succeeded'
        ORDER BY timestamp DESC, id DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_smtp_settings():
    try:
        port = int(get_app_setting("smtp_port", "587") or 587)
    except (TypeError, ValueError):
        port = 587
    encryption = get_app_setting("smtp_encryption", "")
    if not encryption:
        encryption = "TLS" if get_app_setting("smtp_use_tls", "1") == "1" else "None"
    return {
        "host": get_app_setting("smtp_host", ""),
        "port": port,
        "username": get_app_setting("smtp_username", ""),
        "password": get_app_setting("smtp_password", ""),
        "from_email": get_app_setting("smtp_from_email", ""),
        "from_name": get_app_setting("smtp_from_name", "1Aim"),
        "encryption": encryption if encryption in ["SSL", "TLS", "None"] else "TLS",
    }


def is_smtp_configured():
    settings = get_smtp_settings()
    return bool(settings["host"] and settings["from_email"])


def classify_smtp_error(exc):
    text = str(exc)
    if isinstance(exc, (socket.timeout, TimeoutError)) or "timed out" in text.lower():
        return "Timeout: Cannot connect to SMTP server within the timeout window."
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "Authentication failed: Invalid credentials."
    if isinstance(exc, ssl.SSLError):
        return "TLS negotiation failed: Check encryption type and port."
    if isinstance(exc, (ConnectionRefusedError, socket.gaierror, OSError)):
        return f"Cannot connect to SMTP server: {text}"
    if isinstance(exc, smtplib.SMTPConnectError):
        return f"Cannot connect to SMTP server: {text}"
    if isinstance(exc, smtplib.SMTPServerDisconnected):
        return f"Cannot connect to SMTP server: {text}"
    if isinstance(exc, smtplib.SMTPException):
        return f"SMTP error: {text}"
    return text


def open_smtp_connection(settings, timeout=20):
    if settings["encryption"] == "SSL":
        return smtplib.SMTP_SSL(settings["host"], settings["port"], timeout=timeout)

    server = smtplib.SMTP(settings["host"], settings["port"], timeout=timeout)
    if settings["encryption"] == "TLS":
        server.starttls()
    return server


def test_smtp_connection():
    settings = get_smtp_settings()
    if not settings["host"]:
        return {
            "ok": False,
            "connection": "Missing SMTP host",
            "encryption": "Not tested",
            "authentication": "Not tested",
            "error": "SMTP host is required.",
        }

    try:
        with open_smtp_connection(settings) as server:
            connection = "Connection OK"
            encryption = "Encryption OK"
            if settings["username"]:
                server.login(settings["username"], settings["password"])
                authentication = "Authentication OK"
            else:
                authentication = "Authentication skipped"
        return {
            "ok": True,
            "connection": connection,
            "encryption": encryption,
            "authentication": authentication,
            "error": "",
        }
    except Exception as exc:
        message = classify_smtp_error(exc)
        lower = message.lower()
        return {
            "ok": False,
            "connection": "Cannot connect to SMTP server" if "connect" in lower or "timeout" in lower else "Connection failed",
            "encryption": "TLS negotiation failed" if "tls" in lower else "Encryption failed" if settings["encryption"] != "None" else "No encryption",
            "authentication": "Authentication failed" if "authentication" in lower or "credentials" in lower else "Not completed",
            "error": message,
        }


def looks_like_html(value):
    return bool(re.search(r"</?[a-z][\s\S]*>", value or "", flags=re.IGNORECASE))


def strip_html(value):
    text = re.sub(r"<\s*br\s*/?>", "\n", value or "", flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text).strip()


def html_from_plain_text(value):
    return "<br>\n".join(escape(value or "").splitlines())


def get_tracking_base_url():
    return clean_value(get_app_setting("tracking_base_url", ""))


def build_tracking_url(token):
    base_url = get_tracking_base_url().rstrip("/")
    if not base_url or not token:
        return ""
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}track_open={token}"


def append_tracking_pixel(message_body, tracking_token=""):
    tracking_url = build_tracking_url(tracking_token)
    if not tracking_url:
        return message_body
    pixel = (
        f'<img src="{escape(tracking_url)}" width="1" height="1" '
        'alt="" style="display:none;border:0;opacity:0;width:1px;height:1px;" />'
    )
    if looks_like_html(message_body):
        return f"{message_body}\n{pixel}"
    return f"{html_from_plain_text(message_body)}<br>\n{pixel}"


def send_email_via_smtp(to_email, subject, message_body, tracking_token=""):
    settings = get_smtp_settings()
    if not is_smtp_configured():
        return False, "SMTP settings are not configured."

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = (
        f"{settings['from_name']} <{settings['from_email']}>"
        if settings["from_name"]
        else settings["from_email"]
    )
    message["To"] = to_email
    if tracking_token:
        message["Message-ID"] = f"<{tracking_token}@1aimgrowthengine.local>"
        message["X-1Aim-Tracking-Token"] = tracking_token
    tracked_body = append_tracking_pixel(message_body, tracking_token)
    if looks_like_html(tracked_body):
        message.set_content(strip_html(message_body))
        message.add_alternative(tracked_body.replace("\n", "<br>\n"), subtype="html")
    else:
        message.set_content(tracked_body)

    try:
        with open_smtp_connection(settings, timeout=30) as server:
            if settings["username"]:
                server.login(settings["username"], settings["password"])
            server.send_message(message)
        return True, ""
    except Exception as exc:
        return False, classify_smtp_error(exc)


def send_outreach_preview_email(to_email, messages, limit=3):
    sent = 0
    failed = 0
    errors = []
    for message in messages[:limit]:
        ok, error_message = send_email_via_smtp(
            to_email,
            f"[PREVIEW] {message.get('subject', '')}",
            message.get("message_body", ""),
        )
        if ok:
            sent += 1
        else:
            failed += 1
            errors.append(error_message)
    return {"sent": sent, "failed": failed, "errors": errors}


def record_outreach_open(tracking_token, user_agent=""):
    token = clean_value(tracking_token)
    if not token:
        return {"ok": False, "message": "Missing tracking token."}
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT *
        FROM outreach_messages
        WHERE tracking_token = ?
        LIMIT 1
        """,
        (token,),
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "message": "Tracking token not found."}
    first_open = not clean_value(row["opened_at"])
    cur.execute(
        """
        UPDATE outreach_messages
        SET opened_at = COALESCE(opened_at, CURRENT_TIMESTAMP),
            delivery_status = CASE
                WHEN delivery_status IN ('Sent', 'Unknown', '') THEN 'Delivered'
                ELSE delivery_status
            END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (row["id"],),
    )
    if first_open:
        log_crm_activity(
            cur,
            "Email Opened",
            f"Campaign email opened: {row['subject']} ({row['email']})",
            lead_id=row["lead_id"],
            organization_id=row["organization_id"],
            contact_id=row["contact_id"],
            user="tracking",
        )
    conn.commit()
    conn.close()
    return {"ok": True, "message": "Open tracked.", "first_open": first_open}


BOUNCE_SUBJECT_MARKERS = [
    "undelivered mail returned to sender",
    "mail delivery failed",
    "delivery status notification",
    "returned mail",
    "mailer-daemon",
]

HARD_BOUNCE_MARKERS = [
    "5.1.1",
    "recipient does not exist",
    "user unknown",
    "mailbox unavailable",
    "no such user",
]

SOFT_BOUNCE_MARKERS = [
    "mailbox full",
    "temporarily unavailable",
    "connection timed out",
    "greylisted",
]


def decode_mime_header(value):
    parts = decode_header(value or "")
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="ignore"))
        else:
            decoded.append(part)
    return "".join(decoded)


def extract_message_text(message):
    chunks = []
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type not in ["text/plain", "message/delivery-status", "text/html"]:
                continue
            payload = part.get_payload(decode=True)
            if payload:
                chunks.append(payload.decode(part.get_content_charset() or "utf-8", errors="ignore"))
    else:
        payload = message.get_payload(decode=True)
        if payload:
            chunks.append(payload.decode(message.get_content_charset() or "utf-8", errors="ignore"))
    return "\n".join(chunks)


def parse_bounced_email(body):
    patterns = [
        r"Final-Recipient:\s*(?:rfc822;)?\s*([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})",
        r"Original-Recipient:\s*(?:rfc822;)?\s*([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})",
        r"RCPT TO:\s*<?([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})>?",
        r"Recipient:\s*<?([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})>?",
    ]
    for pattern in patterns:
        match = re.search(pattern, body or "", flags=re.IGNORECASE)
        if match:
            return match.group(1).lower()
    emails = re.findall(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", body or "", flags=re.IGNORECASE)
    ignored_domains = ["1aimlogistics.com"]
    for found in emails:
        lowered = found.lower()
        if not any(lowered.endswith(f"@{domain}") for domain in ignored_domains):
            return lowered
    return emails[0].lower() if emails else ""


def classify_bounce(body):
    lower = (body or "").lower()
    if any(marker in lower for marker in HARD_BOUNCE_MARKERS):
        return "Hard"
    if any(marker in lower for marker in SOFT_BOUNCE_MARKERS) or re.search(r"\b4\.\d+\.\d+\b", lower):
        return "Soft"
    return "Unknown"


def summarize_bounce_reason(body):
    lower = (body or "").lower()
    for marker in HARD_BOUNCE_MARKERS + SOFT_BOUNCE_MARKERS:
        if marker in lower:
            return marker
    status_match = re.search(r"\b[45]\.\d+\.\d+\b", body or "")
    if status_match:
        return status_match.group(0)
    lines = [line.strip() for line in (body or "").splitlines() if line.strip()]
    return lines[0][:240] if lines else "Bounce reason unavailable"


def record_processed_bounce(cur, message_id, bounced_email, bounce_type, reason):
    cur.execute(
        """
        INSERT OR IGNORE INTO processed_bounce_messages (
            message_id,
            processed_at,
            bounced_email,
            bounce_type,
            reason
        )
        VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?)
        """,
        (message_id, bounced_email, bounce_type, reason),
    )


def update_contact_email_status(contact_id, status, reason="", user="admin"):
    conn = get_connection()
    cur = conn.cursor()
    contact = cur.execute(
        """
        SELECT contacts.id, contacts.email, contacts.notes, contacts.organization_id, leads.id AS lead_id
        FROM contacts
        LEFT JOIN leads ON leads.contact_id = contacts.id
        WHERE contacts.id = ?
        ORDER BY leads.updated_at DESC, leads.id DESC
        LIMIT 1
        """,
        (contact_id,),
    ).fetchone()
    if not contact:
        conn.close()
        return False

    note_suffix = ""
    if reason:
        note_suffix = f"\nEmail marked {status} on {date.today().isoformat()}: {reason}"
    cur.execute(
        """
        UPDATE contacts
        SET email_status = ?,
            notes = COALESCE(notes, '') || ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, note_suffix, contact_id),
    )
    log_crm_activity(
        cur,
        f"Email {status}",
        f"{contact['email']} marked {status}. {reason}".strip(),
        lead_id=contact["lead_id"],
        organization_id=contact["organization_id"],
        contact_id=contact_id,
        user=user,
    )
    conn.commit()
    conn.close()
    return True


def get_invalid_email_contacts(status_filter="All", search_text="", limit=100):
    status = clean_value(status_filter)
    search = f"%{clean_value(search_text)}%"
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            contacts.id AS contact_id,
            contacts.name AS contact_name,
            contacts.full_name,
            contacts.email,
            COALESCE(contacts.email_status, 'Unknown') AS email_status,
            contacts.notes,
            contacts.updated_at,
            organizations.id AS organization_id,
            organizations.name AS organization_name,
            organizations.country,
            organizations.city,
            latest_leads.lead_id
        FROM contacts
        LEFT JOIN organizations ON organizations.id = contacts.organization_id
        LEFT JOIN (
            SELECT contact_id, MAX(id) AS lead_id
            FROM leads
            GROUP BY contact_id
        ) latest_leads ON latest_leads.contact_id = contacts.id
        WHERE COALESCE(contacts.email_status, 'Unknown') IN ('Bounced', 'Invalid')
            AND (? = 'All' OR COALESCE(contacts.email_status, 'Unknown') = ?)
            AND (
                ? = '%%'
                OR LOWER(COALESCE(contacts.email, '')) LIKE LOWER(?)
                OR LOWER(COALESCE(contacts.name, contacts.full_name, '')) LIKE LOWER(?)
                OR LOWER(COALESCE(organizations.name, '')) LIKE LOWER(?)
            )
        ORDER BY contacts.updated_at DESC, contacts.id DESC
        LIMIT ?
        """,
        (
            status,
            status,
            search,
            search,
            search,
            search,
            int(limit or 100),
        ),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_contact_email_address(contact_id, email_address, status="Valid", reason="", user="admin"):
    conn = get_connection()
    cur = conn.cursor()
    contact = cur.execute(
        """
        SELECT contacts.id, contacts.email, contacts.organization_id, leads.id AS lead_id
        FROM contacts
        LEFT JOIN leads ON leads.contact_id = contacts.id
        WHERE contacts.id = ?
        ORDER BY leads.updated_at DESC, leads.id DESC
        LIMIT 1
        """,
        (contact_id,),
    ).fetchone()
    if not contact:
        conn.close()
        return False

    old_email = contact["email"] or ""
    note = f"\nEmail corrected on {date.today().isoformat()}: {old_email} -> {email_address}"
    if reason:
        note += f" ({reason})"
    cur.execute(
        """
        UPDATE contacts
        SET email = ?,
            email_status = ?,
            notes = COALESCE(notes, '') || ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (email_address, status, note, contact_id),
    )
    log_crm_activity(
        cur,
        "Contact Update",
        f"Email corrected from {old_email or '-'} to {email_address}; status {status}",
        lead_id=contact["lead_id"],
        organization_id=contact["organization_id"],
        contact_id=contact_id,
        user=user,
    )
    conn.commit()
    conn.close()
    return True


def apply_bounce_to_crm(cur, bounced_email, bounce_type, reason, user="admin"):
    contact = cur.execute(
        """
        SELECT contacts.id, contacts.email, contacts.notes, contacts.organization_id, leads.id AS lead_id
        FROM contacts
        LEFT JOIN leads ON leads.contact_id = contacts.id
        WHERE LOWER(TRIM(contacts.email)) = LOWER(TRIM(?))
        ORDER BY leads.updated_at DESC, leads.id DESC
        LIMIT 1
        """,
        (bounced_email,),
    ).fetchone()
    if not contact:
        return False

    activity_type = "Email Bounced" if bounce_type == "Hard" else "Email Soft Bounce"
    if bounce_type == "Hard":
        note = f"\nEmail hard bounced on {date.today().isoformat()}: {reason}"
        cur.execute(
            """
            UPDATE contacts
            SET email_status = 'Bounced',
                notes = COALESCE(notes, '') || ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (note, contact["id"]),
        )
        cur.execute(
            """
            UPDATE outreach_messages
            SET delivery_status = 'Bounced',
                status = CASE WHEN status = 'Sent' THEN 'Bounced' ELSE status END,
                error_message = COALESCE(NULLIF(error_message, ''), ?),
                updated_at = CURRENT_TIMESTAMP
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))
            """,
            (reason, bounced_email),
        )
    else:
        cur.execute(
            """
            UPDATE outreach_messages
            SET delivery_status = 'Bounced',
                error_message = COALESCE(NULLIF(error_message, ''), ?),
                updated_at = CURRENT_TIMESTAMP
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))
            """,
            (reason, bounced_email),
        )

    log_crm_activity(
        cur,
        activity_type,
        f"{bounced_email}: {reason}",
        lead_id=contact["lead_id"],
        organization_id=contact["organization_id"],
        contact_id=contact["id"],
        user=user,
    )
    return True


def process_email_bounces(max_messages=100, user="admin"):
    settings = get_smtp_settings()
    username = settings.get("username")
    password = settings.get("password")
    host = get_app_setting("imap_host", "mail.1aimlogistics.com")
    try:
        port = int(get_app_setting("imap_port", "993") or 993)
    except (TypeError, ValueError):
        port = 993

    result = {
        "scanned": 0,
        "hard_bounces": 0,
        "soft_bounces": 0,
        "contacts_updated": 0,
        "unmatched": [],
        "errors": [],
    }
    if not username or not password:
        result["errors"].append("IMAP username/password missing. Save SMTP username and password first.")
        return result

    conn = get_connection()
    cur = conn.cursor()
    try:
        with imaplib.IMAP4_SSL(host, port) as mailbox:
            mailbox.login(username, password)
            mailbox.select("INBOX")
            status, data = mailbox.search(None, "ALL")
            if status != "OK":
                result["errors"].append("Unable to search mailbox.")
                return result
            message_ids = data[0].split()[-int(max_messages):]
            for message_id_bytes in reversed(message_ids):
                imap_id = message_id_bytes.decode()
                fetch_status, fetch_data = mailbox.fetch(message_id_bytes, "(RFC822)")
                if fetch_status != "OK" or not fetch_data or not fetch_data[0]:
                    continue
                raw_message = fetch_data[0][1]
                message = email.message_from_bytes(raw_message)
                mail_message_id = message.get("Message-ID") or f"imap:{imap_id}"
                already_processed = cur.execute(
                    "SELECT 1 FROM processed_bounce_messages WHERE message_id = ?",
                    (mail_message_id,),
                ).fetchone()
                if already_processed:
                    continue
                subject = decode_mime_header(message.get("Subject", ""))
                if not any(marker in subject.lower() for marker in BOUNCE_SUBJECT_MARKERS):
                    continue

                result["scanned"] += 1
                body = extract_message_text(message)
                bounced_email = parse_bounced_email(body)
                bounce_type = classify_bounce(body)
                reason = summarize_bounce_reason(body)
                if bounce_type == "Hard":
                    result["hard_bounces"] += 1
                elif bounce_type == "Soft":
                    result["soft_bounces"] += 1

                updated = bool(bounced_email) and apply_bounce_to_crm(cur, bounced_email, bounce_type, reason, user=user)
                if updated:
                    result["contacts_updated"] += 1
                elif bounced_email:
                    result["unmatched"].append(bounced_email)
                else:
                    result["unmatched"].append("(no recipient found)")
                record_processed_bounce(cur, mail_message_id, bounced_email, bounce_type, reason)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        result["errors"].append(str(exc))
    finally:
        conn.close()
    return result


def normalize_email_subject(subject):
    value = clean_value(subject).lower()
    value = re.sub(r"^\s*(re|fw|fwd)\s*:\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def find_outreach_reply_match(cur, sender_email, subject, body, headers_text):
    token_match = re.search(r"([a-f0-9]{32})@1aimgrowthengine\.local", headers_text or "", flags=re.IGNORECASE)
    if not token_match:
        token_match = re.search(r"\b([a-f0-9]{32})\b", (headers_text or "") + "\n" + (body or ""), flags=re.IGNORECASE)
    if token_match:
        row = cur.execute(
            """
            SELECT *
            FROM outreach_messages
            WHERE tracking_token = ?
            ORDER BY sent_at DESC, id DESC
            LIMIT 1
            """,
            (token_match.group(1),),
        ).fetchone()
        if row:
            return row

    clean_sender = clean_value(sender_email).lower()
    clean_subject = normalize_email_subject(subject)
    if not clean_sender:
        return None
    rows = cur.execute(
        """
        SELECT *
        FROM outreach_messages
        WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))
            AND status = 'Sent'
        ORDER BY sent_at DESC, id DESC
        LIMIT 20
        """,
        (clean_sender,),
    ).fetchall()
    for row in rows:
        outbound_subject = normalize_email_subject(row["subject"])
        if clean_subject and outbound_subject and (clean_subject == outbound_subject or outbound_subject in clean_subject):
            return row
    return rows[0] if rows else None


def record_processed_reply(cur, message_id, outreach_message_id, sender_email, subject):
    cur.execute(
        """
        INSERT OR IGNORE INTO processed_reply_messages (
            message_id,
            outreach_message_id,
            sender_email,
            subject,
            processed_at
        )
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (message_id, outreach_message_id, sender_email, subject),
    )


def process_email_replies(max_messages=100, user="admin"):
    settings = get_smtp_settings()
    username = settings.get("username")
    password = settings.get("password")
    host = get_app_setting("imap_host", "mail.1aimlogistics.com")
    try:
        port = int(get_app_setting("imap_port", "993") or 993)
    except (TypeError, ValueError):
        port = 993

    result = {"scanned": 0, "replies_found": 0, "messages_updated": 0, "unmatched": [], "errors": []}
    if not username or not password:
        result["errors"].append("IMAP username/password missing. Save SMTP username and password first.")
        return result

    conn = get_connection()
    cur = conn.cursor()
    try:
        with imaplib.IMAP4_SSL(host, port) as mailbox:
            mailbox.login(username, password)
            mailbox.select("INBOX")
            status, data = mailbox.search(None, "ALL")
            if status != "OK":
                result["errors"].append("Unable to search mailbox.")
                return result
            message_ids = data[0].split()[-int(max_messages):]
            for message_id_bytes in reversed(message_ids):
                imap_id = message_id_bytes.decode()
                fetch_status, fetch_data = mailbox.fetch(message_id_bytes, "(RFC822)")
                if fetch_status != "OK" or not fetch_data or not fetch_data[0]:
                    continue
                raw_message = fetch_data[0][1]
                message = email.message_from_bytes(raw_message)
                mail_message_id = message.get("Message-ID") or f"reply-imap:{imap_id}"
                already_processed = cur.execute(
                    "SELECT 1 FROM processed_reply_messages WHERE message_id = ?",
                    (mail_message_id,),
                ).fetchone()
                if already_processed:
                    continue

                subject = decode_mime_header(message.get("Subject", ""))
                subject_lower = subject.lower()
                if any(marker in subject_lower for marker in BOUNCE_SUBJECT_MARKERS):
                    continue
                sender_email = parseaddr(message.get("From", ""))[1]
                if sender_email.lower() == clean_value(settings.get("from_email")).lower():
                    continue
                if not subject_lower.startswith(("re:", "fw:", "fwd:")) and "@1aimgrowthengine.local" not in (
                    (message.get("In-Reply-To", "") or "") + (message.get("References", "") or "")
                ):
                    continue

                result["scanned"] += 1
                body = extract_message_text(message)
                headers_text = "\n".join(
                    [
                        message.get("In-Reply-To", "") or "",
                        message.get("References", "") or "",
                        message.get("X-1Aim-Tracking-Token", "") or "",
                    ]
                )
                matched = find_outreach_reply_match(cur, sender_email, subject, body, headers_text)
                if not matched:
                    result["unmatched"].append(f"{sender_email} | {subject}")
                    record_processed_reply(cur, mail_message_id, None, sender_email, subject)
                    continue

                result["replies_found"] += 1
                cur.execute(
                    """
                    UPDATE outreach_messages
                    SET replied_at = COALESCE(replied_at, CURRENT_TIMESTAMP),
                        delivery_status = 'Replied',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (matched["id"],),
                )
                cur.execute(
                    """
                    UPDATE leads
                    SET lead_status = CASE
                            WHEN lead_status IN ('Qualified', 'Converted', 'Disqualified') THEN lead_status
                            ELSE 'Replied'
                        END,
                        status = CASE
                            WHEN status IN ('Qualified', 'Converted', 'Disqualified') THEN status
                            ELSE 'Replied'
                        END,
                        next_action = 'Continue conversation / ask for Vietnam shipments',
                        next_action_date = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (days_from_today(14), matched["lead_id"]),
                )
                if matched["contact_id"]:
                    cur.execute(
                        """
                        UPDATE contacts
                        SET relationship_status = CASE
                                WHEN relationship_status IN ('Active', 'Inactive') THEN relationship_status
                                ELSE 'Warm'
                            END,
                            last_contacted_at = CURRENT_TIMESTAMP,
                            next_follow_up_at = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (days_from_today(14), matched["contact_id"]),
                    )
                log_crm_activity(
                    cur,
                    "Email Replied",
                    f"Reply detected from {sender_email}: {subject}",
                    lead_id=matched["lead_id"],
                    organization_id=matched["organization_id"],
                    contact_id=matched["contact_id"],
                    user=user,
                )
                record_processed_reply(cur, mail_message_id, matched["id"], sender_email, subject)
                result["messages_updated"] += 1
        conn.commit()
    except Exception as exc:
        conn.rollback()
        result["errors"].append(str(exc))
    finally:
        conn.close()
    return result


def get_campaign_filter_options():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            COALESCE(organizations.country, leads.country, '') AS country,
            COALESCE(organizations.membership, leads.membership, '') AS membership,
            COALESCE(leads.lead_status, 'New') AS lead_status,
            COALESCE(contacts.relationship_status, 'New') AS relationship_status
        FROM leads
        LEFT JOIN organizations ON organizations.id = leads.organization_id
        LEFT JOIN contacts ON contacts.id = leads.contact_id
        """
    ).fetchall()
    conn.close()

    def values_for(key):
        return sorted({clean_value(row[key]) for row in rows if clean_value(row[key])})

    return {
        "countries": values_for("country"),
        "memberships": values_for("membership"),
        "lead_statuses": values_for("lead_status"),
        "relationship_statuses": values_for("relationship_status"),
    }


def get_campaign_audience(filters):
    country = clean_value(filters.get("country"))
    membership = clean_value(filters.get("membership"))
    lead_status = clean_value(filters.get("lead_status"))
    relationship_status = clean_value(filters.get("relationship_status"))
    limit = int(filters.get("limit") or 50)

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            leads.id AS lead_id,
            leads.organization_id,
            leads.contact_id,
            COALESCE(contacts.name, contacts.contact_person, contacts.full_name, leads.contact_person, '') AS contact_name,
            COALESCE(contacts.job_title, leads.job_title, '') AS job_title,
            COALESCE(organizations.name, leads.company_name, '') AS organization_name,
            COALESCE(organizations.country, leads.country, '') AS country,
            COALESCE(organizations.city, leads.city, '') AS city,
            COALESCE(organizations.membership, leads.membership, '') AS membership,
            COALESCE(leads.lead_status, 'New') AS lead_status,
            COALESCE(contacts.relationship_status, 'New') AS relationship_status,
            COALESCE(contacts.email_status, 'Unknown') AS email_status,
            COALESCE(contacts.email, leads.email, '') AS email
        FROM leads
        LEFT JOIN organizations ON organizations.id = leads.organization_id
        LEFT JOIN contacts ON contacts.id = leads.contact_id
        WHERE COALESCE(contacts.email, leads.email, '') <> ''
            AND COALESCE(contacts.email_status, 'Unknown') NOT IN ('Bounced', 'Invalid')
            AND (? = '' OR LOWER(TRIM(COALESCE(organizations.country, leads.country, ''))) = LOWER(TRIM(?)))
            AND (? = '' OR LOWER(COALESCE(organizations.membership, leads.membership, '')) LIKE '%' || LOWER(?) || '%')
            AND (? = '' OR COALESCE(leads.lead_status, 'New') = ?)
            AND (? = '' OR COALESCE(contacts.relationship_status, 'New') = ?)
        ORDER BY COALESCE(leads.action_score, 0) DESC,
            leads.next_action_date ASC,
            leads.id ASC
        LIMIT ?
        """,
        (
            country,
            country,
            membership,
            membership,
            lead_status,
            lead_status,
            relationship_status,
            relationship_status,
            limit,
        ),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_campaign_invalid_email_skip_count(filters):
    country = clean_value(filters.get("country"))
    membership = clean_value(filters.get("membership"))
    lead_status = clean_value(filters.get("lead_status"))
    relationship_status = clean_value(filters.get("relationship_status"))

    conn = get_connection()
    row = conn.execute(
        """
        SELECT COUNT(*) AS skipped
        FROM leads
        LEFT JOIN organizations ON organizations.id = leads.organization_id
        LEFT JOIN contacts ON contacts.id = leads.contact_id
        WHERE COALESCE(contacts.email, leads.email, '') <> ''
            AND COALESCE(contacts.email_status, 'Unknown') IN ('Bounced', 'Invalid')
            AND (? = '' OR LOWER(TRIM(COALESCE(organizations.country, leads.country, ''))) = LOWER(TRIM(?)))
            AND (? = '' OR LOWER(COALESCE(organizations.membership, leads.membership, '')) LIKE '%' || LOWER(?) || '%')
            AND (? = '' OR COALESCE(leads.lead_status, 'New') = ?)
            AND (? = '' OR COALESCE(contacts.relationship_status, 'New') = ?)
        """,
        (
            country,
            country,
            membership,
            membership,
            lead_status,
            lead_status,
            relationship_status,
            relationship_status,
        ),
    ).fetchone()
    conn.close()
    return int(row["skipped"] or 0) if row else 0


def get_email_signature_settings():
    return {
        "name": get_app_setting("signature_name", "Kien Ho"),
        "title": get_app_setting("signature_title", "CEO"),
        "company": get_app_setting("signature_company", "1Aim Logistics"),
        "phone": get_app_setting("signature_phone", ""),
        "email": get_app_setting("signature_email", ""),
        "website": get_app_setting("signature_website", ""),
        "wechat": get_app_setting("signature_wechat", ""),
        "whatsapp": get_app_setting("signature_whatsapp", ""),
        "html": get_app_setting("signature_html", ""),
    }


def render_email_signature():
    signature = get_email_signature_settings()
    if clean_value(signature["html"]):
        return signature["html"]

    lines = [
        "Best regards,",
        "",
        signature["name"],
        signature["title"],
        signature["company"],
    ]
    contact_lines = []
    if signature["phone"]:
        contact_lines.append(f"Mobile: {signature['phone']}")
    if signature["email"]:
        contact_lines.append(f"Email: {signature['email']}")
    if signature["website"]:
        contact_lines.append(f"Website: {signature['website']}")
    if signature["wechat"]:
        contact_lines.append(f"WeChat: {signature['wechat']}")
    if signature["whatsapp"]:
        contact_lines.append(f"WhatsApp: {signature['whatsapp']}")
    if contact_lines:
        lines.extend(["", *contact_lines])
    return "\n".join(line for line in lines if line is not None)


def render_subject_template(subject_template, row, campaign_name=""):
    company = clean_value(row_value(row, "organization_name", "your team"))
    contact_name = clean_value(row_value(row, "contact_name", ""))
    values = {
        "{{name}}": contact_name,
        "{{contact_name}}": contact_name,
        "{{first_name}}": contact_name.split()[0] if contact_name else "",
        "{{company}}": company,
        "{{city}}": clean_value(row_value(row, "city", "")),
        "{{country}}": clean_value(row_value(row, "country", "")),
        "{{membership}}": clean_value(row_value(row, "membership", "")),
        "{{job_title}}": clean_value(row_value(row, "job_title", "")),
        "{{campaign}}": campaign_name,
    }
    subject = subject_template or "OLO HCM 2026, {{first_name}}"
    for token, value in values.items():
        subject = subject.replace(token, value)
    return " ".join(subject.split())


def generate_outreach_subject(row, campaign_name, subject_template=None):
    return render_subject_template(subject_template or "OLO HCM 2026, {{first_name}}", row, campaign_name)


def generate_outreach_message(row, campaign_name, instructions=""):
    raw_name = clean_value(row_value(row, "contact_name", ""))
    instruction_text = normalize(instructions)
    use_first_name = "first name" in instruction_text
    name = raw_name.split()[0] if use_first_name and raw_name else raw_name or "there"
    company = clean_value(row_value(row, "organization_name", "your team"))
    city = clean_value(row_value(row, "city", ""))
    country = clean_value(row_value(row, "country", ""))
    job_title = clean_value(row_value(row, "job_title", ""))

    location = " / ".join(part for part in [city, country] if part)
    role_line = f" I noticed your role as {job_title}." if job_title else ""
    location_line = f" Since {company} is based in {location}, I wanted to reach out directly." if location else ""
    mention_olo = "olo" in instruction_text
    avoid_backend = "avoid saying \"backend support\"" in instruction_text or "avoid saying backend support" in instruction_text
    friendly = "friendly" in instruction_text
    short = "under 120 words" in instruction_text or "short" in instruction_text

    intro = "Hope you're doing well." if friendly else ""
    support_phrase = (
        "We support freight forwarders with Vietnam-related shipments and overseas coordination."
        if avoid_backend
        else "We support freight forwarders with Vietnam-related shipments, overseas coordination, and backend follow-up work."
    )
    olo_phrase = " I would also be happy to connect around OLO HCM." if mention_olo else ""

    if short:
        body = (
            f"Hi {name},\n\n"
            f"This is Kien from 1Aim in Vietnam. {intro}\n\n"
            f"{support_phrase}{olo_phrase} Would it be useful to stay connected for Vietnam inquiries?\n\n"
        )
    else:
        body = (
            f"Hi {name},\n\n"
            f"This is Kien from 1Aim in Vietnam.{role_line}{location_line} {intro}\n\n"
            f"{support_phrase} "
            "Our goal is to help partners respond faster and keep customers moving."
            f"{olo_phrase}\n\n"
            "Would it be useful to stay connected and explore how 1Aim can support your team when you have Vietnam inquiries?\n\n"
        )

    return body + render_email_signature()


def get_outreach_campaign_templates():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM outreach_campaign_templates
        ORDER BY template_name
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_outreach_campaign_template(template_name, campaign_name, subject_template, instructions):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO outreach_campaign_templates (
            template_name,
            campaign_name,
            subject_template,
            instructions,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(template_name) DO UPDATE SET
            campaign_name = excluded.campaign_name,
            subject_template = excluded.subject_template,
            instructions = excluded.instructions,
            updated_at = CURRENT_TIMESTAMP
        """,
        (template_name, campaign_name, subject_template, instructions),
    )
    conn.commit()
    conn.close()


def create_and_send_outreach_campaign(campaign_name, filters, messages, subject_template="", instructions="", user="admin"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO outreach_campaigns (
            campaign_name,
            country_filter,
            membership_filter,
            lead_status_filter,
            relationship_status_filter,
            subject_template,
            instructions,
            status,
            created_at,
            approved_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Approved', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            campaign_name,
            clean_value(filters.get("country")),
            clean_value(filters.get("membership")),
            clean_value(filters.get("lead_status")),
            clean_value(filters.get("relationship_status")),
            subject_template,
            instructions,
        ),
    )
    campaign_id = cur.lastrowid

    results = {"sent": 0, "failed": 0, "skipped": 0, "campaign_id": campaign_id, "failed_messages": []}
    for message in messages:
        tracking_token = uuid.uuid4().hex
        ok, error_message = send_email_via_smtp(
            message["email"],
            message["subject"],
            message["message_body"],
            tracking_token=tracking_token,
        )
        status = "Sent" if ok else "Failed"
        sent_at = datetime.now().isoformat(timespec="seconds") if ok else None
        cur.execute(
            """
            INSERT INTO outreach_messages (
                campaign_id,
                lead_id,
                organization_id,
                contact_id,
                email,
                subject,
                message_body,
                message_version,
                tracking_token,
                status,
                delivery_status,
                sent_at,
                error_message,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                campaign_id,
                message.get("lead_id"),
                message.get("organization_id"),
                message.get("contact_id"),
                message.get("email"),
                message.get("subject"),
                message.get("message_body"),
                int(message.get("message_version") or 1),
                tracking_token,
                status,
                status,
                sent_at,
                error_message,
            ),
        )

        if ok:
            results["sent"] += 1
            cur.execute(
                """
                UPDATE leads
                SET lead_status = 'Contacted',
                    status = 'Contacted',
                    campaign = COALESCE(NULLIF(campaign, ''), ?),
                    next_action = 'Follow-up',
                    next_action_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (campaign_name, days_from_today(7), message.get("lead_id")),
            )
            if message.get("contact_id"):
                cur.execute(
                    """
                    UPDATE contacts
                    SET last_contacted_at = CURRENT_TIMESTAMP,
                        next_follow_up_at = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (days_from_today(7), message.get("contact_id")),
                )
            log_crm_activity(
                cur,
                "Email Sent",
                f"Campaign {campaign_name}: {message.get('subject')} sent to {message.get('email')} at {sent_at}",
                lead_id=message.get("lead_id"),
                organization_id=message.get("organization_id"),
                contact_id=message.get("contact_id"),
                user=user,
            )
        else:
            results["failed"] += 1
            results["failed_messages"].append(
                {
                    "email": message.get("email"),
                    "contact": message.get("contact_name"),
                    "company": message.get("organization_name"),
                    "subject": message.get("subject"),
                    "error": error_message,
                }
            )

    cur.execute(
        """
        UPDATE outreach_campaigns
        SET status = ?,
            sent_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        ("Sent" if results["failed"] == 0 else "Partial", campaign_id),
    )
    conn.commit()
    conn.close()
    return results


def get_outreach_campaign_metrics():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            outreach_campaigns.id,
            outreach_campaigns.campaign_name,
            outreach_campaigns.status,
            outreach_campaigns.sent_at,
            COUNT(outreach_messages.id) AS total,
            SUM(CASE WHEN outreach_messages.status = 'Sent' THEN 1 ELSE 0 END) AS sent,
            SUM(CASE WHEN outreach_messages.opened_at IS NOT NULL THEN 1 ELSE 0 END) AS opened,
            SUM(CASE WHEN outreach_messages.replied_at IS NOT NULL OR leads.lead_status IN ('Replied', 'Qualified', 'Converted') THEN 1 ELSE 0 END) AS replied,
            SUM(CASE WHEN outreach_messages.qualified_at IS NOT NULL OR leads.lead_status IN ('Qualified', 'Converted') THEN 1 ELSE 0 END) AS qualified
        FROM outreach_campaigns
        LEFT JOIN outreach_messages ON outreach_messages.campaign_id = outreach_campaigns.id
        LEFT JOIN leads ON leads.id = outreach_messages.lead_id
        GROUP BY outreach_campaigns.id
        ORDER BY outreach_campaigns.created_at DESC, outreach_campaigns.id DESC
        LIMIT 20
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_existing_lead_keys():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            LOWER(TRIM(COALESCE(organizations.name, leads.company_name, ''))) AS company_name,
            LOWER(TRIM(COALESCE(organizations.country, leads.country, ''))) AS country,
            LOWER(TRIM(COALESCE(contacts.name, contacts.contact_person, contacts.full_name, leads.contact_person, ''))) AS contact_person,
            LOWER(TRIM(COALESCE(contacts.email, leads.email, ''))) AS email,
            LOWER(TRIM(COALESCE(contacts.wechat, leads.wechat, ''))) AS wechat,
            LOWER(TRIM(COALESCE(contacts.whatsapp, leads.whatsapp, ''))) AS whatsapp,
            LOWER(TRIM(COALESCE(leads.campaign, ''))) AS campaign
        FROM leads
        LEFT JOIN organizations ON organizations.id = leads.organization_id
        LEFT JOIN contacts ON contacts.id = leads.contact_id
        """
    ).fetchall()

    conn.close()
    return rows


def import_leads(leads, owner="admin"):
    conn = get_connection()
    cur = conn.cursor()
    imported_count = 0

    for lead in leads:
        lead = dict(lead)
        lead["source"] = lead.get("source") or "Excel Import"
        lead["lead_status"] = lead.get("lead_status") or "New"
        lead["next_action"] = lead.get("next_action") or "Send first introduction"
        lead["next_action_date"] = lead.get("next_action_date") or days_from_today(1)
        lead["owner"] = lead.get("owner") or owner or "admin"

        organization_id = upsert_organization(cur, lead)
        contact_id = upsert_contact(cur, organization_id, lead)

        if lead_exists(cur, organization_id, contact_id, lead.get("campaign")):
            continue

        cur.execute(
            """
            INSERT INTO leads (
                organization_id,
                contact_id,
                company_name,
                contact_person,
                country,
                city,
                job_title,
                phone,
                email,
                wechat,
                whatsapp,
                membership,
                source,
                campaign,
                lead_status,
                interest_level,
                next_action,
                next_action_date,
                status,
                owner,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                organization_id,
                contact_id,
                lead.get("company_name"),
                lead.get("contact_person"),
                lead.get("country"),
                lead.get("city"),
                lead.get("job_title"),
                lead.get("phone"),
                lead.get("email"),
                lead.get("wechat"),
                lead.get("whatsapp"),
                lead.get("membership"),
                lead.get("source"),
                lead.get("campaign"),
                lead.get("lead_status") or "New",
                lead.get("interest_level"),
                lead.get("next_action"),
                lead.get("next_action_date"),
                lead.get("status") or "New Lead",
                lead.get("owner"),
                lead.get("notes"),
            ),
        )
        lead_id = cur.lastrowid
        log_crm_activity(
            cur,
            "Import",
            f"Lead imported from {lead.get('source') or 'Excel Import'} / {lead.get('campaign') or ''}".strip(),
            lead_id=lead_id,
            organization_id=organization_id,
            contact_id=contact_id,
            user=lead.get("owner") or owner or "admin",
        )
        imported_count += 1

    conn.commit()
    conn.close()
    return imported_count


def get_leads():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            leads.id,
            leads.organization_id,
            leads.contact_id,
            COALESCE(organizations.name, leads.company_name) AS company_name,
            COALESCE(contacts.name, contacts.contact_person, contacts.full_name, leads.contact_person) AS contact_person,
            COALESCE(organizations.country, leads.country) AS country,
            COALESCE(organizations.city, leads.city) AS city,
            COALESCE(contacts.job_title, leads.job_title) AS job_title,
            COALESCE(contacts.email, leads.email) AS email,
            COALESCE(contacts.phone, leads.phone) AS phone,
            COALESCE(contacts.wechat, leads.wechat) AS wechat,
            COALESCE(contacts.whatsapp, leads.whatsapp) AS whatsapp,
            COALESCE(organizations.membership, leads.membership) AS membership,
            COALESCE(leads.lead_status, 'New') AS lead_status,
            COALESCE(leads.priority_score, 0) AS priority_score,
            leads.action_score,
            COALESCE(leads.status, leads.lead_status, 'New') AS status,
            COALESCE(leads.owner, 'admin') AS owner,
            leads.source,
            leads.campaign,
            leads.interest_level,
            leads.next_action,
            leads.next_action_date,
            contacts.last_contacted_at,
            contacts.next_follow_up_at,
            contacts.relationship_status,
            COALESCE(contacts.email_status, 'Unknown') AS email_status,
            organizations.customer_status,
            leads.created_at,
            leads.updated_at
        FROM leads
        LEFT JOIN organizations ON organizations.id = leads.organization_id
        LEFT JOIN contacts ON contacts.id = leads.contact_id
        ORDER BY leads.created_at DESC, leads.id DESC
        """
    ).fetchall()

    conn.close()
    return rows


def get_lead_detail(lead_id):
    conn = get_connection()

    lead = conn.execute(
        """
        SELECT *
        FROM leads
        WHERE id = ?
        """,
        (lead_id,),
    ).fetchone()

    if not lead:
        conn.close()
        return None

    organization = None
    if lead["organization_id"]:
        organization = conn.execute(
            """
            SELECT *
            FROM organizations
            WHERE id = ?
            """,
            (lead["organization_id"],),
        ).fetchone()

    contact = None
    if lead["contact_id"]:
        contact = conn.execute(
            """
            SELECT *
            FROM contacts
            WHERE id = ?
            """,
            (lead["contact_id"],),
        ).fetchone()

    activities = conn.execute(
        """
        SELECT *
        FROM activities
        WHERE lead_id = ?
            OR (contact_id IS NOT NULL AND contact_id = ?)
            OR (organization_id IS NOT NULL AND organization_id = ?)
        ORDER BY COALESCE(activity_at, created_at) DESC, id DESC
        """,
        (
            lead_id,
            lead["contact_id"],
            lead["organization_id"],
        ),
    ).fetchall()

    conn.close()
    return {
        "lead": dict(lead),
        "organization": dict(organization) if organization else None,
        "contact": dict(contact) if contact else None,
        "data_quality": calculate_crm_completeness(
            dict(contact) if contact else {},
            dict(organization) if organization else {},
        ),
        "missing_data": get_missing_data_checklist(
            dict(contact) if contact else {},
            dict(organization) if organization else {},
        ),
        "relationship_health": calculate_relationship_health(
            dict(lead),
            dict(contact) if contact else {},
            dict(organization) if organization else {},
        ),
        "activities": [dict(activity) for activity in activities],
    }


def get_crm_follow_up_rows():
    refresh_lead_priority_scores()
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            leads.id AS lead_id,
            leads.organization_id,
            leads.contact_id,
            COALESCE(contacts.name, contacts.contact_person, contacts.full_name, leads.contact_person, '') AS contact_name,
            COALESCE(contacts.job_title, leads.job_title, '') AS job_title,
            COALESCE(organizations.name, leads.company_name, '') AS organization_name,
            COALESCE(organizations.type, '') AS organization_type,
            COALESCE(organizations.website, '') AS organization_website,
            COALESCE(organizations.country, leads.country, '') AS country,
            COALESCE(organizations.city, leads.city, '') AS city,
            COALESCE(organizations.membership, leads.membership, '') AS membership,
            COALESCE(organizations.customer_status, '') AS customer_status,
            COALESCE(contacts.relationship_status, '') AS relationship_status,
            COALESCE(leads.lead_status, 'New') AS lead_status,
            COALESCE(leads.priority_score, 0) AS priority_score,
            COALESCE(leads.action_score, 0) AS action_score,
            COALESCE(contacts.last_contacted_at, leads.last_contacted_at, '') AS last_contacted_at,
            COALESCE(contacts.next_follow_up_at, '') AS contact_next_follow_up_at,
            COALESCE(leads.next_action, '') AS next_action,
            COALESCE(leads.next_action_date, '') AS next_action_date,
            COALESCE(leads.source, '') AS source,
            COALESCE(leads.campaign, '') AS campaign,
            COALESCE(leads.owner, 'admin') AS owner,
            COALESCE(contacts.email, leads.email, '') AS email,
            COALESCE(contacts.phone, leads.phone, '') AS phone,
            COALESCE(contacts.wechat, leads.wechat, '') AS wechat,
            COALESCE(contacts.whatsapp, leads.whatsapp, '') AS whatsapp,
            EXISTS (
                SELECT 1 FROM opportunities
                WHERE opportunities.contact_id = leads.contact_id
                    AND LOWER(COALESCE(opportunities.status, '')) IN ('new', 'open', 'active')
            ) AS has_open_opportunity,
            EXISTS (
                SELECT 1 FROM opportunities
                WHERE opportunities.contact_id = leads.contact_id
                    AND LOWER(COALESCE(opportunities.status, '')) IN ('quote_requested', 'quote requested')
            ) AS has_quote_requested,
            EXISTS (
                SELECT 1 FROM quotations
                LEFT JOIN opportunities ON opportunities.id = quotations.opportunity_id
                WHERE opportunities.contact_id = leads.contact_id
                    AND LOWER(COALESCE(quotations.status, '')) IN ('draft', 'pricing', 'sent')
            ) AS has_pricing
        FROM leads
        LEFT JOIN organizations ON organizations.id = leads.organization_id
        LEFT JOIN contacts ON contacts.id = leads.contact_id
        """
    ).fetchall()

    conn.close()
    today = date.today()
    queue_rows = []
    for row in rows:
        item = dict(row)
        item["priority_score"] = calculate_priority_score(item)
        item["action_score"] = calculate_action_score(item)
        item["action_score_breakdown"] = get_action_score_breakdown(item)
        item["relationship_health"] = calculate_relationship_health(
            {
                "last_contacted_at": item["last_contacted_at"],
                "next_action_date": item["next_action_date"],
            },
            {
                "relationship_status": item["relationship_status"],
                "last_contacted_at": item["last_contacted_at"],
                "next_follow_up_at": item["contact_next_follow_up_at"],
                "email": item["email"],
                "phone": item["phone"],
                "wechat": item["wechat"],
                "whatsapp": item["whatsapp"],
                "job_title": item["job_title"],
            },
            {
                "customer_status": item["customer_status"],
                "website": item["organization_website"],
                "membership": item["membership"],
                "country": item["country"],
                "city": item["city"],
                "type": item["organization_type"],
            },
        )
        item["recommended_action"] = recommended_action_for_row(item)
        next_date_text = item["next_action_date"] or item["contact_next_follow_up_at"]
        next_date = None
        if next_date_text:
            try:
                next_date = date.fromisoformat(str(next_date_text)[:10])
            except ValueError:
                next_date = None

        last_contact_date = parse_iso_date(item["last_contacted_at"])
        if last_contact_date:
            days_since_contact = (today - last_contact_date).days
            maintenance_overdue_days = max(days_since_contact - 30, 0)
            needs_maintenance = last_contact_date <= today - timedelta(days=30)
        else:
            days_since_contact = None
            maintenance_overdue_days = 9999
            needs_maintenance = True

        scheduled_due = next_date is not None and next_date <= today
        active_relationship_maintenance = (
            item["relationship_status"] in ["Warm", "Active"]
            and needs_maintenance
        )
        customer_maintenance = (
            item["customer_status"] in ["Customer", "Qualified"]
            and needs_maintenance
        )
        new_lead_first_touch = (
            item["lead_status"] == "New"
            and next_date is not None
            and next_date <= today
        )

        if not (
            scheduled_due
            or active_relationship_maintenance
            or customer_maintenance
            or new_lead_first_touch
        ):
            continue

        if next_date and next_date < today:
            due_bucket = "Overdue"
            due_rank = 1
        elif next_date == today:
            due_bucket = "Today"
            due_rank = 2
        elif not next_date:
            due_bucket = "No Follow-up Date"
            due_rank = 6
        elif next_date <= today + timedelta(days=7):
            due_bucket = "This Week"
            due_rank = 3
        else:
            due_bucket = "Future"
            due_rank = 7

        if customer_maintenance:
            action_reason = "Customer Maintenance"
        elif active_relationship_maintenance:
            action_reason = "Active Relationship Maintenance"
        elif new_lead_first_touch:
            action_reason = "New Lead First Touch"
        elif next_date and next_date < today:
            action_reason = "Overdue"
        else:
            action_reason = "Due Today"

        if scheduled_due and next_date:
            overdue_days = max((today - next_date).days, 0)
        elif active_relationship_maintenance or customer_maintenance:
            overdue_days = maintenance_overdue_days
        else:
            overdue_days = 0

        status_rank = 6
        if item["relationship_status"] in ["Warm", "Active"]:
            status_rank = 3
        if item["lead_status"] == "Qualified":
            status_rank = min(status_rank, 4)
        if item["lead_status"] == "New":
            status_rank = min(status_rank, 5)

        overdue_rank = 0 if due_bucket == "Overdue" else 1
        item["due_bucket"] = due_bucket
        item["action_reason"] = action_reason
        item["overdue_days"] = overdue_days
        item["sort_rank"] = (
            -item["action_score"],
            -item["overdue_days"],
            next_date or date.max,
            overdue_rank,
            status_rank,
        )
        queue_rows.append(item)

    return sorted(queue_rows, key=lambda item: item["sort_rank"])


def initialize_missing_lead_followups(user="admin"):
    conn = get_connection()
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT
            leads.id,
            leads.organization_id,
            leads.contact_id,
            COALESCE(leads.lead_status, 'New') AS lead_status,
            COALESCE(contacts.relationship_status, '') AS relationship_status
        FROM leads
        LEFT JOIN contacts ON contacts.id = leads.contact_id
        WHERE COALESCE(leads.lead_status, 'New') <> 'Disqualified'
            AND (
                leads.next_action_date IS NULL
                OR TRIM(leads.next_action_date) = ''
                OR leads.next_action IS NULL
                OR TRIM(leads.next_action) = ''
            )
        ORDER BY leads.created_at, leads.id
        """
    ).fetchall()

    updated = 0
    scheduled_counts = {}
    capacity = get_daily_outreach_capacity()
    for index, lead in enumerate(rows):
        days_ahead = 0 if index < capacity else ((index - capacity) % 30) + 1
        next_date = days_from_today(days_ahead)
        next_action = next_action_for_state(lead["lead_status"], lead["relationship_status"])
        cur.execute(
            """
            UPDATE leads
            SET next_action = ?,
                next_action_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (next_action, next_date, lead["id"]),
        )
        if lead["contact_id"]:
            cur.execute(
                """
                UPDATE contacts
                SET next_follow_up_at = COALESCE(NULLIF(next_follow_up_at, ''), ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (next_date, lead["contact_id"]),
            )
        log_crm_activity(
            cur,
            "Follow-up",
            f"Follow-up initialized: {next_action} on {next_date}",
            lead_id=lead["id"],
            organization_id=lead["organization_id"],
            contact_id=lead["contact_id"],
            user=user,
        )
        updated += 1
        scheduled_counts[next_date] = scheduled_counts.get(next_date, 0) + 1

    conn.commit()
    conn.close()
    return {
        "updated": updated,
        "start_date": days_from_today(1) if updated else "",
        "end_date": days_from_today(30) if updated else "",
        "scheduled_counts": scheduled_counts,
    }


def get_crm_dashboard_data():
    refresh_lead_priority_scores()
    conn = get_connection()
    today = today_iso()
    week_end = days_from_today(7)
    month_end = days_from_today(30)
    capacity = get_daily_outreach_capacity()

    kpis = conn.execute(
        """
        SELECT
            SUM(CASE WHEN leads.next_action_date = ? OR contacts.next_follow_up_at = ? THEN 1 ELSE 0 END) AS due_today,
            SUM(CASE WHEN (leads.next_action_date <> '' AND leads.next_action_date < ?)
                      OR (contacts.next_follow_up_at <> '' AND contacts.next_follow_up_at < ?) THEN 1 ELSE 0 END) AS overdue,
            SUM(CASE WHEN COALESCE(leads.lead_status, 'New') = 'New' THEN 1 ELSE 0 END) AS new_leads,
            SUM(CASE WHEN contacts.relationship_status IN ('Warm', 'Active') THEN 1 ELSE 0 END) AS warm_relationships,
            SUM(CASE WHEN leads.lead_status = 'Qualified' THEN 1 ELSE 0 END) AS qualified_leads,
            COUNT(DISTINCT CASE WHEN organizations.customer_status = 'Customer' THEN organizations.id END) AS customers,
            COUNT(DISTINCT CASE WHEN COALESCE(leads.priority_score, 0) >= 70 THEN contacts.id END) AS high_priority_contacts,
            SUM(CASE WHEN LOWER(TRIM(COALESCE(organizations.country, leads.country, ''))) = 'china' THEN 1 ELSE 0 END) AS china_leads,
            COUNT(DISTINCT CASE WHEN LOWER(TRIM(COALESCE(organizations.country, leads.country, ''))) = 'china'
                      AND contacts.relationship_status IN ('Warm', 'Active') THEN contacts.id END) AS china_warm_relationships,
            SUM(CASE WHEN COALESCE(leads.next_action_date, '') = ''
                      AND COALESCE(contacts.next_follow_up_at, '') = '' THEN 1 ELSE 0 END) AS no_followup
        FROM leads
        LEFT JOIN contacts ON contacts.id = leads.contact_id
        LEFT JOIN organizations ON organizations.id = leads.organization_id
        """,
        (today, today, today, today),
    ).fetchone()

    outreach = conn.execute(
        """
        SELECT
            SUM(CASE WHEN leads.next_action_date = ? THEN 1 ELSE 0 END) AS today_count,
            SUM(CASE WHEN leads.next_action_date >= ? AND leads.next_action_date <= ? THEN 1 ELSE 0 END) AS week_count,
            SUM(CASE WHEN leads.next_action_date >= ? AND leads.next_action_date <= ? THEN 1 ELSE 0 END) AS month_count
        FROM leads
        WHERE COALESCE(leads.lead_status, 'New') <> 'Disqualified'
            AND COALESCE(leads.next_action_date, '') <> ''
        """,
        (today, today, week_end, today, month_end),
    ).fetchone()

    campaign_progress = conn.execute(
        """
        SELECT
            COALESCE(NULLIF(campaign, ''), NULLIF(source, ''), 'Unknown') AS campaign,
            COUNT(*) AS total_leads,
            SUM(CASE WHEN lead_status = 'Contacted' THEN 1 ELSE 0 END) AS contacted,
            SUM(CASE WHEN lead_status = 'Replied' THEN 1 ELSE 0 END) AS replied,
            SUM(CASE WHEN lead_status = 'Qualified' THEN 1 ELSE 0 END) AS qualified,
            SUM(CASE WHEN lead_status = 'Converted' THEN 1 ELSE 0 END) AS converted,
            SUM(CASE WHEN lead_status = 'Disqualified' THEN 1 ELSE 0 END) AS disqualified
        FROM leads
        GROUP BY COALESCE(NULLIF(campaign, ''), NULLIF(source, ''), 'Unknown')
        ORDER BY total_leads DESC
        """
    ).fetchall()

    country_pipeline = conn.execute(
        """
        SELECT
            COALESCE(NULLIF(organizations.country, ''), NULLIF(leads.country, ''), 'Unknown') AS country,
            COUNT(leads.id) AS leads,
            COUNT(DISTINCT contacts.id) AS contacts,
            COUNT(DISTINCT CASE WHEN contacts.relationship_status IN ('Warm', 'Active') THEN contacts.id END) AS warm,
            COUNT(DISTINCT CASE WHEN organizations.customer_status = 'Customer' THEN organizations.id END) AS customers
        FROM leads
        LEFT JOIN contacts ON contacts.id = leads.contact_id
        LEFT JOIN organizations ON organizations.id = leads.organization_id
        GROUP BY COALESCE(NULLIF(organizations.country, ''), NULLIF(leads.country, ''), 'Unknown')
        ORDER BY leads DESC
        """
    ).fetchall()

    relationship_counts = {
        "New": 0,
        "Connected": 0,
        "Introduced": 0,
        "Warm": 0,
        "Active": 0,
        "Customer": 0,
    }
    relationship_rows = conn.execute(
        """
        SELECT COALESCE(NULLIF(relationship_status, ''), 'New') AS stage,
            COUNT(DISTINCT id) AS count
        FROM contacts
        GROUP BY COALESCE(NULLIF(relationship_status, ''), 'New')
        """
    ).fetchall()
    for row in relationship_rows:
        stage = row["stage"] if row["stage"] in relationship_counts else "New"
        relationship_counts[stage] += row["count"]
    relationship_counts["Customer"] = conn.execute(
        """
        SELECT COUNT(DISTINCT id) AS count
        FROM organizations
        WHERE customer_status = 'Customer'
        """
    ).fetchone()["count"]

    funnel_order = ["New", "Connected", "Introduced", "Warm", "Active", "Customer"]
    relationship_funnel = []
    previous_count = None
    for stage in funnel_order:
        count = relationship_counts.get(stage, 0)
        conversion_rate = None
        if previous_count is not None:
            conversion_rate = round((count / previous_count) * 100, 1) if previous_count else 0
        relationship_funnel.append(
            {
                "stage": stage,
                "count": count,
                "conversion_rate": conversion_rate,
            }
        )
        previous_count = count

    quality_rows = conn.execute(
        """
        SELECT
            COALESCE(contacts.email, leads.email, '') AS email,
            COALESCE(contacts.phone, leads.phone, '') AS phone,
            COALESCE(contacts.wechat, leads.wechat, '') AS wechat,
            COALESCE(contacts.whatsapp, leads.whatsapp, '') AS whatsapp,
            COALESCE(contacts.job_title, leads.job_title, '') AS job_title,
            COALESCE(organizations.website, '') AS website,
            COALESCE(organizations.membership, leads.membership, '') AS membership,
            COALESCE(organizations.country, leads.country, '') AS country,
            COALESCE(organizations.city, leads.city, '') AS city,
            COALESCE(organizations.type, '') AS type
        FROM leads
        LEFT JOIN contacts ON contacts.id = leads.contact_id
        LEFT JOIN organizations ON organizations.id = leads.organization_id
        """
    ).fetchall()
    quality_scores = [
        round(
            (
                calculate_contact_completeness(row)
                + calculate_organization_completeness(row)
            )
            / 2
        )
        for row in quality_rows
    ]

    china_cities = ["Shenzhen", "Shanghai", "Ningbo", "Qingdao", "Xiamen", "Tianjin"]
    china_network = []
    for city in china_cities:
        row = conn.execute(
            """
            SELECT
                COUNT(DISTINCT contacts.id) AS contacts,
                COUNT(DISTINCT CASE WHEN contacts.relationship_status = 'Warm' THEN contacts.id END) AS warm,
                COUNT(DISTINCT CASE WHEN contacts.relationship_status = 'Active' THEN contacts.id END) AS active,
                COUNT(DISTINCT CASE WHEN organizations.customer_status = 'Customer' THEN organizations.id END) AS customers
            FROM organizations
            LEFT JOIN contacts ON contacts.organization_id = organizations.id
            WHERE LOWER(TRIM(organizations.country)) = 'china'
                AND LOWER(TRIM(organizations.city)) = LOWER(TRIM(?))
            """,
            (city,),
        ).fetchone()
        china_network.append(
            {
                "city": city,
                "contacts": row["contacts"] or 0,
                "warm": row["warm"] or 0,
                "active": row["active"] or 0,
                "customers": row["customers"] or 0,
            }
        )

    conn.close()
    queue_rows = get_crm_follow_up_rows()
    today_actions = [row for row in queue_rows if row.get("action_reason")][:capacity]
    return {
        "kpis": dict(kpis),
        "daily_outreach_capacity": capacity,
        "outreach_queue": {
            "today": min(int(row_value(outreach, "today_count", 0) or 0), capacity),
            "this_week": min(int(row_value(outreach, "week_count", 0) or 0), capacity * 7),
            "next_30_days": int(row_value(outreach, "month_count", 0) or 0),
        },
        "today_action_list": today_actions,
        "relationship_funnel": relationship_funnel,
        "data_quality": {
            "average_score": round(sum(quality_scores) / len(quality_scores)) if quality_scores else 0,
            "record_count": len(quality_scores),
        },
        "china_network": china_network,
        "today_followups": [row for row in queue_rows if row["due_bucket"] == "Today"][:10],
        "overdue_followups": [row for row in queue_rows if row["due_bucket"] == "Overdue"][:10],
        "warm_relationships": [
            row for row in queue_rows
            if row["relationship_status"] in ["Warm", "Active"]
        ][:10],
        "new_leads_first_touch": [
            row for row in queue_rows
            if row["lead_status"] == "New" and not row["last_contacted_at"]
        ][:10],
        "campaign_progress": [dict(row) for row in campaign_progress],
        "country_pipeline": [dict(row) for row in country_pipeline],
    }


def get_opportunity_dashboard_data():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            id,
            COALESCE(NULLIF(stage, ''), status, 'Interested') AS raw_stage,
            COALESCE(potential_revenue, 0) AS potential_revenue,
            COALESCE(potential_profit, 0) AS potential_profit
        FROM opportunities
        """
    ).fetchall()
    conn.close()

    stage_counts = {stage: 0 for stage in OPPORTUNITY_STAGES}
    total_pipeline_value = 0.0
    negotiation_value = 0.0
    won_value = 0.0

    for row in rows:
        stage = normalize_opportunity_stage(row["raw_stage"])
        value = float(row["potential_revenue"] or 0)
        stage_counts[stage] += 1
        if stage != "Lost":
            total_pipeline_value += value
        if stage == "Negotiation":
            negotiation_value += value
        if stage == "Won":
            won_value += value

    return {
        "total_opportunities": len(rows),
        "stage_counts": stage_counts,
        "total_pipeline_value": total_pipeline_value,
        "negotiation_value": negotiation_value,
        "won_value": won_value,
    }


def get_opportunities():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            opportunities.*,
            COALESCE(opportunities.opportunity_name, opportunities.title) AS display_name,
            COALESCE(NULLIF(opportunities.stage, ''), opportunities.status, 'Interested') AS raw_stage,
            organizations.name AS organization_name,
            organizations.country,
            organizations.city,
            contacts.name AS contact_name
        FROM opportunities
        LEFT JOIN organizations ON organizations.id = opportunities.organization_id
        LEFT JOIN contacts ON contacts.id = opportunities.contact_id
        ORDER BY opportunities.updated_at DESC, opportunities.id DESC
        """
    ).fetchall()
    conn.close()

    opportunities = []
    for row in rows:
        item = dict(row)
        item["stage"] = normalize_opportunity_stage(item.get("raw_stage"))
        opportunities.append(item)

    stage_rank = {
        "Interested": 1,
        "Quote Requested": 2,
        "Quoted": 3,
        "Negotiation": 4,
        "Won": 5,
        "Lost": 6,
    }
    return sorted(
        opportunities,
        key=lambda item: (
            stage_rank.get(item["stage"], 9),
            item.get("next_action_date") or item.get("expected_close_date") or "9999-12-31",
            -int(item["id"]),
        ),
    )


def get_test_opportunity_candidates():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            opportunities.id,
            COALESCE(opportunities.opportunity_name, opportunities.title) AS opportunity_name,
            COALESCE(opportunities.stage, 'Interested') AS stage,
            COALESCE(opportunities.potential_revenue, 0) AS potential_revenue,
            opportunities.organization_id,
            opportunities.contact_id,
            opportunities.created_at,
            opportunities.updated_at
        FROM opportunities
        WHERE COALESCE(opportunities.potential_revenue, 0) = 0
            AND COALESCE(opportunities.stage, 'Interested') = 'Interested'
            AND opportunities.organization_id IS NULL
            AND opportunities.contact_id IS NULL
            AND (
                LOWER(COALESCE(opportunities.opportunity_name, opportunities.title, '')) LIKE '%need rate%'
                OR LOWER(COALESCE(opportunities.opportunity_name, opportunities.title, '')) LIKE '%nhờ%'
                OR LOWER(COALESCE(opportunities.opportunity_name, opportunities.title, '')) LIKE '%test%'
            )
        ORDER BY opportunities.created_at DESC, opportunities.id DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_test_opportunities(opportunity_ids):
    ids = [int(item) for item in opportunity_ids or []]
    if not ids:
        return 0

    placeholders = ",".join("?" for _ in ids)
    conn = get_connection()
    cur = conn.cursor()
    candidates = cur.execute(
        f"""
        SELECT id
        FROM opportunities
        WHERE id IN ({placeholders})
            AND COALESCE(potential_revenue, 0) = 0
            AND COALESCE(stage, 'Interested') = 'Interested'
            AND organization_id IS NULL
            AND contact_id IS NULL
            AND (
                LOWER(COALESCE(opportunity_name, title, '')) LIKE '%need rate%'
                OR LOWER(COALESCE(opportunity_name, title, '')) LIKE '%nhờ%'
                OR LOWER(COALESCE(opportunity_name, title, '')) LIKE '%test%'
            )
        """,
        ids,
    ).fetchall()
    safe_ids = [row["id"] for row in candidates]
    if not safe_ids:
        conn.close()
        return 0

    safe_placeholders = ",".join("?" for _ in safe_ids)
    cur.execute(f"DELETE FROM tasks WHERE opportunity_id IN ({safe_placeholders})", safe_ids)
    cur.execute(f"DELETE FROM activities WHERE opportunity_id IN ({safe_placeholders})", safe_ids)
    cur.execute(f"DELETE FROM vendor_rates WHERE opportunity_id IN ({safe_placeholders})", safe_ids)
    cur.execute(f"DELETE FROM opportunities WHERE id IN ({safe_placeholders})", safe_ids)
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def get_opportunity_detail(opportunity_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT
            opportunities.*,
            COALESCE(opportunities.opportunity_name, opportunities.title) AS display_name,
            COALESCE(NULLIF(opportunities.stage, ''), opportunities.status, 'Interested') AS raw_stage,
            organizations.name AS organization_name,
            organizations.country,
            organizations.city,
            contacts.name AS contact_name,
            contacts.email,
            contacts.phone,
            contacts.wechat,
            contacts.whatsapp
        FROM opportunities
        LEFT JOIN organizations ON organizations.id = opportunities.organization_id
        LEFT JOIN contacts ON contacts.id = opportunities.contact_id
        WHERE opportunities.id = ?
        """,
        (opportunity_id,),
    ).fetchone()

    activities = conn.execute(
        """
        SELECT *
        FROM activities
        WHERE opportunity_id = ?
        ORDER BY COALESCE(activity_at, created_at) DESC, id DESC
        """,
        (opportunity_id,),
    ).fetchall()
    conn.close()

    if not row:
        return None
    item = dict(row)
    item["stage"] = normalize_opportunity_stage(item.get("raw_stage"))
    item["activities"] = [dict(activity) for activity in activities]
    return item


def save_opportunity(record, opportunity_id=None, user="admin"):
    if not opportunity_id:
        return create_opportunity(record, user=user)["opportunity_id"]

    conn = get_connection()
    cur = conn.cursor()
    stage = normalize_opportunity_stage(record.get("stage"))
    status = opportunity_status_from_stage(stage)
    opportunity_name = clean_value(record.get("opportunity_name")) or "New Opportunity"

    if opportunity_id:
        existing = cur.execute(
            "SELECT * FROM opportunities WHERE id = ?",
            (opportunity_id,),
        ).fetchone()
        if not existing:
            conn.close()
            return None
        cur.execute(
            """
            UPDATE opportunities
            SET opportunity_name = ?,
                title = ?,
                organization_id = ?,
                contact_id = ?,
                owner = ?,
                stage = ?,
                status = ?,
                trade_lane = ?,
                service_type = ?,
                route = ?,
                commodity = ?,
                volume = ?,
                cargo_description = ?,
                origin = ?,
                destination = ?,
                weight = ?,
                container_type = ?,
                quantity = ?,
                incoterm = ?,
                quotation_status = ?,
                mode = ?,
                potential_revenue = ?,
                potential_profit = ?,
                expected_close_date = ?,
                next_action = ?,
                next_action_date = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                opportunity_name,
                opportunity_name,
                record.get("organization_id"),
                record.get("contact_id"),
                record.get("owner"),
                stage,
                status,
                record.get("trade_lane"),
                record.get("service_type"),
                record.get("trade_lane") or build_route(record.get("origin"), record.get("destination")),
                record.get("commodity") or record.get("cargo_description"),
                record.get("volume"),
                record.get("cargo_description") or record.get("commodity"),
                record.get("origin"),
                record.get("destination"),
                record.get("weight"),
                record.get("container_type"),
                record.get("quantity"),
                record.get("incoterm"),
                record.get("quotation_status") or "Not Started",
                record.get("mode"),
                parse_money(record.get("potential_revenue")),
                parse_money(record.get("potential_profit")),
                record.get("expected_close_date"),
                record.get("next_action"),
                record.get("next_action_date"),
                record.get("notes"),
                opportunity_id,
            ),
        )
        saved_id = opportunity_id
        description = f"Opportunity updated: {opportunity_name}"

    log_crm_activity(
        cur,
        "Opportunity Update",
        description,
        opportunity_id=saved_id,
        organization_id=record.get("organization_id"),
        contact_id=record.get("contact_id"),
        user=user,
    )

    conn.commit()
    conn.close()
    return saved_id


def update_opportunity_stage(opportunity_id, stage, user="admin"):
    conn = get_connection()
    cur = conn.cursor()
    opportunity = cur.execute(
        "SELECT organization_id, contact_id FROM opportunities WHERE id = ?",
        (opportunity_id,),
    ).fetchone()
    if not opportunity:
        conn.close()
        return False

    normalized_stage = normalize_opportunity_stage(stage)
    cur.execute(
        """
        UPDATE opportunities
        SET stage = ?,
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (normalized_stage, opportunity_status_from_stage(normalized_stage), opportunity_id),
    )
    log_crm_activity(
        cur,
        "Opportunity Update",
        f"Opportunity stage changed to {normalized_stage}",
        opportunity_id=opportunity_id,
        organization_id=opportunity["organization_id"],
        contact_id=opportunity["contact_id"],
        user=user,
    )
    if normalized_stage == "Won" and opportunity["organization_id"]:
        cur.execute(
            """
            UPDATE organizations
            SET customer_status = 'Customer',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (opportunity["organization_id"],),
        )
    conn.commit()
    conn.close()
    return True


def get_vendor_rates(opportunity_id=None):
    conn = get_connection()
    params = []
    where_clause = ""
    if opportunity_id:
        where_clause = "WHERE vendor_rates.opportunity_id = ?"
        params.append(opportunity_id)

    rows = conn.execute(
        f"""
        SELECT
            vendor_rates.*,
            COALESCE(opportunities.opportunity_name, opportunities.title) AS opportunity_name
        FROM vendor_rates
        LEFT JOIN opportunities ON opportunities.id = vendor_rates.opportunity_id
        {where_clause}
        ORDER BY vendor_rates.updated_at DESC, vendor_rates.id DESC
        """,
        params,
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_vendor_rate(record, rate_id=None, user="admin"):
    clean_record = {key: clean_value(value) for key, value in (record or {}).items()}
    opportunity_id = clean_record.get("opportunity_id")
    if not opportunity_id:
        return None

    cost_amount = parse_money(clean_record.get("cost_amount"))
    margin_percent = parse_money(clean_record.get("margin_percent"))
    fixed_margin = parse_money(clean_record.get("margin_amount"))
    calculated = calculate_suggested_sell_rate(cost_amount, margin_percent, fixed_margin)
    vendor_type = clean_record.get("vendor_type") or "Carrier"
    charge_name = clean_record.get("charge_name") or "Freight"

    conn = get_connection()
    cur = conn.cursor()
    opportunity = cur.execute(
        """
        SELECT organization_id, contact_id
        FROM opportunities
        WHERE id = ?
        """,
        (opportunity_id,),
    ).fetchone()
    if not opportunity:
        conn.close()
        return None

    values = (
        opportunity_id,
        clean_record.get("quotation_id") or None,
        vendor_type,
        clean_record.get("vendor_name"),
        clean_record.get("charge_type") or vendor_type,
        charge_name,
        clean_record.get("basis"),
        clean_record.get("currency") or "USD",
        calculated["cost_amount"],
        margin_percent,
        fixed_margin,
        calculated["suggested_sell_amount"],
        clean_record.get("transit_time"),
        clean_record.get("valid_until"),
        clean_record.get("notes"),
    )

    if rate_id:
        cur.execute(
            """
            UPDATE vendor_rates
            SET opportunity_id = ?,
                quotation_id = ?,
                vendor_type = ?,
                vendor_name = ?,
                charge_type = ?,
                charge_name = ?,
                basis = ?,
                currency = ?,
                cost_amount = ?,
                margin_percent = ?,
                margin_amount = ?,
                suggested_sell_amount = ?,
                transit_time = ?,
                valid_until = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values + (rate_id,),
        )
        saved_id = rate_id
        action = "updated"
    else:
        cur.execute(
            """
            INSERT INTO vendor_rates (
                opportunity_id,
                quotation_id,
                vendor_type,
                vendor_name,
                charge_type,
                charge_name,
                basis,
                currency,
                cost_amount,
                margin_percent,
                margin_amount,
                suggested_sell_amount,
                transit_time,
                valid_until,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            values,
        )
        saved_id = cur.lastrowid
        action = "added"

    log_crm_activity(
        cur,
        "Pricing Update",
        f"Pricing line {action}: {vendor_type} - {charge_name}",
        opportunity_id=opportunity_id,
        organization_id=opportunity["organization_id"],
        contact_id=opportunity["contact_id"],
        user=user,
    )
    conn.commit()
    conn.close()
    return saved_id


def get_pricing_summary(opportunity_id):
    rates = get_vendor_rates(opportunity_id)
    totals = {}
    local_totals = {}
    for rate in rates:
        currency = rate.get("currency") or "USD"
        vendor_type = rate.get("vendor_type") or "Unknown"
        vendor_name = rate.get("vendor_name") or vendor_type
        if vendor_type == "Local Charge":
            vendor_name = "Local Charges"
        key = (currency, vendor_type, vendor_name)
        if key not in totals:
            totals[key] = {
                "currency": currency,
                "vendor_type": vendor_type,
                "vendor_name": vendor_name,
                "line_count": 0,
                "cost_total": 0.0,
                "margin_total": 0.0,
                "suggested_sell_total": 0.0,
                "transit_times": [],
                "valid_until": "",
            }
        cost = float(rate.get("cost_amount") or 0)
        suggested = float(rate.get("suggested_sell_amount") or 0)
        totals[key]["line_count"] += 1
        totals[key]["cost_total"] += cost
        totals[key]["suggested_sell_total"] += suggested
        totals[key]["margin_total"] += suggested - cost
        if rate.get("transit_time"):
            totals[key]["transit_times"].append(rate["transit_time"])
        if rate.get("valid_until"):
            current_valid_until = totals[key]["valid_until"]
            if not current_valid_until or rate["valid_until"] < current_valid_until:
                totals[key]["valid_until"] = rate["valid_until"]
        if vendor_type == "Local Charge":
            if currency not in local_totals:
                local_totals[currency] = {
                    "line_count": 0,
                    "cost_total": 0.0,
                    "margin_total": 0.0,
                    "suggested_sell_total": 0.0,
                }
            local_totals[currency]["line_count"] += 1
            local_totals[currency]["cost_total"] += cost
            local_totals[currency]["margin_total"] += suggested - cost
            local_totals[currency]["suggested_sell_total"] += suggested

    comparisons = []
    has_vendor_options = any(item["vendor_type"] != "Local Charge" for item in totals.values())
    for item in totals.values():
        if item["vendor_type"] == "Local Charge" and has_vendor_options:
            continue
        local = local_totals.get(item["currency"])
        if item["vendor_type"] != "Local Charge" and local:
            item["line_count"] += local["line_count"]
            item["cost_total"] += local["cost_total"]
            item["margin_total"] += local["margin_total"]
            item["suggested_sell_total"] += local["suggested_sell_total"]
        item["cost_total"] = round(item["cost_total"], 2)
        item["margin_total"] = round(item["margin_total"], 2)
        item["suggested_sell_total"] = round(item["suggested_sell_total"], 2)
        item["margin_percent"] = round((item["margin_total"] / item["cost_total"]) * 100, 2) if item["cost_total"] else 0
        item["transit_time"] = ", ".join(dict.fromkeys(item["transit_times"]))
        del item["transit_times"]
        comparisons.append(item)

    comparisons = sorted(
        comparisons,
        key=lambda item: (
            item["currency"],
            item["suggested_sell_total"],
            item["vendor_type"],
            item["vendor_name"],
        ),
    )
    best_by_currency = {}
    for item in comparisons:
        best_by_currency.setdefault(item["currency"], item)

    return {
        "rates": rates,
        "comparisons": comparisons,
        "best_by_currency": best_by_currency,
    }


def apply_pricing_summary_to_opportunity(opportunity_id, currency="USD", user="admin"):
    summary = get_pricing_summary(opportunity_id)
    best = summary["best_by_currency"].get(currency)
    if not best:
        return False

    conn = get_connection()
    cur = conn.cursor()
    opportunity = cur.execute(
        """
        SELECT organization_id, contact_id
        FROM opportunities
        WHERE id = ?
        """,
        (opportunity_id,),
    ).fetchone()
    if not opportunity:
        conn.close()
        return False

    cur.execute(
        """
        UPDATE opportunities
        SET potential_revenue = ?,
            potential_profit = ?,
            next_action = COALESCE(NULLIF(next_action, ''), 'Prepare quotation'),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            best["suggested_sell_total"],
            best["margin_total"],
            opportunity_id,
        ),
    )
    log_crm_activity(
        cur,
        "Pricing Update",
        (
            "Applied suggested sell rate to opportunity: "
            f"{currency} {best['suggested_sell_total']:,.2f} "
            f"with margin {best['margin_total']:,.2f}"
        ),
        opportunity_id=opportunity_id,
        organization_id=opportunity["organization_id"],
        contact_id=opportunity["contact_id"],
        user=user,
    )
    conn.commit()
    conn.close()
    return True


def get_quotation_templates():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM quotation_templates
        ORDER BY template_name
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_quotation_template(template_name, header_text="", footer_text="", payment_terms="", validity_days=14):
    clean_name = clean_value(template_name)
    if not clean_name:
        return None
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO quotation_templates (
            template_name,
            header_text,
            footer_text,
            payment_terms,
            validity_days,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(template_name) DO UPDATE SET
            header_text = excluded.header_text,
            footer_text = excluded.footer_text,
            payment_terms = excluded.payment_terms,
            validity_days = excluded.validity_days,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            clean_name,
            clean_value(header_text),
            clean_value(footer_text),
            clean_value(payment_terms),
            int(parse_money(validity_days) or 14),
        ),
    )
    conn.commit()
    conn.close()
    return clean_name


def generate_quote_no(cur):
    quote_no_prefix = date.today().strftime("%y%m")
    latest_quote = cur.execute(
        """
        SELECT quote_no
        FROM quotations
        WHERE quote_no LIKE ?
        ORDER BY quote_no DESC
        LIMIT 1
        """,
        (quote_no_prefix + "%",),
    ).fetchone()
    if latest_quote and latest_quote["quote_no"]:
        try:
            next_quote_number = int(latest_quote["quote_no"][4:]) + 1
        except ValueError:
            next_quote_number = 1
    else:
        next_quote_number = 1
    return quote_no_prefix + f"{next_quote_number:02d}"


def quote_status_label(status):
    value = normalize(status)
    return {
        "draft": "Draft",
        "pending approval": "Pending Approval",
        "pending_approval": "Pending Approval",
        "approved": "Approved",
        "sent": "Sent",
        "rejected": "Rejected",
    }.get(value, "Draft")


def calculate_quotation_totals(items):
    total = 0.0
    cost_total = 0.0
    for item in items or []:
        quantity = parse_money(item.get("quantity") or 1) or 1
        unit_price = parse_money(item.get("unit_price"))
        amount = parse_money(item.get("amount"))
        if not amount:
            amount = quantity * unit_price
        total += amount
        cost_total += parse_money(item.get("cost_amount"))
    return {
        "sell_amount": round(total, 2),
        "cost_amount": round(cost_total, 2),
        "margin_amount": round(total - cost_total, 2),
    }


def get_quotations():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            quotations.*,
            COALESCE(opportunities.opportunity_name, opportunities.title) AS opportunity_name,
            organizations.name AS organization_name,
            contacts.name AS crm_contact_name
        FROM quotations
        LEFT JOIN opportunities ON opportunities.id = quotations.opportunity_id
        LEFT JOIN organizations ON organizations.id = opportunities.organization_id
        LEFT JOIN contacts ON contacts.id = opportunities.contact_id
        ORDER BY quotations.updated_at DESC, quotations.id DESC
        """
    ).fetchall()
    conn.close()
    quotations = []
    for row in rows:
        item = dict(row)
        item["status"] = quote_status_label(item.get("status"))
        item["customer_name"] = item.get("customer_name") or item.get("organization_name") or ""
        item["contact_name"] = item.get("contact_name") or item.get("crm_contact_name") or ""
        quotations.append(item)
    return quotations


def get_quotation_detail(quotation_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT
            quotations.*,
            quotation_templates.header_text,
            quotation_templates.footer_text,
            COALESCE(opportunities.opportunity_name, opportunities.title) AS opportunity_name,
            opportunities.organization_id,
            opportunities.contact_id,
            organizations.name AS organization_name,
            contacts.name AS crm_contact_name,
            contacts.email AS contact_email
        FROM quotations
        LEFT JOIN quotation_templates ON quotation_templates.template_name = quotations.template_name
        LEFT JOIN opportunities ON opportunities.id = quotations.opportunity_id
        LEFT JOIN organizations ON organizations.id = opportunities.organization_id
        LEFT JOIN contacts ON contacts.id = opportunities.contact_id
        WHERE quotations.id = ?
        """,
        (quotation_id,),
    ).fetchone()
    if not row:
        conn.close()
        return None
    items = conn.execute(
        """
        SELECT *
        FROM quotation_items
        WHERE quotation_id = ?
        ORDER BY line_no, id
        """,
        (quotation_id,),
    ).fetchall()
    activities = conn.execute(
        """
        SELECT *
        FROM activities
        WHERE quotation_id = ?
        ORDER BY COALESCE(activity_at, created_at) DESC, id DESC
        """,
        (quotation_id,),
    ).fetchall()
    conn.close()
    detail = dict(row)
    detail["status"] = quote_status_label(detail.get("status"))
    detail["customer_name"] = detail.get("customer_name") or detail.get("organization_name") or ""
    detail["contact_name"] = detail.get("contact_name") or detail.get("crm_contact_name") or ""
    detail["items"] = [dict(item) for item in items]
    detail["activities"] = [dict(activity) for activity in activities]
    detail["totals"] = calculate_quotation_totals(detail["items"])
    return detail


def replace_quotation_items(cur, quotation_id, items):
    cur.execute("DELETE FROM quotation_items WHERE quotation_id = ?", (quotation_id,))
    cleaned_items = []
    for index, item in enumerate(items or [], start=1):
        description = clean_value(item.get("description"))
        if not description:
            continue
        quantity = parse_money(item.get("quantity") or 1) or 1
        unit_price = parse_money(item.get("unit_price"))
        amount = parse_money(item.get("amount")) or round(quantity * unit_price, 2)
        cost_amount = parse_money(item.get("cost_amount"))
        margin_amount = amount - cost_amount
        currency = clean_value(item.get("currency")) or "USD"
        cleaned = {
            "line_no": index,
            "description": description,
            "basis": clean_value(item.get("basis")),
            "quantity": quantity,
            "unit_price": unit_price,
            "currency": currency,
            "amount": round(amount, 2),
            "cost_amount": cost_amount,
            "margin_amount": round(margin_amount, 2),
            "vendor_name": clean_value(item.get("vendor_name")),
            "notes": clean_value(item.get("notes")),
        }
        cur.execute(
            """
            INSERT INTO quotation_items (
                quotation_id,
                line_no,
                description,
                basis,
                quantity,
                unit_price,
                currency,
                amount,
                cost_amount,
                margin_amount,
                vendor_name,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                quotation_id,
                cleaned["line_no"],
                cleaned["description"],
                cleaned["basis"],
                cleaned["quantity"],
                cleaned["unit_price"],
                cleaned["currency"],
                cleaned["amount"],
                cleaned["cost_amount"],
                cleaned["margin_amount"],
                cleaned["vendor_name"],
                cleaned["notes"],
            ),
        )
        cleaned_items.append(cleaned)
    return cleaned_items


def save_quotation(record, items=None, quotation_id=None, user="admin"):
    clean_record = {key: clean_value(value) for key, value in (record or {}).items()}
    conn = get_connection()
    cur = conn.cursor()
    admin_user = cur.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
    admin_user_id = admin_user["id"] if admin_user else None
    opportunity = None
    opportunity_id = clean_record.get("opportunity_id") or None
    if opportunity_id:
        opportunity = cur.execute(
            """
            SELECT
                opportunities.*,
                organizations.name AS organization_name,
                contacts.name AS contact_name
            FROM opportunities
            LEFT JOIN organizations ON organizations.id = opportunities.organization_id
            LEFT JOIN contacts ON contacts.id = opportunities.contact_id
            WHERE opportunities.id = ?
            """,
            (opportunity_id,),
        ).fetchone()

    quote_items = items if items is not None else []
    totals = calculate_quotation_totals(quote_items)
    status = quote_status_label(clean_record.get("status"))
    currency = clean_record.get("currency") or (
        quote_items[0].get("currency") if quote_items else "USD"
    )
    customer_name = clean_record.get("customer_name") or row_value(opportunity, "organization_name")
    contact_name = clean_record.get("contact_name") or row_value(opportunity, "contact_name")
    trade_lane = clean_record.get("trade_lane") or row_value(opportunity, "trade_lane")
    service_type = clean_record.get("service_type") or row_value(opportunity, "service_type")

    if quotation_id:
        existing = cur.execute("SELECT * FROM quotations WHERE id = ?", (quotation_id,)).fetchone()
        if not existing:
            conn.close()
            return None
        cur.execute(
            """
            UPDATE quotations
            SET opportunity_id = ?,
                quote_date = ?,
                valid_until = ?,
                currency = ?,
                sell_amount = ?,
                status = ?,
                template_name = ?,
                customer_name = ?,
                contact_name = ?,
                trade_lane = ?,
                service_type = ?,
                payment_terms = ?,
                prepared_by = ?,
                follow_up_date = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                opportunity_id,
                clean_record.get("quote_date") or today_iso(),
                clean_record.get("valid_until"),
                currency,
                totals["sell_amount"],
                status,
                clean_record.get("template_name") or "Standard Freight Quote",
                customer_name,
                contact_name,
                trade_lane,
                service_type,
                clean_record.get("payment_terms"),
                clean_record.get("prepared_by") or user,
                clean_record.get("follow_up_date"),
                clean_record.get("notes"),
                quotation_id,
            ),
        )
        saved_id = quotation_id
        action = "updated"
    else:
        quote_no = clean_record.get("quote_no") or generate_quote_no(cur)
        cur.execute(
            """
            INSERT INTO quotations (
                opportunity_id,
                quote_no,
                quote_date,
                valid_until,
                currency,
                sell_amount,
                status,
                template_name,
                version,
                parent_quotation_id,
                customer_name,
                contact_name,
                trade_lane,
                service_type,
                payment_terms,
                prepared_by,
                owner,
                follow_up_date,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                opportunity_id,
                quote_no,
                clean_record.get("quote_date") or today_iso(),
                clean_record.get("valid_until"),
                currency,
                totals["sell_amount"],
                status,
                clean_record.get("template_name") or "Standard Freight Quote",
                int(parse_money(clean_record.get("version")) or 1),
                clean_record.get("parent_quotation_id") or None,
                customer_name,
                contact_name,
                trade_lane,
                service_type,
                clean_record.get("payment_terms"),
                clean_record.get("prepared_by") or user,
                clean_record.get("owner") or admin_user_id,
                clean_record.get("follow_up_date"),
                clean_record.get("notes"),
            ),
        )
        saved_id = cur.lastrowid
        action = "created"

    saved_items = replace_quotation_items(cur, saved_id, quote_items)
    totals = calculate_quotation_totals(saved_items)
    cur.execute(
        """
        UPDATE quotations
        SET sell_amount = ?,
            currency = COALESCE(NULLIF(currency, ''), ?),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (totals["sell_amount"], currency or "USD", saved_id),
    )

    if opportunity_id and status in ["Approved", "Sent"]:
        cur.execute(
            """
            UPDATE opportunities
            SET stage = 'Quoted',
                status = 'quoted',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (opportunity_id,),
        )

    log_crm_activity(
        cur,
        "Quotation Update",
        f"Quotation {action}: {clean_record.get('quote_no') or row_value(cur.execute('SELECT quote_no FROM quotations WHERE id = ?', (saved_id,)).fetchone(), 'quote_no')}",
        opportunity_id=opportunity_id,
        quotation_id=saved_id,
        organization_id=row_value(opportunity, "organization_id", None),
        contact_id=row_value(opportunity, "contact_id", None),
        user=user,
    )
    conn.commit()
    conn.close()
    return saved_id


def build_quotation_items_from_pricing(opportunity_id, currency="USD"):
    summary = get_pricing_summary(opportunity_id)
    rates = [
        rate for rate in summary["rates"]
        if not currency or (rate.get("currency") or "USD") == currency
    ]
    items = []
    for rate in rates:
        items.append(
            {
                "description": rate.get("charge_name") or rate.get("charge_type") or "Freight charge",
                "basis": rate.get("basis") or "Shipment",
                "quantity": 1,
                "unit_price": rate.get("suggested_sell_amount") or 0,
                "currency": rate.get("currency") or currency or "USD",
                "amount": rate.get("suggested_sell_amount") or 0,
                "cost_amount": rate.get("cost_amount") or 0,
                "vendor_name": rate.get("vendor_name") or rate.get("vendor_type") or "",
                "notes": rate.get("notes") or "",
            }
        )
    return items


def create_quotation_from_opportunity(opportunity_id, template_name="Standard Freight Quote", currency="USD", user="admin"):
    templates = {template["template_name"]: template for template in get_quotation_templates()}
    template = templates.get(template_name) or templates.get("Standard Freight Quote") or {}
    valid_until = days_from_today(int(template.get("validity_days") or 14))
    items = build_quotation_items_from_pricing(opportunity_id, currency)
    if not items:
        opportunity = get_opportunity_detail(opportunity_id)
        amount = opportunity.get("potential_revenue") if opportunity else 0
        items = [
            {
                "description": "Freight service",
                "basis": "Shipment",
                "quantity": 1,
                "unit_price": amount or 0,
                "currency": currency or "USD",
                "amount": amount or 0,
                "cost_amount": 0,
                "vendor_name": "",
                "notes": "",
            }
        ]
    record = {
        "opportunity_id": opportunity_id,
        "template_name": template_name,
        "valid_until": valid_until,
        "currency": currency or "USD",
        "status": "Draft",
        "payment_terms": template.get("payment_terms") or "",
        "prepared_by": user,
    }
    return save_quotation(record, items, user=user)


def create_quotation_version(quotation_id, user="admin"):
    detail = get_quotation_detail(quotation_id)
    if not detail:
        return None
    base_parent_id = detail.get("parent_quotation_id") or detail["id"]
    conn = get_connection()
    latest_version = conn.execute(
        """
        SELECT MAX(version) AS latest_version
        FROM quotations
        WHERE id = ? OR parent_quotation_id = ?
        """,
        (base_parent_id, base_parent_id),
    ).fetchone()
    conn.close()
    next_version = int(row_value(latest_version, "latest_version", 1) or 1) + 1
    record = {
        "opportunity_id": detail.get("opportunity_id"),
        "quote_no": detail.get("quote_no"),
        "quote_date": today_iso(),
        "valid_until": detail.get("valid_until"),
        "currency": detail.get("currency"),
        "status": "Draft",
        "template_name": detail.get("template_name"),
        "version": next_version,
        "parent_quotation_id": base_parent_id,
        "customer_name": detail.get("customer_name"),
        "contact_name": detail.get("contact_name"),
        "trade_lane": detail.get("trade_lane"),
        "service_type": detail.get("service_type"),
        "payment_terms": detail.get("payment_terms"),
        "prepared_by": user,
        "follow_up_date": detail.get("follow_up_date"),
        "notes": detail.get("notes"),
    }
    return save_quotation(record, detail.get("items", []), user=user)


def update_quotation_status(quotation_id, status, user="admin"):
    normalized_status = quote_status_label(status)
    conn = get_connection()
    cur = conn.cursor()
    quotation = cur.execute(
        """
        SELECT quotations.*, opportunities.organization_id, opportunities.contact_id
        FROM quotations
        LEFT JOIN opportunities ON opportunities.id = quotations.opportunity_id
        WHERE quotations.id = ?
        """,
        (quotation_id,),
    ).fetchone()
    if not quotation:
        conn.close()
        return False
    approved_at = row_value(quotation, "approved_at") or None
    approved_by = row_value(quotation, "approved_by") or None
    sent_at = row_value(quotation, "sent_at") or None
    if normalized_status == "Approved":
        approved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        approved_by = user
    if normalized_status == "Sent":
        sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not approved_at:
            approved_at = sent_at
            approved_by = user
    cur.execute(
        """
        UPDATE quotations
        SET status = ?,
            approved_at = ?,
            approved_by = ?,
            sent_at = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (normalized_status, approved_at, approved_by, sent_at, quotation_id),
    )
    if normalized_status in ["Approved", "Sent"] and quotation["opportunity_id"]:
        cur.execute(
            """
            UPDATE opportunities
            SET stage = 'Quoted',
                status = 'quoted',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (quotation["opportunity_id"],),
        )
    if normalized_status == "Sent":
        existing_follow_up = cur.execute(
            """
            SELECT id
            FROM tasks
            WHERE quotation_id = ?
                AND task_type = 'quote_follow_up'
                AND status = 'open'
            LIMIT 1
            """,
            (quotation_id,),
        ).fetchone()
        if not existing_follow_up:
            follow_up_date = row_value(quotation, "follow_up_date", "") or days_from_today(3)
            task_title = "Follow up quote: " + (
                row_value(quotation, "quote_no", "")
                or row_value(quotation, "customer_name", "")
                or "Quotation"
            )
            cur.execute(
                """
                INSERT INTO tasks (
                    opportunity_id,
                    quotation_id,
                    task_type,
                    title,
                    due_date,
                    status,
                    priority,
                    assigned_to,
                    created_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    quotation["opportunity_id"],
                    quotation_id,
                    "quote_follow_up",
                    task_title,
                    follow_up_date,
                    "open",
                    "high",
                    row_value(quotation, "owner", None),
                    row_value(quotation, "owner", None),
                ),
            )
            cur.execute(
                """
                UPDATE quotations
                SET follow_up_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (follow_up_date, quotation_id),
            )
    log_crm_activity(
        cur,
        "Quotation Approval",
        f"Quotation {quotation['quote_no']} status changed to {normalized_status}",
        opportunity_id=quotation["opportunity_id"],
        quotation_id=quotation_id,
        organization_id=quotation["organization_id"],
        contact_id=quotation["contact_id"],
        user=user,
    )
    conn.commit()
    conn.close()
    return True


def update_lead_detail(lead_id, organization_data, contact_data, lead_data):
    conn = get_connection()
    cur = conn.cursor()

    lead = cur.execute(
        """
        SELECT organization_id, contact_id
        FROM leads
        WHERE id = ?
        """,
        (lead_id,),
    ).fetchone()

    if not lead:
        conn.close()
        return False

    if lead["organization_id"] and organization_data:
        cur.execute(
            """
            UPDATE organizations
            SET name = ?,
                local_name = ?,
                type = ?,
                country = ?,
                province = ?,
                city = ?,
                website = ?,
                founding_date = ?,
                anniversary_date = ?,
                preferred_language = ?,
                relationship_tone = ?,
                membership = ?,
                customer_status = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                organization_data.get("name"),
                organization_data.get("local_name"),
                organization_data.get("type"),
                organization_data.get("country"),
                organization_data.get("province"),
                organization_data.get("city"),
                organization_data.get("website"),
                organization_data.get("founding_date"),
                organization_data.get("anniversary_date"),
                organization_data.get("preferred_language"),
                organization_data.get("relationship_tone"),
                organization_data.get("membership"),
                organization_data.get("customer_status"),
                organization_data.get("notes"),
                lead["organization_id"],
            ),
        )
        log_crm_activity(
            cur,
            "Organization Update",
            "Organization details edited",
            lead_id=lead_id,
            organization_id=lead["organization_id"],
            contact_id=lead["contact_id"],
        )

    if lead["contact_id"] and contact_data:
        contact_name = contact_data.get("name")
        cur.execute(
            """
            UPDATE contacts
            SET name = ?,
                full_name = ?,
                contact_person = ?,
                job_title = ?,
                title = ?,
                email = ?,
                email_status = ?,
                phone = ?,
                wechat = ?,
                whatsapp = ?,
                birthday = ?,
                preferred_language = ?,
                preferred_channel = ?,
                relationship_tone = ?,
                relationship_status = ?,
                last_contacted_at = ?,
                next_follow_up_at = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                contact_name,
                contact_name,
                contact_name,
                contact_data.get("job_title"),
                contact_data.get("job_title"),
                contact_data.get("email"),
                contact_data.get("email_status") or "Unknown",
                contact_data.get("phone"),
                contact_data.get("wechat"),
                contact_data.get("whatsapp"),
                contact_data.get("birthday"),
                contact_data.get("preferred_language"),
                contact_data.get("preferred_channel"),
                contact_data.get("relationship_tone"),
                contact_data.get("relationship_status"),
                contact_data.get("last_contacted_at"),
                contact_data.get("next_follow_up_at"),
                contact_data.get("notes"),
                lead["contact_id"],
            ),
        )
        log_crm_activity(
            cur,
            "Contact Update",
            "Contact details edited",
            lead_id=lead_id,
            organization_id=lead["organization_id"],
            contact_id=lead["contact_id"],
        )

    cur.execute(
        """
        UPDATE leads
        SET source = ?,
            campaign = ?,
            lead_status = ?,
            status = ?,
            interest_level = ?,
            next_action = ?,
            next_action_date = ?,
            notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            lead_data.get("source"),
            lead_data.get("campaign"),
            lead_data.get("lead_status"),
            lead_data.get("lead_status"),
            lead_data.get("interest_level"),
            lead_data.get("next_action"),
            lead_data.get("next_action_date"),
            lead_data.get("notes"),
            lead_id,
        ),
    )
    log_crm_activity(
        cur,
        "Status Change",
        "Lead details edited",
        lead_id=lead_id,
        organization_id=lead["organization_id"],
        contact_id=lead["contact_id"],
    )

    conn.commit()
    conn.close()
    return True


def update_lead_status_action(lead_id, action):
    conn = get_connection()
    cur = conn.cursor()

    lead = cur.execute(
        """
        SELECT organization_id, contact_id
        FROM leads
        WHERE id = ?
        """,
        (lead_id,),
    ).fetchone()

    if not lead:
        conn.close()
        return False

    if action == "Contacted":
        cur.execute(
            """
            UPDATE leads
            SET lead_status = ?,
                status = ?,
                next_action = ?,
                next_action_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            ("Contacted", "Contacted", "Follow up after intro", days_from_today(7), lead_id),
        )
        if lead["contact_id"]:
            cur.execute(
                """
                UPDATE contacts
                SET last_contacted_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (lead["contact_id"],),
            )
        log_crm_activity(
            cur,
            "Status Change",
            "Lead marked Contacted",
            lead_id=lead_id,
            organization_id=lead["organization_id"],
            contact_id=lead["contact_id"],
        )
    elif action == "Replied":
        cur.execute(
            """
            UPDATE leads
            SET lead_status = ?,
                status = ?,
                next_action = ?,
                next_action_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                "Replied",
                "Replied",
                "Continue conversation / ask for Vietnam shipments",
                days_from_today(14),
                lead_id,
            ),
        )
        if lead["contact_id"]:
            cur.execute(
                """
                UPDATE contacts
                SET relationship_status = ?,
                    last_contacted_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                ("Warm", lead["contact_id"]),
            )
        log_crm_activity(
            cur,
            "Status Change",
            "Lead marked Replied and relationship warmed",
            lead_id=lead_id,
            organization_id=lead["organization_id"],
            contact_id=lead["contact_id"],
        )
    elif action == "Qualified":
        cur.execute(
            """
            UPDATE leads
            SET lead_status = ?,
                status = ?,
                next_action = ?,
                next_action_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            ("Qualified", "Qualified", "Ask for current shipment inquiry", days_from_today(14), lead_id),
        )
        if lead["organization_id"]:
            cur.execute(
                """
                UPDATE organizations
                SET customer_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                ("Qualified", lead["organization_id"]),
            )
        if lead["contact_id"]:
            cur.execute(
                """
                UPDATE contacts
                SET relationship_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                ("Warm", lead["contact_id"]),
            )
        log_crm_activity(
            cur,
            "Status Change",
            "Lead qualified",
            lead_id=lead_id,
            organization_id=lead["organization_id"],
            contact_id=lead["contact_id"],
        )
    elif action == "Converted":
        cur.execute(
            """
            UPDATE leads
            SET lead_status = ?,
                status = ?,
                next_action = ?,
                next_action_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            ("Converted", "Converted", "Relationship Maintenance", days_from_today(30), lead_id),
        )
        if lead["organization_id"]:
            cur.execute(
                """
                UPDATE organizations
                SET customer_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                ("Customer", lead["organization_id"]),
            )
        if lead["contact_id"]:
            cur.execute(
                """
                UPDATE contacts
                SET relationship_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                ("Active", lead["contact_id"]),
            )
        log_crm_activity(
            cur,
            "Status Change",
            "Lead converted to customer",
            lead_id=lead_id,
            organization_id=lead["organization_id"],
            contact_id=lead["contact_id"],
        )
    elif action == "Disqualified":
        cur.execute(
            """
            UPDATE leads
            SET lead_status = ?,
                status = ?,
                next_action = '',
                next_action_date = '',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            ("Disqualified", "Disqualified", lead_id),
        )
        log_crm_activity(
            cur,
            "Status Change",
            "Lead disqualified",
            lead_id=lead_id,
            organization_id=lead["organization_id"],
            contact_id=lead["contact_id"],
        )
    else:
        conn.close()
        return False

    conn.commit()
    conn.close()
    return True


def update_contact_relationship_action(contact_id, relationship_status):
    conn = get_connection()
    cur = conn.cursor()

    lead = cur.execute(
        """
        SELECT id, organization_id
        FROM leads
        WHERE contact_id = ?
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (contact_id,),
    ).fetchone()

    cur.execute(
        """
        UPDATE contacts
        SET relationship_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (relationship_status, contact_id),
    )

    if lead:
        next_action = next_action_for_state(None, relationship_status)
        next_days = 30 if relationship_status == "Active" else 14
        cur.execute(
            """
            UPDATE leads
            SET next_action = ?,
                next_action_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (next_action, days_from_today(next_days), lead["id"]),
        )

    log_crm_activity(
        cur,
        "Status Change",
        f"Relationship status changed to {relationship_status}",
        lead_id=row_value(lead, "id", None),
        organization_id=row_value(lead, "organization_id", None),
        contact_id=contact_id,
    )

    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def update_organization_customer_action(organization_id, customer_status):
    conn = get_connection()
    cur = conn.cursor()

    lead = cur.execute(
        """
        SELECT id, contact_id
        FROM leads
        WHERE organization_id = ?
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (organization_id,),
    ).fetchone()

    cur.execute(
        """
        UPDATE organizations
        SET customer_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (customer_status, organization_id),
    )

    log_crm_activity(
        cur,
        "Status Change",
        f"Customer status changed to {customer_status}",
        lead_id=row_value(lead, "id", None),
        organization_id=organization_id,
        contact_id=row_value(lead, "contact_id", None),
    )

    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def update_lead_next_follow_up(lead_id, next_action, next_action_date):
    conn = get_connection()
    cur = conn.cursor()

    lead = cur.execute(
        """
        SELECT contact_id
        FROM leads
        WHERE id = ?
        """,
        (lead_id,),
    ).fetchone()

    if not lead:
        conn.close()
        return False

    cur.execute(
        """
        UPDATE leads
        SET next_action = ?,
            next_action_date = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (next_action, next_action_date, lead_id),
    )

    if lead["contact_id"]:
        cur.execute(
            """
            UPDATE contacts
            SET next_follow_up_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (next_action_date, lead["contact_id"]),
        )

    log_crm_activity(
        cur,
        "Follow-up",
        f"Next follow-up updated: {next_action or 'No action'}"
        + (f" on {next_action_date}" if next_action_date else ""),
        lead_id=lead_id,
        contact_id=lead["contact_id"],
    )

    conn.commit()
    conn.close()
    return True


def snooze_follow_up(lead_id, days, user="admin"):
    conn = get_connection()
    cur = conn.cursor()
    next_date = days_from_today(days)

    lead = cur.execute(
        """
        SELECT organization_id, contact_id
        FROM leads
        WHERE id = ?
        """,
        (lead_id,),
    ).fetchone()

    if not lead:
        conn.close()
        return False

    cur.execute(
        """
        UPDATE leads
        SET next_action_date = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (next_date, lead_id),
    )

    if lead["contact_id"]:
        cur.execute(
            """
            UPDATE contacts
            SET next_follow_up_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (next_date, lead["contact_id"]),
        )

    log_crm_activity(
        cur,
        "Follow-up",
        f"Follow-up snoozed {days} days",
        lead_id=lead_id,
        organization_id=lead["organization_id"],
        contact_id=lead["contact_id"],
        user=user,
    )

    conn.commit()
    conn.close()
    return True


def complete_follow_up(lead_id, user="admin"):
    conn = get_connection()
    cur = conn.cursor()

    lead = cur.execute(
        """
        SELECT
            leads.organization_id,
            leads.contact_id,
            COALESCE(leads.lead_status, 'New') AS lead_status,
            COALESCE(contacts.relationship_status, '') AS relationship_status
        FROM leads
        LEFT JOIN contacts ON contacts.id = leads.contact_id
        WHERE id = ?
        """,
        (lead_id,),
    ).fetchone()

    if not lead:
        conn.close()
        return False

    next_status = lead["lead_status"]
    relationship_status = lead["relationship_status"]
    next_days = 14

    if lead["lead_status"] == "New":
        next_status = "Contacted"
        next_action = "Follow-up"
        next_days = 7
        if lead["contact_id"]:
            cur.execute(
                """
                UPDATE contacts
                SET last_contacted_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (lead["contact_id"],),
            )
    elif relationship_status == "Active" or lead["lead_status"] == "Converted":
        next_action = "Relationship Maintenance"
        next_days = 30
    elif relationship_status == "Warm":
        next_action = "Relationship Nurturing"
        next_days = 14
    elif lead["lead_status"] == "Contacted":
        next_action = "Follow-up"
        next_days = 7
    else:
        next_action = next_action_for_state(lead["lead_status"], relationship_status)

    next_date = days_from_today(next_days)

    cur.execute(
        """
        UPDATE leads
        SET lead_status = ?,
            status = ?,
            next_action = ?,
            next_action_date = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (next_status, next_status, next_action, next_date, lead_id),
    )

    if lead["contact_id"]:
        cur.execute(
            """
            UPDATE contacts
            SET next_follow_up_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (next_date, lead["contact_id"]),
        )

    log_crm_activity(
        cur,
        "Follow-up",
        f"Follow-up completed. Next: {next_action} on {next_date}",
        lead_id=lead_id,
        organization_id=lead["organization_id"],
        contact_id=lead["contact_id"],
        user=user,
    )

    conn.commit()
    conn.close()
    return True


def update_lead_notes(lead_id, notes, user="admin"):
    conn = get_connection()
    cur = conn.cursor()

    lead = cur.execute(
        """
        SELECT organization_id, contact_id
        FROM leads
        WHERE id = ?
        """,
        (lead_id,),
    ).fetchone()

    if not lead:
        conn.close()
        return False

    cur.execute(
        """
        UPDATE leads
        SET notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (notes, lead_id),
    )

    log_crm_activity(
        cur,
        "Note",
        "Manual note added",
        lead_id=lead_id,
        organization_id=lead["organization_id"],
        contact_id=lead["contact_id"],
        user=user,
    )

    conn.commit()
    conn.close()
    return True


def occasion_display_date(occasion_date, is_recurring):
    if not occasion_date:
        return None
    try:
        base_date = date.fromisoformat(str(occasion_date)[:10])
    except ValueError:
        return None
    if not is_recurring:
        return base_date

    current_year_date = base_date.replace(year=date.today().year)
    if current_year_date < date.today():
        return current_year_date.replace(year=date.today().year + 1)
    return current_year_date


def draft_relationship_message(row):
    contact_name = clean_value(row.get("contact_name"))
    organization_name = clean_value(row.get("organization_name"))
    occasion_name = clean_value(row.get("occasion_name"))
    language = clean_value(row.get("preferred_language")) or "English"
    tone = clean_value(row.get("message_tone")) or clean_value(row.get("relationship_tone")) or "Warm"

    if language == "Chinese":
        if contact_name:
            return (
                f"{contact_name}，祝您和团队{occasion_name}快乐，身体健康，事业顺利。"
                "期待我们保持联系，未来有更多合作机会。"
            )
        return (
            f"祝{organization_name or '贵司'}团队{occasion_name}快乐，身体健康，事业顺利。"
            "期待我们保持联系，未来有更多合作机会。"
        )

    if language == "Vietnamese":
        recipient = f"anh/chị {contact_name}" if contact_name else f"đội ngũ {organization_name or 'quý công ty'}"
        return (
            f"Chúc {recipient} và đội ngũ {occasion_name} nhiều sức khỏe, may mắn và thành công. "
            "Rất mong tiếp tục giữ liên lạc và có thêm cơ hội hợp tác trong thời gian tới."
        )

    if contact_name:
        greeting = f"Hi {contact_name},"
    else:
        greeting = f"Hi {organization_name or 'team'},"

    if tone == "Short":
        return f"{greeting} wishing you and your team a wonderful {occasion_name}. Hope all is well."
    if tone == "Formal":
        return (
            f"{greeting} wishing you and your team a wonderful {occasion_name}. "
            "May this occasion bring good health, happiness, and continued success."
        )
    return (
        f"{greeting} wishing you and your team a wonderful {occasion_name}. "
        "Hope this season brings good health, happiness, and continued success. "
        "Looking forward to staying in touch."
    )


def create_relationship_occasion(record):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO relationship_occasions (
            organization_id,
            contact_id,
            occasion_type,
            occasion_name,
            occasion_date,
            country,
            is_recurring,
            recurrence_rule,
            preferred_channel,
            preferred_language,
            message_tone,
            reminder_days_before,
            status,
            notes,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            record.get("organization_id"),
            record.get("contact_id"),
            record.get("occasion_type"),
            record.get("occasion_name"),
            record.get("occasion_date"),
            record.get("country"),
            1 if record.get("is_recurring", True) else 0,
            record.get("recurrence_rule") or "yearly_mm_dd",
            record.get("preferred_channel"),
            record.get("preferred_language"),
            record.get("message_tone"),
            record.get("reminder_days_before", 7),
            record.get("status") or "Active",
            record.get("notes"),
        ),
    )
    occasion_id = cur.lastrowid
    conn.commit()
    conn.close()
    return occasion_id


def add_country_holiday_reminders(organization_id, contact_id=None):
    conn = get_connection()
    cur = conn.cursor()
    organization = cur.execute(
        """
        SELECT *
        FROM organizations
        WHERE id = ?
        """,
        (organization_id,),
    ).fetchone()
    if not organization or not organization["country"]:
        conn.close()
        return 0

    holidays = cur.execute(
        """
        SELECT *
        FROM holiday_library
        WHERE LOWER(TRIM(country)) = LOWER(TRIM(?))
        """,
        (organization["country"],),
    ).fetchall()

    created = 0
    for holiday in holidays:
        exists = cur.execute(
            """
            SELECT id
            FROM relationship_occasions
            WHERE organization_id = ?
                AND COALESCE(contact_id, 0) = COALESCE(?, 0)
                AND occasion_name = ?
            LIMIT 1
            """,
            (organization_id, contact_id, holiday["holiday_name"]),
        ).fetchone()
        if exists:
            continue
        cur.execute(
            """
            INSERT INTO relationship_occasions (
                organization_id,
                contact_id,
                occasion_type,
                occasion_name,
                occasion_date,
                country,
                is_recurring,
                recurrence_rule,
                preferred_channel,
                preferred_language,
                message_tone,
                reminder_days_before,
                status,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                organization_id,
                contact_id,
                "National Holiday",
                holiday["holiday_name"],
                holiday["holiday_date"],
                holiday["country"],
                holiday["is_recurring"],
                holiday["recurrence_rule"],
                None,
                organization["preferred_language"] or "English",
                organization["relationship_tone"] or "Warm",
                7,
                "Active",
                holiday["default_message_theme"],
            ),
        )
        created += 1

    conn.commit()
    conn.close()
    return created


def sync_date_based_occasions(organization_id=None, contact_id=None):
    conn = get_connection()
    cur = conn.cursor()
    created = 0

    if contact_id:
        contact = cur.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
        if contact and contact["birthday"]:
            exists = cur.execute(
                """
                SELECT id FROM relationship_occasions
                WHERE contact_id = ? AND occasion_type = ? LIMIT 1
                """,
                (contact_id, "Birthday"),
            ).fetchone()
            if not exists:
                cur.execute(
                    """
                    INSERT INTO relationship_occasions (
                        organization_id, contact_id, occasion_type, occasion_name,
                        occasion_date, country, is_recurring, recurrence_rule,
                        preferred_channel, preferred_language, message_tone,
                        reminder_days_before, status, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (
                        contact["organization_id"],
                        contact_id,
                        "Birthday",
                        "Birthday",
                        contact["birthday"],
                        None,
                        1,
                        "yearly_mm_dd",
                        contact["preferred_channel"],
                        contact["preferred_language"] or "English",
                        contact["relationship_tone"] or "Warm",
                        7,
                        "Active",
                    ),
                )
                created += 1

    if organization_id:
        organization = cur.execute("SELECT * FROM organizations WHERE id = ?", (organization_id,)).fetchone()
        for field, occasion_type, occasion_name in [
            ("founding_date", "Company Anniversary", "Company Anniversary"),
            ("anniversary_date", "Cooperation Anniversary", "Cooperation Anniversary"),
        ]:
            if not organization or not organization[field]:
                continue
            exists = cur.execute(
                """
                SELECT id FROM relationship_occasions
                WHERE organization_id = ? AND occasion_type = ? LIMIT 1
                """,
                (organization_id, occasion_type),
            ).fetchone()
            if exists:
                continue
            cur.execute(
                """
                INSERT INTO relationship_occasions (
                    organization_id, occasion_type, occasion_name, occasion_date,
                    country, is_recurring, recurrence_rule, preferred_language,
                    message_tone, reminder_days_before, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    organization_id,
                    occasion_type,
                    occasion_name,
                    organization[field],
                    organization["country"],
                    1,
                    "yearly_mm_dd",
                    organization["preferred_language"] or "English",
                    organization["relationship_tone"] or "Warm",
                    14,
                    "Active",
                ),
            )
            created += 1

    conn.commit()
    conn.close()
    return created


def get_occasion_reminders():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            relationship_occasions.*,
            organizations.name AS organization_name,
            organizations.country AS organization_country,
            organizations.relationship_tone AS organization_tone,
            contacts.name AS contact_name,
            contacts.relationship_status,
            contacts.notes AS contact_notes,
            contacts.preferred_language AS contact_language,
            contacts.preferred_channel AS contact_channel,
            contacts.relationship_tone AS contact_tone,
            leads.id AS lead_id
        FROM relationship_occasions
        LEFT JOIN organizations ON organizations.id = relationship_occasions.organization_id
        LEFT JOIN contacts ON contacts.id = relationship_occasions.contact_id
        LEFT JOIN leads ON leads.contact_id = relationship_occasions.contact_id
            OR (
                relationship_occasions.contact_id IS NULL
                AND leads.organization_id = relationship_occasions.organization_id
            )
        WHERE relationship_occasions.status = 'Active'
        GROUP BY relationship_occasions.id
        """
    ).fetchall()
    conn.close()

    reminders = []
    today = date.today()
    for row in rows:
        item = dict(row)
        display_date = occasion_display_date(item["occasion_date"], item["is_recurring"])
        if not display_date:
            continue
        reminder_start = display_date - timedelta(days=item["reminder_days_before"] or 0)
        if today < reminder_start:
            continue
        if display_date < today:
            bucket = "Overdue"
        elif display_date == today:
            bucket = "Today"
        elif display_date <= today + timedelta(days=7):
            bucket = "Next 7 days"
        elif display_date <= today + timedelta(days=30):
            bucket = "Next 30 days"
        else:
            continue

        item["display_date"] = display_date.isoformat()
        item["bucket"] = bucket
        item["preferred_language"] = item["preferred_language"] or item["contact_language"] or "English"
        item["preferred_channel"] = item["preferred_channel"] or item["contact_channel"] or "WeChat"
        item["message_tone"] = item["message_tone"] or item["contact_tone"] or item["organization_tone"] or "Warm"
        item["country"] = item["country"] or item["organization_country"] or ""
        item["suggested_message"] = draft_relationship_message(item)
        reminders.append(item)

    return sorted(reminders, key=lambda item: (item["display_date"], item["id"]))


def mark_occasion_message_sent(occasion_id, user="admin"):
    conn = get_connection()
    cur = conn.cursor()
    occasion = cur.execute(
        "SELECT * FROM relationship_occasions WHERE id = ?",
        (occasion_id,),
    ).fetchone()
    if not occasion:
        conn.close()
        return False

    lead = cur.execute(
        """
        SELECT id FROM leads
        WHERE (contact_id = ? AND ? IS NOT NULL)
            OR (organization_id = ? AND ? IS NOT NULL)
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (occasion["contact_id"], occasion["contact_id"], occasion["organization_id"], occasion["organization_id"]),
    ).fetchone()

    if occasion["contact_id"]:
        cur.execute(
            """
            UPDATE contacts
            SET last_contacted_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (today_iso(), occasion["contact_id"]),
        )

    log_crm_activity(
        cur,
        "Occasion Message Sent",
        f"Sent {occasion['occasion_name']} greeting via {occasion['preferred_channel'] or 'manual channel'}",
        lead_id=row_value(lead, "id", None),
        organization_id=occasion["organization_id"],
        contact_id=occasion["contact_id"],
        user=user,
    )

    if not occasion["is_recurring"]:
        cur.execute(
            """
            UPDATE relationship_occasions
            SET status = 'Completed',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (occasion_id,),
        )

    conn.commit()
    conn.close()
    return True


def snooze_occasion(occasion_id, days=7):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE relationship_occasions
        SET occasion_date = ?,
            is_recurring = 0,
            recurrence_rule = 'snoozed_once',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (days_from_today(days), occasion_id),
    )
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def update_relationship_occasion(occasion_id, record):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE relationship_occasions
        SET occasion_type = ?,
            occasion_name = ?,
            occasion_date = ?,
            country = ?,
            is_recurring = ?,
            recurrence_rule = ?,
            preferred_channel = ?,
            preferred_language = ?,
            message_tone = ?,
            reminder_days_before = ?,
            status = ?,
            notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            record.get("occasion_type"),
            record.get("occasion_name"),
            record.get("occasion_date"),
            record.get("country"),
            1 if record.get("is_recurring") else 0,
            record.get("recurrence_rule"),
            record.get("preferred_channel"),
            record.get("preferred_language"),
            record.get("message_tone"),
            record.get("reminder_days_before"),
            record.get("status"),
            record.get("notes"),
            occasion_id,
        ),
    )
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_holiday_library():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM holiday_library
        ORDER BY country, holiday_name
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_holiday_library_item(record, holiday_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if holiday_id:
        cur.execute(
            """
            UPDATE holiday_library
            SET country = ?,
                holiday_name = ?,
                holiday_date = ?,
                is_recurring = ?,
                recurrence_rule = ?,
                default_message_theme = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                record.get("country"),
                record.get("holiday_name"),
                record.get("holiday_date"),
                1 if record.get("is_recurring") else 0,
                record.get("recurrence_rule"),
                record.get("default_message_theme"),
                holiday_id,
            ),
        )
        saved_id = holiday_id
    else:
        cur.execute(
            """
            INSERT INTO holiday_library (
                country,
                holiday_name,
                holiday_date,
                is_recurring,
                recurrence_rule,
                default_message_theme,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                record.get("country"),
                record.get("holiday_name"),
                record.get("holiday_date"),
                1 if record.get("is_recurring", True) else 0,
                record.get("recurrence_rule") or "yearly_mm_dd",
                record.get("default_message_theme"),
            ),
        )
        saved_id = cur.lastrowid

    conn.commit()
    conn.close()
    return saved_id


def convert_lead_to_contact(lead_id):
    conn = get_connection()
    cur = conn.cursor()

    lead = cur.execute(
        """
        SELECT *
        FROM leads
        WHERE id = ?
        """,
        (lead_id,),
    ).fetchone()

    if not lead:
        conn.close()
        return None

    lead_data = dict(lead)
    organization_id = lead["organization_id"] or upsert_organization(cur, lead_data)
    contact_id = lead["contact_id"] or upsert_contact(cur, organization_id, lead_data)

    cur.execute(
        """
        UPDATE organizations
        SET customer_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        ("Qualified", organization_id),
    )

    cur.execute(
        """
        UPDATE contacts
        SET relationship_status = ?,
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        ("Warm", "Qualified Contact", contact_id),
    )

    cur.execute(
        """
        UPDATE leads
        SET organization_id = ?,
            contact_id = ?,
            lead_status = ?,
            status = ?,
            converted_contact_id = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (organization_id, contact_id, "Converted", "Converted", contact_id, lead_id),
    )

    conn.commit()
    conn.close()
    return contact_id


def mark_organization_as_customer(organization_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE organizations
        SET customer_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        ("Customer", organization_id),
    )

    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def find_captured_crm_duplicates(record):
    conn = get_connection()
    cur = conn.cursor()
    record = dict(record)
    duplicates = {
        "organizations": [],
        "contacts": [],
        "leads": [],
    }

    name = clean_value(record.get("company_name") or record.get("organization_name"))
    country = clean_value(record.get("country"))
    if name:
        rows = cur.execute(
            """
            SELECT id, name, country, website
            FROM organizations
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
                AND LOWER(TRIM(COALESCE(country, ''))) = LOWER(TRIM(COALESCE(?, '')))
            """,
            (name, country),
        ).fetchall()
        duplicates["organizations"].extend(
            dict(row) | {"reason": "Same organization name and country"}
            for row in rows
        )

    domain = normalize_domain(record.get("website"))
    if domain:
        rows = cur.execute(
            """
            SELECT id, name, country, website
            FROM organizations
            WHERE COALESCE(website, '') <> ''
            """
        ).fetchall()
        for row in rows:
            if normalize_domain(row["website"]) == domain:
                duplicate = dict(row) | {"reason": "Same website/domain"}
                if duplicate not in duplicates["organizations"]:
                    duplicates["organizations"].append(duplicate)

    candidate_organization = find_organization_for_record(cur, record)
    organization_id = row_value(candidate_organization, "id", None)

    for field, reason in [
        ("email", "Same email"),
        ("wechat", "Same WeChat"),
        ("whatsapp", "Same Whatsapp"),
    ]:
        value = clean_value(record.get(field))
        if value:
            rows = cur.execute(
                f"""
                SELECT id, organization_id, name, email, wechat, whatsapp
                FROM contacts
                WHERE LOWER(TRIM(COALESCE({field}, ''))) = LOWER(TRIM(?))
                """,
                (value,),
            ).fetchall()
            duplicates["contacts"].extend(dict(row) | {"reason": reason} for row in rows)

    contact_name = clean_value(record.get("contact_person") or record.get("name"))
    if organization_id and contact_name:
        rows = cur.execute(
            """
            SELECT id, organization_id, name, email, wechat, whatsapp
            FROM contacts
            WHERE organization_id = ?
                AND LOWER(TRIM(COALESCE(name, contact_person, full_name, ''))) = LOWER(TRIM(?))
            """,
            (organization_id, contact_name),
        ).fetchall()
        duplicates["contacts"].extend(
            dict(row) | {"reason": "Same organization and contact name"}
            for row in rows
        )

    unique_contacts = {}
    for contact in duplicates["contacts"]:
        unique_contacts[contact["id"]] = contact
    duplicates["contacts"] = list(unique_contacts.values())

    contact_id = duplicates["contacts"][0]["id"] if duplicates["contacts"] else None
    if organization_id and contact_id:
        rows = cur.execute(
            """
            SELECT id, organization_id, contact_id, source, campaign, lead_status
            FROM leads
            WHERE organization_id = ?
                AND contact_id = ?
                AND LOWER(TRIM(COALESCE(source, ''))) = LOWER(TRIM(COALESCE(?, '')))
                AND LOWER(TRIM(COALESCE(campaign, ''))) = LOWER(TRIM(COALESCE(?, '')))
            """,
            (
                organization_id,
                contact_id,
                clean_value(record.get("source")),
                clean_value(record.get("campaign")),
            ),
        ).fetchall()
        duplicates["leads"].extend(
            dict(row) | {"reason": "Same organization, contact, source, and campaign"}
            for row in rows
        )

    conn.close()
    return duplicates


def has_captured_crm_duplicates(duplicates):
    return any(duplicates.get(key) for key in ["organizations", "contacts", "leads"])


def apply_capture_mode(record, save_as):
    record = dict(record)
    save_as = clean_value(save_as) or "Lead"

    if save_as in ["Lead", "Lead only", "Lead + Contact + Organization"]:
        record["lead_status"] = "New"
        record["status"] = "New"
    elif save_as == "Qualified Contact":
        record["customer_status"] = "Qualified"
        record["relationship_status"] = "Warm"
        record["lead_status"] = "Qualified"
        record["status"] = "Qualified"
    elif save_as == "Customer":
        record["customer_status"] = "Customer"
        record["relationship_status"] = "Active"
        record["lead_status"] = "Converted"
        record["status"] = "Converted"

    return record


def save_captured_crm_record(record, save_as="Lead", duplicate_action="Update existing"):
    conn = get_connection()
    cur = conn.cursor()
    save_as = clean_value(save_as) or "Lead"
    duplicate_action = clean_value(duplicate_action) or "Update existing"
    record = apply_capture_mode(record, save_as)
    force_new = duplicate_action == "Create new anyway"

    if force_new:
        organization_id = insert_organization(cur, record) if record.get("company_name") else None
    else:
        organization_id = upsert_organization(cur, record) if record.get("company_name") else None

    contact_id = None
    has_contact_data = any(
        record.get(field)
        for field in ["contact_person", "email", "wechat", "whatsapp", "phone"]
    )
    if has_contact_data:
        if force_new:
            contact_id = insert_contact(cur, organization_id, record)
        else:
            contact_id = upsert_contact(cur, organization_id, record)

    lead_id = None
    existing_lead = None
    if not force_new and organization_id and contact_id:
        existing_lead = lead_exists(
            cur,
            organization_id,
            contact_id,
            record.get("campaign"),
            record.get("source"),
        )

    if existing_lead and duplicate_action == "Update existing":
        lead_id = existing_lead["id"]
        cur.execute(
            """
            UPDATE leads
            SET lead_status = ?,
                status = ?,
                notes = COALESCE(NULLIF(?, ''), notes),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                record.get("lead_status") or "New",
                record.get("status") or record.get("lead_status") or "New",
                record.get("notes"),
                lead_id,
            ),
        )
        log_crm_activity(
            cur,
            "Status Change",
            f"Existing lead updated as {save_as}",
            lead_id=lead_id,
            organization_id=organization_id,
            contact_id=contact_id,
            user=record.get("owner") or "admin",
        )
    elif organization_id or contact_id:
        lead_id = insert_lead(cur, organization_id, contact_id, record)
        log_crm_activity(
            cur,
            "Import",
            f"Lead captured as {save_as}",
            lead_id=lead_id,
            organization_id=organization_id,
            contact_id=contact_id,
            user=record.get("owner") or "admin",
        )

    conn.commit()
    conn.close()

    return {
        "organization_id": organization_id,
        "contact_id": contact_id,
        "lead_id": lead_id,
        "save_as": save_as,
        "updated_existing_lead": bool(existing_lead and duplicate_action == "Update existing"),
    }
