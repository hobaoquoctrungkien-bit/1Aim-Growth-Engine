# Decisions

Date: 2026-06-23

Decision:
Opportunity creation uses shared `create_opportunity(data)` logic for both parsed inquiry and manual entry workflows.

Reason:
Parsed inquiry and manual entry create the same business object. A single save path avoids diverging schemas, duplicated insert logic, and quotation-preparation field drift as the opportunity-to-quotation workflow grows.

Approved By:
Kien Ho

---

Date: 2026-06-23

Decision:
Regex parser is sufficient as fallback; future parser accuracy should come from pluggable AI providers.

Reason:
Adding hundreds of document-specific regex rules has low ROI and will remain less accurate than AI parsing for varied logistics, compliance, and commercial documents.

Approved By:
Kien Ho

---

Date: 2026-06-23

Decision:
Document parsing is a central platform service, not a Legal Library-only feature.

Reason:
The same document intelligence pipeline should later power Knowledge Base, inquiry parsing, quotation generation, compliance checks, SOP intake, and shipment intake. Centralizing it avoids duplicated parsers and keeps future AI provider integration clean.

Approved By:
Kien Ho

---

Date: 2026-06-23

Decision:
External AI providers are abstracted behind `parse_with_ai()` and not hardcoded in V1.

Reason:
1Aim needs the architecture for AI-assisted parsing now, while keeping the app usable without external API credentials. Regex/rule parsing remains a fallback when AI is unavailable.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Opportunity and Quotation can be saved as Knowledge Intelligence before a shipment/job module exists.

Reason:
Useful operational memory already appears during inquiry, pricing, quotation, won/lost, and follow-up work. Capturing this as intelligence now improves learning without pretending that full shipment/job records exist.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Knowledge intelligence V1 uses a single typed `knowledge_intelligence` table.

Reason:
Lessons learned, market intelligence, vendor intelligence, customer intelligence, and shipment history intelligence share the same early workflow: capture source, context, summary, details, confidence, tags, and make them searchable. A single typed table avoids premature fragmentation while preserving a path to split specialized tables later.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Outreach open and reply tracking are supporting signals, not automatic sales judgement.

Reason:
Open and reply signals help Kien prioritize follow-up, but relationship quality and opportunity qualification still require human judgement. Tracking should update activity/follow-up context without replacing sales decisions.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Quotation Engine uses the existing `quotations` table as the quote header, with `quotation_items` for customer-facing line items and `quotation_templates` for reusable quote text.

Reason:
Quotations belong after opportunities and pricing. Extending the existing quotation concept preserves quote history, avoids another revenue object, and keeps exported customer documents tied to the opportunity pipeline.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Quotation versioning keeps the same quote number and increments a version number.

Reason:
Customers often request revisions to the same quotation. Keeping one quote number with version history makes follow-up and audit easier than creating unrelated quote numbers for every revision.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Approved or sent quotations update the linked opportunity stage to `Quoted`.

Reason:
Quotation approval/sending is the business event that moves an opportunity from quote preparation into quoted pipeline status. This is a narrow CRM linkage and does not change unrelated relationship state.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Pricing Engine uses `vendor_rates` as the quote-preparation rate table linked to existing opportunities.

Reason:
Carrier, agent, and local charge pricing belongs between Opportunity and Quotation. Linking rate lines to opportunities avoids creating a duplicate revenue object while preserving a path to connect selected rates to quotations later.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Local charges are rolled into carrier and agent options during pricing comparison.

Reason:
Local charges are part of the real sell-rate total and should not appear as standalone winning options when comparing carrier or agent choices.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
`PRODUCT_CONSTITUTION.md` is the highest-priority product document for future 1Aim Growth Engine development.

Reason:
The product now spans CRM, outreach, opportunities, quotations, future shipments, backups, Git safety, and relationship intelligence. A single source of truth prevents feature drift and keeps development aligned with 1Aim's freight-forwarding relationship mission.

