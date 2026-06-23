import csv
import io
import re
from datetime import date, datetime
from pathlib import Path


INQUIRY_UPLOAD_DIR = Path("data/inquiries")
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clean_multiline(value):
    lines = [line.strip() for line in str(value or "").replace("\r\n", "\n").split("\n")]
    return "\n".join(line for line in lines if line)


def first_match(patterns, text, flags=re.IGNORECASE):
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return clean_text(match.group(1))
    return ""


def parse_email_header(raw_text, header_name):
    pattern = rf"^{re.escape(header_name)}\s*:\s*(.+)$"
    return first_match([pattern], raw_text, flags=re.IGNORECASE | re.MULTILINE)


def parse_sender_name(raw_text):
    sender = parse_email_header(raw_text, "From")
    if not sender:
        return ""
    sender = re.sub(r"<[^>]+>", "", sender).strip()
    sender = re.sub(r"['\"]", "", sender).strip()
    return sender


def detect_service_type(text):
    lowered = text.lower()
    if any(term in lowered for term in ["air freight", "air shipment", "by air", "airport"]):
        return "Air Freight"
    if any(term in lowered for term in ["sea freight", "ocean freight", "by sea", "fcl", "lcl", "container"]):
        return "Sea Freight"
    if any(term in lowered for term in ["customs clearance", "custom clearance", "import clearance", "export clearance"]):
        return "Customs Brokerage"
    if any(term in lowered for term in ["trucking", "truck", "road freight", "door delivery", "pickup"]):
        return "Trucking"
    if any(term in lowered for term in ["ddp", "dap", "exw", "fob", "cif"]):
        return "Freight Forwarding"
    return "Freight Forwarding"


def detect_mode(text, service_type):
    lowered = text.lower()
    if "fcl" in lowered:
        return "FCL"
    if "lcl" in lowered:
        return "LCL"
    if service_type == "Air Freight":
        return "Air"
    if service_type == "Sea Freight":
        return "Sea"
    return ""


