# CRM Rules

## Core Business Model

- Organization = company.
- Contact = person working for an organization.
- Lead = sales opportunity or outreach record connected to a contact and organization.
- Customer = status of an organization, not a separate object.

## Relationship Funnel

- New
- Connected
- Introduced
- Warm
- Active

## Customer Funnel

- Prospect
- Qualified
- Customer

## Opportunity Pipeline

Opportunity tracks real business and revenue potential. It is connected to an organization and contact.

Pipeline stages:

- Interested
- Quote Requested
- Quoted
- Negotiation
- Won
- Lost

When an opportunity is marked Won, the linked organization becomes a Customer.

Opportunity pipeline is revenue tracking. Relationship tracking remains in contacts, organizations, leads, and follow-up logic.

## Inquiry Intake

Inbound freight inquiries should become reviewed opportunities, not separate CRM objects.

Inquiry Intake workflow:

1. Open Opportunities and use `Create Opportunity`.
2. Use `Parse Inquiry` for pasted inquiry text or `Manual Entry` for direct entry.
3. Paste the inquiry email and upload any customer attachments when parsing.
4. Extract opportunity name, organization, contact, trade lane, service, cargo description, origin, destination, volume, weight, container type, quantity, incoterm, deadline/date information, and quote-preparation action.
5. Let the user review and correct extracted fields before saving.
6. Save uploaded files into a dated folder under `data/inquiries/`.
7. Create an opportunity with `stage = Quote Requested`.
8. Create an open `prepare_quote` task due on the reviewed next action date.
9. Log an `Inquiry Received` activity with the opportunity, contact, organization, and saved file references.

Rules:

- Do not create a separate inquiry object in V1.
- Do not auto-qualify strategic value beyond creating the quote-preparation task.
- Existing organizations and contacts should be reused when matched by current CRM upsert rules.
- Parsed inquiry details must stay editable before save.
- Parse Inquiry and Manual Entry must both use the shared `create_opportunity(data)` database function.
- New quotation-preparation fields on opportunities are optional and must default safely, with `quotation_status = Not Started`.
- TXT, EML, CSV, PDF, DOCX, XLS, and XLSX attachments should be parsed when possible.
- Attachments are saved for quotation preparation evidence, but unsupported attachment types may be saved without text extraction.

Admin test-opportunity cleanup rules:

- Preview matching records before deletion.
- Require typed confirmation before deletion.
- Only delete records that still match the strict cleanup rule in the database layer.
- Target only obvious test records with zero revenue, stage `Interested`, no linked organization/contact, and test-like names containing `Need rate`, `Nhờ`, or `test`.

## Pricing Engine

Pricing Engine supports quotation preparation after an opportunity reaches quote work.

Rules:

- Pricing lines belong to an existing opportunity.
- Carrier rates, agent rates, and local charges are saved as `vendor_rates`.
- Each pricing line stores cost, currency, margin percentage, optional fixed margin, and suggested sell amount.
- Suggested sell amount equals cost plus percentage margin plus fixed margin.
- Local charges are not compared as standalone carrier options when carrier or agent rates exist.
- Local charges are rolled into each carrier or agent option for rate comparison.
- Applying the suggested sell rate updates opportunity `potential_revenue` and `potential_profit` only.
- Pricing Engine does not create shipments, billing records, accounting records, or operation execution objects.

## Quotation Engine

Quotation Engine creates customer-facing quotes from opportunities after pricing work.

Rules:

- A quotation must belong to an existing opportunity when created from the app workflow.
- Quote line items are saved as quotation-owned items, not as shipment, billing, or accounting records.
- Saved pricing lines may be copied into quotation line items, but the quotation remains editable before approval.
- Quote statuses are Draft, Pending Approval, Approved, Sent, and Rejected.
- A quote should be reviewed before approval.
- Marking a quote Approved records who approved it and when.
- Marking a quote Sent records the sent timestamp.
- Approved or sent quotations update the linked opportunity to `Quoted`.
- Quote revisions should use version control instead of overwriting customer history.
- New quote versions keep the same quote number, increment the version number, and copy the prior quote line items.
- Excel and PDF exports must use saved quotation data so exported documents match the approval record.
- Quotation Engine does not create shipments, invoices, payment records, or accounting records.

## Strategic Direction

1Aim's primary growth strategy is to build strong freight-forwarder relationships, with special focus on China network development.

Follow-up discipline is more important than reporting. The dashboard must surface actions, not just statistics.

## Dashboard Philosophy

The dashboard exists to answer:

"What should Kien do today?"

The dashboard is not a reporting screen. The most important component is Today's Action List. All other widgets are secondary.

When conflicts exist, prioritize actionability over analytics.

## Follow-up Philosophy

Every contact should always have:

- Last Contact Date
- Next Follow-up Date
- Next Action

