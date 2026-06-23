import re
import unicodedata
from abc import ABC, abstractmethod
from os import environ
from pathlib import Path

from knowledge_service import (
    extract_key_clauses as regex_extract_key_clauses,
    extract_uploaded_text,
    normalize_date,
    parse_legal_document_text,
    search_cases,
    search_sops,
)


DOCUMENT_TYPES = [
    "LAW",
    "DECREE",
    "CIRCULAR",
    "OFFICIAL LETTER",
    "SOP",
    "CASE",
    "INQUIRY",
    "COMMERCIAL INVOICE",
    "PACKING LIST",
    "DATASHEET",
    "PERMIT",
    "BOOKING",
    "SHIPMENT DOCUMENT",
    "OTHER",
]

DEFAULT_FIELDS = {
    "document_type": "",
    "title": "",
    "document_no": "",
    "issuing_authority": "",
    "issue_date": "",
    "effective_date": "",
    "expiry_date": "",
    "category": "",
    "tags": [],
    "summary": "",
    "keywords": [],
    "key_clauses": [],
    "purpose": "",
    "steps": "",
    "checklist": "",
    "risks": "",
    "problem": "",
    "root_cause": "",
    "solution": "",
    "lessons_learned": "",
    "shipper": "",
    "consignee": "",
    "commodity": "",
    "invoice_number": "",
    "invoice_date": "",
    "value": "",
    "currency": "",
    "packages": "",
    "weight": "",
    "volume": "",
    "product_name": "",
    "manufacturer": "",
    "model": "",
    "technical_description": "",
    "permit_number": "",
    "validity_period": "",
    "possible_compliance_topics": [],
    "possible_sop_matches": [],
    "possible_case_matches": [],
    "confidence_score": "Low",
    "field_confidence": {},
    "parser_engine": "fallback",
    "parser_error": "",
    "raw_text": "",
}


def clean(value):
    return "" if value is None else str(value).strip()


class AIParserProvider(ABC):
    name = "base"

    def __init__(self, api_key="", model=""):
        self.api_key = clean(api_key)
        self.model = clean(model)

    def is_configured(self):
        return True

    @abstractmethod
    def parse(self, text, filename=""):
        """Return {"ok": bool, "provider": str, "data": dict, "error": str}."""


class RegexParserProvider(AIParserProvider):
    name = "regex"

    def parse(self, text, filename=""):
        return {
            "ok": True,
            "provider": self.name,
            "data": fallback_parse_document(text, filename=filename),
            "error": "",
        }


class OpenAIParserProvider(AIParserProvider):
    name = "openai"

    def is_configured(self):
        return bool(self.api_key)

    def parse(self, text, filename=""):
        if not self.is_configured():
            return {"ok": False, "provider": self.name, "data": {}, "error": "OpenAI parser is not configured."}
        return {
            "ok": False,
            "provider": self.name,
            "data": {},
            "error": "OpenAI parser provider stub is configured but not implemented yet.",
        }


class GeminiParserProvider(AIParserProvider):
    name = "gemini"

    def is_configured(self):
        return bool(self.api_key)

    def parse(self, text, filename=""):
        if not self.is_configured():
            return {"ok": False, "provider": self.name, "data": {}, "error": "Gemini parser is not configured."}
        return {
            "ok": False,
            "provider": self.name,
            "data": {},
            "error": "Gemini parser provider stub is configured but not implemented yet.",
        }
def fold_text(value):
    normalized = unicodedata.normalize("NFKD", clean(value)).replace("Đ", "D").replace("đ", "d")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def first_regex(pattern, text, flags=re.IGNORECASE):
    match = re.search(pattern, text or "", flags)
    return clean(match.group(1)) if match else ""


def merge_result(base, updates):
    result = {**DEFAULT_FIELDS, **base}
    for key, value in updates.items():
        if key in result:
            result[key] = value
    return result


def confidence_for(value, high=False):
    if not clean(value):
        return "Low"
    return "High" if high else "Medium"


