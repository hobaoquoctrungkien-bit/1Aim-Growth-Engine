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

    cur.execute(
        """
        INSERT OR IGNORE INTO compliance_product_groups (
            name,
            code,
            description,
            managing_authority,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, 'Active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            "San pham mat ma dan su",
            "SP_MMDS",
            "Civil cryptography products such as firewall, VPN appliance, encryption gateway, crypto module, HSM, security appliance, and routers with encryption functionality.",
            "Ban Co yeu Chinh phu",
        ),
    )
    sp_mmds = cur.execute("SELECT id FROM compliance_product_groups WHERE code = 'SP_MMDS'").fetchone()
    sp_mmds_id = sp_mmds[0] if sp_mmds else None
    sp_mmds_keywords = [
        ("mat ma dan su", "Vietnamese"),
        ("san pham mat ma dan su", "Vietnamese"),
        ("thiet bi mat ma", "Vietnamese"),
        ("thiet bi ma hoa", "Vietnamese"),
        ("encryption", "English"),
        ("cryptography", "English"),
        ("VPN", "Product"),
        ("firewall", "Product"),
        ("router", "Product"),
        ("crypto module", "Product"),
        ("IPSec", "Technical"),
        ("SSL VPN", "Technical"),
        ("HSM", "Product"),
        ("security appliance", "Product"),
    ]
    if sp_mmds_id:
        for keyword, keyword_type in sp_mmds_keywords:
            cur.execute(
                """
                INSERT OR IGNORE INTO compliance_keywords (
                    product_group_id,
                    keyword,
                    keyword_type,
                    created_at
                )
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (sp_mmds_id, keyword, keyword_type),
            )

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