Approved By:
Kien Ho

---

Date: 2026-06-21

Decision:
Customer is a status of Organization.

Reason:
Avoid duplicate records and keep the CRM model simple for V1.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Git backup automation must only report success after push succeeds.

Reason:
The project should never claim backup completion when commit or remote push failed. This prevents false confidence after Windows `.git/index.lock` or permission errors.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Git health should be visible inside Admin.

Reason:
Kien needs to know whether CRM changes are safely committed and pushed without leaving the app.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Git backup must use an application-level lock and stale Git lock cleanup.

Reason:
Windows intermittently leaves `index.lock` or `packed-refs.lock` when multiple Git processes touch the repo. A higher-level lock prevents concurrent backup execution, while stale lock cleanup avoids unnecessary manual repair.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Git Health ignores transient lock files and must list remaining dirty files.

Reason:
Runtime lock files can make Admin show a false warning after a successful backup. When real uncommitted changes remain, Kien needs the exact file list instead of a vague "Uncommitted changes exist" message.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Git Health ignores runtime SQLite database files under `data/*.db`.

Reason:
The live SQLite database changes whenever the app records runtime state such as backup history. Database safety is handled by timestamped DB backups and restore testing, while Git Health should reflect source code, documentation, and configuration sync.

Approved By:
Kien Ho

---

Date: 2026-06-21

Decision:
Opportunity Pipeline extends the existing `opportunities` table instead of creating a duplicate revenue object.

Reason:
The app already had opportunities for inquiry and quote workflow. Extending the current table preserves history, avoids duplicate concepts, and moves the CRM from relationship tracking into revenue tracking without breaking existing quote logic.

Approved By:
Kien Ho

---

Date: 2026-06-21

Decision:
Opportunity stage uses the business pipeline values Interested, Quote Requested, Quoted, Negotiation, Won, and Lost.

Reason:
These stages are simple enough for a solo founder and directly connect relationship work to revenue pipeline.

Approved By:
Kien Ho

---

Date: 2026-06-21

Decision:
Relationship Health is calculated from existing CRM fields instead of stored as a new database field.

Reason:
Health is a derived operational indicator. Keeping it calculated avoids stale data and prevents another duplicate CRM concept.

Approved By:
Kien Ho

---

Date: 2026-06-21

Decision:
Missing Data Checklist is calculated from existing contact and organization fields instead of stored separately.

Reason:
The checklist is a live quality view, not independent data. Calculating it avoids stale cleanup tasks and keeps CRM data quality simple.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Outreach Campaign Engine sends only after manual review and approval.

Reason:
1Aim needs scale, but Kien must keep control of relationship quality and avoid accidental mass sending.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Outreach message generation is rule-based for V2.

Reason:
The current requirement is personalized campaign execution without adding AI dependency or unpredictable message generation.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Campaign Instructions tune the existing rule-based outreach generator instead of calling an external AI API.

Reason:
Kien needs fast campaign tuning, but the current CRM direction avoids AI automation for outreach sending. Rule-based tuning keeps messages predictable and avoids token waste.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Outreach campaigns require recipient selection and a final approval summary before sending.

Reason:
Bulk outreach should remain controlled. Include/exclude checkboxes and a final summary reduce accidental sends while preserving one-workflow execution.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Outreach campaign review uses rule-based quality checks instead of AI scoring.

Reason:
Kien needs fast safety signals for 30-50 messages, but V1 should remain predictable, local, and free from external AI dependency.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Preview emails do not update CRM lead, contact, campaign, or activity state.

Reason:
Preview sends are delivery tests for Kien, not real outreach. Real CRM state should only change after final campaign approval and successful recipient send.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Hard-bounced or manually invalid emails are excluded from future outreach campaigns by default.

