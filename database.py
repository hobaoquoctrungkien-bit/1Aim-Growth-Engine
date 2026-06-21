import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path("data/growth_engine.db")


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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
        wechat TEXT,
        whatsapp TEXT,
        phone TEXT,
        title TEXT,
        job_title TEXT,
        source TEXT,
        relationship_status TEXT DEFAULT 'New',
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
        contact_id INTEGER,
        title TEXT NOT NULL,
        route TEXT,
        commodity TEXT,
        volume TEXT,
        mode TEXT,
        status TEXT DEFAULT 'new',
        owner INTEGER,
        inquiry_text TEXT,
        inquiry_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(owner) REFERENCES users(id),
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
        owner INTEGER,
        follow_up_date TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(owner) REFERENCES users(id),
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id INTEGER,
        opportunity_id INTEGER,
        quotation_id INTEGER,
        activity_type TEXT,
        summary TEXT,
        activity_at TEXT DEFAULT CURRENT_TIMESTAMP,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
    add_column("tasks", "assigned_to INTEGER")
    add_column("tasks", "created_by INTEGER")
    add_column("opportunities", "owner INTEGER")
    add_column("quotations", "owner INTEGER")
    add_column("organizations", "type TEXT DEFAULT 'Other'")
    add_column("organizations", "country TEXT")
    add_column("organizations", "province TEXT")
    add_column("organizations", "city TEXT")
    add_column("organizations", "website TEXT")
    add_column("organizations", "local_name TEXT")
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

    migrate_crm_records(cur)

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


def row_value(row, key, default=""):
    if not row or key not in row.keys():
        return default
    value = row[key]
    if value is None:
        return default
    return value


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
            record.get("next_action"),
            record.get("next_action_date"),
            record.get("status") or record.get("lead_status") or "New",
            record.get("owner") or "admin",
            record.get("notes"),
        ),
    )
    return cur.lastrowid


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
            COALESCE(leads.status, leads.lead_status, 'New') AS status,
            COALESCE(leads.owner, 'admin') AS owner,
            leads.source,
            leads.campaign,
            leads.interest_level,
            leads.next_action,
            leads.next_action_date,
            contacts.last_contacted_at,
            contacts.relationship_status,
            organizations.customer_status
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

    conn.close()
    return {
        "lead": dict(lead),
        "organization": dict(organization) if organization else None,
        "contact": dict(contact) if contact else None,
    }


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
                organization_data.get("membership"),
                organization_data.get("customer_status"),
                organization_data.get("notes"),
                lead["organization_id"],
            ),
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
                phone = ?,
                wechat = ?,
                whatsapp = ?,
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
                contact_data.get("phone"),
                contact_data.get("wechat"),
                contact_data.get("whatsapp"),
                contact_data.get("relationship_status"),
                contact_data.get("last_contacted_at"),
                contact_data.get("next_follow_up_at"),
                contact_data.get("notes"),
                lead["contact_id"],
            ),
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
            SET lead_status = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            ("Contacted", "Contacted", lead_id),
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
    elif action == "Replied":
        cur.execute(
            """
            UPDATE leads
            SET lead_status = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            ("Replied", "Replied", lead_id),
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
    elif action == "Qualified":
        cur.execute(
            """
            UPDATE leads
            SET lead_status = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            ("Qualified", "Qualified", lead_id),
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
    elif action == "Converted":
        cur.execute(
            """
            UPDATE leads
            SET lead_status = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            ("Converted", "Converted", lead_id),
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
    elif action == "Disqualified":
        cur.execute(
            """
            UPDATE leads
            SET lead_status = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            ("Disqualified", "Disqualified", lead_id),
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

    cur.execute(
        """
        UPDATE contacts
        SET relationship_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (relationship_status, contact_id),
    )

    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def update_organization_customer_action(organization_id, customer_status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE organizations
        SET customer_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (customer_status, organization_id),
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

    conn.commit()
    conn.close()
    return True


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
    elif organization_id or contact_id:
        lead_id = insert_lead(cur, organization_id, contact_id, record)

    conn.commit()
    conn.close()

    return {
        "organization_id": organization_id,
        "contact_id": contact_id,
        "lead_id": lead_id,
        "save_as": save_as,
        "updated_existing_lead": bool(existing_lead and duplicate_action == "Update existing"),
    }
