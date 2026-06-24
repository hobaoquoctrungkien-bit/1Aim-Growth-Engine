import importlib
import json

import pandas as pd
import streamlit as st
import knowledge_service as knowledge_service_module

from document_parser_service import extract_text as extract_document_text, parse_document
from knowledge_service import (
    INTELLIGENCE_TYPES,
    generate_answer,
    generate_compliance_answer,
    get_compliance_product_group,
    get_compliance_keywords,
    save_case,
    save_compliance_note,
    save_compliance_rule,
    save_document,
    save_intelligence,
    save_sop,
    save_uploaded_knowledge_file,
    search_compliance_notes,
    search_compliance_rules,
    search_cases,
    search_documents,
    search_intelligence,
    search_product_group_documents,
    search_sops,
    update_compliance_rule_status,
)


def show_legal_library():
    st.title("Legal Library")
    st.caption("Store laws, decrees, circulars, official letters, and compliance references for logistics operations.")

    with st.expander("Add Legal Document", expanded=False):
        st.subheader("Step 1: Upload file")
        uploaded_file = st.file_uploader("Upload PDF, DOCX, or TXT", type=["pdf", "docx", "txt"], key="kb_legal_upload")

        parse_cols = st.columns([1, 1, 1, 3])
        if parse_cols[0].button("Extract Text", key="kb_extract_text", disabled=not uploaded_file):
            try:
                uploaded_text = extract_document_text(uploaded_file)
                st.session_state.kb_doc_extracted_text = uploaded_text
                st.session_state.kb_doc_extract_error = ""
                st.success("Text extracted. Review or run AI Parse.")
            except Exception as exc:
                st.session_state.kb_doc_extract_error = str(exc)
                st.error(f"Text extraction failed: {exc}")
            st.rerun()

        extracted_text = st.session_state.get("kb_doc_extracted_text", "")
        if parse_cols[1].button("Parse Metadata", key="kb_ai_parse_doc", disabled=not extracted_text.strip()):
            try:
                parsed = parse_document(extracted_text, uploaded_file.name if uploaded_file else "")
                st.session_state.kb_doc_parsed = parsed
                st.session_state.kb_doc_chunks = parsed.get("key_clauses", [])
                parsed_fields = parsed.get("parsed_fields", {})
                st.session_state.kb_doc_title = parsed_fields.get("title", {}).get("value", "")
                st.session_state.kb_doc_no = parsed_fields.get("document_no", {}).get("value", "")
                st.session_state.kb_doc_type = parsed_fields.get("document_type", {}).get("value", "") or "OTHER"
                st.session_state.kb_doc_authority = parsed_fields.get("issuing_authority", {}).get("value", "")
                st.session_state.kb_doc_issue = parsed_fields.get("issue_date", {}).get("value", "")
                st.session_state.kb_doc_effective = parsed_fields.get("effective_date", {}).get("value", "")
                st.session_state.kb_doc_expiry = parsed_fields.get("expiry_date", {}).get("value", "")
                st.session_state.kb_doc_status = parsed_fields.get("status", {}).get("value", "") or "Active"
                st.session_state.kb_doc_category = parsed_fields.get("category", {}).get("value", "")
                st.session_state.kb_doc_product_group = parsed_fields.get("related_product_group", {}).get("value", "")
                st.session_state.kb_doc_source = parsed.get("source_url", "")
                st.session_state.kb_doc_tags = parsed_fields.get("tags", {}).get("value", "")
                st.session_state.kb_doc_summary = parsed_fields.get("summary", {}).get("value", "")
                st.session_state.kb_doc_chunk = parsed.get("raw_text", "")
                first_clause = (parsed.get("key_clauses") or [{}])[0]
                st.session_state.kb_doc_article = first_clause.get("article_no", "")
                st.session_state.kb_doc_clause = first_clause.get("clause_no", "")
                st.session_state.kb_doc_keywords = ", ".join(parsed.get("keywords", []))
                st.session_state.kb_doc_extract_error = ""
                st.success("Parsed metadata is ready for admin review.")
            except Exception as exc:
                st.session_state.kb_doc_extract_error = str(exc)
                st.error(f"AI parsing failed: {exc}")
            st.rerun()

        if parse_cols[2].button("Clear Draft", key="kb_clear_doc_draft"):
            for key in list(st.session_state.keys()):
                if key.startswith("kb_doc_"):
                    del st.session_state[key]
            st.rerun()

        if st.session_state.get("kb_doc_extract_error"):
            st.warning(st.session_state.kb_doc_extract_error)

        if extracted_text:
            with st.expander("Extracted Text Preview", expanded=False):
                st.text_area("Extracted Text", value=extracted_text, height=220, key="kb_extracted_text_preview")

        parsed_doc = st.session_state.get("kb_doc_parsed") or {}
        if parsed_doc:
            parse_status_cols = st.columns(3)
            parse_status_cols[0].metric("Parser", parsed_doc.get("parser_engine") or "-")
            parse_status_cols[1].metric("Confidence", parsed_doc.get("confidence_score") or "Low")
            parse_status_cols[2].caption(parsed_doc.get("parser_error") or "")

        st.subheader("Step 2: Parsed Metadata Review")
        st.caption("Parser prefers blank over wrong. Review evidence, correct fields, then save as verified.")
        parsed_fields = parsed_doc.get("parsed_fields") or {}
        if parsed_fields:
            metadata_rows = [
                {
                    "Field": field,
                    "Parsed Value": meta.get("value") if isinstance(meta, dict) else "",
                    "Confidence": meta.get("confidence") if isinstance(meta, dict) else "low",
                    "Evidence": meta.get("evidence_text") if isinstance(meta, dict) else "",
                    "Needs Review": meta.get("needs_review") if isinstance(meta, dict) else True,
                }
                for field, meta in parsed_fields.items()
            ]
            st.dataframe(pd.DataFrame(metadata_rows), use_container_width=True, hide_index=True)
        form_cols = st.columns(3)
        title = form_cols[0].text_input("Title", key="kb_doc_title")
        document_no = form_cols[1].text_input("Document No.", key="kb_doc_no")
        document_type_options = ["Luật", "Nghị định", "Thông tư", "Quyết định", "Công văn", "Official Letter", "Law", "Decree", "Circular", "Other"]
        document_type_options = list(dict.fromkeys(
            [
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
            + document_type_options
        ))
        if st.session_state.get("kb_doc_type") not in document_type_options:
            st.session_state.kb_doc_type = "Other"
        document_type = form_cols[2].selectbox(
            "Document Type",
            document_type_options,
            key="kb_doc_type",
        )
        meta_cols = st.columns(4)
        authority = meta_cols[0].text_input("Issuing Authority", key="kb_doc_authority")
        issue_date = meta_cols[1].text_input("Issue Date", placeholder="YYYY-MM-DD", key="kb_doc_issue")
        effective_date = meta_cols[2].text_input("Effective Date", placeholder="YYYY-MM-DD", key="kb_doc_effective")
        expiry_date = meta_cols[3].text_input("Expiry Date", placeholder="YYYY-MM-DD", key="kb_doc_expiry")
        meta_cols2 = st.columns(3)
        status = meta_cols2[0].selectbox("Status", ["Active", "Draft", "Expired", "Replaced", "Unknown"], key="kb_doc_status")
        category = meta_cols2[1].text_input("Category", placeholder="Import Compliance", key="kb_doc_category")
        source_url = meta_cols2[2].text_input("Source URL", key="kb_doc_source")
        compliance_cols = st.columns(2)
        related_product_group = compliance_cols[0].text_input("Related Product Group", placeholder="SP_MMDS", key="kb_doc_product_group")
        approval_status = compliance_cols[1].selectbox("Approval Status", ["Approved", "Pending", "Rejected"], key="kb_doc_approval_status")
        tags = st.text_input("Tags", placeholder="customs, civil cryptography, DDP", key="kb_doc_tags")
        summary = st.text_area("Summary", height=120, key="kb_doc_summary")
        fallback_chunk_content = st.text_area(
            "Content / Source Text",
            height=220,
            key="kb_doc_chunk",
            help="Used as source text when no clauses were extracted.",
        )
        chunk_cols = st.columns(3)
        article_no = chunk_cols[0].text_input("Article No.", key="kb_doc_article")
        clause_no = chunk_cols[1].text_input("Clause No.", key="kb_doc_clause")
        keywords = chunk_cols[2].text_input("Keywords", key="kb_doc_keywords")

        st.subheader("Step 3: Source Clauses")
        parsed_chunks = st.session_state.get("kb_doc_chunks", [])
        if parsed_chunks:
            st.caption("These clauses are stored as source references only. Admin approval happens at Compliance Rule level.")
            for index, chunk in enumerate(parsed_chunks):
                with st.container(border=True):
                    st.write(f"Article: {chunk.get('article_no') or '-'} | Clause: {chunk.get('clause_no') or '-'}")
                    st.write(chunk.get("heading") or "")
                    st.caption(chunk.get("keywords") or "")
                    st.write((chunk.get("content") or "")[:900])
        else:
            st.info("No extracted clauses yet. Upload a file and click AI Parse, or use manual source text above.")

        st.subheader("Step 4: Save Verified Document")
        if st.button("Save as Verified Document", type="primary", key="kb_save_doc", disabled=not title.strip()):
            file_path = save_uploaded_knowledge_file(uploaded_file)
            chunks_to_save = [
                {
                    "article_no": chunk.get("article_no", ""),
                    "clause_no": chunk.get("clause_no", ""),
                    "heading": chunk.get("heading", title),
                    "content": chunk.get("content", ""),
                    "keywords": chunk.get("keywords", ""),
                    "status": "Approved",
                }
                for chunk in parsed_chunks
                if (chunk.get("content") or "").strip()
            ]
            if not chunks_to_save and fallback_chunk_content.strip():
                chunks_to_save = [
                    {
                        "article_no": article_no,
                        "clause_no": clause_no,
                        "heading": title,
                        "content": fallback_chunk_content,
                        "keywords": keywords,
                        "status": "Approved",
                    }
                ]
            document_id = save_document(
                {
                    "title": title,
                    "document_no": document_no,
                    "document_type": document_type,
                    "issuing_authority": authority,
                    "issue_date": issue_date,
                    "effective_date": effective_date,
                    "expiry_date": expiry_date,
                    "status": status,
                    "category": category,
                    "source_url": source_url,
                    "file_path": file_path,
                    "summary": summary,
                    "related_product_group": related_product_group,
                    "approval_status": "Approved",
                    "extracted_text": extracted_text or fallback_chunk_content,
                    "parser_raw_json": json.dumps(parsed_doc, ensure_ascii=False),
                    "parser_provider": parsed_doc.get("parser_engine", ""),
                    "parser_confidence": parsed_doc.get("confidence_score", ""),
                    "parser_warnings": parsed_doc.get("parser_error", ""),
                    "metadata_review_status": "admin_verified",
                },
                chunks=chunks_to_save,
                tag_names=[item.strip() for item in tags.split(",") if item.strip()],
            )
            st.success(f"Verified legal document saved: #{document_id}")
            st.rerun()

    search_cols = st.columns(4)
    keyword = search_cols[0].text_input("Keyword", key="kb_doc_search")
    document_no = search_cols[1].text_input("Document No.", key="kb_doc_no_search")
    authority = search_cols[2].text_input("Authority", key="kb_doc_authority_search")
    category = search_cols[3].text_input("Category", key="kb_doc_category_search")
    documents = search_documents(keyword, document_no, authority, category)
    st.caption(f"Showing {len(documents)} legal documents")
    if documents:
        st.dataframe(
            pd.DataFrame(documents)[["title", "document_no", "issuing_authority", "effective_date", "status", "category"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No legal documents found.")


def show_sop_library():
    st.title("SOP Library")
    st.caption("Store internal procedures for import/export, customs clearance, quotation, and operations.")

    with st.expander("Add SOP", expanded=False):
        title = st.text_input("Title", placeholder="Import Cisco Router", key="kb_sop_title")
        purpose = st.text_area("Purpose", height=90, key="kb_sop_purpose")
        procedure_steps = st.text_area("Procedure Steps", height=180, key="kb_sop_steps")
        checklist = st.text_area("Checklist", height=150, key="kb_sop_checklist")
        rel_cols = st.columns(3)
        related_documents = rel_cols[0].text_input("Related Documents", key="kb_sop_docs")
        related_cases = rel_cols[1].text_input("Related Cases", key="kb_sop_cases")
        category = rel_cols[2].text_input("Category", key="kb_sop_category")
        status = st.selectbox("Status", ["Active", "Draft", "Paused"], key="kb_sop_status")
        if st.button("Save SOP", type="primary", key="kb_save_sop", disabled=not title.strip()):
            sop_id = save_sop(
                {
                    "title": title,
                    "purpose": purpose,
                    "procedure_steps": procedure_steps,
                    "checklist": checklist,
                    "related_documents": related_documents,
                    "related_cases": related_cases,
                    "category": category,
                    "status": status,
                    "created_by": "admin",
                }
            )
            st.success(f"SOP saved: #{sop_id}")
            st.rerun()

    search_cols = st.columns(3)
    keyword = search_cols[0].text_input("Search SOPs", key="kb_sop_search")
    category = search_cols[1].text_input("Category", key="kb_sop_category_search")
    status = search_cols[2].selectbox("Status", ["", "Active", "Draft", "Paused"], key="kb_sop_status_search")
    sops = search_sops(keyword, category, status)
    st.caption(f"Showing {len(sops)} SOPs")
    for sop in sops:
        with st.expander(sop["title"]):
            st.write(sop.get("purpose") or "")
            st.markdown("**Procedure Steps**")
            st.write(sop.get("procedure_steps") or "-")
            st.markdown("**Checklist**")
            st.write(sop.get("checklist") or "-")
            st.caption(f"Category: {sop.get('category') or '-'} | Status: {sop.get('status') or '-'}")


def show_case_library():
    st.title("Case Library")
    st.caption("Store real operational experience, customer-specific know-how, and approved lessons learned.")

    with st.expander("Add Case", expanded=False):
        title = st.text_input("Title", key="kb_case_title")
        meta_cols = st.columns(5)
        customer = meta_cols[0].text_input("Customer", key="kb_case_customer")
        commodity = meta_cols[1].text_input("Commodity", key="kb_case_commodity")
        hs_code = meta_cols[2].text_input("HS Code", key="kb_case_hs")
        country = meta_cols[3].text_input("Country", key="kb_case_country")
        attachments = meta_cols[4].text_input("Attachments", key="kb_case_attachments")
        problem = st.text_area("Problem / Question", height=130, key="kb_case_problem")
        solution = st.text_area("Solution / Conclusion", height=130, key="kb_case_solution")
        legal_basis = st.text_area("Legal Basis", height=120, key="kb_case_legal")
        risk_notes = st.text_area("Risk Notes / Lessons Learned", height=120, key="kb_case_risk")
        if st.button("Save Case", type="primary", key="kb_save_case", disabled=not title.strip()):
            case_id = save_case(
                {
                    "title": title,
                    "customer": customer,
                    "commodity": commodity,
                    "hs_code": hs_code,
                    "country": country,
                    "problem": problem,
                    "solution": solution,
                    "legal_basis": legal_basis,
                    "risk_notes": risk_notes,
                    "attachments": attachments,
                    "created_by": "admin",
                }
            )
            st.success(f"Case saved: #{case_id}")
            st.rerun()

    search_cols = st.columns(5)
    keyword = search_cols[0].text_input("Search Cases", key="kb_case_search")
    customer = search_cols[1].text_input("Customer", key="kb_case_customer_search")
    commodity = search_cols[2].text_input("Commodity", key="kb_case_commodity_search")
    hs_code = search_cols[3].text_input("HS Code", key="kb_case_hs_search")
    country = search_cols[4].text_input("Country", key="kb_case_country_search")
    cases = search_cases(keyword, customer, commodity, hs_code, country)
    st.caption(f"Showing {len(cases)} cases")
    for case in cases:
        with st.expander(case["title"]):
            st.write(f"Customer: {case.get('customer') or '-'} | Commodity: {case.get('commodity') or '-'} | HS: {case.get('hs_code') or '-'} | Country: {case.get('country') or '-'}")
            st.markdown("**Problem**")
            st.write(case.get("problem") or "-")
            st.markdown("**Solution**")
            st.write(case.get("solution") or "-")
            st.markdown("**Legal Basis**")
            st.write(case.get("legal_basis") or "-")
            st.markdown("**Risk Notes**")
            st.write(case.get("risk_notes") or "-")


def show_intelligence_library():
    st.title("Intelligence Library")
    st.caption("Store reusable business intelligence: lessons learned, market signals, vendor notes, customer know-how, and shipment history.")

    with st.expander("Add Intelligence", expanded=False):
        type_cols = st.columns([1.5, 2.5, 1, 1])
        intelligence_type = type_cols[0].selectbox("Type", INTELLIGENCE_TYPES, key="kb_intel_type")
        title = type_cols[1].text_input("Title", key="kb_intel_title")
        confidence = type_cols[2].selectbox("Confidence", ["High", "Medium", "Low"], index=1, key="kb_intel_confidence")
        status = type_cols[3].selectbox("Status", ["Active", "Draft", "Archived"], key="kb_intel_status")

        meta_cols = st.columns(5)
        entity_name = meta_cols[0].text_input("Entity", placeholder="Customer / vendor / market", key="kb_intel_entity")
        country = meta_cols[1].text_input("Country", key="kb_intel_country")
        lane = meta_cols[2].text_input("Lane", placeholder="China - Vietnam", key="kb_intel_lane")
        commodity = meta_cols[3].text_input("Commodity", key="kb_intel_commodity")
        hs_code = meta_cols[4].text_input("HS Code", key="kb_intel_hs")
        summary = st.text_area("Summary", height=100, key="kb_intel_summary")
        details = st.text_area("Details / Evidence / What to remember", height=180, key="kb_intel_details")
        source_cols = st.columns([2, 2])
        source = source_cols[0].text_input("Source", placeholder="Shipment, customer call, vendor quote, market note", key="kb_intel_source")
        tags = source_cols[1].text_input("Tags", placeholder="China, OLO, customs, DDP", key="kb_intel_tags")
        if st.button("Save Intelligence", type="primary", key="kb_save_intelligence", disabled=not title.strip()):
            intelligence_id = save_intelligence(
                {
                    "intelligence_type": intelligence_type,
                    "title": title,
                    "entity_name": entity_name,
                    "country": country,
                    "lane": lane,
                    "commodity": commodity,
                    "hs_code": hs_code,
                    "summary": summary,
                    "details": details,
                    "source": source,
                    "confidence": confidence,
                    "tags": tags,
                    "status": status,
                    "created_by": "admin",
                }
            )
            st.success(f"Intelligence saved: #{intelligence_id}")
            st.rerun()

    search_cols = st.columns(5)
    keyword = search_cols[0].text_input("Search Intelligence", key="kb_intel_search")
    intelligence_type = search_cols[1].selectbox("Type", [""] + INTELLIGENCE_TYPES, key="kb_intel_type_search")
    country = search_cols[2].text_input("Country", key="kb_intel_country_search")
    entity_name = search_cols[3].text_input("Entity", key="kb_intel_entity_search")
    tags = search_cols[4].text_input("Tags", key="kb_intel_tags_search")
    rows = search_intelligence(keyword, intelligence_type, country, entity_name, tags)
    st.caption(f"Showing {len(rows)} intelligence records")
    if not rows:
        st.info("No intelligence records found.")
        return

    for item in rows:
        title = f"{item.get('intelligence_type') or 'Intelligence'} - {item.get('title') or 'Untitled'}"
        with st.expander(title):
            meta_cols = st.columns(5)
            meta_cols[0].write(item.get("entity_name") or "-")
            meta_cols[1].write(item.get("country") or "-")
            meta_cols[2].write(item.get("lane") or "-")
            meta_cols[3].write(item.get("commodity") or "-")
            meta_cols[4].write(item.get("confidence") or "-")
            st.markdown("**Summary**")
            st.write(item.get("summary") or "-")
            st.markdown("**Details**")
            st.write(item.get("details") or "-")
            source_label = item.get("source") or "-"
            if item.get("source_type") and item.get("source_id"):
                source_label = f"{source_label} ({item.get('source_type')} #{item.get('source_id')})"
            st.caption(f"Source: {source_label} | Tags: {item.get('tags') or '-'}")


def show_compliance_engine():
    compliance_service = importlib.reload(knowledge_service_module)
    st.title("Compliance Engine")
    st.caption("Operational compliance answers from approved legal sources and approved company knowledge.")
    product_group = compliance_service.get_compliance_product_group("SP_MMDS") or {}
    st.subheader("SP_MMDS")
    st.caption(product_group.get("description") or "Civil cryptography product group.")
    summary_cols = st.columns(3)
    summary_cols[0].metric("Product Group", product_group.get("code") or "SP_MMDS")
    summary_cols[1].metric("Authority", product_group.get("managing_authority") or "-")
    summary_cols[2].metric("Status", product_group.get("status") or "-")

    sections = st.tabs(["Legal Documents", "Compliance Rules", "Compliance Notes", "SOPs", "Cases", "Ask Compliance Question"])

    with sections[0]:
        keyword = st.text_input("Search SP_MMDS legal documents", key="compliance_doc_search")
        documents = compliance_service.search_product_group_documents("SP_MMDS", keyword)
        st.caption(f"Showing {len(documents)} approved legal documents linked to SP_MMDS")
        if documents:
            st.dataframe(
                pd.DataFrame(documents)[["title", "document_no", "issuing_authority", "effective_date", "approval_status"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No approved legal documents linked to SP_MMDS yet. Add Related Product Group = SP_MMDS in Legal Library.")

    with sections[1]:
        st.subheader("Review Compliance Rules")
        st.caption("Approve, reject, or edit generated compliance rules. Legal chunks are source references only.")
        with st.expander("Add Compliance Rule", expanded=False):
            document_options = compliance_service.search_product_group_documents("SP_MMDS", "")
            doc_labels = ["No linked legal document"] + [
                f"{doc.get('document_no') or 'No No.'} - {doc.get('title')}" for doc in document_options
            ]
            selected_doc = st.selectbox("Legal Document", doc_labels, key="compliance_rule_doc")
            selected_doc_id = None
            if selected_doc != doc_labels[0]:
                selected_doc_id = document_options[doc_labels.index(selected_doc) - 1]["id"]
            rule_cols = st.columns(3)
            rule_title = rule_cols[0].text_input("Rule Title", key="compliance_rule_title")
            rule_type = rule_cols[1].text_input("Rule Type", placeholder="Import requirement", key="compliance_rule_type")
            rule_approval = rule_cols[2].selectbox("Approval Status", ["pending_review", "Approved", "Rejected"], key="compliance_rule_approval")
            ref_cols = st.columns(4)
            article_no = ref_cols[0].text_input("Article No.", key="compliance_rule_article")
            clause_no = ref_cols[1].text_input("Clause No.", key="compliance_rule_clause")
            appendix_no = ref_cols[2].text_input("Appendix No.", key="compliance_rule_appendix")
            table_no = ref_cols[3].text_input("Table No.", key="compliance_rule_table")
            rule_content = st.text_area("Rule Content", height=140, key="compliance_rule_content")
            required_documents = st.text_area("Required Documents", height=100, key="compliance_rule_required_docs")
            rule_meta_cols = st.columns(2)
            rule_authority = rule_meta_cols[0].text_input("Managing Authority", value=product_group.get("managing_authority") or "", key="compliance_rule_authority")
            effective_date = rule_meta_cols[1].text_input("Effective Date", placeholder="YYYY-MM-DD", key="compliance_rule_effective")
            if st.button("Save Compliance Rule", type="primary", key="compliance_save_rule", disabled=not rule_title.strip()):
                compliance_service.save_compliance_rule(
                    {
                        "product_group_id": product_group.get("id"),
                        "rule_title": rule_title,
                        "rule_type": rule_type,
                        "legal_document_id": selected_doc_id,
                        "article_no": article_no,
                        "clause_no": clause_no,
                        "appendix_no": appendix_no,
                        "table_no": table_no,
                        "content": rule_content,
                        "required_documents": required_documents,
                        "managing_authority": rule_authority,
                        "effective_date": effective_date,
                        "approval_status": rule_approval,
                    }
                )
                st.success("Compliance rule saved.")
                st.rerun()

        rule_keyword = st.text_input("Search Compliance Rules", key="compliance_rule_search")
        rules = compliance_service.search_compliance_rules("SP_MMDS", rule_keyword, approved_only=False)
        st.caption(f"Showing {len(rules)} compliance rules")
        for rule in rules:
            with st.expander(f"{rule.get('rule_title')} ({rule.get('approval_status') or 'pending_review'})"):
                edit_cols = st.columns([2, 1, 1, 1])
                edited_title = edit_cols[0].text_input("Rule Title", value=rule.get("rule_title") or "", key=f"rule_title_{rule['id']}")
                edited_type = edit_cols[1].text_input("Rule Type", value=rule.get("rule_type") or "", key=f"rule_type_{rule['id']}")
                edited_confidence = edit_cols[2].text_input("Confidence", value=rule.get("confidence_score") or "", key=f"rule_conf_{rule['id']}")
                status_options = ["pending_review", "Approved", "Rejected"]
                edited_status = edit_cols[3].selectbox(
                    "Status",
                    status_options,
                    index=status_options.index(rule.get("approval_status") or "pending_review")
                    if (rule.get("approval_status") or "pending_review") in status_options
                    else 0,
                    key=f"rule_status_{rule['id']}",
                )
                edited_content = st.text_area("Extracted Content", value=rule.get("content") or "", height=120, key=f"rule_content_{rule['id']}")
                edited_required = st.text_area("Required Documents", value=rule.get("required_documents") or "", height=90, key=f"rule_required_{rule['id']}")
                st.caption(
                    f"Document: {rule.get('legal_document_no') or '-'} | Article: {rule.get('article_no') or '-'} | Clause: {rule.get('clause_no') or '-'}"
                )
                action_cols = st.columns([1, 1, 1, 4])
                if action_cols[0].button("Approve", key=f"approve_rule_{rule['id']}"):
                    compliance_service.update_compliance_rule_status(rule["id"], "Approved")
                    st.success("Rule approved.")
                    st.rerun()
                if action_cols[1].button("Reject", key=f"reject_rule_{rule['id']}"):
                    compliance_service.update_compliance_rule_status(rule["id"], "Rejected")
                    st.success("Rule rejected.")
                    st.rerun()
                if action_cols[2].button("Save Edit", key=f"save_rule_edit_{rule['id']}"):
                    compliance_service.save_compliance_rule(
                        {
                            **rule,
                            "rule_title": edited_title,
                            "rule_type": edited_type,
                            "content": edited_content,
                            "required_documents": edited_required,
                            "confidence_score": edited_confidence,
                            "approval_status": edited_status,
                            "product_group_id": product_group.get("id"),
                        },
                        rule_id=rule["id"],
                    )
                    st.success("Rule updated.")
                    st.rerun()
                if rule.get("source_content"):
                    with st.expander("View Original Source", expanded=False):
                        st.write(rule.get("source_heading") or "")
                        st.write(rule.get("source_content") or "")

    with sections[2]:
        with st.expander("Add Compliance Note", expanded=False):
            note_cols = st.columns(3)
            note_title = note_cols[0].text_input("Title", key="compliance_note_title")
            note_topic = note_cols[1].text_input("Topic", key="compliance_note_topic")
            note_approval = note_cols[2].selectbox("Approval Status", ["Pending", "Approved", "Rejected"], key="compliance_note_approval")
            note_summary = st.text_area("Summary", height=90, key="compliance_note_summary")
            note_interpretation = st.text_area("Interpretation", height=120, key="compliance_note_interpretation")
            note_guidance = st.text_area("Operational Guidance", height=120, key="compliance_note_guidance")
            note_risk = st.text_area("Risk Notes", height=100, key="compliance_note_risk")
            rel_cols = st.columns(3)
            related_documents = rel_cols[0].text_input("Related Documents", key="compliance_note_docs")
            related_sops = rel_cols[1].text_input("Related SOPs", key="compliance_note_sops")
            related_cases = rel_cols[2].text_input("Related Cases", key="compliance_note_cases")
            if st.button("Save Compliance Note", type="primary", key="compliance_save_note", disabled=not note_title.strip()):
                compliance_service.save_compliance_note(
                    {
                        "title": note_title,
                        "topic": note_topic,
                        "product_group_id": product_group.get("id"),
                        "summary": note_summary,
                        "interpretation": note_interpretation,
                        "operational_guidance": note_guidance,
                        "risk_notes": note_risk,
                        "related_documents": related_documents,
                        "related_sops": related_sops,
                        "related_cases": related_cases,
                        "approval_status": note_approval,
                        "created_by": "admin",
                    }
                )
                st.success("Compliance note saved.")
                st.rerun()

        note_keyword = st.text_input("Search Compliance Notes", key="compliance_note_search")
        notes = compliance_service.search_compliance_notes("SP_MMDS", note_keyword, approved_only=False)
        st.caption(f"Showing {len(notes)} compliance notes")
        for note in notes:
            with st.expander(f"{note.get('title')} ({note.get('approval_status') or 'Pending'})"):
                st.markdown("**Summary**")
                st.write(note.get("summary") or "-")
                st.markdown("**Interpretation**")
                st.write(note.get("interpretation") or "-")
                st.markdown("**Operational Guidance**")
                st.write(note.get("operational_guidance") or "-")
                st.markdown("**Risk Notes**")
                st.write(note.get("risk_notes") or "-")

    with sections[3]:
        sops = search_sops("SP_MMDS", status="Active")
        if not sops:
            sops = search_sops("cryptography", status="Active")
        st.caption(f"Showing {len(sops)} related SOPs")
        for sop in sops:
            with st.expander(sop["title"]):
                st.write(sop.get("purpose") or "-")
                st.markdown("**Procedure Steps**")
                st.write(sop.get("procedure_steps") or "-")
                st.markdown("**Checklist**")
                st.write(sop.get("checklist") or "-")

    with sections[4]:
        cases = search_cases("cryptography")
        st.caption(f"Showing {len(cases)} related cases")
        for case in cases:
            with st.expander(case["title"]):
                st.markdown("**Problem**")
                st.write(case.get("problem") or "-")
                st.markdown("**Solution**")
                st.write(case.get("solution") or "-")
                st.markdown("**Legal Basis**")
                st.write(case.get("legal_basis") or "-")
                st.markdown("**Risk Notes**")
                st.write(case.get("risk_notes") or "-")

    with sections[5]:
        st.caption("Ask operational import/export compliance questions. The answer uses approved sources only.")
        examples = [
            "Cisco firewall import Vietnam",
            "Cisco ISR4331",
            "VPN appliance",
            "HSM device",
            "Does this device require import license?",
        ]
        example = st.selectbox("Example Questions", [""] + examples, key="compliance_question_example")
        question_default = example or st.session_state.get("compliance_question_text", "")
        question = st.text_area("Compliance Question", value=question_default, height=120, key="compliance_question_text")
        if st.button("Search Compliance Knowledge", type="primary", key="compliance_ask", disabled=not question.strip()):
            st.session_state.compliance_answer = compliance_service.generate_compliance_answer(question, "SP_MMDS")

        answer = st.session_state.get("compliance_answer")
        if answer:
            st.subheader("Conclusion")
            st.write(answer["conclusion"])
            st.subheader("Product Group")
            st.write(answer["product_group"])
            st.subheader("Managing Authority")
            st.write(answer["managing_authority"] or "-")
            st.subheader("Legal Basis")
            st.write(answer["legal_basis"] or "-")
            st.subheader("Document Number")
            st.write(answer["document_number"] or "-")
            st.subheader("Article / Clause")
            st.write(answer["article_clause"] or "-")
            st.subheader("Required Documents")
            st.write(answer["required_documents"] or "-")
            st.subheader("Required Actions")
            st.write(answer["required_actions"])
            st.subheader("Relevant Compliance Notes")
            if answer["relevant_compliance_notes"]:
                st.dataframe(pd.DataFrame(answer["relevant_compliance_notes"]), use_container_width=True, hide_index=True)
            else:
                st.write("None found.")
            st.subheader("Relevant SOPs")
            if answer["relevant_sops"]:
                st.dataframe(pd.DataFrame(answer["relevant_sops"])[["title", "purpose", "category", "status"]], use_container_width=True, hide_index=True)
            else:
                st.write("None found.")
            st.subheader("Relevant Cases")
            if answer["relevant_cases"]:
                st.dataframe(pd.DataFrame(answer["relevant_cases"])[["title", "customer", "commodity", "country", "solution"]], use_container_width=True, hide_index=True)
            else:
                st.write("None found.")
            st.subheader("Risk Notes")
            st.write(answer["risk_notes"])
            st.subheader("Uncertainty")
            st.write(answer["uncertainty"])
            st.subheader("Recommended Next Step")
            st.write(answer["recommended_next_step"])
            st.subheader("Sources Used")
            if answer["sources_used"]:
                for source in answer["sources_used"]:
                    with st.expander(f"{source.get('source_type')}: {source.get('title') or '-'}"):
                        st.write(f"Document Number: {source.get('document_no') or '-'}")
                        st.write(f"Article: {source.get('article_no') or '-'} | Clause: {source.get('clause_no') or '-'}")
                        if source.get("source_content"):
                            st.markdown("**Original Source**")
                            st.write(source.get("source_content"))
            else:
                st.write("None found.")
            st.subheader("Confidence Level")
            st.write(answer["confidence"])


def show_knowledge_ai_assistant():
    st.title("AI Assistant")
    st.caption("Evidence-only assistant. It answers from stored cases, SOPs, and legal documents. No external AI provider is used in V1.")
    question = st.text_area("Question", placeholder="Does Cisco firewall require cryptography permit?", height=120, key="kb_ai_question")
    if st.button("Search Knowledge Base", type="primary", key="kb_ai_search", disabled=not question.strip()):
        st.session_state.kb_ai_answer = generate_answer(question)

    answer = st.session_state.get("kb_ai_answer")
    if not answer:
        return
    st.subheader("Conclusion")
    st.write(answer["conclusion"])
    st.subheader("Legal Basis")
    st.write(answer["legal_basis"] or "No legal basis found in stored knowledge.")
    st.subheader("Relevant Documents")
    if answer["relevant_documents"]:
        st.dataframe(pd.DataFrame(answer["relevant_documents"]), use_container_width=True, hide_index=True)
    else:
        st.write("None found.")
    st.subheader("Applicable SOP")
    if answer["applicable_sops"]:
        st.dataframe(pd.DataFrame(answer["applicable_sops"])[["title", "purpose", "category", "status"]], use_container_width=True, hide_index=True)
    else:
        st.write("None found.")
    st.subheader("Related Cases")
    if answer["related_cases"]:
        st.dataframe(pd.DataFrame(answer["related_cases"])[["title", "customer", "commodity", "country", "solution"]], use_container_width=True, hide_index=True)
    else:
        st.write("None found.")
    st.subheader("Relevant Intelligence")
    if answer.get("intelligence"):
        st.dataframe(
            pd.DataFrame(answer["intelligence"])[["intelligence_type", "title", "entity_name", "country", "summary", "confidence"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("None found.")
    st.subheader("Risk Notes")
    st.write(answer["risk_notes"])
    st.subheader("Confidence Level")
    st.write(answer["confidence"])


def show_knowledge_base():
    st.title("Knowledge Base")
    st.caption("For logistics, customs clearance, import/export compliance, quotation preparation, and shipment operations.")
    section = st.session_state.get("knowledge_base_page", "Legal Library")
    if section == "Legal Library":
        show_legal_library()
    elif section == "SOP Library":
        show_sop_library()
    elif section == "Case Library":
        show_case_library()
    elif section == "Intelligence Library":
        show_intelligence_library()
    elif section == "Compliance Engine":
        show_compliance_engine()
    else:
        show_knowledge_ai_assistant()