def overall_confidence(field_confidence):
    values = list(field_confidence.values())
    if not values:
        return "Low"
    high = values.count("High")
    medium = values.count("Medium")
    if high >= max(3, len(values) // 2):
        return "High"
    if high + medium >= 3:
        return "Medium"
    return "Low"


def extract_text(file_or_text):
    if file_or_text is None:
        return ""
    if isinstance(file_or_text, str):
        return file_or_text
    return extract_uploaded_text(file_or_text)


def get_parser_setting(key, default=""):
    env_key = key.upper()
    if env_key in environ:
        return environ.get(env_key, default)
    try:
        from database import get_app_setting

        return get_app_setting(key, default)
    except Exception:
        return default


def get_configured_provider_name(provider=None):
    explicit = clean(provider)
    if explicit:
        return explicit
    configured = clean(get_parser_setting("document_parser_provider", "Auto"))
    if configured and configured.lower() != "auto":
        return configured
    if get_parser_setting("openai_api_key", "") or environ.get("OPENAI_API_KEY"):
        return "OpenAI"
    if get_parser_setting("gemini_api_key", "") or environ.get("GEMINI_API_KEY"):
        return "Gemini"
    return "Regex"


def get_parser_provider(provider=None):
    provider_name = get_configured_provider_name(provider).strip().lower()
    if provider_name == "openai":
        return OpenAIParserProvider(
            api_key=get_parser_setting("openai_api_key", "") or environ.get("OPENAI_API_KEY", ""),
            model=get_parser_setting("openai_parser_model", "gpt-4.1-mini"),
        )
    if provider_name == "gemini":
        return GeminiParserProvider(
            api_key=get_parser_setting("gemini_api_key", "") or environ.get("GEMINI_API_KEY", ""),
            model=get_parser_setting("gemini_parser_model", "gemini-1.5-pro"),
        )
    return RegexParserProvider()


def parse_with_ai(text, provider=None, filename=""):
    parser = get_parser_provider(provider)
    if isinstance(parser, RegexParserProvider):
        return {
            "ok": False,
            "provider": parser.name,
            "data": {},
            "error": "No AI parser configured. Regex parser used as fallback.",
        }
    return parser.parse(text, filename=filename)


def classify_document(text):
    folded = fold_text(text)
    checks = [
        ("DECREE", ["nghi dinh", "nd-cp", "decree"]),
        ("CIRCULAR", ["thong tu", "tt-btc", "tt-bct", "circular"]),
        ("LAW", [" luat ", "law no"]),
        ("OFFICIAL LETTER", ["cong van", "official letter"]),
        ("COMMERCIAL INVOICE", ["commercial invoice", "invoice no", "invoice number", "total value"]),
        ("PACKING LIST", ["packing list", "gross weight", "net weight", "packages", "cbm"]),
        ("DATASHEET", ["datasheet", "technical data", "model", "manufacturer", "specification"]),
        ("PERMIT", ["permit", "license", "validity", "issued by", "giay phep"]),
        ("BOOKING", ["booking confirmation", "booking no", "vessel", "voyage", "etd", "eta"]),
        ("SOP", ["standard operating procedure", "sop", "procedure steps", "checklist"]),
        ("CASE", ["root cause", "lessons learned", "problem", "solution"]),
        ("INQUIRY", ["please quote", "quotation", "inquiry", "cargo ready", "shipper", "consignee"]),
        ("SHIPMENT DOCUMENT", ["bill of lading", "awb", "hbl", "mbl", "shipment"]),
    ]
    padded = f" {folded} "
    for document_type, markers in checks:
        if any(marker in padded for marker in markers):
            return document_type
    return "OTHER"


def suggest_tags(text):
    folded = fold_text(text)
    rules = [
        ("customs", ["customs", "hai quan", "hs code", "declaration", "valuation"]),
        ("civil cryptography", ["civil cryptography", "mat ma dan su", "encryption", "firewall", "router"]),
        ("food", ["food", "thuc pham", "fda", "attp"]),
        ("animal quarantine", ["quarantine", "kiem dich"]),
        ("DG", ["dangerous goods", "dg", "hazardous", "un3480"]),
        ("battery", ["battery", "lithium", "un3480", "un3481"]),
        ("medical device", ["medical device", "medical equipment"]),
        ("telecom", ["telecom", "wireless", "radio frequency"]),
        ("import permit", ["import permit", "license", "giay phep"]),
        ("CO", ["certificate of origin", "c/o", "origin"]),
        ("invoice", ["invoice", "commercial invoice"]),
        ("packing list", ["packing list", "packages", "gross weight"]),
    ]
    tags = []
    for tag, markers in rules:
        if any(marker in folded for marker in markers):
            tags.append(tag)
    return sorted(set(tags))


def generate_summary(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return ""
    relevant = []
    folded_keywords = ["import", "export", "customs", "permit", "invoice", "packing", "shipment", "procedure", "risk"]
    for line in lines[:80]:
        folded = fold_text(line)
        if any(keyword in folded for keyword in folded_keywords):
            relevant.append(line)
        if len(relevant) >= 4:
            break
    if not relevant:
        relevant = lines[:4]
    return "\n".join(relevant)[:1600]


def extract_key_clauses(text):
    clauses = regex_extract_key_clauses(text)
    if clauses:
        return clauses
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text or "") if item.strip()]
    important = ["must", "shall", "required", "permit", "license", "customs", "risk", "procedure", "checklist"]
    results = []
    for paragraph in paragraphs:
        if any(term in fold_text(paragraph) for term in important):
            results.append(
                {
                    "article_no": "",
                    "clause_no": "",
                    "heading": paragraph[:120],
                    "content": paragraph[:3000],
                    "keywords": ", ".join(term for term in important if term in fold_text(paragraph)),
                    "status": "pending_review",
                }
            )
        if len(results) >= 12:
            break
    return results


