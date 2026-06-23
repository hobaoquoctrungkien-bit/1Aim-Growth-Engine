import re
import unicodedata
from datetime import datetime
from pathlib import Path

from database import get_connection

UPLOAD_DIR = Path("data/knowledge_uploads")


def clean(value):
    return "" if value is None else str(value).strip()


def like_query(text):
    return f"%{clean(text)}%"


def ascii_fold(text):
    normalized = unicodedata.normalize("NFKD", clean(text)).replace("Đ", "D").replace("đ", "d")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def save_uploaded_knowledge_file(uploaded_file):
    if not uploaded_file:
        return ""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name.replace(" ", "_")
    target = UPLOAD_DIR / safe_name
    counter = 1
    while target.exists():
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        target = UPLOAD_DIR / f"{stem}_{counter}{suffix}"
        counter += 1
    target.write_bytes(uploaded_file.getvalue())
    return str(target)


def extract_uploaded_text(uploaded_file):
    if not uploaded_file:
        return ""
    suffix = Path(uploaded_file.name).suffix.lower()
    try:
        if suffix == ".txt":
            return uploaded_file.getvalue().decode("utf-8", errors="ignore")
        if suffix == ".pdf":
            return extract_pdf_text(uploaded_file)
        if suffix == ".docx":
            return extract_docx_text(uploaded_file)
    except Exception as exc:
        raise ValueError(f"Could not extract text from {uploaded_file.name}: {exc}") from exc
    return ""


def extract_pdf_text(uploaded_file):
    try:
        import fitz

        doc = fitz.open(stream=uploaded_file.getvalue(), filetype="pdf")
        return "\n".join(page.get_text("text") for page in doc)
    except ImportError:
        try:
            from pypdf import PdfReader
            import io

            reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError as exc:
            raise ValueError("Install PyMuPDF or pypdf to extract PDF text.") from exc


def extract_docx_text(uploaded_file):
    try:
        from docx import Document
        import io
    except ImportError as exc:
        raise ValueError("Install python-docx to extract DOCX text.") from exc
    document = Document(io.BytesIO(uploaded_file.getvalue()))
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())


def normalize_date(value):
    text = clean(value)
    if not text:
        return ""
    for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    folded = ascii_fold(text)
    match = re.search(r"ngay\s+(\d{1,2})\s+thang\s+(\d{1,2})\s+nam\s+(\d{4})", folded, flags=re.IGNORECASE)
    if match:
        day, month, year = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    match = re.search(r"(\d{1,2})\s+thang\s+(\d{1,2})\s+nam\s+(\d{4})", folded, flags=re.IGNORECASE)
    if match:
        day, month, year = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return ""


def first_regex(pattern, text, flags=re.IGNORECASE):
    match = re.search(pattern, text or "", flags)
    return clean(match.group(1)) if match else ""


def detect_document_type(text):
    upper = (text or "").upper()
    folded = ascii_fold(text).upper()
    checks = [
        ("Nghị định", ["NGHỊ ĐỊNH", "NGHI DINH", "ND-CP", "NĐ-CP"]),
        ("Thông tư", ["THÔNG TƯ", "THONG TU", "TT-BTC", "TT-BCT"]),
        ("Luật", ["LUẬT", "LUAT"]),
        ("Quyết định", ["QUYẾT ĐỊNH", "QUYET DINH"]),
        ("Công văn", ["CÔNG VĂN", "CONG VAN"]),
        ("Official Letter", ["OFFICIAL LETTER"]),
    ]
    for label, markers in checks:
        if any(marker in upper or marker in folded for marker in markers):
            return label
    return "Other"


