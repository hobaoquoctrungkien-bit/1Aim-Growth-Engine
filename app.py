import logging
import importlib
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import database as database_module

database_module = importlib.reload(database_module)

from ui_helpers import status_badge_html
from pages.knowledge_base import show_knowledge_base
from database import (
    apply_pricing_summary_to_opportunity,
    calculate_suggested_sell_rate,
    create_opportunity,
    create_inquiry,
    create_inquiry_opportunity,
    delete_test_opportunities,
    find_captured_crm_duplicates,
    get_app_setting,
    get_backup_history,
    get_database_backup_status,
    get_existing_lead_keys,
    get_lead_detail,
    get_last_successful_backup,
    get_leads,
    get_crm_dashboard_data,
    get_crm_follow_up_rows,
    get_daily_outreach_capacity,
    get_holiday_library,
    get_invalid_email_contacts,
    get_opportunities,
    get_opportunity_dashboard_data,
    get_opportunity_detail,
    get_test_opportunity_candidates,
    get_open_tasks,
    get_outreach_campaign_metrics,
    get_outreach_campaign_templates,
    get_pricing_summary,
    get_quotation_detail,
    get_quotation_templates,
    get_quotations,
    get_quote_follow_up_tasks,
    process_email_bounces,
    process_email_replies,
    record_outreach_open,
    get_campaign_audience,
    get_campaign_filter_options,
    get_campaign_invalid_email_skip_count,
    generate_outreach_message,
    generate_outreach_subject,
    render_subject_template,
    save_outreach_campaign_template,
    send_outreach_preview_email,
    get_task_counts_by_type,
    complete_execution_task,
    import_leads,
    initialize_missing_lead_followups,
    init_db,
    mark_prepare_quote_sent,
    create_quotation_from_opportunity,
    create_quotation_version,
    save_captured_crm_record,
    save_holiday_library_item,
    save_opportunity,
    save_quotation,
    save_quotation_template,
    save_vendor_rate,
    create_and_send_outreach_campaign,
    has_captured_crm_duplicates,
    is_smtp_configured,
    send_email_via_smtp,
    test_smtp_connection,
    set_app_setting,
    complete_follow_up,
    add_country_holiday_reminders,
    create_relationship_occasion,
    snooze_follow_up,
    get_occasion_reminders,
    mark_occasion_message_sent,
    record_backup_history,
    snooze_occasion,
    sync_date_based_occasions,
    refresh_lead_priority_scores,
    update_relationship_occasion,
    update_contact_email_status,
    update_contact_email_address,
    update_contact_relationship_action,
    update_lead_detail,
    update_lead_next_follow_up,
    update_lead_notes,
    update_lead_status_action,
    update_organization_customer_action,
    update_opportunity_stage,
    update_quotation_status,
    complete_quote_follow_up_task,
    OPPORTUNITY_STAGES,
)
from inquiry_intake import (
    build_inquiry_notes,
    extract_attachment_text,
    parse_inquiry_text,
    save_inquiry_files,
)
from typography import DEFAULT_UI_SCALE, UI_SCALE_OPTIONS, get_typography_tokens
from knowledge_service import (
    INTELLIGENCE_TYPES,
    save_intelligence,
)
from quotation_engine import build_quotation_excel, build_quotation_pdf


EXCEL_COLUMNS = {
    "Company Name": "company_name",
    "Contact Person": "contact_person",
    "Country": "country",
    "City": "city",
    "Job Title": "job_title",
    "Tel.": "phone",
    "Email": "email",
    "WeChat": "wechat",
    "Whatsapp": "whatsapp",
    "Membership (OLO, JCTRANS, WCA)": "membership",
}

REQUIRED_CONTACT_COLUMNS = ["Contact Person", "Email", "WeChat", "Whatsapp"]
MEMBERSHIP_EXCEL_COLUMNS = ["Membership (OLO, JCTRANS, WCA)", "Membership"]
MEMBERSHIP_OPTIONS = ["OLO", "JCTrans", "WCA", "GLA"]
MEMBERSHIP_SOURCE_USE_EXCEL = "Use value from Excel"
MEMBERSHIP_SOURCE_OVERRIDE = "Override with selected Membership"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ACCEPTED_IMPORT_EXTENSIONS = ["xlsx", "xls", "csv"]
ACCEPTED_CARD_IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "webp"]
ORG_TYPE_OPTIONS = [
    "Forwarder",
    "Shipper",
    "Consignee",
    "Carrier",
    "Vendor",
    "Overseas Agent",
    "Other",
]
CUSTOMER_STATUS_OPTIONS = ["Prospect", "Qualified", "Customer", "Inactive"]
RELATIONSHIP_STATUS_OPTIONS = ["New", "Connected", "Introduced", "Warm", "Active", "Inactive"]
LEAD_STATUS_OPTIONS = ["New", "Contacted", "Replied", "Qualified", "Disqualified", "Converted"]
EMAIL_STATUS_OPTIONS = ["Unknown", "Valid", "Invalid", "Bounced"]
CAPTURE_SAVE_AS_OPTIONS = [
    "Lead",
    "Customer",
]
DUPLICATE_ACTION_OPTIONS = [
    "Update existing",
    "Create new anyway",
]
PREFERRED_LANGUAGE_OPTIONS = ["English", "Vietnamese", "Chinese"]
PREFERRED_CHANNEL_OPTIONS = ["Email", "Phone", "WhatsApp", "WeChat"]
RELATIONSHIP_TONE_OPTIONS = ["Formal", "Warm", "Friendly", "Short"]
OCCASION_TYPE_OPTIONS = [
    "National Holiday",
    "Birthday",
    "Company Anniversary",
    "Cooperation Anniversary",
    "First Meeting Anniversary",
    "Custom",
]
PRICING_VENDOR_TYPE_OPTIONS = ["Carrier", "Agent", "Local Charge"]
PRICING_CHARGE_TYPE_OPTIONS = ["Freight", "Origin", "Destination", "Customs", "Documentation", "Trucking", "Other"]
PRICING_CURRENCY_OPTIONS = ["USD", "VND", "CNY", "EUR"]
QUOTATION_STATUS_OPTIONS = ["Draft", "Pending Approval", "Approved", "Sent", "Rejected"]
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="1Aim Growth Engine",
    layout="wide",
)

init_db()

if "ui_scale" not in st.session_state:
    saved_ui_scale = get_app_setting("ui_scale")
    if not saved_ui_scale:
        saved_ui_scale = DEFAULT_UI_SCALE
        set_app_setting("ui_scale", saved_ui_scale)
    st.session_state.ui_scale = saved_ui_scale
    st.session_state.persisted_ui_scale = saved_ui_scale

if st.session_state.ui_scale not in UI_SCALE_OPTIONS:
    st.session_state.ui_scale = DEFAULT_UI_SCALE
    st.session_state.persisted_ui_scale = DEFAULT_UI_SCALE
    set_app_setting("ui_scale", DEFAULT_UI_SCALE)

if "persisted_ui_scale" not in st.session_state:
    st.session_state.persisted_ui_scale = st.session_state.ui_scale

if "lead_import_memberships" not in st.session_state:
    saved_memberships = get_app_setting("lead_import_memberships", "")
    st.session_state.lead_import_memberships = [
        membership.strip()
        for membership in saved_memberships.split(",")
        if membership.strip() in MEMBERSHIP_OPTIONS
    ]
    st.session_state.persisted_lead_import_memberships = ",".join(
        st.session_state.lead_import_memberships
    )


def apply_global_typography(ui_scale):
    # Accessibility: use global typography tokens only.
    tokens = get_typography_tokens(ui_scale)

    stylesheet = """
    <style>
        :root {
            --font-size-xs: __FONT_SIZE_XS__px;
            --font-size-sm: __FONT_SIZE_SM__px;
            --font-size-md: __FONT_SIZE_MD__px;
            --font-size-lg: __FONT_SIZE_LG__px;
            --font-size-xl: __FONT_SIZE_XL__px;
            --font-size-xxl: __FONT_SIZE_XXL__px;
            --color-bg: #0b1018;
            --color-surface: #141c2a;
            --color-surface-soft: #182233;
            --color-control: #1c2636;
            --color-border: #263244;
            --color-border-strong: #3d4b63;
            --color-text: #edf2f7;
            --color-muted: #b7c4d8;
            --color-accent: #2f80ed;
            --color-accent-soft: rgba(47, 128, 237, 0.18);
        }
        .stApp {
            background: var(--color-bg);
            color: var(--color-text);
            font-size: var(--font-size-sm);
        }
        [data-testid="stSidebar"] {
            background: #111827;
            border-right: 1px solid var(--color-border);
        }
        [data-testid="stSidebar"] [role="radiogroup"] label,
        [data-testid="stSidebar"] [data-baseweb="radio"] {
            border-radius: 6px;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: var(--color-surface-soft);
        }
        html, body, p, li, label, textarea, input, select,
        [data-testid="stMarkdownContainer"],
        [data-testid="stWidgetLabel"],
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stSelectbox"],
        [data-testid="stFileUploader"],
        [data-testid="stAlert"],
        [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] * {
            font-size: var(--font-size-sm) !important;
            line-height: 1.5 !important;
        }
        small, [data-testid="stCaptionContainer"], .stCaption {
            color: var(--color-muted) !important;
        }
        h1, [data-testid="stHeadingWithActionElements"] h1 {
            font-size: var(--font-size-xxl) !important;
            line-height: 1.15 !important;
        }
        h2, h3, [data-testid="stHeadingWithActionElements"] h2,
        [data-testid="stHeadingWithActionElements"] h3 {
            font-size: var(--font-size-xl) !important;
            line-height: 1.25 !important;
        }
        strong, b {
            font-size: var(--font-size-lg) !important;
        }
        [data-testid="stMetric"] {
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: 8px;
            padding: 14px;
        }
        [data-testid="stMetric"] label,
        [data-testid="stMetric"] [data-testid="stMetricLabel"] {
            font-size: var(--font-size-lg) !important;
            line-height: 1.3 !important;
        }
        [data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: var(--font-size-xl) !important;
            line-height: 1.2 !important;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--color-border);
            border-radius: 8px;
            overflow: hidden;
        }
        div[data-testid="stDataFrame"],
        div[data-testid="stDataFrame"] *,
        div[data-testid="stTable"],
        div[data-testid="stTable"] * {
            font-size: var(--font-size-sm) !important;
            line-height: 1.45 !important;
        }
        .stButton > button {
            border-radius: 6px;
            border: 1px solid var(--color-border-strong);
            background: var(--color-control);
            color: var(--color-text);
            font-size: var(--font-size-sm) !important;
            line-height: 1.35 !important;
            min-height: calc(var(--font-size-sm) * 2.5);
        }
        .stButton > button:hover {
            border-color: var(--color-accent);
            background: var(--color-surface-soft);
            color: var(--color-text);
        }
        .stButton > button:focus-visible,
        a:focus-visible,
        input:focus,
        textarea:focus,
        [data-baseweb="select"] > div:focus-within {
            outline: 3px solid var(--color-accent-soft) !important;
            outline-offset: 2px !important;
            border-color: var(--color-accent) !important;
            box-shadow: none !important;
        }
        .stButton > button:disabled,
        .stButton > button:disabled:hover {
            background: #171f2d;
            border-color: var(--color-border);
            color: #7f8ba0;
        }
        .stButton > button[kind="primary"] {
            background: var(--color-accent);
            border-color: var(--color-accent);
        }
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-baseweb="select"] > div,
        [data-testid="stDateInput"] input,
        [data-testid="stNumberInput"] input {
            background: var(--color-control) !important;
            border-color: var(--color-border-strong) !important;
            color: var(--color-text) !important;
            border-radius: 6px !important;
        }
        [data-testid="stTabs"] [role="tablist"] {
            gap: 6px;
            border-bottom: 1px solid var(--color-border);
        }
        [data-testid="stTabs"] [role="tab"] {
            border-radius: 6px 6px 0 0;
            color: var(--color-muted);
            padding: 8px 12px;
        }
        [data-testid="stTabs"] [aria-selected="true"] {
            background: var(--color-surface);
            color: var(--color-text);
            border: 1px solid var(--color-border);
            border-bottom-color: var(--color-surface);
        }
        [data-testid="stExpander"] {
            border: 1px solid var(--color-border);
            border-radius: 8px;
            background: rgba(20, 28, 42, 0.48);
        }
        [data-testid="stAlert"] {
            border-radius: 8px;
            border: 1px solid var(--color-border);
        }
        .ui-status-badge {
            display: inline-flex;
            align-items: center;
            min-height: 24px;
            padding: 2px 8px;
            border-radius: 6px;
            border: 1px solid;
            font-weight: 700;
            white-space: nowrap;
        }
        .st-key-capture_organization_type div[data-baseweb="select"] > div,
        .st-key-capture_customer_status div[data-baseweb="select"] > div,
        .st-key-capture_relationship_status div[data-baseweb="select"] > div {
            border: 2px solid #ff5a5f !important;
            box-shadow: 0 0 0 1px rgba(255, 90, 95, 0.35) !important;
        }
        .st-key-capture_organization_type label,
        .st-key-capture_customer_status label,
        .st-key-capture_relationship_status label {
            color: #ffb3b5 !important;
            font-weight: 700 !important;
        }
    </style>
    """

    for token_name, token_value in tokens.items():
        stylesheet = stylesheet.replace(
            f"__FONT_SIZE_{token_name.upper()}__",
            str(token_value),
        )

    st.markdown(
        stylesheet,
        unsafe_allow_html=True,
    )


def status_badge(label, tone="neutral"):
    st.markdown(
        status_badge_html(label, tone),
        unsafe_allow_html=True,
    )