def parse_amount(text):
    match = re.search(r"(?:total(?:\s+value)?|amount|invoice\s+value)\s*:?\s*([A-Z]{3})?\s*([0-9][0-9,]*(?:\.[0-9]+)?)", text or "", flags=re.IGNORECASE)
    if not match:
        match = re.search(r"\b(USD|VND|CNY|EUR)\s*([0-9][0-9,]*(?:\.[0-9]+)?)", text or "", flags=re.IGNORECASE)
    if not match:
        return "", ""
    currency = clean(match.group(1)).upper()
    value = clean(match.group(2))
    return value, currency


def parse_logistics_fields(text, document_type):
    value, currency = parse_amount(text)
    fields = {
        "shipper": first_regex(r"(?:shipper|seller|exporter)\s*:?\s*([^\n]+)", text),
        "consignee": first_regex(r"(?:consignee|buyer|importer)\s*:?\s*([^\n]+)", text),
        "commodity": first_regex(r"(?:commodity|description of goods|goods description|product)\s*:?\s*([^\n]+)", text),
        "invoice_number": first_regex(r"(?:invoice no\.?|invoice number)\s*:?\s*([A-Za-z0-9\-/.]+)", text),
        "invoice_date": normalize_date(first_regex(r"(?:invoice date|date)\s*:?\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})", text)),
        "value": value,
        "currency": currency,
        "packages": first_regex(r"(?:packages|package count|ctns|cartons)\s*:?\s*([^\n]+)", text),
        "weight": first_regex(r"(?:gross weight|net weight|weight)\s*:?\s*([^\n]+)", text),
        "volume": first_regex(r"(?:volume|cbm)\s*:?\s*([^\n]+)", text),
        "product_name": first_regex(r"(?:product name|product)\s*:?\s*([^\n]+)", text),
        "manufacturer": first_regex(r"(?:manufacturer|maker|brand)\s*:?\s*([^\n]+)", text),
        "model": first_regex(r"(?:model|model no\.?)\s*:?\s*([^\n]+)", text),
        "permit_number": first_regex(r"(?:permit no\.?|permit number|license no\.?)\s*:?\s*([A-Za-z0-9\-/.]+)", text),
        "validity_period": first_regex(r"(?:validity|valid until|expiry date)\s*:?\s*([^\n]+)", text),
    }
    if document_type == "DATASHEET":
        fields["technical_description"] = generate_summary(text)
    return fields


def parse_sop_fields(text):
    return {
        "purpose": first_regex(r"(?:purpose|objective)\s*:?\s*([\s\S]{0,700}?)(?:\n\s*(?:steps|procedure|checklist|risks)\b|$)", text),
        "steps": first_regex(r"(?:steps|procedure steps|procedure)\s*:?\s*([\s\S]{0,1200}?)(?:\n\s*(?:checklist|risks)\b|$)", text),
        "checklist": first_regex(r"(?:checklist)\s*:?\s*([\s\S]{0,900}?)(?:\n\s*(?:risks)\b|$)", text),
        "risks": first_regex(r"(?:risks?|risk notes)\s*:?\s*([\s\S]{0,900})", text),
    }


def parse_case_fields(text):
    return {
        "problem": first_regex(r"(?:problem|issue|question)\s*:?\s*([\s\S]{0,900}?)(?:\n\s*(?:root cause|solution|lessons)\b|$)", text),
        "root_cause": first_regex(r"(?:root cause)\s*:?\s*([\s\S]{0,700}?)(?:\n\s*(?:solution|lessons)\b|$)", text),
        "solution": first_regex(r"(?:solution|conclusion)\s*:?\s*([\s\S]{0,900}?)(?:\n\s*(?:lessons|risk)\b|$)", text),
        "lessons_learned": first_regex(r"(?:lessons learned|lesson)\s*:?\s*([\s\S]{0,900})", text),
    }