def detect_trade_lane(text):
    patterns = [
        r"\bfrom\s+([A-Za-z0-9 ,./-]+?)\s+to\s+([A-Za-z0-9 ,./-]+?)(?:[.\n,;]|$)",
        r"\borigin\s*[:：]\s*([A-Za-z0-9 ,./-]+).*?\bdestination\s*[:：]\s*([A-Za-z0-9 ,./-]+)",
        r"\bpol\s*[:：]\s*([A-Za-z0-9 ,./-]+).*?\bpod\s*[:：]\s*([A-Za-z0-9 ,./-]+)",
        r"\bpick\s*up\s*[:：]\s*([A-Za-z0-9 ,./-]+).*?\bdeliver(?:y)?\s*[:：]\s*([A-Za-z0-9 ,./-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            origin = clean_text(match.group(1)).strip(" ,;.-")
            destination = clean_text(match.group(2)).strip(" ,;.-")
            if origin and destination:
                return f"{origin} -> {destination}"
    return ""


def detect_origin_destination(text):
    origin = first_match(
        [
            r"\borigin\s*[:：]\s*(.+?)(?:\n|$)",
            r"\bpol\s*[:：]\s*(.+?)(?:\n|$)",
            r"\bfrom\s+(.+?)\s+to\s+.+?(?:[.\n,;]|$)",
            r"\bpick\s*up\s*[:：]\s*(.+?)(?:\n|$)",
        ],
        text,
    )
    destination = first_match(
        [
            r"\bdestination\s*[:：]\s*(.+?)(?:\n|$)",
            r"\bpod\s*[:：]\s*(.+?)(?:\n|$)",
            r"\bfrom\s+.+?\s+to\s+(.+?)(?:[.\n,;]|$)",
            r"\bdeliver(?:y)?\s*[:：]\s*(.+?)(?:\n|$)",
        ],
        text,
    )
    return origin.strip(" ,;.-"), destination.strip(" ,;.-")


def detect_commodity(text):
    return first_match(
        [
            r"\bcommodity\s*[:：]\s*(.+?)(?:\n|$)",
            r"\bcargo\s*[:：]\s*(.+?)(?:\n|$)",
            r"\bgoods\s*[:：]\s*(.+?)(?:\n|$)",
            r"\bdescription\s*[:：]\s*(.+?)(?:\n|$)",
        ],
        text,
    )


def detect_volume(text):
    patterns = [
        r"\b(\d+\s*x\s*\d+\s*(?:gp|hc|dv|rf|ft|feet|container)s?)\b",
        r"\b(\d+\s*(?:x\s*)?(?:20|40|45)\s*(?:gp|hc|dv|rf|ft|feet|container)s?)\b",
        r"\b(\d+(?:\.\d+)?\s*(?:cbm|m3|kgs?|kg|tons?|ctns?|cartons?|pallets?|pkgs?))\b",
        r"\b(?:volume|weight|quantity)\s*[:：]\s*(.+?)(?:\n|$)",
    ]
    return first_match(patterns, text)


def detect_weight(text):
    return first_match(
        [
            r"\bweight\s*[:：]\s*(.+?)(?:\n|$)",
            r"\b(gross weight\s*[:：]\s*.+?)(?:\n|$)",
            r"\b(\d+(?:\.\d+)?\s*(?:kgs?|kg|tons?|tonnes?))\b",
        ],
        text,
    )


def detect_container_type(text):
    return first_match(
        [
            r"\bcontainer\s*(?:type)?\s*[:：]\s*(.+?)(?:\n|$)",
            r"\b(\d+\s*x\s*(?:20|40|45)\s*(?:gp|hc|dv|rf|ft|feet|container)s?)\b",
            r"\b((?:20|40|45)\s*(?:gp|hc|dv|rf|ft|feet|container))\b",
        ],
        text,
    )


def detect_quantity(text):
    return first_match(
        [
            r"\bquantity\s*[:：]\s*(.+?)(?:\n|$)",
            r"\bqty\s*[:：]\s*(.+?)(?:\n|$)",
            r"\b(\d+\s*(?:ctns?|cartons?|pallets?|pkgs?|packages?|containers?))\b",
        ],
        text,
    )


def detect_incoterm(text):
    match = re.search(r"\b(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b", text, re.IGNORECASE)
    return match.group(1).upper() if match else ""


def detect_deadline(text):
    return first_match(
        [
            r"\b(?:deadline|closing|ready date|cargo ready|etd|eta|date)\s*[:：]\s*(.+?)(?:\n|$)",
            r"\b(?:before|by)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
            r"\b(\d{4}-\d{2}-\d{2})\b",
        ],
        text,
    )


def detect_company(raw_text, sender_name):
    company = first_match(
        [
            r"\bcompany\s*[:：]\s*(.+?)(?:\n|$)",
            r"\borganization\s*[:：]\s*(.+?)(?:\n|$)",
            r"\bcustomer\s*[:：]\s*(.+?)(?:\n|$)",
        ],
        raw_text,
    )
    if company:
        return company

    signature_lines = clean_multiline(raw_text).split("\n")[-8:]
    for line in signature_lines:
        if re.search(r"\b(co\.?|ltd\.?|limited|logistics|freight|shipping|forwarding|transport)\b", line, re.IGNORECASE):
            if sender_name and sender_name.lower() in line.lower():
                continue
            return clean_text(line)
    return ""


def detect_country_city(text):
    country = first_match([r"\bcountry\s*[:：]\s*(.+?)(?:\n|$)"], text)
    city = first_match([r"\bcity\s*[:：]\s*(.+?)(?:\n|$)"], text)
    return country, city


def build_opportunity_name(parsed):
    parts = [
        parsed.get("company_name") or "Inquiry",
        parsed.get("trade_lane"),
        parsed.get("service_type"),
    ]
    return " - ".join(part for part in parts if part)[:120]


def parse_inquiry_text(raw_text, attachment_texts=None):
    raw_text = clean_multiline(raw_text)
    attachment_texts = attachment_texts or []
    combined_text = "\n\n".join([raw_text] + [item.get("text", "") for item in attachment_texts if item.get("text")])
    subject = parse_email_header(raw_text, "Subject")
    sender_name = parse_sender_name(raw_text)
    email_match = EMAIL_PATTERN.search(raw_text)
    phone_match = PHONE_PATTERN.search(raw_text)
    service_type = detect_service_type(combined_text)
    country, city = detect_country_city(combined_text)
    origin, destination = detect_origin_destination(combined_text)
    cargo_description = detect_commodity(combined_text)

    trade_lane = detect_trade_lane(combined_text)
    if not trade_lane and origin and destination:
        trade_lane = f"{origin} -> {destination}"

    parsed = {
        "subject": subject,
        "company_name": detect_company(raw_text, sender_name),
        "organization": detect_company(raw_text, sender_name),
        "contact_person": sender_name,
        "email": email_match.group(0) if email_match else "",
        "phone": clean_text(phone_match.group(0)) if phone_match else "",
        "country": country,
        "city": city,
        "trade_lane": trade_lane,
        "service_type": service_type,
        "mode": detect_mode(combined_text, service_type),
        "commodity": cargo_description,
        "cargo_description": cargo_description,
        "origin": origin,
        "destination": destination,
        "volume": detect_volume(combined_text),
        "weight": detect_weight(combined_text),
        "container_type": detect_container_type(combined_text),
        "quantity": detect_quantity(combined_text),
        "incoterm": detect_incoterm(combined_text),
        "deadline": detect_deadline(combined_text),
        "inquiry_date": date.today().isoformat(),
        "next_action": "Prepare quotation",
        "next_action_date": date.today().isoformat(),
        "raw_text": raw_text,
        "attachment_text": "\n\n".join(
            f"Attachment: {item.get('filename')}\n{item.get('text')}"
            for item in attachment_texts
            if item.get("text")
        ),
    }
    parsed["opportunity_name"] = subject or build_opportunity_name(parsed)
    parsed["notes"] = build_inquiry_notes(parsed, [])
    return parsed


def build_inquiry_notes(parsed, saved_files):
    sections = []
    if parsed.get("user_notes"):
        sections.append("User notes:\n" + parsed["user_notes"])
    if parsed.get("raw_text"):
        sections.append("Original inquiry:\n" + parsed["raw_text"])
    if parsed.get("attachment_text"):
        sections.append("Parsed attachment text:\n" + parsed["attachment_text"])
    if saved_files:
        sections.append("Saved files:\n" + "\n".join(saved_files))
    return "\n\n".join(sections)


def extract_attachment_text(filename, content):
    suffix = Path(filename or "").suffix.lower()
    if not content:
        return ""
    if suffix in [".txt", ".eml", ".csv"]:
        try:
            decoded = content.decode("utf-8", errors="ignore")
            if suffix == ".csv":
                reader = csv.reader(io.StringIO(decoded))
                return "\n".join(" | ".join(cell.strip() for cell in row) for row in reader)
            return decoded
        except Exception:
            return ""
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    if suffix == ".docx":
        try:
            from docx import Document

            document = Document(io.BytesIO(content))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        except Exception:
            return ""
    if suffix in [".xlsx", ".xls"]:
        try:
            import pandas as pd

            sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, dtype=str, header=None)
            output = []
            for sheet_name, dataframe in sheets.items():
                output.append(f"Sheet: {sheet_name}")
                for row in dataframe.fillna("").astype(str).values.tolist():
                    row_text = " | ".join(cell.strip() for cell in row if cell.strip())
                    if row_text:
                        output.append(row_text)
            return "\n".join(output)
        except Exception:
            return ""
    return ""


def safe_filename(filename):
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename or "attachment").name).strip("._")
    return safe or "attachment"


def safe_folder_name(value):
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", clean_text(value)).strip("_")
    return (safe or "inquiry")[:60]


def save_inquiry_files(opportunity_name, files):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = INQUIRY_UPLOAD_DIR / f"{timestamp}_{safe_folder_name(opportunity_name)}"
    folder.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for file_item in files or []:
        filename = safe_filename(file_item.get("filename"))
        target = folder / filename
        stem = target.stem
        suffix = target.suffix
        counter = 1
        while target.exists():
            target = folder / f"{stem}_{counter}{suffix}"
            counter += 1
        target.write_bytes(file_item.get("content") or b"")
        saved_paths.append(str(target))
    return str(folder), saved_paths