A contact should never disappear simply because no follow-up date exists.

High-value relationships must reappear automatically, including:

- Active relationships
- Warm relationships
- Customers
- Qualified organizations
- China strategic contacts

## Leads List Lookup

Leads List is for fast CRM lookup, not conversion workflow.

Rules:

- Do not show a separate `Open Leads` section.
- Show `All Leads` with search, filters, sorting, and pagination.
- Search must cover company, contact, email, phone, WeChat, WhatsApp, city, country, and membership.
- Email status must be filterable so bounced or invalid records can be found quickly.
- The user should be able to find a specific company or contact, such as Ronghua or Jackson, within seconds.

## Today's Action List Inclusion

Include records if any condition is true:

- `lead.next_action_date <= today`
- `contact.next_follow_up_at <= today`
- `contact.relationship_status IN ('Warm', 'Active')` and contact has never been contacted or was last contacted at least 30 days ago
- `organization.customer_status IN ('Customer', 'Qualified')` and contact has never been contacted or was last contacted at least 30 days ago
- `lead.lead_status = 'New'` and `lead.next_action_date <= today`

## Today's Action List Sorting

Sort by:

1. `action_score` descending
2. `overdue_days` descending
3. `next_action_date` ascending

## Today's Action Reasons

- Due Today
- Overdue
- Active Relationship Maintenance
- Customer Maintenance
- New Lead First Touch

## Today's Action Explainability

Each row in Today's Action List should show why it appears and why it is ranked where it is.

The user should be able to inspect:

- Action reason
- Due date
- Overdue days
- Action score components

## Relationship Health

Lead Detail should show a compact relationship health indicator.

Relationship health combines:

- Customer status
- Relationship status
- Last contact recency
- Next follow-up discipline
- CRM data quality

Labels:

- Healthy
- Needs Attention
- At Risk

The score must be explainable through visible components.

Dashboard Today's Action List should also show relationship health so Kien can see relationship strength before opening a record.

## Missing Data Checklist

Lead Detail should show exactly which CRM fields are missing so Kien can clean records quickly.

Contact checklist fields:

- Email
- Phone
- WeChat
- WhatsApp
- Job Title

Organization checklist fields:

- Website
- Membership
- Country
- City
- Organization Type

## Action Score

Action score ranks who should appear first in Today's Action List. It is separate from `priority_score`.

Current formula:

- Customer = +100
- Active = +80
- Warm = +60
- Introduced = +40
- Connected = +20
- New = +0
- China = +20
- OLO = +15
- WCA = +15
- JCTrans = +15
- No contact > 90 days = +40
- No contact > 60 days = +30
- No contact > 30 days = +20
- No contact > 14 days = +10

## Dashboard Simplification

Do not re-add dashboard sections that duplicate Follow-up Queue, including:

- China Priority Leads
- New Leads Needing First Touch

## Outreach Campaigns

Outreach campaigns allow Kien to send personalized email outreach at scale after manual review.

Campaign workflow:

1. Select audience by country, membership, lead status, and relationship status.
2. Preview the first 5 messages before generating the full campaign.
3. Choose a subject template and instruction preset.
4. Generate rule-based personalized drafts using contact and organization fields.
5. Review each recipient and uncheck anyone who should be excluded.
6. Apply global find/replace edits when a phrase needs to change across all drafts.
7. Review quality checks for subject length, message length, greeting, signature, first-name use, and spam-risk words.
8. Send preview messages to Kien before real sending when needed.
9. Review the campaign summary and approve with the required review checkbox.
10. Final approve and send manually.
11. Update CRM follow-up state after successful send.

Campaign sending rules:

- Do not use AI generation for V1/V2.
- Campaign Instructions tune the rule-based generator only; they do not call an external AI API.
- Do not send without explicit `Final Approve & Send`.
- Do not send if SMTP settings are missing.
- Only checked recipients are sent.
- Contacts with `email_status` of `Bounced` or `Invalid` are skipped by default.
- The campaign subject is managed globally with tokens such as `{{first_name}}`, `{{contact_name}}`, `{{company}}`, `{{city}}`, `{{country}}`, `{{membership}}`, and `{{job_title}}`.
- Default subjects should be short and person-focused, avoiding long company-heavy subjects.
- Generated messages automatically append the centrally managed email signature.
- Campaign templates can be saved and reused for campaign name, subject template, and instructions.
- Preview sends must prefix the subject with `[PREVIEW]` and must not update CRM lead/contact state.
- SMTP settings should be verified with a test email before sending a real campaign.
- SMTP connection can be tested without sending email.
- SMTP encryption must be explicit: SSL, TLS, or None.
- After a successful send, set `lead_status = Contacted`.
- After a successful send, set `next_action = Follow-up`.
- After a successful send, set `next_action_date = today + 7 days`.
- Log an `Email Sent` activity for each successfully sent message, including campaign name, subject, recipient email, and sent timestamp.
- Failed recipients must not stop the campaign. Store the recipient error and continue sending remaining emails.
- Real campaign sends should include a unique tracking token.
- Preview sends must not include CRM state updates and should not mark outreach messages as sent/opened/replied.
- Open tracking is valid only when the configured tracking URL is reachable by the recipient email client.
- Reply tracking is processed through IMAP and should not overwrite Qualified, Converted, or Disqualified lead outcomes.
- A detected reply should warm the relationship and schedule a follow-up 14 days later.