def compliance_enrichment(text):
    topics = suggest_tags(text)
    query = " ".join(topics[:3]) or generate_summary(text)[:120]
    sop_matches = search_sops(keyword=query, limit=3) if query else []
    case_matches = search_cases(keyword=query, limit=3) if query else []
    return {
        "possible_compliance_topics": topics,
        "possible_sop_matches": [
            {"id": item.get("id"), "title": item.get("title"), "category": item.get("category")}
            for item in sop_matches
        ],
        "possible_case_matches": [
            {"id": item.get("id"), "title": item.get("title"), "country": item.get("country")}
            for item in case_matches
        ],
    }


def fallback_parse_document(text, filename=""):
    document_type = classify_document(text)
    tags = suggest_tags(text)
    summary = generate_summary(text)
    key_clauses = extract_key_clauses(text)
    legal = parse_legal_document_text(text, filename) if document_type in ["LAW", "DECREE", "CIRCULAR", "OFFICIAL LETTER"] else {}
    logistics = parse_logistics_fields(text, document_type)
    sop = parse_sop_fields(text) if document_type == "SOP" else {}
    case = parse_case_fields(text) if document_type == "CASE" else {}
    fields = merge_result(
        {},
        {
            "document_type": document_type,
            "title": legal.get("title") or first_regex(r"(?:title|subject)\s*:?\s*([^\n]+)", text) or Path(filename).stem,
            "document_no": legal.get("document_no") or first_regex(r"(?:document no\.?|doc no\.?|no\.)\s*:?\s*([A-Za-z0-9\-/.]+)", text),
            "issuing_authority": legal.get("issuing_authority") or first_regex(r"(?:issuing authority|authority|issued by)\s*:?\s*([^\n]+)", text),
            "issue_date": legal.get("issue_date") or normalize_date(first_regex(r"(?:issue date|issued date|date)\s*:?\s*([^\n]+)", text)),
            "effective_date": legal.get("effective_date") or normalize_date(first_regex(r"(?:effective date|takes effect from)\s*:?\s*([^\n]+)", text)),
            "expiry_date": legal.get("expiry_date") or normalize_date(first_regex(r"(?:expiry date|valid until)\s*:?\s*([^\n]+)", text)),
            "category": legal.get("category") or (tags[0] if tags else document_type.title()),
            "tags": tags or legal.get("tags") or [],
            "summary": legal.get("summary") or summary,
            "keywords": sorted(set((tags or []) + [document_type.lower()])),
            "key_clauses": key_clauses,
            "raw_text": text[:12000],
            **logistics,
            **sop,
            **case,
            **compliance_enrichment(text),
        },
    )
    confidence = {}
    high_fields = {"document_type", "invoice_number", "permit_number", "document_no"}
    for key, value in fields.items():
        if key in ["field_confidence", "confidence_score", "parser_engine", "parser_error", "raw_text"]:
            continue
        if isinstance(value, list):
            confidence[key] = confidence_for(value, high=key in high_fields)
        else:
            confidence[key] = confidence_for(value, high=key in high_fields)
    fields["field_confidence"] = confidence
    fields["confidence_score"] = overall_confidence(confidence)
    fields["parser_engine"] = "regex_fallback"
    return fields


def parse_document(text, filename="", provider=None):
    body = clean(text)
    if not body:
        result = {**DEFAULT_FIELDS}
        result["parser_error"] = "No text extracted. Manual entry required."
        return result
    selected_provider = get_parser_provider(provider)
    if isinstance(selected_provider, RegexParserProvider):
        parsed = selected_provider.parse(body, filename=filename)["data"]
        parsed["parser_engine"] = selected_provider.name
        parsed["parser_error"] = ""
        return parsed

    ai_result = selected_provider.parse(body, filename=filename)
    if ai_result.get("ok") and isinstance(ai_result.get("data"), dict):
        parsed = merge_result({}, ai_result["data"])
        parsed["parser_engine"] = ai_result.get("provider") or "ai"
        return parsed
    parsed = fallback_parse_document(body, filename=filename)
    parsed["parser_error"] = ai_result.get("error", "")
    parsed["parser_engine"] = f"{ai_result.get('provider') or selected_provider.name}_failed_regex_fallback"
    return parsed
