import logging
import importlib
import re
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import database as database_module

database_module = importlib.reload(database_module)

from database import (
    convert_lead_to_contact,
    create_inquiry,
    find_captured_crm_duplicates,
    get_app_setting,
    get_database_backup_status,
    get_existing_lead_keys,
    get_lead_detail,
    get_leads,
    get_crm_dashboard_data,
    get_crm_follow_up_rows,
    get_daily_outreach_capacity,
    get_holiday_library,
    get_open_tasks,
    get_task_counts_by_type,
    import_leads,
    initialize_missing_lead_followups,
    init_db,
    mark_prepare_quote_sent,
    save_captured_crm_record,
    save_holiday_library_item,
    has_captured_crm_duplicates,
    set_app_setting,
    complete_follow_up,
    add_country_holiday_reminders,
    create_relationship_occasion,
    snooze_follow_up,
    get_occasion_reminders,
    mark_occasion_message_sent,
    snooze_occasion,
    sync_date_based_occasions,
    refresh_lead_priority_scores,
    update_relationship_occasion,
    update_contact_relationship_action,
    update_lead_detail,
    update_lead_next_follow_up,
    update_lead_notes,
    update_lead_status_action,
    update_organization_customer_action,
)
from typography import DEFAULT_UI_SCALE, UI_SCALE_OPTIONS, get_typography_tokens


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
        }
        .stApp {
            background: #0b1018;
            color: #edf2f7;
            font-size: var(--font-size-sm);
        }
        [data-testid="stSidebar"] {
            background: #111827;
            border-right: 1px solid #263244;
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
            background: #141c2a;
            border: 1px solid #263244;
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
            border: 1px solid #263244;
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
            border: 1px solid #3d4b63;
            background: #1c2636;
            color: #edf2f7;
            font-size: var(--font-size-sm) !important;
            line-height: 1.35 !important;
            min-height: calc(var(--font-size-sm) * 2.5);
        }
        .stButton > button[kind="primary"] {
            background: #2f80ed;
            border-color: #2f80ed;
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


def show_dashboard():
    st.title("CRM Sales Cockpit")
    data = get_crm_dashboard_data()
    kpis = data["kpis"]
    outreach_queue = data["outreach_queue"]

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
        header_cols = st.columns([1, 2, 2, 1, 2, 1, 1, 1])
        header_cols[0].caption("Priority")
        header_cols[1].caption("Contact")
        header_cols[2].caption("Organization")
        header_cols[3].caption("Country")
        header_cols[4].caption("Next Action")
        header_cols[5].caption("Open")
        header_cols[6].caption("Done")
        header_cols[7].caption("Snooze")
    for row in data["today_action_list"]:
        cols = st.columns([1, 2, 2, 1, 2, 1, 1, 1])
        with cols[0]:
            priority_badge(row["priority_score"])
        cols[1].write(row["contact_name"] or "No contact")
        cols[2].write(row["organization_name"] or "No organization")
        cols[3].write(row["country"] or "-")
        cols[4].write(row["recommended_action"] or row["next_action"] or "Follow up")
        if cols[5].button("Open", key=f"dash_action_open_{row['lead_id']}"):
            st.session_state.selected_lead_id = row["lead_id"]
            st.session_state.pending_page = "Leads List"
            st.rerun()
        if cols[6].button("Done", key=f"dash_action_done_{row['lead_id']}"):
            complete_follow_up(row["lead_id"])
            st.rerun()
        if cols[7].button("Snooze", key=f"dash_action_snooze_{row['lead_id']}"):
            snooze_follow_up(row["lead_id"], 7)
            st.rerun()

    st.subheader("China Priority Leads")
    if not data["china_priority_leads"]:
        st.info("No China priority leads in the active queue.")
    else:
        header_cols = st.columns([2, 2, 1, 1, 1, 1])
        header_cols[0].caption("Contact")
        header_cols[1].caption("Company")
        header_cols[2].caption("City")
        header_cols[3].caption("Membership")
        header_cols[4].caption("Status")
        header_cols[5].caption("Score")
    for row in data["china_priority_leads"]:
        cols = st.columns([2, 2, 1, 1, 1, 1])
        cols[0].write(row["contact_name"] or "No contact")
        cols[1].write(row["organization_name"] or "No organization")
        cols[2].write(row["city"] or "-")
        cols[3].write(row["membership"] or "-")
        cols[4].write(row["relationship_status"] or row["lead_status"] or "-")
        with cols[5]:
            priority_badge(row["priority_score"])

    st.subheader("Overdue Follow-ups")
    show_mini_rows(data["overdue_followups"], "dash_overdue")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Warm Relationships")
        show_mini_rows(data["warm_relationships"], "dash_warm")
    with col_b:
        st.subheader("New Leads Needing First Touch")
        show_mini_rows(data["new_leads_first_touch"], "dash_new")

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


def show_admin():
    st.title("Admin")

    status = get_database_backup_status()
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Current DB Size", format_bytes(status["db_size_bytes"]))
    with col2:
        st.metric("Backups", status["backup_count"])
    with col3:
        st.metric("Latest Backup Time", status["latest_backup_time"] or "No backups")

    if status["latest_backup_name"]:
        st.caption(f"Latest backup: {status['latest_backup_name']}")

    st.divider()
    st.subheader("System Settings")
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

    st.divider()
    st.subheader("CRM Activation")
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
        status_cols = st.columns(3)
        status_cols[0].metric("Lead Status", lead_status)
        status_cols[1].metric("Relationship Status", relationship_status or "No contact linked")
        status_cols[2].metric("Customer Status", customer_status or "No organization linked")

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

    st.subheader("Open Lead")
    for lead in leads[:25]:
        row_cols = st.columns([1, 3, 3, 2, 2])
        row_cols[0].write(f"#{lead_value(lead, 'id')}")
        row_cols[1].write(lead_value(lead, "contact_person") or "No contact name")
        row_cols[2].write(lead_value(lead, "company_name") or "No organization")
        row_cols[3].write(lead_value(lead, "lead_status", "New"))
        if row_cols[4].button("Open", key=f"open_lead_{lead_value(lead, 'id')}"):
            st.session_state.selected_lead_id = lead_value(lead, "id")
            st.rerun()

    st.divider()
    st.subheader("All Leads")

    dataframe = pd.DataFrame(
        [
            {
                "Company": lead_value(lead, "company_name"),
                "Contact Person": lead_value(lead, "contact_person"),
                "Country": lead_value(lead, "country"),
                "City": lead_value(lead, "city"),
                "Job Title": lead_value(lead, "job_title"),
                "Email": lead_value(lead, "email"),
                "WeChat": lead_value(lead, "wechat"),
                "Whatsapp": lead_value(lead, "whatsapp"),
                "Membership": lead_value(lead, "membership"),
                "Source": lead_value(lead, "source"),
                "Campaign": lead_value(lead, "campaign"),
                "Lead Status": lead_value(lead, "lead_status", "New"),
                "Customer Status": lead_value(lead, "customer_status", "Prospect"),
                "Relationship": lead_value(lead, "relationship_status", "New"),
                "Next Action": lead_value(lead, "next_action"),
                "Next Action Date": lead_value(lead, "next_action_date"),
                "Last Contacted": lead_value(lead, "last_contacted_at"),
            }
            for lead in leads
        ]
    )

    st.dataframe(
        dataframe,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Convert Lead")
    open_leads = [
        lead for lead in leads
        if lead_value(lead, "lead_status", "New") != "Converted"
    ]

    if not open_leads:
        st.info("All listed leads are already converted.")
        return

    lead_options = {
        f"#{lead_value(lead, 'id')} - {lead_value(lead, 'company_name') or 'Unknown company'} - {lead_value(lead, 'contact_person') or lead_value(lead, 'email') or lead_value(lead, 'wechat') or lead_value(lead, 'whatsapp') or 'No contact name'}": lead_value(lead, "id")
        for lead in open_leads
    }
    selected_label = st.selectbox(
        "Lead",
        list(lead_options.keys()),
    )

    if st.button("Convert Lead", type="primary"):
        contact_id = convert_lead_to_contact(lead_options[selected_label])
        if contact_id:
            st.success("Lead converted.")
            st.rerun()
        else:
            st.error("Could not find that lead to convert.")

pending_page = st.session_state.pop("pending_page", None)
if pending_page:
    st.session_state.page = pending_page

with st.sidebar:
    st.title("1Aim")
    st.radio(
        "UI Scale",
        UI_SCALE_OPTIONS,
        key="ui_scale",
        index=UI_SCALE_OPTIONS.index(st.session_state.ui_scale),
    )

    if st.session_state.ui_scale != st.session_state.persisted_ui_scale:
        set_app_setting("ui_scale", st.session_state.ui_scale)
        st.session_state.persisted_ui_scale = st.session_state.ui_scale

    page = st.radio(
        "Menu",
        ["Dashboard", "Follow-up Queue", "Occasion Reminders", "Quick Capture", "Leads Import", "Leads List", "Admin"],
        key="page",
    )

apply_global_typography(st.session_state.ui_scale)

if page == "Dashboard":
    show_dashboard()
elif page == "Follow-up Queue":
    show_follow_up_queue()
elif page == "Occasion Reminders":
    show_occasion_reminders()
elif page == "Quick Capture":
    show_quick_capture()
elif page == "Leads Import":
    show_leads_import()
elif page == "Admin":
    show_admin()
else:
    show_leads_list()