def clean_cell(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def key_value(value):
    return clean_cell(value).lower()


def is_valid_email(email):
    if not email:
        return True
    return bool(EMAIL_PATTERN.match(email))


def first_match(pattern, text, flags=re.IGNORECASE):
    match = re.search(pattern, text, flags)
    if not match:
        return ""
    return clean_cell(match.group(1))


def clean_contact_line(line):
    return re.sub(
        r"^(name|contact|attn|person|mr\.?|ms\.?|mrs\.?)\s*[:：-]\s*",
        "",
        clean_cell(line),
        flags=re.IGNORECASE,
    )


def extract_text_from_card_image(uploaded_file):
    if not uploaded_file:
        return "", ""

    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return "", (
            "OCR is not installed on this machine. Paste the namecard text below "
            "and the system will still parse it."
        )

    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        text = pytesseract.image_to_string(image)
        return clean_cell(text), ""
    except Exception as exc:
        logger.exception("Namecard OCR failed.")
        return "", f"Could not read text from this image: {exc}"


def parse_contact_text(raw_text):
    text = clean_cell(raw_text)
    lines = [
        clean_cell(line)
        for line in re.split(r"[\r\n]+", text)
        if clean_cell(line)
    ]
    confidence = {}
    parsed = {
        "company_name": "",
        "local_name": "",
        "contact_person": "",
        "job_title": "",
        "email": "",
        "phone": "",
        "wechat": "",
        "whatsapp": "",
        "website": "",
        "country": "",
        "city": "",
        "membership": "",
        "organization_type": "Overseas Agent",
        "customer_status": "Customer",
        "relationship_status": "Active",
        "source": "Quick Capture",
        "campaign": "Quick Capture",
        "lead_status": "New",
        "notes": text,
    }

    def set_field(field, value, level):
        value = clean_cell(value)
        if value and not parsed[field]:
            parsed[field] = value
            confidence[field] = level

    def has_email(value):
        return bool(re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", value, re.I))

    def has_website(value):
        return bool(
            re.search(r"https?://|www\.", value, re.I)
            or re.search(r"\b[A-Z0-9-]+\.(com|net|org|vn|cn|hk|sg|co|io)\b", value, re.I)
        )

    def strip_label(value):
        return re.sub(r"^[^:：-]{1,30}[:：-]\s*", "", clean_cell(value))

    def extract_phone(value):
        match = re.search(r"(\+?[0-9][0-9 .()/-]{6,}[0-9])", value)
        return clean_cell(match.group(1)) if match else ""

    def is_chinese_company(value):
        return bool(re.search(r"[\u4e00-\u9fff]", value)) and any(
            marker in value for marker in ["有限公司", "物流", "货运", "供应链"]
        )

    org_markers = [
        "ltd",
        "limited",
        "logistics",
        "freight",
        "forwarding",
        "transport",
        "shipping",
        "supply chain",
        "co.",
        "company",
        "corp",
    ]
    title_markers = [
        "manager",
        "director",
        "sales",
        "operation",
        "operations",
        "supervisor",
        "executive",
        "president",
        "ceo",
        "founder",
        "alliances",
        "strategic",
    ]
    non_name_markers = [
        "email",
        "tel",
        "phone",
        "mobile",
        "whatsapp",
        "wechat",
        "address",
        "website",
        "www",
        "http",
    ]
    location_markers = [
        "china",
        "vietnam",
        "singapore",
        "hong kong",
        "shenzhen",
        "guangzhou",
        "shanghai",
        "beijing",
        "hanoi",
        "ho chi minh",
        "bangkok",
    ]

    if lines:
        split_match = re.match(r"^(.{2,80}?)\s+[/\-]\s+(.{2,100})$", lines[0])
        if split_match:
            left_side = clean_cell(split_match.group(1))
            right_side = clean_cell(split_match.group(2))
            lower_left = left_side.lower()
            if (
                not has_email(left_side)
                and not has_website(left_side)
                and not any(marker in lower_left for marker in org_markers)
            ):
                set_field("contact_person", left_side, "High")
                set_field("job_title", right_side, "High")

    email = first_match(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", text)
    set_field("email", email.lower(), "High")

    english_company_lines = []
    chinese_company_lines = []
    for line in lines:
        lower_line = line.lower()
        if has_email(line) or has_website(line):
            continue
        if is_chinese_company(line):
            chinese_company_lines.append(line)
        if any(marker in lower_line for marker in org_markers):
            english_company_lines.append(line)

    if english_company_lines:
        set_field("company_name", english_company_lines[0], "High")
    if chinese_company_lines:
        if parsed["company_name"]:
            set_field("local_name", chinese_company_lines[0], "High")
        else:
            set_field("company_name", chinese_company_lines[0], "High")

    for line in lines:
        lower_line = line.lower()
        if parsed["website"] or has_email(line):
            continue
        if "www." in lower_line or "http://" in lower_line or "https://" in lower_line or "website" in lower_line:
            website = first_match(
                r"((?:https?://)?(?:www\.)?[A-Z0-9-]+(?:\.[A-Z0-9-]+)+(/[^\s]*)?)",
                line,
            )
            set_field("website", website, "High")

    for line in lines:
        lower_line = line.lower()
        if not parsed["phone"] and any(label in lower_line for label in ["tel", "phone", "mobile", "cell"]):
            set_field("phone", extract_phone(line), "High")
        if not parsed["whatsapp"] and re.search(r"\b(whatsapp|whats app|wa|mobile)\b\s*[:：]?", lower_line):
            set_field("whatsapp", extract_phone(line), "High")
        if not parsed["wechat"] and re.search(r"\b(wechat|weixin|wx)\b\s*[:：]?", lower_line):
            wechat = first_match(r"(?:wechat|weixin|wx)\s*[:：]?\s*([@A-Z0-9._-]{3,})", line)
            set_field("wechat", wechat, "High")

    if not parsed["job_title"]:
        for line in lines:
            lower_line = line.lower()
            if has_email(line) or has_website(line):
                continue
            if any(marker in lower_line for marker in title_markers):
                set_field("job_title", strip_label(line), "Medium")
                break

    if not parsed["contact_person"]:
        for line in lines:
            lower_line = line.lower()
            if line in [parsed["company_name"], parsed["local_name"], parsed["job_title"]]:
                continue
            if has_email(line) or has_website(line):
                continue
            if any(marker in lower_line for marker in non_name_markers):
                continue
            if "," in line or any(marker in lower_line for marker in location_markers):
                continue
            if re.search(r"\d", line):
                continue
            if any(marker in lower_line for marker in org_markers) or is_chinese_company(line):
                continue
            if len(line.split()) <= 5:
                set_field("contact_person", clean_contact_line(line), "Medium")
                break

    company_for_location = parsed["company_name"] or parsed["local_name"]
    city_match = re.search(r"[（(]\s*([A-Za-z ]{2,40})\s*[）)]", company_for_location)
    if city_match and clean_cell(city_match.group(1)).lower() == "shenzhen":
        set_field("city", "Shenzhen", "High")
        set_field("country", "China", "High")

    for field in parsed:
        confidence.setdefault(field, "" if not parsed[field] else "Low")
    parsed["_confidence"] = confidence
    return parsed


def lead_duplicate_keys(company_name, country, campaign, contact_values):
    organization_key = (key_value(company_name), key_value(country))
    campaign_key = key_value(campaign)
    keys = set()

    for contact_value in contact_values:
        contact_key = key_value(contact_value)
        if organization_key[0] and contact_key and campaign_key:
            keys.add((*organization_key, contact_key, campaign_key))

    return keys


def build_existing_key_sets():
    existing_rows = get_existing_lead_keys()
    keys = {"lead": set()}

    for row in existing_rows:
        keys["lead"].update(
            lead_duplicate_keys(
                row["company_name"],
                row["country"],
                row["campaign"],
                [
                    row["email"],
                    row["wechat"],
                    row["whatsapp"],
                    row["contact_person"],
                ],
            )
        )

    return keys


def format_membership_value(memberships):
    return ", ".join(memberships)


def find_membership_column(dataframe):
    for column in MEMBERSHIP_EXCEL_COLUMNS:
        if column in dataframe.columns:
            return column
    return None


def parse_leads(dataframe, campaign, selected_memberships=None, membership_source=None):
    existing_keys = build_existing_key_sets()
    seen_keys = {"lead": set()}
    selected_memberships = selected_memberships or []
    selected_membership_value = format_membership_value(selected_memberships)
    membership_source = membership_source or MEMBERSHIP_SOURCE_OVERRIDE
    campaign = campaign.strip()

    parsed_rows = []

    for index, row in dataframe.iterrows():
        lead = {}

        for excel_column, db_field in EXCEL_COLUMNS.items():
            lead[db_field] = clean_cell(row.get(excel_column, ""))

        if selected_membership_value and membership_source == MEMBERSHIP_SOURCE_OVERRIDE:
            lead["membership"] = selected_membership_value

        lead["email"] = lead["email"].lower()
        lead["source"] = "Excel Import"
        lead["campaign"] = campaign
        lead["lead_status"] = "New"
        lead["status"] = "New"
        lead["owner"] = "admin"

        reasons = []
        duplicate_reasons = []

        has_company = bool(lead["company_name"])
        has_contact_channel = any(
            lead[field]
            for field in ["contact_person", "email", "wechat", "whatsapp"]
        )

        if not has_company or not has_contact_channel:
            reasons.append("Missing company/contact")

        if lead["email"] and not is_valid_email(lead["email"]):
            reasons.append("Invalid email")

        lead_keys = lead_duplicate_keys(
            lead["company_name"],
            lead["country"],
            lead["campaign"],
            [
                lead["email"],
                lead["wechat"],
                lead["whatsapp"],
                lead["contact_person"],
            ],
        )

        if lead_keys & existing_keys["lead"]:
            duplicate_reasons.append("Duplicate lead for this campaign")

        if lead_keys & seen_keys["lead"]:
            duplicate_reasons.append("Duplicate lead in file")

        if duplicate_reasons:
            reasons.extend(duplicate_reasons)

        seen_keys["lead"].update(lead_keys)

        parsed_rows.append(
            {
                "row_number": index + 2,
                "lead": lead,
                "is_missing_required": "Missing company/contact" in reasons,
                "is_invalid_email": "Invalid email" in reasons,
                "is_duplicate": bool(duplicate_reasons),
                "is_importable": not reasons,
                "status": "Ready" if not reasons else "Skipped",
                "reason": ", ".join(reasons),
            }
        )

    return parsed_rows


def summarize_rows(parsed_rows):
    return {
        "total_rows": len(parsed_rows),
        "valid_rows": sum(1 for row in parsed_rows if row["is_importable"]),
        "duplicate_rows": sum(1 for row in parsed_rows if row["is_duplicate"]),
        "missing_required_rows": sum(
            1 for row in parsed_rows if row["is_missing_required"]
        ),
        "invalid_email_rows": sum(
            1 for row in parsed_rows if row["is_invalid_email"]
        ),
        "invalid_rows": sum(
            1 for row in parsed_rows
            if row["is_missing_required"] or row["is_invalid_email"]
        ),
    }


def build_preview(parsed_rows, limit=20):
    preview_rows = []

    for parsed_row in parsed_rows[:limit]:
        lead = parsed_row["lead"]
        preview_rows.append(
            {
                "Row": parsed_row["row_number"],
                "Status": parsed_row["status"],
                "Reason": parsed_row["reason"],
                "Company": lead["company_name"],
                "Contact Person": lead["contact_person"],
                "Country": lead["country"],
                "City": lead["city"],
                "Job Title": lead["job_title"],
                "Email": lead["email"],
                "WeChat": lead["wechat"],
                "Whatsapp": lead["whatsapp"],
                "Membership": lead["membership"],
                "Campaign": lead["campaign"],
            }
        )

    return pd.DataFrame(preview_rows)


def get_uploaded_file_extension(uploaded_file):
    return Path(uploaded_file.name).suffix.lower().lstrip(".")


def get_excel_engine(extension):
    if extension == "xlsx":
        return "openpyxl"
    if extension == "xls":
        return "xlrd"
    return None


def log_upload_details(uploaded_file, extension, engine):
    detected_mime_type = getattr(uploaded_file, "type", None)

    logger.info(
        "Lead import upload: filename=%s extension=.%s mime_type=%s engine=%s",
        uploaded_file.name,
        extension,
        detected_mime_type,
        engine or "none",
    )


def is_missing_xlrd_error(extension, exc):
    return extension == "xls" and "xlrd" in str(exc).lower()


def friendly_xlrd_error():
    return (
        "Legacy Excel (.xls) files require xlrd. "
        "Please install dependencies or save the file as .xlsx."
    )


def read_xls_with_fallback(uploaded_file, reader):
    try:
        uploaded_file.seek(0)
        logger.info(
            "Lead import parser attempt: filename=%s extension=.xls engine=xlrd",
            uploaded_file.name,
        )
        return reader("xlrd")
    except ImportError as exc:
        if not is_missing_xlrd_error("xls", exc):
            raise

        try:
            uploaded_file.seek(0)
            logger.info(
                "Lead import parser fallback: filename=%s extension=.xls engine=openpyxl",
                uploaded_file.name,
            )
            return reader("openpyxl")
        except Exception as fallback_exc:
            raise ImportError(friendly_xlrd_error()) from fallback_exc


def validate_uploaded_file_extension(uploaded_file):
    extension = get_uploaded_file_extension(uploaded_file)

    if extension not in ACCEPTED_IMPORT_EXTENSIONS:
        accepted_extensions = ", ".join(f".{item}" for item in ACCEPTED_IMPORT_EXTENSIONS)
        raise ValueError(f"Unsupported file extension. Supported formats: {accepted_extensions}.")

    return extension


def get_workbook_sheet_names(uploaded_file, extension):
    engine = get_excel_engine(extension)
    log_upload_details(uploaded_file, extension, engine)

    if extension == "csv":
        return []

    if extension == "xls":
        return read_xls_with_fallback(
            uploaded_file,
            lambda active_engine: pd.ExcelFile(uploaded_file, engine=active_engine).sheet_names,
        )

    uploaded_file.seek(0)
    workbook = pd.ExcelFile(uploaded_file, engine=engine)
    return workbook.sheet_names


def read_raw_preview(uploaded_file, extension, sheet_name=None, limit=20):
    engine = get_excel_engine(extension)

    uploaded_file.seek(0)
    if extension == "csv":
        return pd.read_csv(uploaded_file, dtype=str, header=None, nrows=limit)

    if extension == "xls":
        return read_xls_with_fallback(
            uploaded_file,
            lambda active_engine: pd.read_excel(
                uploaded_file,
                sheet_name=sheet_name,
                dtype=str,
                header=None,
                nrows=limit,
                engine=active_engine,
            ),
        )

    return pd.read_excel(
        uploaded_file,
        sheet_name=sheet_name,
        dtype=str,
        header=None,
        nrows=limit,
        engine=engine,
    )


def read_uploaded_leads_file(uploaded_file, extension, sheet_name, header_row_index):
    engine = get_excel_engine(extension)

    uploaded_file.seek(0)
    if extension == "csv":
        return pd.read_csv(uploaded_file, dtype=str, header=header_row_index)

    if extension == "xls":
        return read_xls_with_fallback(
            uploaded_file,
            lambda active_engine: pd.read_excel(
                uploaded_file,
                sheet_name=sheet_name,
                dtype=str,
                header=header_row_index,
                engine=active_engine,
            ),
        )

    return pd.read_excel(
        uploaded_file,
        sheet_name=sheet_name,
        dtype=str,
        header=header_row_index,
        engine=engine,
    )


def build_quote_follow_up_suggestion(task, channel):
    quote_no = task.get("quote_no") or "the quotation"
    customer = task.get("organization_name") or "your team"
    opportunity = task.get("opportunity_title") or "this shipment"
    amount = currency_display(task.get("sell_amount"), task.get("currency") or "USD")

    if channel == "WeChat":
        return (
            f"Hi, just checking whether you had a chance to review quote {quote_no} "
            f"for {opportunity}. Happy to adjust details if needed."
        )
    if channel == "WhatsApp":
        return (
            f"Hi, following up on quote {quote_no} for {opportunity}. "
            f"Please let me know if the rate or schedule works for you."
        )
    return (
        f"Dear {customer},\n\n"
        f"I hope you are well. I am following up on quote {quote_no} for {opportunity}"
        f"{f' ({amount})' if task.get('sell_amount') else ''}.\n\n"
        "Please let me know if you have any questions or if you would like us to adjust the offer.\n\n"
        "Best regards,"
    )


def show_quote_follow_up_engine():
    tasks = get_quote_follow_up_tasks()
    st.subheader("Quote Follow-up Engine")

    if not tasks:
        st.info("No open quote follow-ups.")
        return

    st.caption("Follow up sent quotes, log the channel used, and schedule the next touch.")
    for task in tasks:
        label = " | ".join(
            item for item in [
                task.get("quote_no"),
                task.get("organization_name"),
                task.get("opportunity_title") or task.get("title"),
            ]
            if item
        )
        with st.container(border=True):
            st.markdown(f"**{label or task.get('title') or 'Quote follow-up'}**")
            meta_cols = st.columns(4)
            meta_cols[0].caption(f"Due: {task.get('due_date') or '-'}")
            meta_cols[1].caption(f"Channel: {task.get('channel') or '-'}")
            meta_cols[2].caption(f"Status: {task.get('quotation_status') or '-'}")
            meta_cols[3].caption(currency_display(task.get("sell_amount"), task.get("currency") or "USD"))

            control_cols = st.columns([1, 1, 2])
            channel = control_cols[0].selectbox(
                "Channel",
                ["Email", "WeChat", "WhatsApp"],
                key=f"quote_fu_channel_{task['id']}",
            )
            next_follow_up_date = control_cols[1].date_input(
                "Next follow-up",
                value=datetime.today().date() + timedelta(days=3),
                key=f"quote_fu_next_{task['id']}",
            )
            schedule_next = control_cols[2].checkbox(
                "Schedule next follow-up",
                value=True,
                key=f"quote_fu_schedule_{task['id']}",
            )

            suggestion = build_quote_follow_up_suggestion(task, channel)
            st.text_area(
                "AI follow-up suggestion",
                value=suggestion,
                height=130,
                key=f"quote_fu_suggestion_{task['id']}",
            )

            action_cols = st.columns(3)
            channel_buttons = [
                ("Email follow-up", "Email", action_cols[0]),
                ("WeChat follow-up", "WeChat", action_cols[1]),
                ("WhatsApp follow-up", "WhatsApp", action_cols[2]),
            ]
            for label_text, button_channel, button_col in channel_buttons:
                if button_col.button(label_text, key=f"quote_fu_{button_channel.lower()}_{task['id']}"):
                    next_date = next_follow_up_date.isoformat() if schedule_next else None
                    complete_quote_follow_up_task(
                        task["id"],
                        button_channel,
                        next_date,
                        suggestion,
                    )
                    st.success(f"{button_channel} follow-up logged.")
                    st.rerun()


def show_dashboard():
    st.title("1AGE Execution Engine")
    data = get_crm_dashboard_data()
    kpis = data["kpis"]
    execution = data.get("execution") or {}
    outreach_queue = data["outreach_queue"]
    last_backup = get_last_successful_backup()

    def priority_color(score):
        if score >= 90:
            return "#ff5a5f"
        if score >= 70:
            return "#ff9f43"
        if score >= 50:
            return "#f6d365"
        return "#94a3b8"

    def priority_badge(score):
        color = priority_color(int(score or 0))
        st.markdown(
            f"""
            <div style="border:1px solid {color};color:{color};border-radius:6px;padding:6px 8px;text-align:center;font-weight:700;">
                {int(score or 0)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    def action_score_badge(score):
        st.markdown(
            f"""
            <div style="border:1px solid #2f80ed;color:#edf2f7;background:#172033;border-radius:6px;padding:6px 8px;text-align:center;font-weight:700;">
                {int(score or 0)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    def health_badge(health):
        score = int((health or {}).get("score") or 0)
        label = (health or {}).get("label") or "-"
        color = "#2ecc71" if score >= 75 else "#ff9f43" if score >= 50 else "#ff5a5f"
        st.markdown(
            f"""
            <div style="border:1px solid {color};color:{color};border-radius:6px;padding:6px 8px;text-align:center;font-weight:700;">
                {score}% {label}
            </div>
            """,
            unsafe_allow_html=True,
        )

    def mps_badge(score):
        score = int(score or 0)
        color = "#ff5a5f" if score >= 100 else "#f6d365" if score >= 50 else "#2f80ed" if score >= 20 else "#94a3b8"
        st.markdown(
            f"""
            <div style="border:1px solid {color};color:{color};border-radius:6px;padding:6px 8px;text-align:center;font-weight:700;">
                MPS {score}
            </div>
            """,
            unsafe_allow_html=True,
        )

    def open_task_target(task):
        if task.get("opportunity_id"):
            st.session_state.selected_opportunity_id = task["opportunity_id"]
            st.session_state.pending_page = "Opportunities"
            st.rerun()
        if task.get("contact_id"):
            st.session_state.selected_lead_id = task.get("lead_id")
            st.session_state.pending_page = "Leads List"
            st.rerun()

    def render_execution_rows(rows, key_prefix, limit=10):
        visible_rows = rows[:limit]
        if not visible_rows:
            st.info("No execution actions in this section.")
            return
        header_cols = st.columns([1, 3, 2, 2, 1, 1, 1])
        header_cols[0].caption("Money")
        header_cols[1].caption("Next Action")
        header_cols[2].caption("Customer / Project")
        header_cols[3].caption("Expected Outcome")
        header_cols[4].caption("Due")
        header_cols[5].caption("Open")
        header_cols[6].caption("DONE")
        for task in visible_rows:
            cols = st.columns([1, 3, 2, 2, 1, 1, 1])
            with cols[0]:
                mps_badge(task.get("money_proximity_score"))
            cols[1].write(task.get("title") or "Untitled action")
            cols[2].write(task.get("organization_name") or task.get("opportunity_title") or "-")
            cols[3].write(task.get("expected_outcome") or "-")
            cols[4].write(task.get("due_date") or "-")
            if cols[5].button("Open", key=f"{key_prefix}_open_{task['id']}"):
                open_task_target(task)
            if cols[6].button("DONE", key=f"{key_prefix}_done_{task['id']}"):
                complete_execution_task(task["id"])
                st.rerun()

    st.subheader("MONEY IS HERE 🔥")
    open_loop = int(execution.get("open_loop_score") or 0)
    loop_status = execution.get("open_loop_status") or {}
    exec_cols = st.columns(4)
    exec_cols[0].metric("Revenue Actions", len(execution.get("money_is_here") or []))
    exec_cols[1].metric("Open Loops", open_loop)
    exec_cols[2].metric("Loop Status", loop_status.get("label") or "-")
    exec_cols[3].metric("Next Actions", len(execution.get("next_actions") or []))

    mission = execution.get("current_mission")
    if mission:
        with st.container(border=True):
            st.subheader("CURRENT MISSION")
            mission_cols = st.columns([3, 1, 3, 1])
            mission_cols[0].markdown(f"**{mission.get('title') or 'Next action'}**")
            mission_cols[1].metric("Time", f"{int(mission.get('estimated_minutes') or 30)} min")
            mission_cols[2].write(mission.get("expected_outcome") or "-")
            if mission_cols[3].button("DONE", type="primary", key=f"mission_done_{mission['id']}"):
                complete_execution_task(mission["id"])
                st.rerun()
    else:
        st.info("No current mission. Add one clear next action to restart execution flow.")

    render_execution_rows(execution.get("money_is_here") or [], "money_here", limit=8)

    st.subheader("NEXT ACTION ⚡")
    render_execution_rows(execution.get("next_actions") or [], "next_action", limit=10)

    st.subheader("PARKING LOT 📦")
    parking_lot = execution.get("parking_lot") or []
    if not parking_lot:
        st.info("No ambiguous projects waiting for a next action.")
    else:
        for item in parking_lot:
            cols = st.columns([3, 2, 2, 2])
            cols[0].write(item.get("title") or "Untitled project")
            cols[1].write(item.get("organization_name") or "-")
            cols[2].write(item.get("stage") or "-")
            cols[3].write(item.get("next_action") or "Needs next action")

    kpi_cols = st.columns(6)
    labels = [
        ("Follow-ups Due Today", "due_today"),
        ("Overdue Follow-ups", "overdue"),
        ("New Leads", "new_leads"),
        ("Warm Relationships", "warm_relationships"),
        ("Qualified Leads", "qualified_leads"),
        ("Customers", "customers"),
    ]
    for col, (label, key) in zip(kpi_cols, labels):
        col.metric(label, int(kpis.get(key) or 0))

    priority_cols = st.columns(6)
    priority_cols[0].metric("Today's Outreach Queue", outreach_queue["today"])
    priority_cols[1].metric("This Week", outreach_queue["this_week"])
    priority_cols[2].metric("Next 30 Days", outreach_queue["next_30_days"])
    priority_cols[3].metric("High Priority Contacts", int(kpis.get("high_priority_contacts") or 0))
    priority_cols[4].metric("China Leads", int(kpis.get("china_leads") or 0))
    priority_cols[5].metric("China Warm Relationships", int(kpis.get("china_warm_relationships") or 0))

    st.subheader("Backup Status")
    backup_cols = st.columns(3)
    backup_cols[0].metric("Last Backup", last_backup.get("timestamp", "No successful backup") if last_backup else "No successful backup")
    backup_cols[1].metric("Commit", ((last_backup.get("commit_hash", "") if last_backup else "") or "-")[:8])
    backup_cols[2].metric("Status", "Synced" if last_backup else "No backup")

    show_quote_follow_up_engine()

    intelligence_cols = st.columns(2)
    with intelligence_cols[0]:
        st.subheader("Relationship Funnel")
        funnel = data["relationship_funnel"]
        funnel_cols = st.columns(len(funnel))
        for col, stage in zip(funnel_cols, funnel):
            delta = ""
            if stage["conversion_rate"] is not None:
                delta = f"{stage['conversion_rate']}% from previous"
            col.metric(stage["stage"], stage["count"], delta=delta)
    with intelligence_cols[1]:
        st.subheader("CRM Data Quality")
        st.metric("Average Completeness", f"{data['data_quality']['average_score']}%")
        st.caption(f"Measured across {data['data_quality']['record_count']} lead records.")

    if int(kpis.get("no_followup") or 0):
        st.warning(f"{int(kpis.get('no_followup') or 0)} leads need activation scheduling.")
        if st.button("Activate Missing Follow-ups", key="dashboard_activate_followups"):
            result = initialize_missing_lead_followups()
            st.success(
                f"Activated {result['updated']} leads"
                + (f" from {result['start_date']} to {result['end_date']}." if result["updated"] else ".")
            )
            st.rerun()

    def open_lead_button(row, key_prefix):
        if st.button("Open", key=f"{key_prefix}_{row['lead_id']}"):
            st.session_state.selected_lead_id = row["lead_id"]
            st.session_state.pending_page = "Leads List"
            st.rerun()

    def show_mini_rows(rows, key_prefix):
        if not rows:
            st.info("No records.")
            return
        for row in rows:
            cols = st.columns([2, 2, 1, 1, 1])
            cols[0].write(row["contact_name"] or "No contact")
            cols[1].write(row["organization_name"] or "No organization")
            cols[2].write(row["lead_status"])
            cols[3].write(row["next_action_date"] or row["due_bucket"])
            with cols[4]:
                open_lead_button(row, key_prefix)

    st.subheader("Today's Action List")
    if not data["today_action_list"]:
        st.info("No outreach actions due today.")
    else:
        header_cols = st.columns([1, 2, 2, 1, 2, 2, 2, 2, 1, 1, 1, 1])
        header_cols[0].caption("Action Score")
        header_cols[1].caption("Contact")
        header_cols[2].caption("Company")
        header_cols[3].caption("Country")
        header_cols[4].caption("Relationship")
        header_cols[5].caption("Health")
        header_cols[6].caption("Next Action")
        header_cols[7].caption("Reason")
        header_cols[8].caption("Why")
        header_cols[9].caption("Open")
        header_cols[10].caption("Done")
        header_cols[11].caption("Snooze")
    for row in data["today_action_list"]:
        cols = st.columns([1, 2, 2, 1, 2, 2, 2, 2, 1, 1, 1, 1])
        with cols[0]:
            action_score_badge(row["action_score"])
        cols[1].write(row["contact_name"] or "No contact")
        cols[2].write(row["organization_name"] or "No organization")
        cols[3].write(row["country"] or "-")
        cols[4].write(row["relationship_status"] or row["lead_status"] or "-")
        with cols[5]:
            health_badge(row.get("relationship_health"))
        cols[6].write(row["recommended_action"] or row["next_action"] or "Follow up")
        cols[7].write(row.get("action_reason") or row["due_bucket"])
        with cols[8]:
            with st.popover("Why"):
                st.write(f"Reason: {row.get('action_reason') or row['due_bucket']}")
                st.write(f"Due date: {row.get('next_action_date') or '-'}")
                st.write(f"Overdue days: {row.get('overdue_days') or 0}")
                st.write("Score components:")
                breakdown = row.get("action_score_breakdown") or []
                if breakdown:
                    for item in breakdown:
                        st.write(f"+{item['points']} {item['label']}")
                else:
                    st.write("No score boosters yet.")
        if cols[9].button("Open", key=f"dash_action_open_{row['lead_id']}"):
            st.session_state.selected_lead_id = row["lead_id"]
            st.session_state.pending_page = "Leads List"
            st.rerun()
        if cols[10].button("Done", key=f"dash_action_done_{row['lead_id']}"):
            complete_follow_up(row["lead_id"])
            st.rerun()
        if cols[11].button("Snooze", key=f"dash_action_snooze_{row['lead_id']}"):
            snooze_follow_up(row["lead_id"], 7)
            st.rerun()

    st.subheader("China Network")
    china_network = pd.DataFrame(data["china_network"])
    st.dataframe(china_network, use_container_width=True, hide_index=True)

    st.subheader("Overdue Follow-ups")
    show_mini_rows(data["overdue_followups"], "dash_overdue")

    st.subheader("Warm Relationships")
    show_mini_rows(data["warm_relationships"], "dash_warm")

    st.subheader("Campaign Progress")
    st.dataframe(pd.DataFrame(data["campaign_progress"]), use_container_width=True, hide_index=True)

    st.subheader("Country Pipeline")
    st.dataframe(pd.DataFrame(data["country_pipeline"]), use_container_width=True, hide_index=True)


def format_bytes(size_bytes):
    size = float(size_bytes or 0)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def run_git_command(args, repo_path=None, timeout=30):
    cwd = repo_path or Path.cwd()
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        shell=False,
    )


def git_output(result):
    return "\n".join(part.strip() for part in [result.stdout, result.stderr] if part.strip())


def is_ignored_git_status_path(path_text):
    clean_path = (path_text or "").replace("\\", "/").strip().strip('"')
    if not clean_path:
        return False
    return (
        clean_path == "data/git_backup_running.lock"
        or clean_path == "data/growth_engine.db"
        or clean_path.endswith(".lock")
        or clean_path.startswith("data/backups/")
        or (clean_path.startswith("data/") and clean_path.endswith(".db"))
    )


def parse_git_status_lines(status_text):
    changes = []
    for raw_line in (status_text or "").splitlines():
        if not raw_line.strip():
            continue
        path_text = raw_line[3:].strip() if len(raw_line) > 3 else raw_line.strip()
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        if is_ignored_git_status_path(path_text):
            continue
        changes.append({"status": raw_line[:2].strip() or "?", "path": path_text})
    return changes


def detect_git_error(message, repo_path):
    lower = (message or "").lower()
    git_dir = Path(repo_path) / ".git" if repo_path else None
    for lock_name in ["index.lock", "packed-refs.lock"]:
        lock_path = git_dir / lock_name if git_dir else None
        if lock_path and lock_path.exists():
            return "Permission Error", f"{lock_name} exists", "Close Git/Python processes or run backup_git.bat with force unlock."
    if "permission denied" in lower or "access is denied" in lower:
        return "Permission Error", message, "Run: attrib -R .git /S /D and icacls .git /grant %USERNAME%:F /T"
    if "authentication failed" in lower or "could not read username" in lower:
        return "Push Failed", message, "Check Git remote credentials or sign in to your Git provider."
    if "could not resolve host" in lower or "failed to connect" in lower or "remote unavailable" in lower:
        return "Push Failed", message, "Check internet connection and remote URL."
    if message:
        return "Push Failed", message, "Run backup_git.bat for detailed diagnostics."
    return "", "", ""


def get_git_health():
    health = {
        "repo_path": "",
        "branch": "",
        "remote_url": "",
        "last_commit_hash": "",
        "last_commit_time": "",
        "last_push_time": "",
        "status": "Push Failed",
        "indicator": "Red",
        "error_message": "",
        "suggested_fix": "",
        "uncommitted_changes": False,
        "uncommitted_files": [],
        "ahead": 0,
        "behind": 0,
    }

    root_result = run_git_command(["git", "rev-parse", "--show-toplevel"])
    if root_result.returncode != 0:
        message = git_output(root_result)
        health["error_message"] = message
        health["suggested_fix"] = "Open the app from inside a Git repository."
        return health

    repo_path = Path(root_result.stdout.strip()).resolve()
    health["repo_path"] = str(repo_path)

    branch_result = run_git_command(["git", "branch", "--show-current"], repo_path)
    remote_result = run_git_command(["git", "remote", "get-url", "origin"], repo_path)
    commit_result = run_git_command(["git", "log", "-1", "--format=%H"], repo_path)
    commit_time_result = run_git_command(["git", "log", "-1", "--format=%ci"], repo_path)
    status_result = run_git_command(["git", "status", "--short"], repo_path)

    health["branch"] = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
    health["remote_url"] = remote_result.stdout.strip() if remote_result.returncode == 0 else ""
    health["last_commit_hash"] = commit_result.stdout.strip() if commit_result.returncode == 0 else ""
    health["last_commit_time"] = commit_time_result.stdout.strip() if commit_time_result.returncode == 0 else ""
    health["uncommitted_files"] = parse_git_status_lines(status_result.stdout) if status_result.returncode == 0 else []
    health["uncommitted_changes"] = bool(health["uncommitted_files"])

    if status_result.returncode != 0:
        message = git_output(status_result)
        status, error, fix = detect_git_error(message, repo_path)
        health["status"] = status or "Push Failed"
        health["error_message"] = error
        health["suggested_fix"] = fix
        return health

    branch = health["branch"]
    if branch:
        remote_ref = f"origin/{branch}"
        push_time_result = run_git_command(["git", "log", "-1", "--format=%ci", remote_ref], repo_path)
        if push_time_result.returncode == 0:
            health["last_push_time"] = push_time_result.stdout.strip()

        ahead_result = run_git_command(
            ["git", "rev-list", "--left-right", "--count", f"HEAD...{remote_ref}"],
            repo_path,
        )
        if ahead_result.returncode == 0:
            parts = ahead_result.stdout.strip().split()
            if len(parts) == 2:
                health["ahead"] = int(parts[0])
                health["behind"] = int(parts[1])
        else:
            message = git_output(ahead_result)
            status, error, fix = detect_git_error(message, repo_path)
            health["error_message"] = error
            health["suggested_fix"] = fix

    lock_status, lock_error, lock_fix = detect_git_error("", repo_path)
    if lock_status == "Permission Error":
        health["status"] = lock_status
        health["indicator"] = "Red"
        health["error_message"] = lock_error
        health["suggested_fix"] = lock_fix
        return health

    if health["behind"] > 0:
        health["status"] = "Behind Remote"
        health["indicator"] = "Red"
    elif health["ahead"] > 0:
        health["status"] = "Ahead of Remote"
        health["indicator"] = "Yellow"
    elif health["uncommitted_changes"]:
        health["status"] = "Uncommitted Changes"
        health["indicator"] = "Yellow"
        changed_files = ", ".join(item["path"] for item in health["uncommitted_files"][:8])
        remaining = len(health["uncommitted_files"]) - 8
        suffix = f" and {remaining} more" if remaining > 0 else ""
        health["error_message"] = f"Uncommitted changes exist: {changed_files}{suffix}"
        health["suggested_fix"] = "Run Backup Now to commit and push current work."
    elif health["error_message"]:
        health["status"] = "Push Failed"
        health["indicator"] = "Red"
    else:
        health["status"] = "Synced with remote"
        health["indicator"] = "Green"

    return health


def render_git_indicator(indicator):
    color = {"Green": "#2ecc71", "Yellow": "#ffcc00", "Red": "#ff5a5f"}.get(indicator, "#94a3b8")
    st.markdown(
        f"""
        <div style="display:inline-block;background:{color};width:14px;height:14px;border-radius:50%;margin-right:8px;"></div>
        <span style="font-weight:700;">{indicator}</span>
        """,
        unsafe_allow_html=True,
    )


def parse_backup_output(output):
    result = {
        "branch": "",
        "commit_hash": "",
        "push_status": "failed",
    }
    for line in (output or "").splitlines():
        clean = line.strip()
        lower = clean.lower()
        if lower.startswith("branch:"):
            result["branch"] = clean.split(":", 1)[1].strip()
        elif lower.startswith("commit hash:"):
            result["commit_hash"] = clean.split(":", 1)[1].strip()
        elif lower.startswith("push status:"):
            result["push_status"] = clean.split(":", 1)[1].strip().lower()
    return result


def run_git_backup_now(message="Auto backup CRM progress"):
    repo_health = get_git_health()
    repo_path = Path(repo_health["repo_path"] or Path.cwd())
    script_path = repo_path / "scripts" / "git_backup.py"
    if not script_path.exists():
        output = f"Backup script not found: {script_path}"
        record_backup_history("", repo_health.get("branch", ""), "failed", output)
        return 1, output

    st.session_state.git_backup_running = True
    set_app_setting("git_backup_running", "1")
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--message",
                message,
                "--force-unlock",
            ],
            cwd=repo_path,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
            shell=False,
        )
        output = git_output(result) or "No output."
        parsed = parse_backup_output(output)
        status = "succeeded" if result.returncode == 0 and parsed["push_status"] == "succeeded" else "failed"
        record_backup_history(
            parsed["commit_hash"],
            parsed["branch"] or repo_health.get("branch", ""),
            status,
            output,
        )
        if status == "succeeded":
            set_app_setting("git_last_auto_backup_at", datetime.now().isoformat(timespec="seconds"))
        return result.returncode, output
    except Exception as exc:
        output = str(exc)
        record_backup_history("", repo_health.get("branch", ""), "failed", output)
        return 1, output
    finally:
        st.session_state.git_backup_running = False
        set_app_setting("git_backup_running", "0")


def auto_backup_interval_minutes(value):
    return {
        "Off": None,
        "30 min": 30,
        "1 hour": 60,
        "4 hours": 240,
    }.get(value)


def maybe_run_auto_git_backup():
    if st.session_state.get("git_backup_auto_checked"):
        return
    st.session_state.git_backup_auto_checked = True

    interval_label = get_app_setting("git_auto_backup_every", "Off")
    interval_minutes = auto_backup_interval_minutes(interval_label)
    if not interval_minutes:
        return
    if get_app_setting("git_backup_running", "0") == "1":
        return

    last_run = get_app_setting("git_last_auto_backup_at", "")
    should_run = True
    if last_run:
        try:
            last_run_at = datetime.fromisoformat(last_run)
            should_run = datetime.now() - last_run_at >= timedelta(minutes=interval_minutes)
        except ValueError:
            should_run = True

    if should_run:
        returncode, output = run_git_backup_now("Auto backup CRM progress")
        st.session_state.git_backup_output = output
        st.session_state.git_backup_returncode = returncode


def show_admin():
    st.title("Admin")

    with st.expander("Database Backup Status", expanded=False):
        status = get_database_backup_status()
        col1, col2, col3 = st.columns(3)
        col1.metric("Current DB Size", format_bytes(status["db_size_bytes"]))
        col2.metric("Backups", status["backup_count"])
        col3.metric("Latest Backup Time", status["latest_backup_time"] or "No backups")
        if status["latest_backup_name"]:
            st.caption(f"Latest backup: {status['latest_backup_name']}")

    with st.expander("Clean Test Opportunities", expanded=False):
        st.caption("Preview only obvious test opportunities before deletion. Deletion requires typed confirmation.")
        candidates = get_test_opportunity_candidates()
        if not candidates:
            st.info("No obvious test opportunities found.")
        else:
            st.warning(f"{len(candidates)} test-like opportunities match the cleanup rule.")
            st.dataframe(pd.DataFrame(candidates), use_container_width=True, hide_index=True)
            confirm_text = st.text_input(
                "Type CLEAN TEST OPPORTUNITIES to delete the previewed records",
                key="clean_test_opportunities_confirm",
            )
            if st.button(
                "Clean Test Opportunities",
                type="primary",
                disabled=confirm_text != "CLEAN TEST OPPORTUNITIES",
                key="clean_test_opportunities_button",
            ):
                deleted = delete_test_opportunities([row["id"] for row in candidates])
                st.success(f"Deleted {deleted} test opportunities.")
                st.rerun()

    with st.expander("Git Status", expanded=False):
        git_health = get_git_health()
        if st.button("Refresh Git Status", key="refresh_git_status"):
            st.rerun()

        git_cols = st.columns(3)
        git_cols[0].text_input("Repository Path", value=git_health["repo_path"], disabled=True)
        git_cols[1].text_input("Current Branch", value=git_health["branch"], disabled=True)
        git_cols[2].text_input("Remote URL", value=git_health["remote_url"], disabled=True)

        git_cols2 = st.columns(4)
        git_cols2[0].text_input("Last Commit Hash", value=git_health["last_commit_hash"], disabled=True)
        git_cols2[1].text_input("Last Commit Time", value=git_health["last_commit_time"], disabled=True)
        git_cols2[2].text_input("Last Push Time", value=git_health["last_push_time"], disabled=True)
        with git_cols2[3]:
            st.write("Status")
            render_git_indicator(git_health["indicator"])
            st.caption(git_health["status"])

        if git_health["error_message"]:
            st.error(git_health["error_message"])
        if git_health["suggested_fix"]:
            st.info(git_health["suggested_fix"])
        if git_health["uncommitted_files"]:
            st.caption("Remaining uncommitted files")
            st.dataframe(
                pd.DataFrame(git_health["uncommitted_files"]),
                use_container_width=True,
                hide_index=True,
            )

        auto_options = ["Off", "30 min", "1 hour", "4 hours"]
        current_auto_backup = get_app_setting("git_auto_backup_every", "Off")
        auto_cols = st.columns([1, 1, 2])
        selected_auto_backup = auto_cols[0].selectbox(
            "Auto Backup Every",
            auto_options,
            index=auto_options.index(current_auto_backup) if current_auto_backup in auto_options else 0,
        )
        if auto_cols[1].button("Save Auto Backup", key="save_git_auto_backup"):
            set_app_setting("git_auto_backup_every", selected_auto_backup)
            st.success("Auto backup setting saved.")
            st.rerun()

        backup_running = st.session_state.get("git_backup_running", False) or get_app_setting("git_backup_running", "0") == "1"
        backup_label = "Backup Running..." if backup_running else "Backup Now"
        if auto_cols[2].button(backup_label, key="admin_backup_now", disabled=backup_running):
            with st.spinner("Running Git backup..."):
                returncode, output = run_git_backup_now("Auto backup CRM progress")
                st.session_state.git_backup_output = output
                st.session_state.git_backup_returncode = returncode
                st.session_state.git_backup_completed_at = datetime.now().isoformat(timespec="seconds")
                if returncode == 0:
                    st.session_state.git_backup_flash = "Git backup succeeded. Refreshing Git status..."
                else:
                    st.session_state.git_backup_flash = "Git backup failed. Refreshing Git status..."
                st.rerun()

        if st.session_state.get("git_backup_flash"):
            if st.session_state.get("git_backup_returncode") == 0:
                st.success(st.session_state.git_backup_flash)
            else:
                st.error(st.session_state.git_backup_flash)
            st.session_state.pop("git_backup_flash", None)

        if st.session_state.get("git_backup_output"):
            st.caption("Backup output")
            st.code(st.session_state.git_backup_output)

        history = get_backup_history(20)
        st.caption("Backup History")
        if history:
            st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
        else:
            st.info("No backup history yet.")

    with st.expander("System Settings", expanded=False):
        selected_ui_scale = st.radio(
            "UI Scale",
            UI_SCALE_OPTIONS,
            key="admin_ui_scale",
            index=UI_SCALE_OPTIONS.index(st.session_state.ui_scale),
        )
        st.subheader("Document Parser")
        parser_provider_options = ["Auto", "Regex", "OpenAI", "Gemini"]
        current_parser_provider = get_app_setting("document_parser_provider", "Auto")
        parser_provider = st.selectbox(
            "Parser Provider",
            parser_provider_options,
            index=parser_provider_options.index(current_parser_provider) if current_parser_provider in parser_provider_options else 0,
            key="admin_document_parser_provider",
        )
        parser_cols = st.columns(2)
        openai_model = parser_cols[0].text_input("OpenAI Parser Model", value=get_app_setting("openai_parser_model", "gpt-4.1-mini"))
        gemini_model = parser_cols[1].text_input("Gemini Parser Model", value=get_app_setting("gemini_parser_model", "gemini-1.5-pro"))
        key_cols = st.columns(2)
        openai_key = key_cols[0].text_input("OpenAI API Key", value=get_app_setting("openai_api_key", ""), type="password")
        gemini_key = key_cols[1].text_input("Gemini API Key", value=get_app_setting("gemini_api_key", ""), type="password")
        if st.button("Save System Settings", key="save_system_settings"):
            set_app_setting("ui_scale", selected_ui_scale)
            set_app_setting("document_parser_provider", parser_provider)
            set_app_setting("openai_parser_model", openai_model)
            set_app_setting("gemini_parser_model", gemini_model)
            set_app_setting("openai_api_key", openai_key)
            set_app_setting("gemini_api_key", gemini_key)
            st.session_state.ui_scale = selected_ui_scale
            st.session_state.persisted_ui_scale = selected_ui_scale
            st.success("System settings saved.")
            st.rerun()

    with st.expander("Email Settings", expanded=False):
        email_sending_tab, email_tracking_tab, email_bounce_tab, email_cleanup_tab, email_signature_tab = st.tabs(
            [
                "Email Sending",
                "Email Tracking",
                "Email Bounce Processing",
                "Invalid / Bounced Email Cleanup",
                "Email Signature",
            ]
        )

        with email_sending_tab:
            smtp_cols = st.columns(2)
            smtp_host = smtp_cols[0].text_input("SMTP Host", value=get_app_setting("smtp_host", ""))
            smtp_port = smtp_cols[1].text_input("SMTP Port", value=get_app_setting("smtp_port", "587"))
            smtp_user = smtp_cols[0].text_input("SMTP Username", value=get_app_setting("smtp_username", ""))
            smtp_password = smtp_cols[1].text_input("SMTP Password", value=get_app_setting("smtp_password", ""), type="password")
            smtp_from_email = smtp_cols[0].text_input("From Email", value=get_app_setting("smtp_from_email", ""))
            smtp_from_name = smtp_cols[1].text_input("From Name", value=get_app_setting("smtp_from_name", "1Aim"))
            current_encryption = get_app_setting("smtp_encryption", "")
            if not current_encryption:
                current_encryption = "TLS" if get_app_setting("smtp_use_tls", "1") == "1" else "None"
            encryption_options = ["SSL", "TLS", "None"]
            smtp_encryption = st.selectbox(
                "Encryption Type",
                encryption_options,
                index=encryption_options.index(current_encryption) if current_encryption in encryption_options else 1,
            )
            debug_cols = st.columns(3)
            debug_cols[0].metric("Host", smtp_host or "-")
            debug_cols[1].metric("Port", smtp_port or "-")
            debug_cols[2].metric("Encryption Type", smtp_encryption)
            if st.button("Save Email Settings", key="save_smtp_settings"):
                for key, value in [
                    ("smtp_host", smtp_host),
                    ("smtp_port", smtp_port),
                    ("smtp_username", smtp_user),
                    ("smtp_password", smtp_password),
                    ("smtp_from_email", smtp_from_email),
                    ("smtp_from_name", smtp_from_name),
                    ("smtp_encryption", smtp_encryption),
                    ("smtp_use_tls", "1" if smtp_encryption == "TLS" else "0"),
                ]:
                    set_app_setting(key, value)
                st.success("Email settings saved.")
                st.rerun()

            test_connection_disabled = not bool(get_app_setting("smtp_host", ""))
            if st.button("Test Connection", disabled=test_connection_disabled, key="test_smtp_connection"):
                result = test_smtp_connection()
                result_cols = st.columns(3)
                result_cols[0].write(result["connection"])
                result_cols[1].write(result["encryption"])
                result_cols[2].write(result["authentication"])
                if result["ok"]:
                    st.success("SMTP connection test passed.")
                else:
                    st.error(result["error"])

            test_cols = st.columns([2, 1])
            test_email = test_cols[0].text_input("Test Email To", key="smtp_test_email")
            can_send_test = is_smtp_configured() and is_valid_email(test_email)
            if test_cols[1].button("Send Test Email", disabled=not can_send_test, key="send_smtp_test_email"):
                ok, error_message = send_email_via_smtp(
                    test_email.strip(),
                    "1Aim SMTP Test",
                    "This is a test email from 1Aim Growth Engine. SMTP sending is configured correctly.",
                )
                if ok:
                    st.success("Test email sent.")
                else:
                    st.error(f"Test email failed: {error_message}")
            if not is_smtp_configured():
                st.caption("Save SMTP host and from email before sending a test email.")
            elif test_email and not is_valid_email(test_email):
                st.caption("Enter a valid test email address.")

        with email_tracking_tab:
            st.caption("Open tracking needs a public URL that email clients can reach, such as a deployed app URL or tunnel URL.")
            tracking_base_url = st.text_input(
                "Tracking Base URL",
                value=get_app_setting("tracking_base_url", ""),
                placeholder="https://your-public-app-url",
                key="tracking_base_url_input",
            )
            if st.button("Save Tracking Settings", key="save_tracking_settings"):
                set_app_setting("tracking_base_url", tracking_base_url.strip())
                st.success("Tracking settings saved.")
                st.rerun()
            if tracking_base_url:
                sample_separator = "&" if "?" in tracking_base_url else "?"
                st.caption(f"Sample pixel URL: {tracking_base_url.rstrip('/')}{sample_separator}track_open=TRACKING_TOKEN")
            else:
                st.warning("Open tracking is disabled until Tracking Base URL is set.")

            st.subheader("Reply Tracking")
            reply_cols = st.columns([1, 1, 2])
            reply_limit = reply_cols[0].selectbox("Mailbox Scan Limit", [50, 100, 200, 500], index=1, key="reply_scan_limit")
            reply_cols[1].metric("IMAP Host", get_app_setting("imap_host", "mail.1aimlogistics.com"))
            reply_cols[2].caption("Uses the same IMAP username/password as SMTP settings.")
            if st.button("Process Replies", key="process_reply_emails"):
                with st.spinner("Scanning mailbox for campaign replies..."):
                    st.session_state.reply_processing_result = process_email_replies(reply_limit)
            reply_result = st.session_state.get("reply_processing_result")
            if reply_result:
                reply_result_cols = st.columns(4)
                reply_result_cols[0].metric("Reply Emails Scanned", reply_result.get("scanned", 0))
                reply_result_cols[1].metric("Replies Found", reply_result.get("replies_found", 0))
                reply_result_cols[2].metric("Messages Updated", reply_result.get("messages_updated", 0))
                reply_result_cols[3].metric("Unmatched", len(reply_result.get("unmatched", [])))
                if reply_result.get("unmatched"):
                    st.caption("Unmatched reply emails")
                    st.dataframe(pd.DataFrame({"Reply": reply_result["unmatched"]}), use_container_width=True, hide_index=True)
                if reply_result.get("errors"):
                    st.error(" | ".join(reply_result["errors"]))

        with email_bounce_tab:
            imap_cols = st.columns(4)
            imap_cols[0].metric("IMAP Host", get_app_setting("imap_host", "mail.1aimlogistics.com"))
            imap_cols[1].metric("IMAP Port", get_app_setting("imap_port", "993"))
            imap_cols[2].metric("Encryption", "SSL")
            imap_cols[3].metric("Username", get_app_setting("smtp_username", "") or "-")
            max_bounce_messages = st.selectbox("Mailbox Scan Limit", [50, 100, 200, 500], index=1)
            if st.button("Process Bounce Emails", key="process_bounce_emails"):
                with st.spinner("Reading bounce emails from mailbox..."):
                    result = process_email_bounces(max_bounce_messages)
                st.session_state.bounce_processing_result = result

            bounce_result = st.session_state.get("bounce_processing_result")
            if bounce_result:
                bounce_cols = st.columns(5)
                bounce_cols[0].metric("Bounce Emails Scanned", bounce_result.get("scanned", 0))
                bounce_cols[1].metric("Hard Bounces Found", bounce_result.get("hard_bounces", 0))
                bounce_cols[2].metric("Soft Bounces Found", bounce_result.get("soft_bounces", 0))
                bounce_cols[3].metric("Contacts Updated", bounce_result.get("contacts_updated", 0))
                bounce_cols[4].metric("Unmatched", len(bounce_result.get("unmatched", [])))
                if bounce_result.get("unmatched"):
                    st.caption("Unmatched bounced emails")
                    st.dataframe(pd.DataFrame({"Email": bounce_result["unmatched"]}), use_container_width=True, hide_index=True)
                if bounce_result.get("errors"):
                    st.error(" | ".join(bounce_result["errors"]))

        with email_cleanup_tab:
            cleanup_filters = st.columns([1, 2, 1])
            cleanup_status = cleanup_filters[0].selectbox("Email Status Filter", ["All", "Bounced", "Invalid"], key="email_cleanup_status")
            cleanup_search = cleanup_filters[1].text_input("Search Contact / Company / Email", key="email_cleanup_search")
            cleanup_limit = cleanup_filters[2].selectbox("Rows", [25, 50, 100, 200], index=1, key="email_cleanup_limit")
            bad_email_rows = get_invalid_email_contacts(cleanup_status, cleanup_search, cleanup_limit)
            status_counts = {
                "Bounced": sum(1 for row in bad_email_rows if row.get("email_status") == "Bounced"),
                "Invalid": sum(1 for row in bad_email_rows if row.get("email_status") == "Invalid"),
            }
            cleanup_metric_cols = st.columns(3)
            cleanup_metric_cols[0].metric("Showing", len(bad_email_rows))
            cleanup_metric_cols[1].metric("Bounced", status_counts["Bounced"])
            cleanup_metric_cols[2].metric("Invalid", status_counts["Invalid"])
            if not bad_email_rows:
                st.info("No invalid or bounced emails found for this filter.")
            for row in bad_email_rows:
                title = f"{row.get('contact_name') or row.get('full_name') or 'No contact'} - {row.get('email') or 'No email'}"
                with st.expander(title):
                    meta_cols = st.columns(4)
                    meta_cols[0].write(row.get("organization_name") or "-")
                    meta_cols[1].write(row.get("country") or "-")
                    meta_cols[2].write(row.get("city") or "-")
                    meta_cols[3].write(row.get("email_status") or "Unknown")
                    corrected_email = st.text_input(
                        "Corrected Email",
                        value=row.get("email") or "",
                        key=f"cleanup_email_{row['contact_id']}",
                    )
                    action_cols = st.columns(5)
                    if action_cols[0].button("Save as Valid", key=f"cleanup_save_valid_{row['contact_id']}"):
                        if is_valid_email(corrected_email):
                            update_contact_email_address(row["contact_id"], corrected_email.strip(), "Valid", "Email cleanup")
                            st.success("Email corrected and marked Valid.")
                            st.rerun()
                        else:
                            st.error("Enter a valid email before saving.")
                    if action_cols[1].button("Mark Valid", key=f"cleanup_mark_valid_{row['contact_id']}"):
                        update_contact_email_status(row["contact_id"], "Valid", "Email cleanup")
                        st.rerun()
                    if action_cols[2].button("Mark Invalid", key=f"cleanup_mark_invalid_{row['contact_id']}"):
                        update_contact_email_status(row["contact_id"], "Invalid", "Email cleanup")
                        st.rerun()
                    if action_cols[3].button("Mark Bounced", key=f"cleanup_mark_bounced_{row['contact_id']}"):
                        update_contact_email_status(row["contact_id"], "Bounced", "Email cleanup")
                        st.rerun()
                    if action_cols[4].button("Open Lead", key=f"cleanup_open_lead_{row['contact_id']}", disabled=not row.get("lead_id")):
                        st.session_state.selected_lead_id = row["lead_id"]
                        st.session_state.pending_page = "Leads List"
                        st.rerun()

        with email_signature_tab:
            sig_cols = st.columns(2)
            signature_name = sig_cols[0].text_input("Signature Name", value=get_app_setting("signature_name", "Kien Ho"))
            signature_title = sig_cols[1].text_input("Signature Title", value=get_app_setting("signature_title", "CEO"))
            signature_company = sig_cols[0].text_input("Signature Company", value=get_app_setting("signature_company", "1Aim Logistics"))
            signature_phone = sig_cols[1].text_input("Signature Phone", value=get_app_setting("signature_phone", ""))
            signature_email = sig_cols[0].text_input("Signature Email", value=get_app_setting("signature_email", ""))
            signature_website = sig_cols[1].text_input("Signature Website", value=get_app_setting("signature_website", ""))
            signature_wechat = sig_cols[0].text_input("Signature WeChat", value=get_app_setting("signature_wechat", ""))
            signature_whatsapp = sig_cols[1].text_input("Signature WhatsApp", value=get_app_setting("signature_whatsapp", ""))
            signature_html = st.text_area("HTML Signature", value=get_app_setting("signature_html", ""), height=120)
            if st.button("Save Email Signature", key="save_email_signature"):
                for key, value in [
                    ("signature_name", signature_name),
                    ("signature_title", signature_title),
                    ("signature_company", signature_company),
                    ("signature_phone", signature_phone),
                    ("signature_email", signature_email),
                    ("signature_website", signature_website),
                    ("signature_wechat", signature_wechat),
                    ("signature_whatsapp", signature_whatsapp),
                    ("signature_html", signature_html),
                ]:
                    set_app_setting(key, value)
                st.success("Email signature saved.")
                st.rerun()

    with st.expander("CRM Activation", expanded=False):
        capacity_options = [10, 20, 30, 50]
        current_capacity = get_daily_outreach_capacity()
        selected_capacity = st.selectbox(
            "Daily Outreach Capacity",
            capacity_options,
            index=capacity_options.index(current_capacity) if current_capacity in capacity_options else 0,
        )
        if st.button("Save Capacity", key="save_daily_outreach_capacity"):
            set_app_setting("daily_outreach_capacity", str(selected_capacity))
            st.success("Daily outreach capacity saved.")
            st.rerun()

        st.caption("Initialize missing next actions and spread them across the next 30 days.")
        if st.button("Activate Missing Lead Follow-ups", key="admin_activate_followups"):
            result = initialize_missing_lead_followups()
            st.success(
                f"Activated {result['updated']} leads"
                + (f" from {result['start_date']} to {result['end_date']}." if result["updated"] else ".")
            )
            st.rerun()
        if st.button("Recalculate Priority Scores", key="admin_refresh_priority_scores"):
            updated = refresh_lead_priority_scores()
            st.success(f"Priority scores recalculated. Updated {updated} leads.")
            st.rerun()


def show_follow_up_queue():
    st.title("Follow-up Queue")
    rows = get_crm_follow_up_rows()

    if not rows:
        st.info("No follow-ups due right now.")
        return

    def option_values(key):
        values = sorted({row.get(key) or "" for row in rows if row.get(key)})
        return ["All"] + values

    filter_cols = st.columns(4)
    status_filter = filter_cols[0].selectbox(
        "Status",
        ["All"] + sorted({row["lead_status"] for row in rows} | {row["relationship_status"] for row in rows} | {row["customer_status"] for row in rows}),
    )
    country_filter = filter_cols[1].selectbox("Country", option_values("country"))
    city_filter = filter_cols[2].selectbox("City", option_values("city"))
    org_type_filter = filter_cols[3].selectbox("Organization Type", option_values("organization_type"))

    filter_cols2 = st.columns(4)
    campaign_filter = filter_cols2[0].selectbox("Campaign", option_values("campaign"))
    membership_filter = filter_cols2[1].selectbox("Membership", option_values("membership"))
    owner_filter = filter_cols2[2].selectbox("Owner", option_values("owner"))
    due_filter = filter_cols2[3].selectbox(
        "Due",
        ["All", "Overdue", "Today", "This Week", "No Follow-up Date"],
    )

    def matches(row):
        if status_filter != "All" and status_filter not in [
            row["lead_status"],
            row["relationship_status"],
            row["customer_status"],
        ]:
            return False
        for selected, key in [
            (country_filter, "country"),
            (city_filter, "city"),
            (org_type_filter, "organization_type"),
            (campaign_filter, "campaign"),
            (membership_filter, "membership"),
            (owner_filter, "owner"),
        ]:
            if selected != "All" and row.get(key) != selected:
                return False
        if due_filter != "All" and row["due_bucket"] != due_filter:
            return False
        return True

    filtered_rows = [row for row in rows if matches(row)]
    st.caption(f"{len(filtered_rows)} follow-ups")

    def render_contact_buttons(row):
        comm_cols = st.columns(4)
        with comm_cols[0]:
            if row["email"]:
                st.link_button("Email", f"mailto:{row['email']}")
            else:
                st.button("Email", disabled=True, key=f"queue_email_disabled_{row['lead_id']}")
        with comm_cols[1]:
            if row["phone"]:
                st.link_button("Call", f"tel:{row['phone']}")
            else:
                st.button("Call", disabled=True, key=f"queue_call_disabled_{row['lead_id']}")
        with comm_cols[2]:
            whatsapp_number = re.sub(r"[^0-9]", "", row["whatsapp"] or "")
            if whatsapp_number:
                st.link_button("WhatsApp", f"https://wa.me/{whatsapp_number}")
            else:
                st.button("WhatsApp", disabled=True, key=f"queue_wa_disabled_{row['lead_id']}")
        with comm_cols[3]:
            if row["wechat"]:
                components.html(
                    f"""
                    <button
                        style="background:#1c2636;color:#edf2f7;border:1px solid #3d4b63;border-radius:6px;padding:8px 12px;cursor:pointer;width:100%;"
                        onclick="navigator.clipboard.writeText({row['wechat']!r})"
                    >
                        Copy WeChat
                    </button>
                    """,
                    height=42,
                )
            else:
                st.button("WeChat", disabled=True, key=f"queue_wechat_disabled_{row['lead_id']}")

    for row in filtered_rows:
        with st.container():
            top_cols = st.columns([2, 2, 1, 1])
            top_cols[0].markdown(f"**{row['contact_name'] or 'No contact'}**")
            top_cols[0].caption(row["job_title"])
            top_cols[1].markdown(f"**{row['organization_name'] or 'No organization'}**")
            top_cols[1].caption(" / ".join(item for item in [row["country"], row["city"]] if item))
            top_cols[2].write(row["due_bucket"])
            top_cols[3].write(row["next_action_date"] or "No date")

            status_cols = st.columns(7)
            status_cols[0].write(f"Lead: {row['lead_status']}")
            status_cols[1].write(f"Relationship: {row['relationship_status'] or '-'}")
            status_cols[2].write(f"Customer: {row['customer_status'] or '-'}")
            status_cols[3].write(f"Last: {row['last_contacted_at'] or '-'}")
            status_cols[4].write(f"Priority: {row['priority_score']}")
            status_cols[5].write(row["recommended_action"] or row["next_action"] or "No next action")
            status_cols[6].write(f"{row['source']} / {row['campaign']}")

            render_contact_buttons(row)

            action_cols = st.columns(10)
            action_map = [
                ("Contacted", lambda row=row: update_lead_status_action(row["lead_id"], "Contacted")),
                ("Introduced", lambda row=row: update_contact_relationship_action(row["contact_id"], "Introduced") if row["contact_id"] else False),
                ("Replied", lambda row=row: update_lead_status_action(row["lead_id"], "Replied")),
                ("Warm", lambda row=row: update_contact_relationship_action(row["contact_id"], "Warm") if row["contact_id"] else False),
                ("Active", lambda row=row: update_contact_relationship_action(row["contact_id"], "Active") if row["contact_id"] else False),
                ("+3d", lambda row=row: snooze_follow_up(row["lead_id"], 3)),
                ("+7d", lambda row=row: snooze_follow_up(row["lead_id"], 7)),
                ("+30d", lambda row=row: snooze_follow_up(row["lead_id"], 30)),
            ]
            for col, (label, action) in zip(action_cols, action_map):
                if col.button(label, key=f"queue_{label}_{row['lead_id']}"):
                    action()
                    st.rerun()

            if action_cols[8].button("Open", key=f"queue_open_{row['lead_id']}"):
                st.session_state.selected_lead_id = row["lead_id"]
                st.session_state.pending_page = "Leads List"
                st.rerun()

            with action_cols[9]:
                with st.popover("Set Next"):
                    next_action = st.text_input("Next Action", value=row["next_action"], key=f"queue_next_action_{row['lead_id']}")
                    next_date = st.text_input("Next Date", value=row["next_action_date"], key=f"queue_next_date_{row['lead_id']}")
                    if st.button("Save", key=f"queue_save_next_{row['lead_id']}"):
                        update_lead_next_follow_up(row["lead_id"], next_action, next_date)
                        st.rerun()

            st.divider()


OUTREACH_SUBJECT_TEMPLATES = [
    "OLO HCM 2026, {{first_name}}",
    "Vietnam support for {{company}}",
    "Nice to meet you at OLO HCM",
    "{{first_name}}, Vietnam logistics support",
]


OUTREACH_INSTRUCTION_PRESETS = {
    "Friendly OLO Intro": "Use first name only. Friendly tone. Mention OLO HCM 2026. Keep under 120 words. Avoid sounding like mass marketing.",
    "China Agent Outreach": "Use first name only. Friendly but professional tone. Focus on China forwarder cooperation with Vietnam operations and customs support. Keep under 120 words.",
    "WCA Introduction": "Use first name only. Mention WCA network connection. Professional tone. Keep under 120 words. Ask to stay connected for Vietnam inquiries.",
    "Follow-up No Reply": "Use first name only. Short follow-up tone. Mention that I wanted to reconnect briefly. Keep under 90 words. Avoid pressure.",
    "Holiday Greeting": "Warm greeting tone. Do not mention sales directly. Keep under 100 words. Focus on relationship and good wishes.",
    "Custom": "",
}


def evaluate_outreach_quality(draft, subject, message_body):
    plain_body = re.sub(r"<[^>]+>", " ", message_body or "")
    words = re.findall(r"\b\w+\b", plain_body)
    first_name = (draft.get("contact_name") or "").split()[0] if draft.get("contact_name") else ""
    lower_body = plain_body.lower()
    lower_subject = (subject or "").lower()
    spam_words = ["free", "guarantee", "urgent", "limited time", "act now", "winner", "risk-free", "100%"]
    spam_hits = [word for word in spam_words if word in lower_body or word in lower_subject]
    has_greeting = bool(re.search(r"\b(hi|hello|dear)\b", lower_body))
    has_signature = "best regards" in lower_body or "1aim" in lower_body or "</" in (message_body or "")
    uses_first_name = bool(first_name and first_name.lower() in lower_body[:120])

    subject_length = len(subject or "")
    message_length = len(words)
    quality_issues = []
    if subject_length > 70 or subject_length < 8:
        quality_issues.append("Subject length")
    if message_length > 160 or message_length < 35:
        quality_issues.append("Message length")
    if not has_greeting:
        quality_issues.append("Missing greeting")
    if not has_signature:
        quality_issues.append("Missing signature")

    spam_risk = "High" if len(spam_hits) >= 3 else "Medium" if spam_hits else "Low"
    personalization_points = sum(
        [
            uses_first_name,
            bool(draft.get("organization_name") and draft.get("organization_name").lower() in lower_body),
            bool(draft.get("city") and draft.get("city").lower() in lower_body),
            bool(draft.get("job_title") and draft.get("job_title").lower() in lower_body),
        ]
    )
    personalization = "High" if personalization_points >= 3 else "Medium" if personalization_points >= 1 else "Low"
    quality = "Good" if not quality_issues and spam_risk != "High" else "Needs Review"

    return {
        "quality": quality,
        "spam_risk": spam_risk,
        "personalization": personalization,
        "issues": quality_issues,
        "subject_length": subject_length,
        "message_words": message_length,
        "spam_hits": spam_hits,
    }


def show_outreach_campaigns():
    st.title("Outreach Campaigns")
    metrics = get_outreach_campaign_metrics()
    if metrics:
        st.subheader("Campaign Metrics")
        st.dataframe(pd.DataFrame(metrics), use_container_width=True, hide_index=True)

    campaign_result = st.session_state.get("outreach_campaign_result")
    if campaign_result:
        st.subheader("Campaign Results")
        result_cols = st.columns(5)
        result_cols[0].metric("Sent", int(campaign_result.get("sent") or 0))
        result_cols[1].metric("Failed", int(campaign_result.get("failed") or 0))
        result_cols[2].metric("Skipped", int(campaign_result.get("skipped") or 0))
        result_cols[3].write("Campaign")
        result_cols[3].caption(campaign_result.get("campaign_name", "-"))
        result_cols[4].write("Timestamp")
        result_cols[4].caption(campaign_result.get("timestamp", "-"))
        result_action_cols = st.columns(3)
        if result_action_cols[0].button("View Failed", key="view_failed_outreach_results"):
            st.session_state.show_failed_outreach_results = not st.session_state.get("show_failed_outreach_results", False)
        if result_action_cols[1].button("Open Follow-up Queue", key="open_followup_from_campaign_result"):
            st.session_state.pending_page = "Follow-up Queue"
            st.rerun()
        if result_action_cols[2].button("Clear Results", key="clear_outreach_results"):
            st.session_state.pop("outreach_campaign_result", None)
            st.session_state.pop("show_failed_outreach_results", None)
            st.rerun()
        if st.session_state.get("show_failed_outreach_results"):
            failed_messages = campaign_result.get("failed_messages") or []
            if failed_messages:
                st.dataframe(pd.DataFrame(failed_messages), use_container_width=True, hide_index=True)
            else:
                st.info("No failed recipients.")

    st.subheader("Select Campaign Audience")
    options = get_campaign_filter_options()
    templates = get_outreach_campaign_templates()
    template_map = {template["template_name"]: template for template in templates}

    template_cols = st.columns([2, 1])
    selected_template = template_cols[0].selectbox(
        "Campaign Template",
        ["None"] + list(template_map.keys()),
        key="outreach_template_selector",
    )
    if template_cols[1].button("Load Template", key="load_outreach_template", disabled=selected_template == "None"):
        template = template_map[selected_template]
        st.session_state.outreach_campaign_name = template.get("campaign_name") or template["template_name"]
        st.session_state.outreach_subject_template = template.get("subject_template") or OUTREACH_SUBJECT_TEMPLATES[0]
        st.session_state.outreach_campaign_instructions = template.get("instructions") or ""
        st.session_state.outreach_campaign_name_input = st.session_state.outreach_campaign_name
        st.session_state.outreach_subject_template_input = st.session_state.outreach_subject_template
        st.session_state.outreach_campaign_instructions_input = st.session_state.outreach_campaign_instructions
        st.session_state.outreach_subject_preset = "Custom"
        st.session_state.outreach_instruction_preset = "Custom"
        st.session_state.outreach_last_subject_preset = "Custom"
        st.session_state.outreach_last_instruction_preset = "Custom"
        st.rerun()

    filter_cols = st.columns(5)
    campaign_name = filter_cols[0].text_input(
        "Campaign Name",
        value=st.session_state.get("outreach_campaign_name", "1Aim Vietnam Support"),
        key="outreach_campaign_name_input",
    )
    country = filter_cols[1].selectbox("Country", ["All"] + options["countries"])
    membership = filter_cols[2].selectbox("Membership", ["All"] + options["memberships"])
    lead_status = filter_cols[3].selectbox("Lead Status", ["All"] + options["lead_statuses"])
    relationship_status = filter_cols[4].selectbox("Relationship Status", ["All"] + options["relationship_statuses"])
    limit = st.selectbox("Audience Size", [30, 40, 50], index=2)

    subject_preset = st.selectbox(
        "Default Subject Template",
        OUTREACH_SUBJECT_TEMPLATES + ["Custom"],
        key="outreach_subject_preset",
    )
    if subject_preset != "Custom" and st.session_state.get("outreach_last_subject_preset") != subject_preset:
        st.session_state.outreach_subject_template = subject_preset
        st.session_state.outreach_subject_template_input = subject_preset
        st.session_state.outreach_last_subject_preset = subject_preset

    subject_template = st.text_input(
        "Campaign Subject Template",
        value=st.session_state.get("outreach_subject_template", OUTREACH_SUBJECT_TEMPLATES[0]),
        key="outreach_subject_template_input",
        help="Supported tokens: {{first_name}}, {{contact_name}}, {{company}}, {{city}}, {{country}}, {{membership}}, {{job_title}}",
    )

    instruction_preset = st.selectbox(
        "Campaign Instruction Preset",
        list(OUTREACH_INSTRUCTION_PRESETS.keys()),
        key="outreach_instruction_preset",
    )
    if st.session_state.get("outreach_last_instruction_preset") != instruction_preset:
        preset_text = OUTREACH_INSTRUCTION_PRESETS[instruction_preset]
        if instruction_preset != "Custom":
            st.session_state.outreach_campaign_instructions = preset_text
            st.session_state.outreach_campaign_instructions_input = preset_text
        st.session_state.outreach_last_instruction_preset = instruction_preset

    instructions = st.text_area(
        "Campaign Instructions",
        value=st.session_state.get("outreach_campaign_instructions", ""),
        height=120,
        key="outreach_campaign_instructions_input",
        placeholder='Example: Use first name only. Keep under 120 words. More friendly. Mention OLO HCM. Avoid saying "backend support".',
    )

    filters = {
        "country": "" if country == "All" else country,
        "membership": "" if membership == "All" else membership,
        "lead_status": "" if lead_status == "All" else lead_status,
        "relationship_status": "" if relationship_status == "All" else relationship_status,
        "limit": limit,
    }
    invalid_email_skip_count = get_campaign_invalid_email_skip_count(filters)
    if invalid_email_skip_count:
        st.warning(f"{invalid_email_skip_count} contacts skipped due to bounced/invalid email.")

    save_cols = st.columns([2, 1])
    template_name = save_cols[0].text_input("Save Template As", key="save_outreach_template_name")
    if save_cols[1].button("Save Campaign Template", key="save_outreach_template", disabled=not template_name.strip()):
        save_outreach_campaign_template(
            template_name.strip(),
            campaign_name.strip(),
            subject_template.strip(),
            instructions.strip(),
        )
        st.success("Campaign template saved.")
        st.rerun()

    def build_outreach_drafts(max_rows):
        draft_filters = {**filters, "limit": max_rows}
        audience = get_campaign_audience(draft_filters)
        drafts = []
        for row in audience:
            if not is_valid_email(row.get("email")):
                continue
            drafts.append(
                {
                    **row,
                    "subject": generate_outreach_subject(row, campaign_name, subject_template),
                    "message_body": generate_outreach_message(row, campaign_name, instructions),
                    "message_version": 1,
                    "send": True,
                }
            )
        return drafts, draft_filters

    generation_cols = st.columns(3)
    if generation_cols[0].button("Preview First 5", key="preview_outreach_messages"):
        drafts, draft_filters = build_outreach_drafts(5)
        st.session_state.outreach_campaign_name = campaign_name
        st.session_state.outreach_subject_template = subject_template
        st.session_state.outreach_campaign_instructions = instructions
        st.session_state.outreach_campaign_filters = draft_filters
        st.session_state.outreach_invalid_email_skip_count = invalid_email_skip_count
        st.session_state.outreach_campaign_drafts = drafts
        st.session_state.outreach_campaign_mode = "Preview First 5"
        st.session_state.outreach_preview_sent = False
        st.session_state.outreach_final_reviewed = False
        st.success(f"Generated preview for {len(drafts)} emails.")
        st.rerun()

    if generation_cols[1].button("Regenerate Campaign", key="regenerate_outreach_messages"):
        current_count = len(st.session_state.get("outreach_campaign_drafts", [])) or limit
        drafts, draft_filters = build_outreach_drafts(current_count)
        st.session_state.outreach_campaign_name = campaign_name
        st.session_state.outreach_subject_template = subject_template
        st.session_state.outreach_campaign_instructions = instructions
        st.session_state.outreach_campaign_filters = draft_filters
        st.session_state.outreach_invalid_email_skip_count = invalid_email_skip_count
        st.session_state.outreach_campaign_drafts = drafts
        st.session_state.outreach_campaign_mode = f"Regenerated {current_count}"
        st.session_state.outreach_preview_sent = False
        st.session_state.outreach_final_reviewed = False
        st.success(f"Regenerated {len(drafts)} personalized messages.")
        st.rerun()

    if generation_cols[2].button("Generate Full Campaign", key="generate_full_outreach_messages"):
        drafts, draft_filters = build_outreach_drafts(limit)
        st.session_state.outreach_campaign_name = campaign_name
        st.session_state.outreach_subject_template = subject_template
        st.session_state.outreach_campaign_instructions = instructions
        st.session_state.outreach_campaign_filters = draft_filters
        st.session_state.outreach_invalid_email_skip_count = invalid_email_skip_count
        st.session_state.outreach_campaign_drafts = drafts
        st.session_state.outreach_campaign_mode = "Full Campaign"
        st.session_state.outreach_preview_sent = False
        st.session_state.outreach_final_reviewed = False
        st.success(f"Generated {len(drafts)} personalized messages.")
        st.rerun()

    drafts = st.session_state.get("outreach_campaign_drafts", [])
    if not drafts:
        st.info("Choose filters and preview or generate messages to start a campaign.")
        return

    st.subheader("Apply Edit To All Drafts")
    edit_cols = st.columns([2, 2, 1])
    find_text = edit_cols[0].text_input("Find text", key="outreach_find_text")
    replace_text = edit_cols[1].text_input("Replace with", key="outreach_replace_text")
    if edit_cols[2].button("Apply To All Drafts", key="apply_edit_all_drafts", disabled=not find_text):
        updated_drafts = []
        for index, draft in enumerate(drafts):
            body_key = f"outreach_body_{draft.get('lead_id')}_{index}"
            current_body = st.session_state.get(body_key, draft.get("message_body", ""))
            updated_body = current_body.replace(find_text, replace_text)
            draft = {**draft, "message_body": updated_body, "message_version": int(draft.get("message_version") or 1) + 1}
            st.session_state[body_key] = updated_body
            updated_drafts.append(draft)
        st.session_state.outreach_campaign_drafts = updated_drafts
        st.success(f"Applied edit to {len(updated_drafts)} drafts.")
        st.rerun()

    st.subheader("Review Messages")
    st.caption(f"{st.session_state.get('outreach_campaign_mode', 'Draft')} | Review, exclude, and edit before sending.")

    edited_messages = []
    selected_count = 0
    for index, draft in enumerate(drafts):
        label = f"{draft.get('contact_name') or 'No contact'} - {draft.get('organization_name') or 'No company'}"
        with st.expander(label, expanded=index < 3):
            send_enabled = st.checkbox(
                "Send",
                value=bool(draft.get("send", True)),
                key=f"outreach_send_{draft.get('lead_id')}_{index}",
            )
            st.caption(f"{draft.get('email')} | {draft.get('city') or '-'} / {draft.get('country') or '-'} | {draft.get('job_title') or '-'}")
            subject = render_subject_template(subject_template, draft, campaign_name)
            st.write("Subject Preview")
            st.code(subject, language=None)
            message_body = st.text_area(
                "Message Preview",
                value=draft["message_body"],
                height=220,
                key=f"outreach_body_{draft.get('lead_id')}_{index}",
            )
            quality = evaluate_outreach_quality(draft, subject, message_body)
            quality_cols = st.columns(3)
            quality_cols[0].write(f"Quality: {quality['quality']}")
            quality_cols[1].write(f"Spam Risk: {quality['spam_risk']}")
            quality_cols[2].write(f"Personalization: {quality['personalization']}")
            if quality["issues"] or quality["spam_hits"]:
                review_notes = list(quality["issues"])
                if quality["spam_hits"]:
                    review_notes.append(f"Spam words: {', '.join(quality['spam_hits'])}")
                st.caption("Review: " + ", ".join(review_notes))
            if send_enabled:
                selected_count += 1
            edited_messages.append(
                {
                    **draft,
                    "subject": subject,
                    "message_body": message_body,
                    "message_version": draft.get("message_version", 1),
                    "send": send_enabled,
                }
            )

    excluded_count = len(edited_messages) - selected_count
    count_cols = st.columns(2)
    count_cols[0].metric("Selected", selected_count)
    count_cols[1].metric("Excluded", excluded_count)

    selected_messages = [message for message in edited_messages if message.get("send")]
    country_counts = {}
    for message in selected_messages:
        country_name = message.get("country") or "Unknown"
        country_counts[country_name] = country_counts.get(country_name, 0) + 1

    st.subheader("Send Preview To Myself")
    preview_cols = st.columns([2, 1, 2])
    preview_email = preview_cols[0].text_input("Preview Email", value=get_app_setting("smtp_from_email", ""), key="outreach_preview_email")
    preview_limit = preview_cols[1].selectbox("Preview Count", [1, 3, 5], index=2, key="outreach_preview_count")
    can_send_preview = is_smtp_configured() and is_valid_email(preview_email) and bool(selected_messages)
    if preview_cols[2].button("Send Preview To Myself", key="send_outreach_preview", disabled=not can_send_preview):
        preview_result = send_outreach_preview_email(preview_email, selected_messages, preview_limit)
        st.session_state.outreach_preview_sent = preview_result["sent"] > 0
        if preview_result["failed"]:
            st.warning(f"Preview sent: {preview_result['sent']}. Failed: {preview_result['failed']}.")
            if preview_result.get("errors"):
                st.caption(" | ".join(preview_result["errors"][:3]))
        else:
            st.success(f"Preview sent to {preview_email}.")

    st.subheader("Campaign Summary")
    summary_cols = st.columns(4)
    summary_cols[0].metric("Selected Recipients", selected_count)
    summary_cols[1].metric("Excluded Recipients", excluded_count)
    summary_cols[2].write("Subject")
    summary_cols[2].caption(subject_template)
    summary_cols[3].write("Instruction Preset")
    summary_cols[3].caption(instruction_preset)
    more_summary_cols = st.columns(3)
    more_summary_cols[0].metric("Estimated Emails", selected_count)
    more_summary_cols[1].write("Preview Sent")
    more_summary_cols[1].caption("Yes" if st.session_state.get("outreach_preview_sent") else "No")
    more_summary_cols[2].write("Signature")
    more_summary_cols[2].caption("1Aim Logistics Signature")

    if country_counts:
        st.write("Countries")
        st.dataframe(
            pd.DataFrame(
                [{"Country": country_name, "Recipients": count} for country_name, count in sorted(country_counts.items())]
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Final Approval")
    if not is_smtp_configured():
        st.warning("Email sending is not configured. Add SMTP settings in Admin before approving the campaign.")

    reviewed = st.checkbox("I reviewed and approve this campaign", key="outreach_final_reviewed")
    approve_disabled = not is_smtp_configured() or not selected_messages or not campaign_name.strip() or not reviewed
    if st.button("Final Approve & Send", type="primary", disabled=approve_disabled, key="approve_outreach_campaign"):
        result = create_and_send_outreach_campaign(
            campaign_name.strip(),
            st.session_state.get("outreach_campaign_filters", filters),
            selected_messages,
            subject_template.strip(),
            instructions.strip(),
        )
        result["campaign_name"] = campaign_name.strip()
        result["timestamp"] = datetime.now().isoformat(timespec="seconds")
        result["skipped"] = excluded_count + int(st.session_state.get("outreach_invalid_email_skip_count", 0) or 0)
        st.session_state.pop("outreach_campaign_drafts", None)
        st.session_state.outreach_campaign_result = result
        st.success(f"Campaign sent. Sent: {result['sent']}. Failed: {result['failed']}.")
        st.rerun()

    if st.button("Clear Campaign Draft", key="clear_outreach_campaign"):
        st.session_state.pop("outreach_campaign_drafts", None)
        st.session_state.pop("outreach_preview_sent", None)
        st.rerun()


def show_occasion_reminders():
    st.title("Occasion Reminders")

    with st.expander("Holiday Library", expanded=False):
        holidays = get_holiday_library()
        if holidays:
            st.dataframe(
                pd.DataFrame(holidays)[
                    [
                        "country",
                        "holiday_name",
                        "holiday_date",
                        "is_recurring",
                        "recurrence_rule",
                        "default_message_theme",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

        with st.popover("Add Holiday"):
            country = st.text_input("Country", key="new_holiday_country")
            holiday_name = st.text_input("Holiday Name", key="new_holiday_name")
            holiday_date = st.text_input("Holiday Date", placeholder="YYYY-MM-DD", key="new_holiday_date")
            is_recurring = st.checkbox("Recurring yearly", value=True, key="new_holiday_recurring")
            recurrence_rule = st.text_input("Recurrence Rule", value="yearly_mm_dd", key="new_holiday_rule")
            theme = st.text_input("Default Message Theme", key="new_holiday_theme")
            if st.button("Save Holiday", key="new_holiday_save"):
                save_holiday_library_item(
                    {
                        "country": country,
                        "holiday_name": holiday_name,
                        "holiday_date": holiday_date,
                        "is_recurring": is_recurring,
                        "recurrence_rule": recurrence_rule,
                        "default_message_theme": theme,
                    }
                )
                st.success("Holiday saved.")
                st.rerun()

        for holiday in holidays:
            with st.popover(f"Edit {holiday['country']} - {holiday['holiday_name']}"):
                country = st.text_input("Country", value=holiday["country"], key=f"holiday_country_{holiday['id']}")
                holiday_name = st.text_input("Holiday Name", value=holiday["holiday_name"], key=f"holiday_name_{holiday['id']}")
                holiday_date = st.text_input("Holiday Date", value=holiday["holiday_date"], key=f"holiday_date_{holiday['id']}")
                is_recurring = st.checkbox("Recurring yearly", value=bool(holiday["is_recurring"]), key=f"holiday_recurring_{holiday['id']}")
                recurrence_rule = st.text_input("Recurrence Rule", value=holiday["recurrence_rule"], key=f"holiday_rule_{holiday['id']}")
                theme = st.text_input("Default Message Theme", value=holiday["default_message_theme"] or "", key=f"holiday_theme_{holiday['id']}")
                if st.button("Update Holiday", key=f"holiday_update_{holiday['id']}"):
                    save_holiday_library_item(
                        {
                            "country": country,
                            "holiday_name": holiday_name,
                            "holiday_date": holiday_date,
                            "is_recurring": is_recurring,
                            "recurrence_rule": recurrence_rule,
                            "default_message_theme": theme,
                        },
                        holiday["id"],
                    )
                    st.success("Holiday updated.")
                    st.rerun()

    reminders = get_occasion_reminders()

    if not reminders:
        st.info("No occasion reminders due.")
        return

    bucket_filter = st.radio(
        "When",
        ["All", "Today", "Next 7 days", "Next 30 days", "Overdue"],
        horizontal=True,
    )

    filtered = [
        reminder for reminder in reminders
        if bucket_filter == "All" or reminder["bucket"] == bucket_filter
    ]

    for reminder in filtered:
        with st.container():
            header_cols = st.columns([2, 2, 1, 1])
            header_cols[0].markdown(f"**{reminder.get('contact_name') or 'No contact'}**")
            header_cols[0].caption(reminder.get("organization_name") or "No organization")
            header_cols[1].markdown(f"**{reminder['occasion_name']}**")
            header_cols[1].caption(reminder.get("country") or "")
            header_cols[2].write(reminder["display_date"])
            header_cols[3].write(reminder["bucket"])

            meta_cols = st.columns(3)
            meta_cols[0].write(f"Channel: {reminder.get('preferred_channel') or '-'}")
            meta_cols[1].write(f"Language: {reminder.get('preferred_language') or '-'}")
            meta_cols[2].write(f"Tone: {reminder.get('message_tone') or '-'}")

            message = st.text_area(
                "Suggested Message",
                value=reminder["suggested_message"],
                height=120,
                key=f"occasion_message_{reminder['id']}",
            )

            action_cols = st.columns(5)
            with action_cols[0]:
                components.html(
                    f"""
                    <button
                        style="background:#1c2636;color:#edf2f7;border:1px solid #3d4b63;border-radius:6px;padding:8px 12px;cursor:pointer;width:100%;"
                        onclick="navigator.clipboard.writeText({message!r})"
                    >
                        Copy Message
                    </button>
                    """,
                    height=44,
                )
            if action_cols[1].button("Mark Sent", key=f"occasion_sent_{reminder['id']}"):
                mark_occasion_message_sent(reminder["id"])
                st.success("Occasion message logged as sent.")
                st.rerun()
            if action_cols[2].button("Snooze", key=f"occasion_snooze_{reminder['id']}"):
                snooze_occasion(reminder["id"], 7)
                st.rerun()
            with action_cols[3]:
                with st.popover("Edit Occasion"):
                    occasion_type = st.selectbox(
                        "Type",
                        OCCASION_TYPE_OPTIONS,
                        index=OCCASION_TYPE_OPTIONS.index(reminder["occasion_type"]) if reminder["occasion_type"] in OCCASION_TYPE_OPTIONS else 0,
                        key=f"edit_occ_type_{reminder['id']}",
                    )
                    occasion_name = st.text_input("Occasion Name", value=reminder["occasion_name"], key=f"edit_occ_name_{reminder['id']}")
                    occasion_date = st.text_input("Occasion Date", value=reminder["occasion_date"], key=f"edit_occ_date_{reminder['id']}")
                    country = st.text_input("Country", value=reminder.get("country") or "", key=f"edit_occ_country_{reminder['id']}")
                    channel = st.selectbox(
                        "Channel",
                        PREFERRED_CHANNEL_OPTIONS,
                        index=PREFERRED_CHANNEL_OPTIONS.index(reminder["preferred_channel"]) if reminder.get("preferred_channel") in PREFERRED_CHANNEL_OPTIONS else 0,
                        key=f"edit_occ_channel_{reminder['id']}",
                    )
                    language = st.selectbox(
                        "Language",
                        PREFERRED_LANGUAGE_OPTIONS,
                        index=PREFERRED_LANGUAGE_OPTIONS.index(reminder["preferred_language"]) if reminder.get("preferred_language") in PREFERRED_LANGUAGE_OPTIONS else 0,
                        key=f"edit_occ_lang_{reminder['id']}",
                    )
                    tone = st.selectbox(
                        "Tone",
                        RELATIONSHIP_TONE_OPTIONS,
                        index=RELATIONSHIP_TONE_OPTIONS.index(reminder["message_tone"]) if reminder.get("message_tone") in RELATIONSHIP_TONE_OPTIONS else 1,
                        key=f"edit_occ_tone_{reminder['id']}",
                    )
                    reminder_days = st.number_input(
                        "Reminder Days Before",
                        min_value=0,
                        max_value=60,
                        value=int(reminder.get("reminder_days_before") or 7),
                        key=f"edit_occ_days_{reminder['id']}",
                    )
                    if st.button("Save Occasion", key=f"save_occ_{reminder['id']}"):
                        update_relationship_occasion(
                            reminder["id"],
                            {
                                "occasion_type": occasion_type,
                                "occasion_name": occasion_name,
                                "occasion_date": occasion_date,
                                "country": country,
                                "is_recurring": bool(reminder.get("is_recurring")),
                                "recurrence_rule": reminder.get("recurrence_rule"),
                                "preferred_channel": channel,
                                "preferred_language": language,
                                "message_tone": tone,
                                "reminder_days_before": reminder_days,
                                "status": reminder.get("status") or "Active",
                                "notes": reminder.get("notes"),
                            },
                        )
                        st.rerun()
            if action_cols[4].button("Open Detail", key=f"occasion_open_{reminder['id']}", disabled=not reminder.get("lead_id")):
                st.session_state.selected_lead_id = reminder["lead_id"]
                st.session_state.pending_page = "Leads List"
                st.rerun()

            st.divider()


def money_display(value):
    try:
        return f"${float(value or 0):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def render_save_opportunity_intelligence(opportunity):
    with st.expander("Save as Knowledge Intelligence", expanded=False):
        st.caption("Turn this opportunity into reusable CRM memory for future sales, quotation, or operations decisions.")
        default_type = "Customer Intelligence"
        if opportunity.get("stage") == "Lost":
            default_type = "Lessons Learned"
        elif opportunity.get("stage") == "Won":
            default_type = "Shipment History Intelligence"
        intel_cols = st.columns([1.5, 2.5, 1])
        intel_type = intel_cols[0].selectbox(
            "Intelligence Type",
            INTELLIGENCE_TYPES,
            index=INTELLIGENCE_TYPES.index(default_type),
            key=f"opp_intel_type_{opportunity['id']}",
        )
        title = intel_cols[1].text_input(
            "Title",
            value=f"{opportunity.get('display_name') or 'Opportunity'} - {intel_type}",
            key=f"opp_intel_title_{opportunity['id']}",
        )
        confidence = intel_cols[2].selectbox("Confidence", ["High", "Medium", "Low"], index=1, key=f"opp_intel_conf_{opportunity['id']}")
        summary = st.text_area(
            "Summary",
            value=(
                f"{opportunity.get('display_name') or 'Opportunity'} | "
                f"{opportunity.get('organization_name') or 'No organization'} | "
                f"Stage: {opportunity.get('stage') or '-'} | "
                f"Lane: {opportunity.get('trade_lane') or '-'} | "
                f"Service: {opportunity.get('service_type') or '-'}"
            ),
            height=90,
            key=f"opp_intel_summary_{opportunity['id']}",
        )
        activity_notes = "\n".join(
            f"- {activity.get('activity_type')}: {activity.get('description') or activity.get('summary') or ''}"
            for activity in opportunity.get("activities", [])[:5]
        )
        details = st.text_area(
            "Details / Lesson / What to remember",
            value="\n\n".join(
                item
                for item in [
                    opportunity.get("notes") or "",
                    activity_notes,
                ]
                if item
            ),
            height=170,
            key=f"opp_intel_details_{opportunity['id']}",
        )
        tags = st.text_input(
            "Tags",
            value=", ".join(item for item in ["opportunity", opportunity.get("stage"), opportunity.get("service_type")] if item),
            key=f"opp_intel_tags_{opportunity['id']}",
        )
        if st.button("Save Opportunity Intelligence", key=f"save_opp_intel_{opportunity['id']}", disabled=not title.strip()):
            intelligence_id = save_intelligence(
                {
                    "intelligence_type": intel_type,
                    "title": title,
                    "entity_name": opportunity.get("organization_name"),
                    "country": "",
                    "lane": opportunity.get("trade_lane"),
                    "commodity": "",
                    "hs_code": "",
                    "summary": summary,
                    "details": details,
                    "source": f"Opportunity #{opportunity['id']}",
                    "source_type": "Opportunity",
                    "source_id": opportunity["id"],
                    "confidence": confidence,
                    "tags": tags,
                    "status": "Active",
                    "created_by": "admin",
                }
            )
            st.success(f"Saved to Intelligence Library: #{intelligence_id}")


def render_save_quotation_intelligence(quotation):
    with st.expander("Save as Knowledge Intelligence", expanded=False):
        st.caption("Turn this quote into reusable pricing, customer, vendor, or shipment-history memory.")
        default_type = "Customer Intelligence" if quotation.get("customer_name") else "Lessons Learned"
        quote_cols = st.columns([1.5, 2.5, 1])
        intel_type = quote_cols[0].selectbox(
            "Intelligence Type",
            INTELLIGENCE_TYPES,
            index=INTELLIGENCE_TYPES.index(default_type),
            key=f"quote_intel_type_{quotation['id']}",
        )
        title = quote_cols[1].text_input(
            "Title",
            value=f"{quotation.get('quote_no') or 'Quotation'} v{quotation.get('version') or 1} - {intel_type}",
            key=f"quote_intel_title_{quotation['id']}",
        )
        confidence = quote_cols[2].selectbox("Confidence", ["High", "Medium", "Low"], index=1, key=f"quote_intel_conf_{quotation['id']}")
        item_lines = "\n".join(
            f"- {item.get('description') or item.get('charge_name') or 'Line'}: {item.get('sell_amount') or item.get('amount') or ''}"
            for item in quotation.get("items", [])[:10]
        )
        summary = st.text_area(
            "Summary",
            value=(
                f"{quotation.get('customer_name') or 'Customer'} | "
                f"{quotation.get('trade_lane') or '-'} | "
                f"{quotation.get('service_type') or '-'} | "
                f"Status: {quotation.get('status') or '-'} | "
                f"Total: {currency_display(quotation.get('sell_amount'), quotation.get('currency') or 'USD')}"
            ),
            height=90,
            key=f"quote_intel_summary_{quotation['id']}",
        )
        details = st.text_area(
            "Details / Pricing Memory / What to remember",
            value="\n\n".join(item for item in [quotation.get("notes") or "", item_lines] if item),
            height=170,
            key=f"quote_intel_details_{quotation['id']}",
        )
        tags = st.text_input(
            "Tags",
            value=", ".join(item for item in ["quotation", quotation.get("status"), quotation.get("service_type")] if item),
            key=f"quote_intel_tags_{quotation['id']}",
        )
        if st.button("Save Quotation Intelligence", key=f"save_quote_intel_{quotation['id']}", disabled=not title.strip()):
            intelligence_id = save_intelligence(
                {
                    "intelligence_type": intel_type,
                    "title": title,
                    "entity_name": quotation.get("customer_name"),
                    "country": "",
                    "lane": quotation.get("trade_lane"),
                    "commodity": "",
                    "hs_code": "",
                    "summary": summary,
                    "details": details,
                    "source": f"Quotation #{quotation['id']} {quotation.get('quote_no') or ''}".strip(),
                    "source_type": "Quotation",
                    "source_id": quotation["id"],
                    "confidence": confidence,
                    "tags": tags,
                    "status": "Active",
                    "created_by": "admin",
                }
            )
            st.success(f"Saved to Intelligence Library: #{intelligence_id}")


def show_inquiry_intake():
    st.caption("Parse inbound freight inquiries, save attachments, and create a reviewed opportunity.")

    leads = get_leads()
    lead_options = {"No linked lead": None}
    for lead in leads:
        label = (
            f"#{lead['id']} - "
            f"{lead['company_name'] or 'No organization'} - "
            f"{lead['contact_person'] or 'No contact'}"
        )
        lead_options[label] = lead

    raw_email = st.text_area(
        "Paste customer inquiry",
        key="inquiry_raw_email",
        height=320,
        placeholder="Paste the customer or agent inquiry email here.",
    )
    option_cols = st.columns(3)
    selected_label = option_cols[0].selectbox("Linked Lead", list(lead_options.keys()), key="inquiry_linked_lead")
    linked_lead = lead_options[selected_label]
    customer_email = option_cols[1].text_input(
        "Customer Email",
        value=linked_lead.get("email") if linked_lead else "",
        key="inquiry_customer_email",
    )
    inquiry_notes = option_cols[2].text_input("Notes", key="inquiry_notes")

    with st.expander("Attachments", expanded=False):
        uploaded_files = st.file_uploader(
            "Upload supporting files",
            type=["pdf", "docx", "txt", "csv", "eml", "xlsx", "xls", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="inquiry_attachments",
            help="Text is extracted from PDF, DOCX, TXT, CSV, Excel, and EML files. All uploaded files are saved with the inquiry.",
        )

    parse_disabled = not raw_email.strip() and not uploaded_files
    if st.button("Parse Inquiry", type="primary", disabled=parse_disabled, key="extract_inquiry"):
        attachment_items = []
        attachment_texts = []
        for uploaded_file in uploaded_files or []:
            content = uploaded_file.getvalue()
            attachment_items.append({"filename": uploaded_file.name, "content": content})
            attachment_text = extract_attachment_text(uploaded_file.name, content)
            if attachment_text:
                attachment_texts.append({"filename": uploaded_file.name, "text": attachment_text})
        st.session_state.inquiry_attachment_items = attachment_items
        st.session_state.inquiry_parsed = parse_inquiry_text(raw_email, attachment_texts)
        if linked_lead:
            st.session_state.inquiry_parsed["lead_id"] = linked_lead["id"]
            st.session_state.inquiry_parsed["company_name"] = linked_lead.get("company_name") or st.session_state.inquiry_parsed.get("company_name")
            st.session_state.inquiry_parsed["organization"] = linked_lead.get("company_name") or st.session_state.inquiry_parsed.get("organization")
            st.session_state.inquiry_parsed["contact_person"] = linked_lead.get("contact_person") or st.session_state.inquiry_parsed.get("contact_person")
        if customer_email:
            st.session_state.inquiry_parsed["email"] = customer_email
        if inquiry_notes:
            st.session_state.inquiry_parsed["user_notes"] = inquiry_notes
        st.success("Inquiry fields extracted. Review before saving.")

    parsed = st.session_state.get("inquiry_parsed")
    if not parsed:
        st.info("Paste an inquiry email or upload attachments, then parse the inquiry.")
        return

    st.subheader("Review Extracted Inquiry")
    identity_cols = st.columns(3)
    organization = identity_cols[0].text_input("Organization", value=parsed.get("organization") or parsed.get("company_name") or "", key="inquiry_company")
    contact_person = identity_cols[1].text_input("Contact", value=parsed.get("contact_person") or "", key="inquiry_contact")
    email = identity_cols[2].text_input("Email", value=parsed.get("email") or "", key="inquiry_email")

    opportunity_name = st.text_input(
        "Opportunity Name",
        value=parsed.get("opportunity_name") or "Inbound Inquiry",
        key="inquiry_opportunity_name",
    )
    route_cols = st.columns(3)
    origin = route_cols[0].text_input("Origin", value=parsed.get("origin") or "", key="inquiry_origin")
    destination = route_cols[1].text_input("Destination", value=parsed.get("destination") or "", key="inquiry_destination")
    trade_lane = route_cols[2].text_input("Trade Lane", value=parsed.get("trade_lane") or "", key="inquiry_lane")

    freight_cols = st.columns(4)
    service_type = freight_cols[0].text_input("Service Type", value=parsed.get("service_type") or "", key="inquiry_service")
    cargo_description = freight_cols[1].text_input("Cargo Description", value=parsed.get("cargo_description") or parsed.get("commodity") or "", key="inquiry_cargo")
    incoterm = freight_cols[2].text_input("Incoterm", value=parsed.get("incoterm") or "", key="inquiry_incoterm")
    deadline = freight_cols[3].text_input("Deadline / Date Info", value=parsed.get("deadline") or "", key="inquiry_deadline")

    cargo_cols = st.columns(4)
    volume = cargo_cols[0].text_input("Volume", value=parsed.get("volume") or "", key="inquiry_volume")
    weight = cargo_cols[1].text_input("Weight", value=parsed.get("weight") or "", key="inquiry_weight")
    container_type = cargo_cols[2].text_input("Container Type", value=parsed.get("container_type") or "", key="inquiry_container_type")
    quantity = cargo_cols[3].text_input("Quantity", value=parsed.get("quantity") or "", key="inquiry_quantity")

    next_cols = st.columns(3)
    next_action = next_cols[0].text_input("Next Action", value=parsed.get("next_action") or "Prepare quotation", key="inquiry_next_action")
    next_action_date = next_cols[1].text_input("Next Action Date", value=parsed.get("next_action_date") or "", key="inquiry_next_action_date")
    quotation_status = next_cols[2].text_input("Quotation Status", value=parsed.get("quotation_status") or "Not Started", key="inquiry_quotation_status")

    with st.expander("Parsed Source Text", expanded=False):
        st.text_area("Original Email", value=parsed.get("raw_text") or "", height=180, key="inquiry_review_raw_text")
        if parsed.get("attachment_text"):
            st.text_area("Attachment Text", value=parsed.get("attachment_text") or "", height=180, key="inquiry_review_attachment_text")

    save_disabled = not opportunity_name.strip()
    if st.button("Create Opportunity from Parsed Data", type="primary", disabled=save_disabled, key="save_inquiry_opportunity"):
        attachment_items = st.session_state.get("inquiry_attachment_items", [])
        attachment_folder, saved_files = save_inquiry_files(opportunity_name, attachment_items)
        reviewed_record = {
            "opportunity_name": opportunity_name,
            "subject": parsed.get("subject"),
            "lead_id": parsed.get("lead_id"),
            "company_name": organization,
            "organization": organization,
            "contact_person": contact_person,
            "email": email,
            "phone": parsed.get("phone"),
            "country": parsed.get("country"),
            "city": parsed.get("city"),
            "trade_lane": trade_lane,
            "service_type": service_type,
            "cargo_description": cargo_description,
            "commodity": cargo_description,
            "origin": origin,
            "destination": destination,
            "volume": volume,
            "weight": weight,
            "container_type": container_type,
            "quantity": quantity,
            "incoterm": incoterm,
            "deadline": deadline,
            "quotation_status": quotation_status,
            "stage": "Quote Requested",
            "inquiry_date": parsed.get("inquiry_date"),
            "next_action": next_action,
            "next_action_date": next_action_date,
            "create_prepare_quote_task": "1",
            "user_notes": parsed.get("user_notes"),
            "raw_text": parsed.get("raw_text"),
            "attachment_text": parsed.get("attachment_text"),
            "attachment_folder": attachment_folder,
            "attachment_files": "\n".join(saved_files),
        }
        reviewed_record["notes"] = build_inquiry_notes(reviewed_record, saved_files)
        result = create_opportunity(reviewed_record)
        st.session_state.selected_opportunity_id = result["opportunity_id"]
        st.session_state.inquiry_last_result = result
        st.session_state.pop("inquiry_parsed", None)
        st.session_state.pop("inquiry_attachment_items", None)
        st.success("Opportunity created and inquiry files saved.")
        st.rerun()


def show_opportunities():
    if st.session_state.get("selected_opportunity_id"):
        show_opportunity_detail(st.session_state.selected_opportunity_id)
        return

    st.title("Opportunities")
    dashboard = get_opportunity_dashboard_data()

    kpi_cols = st.columns(6)
    kpi_cols[0].metric("Total Opportunities", dashboard["total_opportunities"])
    for col, stage in zip(kpi_cols[1:], ["Interested", "Quoted", "Negotiation", "Won", "Lost"]):
        col.metric(stage, dashboard["stage_counts"].get(stage, 0))

    revenue_cols = st.columns(3)
    revenue_cols[0].metric("Total Pipeline Value", money_display(dashboard["total_pipeline_value"]))
    revenue_cols[1].metric("Negotiation Value", money_display(dashboard["negotiation_value"]))
    revenue_cols[2].metric("Won Value", money_display(dashboard["won_value"]))

    st.subheader("Create Opportunity")
    parse_tab, manual_tab = st.tabs(["Parse Inquiry", "Manual Entry"])
    with parse_tab:
        show_inquiry_intake()
    with manual_tab:
        leads = get_leads()
        lead_options = {"No linked lead": None}
        for lead in leads:
            label = (
                f"#{lead['id']} - "
                f"{lead['company_name'] or 'No organization'} - "
                f"{lead['contact_person'] or 'No contact'}"
            )
            lead_options[label] = lead

        selected_label = st.selectbox("Link to Lead", list(lead_options.keys()), key="new_opp_lead")
        selected_lead = lead_options[selected_label]
        default_name = ""
        if selected_lead:
            default_name = f"{selected_lead['company_name'] or 'Opportunity'} - {selected_lead['contact_person'] or 'Freight opportunity'}"
        opportunity_name = st.text_input("Opportunity Name", value=default_name, key="new_opp_name")
        create_cols = st.columns(3)
        stage = create_cols[0].selectbox("Stage", OPPORTUNITY_STAGES, key="new_opp_stage")
        trade_lane = create_cols[1].text_input("Trade Lane", key="new_opp_lane")
        service_type = create_cols[2].text_input("Service Type", key="new_opp_service")
        cargo_cols = st.columns(4)
        cargo_description = cargo_cols[0].text_input("Cargo Description", key="new_opp_cargo")
        origin = cargo_cols[1].text_input("Origin", key="new_opp_origin")
        destination = cargo_cols[2].text_input("Destination", key="new_opp_destination")
        incoterm = cargo_cols[3].text_input("Incoterm", key="new_opp_incoterm")
        qty_cols = st.columns(4)
        volume = qty_cols[0].text_input("Volume", key="new_opp_volume")
        weight = qty_cols[1].text_input("Weight", key="new_opp_weight")
        container_type = qty_cols[2].text_input("Container Type", key="new_opp_container")
        quantity = qty_cols[3].text_input("Quantity", key="new_opp_quantity")
        value_cols = st.columns(4)
        potential_revenue = value_cols[0].text_input("Potential Revenue", key="new_opp_revenue")
        potential_profit = value_cols[1].text_input("Potential Profit", key="new_opp_profit")
        expected_close_date = value_cols[2].text_input("Expected Close Date", placeholder="YYYY-MM-DD", key="new_opp_close")
        next_action_date = value_cols[3].text_input("Next Action Date", placeholder="YYYY-MM-DD", key="new_opp_next_date")
        next_action = st.text_input("Next Action", key="new_opp_next_action")
        notes = st.text_area("Notes", key="new_opp_notes")
        if st.button("Create Opportunity", type="primary", key="create_opportunity"):
            result = create_opportunity(
                {
                    "opportunity_name": opportunity_name,
                    "lead_id": selected_lead["id"] if selected_lead else None,
                    "organization_id": selected_lead["organization_id"] if selected_lead else None,
                    "contact_id": selected_lead["contact_id"] if selected_lead else None,
                    "owner": None,
                    "stage": stage,
                    "trade_lane": trade_lane,
                    "service_type": service_type,
                    "cargo_description": cargo_description,
                    "origin": origin,
                    "destination": destination,
                    "volume": volume,
                    "weight": weight,
                    "container_type": container_type,
                    "quantity": quantity,
                    "incoterm": incoterm,
                    "quotation_status": "Not Started",
                    "potential_revenue": potential_revenue,
                    "potential_profit": potential_profit,
                    "expected_close_date": expected_close_date,
                    "next_action": next_action,
                    "next_action_date": next_action_date,
                    "notes": notes,
                }
            )
            st.session_state.selected_opportunity_id = result["opportunity_id"]
            st.rerun()

    opportunities = get_opportunities()
    st.subheader("Opportunity List")
    if not opportunities:
        st.info("No opportunities yet.")
        return

    header = st.columns([2, 2, 1, 1, 1, 1, 1])
    header[0].caption("Opportunity")
    header[1].caption("Organization")
    header[2].caption("Stage")
    header[3].caption("Trade Lane")
    header[4].caption("Revenue")
    header[5].caption("Next Action")
    header[6].caption("Open")
    for opportunity in opportunities:
        cols = st.columns([2, 2, 1, 1, 1, 1, 1])
        cols[0].write(opportunity["display_name"] or "Untitled")
        cols[1].write(opportunity.get("organization_name") or "-")
        cols[2].write(opportunity["stage"])
        cols[3].write(opportunity.get("trade_lane") or "-")
        cols[4].write(money_display(opportunity.get("potential_revenue")))
        cols[5].write(opportunity.get("next_action") or "-")
        if cols[6].button("Open", key=f"open_opp_{opportunity['id']}"):
            st.session_state.selected_opportunity_id = opportunity["id"]
            st.rerun()


def show_opportunity_detail(opportunity_id):
    opportunity = get_opportunity_detail(opportunity_id)
    if not opportunity:
        st.warning("Opportunity not found.")
        if st.button("Back to Opportunities"):
            st.session_state.selected_opportunity_id = None
            st.session_state.pending_page = "Opportunities"
            st.rerun()
        return

    if st.button("Back to Opportunities"):
        st.session_state.selected_opportunity_id = None
        st.session_state.pending_page = "Opportunities"
        st.rerun()

    st.title(opportunity["display_name"] or "Opportunity")
    st.caption(" | ".join(item for item in [
        opportunity.get("organization_name"),
        opportunity.get("contact_name"),
        opportunity.get("trade_lane"),
    ] if item))

    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Stage", opportunity["stage"])
    kpi_cols[1].metric("Potential Revenue", money_display(opportunity.get("potential_revenue")))
    kpi_cols[2].metric("Potential Profit", money_display(opportunity.get("potential_profit")))
    kpi_cols[3].metric("Expected Close", opportunity.get("expected_close_date") or "-")

    st.subheader("Stage")
    stage_cols = st.columns(len(OPPORTUNITY_STAGES))
    for col, stage in zip(stage_cols, OPPORTUNITY_STAGES):
        if col.button(stage, key=f"opp_stage_{stage}_{opportunity_id}"):
            update_opportunity_stage(opportunity_id, stage)
            st.rerun()

    st.subheader("Details")
    name = st.text_input("Opportunity Name", value=opportunity.get("display_name") or "")
    field_cols = st.columns(3)
    stage = field_cols[0].selectbox(
        "Stage",
        OPPORTUNITY_STAGES,
        index=OPPORTUNITY_STAGES.index(opportunity["stage"]) if opportunity["stage"] in OPPORTUNITY_STAGES else 0,
    )
    trade_lane = field_cols[1].text_input("Trade Lane", value=opportunity.get("trade_lane") or "")
    service_type = field_cols[2].text_input("Service Type", value=opportunity.get("service_type") or "")
    cargo_cols = st.columns(4)
    cargo_description = cargo_cols[0].text_input("Cargo Description", value=opportunity.get("cargo_description") or opportunity.get("commodity") or "")
    origin = cargo_cols[1].text_input("Origin", value=opportunity.get("origin") or "")
    destination = cargo_cols[2].text_input("Destination", value=opportunity.get("destination") or "")
    incoterm = cargo_cols[3].text_input("Incoterm", value=opportunity.get("incoterm") or "")
    qty_cols = st.columns(4)
    volume = qty_cols[0].text_input("Volume", value=opportunity.get("volume") or "")
    weight = qty_cols[1].text_input("Weight", value=opportunity.get("weight") or "")
    container_type = qty_cols[2].text_input("Container Type", value=opportunity.get("container_type") or "")
    quantity = qty_cols[3].text_input("Quantity", value=opportunity.get("quantity") or "")
    value_cols = st.columns(4)
    potential_revenue = value_cols[0].text_input("Potential Revenue", value=str(opportunity.get("potential_revenue") or ""))
    potential_profit = value_cols[1].text_input("Potential Profit", value=str(opportunity.get("potential_profit") or ""))
    expected_close_date = value_cols[2].text_input("Expected Close Date", value=opportunity.get("expected_close_date") or "")
    next_action_date = value_cols[3].text_input("Next Action Date", value=opportunity.get("next_action_date") or "")
    next_action = st.text_input("Next Action", value=opportunity.get("next_action") or "")
    notes = st.text_area("Notes", value=opportunity.get("notes") or "", height=180)

    if st.button("Save Opportunity", type="primary", key=f"save_opp_{opportunity_id}"):
        save_opportunity(
            {
                "opportunity_name": name,
                "organization_id": opportunity.get("organization_id"),
                "contact_id": opportunity.get("contact_id"),
                "owner": opportunity.get("owner"),
                "stage": stage,
                "trade_lane": trade_lane,
                "service_type": service_type,
                "cargo_description": cargo_description,
                "origin": origin,
                "destination": destination,
                "volume": volume,
                "weight": weight,
                "container_type": container_type,
                "quantity": quantity,
                "incoterm": incoterm,
                "quotation_status": opportunity.get("quotation_status") or "Not Started",
                "potential_revenue": potential_revenue,
                "potential_profit": potential_profit,
                "expected_close_date": expected_close_date,
                "next_action": next_action,
                "next_action_date": next_action_date,
                "notes": notes,
            },
            opportunity_id,
        )
        st.success("Opportunity saved.")
        st.rerun()

    render_save_opportunity_intelligence(opportunity)

    st.subheader("Activity")
    if not opportunity.get("activities"):
        st.info("No opportunity activity yet.")
    for activity in opportunity.get("activities", []):
        st.markdown(f"**{activity.get('activity_at') or activity.get('created_at')}** - {activity.get('activity_type')}")
        st.write(activity.get("description") or activity.get("summary") or "")


def currency_display(value, currency="USD"):
    try:
        return f"{currency} {float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return f"{currency} 0.00"


def show_pricing_engine():
    st.title("Pricing Engine")
    st.caption("Capture carrier rates, agent rates, local charges, and compare suggested sell rates by opportunity.")

    opportunities = get_opportunities()
    if not opportunities:
        st.info("Create an opportunity first, then add pricing lines here.")
        return

    opportunity_options = {}
    for opportunity in opportunities:
        label = (
            f"#{opportunity['id']} - "
            f"{opportunity.get('display_name') or 'Untitled'}"
            f" | {opportunity.get('stage') or '-'}"
        )
        opportunity_options[label] = opportunity

    selected_label = st.selectbox(
        "Opportunity",
        list(opportunity_options.keys()),
        key="pricing_selected_opportunity",
    )
    selected_opportunity = opportunity_options[selected_label]
    opportunity_id = selected_opportunity["id"]

    st.subheader(selected_opportunity.get("display_name") or "Opportunity")
    meta_cols = st.columns(4)
    meta_cols[0].metric("Stage", selected_opportunity.get("stage") or "-")
    meta_cols[1].metric("Trade Lane", selected_opportunity.get("trade_lane") or "-")
    meta_cols[2].metric("Current Revenue", money_display(selected_opportunity.get("potential_revenue")))
    meta_cols[3].metric("Current Profit", money_display(selected_opportunity.get("potential_profit")))

    with st.expander("Add Pricing Line", expanded=True):
        line_cols = st.columns(3)
        vendor_type = line_cols[0].selectbox("Rate Type", PRICING_VENDOR_TYPE_OPTIONS, key="pricing_vendor_type")
        vendor_name = line_cols[1].text_input("Vendor / Agent", key="pricing_vendor_name")
        charge_type = line_cols[2].selectbox("Charge Type", PRICING_CHARGE_TYPE_OPTIONS, key="pricing_charge_type")

        charge_cols = st.columns(4)
        charge_name = charge_cols[0].text_input("Charge Name", value="Freight", key="pricing_charge_name")
        basis = charge_cols[1].text_input("Basis", value="Shipment", key="pricing_basis")
        currency = charge_cols[2].selectbox("Currency", PRICING_CURRENCY_OPTIONS, key="pricing_currency")
        cost_amount = charge_cols[3].number_input("Cost Amount", min_value=0.0, value=0.0, step=10.0, key="pricing_cost")

        margin_cols = st.columns(4)
        margin_percent = margin_cols[0].number_input("Margin %", min_value=0.0, value=15.0, step=1.0, key="pricing_margin_percent")
        margin_amount = margin_cols[1].number_input("Fixed Margin", min_value=0.0, value=0.0, step=10.0, key="pricing_margin_amount")
        transit_time = margin_cols[2].text_input("Transit Time", key="pricing_transit_time")
        valid_until = margin_cols[3].text_input("Valid Until", placeholder="YYYY-MM-DD", key="pricing_valid_until")
        notes = st.text_area("Notes", height=90, key="pricing_notes")

        calculated = calculate_suggested_sell_rate(cost_amount, margin_percent, margin_amount)
        preview_cols = st.columns(3)
        preview_cols[0].metric("Cost", currency_display(calculated["cost_amount"], currency))
        preview_cols[1].metric("Margin", currency_display(calculated["margin_amount"], currency))
        preview_cols[2].metric("Suggested Sell", currency_display(calculated["suggested_sell_amount"], currency))

        errors = []
        if not charge_name.strip():
            errors.append("Charge name is required.")
        if not vendor_name.strip() and vendor_type != "Local Charge":
            errors.append("Vendor / agent name is required for carrier and agent rates.")
        for error in errors:
            st.warning(error)

        if st.button("Save Pricing Line", type="primary", disabled=bool(errors), key="save_pricing_line"):
            save_vendor_rate(
                {
                    "opportunity_id": opportunity_id,
                    "vendor_type": vendor_type,
                    "vendor_name": vendor_name,
                    "charge_type": charge_type,
                    "charge_name": charge_name,
                    "basis": basis,
                    "currency": currency,
                    "cost_amount": cost_amount,
                    "margin_percent": margin_percent,
                    "margin_amount": margin_amount,
                    "transit_time": transit_time,
                    "valid_until": valid_until,
                    "notes": notes,
                }
            )
            st.success("Pricing line saved.")
            st.rerun()

    summary = get_pricing_summary(opportunity_id)

    st.subheader("Rate Comparison")
    if not summary["comparisons"]:
        st.info("No pricing lines saved for this opportunity yet.")
    else:
        comparison_df = pd.DataFrame(summary["comparisons"])
        st.dataframe(
            comparison_df[
                [
                    "currency",
                    "vendor_type",
                    "vendor_name",
                    "line_count",
                    "cost_total",
                    "margin_total",
                    "margin_percent",
                    "suggested_sell_total",
                    "transit_time",
                    "valid_until",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        currencies = list(summary["best_by_currency"].keys())
        selected_currency = st.selectbox("Suggested Currency", currencies, key="pricing_apply_currency")
        best = summary["best_by_currency"][selected_currency]
        best_cols = st.columns(4)
        best_cols[0].metric("Best Option", best["vendor_name"])
        best_cols[1].metric("Suggested Sell", currency_display(best["suggested_sell_total"], selected_currency))
        best_cols[2].metric("Expected Profit", currency_display(best["margin_total"], selected_currency))
        best_cols[3].metric("Margin", f"{best['margin_percent']}%")
        if st.button("Apply Suggested Rate To Opportunity", key="apply_pricing_to_opportunity"):
            apply_pricing_summary_to_opportunity(opportunity_id, selected_currency)
            st.success("Opportunity revenue and profit updated from the suggested sell rate.")
            st.rerun()

    st.subheader("Saved Rate Lines")
    if summary["rates"]:
        rate_df = pd.DataFrame(summary["rates"])
        st.dataframe(
            rate_df[
                [
                    "vendor_type",
                    "vendor_name",
                    "charge_type",
                    "charge_name",
                    "basis",
                    "currency",
                    "cost_amount",
                    "margin_percent",
                    "margin_amount",
                    "suggested_sell_amount",
                    "transit_time",
                    "valid_until",
                    "notes",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


def quotation_file_name(quotation, extension):
    quote_no = quotation.get("quote_no") or "quotation"
    version = quotation.get("version") or 1
    return f"{quote_no}_v{version}.{extension}"


def show_quotation_engine():
    if st.session_state.get("selected_quotation_id"):
        show_quotation_detail(st.session_state.selected_quotation_id)
        return

    st.title("Quotation Engine")
    st.caption("Create customer quotations from opportunities, manage versions, approve quotes, and export Excel or PDF.")

    quotations = get_quotations()
    dashboard_cols = st.columns(5)
    dashboard_cols[0].metric("Total Quotes", len(quotations))
    for index, status in enumerate(["Draft", "Pending Approval", "Approved", "Sent"], start=1):
        dashboard_cols[index].metric(status, sum(1 for quote in quotations if quote.get("status") == status))

    st.subheader("Create Quotation")
    opportunities = get_opportunities()
    templates = get_quotation_templates()
    template_names = [template["template_name"] for template in templates] or ["Standard Freight Quote"]

    if opportunities:
        with st.expander("New Quote From Opportunity", expanded=True):
            opportunity_options = {}
            for opportunity in opportunities:
                label = (
                    f"#{opportunity['id']} - "
                    f"{opportunity.get('display_name') or 'Untitled'}"
                    f" | {opportunity.get('stage') or '-'}"
                    f" | {money_display(opportunity.get('potential_revenue'))}"
                )
                opportunity_options[label] = opportunity
            selected_label = st.selectbox("Opportunity", list(opportunity_options.keys()), key="quote_new_opportunity")
            selected_opportunity = opportunity_options[selected_label]
            create_cols = st.columns(3)
            template_name = create_cols[0].selectbox("Template", template_names, key="quote_new_template")
            currency = create_cols[1].selectbox("Currency", PRICING_CURRENCY_OPTIONS, key="quote_new_currency")
            create_cols[2].metric("Stage", selected_opportunity.get("stage") or "-")
            if st.button("Create Draft Quote", type="primary", key="create_draft_quote"):
                quotation_id = create_quotation_from_opportunity(
                    selected_opportunity["id"],
                    template_name=template_name,
                    currency=currency,
                )
                st.session_state.selected_quotation_id = quotation_id
                st.rerun()
    else:
        st.info("Create an opportunity before creating a quotation.")

    with st.expander("Quotation Templates", expanded=False):
        template_cols = st.columns(4)
        template_name = template_cols[0].text_input("Template Name", value="Standard Freight Quote", key="quote_template_name")
        validity_days = template_cols[1].number_input("Validity Days", min_value=1, value=14, step=1, key="quote_template_validity")
        payment_terms = template_cols[2].text_input("Payment Terms", value="Payment before cargo release unless otherwise agreed.", key="quote_template_terms")
        template_cols[3].write("")
        header_text = st.text_area("Header Text", value="Thank you for your inquiry. Please find our quotation below.", height=80, key="quote_template_header")
        footer_text = st.text_area("Footer Text", value="Rates are subject to space, equipment, and final cargo details at booking.", height=80, key="quote_template_footer")
        if st.button("Save Template", key="save_quote_template"):
            save_quotation_template(template_name, header_text, footer_text, payment_terms, validity_days)
            st.success("Quotation template saved.")
            st.rerun()

    st.subheader("Quotation List")
    if not quotations:
        st.info("No quotations yet.")
        return

    header = st.columns([1, 1, 1, 2, 2, 1, 1, 1])
    header[0].caption("Quote")
    header[1].caption("Version")
    header[2].caption("Status")
    header[3].caption("Customer")
    header[4].caption("Opportunity")
    header[5].caption("Amount")
    header[6].caption("Valid Until")
    header[7].caption("Open")
    for quotation in quotations:
        cols = st.columns([1, 1, 1, 2, 2, 1, 1, 1])
        cols[0].write(quotation.get("quote_no") or "-")
        cols[1].write(f"v{quotation.get('version') or 1}")
        cols[2].write(quotation.get("status") or "-")
        cols[3].write(quotation.get("customer_name") or "-")
        cols[4].write(quotation.get("opportunity_name") or "-")
        cols[5].write(currency_display(quotation.get("sell_amount"), quotation.get("currency") or "USD"))
        cols[6].write(quotation.get("valid_until") or "-")
        if cols[7].button("Open", key=f"open_quote_{quotation['id']}"):
            st.session_state.selected_quotation_id = quotation["id"]
            st.rerun()


def show_quotation_detail(quotation_id):
    quotation = get_quotation_detail(quotation_id)
    if not quotation:
        st.warning("Quotation not found.")
        if st.button("Back to Quotation Engine"):
            st.session_state.selected_quotation_id = None
            st.rerun()
        return

    if st.button("Back to Quotation Engine"):
        st.session_state.selected_quotation_id = None
        st.rerun()

    st.title(f"{quotation.get('quote_no') or 'Quotation'} v{quotation.get('version') or 1}")
    st.caption(" | ".join(item for item in [
        quotation.get("customer_name"),
        quotation.get("trade_lane"),
        quotation.get("service_type"),
    ] if item))

    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Status", quotation.get("status") or "-")
    kpi_cols[1].metric("Total", currency_display(quotation.get("sell_amount"), quotation.get("currency") or "USD"))
    kpi_cols[2].metric("Valid Until", quotation.get("valid_until") or "-")
    kpi_cols[3].metric("Template", quotation.get("template_name") or "-")

    st.subheader("Quote Details")
    detail_cols = st.columns(4)
    quote_date = detail_cols[0].text_input("Quote Date", value=quotation.get("quote_date") or "", key=f"quote_date_{quotation_id}")
    valid_until = detail_cols[1].text_input("Valid Until", value=quotation.get("valid_until") or "", key=f"quote_valid_{quotation_id}")
    currency = detail_cols[2].selectbox(
        "Currency",
        PRICING_CURRENCY_OPTIONS,
        index=PRICING_CURRENCY_OPTIONS.index(quotation.get("currency")) if quotation.get("currency") in PRICING_CURRENCY_OPTIONS else 0,
        key=f"quote_currency_{quotation_id}",
    )
    status = detail_cols[3].selectbox(
        "Status",
        QUOTATION_STATUS_OPTIONS,
        index=QUOTATION_STATUS_OPTIONS.index(quotation.get("status")) if quotation.get("status") in QUOTATION_STATUS_OPTIONS else 0,
        key=f"quote_status_{quotation_id}",
    )

    meta_cols = st.columns(4)
    customer_name = meta_cols[0].text_input("Customer", value=quotation.get("customer_name") or "", key=f"quote_customer_{quotation_id}")
    contact_name = meta_cols[1].text_input("Contact", value=quotation.get("contact_name") or "", key=f"quote_contact_{quotation_id}")
    trade_lane = meta_cols[2].text_input("Trade Lane", value=quotation.get("trade_lane") or "", key=f"quote_lane_{quotation_id}")
    service_type = meta_cols[3].text_input("Service", value=quotation.get("service_type") or "", key=f"quote_service_{quotation_id}")
    payment_terms = st.text_input("Payment Terms", value=quotation.get("payment_terms") or "", key=f"quote_terms_{quotation_id}")
    notes = st.text_area("Notes", value=quotation.get("notes") or "", height=100, key=f"quote_notes_{quotation_id}")

    st.subheader("Line Items")
    item_rows = []
    for item in quotation.get("items", []):
        item_rows.append(
            {
                "description": item.get("description") or "",
                "basis": item.get("basis") or "",
                "quantity": float(item.get("quantity") or 1),
                "unit_price": float(item.get("unit_price") or 0),
                "currency": item.get("currency") or currency,
                "amount": float(item.get("amount") or 0),
                "cost_amount": float(item.get("cost_amount") or 0),
                "vendor_name": item.get("vendor_name") or "",
                "notes": item.get("notes") or "",
            }
        )
    if not item_rows:
        item_rows = [
            {
                "description": "Freight service",
                "basis": "Shipment",
                "quantity": 1.0,
                "unit_price": 0.0,
                "currency": currency,
                "amount": 0.0,
                "cost_amount": 0.0,
                "vendor_name": "",
                "notes": "",
            }
        ]

    edited_items = st.data_editor(
        pd.DataFrame(item_rows),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"quote_items_{quotation_id}",
        column_config={
            "description": st.column_config.TextColumn("Description", required=True),
            "basis": st.column_config.TextColumn("Basis"),
            "quantity": st.column_config.NumberColumn("Qty", min_value=0.0, step=1.0),
            "unit_price": st.column_config.NumberColumn("Unit Price", min_value=0.0, step=10.0),
            "currency": st.column_config.SelectboxColumn("Currency", options=PRICING_CURRENCY_OPTIONS),
            "amount": st.column_config.NumberColumn("Amount", min_value=0.0, step=10.0),
            "cost_amount": st.column_config.NumberColumn("Cost", min_value=0.0, step=10.0),
            "vendor_name": st.column_config.TextColumn("Vendor"),
            "notes": st.column_config.TextColumn("Notes"),
        },
    )
    item_records = edited_items.fillna("").to_dict("records")
    preview_total = sum(float(item.get("amount") or 0) or (float(item.get("quantity") or 0) * float(item.get("unit_price") or 0)) for item in item_records)
    st.metric("Preview Total", currency_display(preview_total, currency))

    save_cols = st.columns(6)
    if save_cols[0].button("Save Quote", type="primary", key=f"save_quote_{quotation_id}"):
        save_quotation(
            {
                "opportunity_id": quotation.get("opportunity_id"),
                "quote_date": quote_date,
                "valid_until": valid_until,
                "currency": currency,
                "status": status,
                "template_name": quotation.get("template_name"),
                "customer_name": customer_name,
                "contact_name": contact_name,
                "trade_lane": trade_lane,
                "service_type": service_type,
                "payment_terms": payment_terms,
                "prepared_by": quotation.get("prepared_by"),
                "follow_up_date": quotation.get("follow_up_date"),
                "notes": notes,
            },
            item_records,
            quotation_id=quotation_id,
        )
        st.success("Quotation saved.")
        st.rerun()

    if save_cols[1].button("New Version", key=f"version_quote_{quotation_id}"):
        new_id = create_quotation_version(quotation_id)
        st.session_state.selected_quotation_id = new_id
        st.success("New quote version created.")
        st.rerun()

    if save_cols[2].button("Submit Approval", key=f"submit_quote_{quotation_id}"):
        update_quotation_status(quotation_id, "Pending Approval")
        st.rerun()

    if save_cols[3].button("Approve", key=f"approve_quote_{quotation_id}"):
        update_quotation_status(quotation_id, "Approved")
        st.rerun()

    if save_cols[4].button("Reject", key=f"reject_quote_{quotation_id}"):
        update_quotation_status(quotation_id, "Rejected")
        st.rerun()

    if save_cols[5].button("Mark Sent", key=f"sent_quote_{quotation_id}"):
        update_quotation_status(quotation_id, "Sent")
        st.rerun()

    render_save_quotation_intelligence(quotation)

    latest_quotation = get_quotation_detail(quotation_id) or quotation
    export_cols = st.columns(2)
    export_cols[0].download_button(
        "Download Excel",
        data=build_quotation_excel(latest_quotation),
        file_name=quotation_file_name(latest_quotation, "xlsx"),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_quote_excel_{quotation_id}",
    )
    export_cols[1].download_button(
        "Download PDF",
        data=build_quotation_pdf(latest_quotation),
        file_name=quotation_file_name(latest_quotation, "pdf"),
        mime="application/pdf",
        key=f"download_quote_pdf_{quotation_id}",
    )

    st.subheader("Activity")
    if not quotation.get("activities"):
        st.info("No quotation activity yet.")
    for activity in quotation.get("activities", []):
        st.markdown(f"**{activity.get('activity_at') or activity.get('created_at')}** - {activity.get('activity_type')}")
        st.write(activity.get("description") or activity.get("summary") or "")


def show_quick_capture():
    st.title("Quick Capture")

    capture_source = st.radio(
        "Input Type",
        ["Email Signature Text", "Namecard Image"],
        horizontal=True,
    )

    image_text = ""
    if capture_source == "Namecard Image":
        uploaded_card = st.file_uploader(
            "Upload namecard image",
            type=ACCEPTED_CARD_IMAGE_EXTENSIONS,
            help="Supported formats: .png, .jpg, .jpeg, .webp",
        )
        if uploaded_card:
            st.image(uploaded_card, use_container_width=True)
            image_text, ocr_warning = extract_text_from_card_image(uploaded_card)
            if ocr_warning:
                st.warning(ocr_warning)

    if st.session_state.pop("quick_capture_reset", False):
        st.session_state.quick_capture_text = ""
        st.session_state.pop("quick_capture_last_result", None)

    if "quick_capture_text" not in st.session_state:
        st.session_state.quick_capture_text = image_text
    elif image_text and not st.session_state.quick_capture_text:
        st.session_state.quick_capture_text = image_text

    raw_text = st.text_area(
        "Text",
        key="quick_capture_text",
        height=220,
        placeholder="Paste an email signature or OCR text from a namecard.",
    )

    if not raw_text.strip():
        st.info("Paste signature text or upload a namecard image to start.")
        return

    parsed = parse_contact_text(raw_text)
    parsed_confidence = parsed.get("_confidence", {})

    def show_confidence(field):
        level = parsed_confidence.get(field)
        if level == "Low":
            st.warning("Low confidence. Please review.")
        elif level == "Medium":
            st.caption("Medium confidence.")

    def render_duplicate_warning(duplicates):
        if not has_captured_crm_duplicates(duplicates):
            return

        st.warning("Possible duplicate found. Review before saving.")

        for organization in duplicates["organizations"]:
            st.caption(
                f"Organization #{organization['id']}: "
                f"{organization.get('name') or ''} "
                f"({organization.get('country') or 'No country'}) - "
                f"{organization['reason']}"
            )

        for contact in duplicates["contacts"]:
            st.caption(
                f"Contact #{contact['id']}: "
                f"{contact.get('name') or contact.get('email') or 'Unnamed contact'} - "
                f"{contact['reason']}"
            )

        for lead in duplicates["leads"]:
            st.caption(
                f"Lead #{lead['id']}: "
                f"{lead.get('source') or 'No source'} / "
                f"{lead.get('campaign') or 'No campaign'} - "
                f"{lead['reason']}"
            )

    st.subheader("Review")
    left_col, right_col = st.columns(2)

    with left_col:
        company_name = st.text_input("Organization Name", value=parsed["company_name"])
        show_confidence("company_name")
        local_name = st.text_input("Local Name", value=parsed["local_name"])
        show_confidence("local_name")
        organization_type = st.selectbox(
            "Organization Type",
            ORG_TYPE_OPTIONS,
            index=ORG_TYPE_OPTIONS.index("Overseas Agent"),
            key="capture_organization_type",
        )
        customer_status = st.selectbox(
            "Customer Status",
            CUSTOMER_STATUS_OPTIONS,
            index=CUSTOMER_STATUS_OPTIONS.index("Customer"),
            key="capture_customer_status",
        )
        country = st.text_input("Country", value=parsed["country"])
        show_confidence("country")
        city = st.text_input("City", value=parsed["city"])
        show_confidence("city")
        website = st.text_input("Website", value=parsed["website"])
        show_confidence("website")
        membership = st.text_input("Membership", value=parsed["membership"])

    with right_col:
        contact_person = st.text_input("Contact Name", value=parsed["contact_person"])
        show_confidence("contact_person")
        job_title = st.text_input("Job Title", value=parsed["job_title"])
        show_confidence("job_title")
        email = st.text_input("Email", value=parsed["email"])
        show_confidence("email")
        phone = st.text_input("Phone", value=parsed["phone"])
        show_confidence("phone")
        wechat = st.text_input("WeChat", value=parsed["wechat"])
        show_confidence("wechat")
        whatsapp = st.text_input("Whatsapp", value=parsed["whatsapp"])
        show_confidence("whatsapp")
        relationship_status = st.selectbox(
            "Relationship",
            RELATIONSHIP_STATUS_OPTIONS,
            index=RELATIONSHIP_STATUS_OPTIONS.index("Active"),
            key="capture_relationship_status",
        )

    save_as = st.radio(
        "Save as",
        CAPTURE_SAVE_AS_OPTIONS,
        index=CAPTURE_SAVE_AS_OPTIONS.index("Customer"),
        horizontal=True,
    )

    campaign = st.text_input("Source / Campaign", value=parsed["campaign"])

    notes = st.text_area("Notes", value=parsed["notes"], height=120)

    mode_status = {
        "Lead": ("Prospect", "New", "New"),
        "Customer": ("Customer", "Active", "Converted"),
    }
    mode_customer_status, mode_relationship_status, mode_lead_status = mode_status[save_as]

    record = {
        "company_name": company_name.strip(),
        "local_name": local_name.strip(),
        "organization_type": organization_type,
        "customer_status": mode_customer_status,
        "country": country.strip(),
        "city": city.strip(),
        "website": website.strip(),
        "membership": membership.strip(),
        "contact_person": contact_person.strip(),
        "job_title": job_title.strip(),
        "email": email.strip().lower(),
        "phone": phone.strip(),
        "wechat": wechat.strip(),
        "whatsapp": whatsapp.strip(),
        "relationship_status": mode_relationship_status,
        "source": "Namecard Import" if capture_source == "Namecard Image" else "Email Signature",
        "campaign": campaign.strip(),
        "lead_status": mode_lead_status,
        "status": mode_lead_status,
        "owner": "admin",
        "notes": notes.strip(),
    }

    errors = []
    if not record["company_name"]:
        errors.append("Organization name is required.")
    if not any(
        record[field] for field in ["contact_person", "email", "wechat", "whatsapp", "phone"]
    ):
        errors.append("Add at least one contact name or channel.")
    if record["email"] and not is_valid_email(record["email"]):
        errors.append("Email format is invalid.")
    if not record["campaign"]:
        errors.append("Source / Campaign is required.")

    for error in errors:
        st.warning(error)

    duplicates = find_captured_crm_duplicates(record) if not errors else {
        "organizations": [],
        "contacts": [],
        "leads": [],
    }
    render_duplicate_warning(duplicates)
    duplicate_action = "Update existing"
    if has_captured_crm_duplicates(duplicates):
        duplicate_action = st.radio(
            "Duplicate Action",
            DUPLICATE_ACTION_OPTIONS,
            index=0,
            horizontal=True,
        )

    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        save_clicked = st.button(
            "Save",
            type="primary",
            disabled=bool(errors),
        )

    with action_col2:
        clear_clicked = st.button("Clear")

    with action_col3:
        cancel_clicked = st.button("Cancel")

    if clear_clicked:
        st.session_state.quick_capture_reset = True
        st.session_state.pop("quick_capture_last_result", None)
        st.rerun()

    if cancel_clicked:
        st.session_state.pop("quick_capture_last_result", None)
        st.info("Capture canceled.")
        return

    if save_clicked:
        result = save_captured_crm_record(record, save_as, duplicate_action)
        st.session_state.quick_capture_last_result = {
            "result": result,
            "save_as": save_as,
        }
        st.success(
            "Saved "
            f"{save_as.lower()} "
            f"(organization #{result['organization_id']}"
            + (f", contact #{result['contact_id']}" if result["contact_id"] else "")
            + (f", lead #{result['lead_id']}" if result["lead_id"] else "")
            + ")."
        )

    saved_result_state = st.session_state.get("quick_capture_last_result")
    if saved_result_state:
        result = saved_result_state["result"]
        st.divider()
        st.subheader("Saved Record")
        link_col1, link_col2, link_col3 = st.columns(3)
        with link_col1:
            if st.button("View Lead", disabled=not result["lead_id"], key="quick_capture_view_lead"):
                st.session_state.selected_lead_id = result["lead_id"]
                st.session_state.pending_page = "Leads List"
                st.rerun()
        with link_col2:
            if st.button("View Organization", disabled=not result["lead_id"], key="quick_capture_view_org"):
                st.session_state.selected_lead_id = result["lead_id"]
                st.session_state.pending_page = "Leads List"
                st.rerun()
        with link_col3:
            if st.button("Add Another", key="quick_capture_add_another"):
                st.session_state.quick_capture_reset = True
                st.session_state.pop("quick_capture_last_result", None)
                st.rerun()


def show_leads_import():
    st.title("Leads Import")

    uploaded_file = st.file_uploader(
        "Upload lead file",
        type=ACCEPTED_IMPORT_EXTENSIONS,
        help="Supported formats: .xlsx, .xls, and .csv",
    )
    if not uploaded_file:
        st.info("Supported formats: .xlsx, .xls, and .csv")
        return

    campaign = st.text_input(
        "Campaign",
        value=Path(uploaded_file.name).stem,
        placeholder="OLO 2026 conference",
    )

    try:
        extension = validate_uploaded_file_extension(uploaded_file)
    except Exception as exc:
        logger.exception("Lead import file extension validation failed.")
        st.error(str(exc))
        return

    try:
        sheet_names = get_workbook_sheet_names(uploaded_file, extension)
    except Exception as exc:
        logger.exception("Lead import worksheet detection failed.")
        st.error(str(exc))
        return

    selected_sheet = None
    if extension in ["xlsx", "xls"]:
        if not sheet_names:
            st.error("No worksheets were found in this Excel file.")
            return

        selected_sheet = st.selectbox(
            "Sheet",
            sheet_names,
        )

    try:
        raw_preview = read_raw_preview(uploaded_file, extension, selected_sheet)
    except Exception as exc:
        logger.exception("Lead import raw preview could not be parsed.")
        st.error(f"Could not preview this file: {exc}")
        return

    raw_preview = raw_preview.fillna("")
    st.subheader("Raw File Preview")
    st.dataframe(
        raw_preview,
        use_container_width=True,
        hide_index=False,
    )

    max_preview_row = max(len(raw_preview), 1)
    header_row_number = st.number_input(
        "Header row",
        min_value=1,
        max_value=max_preview_row,
        value=1,
        step=1,
    )
    header_row_index = int(header_row_number) - 1

    try:
        dataframe = read_uploaded_leads_file(
            uploaded_file,
            extension,
            selected_sheet,
            header_row_index,
        )
    except Exception as exc:
        logger.exception("Lead import file could not be parsed.")
        st.error(f"Could not parse this file: {exc}")
        return

    dataframe = dataframe.dropna(how="all")
    dataframe.columns = [clean_cell(column) for column in dataframe.columns]
    membership_column = find_membership_column(dataframe)

    if membership_column and membership_column != "Membership (OLO, JCTRANS, WCA)":
        dataframe["Membership (OLO, JCTRANS, WCA)"] = dataframe[membership_column]

    missing_required_columns = []
    if "Company Name" not in dataframe.columns:
        missing_required_columns.append("Company Name")
    if not any(column in dataframe.columns for column in REQUIRED_CONTACT_COLUMNS):
        missing_required_columns.append("one of Contact Person, Email, WeChat, Whatsapp")

    if missing_required_columns:
        st.error(
            "Required columns not found: "
            + ", ".join(missing_required_columns)
            + "."
        )
        return

    for excel_column in EXCEL_COLUMNS:
        if excel_column not in dataframe.columns:
            dataframe[excel_column] = ""

    st.subheader("Membership")
    selected_memberships = st.multiselect(
        "Membership",
        MEMBERSHIP_OPTIONS,
        key="lead_import_memberships",
    )
    selected_membership_setting = ",".join(selected_memberships)
    if selected_membership_setting != st.session_state.persisted_lead_import_memberships:
        set_app_setting("lead_import_memberships", selected_membership_setting)
        st.session_state.persisted_lead_import_memberships = selected_membership_setting

    membership_source = MEMBERSHIP_SOURCE_OVERRIDE
    if membership_column:
        membership_source = st.radio(
            "Membership Source",
            [MEMBERSHIP_SOURCE_USE_EXCEL, MEMBERSHIP_SOURCE_OVERRIDE],
            index=1,
        )

    parsed_rows = parse_leads(
        dataframe,
        campaign,
        selected_memberships,
        membership_source,
    )
    summary = summarize_rows(parsed_rows)

    st.subheader("Preview")
    st.dataframe(
        build_preview(parsed_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Import Summary")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total rows", summary["total_rows"])
    with col2:
        st.metric("Valid rows", summary["valid_rows"])
    with col3:
        st.metric("Duplicate rows", summary["duplicate_rows"])
    with col4:
        st.metric("Missing company/contact", summary["missing_required_rows"])
    with col5:
        st.metric("Invalid email", summary["invalid_email_rows"])

    importable_leads = [
        parsed_row["lead"]
        for parsed_row in parsed_rows
        if parsed_row["is_importable"]
    ]

    if not campaign.strip():
        st.warning("Add a campaign before importing these leads.")

    if not importable_leads:
        st.warning("There are no valid new leads to import.")
        return

    if st.button(
        "Import Valid Leads",
        type="primary",
        disabled=not campaign.strip(),
    ):
        imported_count = import_leads(importable_leads, owner="admin")
        duplicate_count = summary["duplicate_rows"]
        invalid_count = summary["invalid_rows"]
        st.success(
            f"Imported {imported_count} new leads. "
            f"Skipped {duplicate_count} duplicates. "
            f"Skipped {invalid_count} invalid rows."
        )


def as_text(value):
    if value is None:
        return ""
    return str(value)


def parse_date_value(value):
    value = as_text(value).strip()
    if not value:
        return None
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def detail_value(row, key, default=""):
    if not row:
        return default
    return row.get(key) if row.get(key) is not None else default


def show_lead_detail(lead_id):
    detail = get_lead_detail(lead_id)
    if not detail:
        st.warning("Lead not found.")
        if st.button("Back to Leads List"):
            st.session_state.selected_lead_id = None
            st.session_state.pending_page = "Leads List"
            st.rerun()
        return

    lead = detail["lead"]
    organization = detail["organization"]
    contact = detail["contact"]
    activities = detail.get("activities", [])
    data_quality = detail.get("data_quality", {})
    relationship_health = detail.get("relationship_health", {})
    missing_data = detail.get("missing_data", {})
    edit_key = f"lead_detail_edit_{lead_id}"

    contact_name = detail_value(contact, "name") or detail_value(lead, "contact_person") or "No contact linked"
    job_title = detail_value(contact, "job_title") or detail_value(lead, "job_title")
    organization_name = detail_value(organization, "name") or detail_value(lead, "company_name") or "No organization linked"
    location = " / ".join(
        item for item in [
            detail_value(organization, "country") or detail_value(lead, "country"),
            detail_value(organization, "city") or detail_value(lead, "city"),
        ]
        if item
    )
    lead_status = detail_value(lead, "lead_status", "New")
    customer_status = detail_value(organization, "customer_status", "")
    relationship_status = detail_value(contact, "relationship_status", "")

    if st.button("Back to Leads List"):
        st.session_state.selected_lead_id = None
        st.session_state.pending_page = "Leads List"
        st.rerun()

    st.title(contact_name)
    st.caption(" | ".join(item for item in [job_title, organization_name, location] if item))

    email = detail_value(contact, "email") or detail_value(lead, "email")
    phone = detail_value(contact, "phone") or detail_value(lead, "phone")
    whatsapp = detail_value(contact, "whatsapp") or detail_value(lead, "whatsapp")
    wechat = detail_value(contact, "wechat") or detail_value(lead, "wechat")
    editing = st.session_state.get(edit_key, False)

    org_data = {}
    contact_data = {}
    lead_data = {}

    def render_comm_actions():
        comm_cols = st.columns(4)
        with comm_cols[0]:
            if email:
                st.link_button("Email", f"mailto:{email}")
            else:
                st.button("Email", disabled=True)
        with comm_cols[1]:
            if phone:
                st.link_button("Call", f"tel:{phone}")
            else:
                st.button("Call", disabled=True)
        with comm_cols[2]:
            whatsapp_number = re.sub(r"[^0-9]", "", whatsapp or "")
            if whatsapp_number:
                st.link_button("WhatsApp", f"https://wa.me/{whatsapp_number}")
            else:
                st.button("WhatsApp", disabled=True)
        with comm_cols[3]:
            if wechat:
                st.text_input("WeChat ID", value=wechat, disabled=True, key=f"wechat_copy_{lead_id}")
                components.html(
                    f"""
                    <button
                        style="background:#1c2636;color:#edf2f7;border:1px solid #3d4b63;border-radius:6px;padding:8px 12px;cursor:pointer;"
                        onclick="navigator.clipboard.writeText({wechat!r})"
                    >
                        Copy
                    </button>
                    """,
                    height=44,
                )
            else:
                st.button("WeChat", disabled=True)

    def render_activity_list(limit=None):
        shown_activities = activities[:limit] if limit else activities
        if not shown_activities:
            st.info("No activities yet.")
            return
        for activity in shown_activities:
            timestamp = detail_value(activity, "activity_at") or detail_value(activity, "created_at")
            description = detail_value(activity, "description") or detail_value(activity, "summary")
            user = detail_value(activity, "user", "admin")
            st.markdown(f"**{timestamp}** - {detail_value(activity, 'activity_type')}")
            st.write(description)
            st.caption(f"User: {user}")

    def render_status_actions():
        st.markdown("**Lead**")
        action_cols = st.columns(5)
        for col, action in zip(action_cols, ["Contacted", "Replied", "Qualified", "Disqualified", "Converted"]):
            if col.button(action, key=f"lead_action_{action}_{lead_id}"):
                update_lead_status_action(lead_id, action)
                st.rerun()

        st.markdown("**Relationship**")
        relationship_cols = st.columns(5)
        for col, status in zip(relationship_cols, ["Connected", "Introduced", "Warm", "Active", "Inactive"]):
            if col.button(status, key=f"contact_action_{status}_{lead_id}", disabled=not contact):
                update_contact_relationship_action(contact["id"], status)
                st.rerun()

        st.markdown("**Customer**")
        customer_cols = st.columns(4)
        for col, status in zip(customer_cols, ["Prospect", "Qualified", "Customer", "Inactive"]):
            if col.button(status, key=f"org_action_{status}_{lead_id}", disabled=not organization):
                update_organization_customer_action(organization["id"], status)
                st.rerun()

    overview_tab, organization_tab, contact_tab, activities_tab, notes_tab = st.tabs(
        ["Overview", "Organization", "Contact", "Activities", "Notes"]
    )

    with overview_tab:
        status_cols = st.columns(5)
        status_cols[0].metric("Lead Status", lead_status)
        status_cols[1].metric("Relationship Status", relationship_status or "No contact linked")
        status_cols[2].metric("Customer Status", customer_status or "No organization linked")
        status_cols[3].metric("Data Quality", f"{data_quality.get('overall_score', 0)}%")
        status_cols[4].metric(
            "Relationship Health",
            f"{relationship_health.get('score', 0)}%",
            delta=relationship_health.get("label", ""),
        )

        quality_cols = st.columns(3)
        quality_cols[0].metric("Contact Completeness", f"{data_quality.get('contact_score', 0)}%")
        quality_cols[1].metric("Organization Completeness", f"{data_quality.get('organization_score', 0)}%")
        with quality_cols[2]:
            with st.popover("Health Details"):
                st.write(f"Status: {relationship_health.get('label', '-')}")
                st.write(f"Last contact: {relationship_health.get('last_contacted_at') or '-'}")
                st.write(f"Next follow-up: {relationship_health.get('next_follow_up_at') or '-'}")
                st.write("Score components:")
                for item in relationship_health.get("components", []):
                    st.write(f"+{item['points']} {item['label']}")

        st.subheader("Missing Data Checklist")
        checklist_cols = st.columns(2)
        contact_missing = missing_data.get("contact", [])
        organization_missing = missing_data.get("organization", [])
        with checklist_cols[0]:
            st.markdown("**Contact**")
            if contact_missing:
                for item in contact_missing:
                    st.checkbox(item["label"], value=False, disabled=True, key=f"missing_contact_{lead_id}_{item['field']}")
            else:
                st.success("Contact data complete.")
        with checklist_cols[1]:
            st.markdown("**Organization**")
            if organization_missing:
                for item in organization_missing:
                    st.checkbox(item["label"], value=False, disabled=True, key=f"missing_org_{lead_id}_{item['field']}")
            else:
                st.success("Organization data complete.")

        st.subheader("Communication")
        render_comm_actions()

        st.subheader("Next Follow-up")
        follow_col1, follow_col2, follow_col3, follow_col4 = st.columns([2, 1, 1, 1])
        next_action = follow_col1.text_input("Next Action", value=detail_value(lead, "next_action"), key=f"next_action_{lead_id}")
        next_action_date = follow_col2.text_input("Next Action Date", value=detail_value(lead, "next_action_date"), key=f"next_action_date_{lead_id}")
        if follow_col3.button("Save Follow-up", key=f"save_follow_{lead_id}"):
            update_lead_next_follow_up(lead_id, next_action, next_action_date)
            st.success("Next follow-up saved.")
            st.rerun()
        if follow_col4.button("Mark Completed", key=f"complete_follow_{lead_id}"):
            complete_follow_up(lead_id)
            st.success("Follow-up completed.")
            st.rerun()

        with st.popover("Create Opportunity"):
            default_opp_name = f"{organization_name} - {contact_name}"
            opp_name = st.text_input("Opportunity Name", value=default_opp_name, key=f"lead_opp_name_{lead_id}")
            opp_cols = st.columns(3)
            opp_stage = opp_cols[0].selectbox("Stage", OPPORTUNITY_STAGES, key=f"lead_opp_stage_{lead_id}")
            opp_lane = opp_cols[1].text_input("Trade Lane", key=f"lead_opp_lane_{lead_id}")
            opp_service = opp_cols[2].text_input("Service Type", key=f"lead_opp_service_{lead_id}")
            opp_value_cols = st.columns(4)
            opp_revenue = opp_value_cols[0].text_input("Potential Revenue", key=f"lead_opp_revenue_{lead_id}")
            opp_profit = opp_value_cols[1].text_input("Potential Profit", key=f"lead_opp_profit_{lead_id}")
            opp_close = opp_value_cols[2].text_input("Expected Close Date", placeholder="YYYY-MM-DD", key=f"lead_opp_close_{lead_id}")
            opp_next_date = opp_value_cols[3].text_input("Next Action Date", placeholder="YYYY-MM-DD", key=f"lead_opp_next_date_{lead_id}")
            opp_next = st.text_input("Next Action", key=f"lead_opp_next_{lead_id}")
            opp_notes = st.text_area("Notes", key=f"lead_opp_notes_{lead_id}")
            if st.button("Save Opportunity", type="primary", key=f"lead_opp_save_{lead_id}"):
                opportunity_id = save_opportunity(
                    {
                        "opportunity_name": opp_name,
                        "organization_id": detail_value(lead, "organization_id"),
                        "contact_id": detail_value(lead, "contact_id"),
                        "owner": None,
                        "stage": opp_stage,
                        "trade_lane": opp_lane,
                        "service_type": opp_service,
                        "potential_revenue": opp_revenue,
                        "potential_profit": opp_profit,
                        "expected_close_date": opp_close,
                        "next_action": opp_next,
                        "next_action_date": opp_next_date,
                        "notes": opp_notes,
                    }
                )
                st.session_state.selected_opportunity_id = opportunity_id
                st.session_state.pending_page = "Opportunities"
                st.rerun()

        st.subheader("Relationship Actions")
        render_status_actions()

        st.subheader("Recent Activity")
        render_activity_list(limit=5)

    with organization_tab:
        edit_col1, edit_col2, edit_col3 = st.columns(3)
        if edit_col1.button("Edit", disabled=editing, key=f"org_edit_{lead_id}"):
            st.session_state[edit_key] = True
            st.rerun()
        if not organization:
            st.info("No organization linked.")
        org_data["name"] = st.text_input("Organization Name", value=detail_value(organization, "name"), disabled=not editing or not organization)
        org_data["local_name"] = st.text_input("Local Name", value=detail_value(organization, "local_name"), disabled=not editing or not organization)
        org_data["type"] = st.selectbox(
            "Type",
            ORG_TYPE_OPTIONS,
            index=ORG_TYPE_OPTIONS.index(detail_value(organization, "type", "Other")) if detail_value(organization, "type", "Other") in ORG_TYPE_OPTIONS else ORG_TYPE_OPTIONS.index("Other"),
            disabled=not editing or not organization,
        )
        org_data["country"] = st.text_input("Country", value=detail_value(organization, "country"), disabled=not editing or not organization)
        org_data["province"] = st.text_input("Province", value=detail_value(organization, "province"), disabled=not editing or not organization)
        org_data["city"] = st.text_input("City", value=detail_value(organization, "city"), disabled=not editing or not organization)
        org_data["website"] = st.text_input("Website", value=detail_value(organization, "website"), disabled=not editing or not organization)
        org_data["founding_date"] = st.text_input("Founding Date", value=detail_value(organization, "founding_date"), disabled=not editing or not organization)
        org_data["anniversary_date"] = st.text_input("Cooperation Anniversary", value=detail_value(organization, "anniversary_date"), disabled=not editing or not organization)
        org_data["preferred_language"] = st.selectbox(
            "Preferred Language",
            PREFERRED_LANGUAGE_OPTIONS,
            index=PREFERRED_LANGUAGE_OPTIONS.index(detail_value(organization, "preferred_language", "English")) if detail_value(organization, "preferred_language", "English") in PREFERRED_LANGUAGE_OPTIONS else 0,
            disabled=not editing or not organization,
            key=f"org_pref_lang_{lead_id}",
        )
        org_data["relationship_tone"] = st.selectbox(
            "Relationship Tone",
            RELATIONSHIP_TONE_OPTIONS,
            index=RELATIONSHIP_TONE_OPTIONS.index(detail_value(organization, "relationship_tone", "Warm")) if detail_value(organization, "relationship_tone", "Warm") in RELATIONSHIP_TONE_OPTIONS else 1,
            disabled=not editing or not organization,
            key=f"org_tone_{lead_id}",
        )
        org_data["membership"] = st.text_input("Membership", value=detail_value(organization, "membership"), disabled=not editing or not organization)
        org_data["customer_status"] = st.selectbox(
            "Customer Status",
            CUSTOMER_STATUS_OPTIONS,
            index=CUSTOMER_STATUS_OPTIONS.index(detail_value(organization, "customer_status", "Prospect")) if detail_value(organization, "customer_status", "Prospect") in CUSTOMER_STATUS_OPTIONS else 0,
            disabled=not editing or not organization,
        )
        org_data["notes"] = st.text_area("Organization Notes", value=detail_value(organization, "notes"), disabled=not editing or not organization)
        if editing:
            if edit_col2.button("Save", key=f"org_save_{lead_id}"):
                update_lead_detail(lead_id, org_data if organization else {}, {}, lead)
                if organization:
                    sync_date_based_occasions(organization_id=organization["id"])
                st.session_state[edit_key] = False
                st.success("Organization saved.")
                st.rerun()
            if edit_col3.button("Cancel", key=f"org_cancel_{lead_id}"):
                st.session_state[edit_key] = False
                st.rerun()
        occasion_cols = st.columns(2)
        with occasion_cols[0]:
            with st.popover("Add Occasion", disabled=not organization):
                occasion_type = st.selectbox("Type", OCCASION_TYPE_OPTIONS, key=f"org_occ_type_{lead_id}")
                occasion_name = st.text_input("Occasion Name", key=f"org_occ_name_{lead_id}")
                occasion_date = st.text_input("Occasion Date", placeholder="YYYY-MM-DD", key=f"org_occ_date_{lead_id}")
                if st.button("Create Occasion", key=f"org_occ_create_{lead_id}"):
                    create_relationship_occasion(
                        {
                            "organization_id": organization["id"],
                            "contact_id": contact["id"] if contact else None,
                            "occasion_type": occasion_type,
                            "occasion_name": occasion_name,
                            "occasion_date": occasion_date,
                            "country": detail_value(organization, "country"),
                            "preferred_language": detail_value(organization, "preferred_language", "English"),
                            "message_tone": detail_value(organization, "relationship_tone", "Warm"),
                            "preferred_channel": "WeChat",
                            "reminder_days_before": 7,
                        }
                    )
                    st.rerun()
        with occasion_cols[1]:
            if st.button("Add Holiday Reminders for this Country", disabled=not organization, key=f"org_add_holidays_{lead_id}"):
                created = add_country_holiday_reminders(organization["id"], contact["id"] if contact else None)
                st.success(f"Added {created} holiday reminders.")
                st.rerun()

    with contact_tab:
        edit_col1, edit_col2, edit_col3 = st.columns(3)
        if edit_col1.button("Edit", disabled=editing, key=f"contact_edit_{lead_id}"):
            st.session_state[edit_key] = True
            st.rerun()
        if not contact:
            st.info("No contact linked.")
        contact_data["name"] = st.text_input("Contact Name", value=detail_value(contact, "name"), disabled=not editing or not contact)
        contact_data["job_title"] = st.text_input("Job Title", value=detail_value(contact, "job_title"), disabled=not editing or not contact)
        contact_data["email"] = st.text_input("Email", value=detail_value(contact, "email"), disabled=not editing or not contact)
        contact_data["email_status"] = st.selectbox(
            "Email Status",
            EMAIL_STATUS_OPTIONS,
            index=EMAIL_STATUS_OPTIONS.index(detail_value(contact, "email_status", "Unknown")) if detail_value(contact, "email_status", "Unknown") in EMAIL_STATUS_OPTIONS else 0,
            disabled=not editing or not contact,
        )
        email_action_cols = st.columns(3)
        for col, status in zip(email_action_cols, ["Valid", "Invalid", "Bounced"]):
            if col.button(f"Mark Email {status}", key=f"email_status_{status}_{lead_id}", disabled=not contact):
                update_contact_email_status(contact["id"], status, "Manual update from Lead Detail")
                st.rerun()
        contact_data["phone"] = st.text_input("Phone", value=detail_value(contact, "phone"), disabled=not editing or not contact)
        contact_data["wechat"] = st.text_input("WeChat", value=detail_value(contact, "wechat"), disabled=not editing or not contact)
        contact_data["whatsapp"] = st.text_input("Whatsapp", value=detail_value(contact, "whatsapp"), disabled=not editing or not contact)
        contact_data["birthday"] = st.text_input("Birthday", value=detail_value(contact, "birthday"), disabled=not editing or not contact)
        contact_data["preferred_language"] = st.selectbox(
            "Preferred Language",
            PREFERRED_LANGUAGE_OPTIONS,
            index=PREFERRED_LANGUAGE_OPTIONS.index(detail_value(contact, "preferred_language", "English")) if detail_value(contact, "preferred_language", "English") in PREFERRED_LANGUAGE_OPTIONS else 0,
            disabled=not editing or not contact,
            key=f"contact_pref_lang_{lead_id}",
        )
        contact_data["preferred_channel"] = st.selectbox(
            "Preferred Channel",
            PREFERRED_CHANNEL_OPTIONS,
            index=PREFERRED_CHANNEL_OPTIONS.index(detail_value(contact, "preferred_channel", "WeChat")) if detail_value(contact, "preferred_channel", "WeChat") in PREFERRED_CHANNEL_OPTIONS else 3,
            disabled=not editing or not contact,
            key=f"contact_pref_channel_{lead_id}",
        )
        contact_data["relationship_tone"] = st.selectbox(
            "Relationship Tone",
            RELATIONSHIP_TONE_OPTIONS,
            index=RELATIONSHIP_TONE_OPTIONS.index(detail_value(contact, "relationship_tone", "Warm")) if detail_value(contact, "relationship_tone", "Warm") in RELATIONSHIP_TONE_OPTIONS else 1,
            disabled=not editing or not contact,
            key=f"contact_tone_{lead_id}",
        )
        contact_data["relationship_status"] = st.selectbox(
            "Relationship Status",
            RELATIONSHIP_STATUS_OPTIONS,
            index=RELATIONSHIP_STATUS_OPTIONS.index(detail_value(contact, "relationship_status", "New")) if detail_value(contact, "relationship_status", "New") in RELATIONSHIP_STATUS_OPTIONS else 0,
            disabled=not editing or not contact,
        )
        contact_data["last_contacted_at"] = st.text_input("Last Contacted At", value=detail_value(contact, "last_contacted_at"), disabled=not editing or not contact)
        contact_data["next_follow_up_at"] = st.text_input("Next Follow-up At", value=detail_value(contact, "next_follow_up_at"), disabled=not editing or not contact)
        contact_data["notes"] = st.text_area("Contact Notes", value=detail_value(contact, "notes"), disabled=not editing or not contact)
        if editing:
            if edit_col2.button("Save", key=f"contact_save_{lead_id}"):
                update_lead_detail(lead_id, {}, contact_data if contact else {}, lead)
                if contact:
                    sync_date_based_occasions(
                        organization_id=organization["id"] if organization else None,
                        contact_id=contact["id"],
                    )
                st.session_state[edit_key] = False
                st.success("Contact saved.")
                st.rerun()
            if edit_col3.button("Cancel", key=f"contact_cancel_{lead_id}"):
                st.session_state[edit_key] = False
                st.rerun()
        with st.popover("Add Occasion", disabled=not contact):
            occasion_type = st.selectbox("Type", OCCASION_TYPE_OPTIONS, key=f"contact_occ_type_{lead_id}")
            occasion_name = st.text_input("Occasion Name", key=f"contact_occ_name_{lead_id}")
            occasion_date = st.text_input("Occasion Date", placeholder="YYYY-MM-DD", key=f"contact_occ_date_{lead_id}")
            if st.button("Create Occasion", key=f"contact_occ_create_{lead_id}"):
                create_relationship_occasion(
                    {
                        "organization_id": organization["id"] if organization else None,
                        "contact_id": contact["id"],
                        "occasion_type": occasion_type,
                        "occasion_name": occasion_name,
                        "occasion_date": occasion_date,
                        "country": detail_value(organization, "country"),
                        "preferred_language": detail_value(contact, "preferred_language", "English"),
                        "message_tone": detail_value(contact, "relationship_tone", "Warm"),
                        "preferred_channel": detail_value(contact, "preferred_channel", "WeChat"),
                        "reminder_days_before": 7,
                    }
                )
                st.rerun()

    with activities_tab:
        st.subheader("Activity Timeline")
        render_activity_list()

    with notes_tab:
        st.subheader("Relationship Notes")
        notes_value = st.text_area(
            "Notes",
            value=detail_value(lead, "notes"),
            height=360,
            key=f"relationship_notes_{lead_id}",
        )
        if st.button("Save Notes", key=f"save_notes_{lead_id}"):
            update_lead_notes(lead_id, notes_value)
            st.success("Notes saved.")
            st.rerun()

        st.divider()
        st.subheader("Lead Fields")
        edit_col1, edit_col2, edit_col3 = st.columns(3)
        if edit_col1.button("Edit Lead", disabled=editing, key=f"lead_edit_{lead_id}"):
            st.session_state[edit_key] = True
            st.rerun()
        lead_data["source"] = st.text_input("Source", value=detail_value(lead, "source"), disabled=not editing)
        lead_data["campaign"] = st.text_input("Campaign", value=detail_value(lead, "campaign"), disabled=not editing)
        lead_data["lead_status"] = st.selectbox(
            "Lead Status",
            LEAD_STATUS_OPTIONS,
            index=LEAD_STATUS_OPTIONS.index(detail_value(lead, "lead_status", "New")) if detail_value(lead, "lead_status", "New") in LEAD_STATUS_OPTIONS else 0,
            disabled=not editing,
        )
        lead_data["interest_level"] = st.text_input("Interest Level", value=detail_value(lead, "interest_level"), disabled=not editing)
        lead_data["next_action"] = st.text_input("Lead Next Action", value=detail_value(lead, "next_action"), disabled=not editing)
        lead_data["next_action_date"] = st.text_input("Lead Next Action Date", value=detail_value(lead, "next_action_date"), disabled=not editing)
        lead_data["notes"] = st.text_area("Lead Notes", value=detail_value(lead, "notes"), disabled=not editing)
        st.text_input("Created At", value=detail_value(lead, "created_at"), disabled=True)
        st.text_input("Updated At", value=detail_value(lead, "updated_at"), disabled=True)
        if editing:
            if edit_col2.button("Save", key=f"lead_save_{lead_id}"):
                update_lead_detail(lead_id, {}, {}, lead_data)
                st.session_state[edit_key] = False
                st.success("Lead saved.")
                st.rerun()
            if edit_col3.button("Cancel", key=f"lead_cancel_{lead_id}"):
                st.session_state[edit_key] = False
                st.rerun()


def show_leads_list():
    if st.session_state.get("selected_lead_id"):
        show_lead_detail(st.session_state.selected_lead_id)
        return

    st.title("Leads List")

    leads = get_leads()
    if not leads:
        st.info("No leads found yet.")
        return

    def lead_value(lead, key, default=""):
        try:
            return lead[key]
        except (IndexError, KeyError):
            return default

    def unique_options(key):
        return sorted({str(lead_value(lead, key)).strip() for lead in leads if str(lead_value(lead, key)).strip()})

    filter_defaults = {
        "lead_filter_country": [],
        "lead_filter_city": [],
        "lead_filter_membership": [],
        "lead_filter_lead_status": [],
        "lead_filter_customer_status": [],
        "lead_filter_relationship_status": [],
        "lead_filter_email_status": [],
    }
    for key, value in filter_defaults.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("leads_list_page_number", 1)

    st.subheader("All Leads")

    quick_country_cols = st.columns(4)
    for col, country_name in zip(quick_country_cols, ["China", "USA", "India", "Vietnam"]):
        if col.button(country_name, key=f"quick_country_{country_name}"):
            st.session_state.lead_filter_country = [country_name]
            st.session_state.leads_list_page_number = 1
            st.rerun()

    quick_status_cols = st.columns(4)
    for col, status_name in zip(quick_status_cols, ["New", "Contacted", "Qualified", "Converted"]):
        if col.button(status_name, key=f"quick_status_{status_name}"):
            st.session_state.lead_filter_lead_status = [status_name]
            st.session_state.leads_list_page_number = 1
            st.rerun()

    quick_membership_cols = st.columns(4)
    for col, membership_name in zip(quick_membership_cols[:3], ["OLO", "WCA", "JCTrans"]):
        if col.button(membership_name, key=f"quick_membership_{membership_name}"):
            st.session_state.lead_filter_membership = [membership_name]
            st.session_state.leads_list_page_number = 1
            st.rerun()
    if quick_membership_cols[3].button("Clear Filters", key="clear_lead_filters"):
        for key in filter_defaults:
            st.session_state[key] = []
        st.session_state.leads_search = ""
        st.session_state.leads_list_page_number = 1
        st.rerun()

    search_text = st.text_input("Search Leads", key="leads_search", placeholder="Ronghua, Jackson, Shenzhen, WCA")

    filter_cols = st.columns(3)
    country_filter = filter_cols[0].multiselect("Country", unique_options("country"), key="lead_filter_country")
    city_filter = filter_cols[1].multiselect("City", unique_options("city"), key="lead_filter_city")
    membership_filter = filter_cols[2].multiselect("Membership", unique_options("membership"), key="lead_filter_membership")

    filter_cols2 = st.columns(4)
    lead_status_filter = filter_cols2[0].multiselect("Lead Status", unique_options("lead_status"), key="lead_filter_lead_status")
    customer_status_filter = filter_cols2[1].multiselect("Customer Status", unique_options("customer_status"), key="lead_filter_customer_status")
    relationship_status_filter = filter_cols2[2].multiselect("Relationship Status", unique_options("relationship_status"), key="lead_filter_relationship_status")
    email_status_filter = filter_cols2[3].multiselect("Email Status", ["Valid", "Unknown", "Bounced", "Invalid"], key="lead_filter_email_status")

    sort_by = st.selectbox(
        "Sort by",
        ["Priority Score", "Created Date", "Last Contacted", "Next Follow-up", "Company", "Country"],
        key="leads_sort_by",
    )

    def contains_any(value, selected_values):
        if not selected_values:
            return True
        value_text = str(value or "").strip().lower()
        return any(str(selected).strip().lower() == value_text for selected in selected_values)

    def membership_matches(value, selected_values):
        if not selected_values:
            return True
        value_text = str(value or "").lower()
        return any(str(selected).lower() in value_text for selected in selected_values)

    search_lower = (search_text or "").strip().lower()
    search_fields = ["company_name", "contact_person", "email", "phone", "wechat", "whatsapp", "city", "country", "membership"]

    filtered_leads = []
    for lead in leads:
        if search_lower:
            haystack = " ".join(str(lead_value(lead, field) or "") for field in search_fields).lower()
            if search_lower not in haystack:
                continue
        if not contains_any(lead_value(lead, "country"), country_filter):
            continue
        if not contains_any(lead_value(lead, "city"), city_filter):
            continue
        if not membership_matches(lead_value(lead, "membership"), membership_filter):
            continue
        if not contains_any(lead_value(lead, "lead_status", "New"), lead_status_filter):
            continue
        if not contains_any(lead_value(lead, "customer_status", "Prospect"), customer_status_filter):
            continue
        if not contains_any(lead_value(lead, "relationship_status", "New"), relationship_status_filter):
            continue
        if not contains_any(lead_value(lead, "email_status", "Unknown"), email_status_filter):
            continue
        filtered_leads.append(lead)

    def date_sort_value(value, reverse=False):
        text = str(value or "")
        if not text:
            return "0000-00-00" if reverse else "9999-99-99"
        return text

    if sort_by == "Priority Score":
        filtered_leads.sort(key=lambda lead: int(lead_value(lead, "priority_score", 0) or 0), reverse=True)
    elif sort_by == "Created Date":
        filtered_leads.sort(key=lambda lead: date_sort_value(lead_value(lead, "created_at"), reverse=True), reverse=True)
    elif sort_by == "Last Contacted":
        filtered_leads.sort(key=lambda lead: date_sort_value(lead_value(lead, "last_contacted_at"), reverse=True), reverse=True)
    elif sort_by == "Next Follow-up":
        filtered_leads.sort(key=lambda lead: date_sort_value(lead_value(lead, "next_follow_up_at") or lead_value(lead, "next_action_date")))
    elif sort_by == "Company":
        filtered_leads.sort(key=lambda lead: str(lead_value(lead, "company_name") or "").lower())
    elif sort_by == "Country":
        filtered_leads.sort(key=lambda lead: str(lead_value(lead, "country") or "").lower())

    total_count = len(leads)
    filtered_count = len(filtered_leads)
    st.caption(f"Showing {filtered_count} of {total_count} leads")

    page_size = 25
    total_pages = max(1, (filtered_count + page_size - 1) // page_size)
    st.session_state.leads_list_page_number = min(max(1, int(st.session_state.leads_list_page_number)), total_pages)
    page_number = st.session_state.leads_list_page_number
    start = (page_number - 1) * page_size
    end = start + page_size
    page_rows = filtered_leads[start:end]

    nav_cols = st.columns([1, 1, 4])
    if nav_cols[0].button("Previous", disabled=page_number <= 1, key="leads_prev_page"):
        st.session_state.leads_list_page_number = max(1, page_number - 1)
        st.rerun()
    if nav_cols[1].button("Next", disabled=page_number >= total_pages, key="leads_next_page"):
        st.session_state.leads_list_page_number = min(total_pages, page_number + 1)
        st.rerun()
    nav_cols[2].write(f"Page {page_number} of {total_pages}")

    header = st.columns([1, 2, 3, 1.5, 1.5, 1.5, 1.6, 1.4, 2, 1])
    for col, label in zip(header, ["Priority", "Contact", "Company", "Country", "Membership", "Lead Status", "Relationship", "Email Status", "Next Follow-up", "Action"]):
        col.write(label)

    if not page_rows:
        st.info("No leads match the current search and filters.")
        return

    for lead in page_rows:
        row_cols = st.columns([1, 2, 3, 1.5, 1.5, 1.5, 1.6, 1.4, 2, 1])
        row_cols[0].write(int(lead_value(lead, "priority_score", 0) or 0))
        row_cols[1].write(lead_value(lead, "contact_person") or "No contact")
        row_cols[2].write(lead_value(lead, "company_name") or "No company")
        row_cols[3].write(lead_value(lead, "country") or "-")
        row_cols[4].write(lead_value(lead, "membership") or "-")
        row_cols[5].write(lead_value(lead, "lead_status", "New"))
        row_cols[6].write(lead_value(lead, "relationship_status", "New") or "New")
        email_status = lead_value(lead, "email_status", "Unknown") or "Unknown"
        email_tone = "red" if email_status in ["Invalid", "Bounced"] else "green" if email_status == "Valid" else "neutral"
        with row_cols[7]:
            status_badge(email_status, email_tone)
        row_cols[8].write(lead_value(lead, "next_follow_up_at") or lead_value(lead, "next_action_date") or "-")
        if row_cols[9].button("Open", key=f"open_lead_{lead_value(lead, 'id')}"):
            st.session_state.selected_lead_id = lead_value(lead, "id")
            st.rerun()



tracking_token = st.query_params.get("track_open")
if tracking_token:
    record_outreach_open(tracking_token)
    st.markdown(
        "<div style='width:1px;height:1px;overflow:hidden;opacity:0;'>tracked</div>",
        unsafe_allow_html=True,
    )
    st.stop()


pending_page = st.session_state.pop("pending_page", None)
if pending_page:
    if pending_page == "Inquiry Intake":
        pending_page = "Opportunities"
    if pending_page in ["Outreach Campaigns", "Quick Capture", "Leads Import", "Leads List"]:
        st.session_state.page = "Leads"
        st.session_state.leads_page = pending_page
        st.session_state.preserve_subpage_once = True
    elif pending_page in ["Follow-up Queue", "Occasion Reminders"]:
        st.session_state.page = "Relationships"
        st.session_state.relationships_page = pending_page
        st.session_state.preserve_subpage_once = True
    else:
        st.session_state.page = pending_page
if "leads_page" not in st.session_state:
    st.session_state.leads_page = "Leads List"
if "relationships_page" not in st.session_state:
    st.session_state.relationships_page = "Follow-up Queue"
preserve_subpage_once = bool(st.session_state.pop("preserve_subpage_once", False))

with st.sidebar:
    st.title("1Aim")

    page = st.radio(
        "Menu",
        ["Dashboard", "Relationships", "Opportunities", "Pricing Engine", "Quotation Engine", "Leads", "Knowledge Base", "Admin"],
        key="page",
    )
    previous_parent_page = st.session_state.get("previous_parent_page")
    if page == "Leads" and previous_parent_page != "Leads" and not preserve_subpage_once:
        st.session_state.leads_page = "Leads List"
    if page == "Relationships" and previous_parent_page != "Relationships" and not preserve_subpage_once:
        st.session_state.relationships_page = "Follow-up Queue"

    if page == "Relationships":
        st.radio(
            "Relationships",
            ["Follow-up Queue", "Occasion Reminders"],
            key="relationships_page",
        )
    if page == "Leads":
        st.radio(
            "Leads",
            ["Leads List", "Quick Capture", "Leads Import", "Outreach Campaigns"],
            key="leads_page",
        )
    if page == "Knowledge Base":
        st.radio(
            "Knowledge Base",
            ["Legal Library", "SOP Library", "Case Library", "Intelligence Library", "Compliance Engine", "AI Assistant"],
            key="knowledge_base_page",
        )
    st.session_state.previous_parent_page = page

apply_global_typography(st.session_state.ui_scale)
maybe_run_auto_git_backup()

if page == "Dashboard":
    show_dashboard()
elif page == "Relationships":
    relationships_page = st.session_state.get("relationships_page", "Follow-up Queue")
    if relationships_page == "Occasion Reminders":
        show_occasion_reminders()
    else:
        show_follow_up_queue()
elif page == "Opportunities":
    show_opportunities()
elif page == "Pricing Engine":
    show_pricing_engine()
elif page == "Quotation Engine":
    show_quotation_engine()
elif page == "Leads":
    leads_page = st.session_state.get("leads_page", "Leads List")
    if leads_page == "Outreach Campaigns":
        show_outreach_campaigns()
    elif leads_page == "Quick Capture":
        show_quick_capture()
    elif leads_page == "Leads Import":
        show_leads_import()
    else:
        show_leads_list()
elif page == "Knowledge Base":
    show_knowledge_base()
elif page == "Admin":
    show_admin()
else:
    show_dashboard()