Reason:
Repeated sends to invalid recipients damage deliverability and waste review time. Email hygiene should protect campaign execution automatically after bounce detection.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Bounce emails are recorded as processed but not deleted from the mailbox in V1.

Reason:
Keeping the original mailbox evidence is safer while the parser is new. The processed table prevents duplicate CRM updates without destructive email actions.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Invalid and bounced email cleanup belongs in Admin.

Reason:
Email hygiene is an operational maintenance task. Keeping it beside bounce processing lets Kien process bounces, fix typos, and restore valid contacts without mixing cleanup into daily sales screens.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Admin modules should be collapsed by default.

Reason:
Admin contains many maintenance tools. Collapsed sections keep the page calm and let Kien open only the module needed for the current task.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Lead-related workflows are grouped under a parent `Leads` menu.

Reason:
Outreach Campaigns, Quick Capture, Leads Import, and Leads List are all part of lead acquisition and lead management. Grouping them reduces sidebar clutter while preserving quick access through a focused Leads workspace.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Leads List should be a searchable CRM lookup page, not an Open Leads conversion section.

Reason:
Kien needs to locate any contact or company within seconds. A separate Open Leads section was ambiguous and made it harder to find specific records in a large lead database.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Auto-extracted Knowledge Base legal clauses require human approval before AI/search can use them.

Reason:
Legal and compliance answers must be based on reviewed evidence. OCR or parser mistakes could create false legal references if draft clauses became searchable automatically.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Knowledge Base is a logistics and operations knowledge module, not a generic legal database.

Reason:
1Aim needs stored knowledge to support customs clearance, import/export compliance, quotation preparation, shipment operations, SOP reuse, and customer-specific know-how. The assistant must answer only from stored evidence to avoid fabricated legal references.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Knowledge Base V1 uses rule-based retrieval and clean service interfaces instead of external AI providers.

Reason:
The product needs a safe evidence-only assistant now while preserving a clean path for future vector search and OpenAI integration.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Relationship maintenance workflows are grouped under a parent `Relationships` menu.

Reason:
Follow-up Queue and Occasion Reminders both support long-term relationship nurturing. Grouping them clarifies that relationship maintenance is a core workspace separate from lead acquisition.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
Email signature is managed centrally in CRM settings and appended to future generated outreach messages.

Reason:
Central signature management keeps campaign messages consistent and avoids editing the same signature in every draft.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
SMTP configuration must be testable before campaign approval.

Reason:
Campaign sending should not be attempted blindly. A test email reduces the risk of failed or misconfigured outreach runs.

Approved By:
Kien Ho

---

Date: 2026-06-22

Decision:
SMTP encryption mode must be explicit.

Reason:
Different providers use different ports and encryption modes. Explicit SSL, TLS, and None settings make timeout and connection failures easier to diagnose.

Approved By:
Kien Ho

---

Date: 2026-06-21

Decision:
Dashboard is an action cockpit, not a reporting screen.

Reason:
1Aim Growth Engine must answer what Kien should do today. Reporting widgets are secondary to follow-up discipline and relationship maintenance.

Approved By:
Kien Ho

---

Date: 2026-06-21

Decision:
Today's Action List must include high-value relationship maintenance even when next follow-up date is not due today.

Reason:
Active, Warm, Customer, Qualified, and China strategic contacts can be more valuable than untouched new leads. High-value relationships must resurface automatically and should not disappear because their next action date is in the future or missing.

Approved By:
Kien Ho

---

Date: 2026-06-21

Decision:
`action_score` is separate from `priority_score`.

Reason:
`priority_score` measures strategic CRM value. `action_score` ranks daily outreach order based on relationship value, maintenance need, China focus, and network membership.

Approved By:
Kien Ho

---

Date: 2026-06-21

Decision:
Today's Action List ranking must be explainable in the UI.

Reason:
Kien needs to trust why high-value relationships appear before new leads. Showing score components makes the dashboard operational instead of mysterious.

Approved By:
Kien Ho