def detect_authority(text):
    authorities = {
        "CHINH PHU": "CHÍNH PHỦ",
        "BO TAI CHINH": "BỘ TÀI CHÍNH",
        "BO CONG THUONG": "BỘ CÔNG THƯƠNG",
        "BO THONG TIN VA TRUYEN THONG": "BỘ THÔNG TIN VÀ TRUYỀN THÔNG",
        "TONG CUC HAI QUAN": "TỔNG CỤC HẢI QUAN",
        "BO Y TE": "BỘ Y TẾ",
        "BO NONG NGHIEP VA MOI TRUONG": "BỘ NÔNG NGHIỆP VÀ MÔI TRƯỜNG",
    }
    folded = ascii_fold(text).upper()
    for marker, label in authorities.items():
        if marker in folded:
            return label
    return ""


def contains_any_folded(text, markers):
    folded = ascii_fold(text)
    return any(ascii_fold(marker) in folded for marker in markers)


def matching_terms(text, terms):
    folded = ascii_fold(text)
    return [
        term
        for term in terms
        if ascii_fold(term) in folded
    ]


def suggest_category_and_tags(text):
    rules = [
        ("Import Compliance", ["xuất khẩu", "nhập khẩu", "giấy phép", "quản lý chuyên ngành"], ["customs"]),
        ("Customs", ["hải quan", "trị giá", "khai báo", "mã hs"], ["customs", "customs valuation"]),
        ("Civil Cryptography", ["mật mã dân sự", "an toàn thông tin", "sản phẩm mật mã"], ["civil cryptography"]),
        ("Food / Quarantine", ["thực phẩm", "attp", "kiểm dịch"], ["food", "animal quarantine"]),
        ("DG / Battery", ["pin lithium", "hàng nguy hiểm", "un3480"], ["DG", "battery"]),
        ("Origin / C/O", ["c/o", "xuất xứ", "ưu đãi thuế"], ["CO"]),
    ]
    categories = []
    tags = []
    for category, markers, rule_tags in rules:
        if contains_any_folded(text, markers):
            categories.append(category)
            tags.extend(rule_tags)
    return {
        "category": categories[0] if categories else "Import Compliance",
        "tags": sorted(set(tags)) if tags else ["customs"],
    }


def detect_title(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    authority_markers = [
        "CHINH PHU",
        "BO TAI CHINH",
        "BO CONG THUONG",
        "BO THONG TIN VA TRUYEN THONG",
        "TONG CUC HAI QUAN",
        "BO Y TE",
        "BO NONG NGHIEP VA MOI TRUONG",
    ]
    for idx, line in enumerate(lines[:30]):
        folded = ascii_fold(line).upper()
        if any(marker in folded for marker in ["NGHI DINH", "THONG TU", "LUAT", "QUYET DINH", "CONG VAN"]):
            for next_line in lines[idx + 1 : idx + 6]:
                next_folded = ascii_fold(next_line).upper()
                if (
                    len(next_line) > 8
                    and not next_folded.startswith("SO")
                    and not any(marker in next_folded for marker in authority_markers)
                    and not any(marker in next_folded for marker in ["HA NOI", "NGAY "])
                ):
                    return f"{line} - {next_line}"
            return line
    for line in lines[:30]:
        if len(line) > 20 and not ascii_fold(line).startswith("so"):
            return line
    return lines[0] if lines else ""


def generate_rule_based_summary(title, text):
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text or "") if item.strip()]
    relevant = []
    keywords = ["nhập khẩu", "xuất khẩu", "hải quan", "giấy phép", "quản lý chuyên ngành", "mật mã", "hiệu lực"]
    for paragraph in paragraphs:
        if contains_any_folded(paragraph, keywords):
            relevant.append(paragraph)
        if len(relevant) >= 2:
            break
    if not relevant:
        relevant = paragraphs[:2]
    return "\n\n".join([title, *relevant]).strip()[:1600]


