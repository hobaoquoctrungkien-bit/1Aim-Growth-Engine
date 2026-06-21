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
    get_existing_lead_keys,
    get_lead_detail,
    get_leads,
    get_open_tasks,
    get_task_counts_by_type,
    import_leads,
    init_db,
    mark_prepare_quote_sent,
    save_captured_crm_record,
    has_captured_crm_duplicates,
    set_app_setting,
    update_contact_relationship_action,
    update_lead_detail,
    update_lead_next_follow_up,
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
    st.title("1Aim Growth Engine")

    task_counts = get_task_counts_by_type()
    open_tasks = get_open_tasks()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Quote Follow-up", task_counts.get("quote_follow_up", 0))

    with col2:
        st.metric("Lead Nurturing", task_counts.get("relationship_touch", 0))

    with col3:
        st.metric("New Lead Outreach", task_counts.get("new_lead_outreach", 0))

    with col4:
        st.metric("Prepare Quote", task_counts.get("prepare_quote", 0))

    with col5:
        st.metric("Chase Vendor", task_counts.get("chase_vendor", 0))

    st.divider()
    st.subheader("Today Cockpit")

    cockpit_col1, cockpit_col2, cockpit_col3, cockpit_col4, cockpit_col5 = st.columns(5)

    def show_tasks(task_type):
        tasks = [
            task for task in open_tasks
            if task["task_type"] == task_type
        ]

        if not tasks:
            st.info("No open tasks.")
            return

        for task in tasks:
            st.write(task["title"])

            if task["due_date"]:
                st.caption(f"Due: {task['due_date']}")

    def show_prepare_quote_actions():
        tasks = [
            task for task in open_tasks
            if task["task_type"] == "prepare_quote"
        ]

        if not tasks:
            st.info("No open tasks.")
            return

        for task in tasks:
            st.write(task["title"])

            if task["due_date"]:
                st.caption(f"Due: {task['due_date']}")

            follow_up_date = st.date_input(
                "Follow-up date",
                key=f"quote_follow_up_date_{task['id']}",
            )

            if st.button("Mark Quote Sent", key=f"quote_sent_{task['id']}"):
                if mark_prepare_quote_sent(task["id"], follow_up_date.isoformat()):
                    st.success("Quote sent. Follow-up task created.")
                    st.rerun()
                else:
                    st.warning("This task is no longer available.")

    with cockpit_col1:
        st.markdown("**Quote Follow-up**")
        show_tasks("quote_follow_up")

    with cockpit_col2:
        st.markdown("**Lead Nurturing**")
        show_tasks("relationship_touch")

    with cockpit_col3:
        st.markdown("**New Lead Outreach**")
        show_tasks("new_lead_outreach")

    with cockpit_col4:
        st.markdown("**Prepare Quote**")
        show_tasks("prepare_quote")

    with cockpit_col5:
        st.markdown("**Chase Vendor**")
        show_tasks("chase_vendor")

    st.divider()

    st.subheader("Today's Actions")
    show_prepare_quote_actions()

    st.subheader("New Inquiry")

    inquiry_text = st.text_area(
        "Paste inquiry here",
        height=200,
    )

    if st.button("Save Inquiry"):
        if inquiry_text.strip():
            create_inquiry(inquiry_text)
            st.success("Inquiry saved successfully.")
            st.rerun()
        else:
            st.warning("Paste an inquiry before saving.")


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
            "Organization Type [CHECK]",
            ORG_TYPE_OPTIONS,
            index=ORG_TYPE_OPTIONS.index("Overseas Agent"),
        )
        customer_status = st.selectbox(
            "Customer Status [CHECK]",
            CUSTOMER_STATUS_OPTIONS,
            index=CUSTOMER_STATUS_OPTIONS.index("Customer"),
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
            "Relationship [CHECK]",
            RELATIONSHIP_STATUS_OPTIONS,
            index=RELATIONSHIP_STATUS_OPTIONS.index("Active"),
        )

    save_as = st.radio(
        "Save as",
        CAPTURE_SAVE_AS_OPTIONS,
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
        st.session_state.quick_capture_text = ""
        st.rerun()

    if cancel_clicked:
        st.info("Capture canceled.")
        return

    if save_clicked:
        result = save_captured_crm_record(record, save_as, duplicate_action)
        st.success(
            "Saved "
            f"{save_as.lower()} "
            f"(organization #{result['organization_id']}"
            + (f", contact #{result['contact_id']}" if result["contact_id"] else "")
            + (f", lead #{result['lead_id']}" if result["lead_id"] else "")
            + ")."
        )
        link_col1, link_col2, link_col3 = st.columns(3)
        with link_col1:
            if st.button("View Lead", disabled=not result["lead_id"]):
                st.session_state.selected_lead_id = result["lead_id"]
                st.session_state.page = "Leads List"
                st.rerun()
        with link_col2:
            st.button("View Organization", disabled=not result["organization_id"])
        with link_col3:
            if st.button("Add Another"):
                st.session_state.quick_capture_text = ""
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
            st.session_state.page = "Leads List"
            st.rerun()
        return

    lead = detail["lead"]
    organization = detail["organization"]
    contact = detail["contact"]
    edit_key = f"lead_detail_edit_{lead_id}"

    contact_name = detail_value(contact, "name") or detail_value(lead, "contact_person") or "No contact linked"
    organization_name = detail_value(organization, "name") or detail_value(lead, "company_name") or "No organization linked"
    lead_status = detail_value(lead, "lead_status", "New")
    customer_status = detail_value(organization, "customer_status", "")
    relationship_status = detail_value(contact, "relationship_status", "")

    if st.button("Back to Leads List"):
        st.session_state.selected_lead_id = None
        st.session_state.page = "Leads List"
        st.rerun()

    st.title(contact_name)
    st.caption(organization_name)
    header_cols = st.columns(3)
    header_cols[0].metric("Lead Status", lead_status)
    header_cols[1].metric("Customer Status", customer_status or "No organization linked")
    header_cols[2].metric("Relationship", relationship_status or "No contact linked")

    comm_cols = st.columns(4)
    email = detail_value(contact, "email") or detail_value(lead, "email")
    phone = detail_value(contact, "phone") or detail_value(lead, "phone")
    whatsapp = detail_value(contact, "whatsapp") or detail_value(lead, "whatsapp")
    wechat = detail_value(contact, "wechat") or detail_value(lead, "wechat")

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
        if whatsapp:
            whatsapp_number = re.sub(r"[^0-9]", "", whatsapp)
            if whatsapp_number:
                st.link_button("WhatsApp", f"https://wa.me/{whatsapp_number}")
            else:
                st.button("WhatsApp", disabled=True)
        else:
            st.button("WhatsApp", disabled=True)
    with comm_cols[3]:
        if wechat:
            st.text_input("WeChat ID", value=wechat, disabled=True)
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

    st.divider()
    action_cols = st.columns(5)
    for col, action in zip(
        action_cols,
        ["Contacted", "Replied", "Qualified", "Disqualified", "Converted"],
    ):
        if col.button(f"Mark {action}", key=f"lead_action_{action}_{lead_id}"):
            update_lead_status_action(lead_id, action)
            st.rerun()

    relationship_cols = st.columns(5)
    for col, status in zip(
        relationship_cols,
        ["Connected", "Introduced", "Warm", "Active", "Inactive"],
    ):
        disabled = not contact
        if col.button(f"Mark {status}", key=f"contact_action_{status}_{lead_id}", disabled=disabled):
            update_contact_relationship_action(contact["id"], status)
            st.rerun()

    customer_cols = st.columns(4)
    for col, status in zip(customer_cols, ["Prospect", "Qualified", "Customer", "Inactive"]):
        disabled = not organization
        if col.button(f"Mark {status}", key=f"org_action_{status}_{lead_id}", disabled=disabled):
            update_organization_customer_action(organization["id"], status)
            st.rerun()

    st.divider()
    st.subheader("Next Follow-up")
    follow_col1, follow_col2, follow_col3 = st.columns([2, 1, 1])
    next_action = follow_col1.text_input(
        "Next Action",
        value=detail_value(lead, "next_action"),
        key=f"next_action_{lead_id}",
    )
    next_action_date = follow_col2.text_input(
        "Next Action Date",
        value=detail_value(lead, "next_action_date"),
        key=f"next_action_date_{lead_id}",
    )
    if follow_col3.button("Save Next Follow-up", key=f"save_follow_{lead_id}"):
        update_lead_next_follow_up(lead_id, next_action, next_action_date)
        st.success("Next follow-up saved.")
        st.rerun()

    st.divider()
    edit_col1, edit_col2, edit_col3 = st.columns(3)
    if edit_col1.button("Edit", disabled=st.session_state.get(edit_key, False)):
        st.session_state[edit_key] = True
        st.rerun()
    editing = st.session_state.get(edit_key, False)

    org_data = {}
    contact_data = {}
    lead_data = {}

    org_col, contact_col, lead_col = st.columns(3)

    with org_col:
        st.subheader("Organization")
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
        org_data["membership"] = st.text_input("Membership", value=detail_value(organization, "membership"), disabled=not editing or not organization)
        org_data["customer_status"] = st.selectbox(
            "Customer Status",
            CUSTOMER_STATUS_OPTIONS,
            index=CUSTOMER_STATUS_OPTIONS.index(detail_value(organization, "customer_status", "Prospect")) if detail_value(organization, "customer_status", "Prospect") in CUSTOMER_STATUS_OPTIONS else 0,
            disabled=not editing or not organization,
        )
        org_data["notes"] = st.text_area("Organization Notes", value=detail_value(organization, "notes"), disabled=not editing or not organization)

    with contact_col:
        st.subheader("Contact")
        if not contact:
            st.info("No contact linked.")
        contact_data["name"] = st.text_input("Contact Name", value=detail_value(contact, "name"), disabled=not editing or not contact)
        contact_data["job_title"] = st.text_input("Job Title", value=detail_value(contact, "job_title"), disabled=not editing or not contact)
        contact_data["email"] = st.text_input("Email", value=detail_value(contact, "email"), disabled=not editing or not contact)
        contact_data["phone"] = st.text_input("Phone", value=detail_value(contact, "phone"), disabled=not editing or not contact)
        contact_data["wechat"] = st.text_input("WeChat", value=detail_value(contact, "wechat"), disabled=not editing or not contact)
        contact_data["whatsapp"] = st.text_input("Whatsapp", value=detail_value(contact, "whatsapp"), disabled=not editing or not contact)
        contact_data["relationship_status"] = st.selectbox(
            "Relationship Status",
            RELATIONSHIP_STATUS_OPTIONS,
            index=RELATIONSHIP_STATUS_OPTIONS.index(detail_value(contact, "relationship_status", "New")) if detail_value(contact, "relationship_status", "New") in RELATIONSHIP_STATUS_OPTIONS else 0,
            disabled=not editing or not contact,
        )
        contact_data["last_contacted_at"] = st.text_input("Last Contacted At", value=detail_value(contact, "last_contacted_at"), disabled=not editing or not contact)
        contact_data["next_follow_up_at"] = st.text_input("Next Follow-up At", value=detail_value(contact, "next_follow_up_at"), disabled=not editing or not contact)
        contact_data["notes"] = st.text_area("Contact Notes", value=detail_value(contact, "notes"), disabled=not editing or not contact)

    with lead_col:
        st.subheader("Lead")
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
        if edit_col2.button("Save"):
            update_lead_detail(
                lead_id,
                org_data if organization else {},
                contact_data if contact else {},
                lead_data,
            )
            st.session_state[edit_key] = False
            st.success("Lead detail saved.")
            st.rerun()
        if edit_col3.button("Cancel"):
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
        ["Dashboard", "Quick Capture", "Leads Import", "Leads List"],
        key="page",
    )

apply_global_typography(st.session_state.ui_scale)

if page == "Dashboard":
    show_dashboard()
elif page == "Quick Capture":
    show_quick_capture()
elif page == "Leads Import":
    show_leads_import()
else:
    show_leads_list()
