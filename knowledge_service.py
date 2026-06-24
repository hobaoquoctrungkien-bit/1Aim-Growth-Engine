import re
import json
import unicodedata
from datetime import datetime
from pathlib import Path

from database import get_connection

UPLOAD_DIR = Path("data/knowledge_uploads")
APPROVED_STATUSES = ("Approved", "Active")


def clean(value):
    return "" if value is None else str(value).strip()


def like_query(text):
    return f"%{clean(text)}%"


def approved_sql(column="approval_status"):
    return f"COALESCE({column}, 'Approved') IN ('Approved', 'Active')"


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
        WHERE (? = '' OR LOWER(
                title || ' ' ||
                COALESCE(document_no, '') || ' ' ||
                COALESCE(document_type, '') || ' ' ||
                COALESCE(issuing_authority, '') || ' ' ||
                COALESCE(category, '') || ' ' ||
                COALESCE(summary, '') || ' ' ||
                COALESCE(extracted_text, '')
            ) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(document_no, '')) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(issuing_authority, '')) LIKE LOWER(?))
            AND (? = '' OR LOWER(COALESCE(category, '')) LIKE LOWER(?))
            AND LOWER(COALESCE(approval_status, 'Approved')) = 'approved'
            AND COALESCE(metadata_review_status, 'needs_review') = 'admin_verified'
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
            knowledge_documents.effective_date,
            knowledge_documents.metadata_review_status
        FROM knowledge_chunks
        LEFT JOIN knowledge_documents ON knowledge_documents.id = knowledge_chunks.document_id
        WHERE LOWER(
            COALESCE(knowledge_chunks.heading, '') || ' ' ||
            COALESCE(knowledge_chunks.content, '') || ' ' ||
            COALESCE(knowledge_chunks.keywords, '') || ' ' ||
            COALESCE(knowledge_documents.title, '') || ' ' ||
            COALESCE(knowledge_documents.document_no, '') || ' ' ||
            COALESCE(knowledge_documents.extracted_text, '')
        ) LIKE LOWER(?)
            AND COALESCE(knowledge_chunks.status, 'Approved') = 'Approved'
            AND LOWER(COALESCE(knowledge_documents.approval_status, 'Approved')) = 'approved'
            AND COALESCE(knowledge_documents.metadata_review_status, 'needs_review') = 'admin_verified'
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
        "related_product_group",
        "approval_status",
        "extracted_text",
        "parser_raw_json",
        "parser_provider",
        "parser_confidence",
        "parser_warnings",
        "metadata_review_status",
    ]
    values = []
    for field in fields:
        value = clean(record.get(field))
        if field == "approval_status" and not value:
            value = "Approved"
        if field == "metadata_review_status" and not value:
            value = "needs_review"
        values.append(value)
    if document_id:
        cur.execute(
            """
            UPDATE knowledge_documents
            SET title = ?, document_no = ?, document_type = ?, issuing_authority = ?,
                issue_date = ?, effective_date = ?, expiry_date = ?, status = ?,
                category = ?, source_url = ?, file_path = ?, summary = ?,
                related_product_group = ?, approval_status = ?, extracted_text = ?,
                parser_raw_json = ?, parser_provider = ?, parser_confidence = ?,
                parser_warnings = ?, metadata_review_status = ?,
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
                summary, related_product_group, approval_status, extracted_text,
                parser_raw_json, parser_provider, parser_confidence, parser_warnings,
                metadata_review_status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
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
            AND COALESCE(approval_status, 'Approved') IN ('Approved', 'Active')
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
        clean(record.get("approval_status")) or "Approved",
        clean(record.get("created_by")) or "admin",
    )
    if sop_id:
        cur.execute(
            """
            UPDATE knowledge_sops
            SET title = ?, purpose = ?, procedure_steps = ?, checklist = ?,
                related_documents = ?, related_cases = ?, category = ?, status = ?,
                approval_status = ?, created_by = ?, updated_at = CURRENT_TIMESTAMP
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
                related_cases, category, status, approval_status, created_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
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
            AND COALESCE(approval_status, 'Approved') IN ('Approved', 'Active')
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
        clean(record.get("approval_status")) or "Approved",
        clean(record.get("created_by")) or "admin",
    )
    if case_id:
        cur.execute(
            """
            UPDATE knowledge_cases
            SET title = ?, customer = ?, commodity = ?, hs_code = ?, country = ?,
                problem = ?, solution = ?, legal_basis = ?, risk_notes = ?,
                attachments = ?, approval_status = ?, created_by = ?, updated_at = CURRENT_TIMESTAMP
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
                legal_basis, risk_notes, attachments, approval_status, created_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            values,
        )
        saved_id = cur.lastrowid
    conn.commit()
    conn.close()
    return saved_id


INTELLIGENCE_TYPES = [
    "Compliance Note",
    "Lessons Learned",
    "Market Intelligence",
    "Vendor Intelligence",
    "Customer Intelligence",
    "Shipment History Intelligence",
]


def get_compliance_product_groups(active_only=True):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM compliance_product_groups
        WHERE (? = 0 OR COALESCE(status, 'Active') = 'Active')
        ORDER BY code
        """,
        (1 if active_only else 0,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_compliance_product_group(code="SP_MMDS"):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT *
        FROM compliance_product_groups
        WHERE code = ?
        """,
        (clean(code),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_compliance_keywords(product_group_code="SP_MMDS"):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT compliance_keywords.*
        FROM compliance_keywords
        JOIN compliance_product_groups ON compliance_product_groups.id = compliance_keywords.product_group_id
        WHERE compliance_product_groups.code = ?
        ORDER BY keyword_type, keyword
        """,
        (clean(product_group_code),),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_compliance_rule(record, rule_id=None):
    conn = get_connection()
    cur = conn.cursor()
    values = (
        record.get("product_group_id") or None,
        clean(record.get("rule_title")),
        clean(record.get("rule_type")),
        record.get("legal_document_id") or None,
        clean(record.get("article_no")),
        clean(record.get("clause_no")),
        clean(record.get("appendix_no")),
        clean(record.get("table_no")),
        clean(record.get("content")),
        clean(record.get("required_documents")),
        clean(record.get("managing_authority")),
        clean(record.get("effective_date")),
        clean(record.get("approval_status")) or "pending_review",
        clean(record.get("confidence_score")) or "Medium",
        record.get("source_chunk_id") or None,
    )
    if rule_id:
        cur.execute(
            """
            UPDATE compliance_rules
            SET product_group_id = ?, rule_title = ?, rule_type = ?, legal_document_id = ?,
                article_no = ?, clause_no = ?, appendix_no = ?, table_no = ?, content = ?,
                required_documents = ?, managing_authority = ?, effective_date = ?,
                approval_status = ?, confidence_score = ?, source_chunk_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (*values, rule_id),
        )
        saved_id = rule_id
    else:
        cur.execute(
            """
            INSERT INTO compliance_rules (
                product_group_id, rule_title, rule_type, legal_document_id, article_no,
                clause_no, appendix_no, table_no, content, required_documents,
                managing_authority, effective_date, approval_status, confidence_score, source_chunk_id,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            values,
        )
        saved_id = cur.lastrowid
    conn.commit()
    conn.close()
    return saved_id


def update_compliance_rule_status(rule_id, approval_status):
    conn = get_connection()
    conn.execute(
        """
        UPDATE compliance_rules
        SET approval_status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (clean(approval_status), rule_id),
    )
    conn.commit()
    conn.close()


def get_document_chunks(document_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM knowledge_chunks
        WHERE document_id = ?
        ORDER BY id
        """,
        (document_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


COMPLIANCE_RULE_PATTERNS = [
    ("Import License Required", "Permit Requirement", ["giay phep", "import license", "license", "permit", "nhap khau"]),
    ("Export License Required", "Permit Requirement", ["giay phep", "export license", "xuat khau"]),
    ("Specialized Inspection Required", "Specialized Inspection", ["kiem tra chuyen nganh", "kiem tra chat luong", "quality inspection"]),
    ("Conformity Certification Required", "Certification", ["chung nhan", "cong bo hop quy", "certification", "conformity"]),
    ("Product Listed Under Specialized Management", "Specialized Management", ["quan ly chuyen nganh", "danh muc san pham", "specialized management"]),
    ("Notification Requirement", "Notification", ["thong bao", "notification"]),
    ("Permit Requirement", "Permit Requirement", ["giay phep", "permit"]),
    ("Restricted Product", "Restriction", ["cam", "han che", "restricted", "prohibited"]),
    ("Exempted Product", "Exemption", ["mien tru", "ngoai le", "exempt", "exception"]),
    ("Business Condition Required", "Business Condition", ["dieu kien kinh doanh", "business condition"]),
]


def classify_compliance_rule(content):
    folded = ascii_fold(content)
    for title, rule_type, terms in COMPLIANCE_RULE_PATTERNS:
        if any(ascii_fold(term) in folded for term in terms):
            return title, rule_type
    return "Compliance Requirement", "General Requirement"


def generate_compliance_rule_candidates(parsed_document, product_group_code="SP_MMDS"):
    parsed = parsed_document or {}
    chunks = parsed.get("key_clauses") or parsed.get("chunks") or []
    candidates = []
    seen = set()
    for chunk in chunks:
        content = clean(chunk.get("content"))
        if not content:
            continue
        title, rule_type = classify_compliance_rule(content)
        if title == "Compliance Requirement":
            continue
        dedupe_key = (title, chunk.get("article_no") or "", chunk.get("clause_no") or "", content[:120])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        required_documents = []
        folded = ascii_fold(content)
        if "giay phep" in folded or "permit" in folded or "license" in folded:
            required_documents.append("Permit / license dossier if applicable")
        if "chung nhan" in folded or "cong bo hop quy" in folded or "certification" in folded:
            required_documents.append("Certificate / conformity declaration if applicable")
        if "kiem tra" in folded:
            required_documents.append("Specialized inspection registration if applicable")
        candidates.append(
            {
                "product_group_code": product_group_code,
                "rule_title": title,
                "rule_type": rule_type,
                "article_no": clean(chunk.get("article_no")),
                "clause_no": clean(chunk.get("clause_no")),
                "appendix_no": clean(chunk.get("appendix_no")),
                "table_no": clean(chunk.get("table_no")),
                "content": content,
                "required_documents": "\n".join(required_documents),
                "managing_authority": clean(parsed.get("issuing_authority")),
                "effective_date": clean(parsed.get("effective_date")),
                "approval_status": "pending_review",
                "confidence_score": parsed.get("confidence_score") or "Medium",
            }
        )
    return candidates[:20]


def _match_source_chunk(chunks, candidate):
    article = clean(candidate.get("article_no"))
    clause = clean(candidate.get("clause_no"))
    content = clean(candidate.get("content"))
    for chunk in chunks:
        if article and article != clean(chunk.get("article_no")):
            continue
        if clause and clause != clean(chunk.get("clause_no")):
            continue
        chunk_content = clean(chunk.get("content"))
        if content and (content[:160] in chunk_content or chunk_content[:160] in content):
            return chunk.get("id")
    for chunk in chunks:
        chunk_content = clean(chunk.get("content"))
        if content and (content[:160] in chunk_content or chunk_content[:160] in content):
            return chunk.get("id")
    return None


def save_candidate_compliance_rules(document_id, product_group_code, candidates):
    group = get_compliance_product_group(product_group_code)
    if not group:
        return []
    chunks = get_document_chunks(document_id)
    saved_ids = []
    for candidate in candidates or []:
        record = {
            **candidate,
            "product_group_id": group.get("id"),
            "legal_document_id": document_id,
            "source_chunk_id": _match_source_chunk(chunks, candidate),
            "approval_status": candidate.get("approval_status") or "pending_review",
        }
        saved_ids.append(save_compliance_rule(record))
    return saved_ids


def save_compliance_note(record, note_id=None):
    conn = get_connection()
    cur = conn.cursor()
    values = (
        clean(record.get("title")),
        clean(record.get("topic")),
        record.get("product_group_id") or None,
        clean(record.get("summary")),
        clean(record.get("interpretation")),
        clean(record.get("operational_guidance")),
        clean(record.get("risk_notes")),
        clean(record.get("related_documents")),
        clean(record.get("related_sops")),
        clean(record.get("related_cases")),
        clean(record.get("approval_status")) or "Pending",
        clean(record.get("created_by")) or "admin",
    )
    if note_id:
        cur.execute(
            """
            UPDATE compliance_notes
            SET title = ?, topic = ?, product_group_id = ?, summary = ?, interpretation = ?,
                operational_guidance = ?, risk_notes = ?, related_documents = ?, related_sops = ?,
                related_cases = ?, approval_status = ?, created_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (*values, note_id),
        )
        saved_id = note_id
    else:
        cur.execute(
            """
            INSERT INTO compliance_notes (
                title, topic, product_group_id, summary, interpretation, operational_guidance,
                risk_notes, related_documents, related_sops, related_cases, approval_status,
                created_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            values,
        )
        saved_id = cur.lastrowid
    conn.commit()
    conn.close()
    return saved_id


def search_compliance_rules(product_group_code="SP_MMDS", keyword="", approved_only=True, limit=100):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            cr.*,
            cpg.code AS product_group_code,
            kd.title AS legal_document_title,
            kd.document_no AS legal_document_no,
            kc.heading AS source_heading,
            kc.content AS source_content
        FROM compliance_rules cr
        LEFT JOIN compliance_product_groups cpg ON cpg.id = cr.product_group_id
        LEFT JOIN knowledge_documents kd ON kd.id = cr.legal_document_id
        LEFT JOIN knowledge_chunks kc ON kc.id = cr.source_chunk_id
        WHERE cpg.code = ?
            AND (? = '' OR LOWER(
                COALESCE(cr.rule_title, '') || ' ' ||
                COALESCE(cr.rule_type, '') || ' ' ||
                COALESCE(cr.content, '') || ' ' ||
                COALESCE(cr.required_documents, '') || ' ' ||
                COALESCE(kd.document_no, '')
            ) LIKE LOWER(?))
            AND (? = 0 OR COALESCE(cr.approval_status, 'Approved') = 'Approved')
        ORDER BY COALESCE(cr.effective_date, cr.updated_at) DESC, cr.id DESC
        LIMIT ?
        """,
        (clean(product_group_code), clean(keyword), like_query(keyword), 1 if approved_only else 0, int(limit or 100)),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def search_compliance_notes(product_group_code="SP_MMDS", keyword="", approved_only=True, limit=100):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            compliance_notes.*,
            compliance_product_groups.code AS product_group_code
        FROM compliance_notes
        LEFT JOIN compliance_product_groups ON compliance_product_groups.id = compliance_notes.product_group_id
        WHERE compliance_product_groups.code = ?
            AND (? = '' OR LOWER(
                COALESCE(title, '') || ' ' ||
                COALESCE(topic, '') || ' ' ||
                COALESCE(summary, '') || ' ' ||
                COALESCE(interpretation, '') || ' ' ||
                COALESCE(operational_guidance, '') || ' ' ||
                COALESCE(risk_notes, '')
            ) LIKE LOWER(?))
            AND (? = 0 OR COALESCE(compliance_notes.approval_status, 'Pending') = 'Approved')
        ORDER BY compliance_notes.updated_at DESC, compliance_notes.id DESC
        LIMIT ?
        """,
        (clean(product_group_code), clean(keyword), like_query(keyword), 1 if approved_only else 0, int(limit or 100)),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def search_product_group_documents(product_group_code="SP_MMDS", keyword="", limit=100):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM knowledge_documents
        WHERE COALESCE(approval_status, 'Approved') IN ('Approved', 'Active')
            AND (
                LOWER(COALESCE(related_product_group, '')) LIKE LOWER(?)
                OR LOWER(COALESCE(category, '')) LIKE LOWER(?)
                OR LOWER(COALESCE(summary, '')) LIKE LOWER(?)
                OR LOWER(COALESCE(title, '')) LIKE LOWER(?)
            )
            AND (? = '' OR LOWER(
                COALESCE(title, '') || ' ' ||
                COALESCE(document_no, '') || ' ' ||
                COALESCE(summary, '') || ' ' ||
                COALESCE(category, '')
            ) LIKE LOWER(?))
        ORDER BY COALESCE(effective_date, issue_date, created_at) DESC, id DESC
        LIMIT ?
        """,
        (
            like_query(product_group_code),
            like_query(product_group_code),
            like_query(product_group_code),
            like_query(product_group_code),
            clean(keyword),
            like_query(keyword),
            int(limit or 100),
        ),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def retrieve_compliance_context(question, product_group_code="SP_MMDS", limit=8):
    group = get_compliance_product_group(product_group_code)
    keywords = get_compliance_keywords(product_group_code)
    query = clean(question)
    return {
        "product_group": group,
        "keywords": keywords,
        "legal_documents": search_product_group_documents(product_group_code, "", limit=limit),
        "rules": search_compliance_rules(product_group_code, query, approved_only=True, limit=limit),
        "notes": search_compliance_notes(product_group_code, query, approved_only=True, limit=limit),
        "sops": search_sops(keyword=query, category="", status="Active", limit=limit),
        "cases": search_cases(keyword=query, limit=limit),
        "intelligence": search_intelligence(keyword=query, limit=limit),
    }


def _source_lines(rows, fields):
    lines = []
    for row in rows:
        parts = [clean(row.get(field)) for field in fields if clean(row.get(field))]
        if parts:
            lines.append(" - ".join(parts))
    return lines


def generate_compliance_answer(question, product_group_code="SP_MMDS"):
    context = retrieve_compliance_context(question, product_group_code)
    group = context.get("product_group") or {}
    rules = context.get("rules") or []
    legal_documents = context.get("legal_documents") or []
    notes = context.get("notes") or []
    sops = context.get("sops") or []
    cases = context.get("cases") or []
    intelligence = context.get("intelligence") or []
    if not rules:
        return {
            "conclusion": "Insufficient approved basis in the system.",
            "product_group": group.get("code") or product_group_code,
            "managing_authority": group.get("managing_authority") or "",
            "legal_basis": "",
            "document_number": "",
            "article_clause": "",
            "relevant_compliance_notes": notes,
            "relevant_sops": sops,
            "relevant_cases": cases,
            "required_documents": "",
            "required_actions": "Generate and approve compliance rules from the legal source before advising customer.",
            "risk_notes": "Do not classify product or advise customer from raw legal text without approved compliance rules.",
            "uncertainty": "Approved compliance rule is missing.",
            "recommended_next_step": "Review candidate compliance rules and approve the applicable rule.",
            "sources_used": [],
            "confidence": "Low",
            "context": context,
        }

    rule_lines = _source_lines(rules, ["rule_title", "content"])
    document_lines = _source_lines(legal_documents, ["document_no", "title", "issuing_authority"])
    article_clause = ", ".join(
        line
        for line in _source_lines(rules, ["article_no", "clause_no", "appendix_no", "table_no"])
        if line
    )
    required_documents = "\n".join(row.get("required_documents") or "" for row in rules if row.get("required_documents"))
    note_text = " ".join((row.get("interpretation") or row.get("summary") or "") for row in notes)
    legal_text = " ".join((row.get("content") or row.get("summary") or "") for row in [*rules, *legal_documents])
    conflict_warning = ""
    if note_text and legal_text and "khong can" in ascii_fold(note_text) and "can" in ascii_fold(legal_text):
        conflict_warning = "Internal interpretation conflicts with legal source."
    return {
        "conclusion": "Approved legal basis was found. Use the legal basis first, then review internal guidance before advising customer.",
        "product_group": group.get("code") or product_group_code,
        "managing_authority": group.get("managing_authority") or "",
        "legal_basis": "\n".join([*rule_lines, *document_lines]),
        "document_number": ", ".join(sorted({clean(row.get("legal_document_no") or row.get("document_no")) for row in [*rules, *legal_documents] if clean(row.get("legal_document_no") or row.get("document_no"))})),
        "article_clause": article_clause,
        "relevant_compliance_notes": notes,
        "relevant_sops": sops,
        "relevant_cases": cases,
        "required_documents": required_documents,
        "required_actions": "Confirm exact model, HS code, encryption function, and current effective legal document before final customer advice.",
        "risk_notes": conflict_warning or "Internal notes, SOPs, cases, and shipment experience are interpretation only. Legal documents override them.",
        "uncertainty": "Product classification still requires model/spec review unless the legal source directly covers the exact product.",
        "recommended_next_step": "Attach the legal document/rule to the shipment or quotation file and follow the approved SOP.",
        "sources_used": [
            *[
                {
                    "source_type": "Legal Rule",
                    "title": row.get("rule_title"),
                    "document_no": row.get("legal_document_no"),
                    "article_no": row.get("article_no"),
                    "clause_no": row.get("clause_no"),
                    "source_chunk_id": row.get("source_chunk_id"),
                    "source_content": row.get("source_content"),
                }
                for row in rules
            ],
            *[
                {
                    "source_type": "Legal Document",
                    "title": row.get("title"),
                    "document_no": row.get("document_no"),
                    "article_no": "",
                    "clause_no": "",
                }
                for row in legal_documents
            ],
        ],
        "confidence": "High" if rules else "Medium",
        "context": context,
    }


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
            AND COALESCE(approval_status, 'Approved') IN ('Approved', 'Active')
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
        clean(record.get("approval_status")) or "Approved",
        clean(record.get("created_by")) or "admin",
    )
    if intelligence_id:
        cur.execute(
            """
            UPDATE knowledge_intelligence
            SET intelligence_type = ?, title = ?, entity_name = ?, country = ?,
                lane = ?, commodity = ?, hs_code = ?, summary = ?, details = ?,
                source = ?, source_type = ?, source_id = ?, confidence = ?, tags = ?, status = ?, approval_status = ?, created_by = ?,
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
                approval_status, created_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
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
    legal_evidence_count = len(context.get("documents", [])) + len(context.get("chunks", []))
    if legal_evidence_count == 0:
        return {
            "conclusion": "Insufficient verified legal basis in the system.",
            "legal_basis": "",
            "relevant_documents": [],
            "applicable_sops": [],
            "related_cases": [],
            "intelligence": [],
            "risk_notes": "No admin-verified approved legal document supports this answer. Prefer blank/uncertain over wrong legal basis.",
            "confidence": "Low",
            "context": context,
        }

    documents = context["documents"] + [
        {
            "title": chunk.get("document_title"),
            "document_no": chunk.get("document_no"),
            "issuing_authority": chunk.get("issuing_authority"),
            "effective_date": chunk.get("effective_date"),
            "excerpt": (chunk.get("content") or "")[:900],
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
        "conclusion": "Verified legal basis was found. Review the source excerpt before advising customer.",
        "legal_basis": legal_basis,
        "relevant_documents": documents,
        "applicable_sops": sops,
        "related_cases": cases,
        "intelligence": intelligence,
        "risk_notes": risk_notes or "Review applicability, HS code, model details, and current effective date before using this answer.",
        "confidence": "Medium" if legal_basis else "Low",
        "context": context,
    }