Campaign metrics:

- Sent
- Opened
- Replied
- Qualified

## Email Bounce Handling

Contact email status values:

- Valid
- Invalid
- Bounced
- Unknown

Default status is `Unknown`.

Hard bounce indicators include:

- `5.1.1`
- recipient does not exist
- user unknown
- mailbox unavailable
- no such user

Soft bounce indicators include:

- mailbox full
- temporarily unavailable
- `4.x.x`
- connection timed out
- greylisted

Hard bounce behavior:

- Set `contact.email_status = Bounced`.
- Append a hard bounce note to the contact.
- Create an `Email Bounced` activity.
- Mark matching outreach messages as bounced.
- Exclude the contact from future outreach campaigns by default.

Soft bounce behavior:

- Keep contact email status unchanged.
- Create an `Email Soft Bounce` activity.
- Allow retry later.

Bounce processing reads mailbox messages by IMAP, stores processed message IDs, and does not delete bounce emails in V1.

## Invalid Email Cleanup

Admin should provide a cleanup view for contacts with `email_status` of `Bounced` or `Invalid`.

Cleanup actions:

- Correct the email and mark it `Valid`.
- Mark current email `Valid`.
- Mark current email `Invalid`.
- Mark current email `Bounced`.
- Open the linked lead for full CRM context.

Corrected emails should append a contact note and create a contact update activity.

## Knowledge Base Rules

Knowledge Base exists for logistics, customs clearance, import/export compliance, quotation preparation, and shipment operations.

It stores:

- Laws
- Decrees
- Circulars
- Official letters
- Internal SOPs
- Real-life cases
- Customer-specific know-how
- Lessons learned
- Market intelligence
- Vendor intelligence
- Customer intelligence
- Shipment history intelligence

Knowledge Base is not a generic legal database.

AI Assistant rules:

- Search Case Library first.
- Search SOP Library second.
- Search Legal Library third.
- Search Intelligence Library as reusable business memory.
- Answer from stored knowledge only.
- Never fabricate legal references.
- If no supporting evidence exists, answer: "Insufficient information in knowledge base."
- External AI providers are not implemented in V1.
- Auto-extracted legal clauses must be reviewed by a human before they become searchable.
- Chunks with `status = pending_review` must be ignored by AI Assistant and search results.

Approved operational cases should be saved back into Case Library so the system becomes smarter over time.

Legal upload rules:

- PDF, DOCX, TXT, and pasted business text should go through the central document parser pipeline.
- Parser flow is `Extract Text -> AI Parse -> Review -> Save`.
- AI parser provider calls are abstracted through `AIParserProvider`.
- Supported provider implementations are `RegexParserProvider`, `OpenAIParserProvider` stub, and `GeminiParserProvider` stub.
- Regex parsing remains fallback only and should not be expanded aggressively.
- Future parser quality should come from AI providers, not hundreds of fragile regex rules.
- Auto-filled metadata is editable before save.
- User approval is required per extracted clause.
- Rejected or unapproved clauses must not become legal evidence.
- Manual entry remains available when extraction fails or a document is not uploaded.
- Parser output should include field-level confidence where possible.
- Compliance enrichment may suggest topics, SOP matches, and case matches, but must not make legal conclusions.
- Document upload must never be blocked only because parsing failed.

Intelligence rules:

- Lessons learned should capture what to repeat or avoid.
- Market intelligence should capture country, lane, network, and demand signals.
- Vendor intelligence should capture capability, reliability, strengths, and risks.
- Customer intelligence should capture preferences, history, decision behavior, and hidden requirements.
- Shipment history intelligence should capture operational memory from completed or problematic shipments.
- Intelligence confidence must be visible as High, Medium, or Low.
- Intelligence should support human judgement, not become automatic advice.
- Opportunity Detail may save a reviewed opportunity as intelligence when it contains reusable customer, market, sales, or lane learning.
- Quotation Detail may save a reviewed quotation as intelligence when it contains reusable pricing, customer, lane, or quotation learning.
- Saving from Opportunity or Quotation must preserve source context through `source_type` and `source_id`.
- Saving an Opportunity or Quotation as Shipment History Intelligence does not create a shipment/job record. It only captures memory until the shipment module exists.