def extract_key_clauses(text):
    important_terms = [
        "cấm",
        "phải",
        "được phép",
        "giấy phép",
        "điều kiện",
        "hồ sơ",
        "thủ tục",
        "kiểm tra chuyên ngành",
        "quản lý chuyên ngành",
        "nhập khẩu",
        "xuất khẩu",
    ]
    article_pattern = re.compile(r"(?=(Điều\s+\d+\.|Dieu\s+\d+\.|Article\s+\d+\.))", flags=re.IGNORECASE)
    parts = [part.strip() for part in article_pattern.split(text or "") if part.strip()]
    clauses = []
    index = 0
    while index < len(parts):
        heading = parts[index]
        content = parts[index + 1] if index + 1 < len(parts) else heading
        if re.match(r"^(Điều|Dieu|Article)\s+\d+\.", heading, flags=re.IGNORECASE):
            article_no = first_regex(r"^(?:Điều|Dieu|Article)\s+(\d+)", heading)
            combined = f"{heading}\n{content}".strip()
            matched = matching_terms(combined, important_terms)
            if matched:
                clauses.append(
                    {
                        "article_no": article_no,
                        "clause_no": first_regex(r"^\s*(\d+)\.", content),
                        "heading": heading[:240],
                        "content": combined[:3000],
                        "keywords": ", ".join(matched),
                        "status": "pending_review",
                    }
                )
            index += 2
        else:
            index += 1
    if clauses:
        return clauses[:12]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    for paragraph in paragraphs:
        matched = matching_terms(paragraph, important_terms)
        if matched:
            clauses.append(
                {
                    "article_no": "",
                    "clause_no": "",
                    "heading": paragraph[:120],
                    "content": paragraph[:3000],
                    "keywords": ", ".join(matched),
                    "status": "pending_review",
                }
            )
        if len(clauses) >= 12:
            break
    return clauses


def parse_legal_document_text(text, filename=""):
    body = text or ""
    title = detect_title(body) or Path(filename).stem
    document_no = first_regex(r"(?:Số|So|No\.)\s*:?\s*([0-9A-Za-zĐđ/\-.]+)", body)
    document_type = detect_document_type(body)
    authority = detect_authority(body)
    folded_body = ascii_fold(body)
    issue_raw = first_regex(r"(ngay\s+\d{1,2}\s+thang\s+\d{1,2}\s+nam\s+\d{4})", folded_body)
    if not issue_raw:
        issue_raw = first_regex(r"\b(\d{1,2}/\d{1,2}/\d{4})\b", body)
    if not issue_raw:
        issue_raw = first_regex(r"\b(\d{4}-\d{2}-\d{2})\b", body)
    effective_raw = first_regex(r"(?:co hieu luc(?: thi hanh)? tu ngay|takes effect from)\s*([^\n.;]+)", folded_body)
    expiry_raw = first_regex(r"(?:het hieu luc|thay the|bai bo|replaced by|repealed by)\s*([^\n.;]+)", folded_body)
    suggestions = suggest_category_and_tags(body)
    chunks = extract_key_clauses(body)
    return {
        "title": title,
        "document_no": document_no,
        "document_type": document_type,
        "issuing_authority": authority,
        "issue_date": normalize_date(issue_raw),
        "effective_date": normalize_date(effective_raw),
        "expiry_date": normalize_date(expiry_raw),
        "status": "Active" if not expiry_raw else "Replaced",
        "category": suggestions["category"],
        "source_url": "",
        "file_path": "",
        "summary": generate_rule_based_summary(title, body),
        "content": body[:12000],
        "article_no": chunks[0]["article_no"] if chunks else "",
        "clause_no": chunks[0]["clause_no"] if chunks else "",
        "keywords": ", ".join(suggestions["tags"]),
        "tags": suggestions["tags"],
        "chunks": chunks,
        "extraction_error": "",
    }


def search_documents(keyword="", document_no="", authority="", category="", limit=100):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM knowledge_documents
        WHERE (? = '' OR LOWER(title || ' ' || COALESCE(summary, '')) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(document_no, '')) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(issuing_authority, '')) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(category, '')) LIKE LOWER(?))
        ORDER BY COALESCE(effective_date, issue_date, created_at) DESC, id DESC
        LIMIT ?
        """,
        (
            clean(keyword),
            like_query(keyword),
            clean(document_no),
            like_query(document_no),
            clean(authority),
            like_query(authority),
            clean(category),
            like_query(category),
            int(limit or 100),
        ),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def search_chunks(keyword="", limit=20):
    if not clean(keyword):
        return []
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            knowledge_chunks.*,
            knowledge_documents.title AS document_title,
            knowledge_documents.document_no,
            knowledge_documents.document_type,
            knowledge_documents.issuing_authority,
            knowledge_documents.effective_date
        FROM knowledge_chunks
        LEFT JOIN knowledge_documents ON knowledge_documents.id = knowledge_chunks.document_id
        WHERE LOWER(
            COALESCE(knowledge_chunks.heading, '') || ' ' ||
            COALESCE(knowledge_chunks.content, '') || ' ' ||
            COALESCE(knowledge_chunks.keywords, '') || ' ' ||
            COALESCE(knowledge_documents.title, '') || ' ' ||
            COALESCE(knowledge_documents.document_no, '')
        ) LIKE LOWER(?)
            AND COALESCE(knowledge_chunks.status, 'Approved') = 'Approved'
        ORDER BY knowledge_chunks.id DESC
        LIMIT ?
        """,
        (like_query(keyword), int(limit or 20)),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_document(record, chunks=None, tag_names=None, document_id=None):
    conn = get_connection()
    cur = conn.cursor()
    fields = [
        "title",
        "document_no",
        "document_type",
        "issuing_authority",
        "issue_date",
        "effective_date",
        "expiry_date",
        "status",
        "category",
        "source_url",
        "file_path",
        "summary",
    ]
    values = [clean(record.get(field)) for field in fields]
    if document_id:
        cur.execute(
            """
            UPDATE knowledge_documents
            SET title = ?, document_no = ?, document_type = ?, issuing_authority = ?,
                issue_date = ?, effective_date = ?, expiry_date = ?, status = ?,
                category = ?, source_url = ?, file_path = ?, summary = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (*values, document_id),
        )
        saved_id = document_id
    else:
        cur.execute(
            """
            INSERT INTO knowledge_documents (
                title, document_no, document_type, issuing_authority, issue_date,
                effective_date, expiry_date, status, category, source_url, file_path,
                summary, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            values,
        )
        saved_id = cur.lastrowid

    for chunk in chunks or []:
        if not clean(chunk.get("content")):
            continue
        cur.execute(
            """
            INSERT INTO knowledge_chunks (
                document_id, article_no, clause_no, heading, content, keywords, embedding, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                saved_id,
                clean(chunk.get("article_no")),
                clean(chunk.get("clause_no")),
                clean(chunk.get("heading")),
                clean(chunk.get("content")),
                clean(chunk.get("keywords")),
                clean(chunk.get("embedding")),
                clean(chunk.get("status")) or "Approved",
            ),
        )

    for tag_name in tag_names or []:
        name = clean(tag_name)
        if not name:
            continue
        cur.execute("INSERT OR IGNORE INTO knowledge_tags (name) VALUES (?)", (name,))
        tag = cur.execute("SELECT id FROM knowledge_tags WHERE name = ?", (name,)).fetchone()
        if tag:
            cur.execute(
                "INSERT OR IGNORE INTO knowledge_document_tags (document_id, tag_id) VALUES (?, ?)",
                (saved_id, tag["id"]),
            )

    conn.commit()
    conn.close()
    return saved_id


def search_sops(keyword="", category="", status="", limit=100):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM knowledge_sops
        WHERE (? = '' OR LOWER(title || ' ' || COALESCE(purpose, '') || ' ' || COALESCE(procedure_steps, '') || ' ' || COALESCE(checklist, '')) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(category, '')) LIKE LOWER(?))
            AND (? = '' OR COALESCE(status, '') = ?)
        ORDER BY updated_at DESC, id DESC
        LIMIT ?
        """,
        (clean(keyword), like_query(keyword), clean(category), like_query(category), clean(status), clean(status), int(limit or 100)),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_sop(record, sop_id=None):
    conn = get_connection()
    cur = conn.cursor()
    values = (
        clean(record.get("title")),
        clean(record.get("purpose")),
        clean(record.get("procedure_steps")),
        clean(record.get("checklist")),
        clean(record.get("related_documents")),
        clean(record.get("related_cases")),
        clean(record.get("category")),
        clean(record.get("status")) or "Active",
        clean(record.get("created_by")) or "admin",
    )
    if sop_id:
        cur.execute(
            """
            UPDATE knowledge_sops
            SET title = ?, purpose = ?, procedure_steps = ?, checklist = ?,
                related_documents = ?, related_cases = ?, category = ?, status = ?,
                created_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (*values, sop_id),
        )
        saved_id = sop_id
    else:
        cur.execute(
            """
            INSERT INTO knowledge_sops (
                title, purpose, procedure_steps, checklist, related_documents,
                related_cases, category, status, created_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            values,
        )
        saved_id = cur.lastrowid
    conn.commit()
    conn.close()
    return saved_id


def search_cases(keyword="", customer="", commodity="", hs_code="", country="", limit=100):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM knowledge_cases
        WHERE (? = '' OR LOWER(title || ' ' || COALESCE(problem, '') || ' ' || COALESCE(solution, '') || ' ' || COALESCE(legal_basis, '') || ' ' || COALESCE(risk_notes, '')) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(customer, '')) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(commodity, '')) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(hs_code, '')) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(country, '')) LIKE LOWER(?))
        ORDER BY updated_at DESC, id DESC
        LIMIT ?
        """,
        (
            clean(keyword),
            like_query(keyword),
            clean(customer),
            like_query(customer),
            clean(commodity),
            like_query(commodity),
            clean(hs_code),
            like_query(hs_code),
            clean(country),
            like_query(country),
            int(limit or 100),
        ),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_case(record, case_id=None):
    conn = get_connection()
    cur = conn.cursor()
    values = (
        clean(record.get("title")),
        clean(record.get("customer")),
        clean(record.get("commodity")),
        clean(record.get("hs_code")),
        clean(record.get("country")),
        clean(record.get("problem")),
        clean(record.get("solution")),
        clean(record.get("legal_basis")),
        clean(record.get("risk_notes")),
        clean(record.get("attachments")),
        clean(record.get("created_by")) or "admin",
    )
    if case_id:
        cur.execute(
            """
            UPDATE knowledge_cases
            SET title = ?, customer = ?, commodity = ?, hs_code = ?, country = ?,
                problem = ?, solution = ?, legal_basis = ?, risk_notes = ?,
                attachments = ?, created_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (*values, case_id),
        )
        saved_id = case_id
    else:
        cur.execute(
            """
            INSERT INTO knowledge_cases (
                title, customer, commodity, hs_code, country, problem, solution,
                legal_basis, risk_notes, attachments, created_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            values,
        )
        saved_id = cur.lastrowid
    conn.commit()
    conn.close()
    return saved_id


INTELLIGENCE_TYPES = [
    "Lessons Learned",
    "Market Intelligence",
    "Vendor Intelligence",
    "Customer Intelligence",
    "Shipment History Intelligence",
]


def search_intelligence(keyword="", intelligence_type="", country="", entity_name="", tags="", limit=100):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM knowledge_intelligence
        WHERE (? = '' OR LOWER(
                title || ' ' ||
                COALESCE(summary, '') || ' ' ||
                COALESCE(details, '') || ' ' ||
                COALESCE(source, '') || ' ' ||
                COALESCE(tags, '')
            ) LIKE LOWER(?))
            AND (? = '' OR COALESCE(intelligence_type, '') = ?)
            AND (? = '' OR LOWER(COALESCE(country, '')) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(entity_name, '')) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(tags, '')) LIKE LOWER(?))
            AND COALESCE(status, 'Active') = 'Active'
        ORDER BY updated_at DESC, id DESC
        LIMIT ?
        """,
        (
            clean(keyword),
            like_query(keyword),
            clean(intelligence_type),
            clean(intelligence_type),
            clean(country),
            like_query(country),
            clean(entity_name),
            like_query(entity_name),
            clean(tags),
            like_query(tags),
            int(limit or 100),
        ),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_intelligence(record, intelligence_id=None):
    conn = get_connection()
    cur = conn.cursor()
    values = (
        clean(record.get("intelligence_type")) or "Lessons Learned",
        clean(record.get("title")),
        clean(record.get("entity_name")),
        clean(record.get("country")),
        clean(record.get("lane")),
        clean(record.get("commodity")),
        clean(record.get("hs_code")),
        clean(record.get("summary")),
        clean(record.get("details")),
        clean(record.get("source")),
        clean(record.get("source_type")),
        record.get("source_id") or None,
        clean(record.get("confidence")) or "Medium",
        clean(record.get("tags")),
        clean(record.get("status")) or "Active",
        clean(record.get("created_by")) or "admin",
    )
    if intelligence_id:
        cur.execute(
            """
            UPDATE knowledge_intelligence
            SET intelligence_type = ?, title = ?, entity_name = ?, country = ?,
                lane = ?, commodity = ?, hs_code = ?, summary = ?, details = ?,
                source = ?, source_type = ?, source_id = ?, confidence = ?, tags = ?, status = ?, created_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (*values, intelligence_id),
        )
        saved_id = intelligence_id
    else:
        cur.execute(
            """
            INSERT INTO knowledge_intelligence (
                intelligence_type, title, entity_name, country, lane, commodity,
                hs_code, summary, details, source, source_type, source_id, confidence, tags, status,
                created_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            values,
        )
        saved_id = cur.lastrowid
    conn.commit()
    conn.close()
    return saved_id


def retrieve_context(question, limit=5):
    query = clean(question)
    return {
        "cases": search_cases(keyword=query, limit=limit),
        "sops": search_sops(keyword=query, limit=limit),
        "documents": search_documents(keyword=query, limit=limit),
        "chunks": search_chunks(keyword=query, limit=limit),
        "intelligence": search_intelligence(keyword=query, limit=limit),
    }


def generate_answer(question):
    context = retrieve_context(question)
    evidence_count = sum(len(context[key]) for key in context)
    if evidence_count == 0:
        return {
            "conclusion": "Insufficient information in knowledge base.",
            "legal_basis": "",
            "relevant_documents": [],
            "applicable_sops": [],
            "related_cases": [],
            "intelligence": [],
            "risk_notes": "No supporting evidence was found. Do not provide legal or compliance advice from memory.",
            "confidence": "Low",
            "context": context,
        }

    documents = context["documents"] + [
        {
            "title": chunk.get("document_title"),
            "document_no": chunk.get("document_no"),
            "issuing_authority": chunk.get("issuing_authority"),
            "effective_date": chunk.get("effective_date"),
        }
        for chunk in context["chunks"]
        if chunk.get("document_title")
    ]
    cases = context["cases"]
    sops = context["sops"]
    intelligence = context["intelligence"]
    legal_basis = "\n".join(
        item for item in [*(case.get("legal_basis") or "" for case in cases), *(chunk.get("content") or "" for chunk in context["chunks"])] if item
    )
    intelligence_notes = "\n".join(
        f"{item.get('intelligence_type')}: {item.get('title')} - {item.get('summary') or item.get('details') or ''}"
        for item in intelligence
    )
    risk_notes = "\n".join(
        item
        for item in [
            *(case.get("risk_notes") or "" for case in cases),
            intelligence_notes,
        ]
        if item
    )

    return {
        "conclusion": "Supporting knowledge was found. Review the evidence below before advising customer.",
        "legal_basis": legal_basis,
        "relevant_documents": documents,
        "applicable_sops": sops,
        "related_cases": cases,
        "intelligence": intelligence,
        "risk_notes": risk_notes or "Review applicability, HS code, model details, and current effective date before using this answer.",
        "confidence": "Medium" if legal_basis else "Low",
        "context": context,
    }
