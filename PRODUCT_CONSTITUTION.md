# Product Constitution

1Aim Growth Engine must use this document as the highest-priority product source of truth for future development.

When this document conflicts with implementation details, roadmap notes, or older documentation, future work should align the product toward this constitution unless Kien explicitly approves a change to the constitution.

## 1. Mission

1Aim Growth Engine exists to:

1. Build international logistics relationships.
2. Convert relationships into opportunities.
3. Convert opportunities into quotations.
4. Convert quotations into shipments.
5. Convert shipments into long-term customers.

The system is primarily designed for:

- Freight Forwarding
- Customs Brokerage
- Overseas Agent Network Development

The product should help 1Aim become a stronger international logistics network operator, not merely a record keeper.

## 2. Non-Goals

The system is not:

- A generic CRM.
- A marketing automation platform.
- A ticketing or helpdesk system.
- A copy of HubSpot.
- A copy of Salesforce.
- A full ERP.

Every feature must support at least one of:

- Relationship building
- Sales generation
- Operations efficiency
- Customer retention

If a proposed feature does not clearly support one of these outcomes, it should not be built.

## 3. Core Data Model

Target business progression:

```text
Organization
    -> Contact
            -> Lead
                    -> Opportunity
                            -> Quotation
                                    -> Shipment
```

Rules:

- Organization is the primary business entity.
- Contact belongs to Organization.
- Lead represents relationship stage and outreach context.
- Customer is a status of Organization, not a separate object.
- Opportunity belongs to an Organization and Contact.
- One Organization may have many Contacts.
- One Organization may have many Leads.
- One Organization may have many Opportunities.
- One Contact may be connected to many Leads or Opportunities over time.
- History must be preserved through activities, notes, sent messages, quotations, and future shipment records.

Current implementation status:

- Organizations, contacts, leads, opportunities, quotations, activities, outreach campaigns, occasion reminders, backup history, and Git backup history exist.
- Customer is correctly implemented as `organizations.customer_status`.
- Shipments are not implemented yet and belong to a future roadmap layer.

## 4. CRM Principles

- Relationship-first CRM.
- Every lead should have a next action.
- Every active lead should eventually enter a follow-up cycle.
- No lead should be forgotten.
- Follow-up date is mandatory for active leads.
- High-value relationships should reappear automatically even if no manual follow-up date was set.
- History must be preserved.
- Data quality is part of relationship quality.
- Organization, Contact, Lead, Opportunity, Quotation, and future Shipment data should stay connected.

Current system alignment:

- Follow-up Queue and Today's Action List already prioritize action.
- Relationship Health and Missing Data Checklist support CRM quality.
- Activity Timeline preserves relationship history.
- Email bounce handling protects CRM hygiene.

## 5. Outreach Principles

- AI may assist outreach.
- Human approves outreach.
- Personalization over spam.
- Relationship building over mass marketing.
- Every real outreach action creates activity history.
- Every real outreach action can generate the next follow-up.
- Preview sends and tests must not update CRM relationship state.
- Invalid, bounced, or unsafe recipients must be excluded by default.
- Message drafts should be reviewable before sending.
- Open and reply tracking may support follow-up discipline, but tracking signals should inform human judgement rather than replace it.

Current implementation status:

- Outreach is currently rule-based, with instruction presets and templates.
- Human approval is required before sending.
- Include/exclude controls, preview-to-self, quality checks, final approval, bounce handling, and follow-up updates exist.
- Outreach tracking stores campaign opens and replies when tracking URL/IMAP access is configured.

## 6. Opportunity Principles

Target pipeline stages:

- Interested
- Qualified
- Quoted
- Negotiation
- Won
- Lost

Rules:

- Opportunities must be visible from dashboard and opportunity views.
- Revenue forecasting should be possible.
- Pipeline should show bottlenecks.
- Opportunities should connect relationship work to real revenue potential.
- Won opportunities should update the linked Organization to Customer.
- Lost opportunities should remain in history.

Current implementation status:

- Opportunity Pipeline V1 exists.
- Current implementation uses `Quote Requested` where this constitution uses `Qualified`.
- This stage mismatch should be resolved in a future migration or documented compatibility layer.

## 7. Dashboard Principles

Dashboard must answer:

1. Who should I contact today?
2. Who replied?
3. Which relationships are warming up?
4. Which opportunities need attention?
5. What revenue is expected?
6. Which countries and networks are strongest?
7. What is my highest priority action today?

Dashboard should be action-oriented rather than reporting-oriented.

Rules:

- Today's Action List is the primary dashboard component.
- Reporting widgets are secondary.
- Dashboard should surface revenue and relationship actions before vanity metrics.
- Follow-up Queue can hold deeper operational lists; Dashboard should stay focused.

Current implementation status:

- Dashboard is already treated as an action cockpit.
- Today's Action List, action score, relationship funnel, data quality, China network, campaign progress, country pipeline, backup status, and opportunity KPIs exist.

## 8. Automation Principles

Automate:

- Data entry
- OCR
- Parsing
- Reusable document intelligence parsing
- Follow-up scheduling
- Message drafting
- Reporting
- Dashboard updates
- Backup creation
- Git backup diagnostics
- Knowledge retrieval from approved stored evidence
- Legal document metadata extraction and draft clause parsing
- Central document parsing for legal, SOP, case, logistics, inquiry, quotation, compliance, and shipment-intake workflows
- Pluggable document parser providers with regex used only as fallback

Do not automate:

- Relationship judgement
- Opportunity qualification
- Strategic decisions
- Final message approval
- Fabricated legal or compliance references
- Treating unreviewed extracted clauses as approved legal evidence

AI assists.

Human decides.

Current implementation status:

- Quick Capture and OCR/namecard import support data entry automation.
- Parser and deduplication support clean object creation.
- Follow-up initialization, scheduling, reminders, dashboards, backups, Git diagnostics, and message drafting support automation.
- Final outreach approval remains manual.

## 9. UI Principles

Accessibility is mandatory.

Rules:

- Large font first.
- Font scaling must never be removed.
- Dark mode default.
- Minimal clicks.
- Mobile-friendly layout.
- Fast data entry.
- Important actions always visible.
- Operational screens should be compact and action-oriented.
- Admin modules should be collapsed by default when the page contains many maintenance tools.

Current implementation status:

- Dark theme and global typography scale exist.
- Admin modules are collapsed by default.
- Lead Detail uses tabs to reduce long scrolling.
- Follow-up Queue and Dashboard prioritize operational action.

## 10. Data Safety

- Git is required.
- Database backup is required.
- Restore capability is required.
- Every major feature must be recoverable.
- No feature may compromise data integrity.
- Backup and restore should be testable.
- Git success must never be claimed unless push succeeds.
- Destructive data operations must be scoped, explicit, and recoverable.

Current implementation status:

- Automatic SQLite backups exist.
- Backup retention keeps the latest 30 backups.
- Restore was tested by backing up, deleting a test record, restoring, and verifying the record returned.
- Git backup automation and Git Health Monitor exist.

## 11. Definition of Done

A feature is complete only if:

1. Business workflow works.
2. UI works.
3. Data is saved correctly.
4. Dashboard updates correctly where relevant.
5. Activity history is recorded where relevant.
6. Backup compatibility is preserved.
7. Existing features are not broken.
8. Documentation is updated when business logic, architecture, or decisions change.
9. Tests or smoke checks are run when practical.
10. Any known risks are reported.

For outreach or relationship features, Done also means:

- Follow-up impact is clear.
- History is preserved.
- Human approval remains in control.

For data model features, Done also means:

- Migration path is clear.
- Existing records remain readable.
- Duplicated concepts are avoided.

## 12. Future Roadmap

Layer 1: CRM Foundation

- Organizations
- Contacts
- Leads
- Customers as Organization status
- Activities
- Follow-up discipline

Layer 2: Outreach Engine

- Quick Capture
- OCR/namecard import
- Campaign drafting
- Review and approval
- Sending
- Bounce handling
- Follow-up updates

Layer 3: Opportunity Pipeline

- Opportunity creation
- Stage management
- Forecasting
- Bottleneck visibility
- Dashboard revenue signals

Layer 4: Quotation Automation

- Quotation records
- Quote preparation tasks
- Quote follow-up
- Quote-to-opportunity linkage
- Compliance and SOP evidence from Knowledge Base

Layer 5: Shipment Management

- Shipment/job records
- Won opportunity conversion
- Operational status
- Customer history

Layer 6: Customer Retention

- Customer follow-up cycles
- Occasion reminders
- Renewal and repeat business prompts
- Relationship health by customer

Layer 7: Management Reporting

- Revenue reports
- Network strength reports
- Country and membership performance
- Relationship asset visibility

## Existing System Map

CRM:

- Organizations, contacts, leads, activities, and relationship health form the relationship CRM foundation.

Organizations:

- Primary business entity. Stores identity, country/city, membership, type, website, local name, customer status, relationship tone, dates, and notes.

Contacts:

- People linked to organizations. Store communication channels, relationship status, follow-up dates, birthday, preferred channel/language/tone, email status, and notes.

Leads:

- Outreach and prospecting records linked to organizations and contacts. Store lead status, source/campaign, next action, next action date, priority score, and action score.

Customers:

- Organizations with `customer_status = Customer`.

Opportunities:

- Revenue pipeline records linked to organizations and contacts. Store stage, trade lane, service type, potential revenue/profit, expected close, next action, and notes.

Outreach Campaigns:

- Rule-based campaign drafting, recipient review, subject templates, instruction presets, final approval, SMTP sending, bounce prevention, message history, and follow-up updates.

Follow-up Queue:

- Operational action list for due, overdue, high-value, and unscheduled relationship maintenance.

Occasion Reminders:

- Relationship reminder system for birthdays, holidays, anniversaries, and custom relationship events.

Dashboard:

- Sales cockpit focused on Today's Action List, relationship strength, data quality, China network, country pipeline, campaign progress, opportunity KPIs, and backup status.

Backup Center:

- SQLite database backups on app start, timestamped backup files, retention, Admin status, and tested restore behavior.

Git Integration:

- Git status, backup script, lock handling, backup history, auto backup settings, and push verification discipline.

Quick Capture:

- Text and namecard capture flow that parses CRM data, supports review, deduplication, and creation of organization/contact/lead/customer records.

OCR Namecard Import:

- Namecard image upload supports text extraction into Quick Capture, then parser/review/deduplication before save.

Knowledge Base:

- Stores laws, decrees, circulars, official letters, internal SOPs, real-life cases, and customer-specific know-how for logistics, customs clearance, import/export compliance, quotation preparation, and shipment operations.
- Assistant answers only from stored knowledge and must never fabricate legal references.
- Uploaded legal documents may be auto-parsed, but extracted clauses become AI/search evidence only after human approval.
- Stores business intelligence assets: lessons learned, market intelligence, vendor intelligence, customer intelligence, and shipment history intelligence.
- Intelligence records are reusable memory for human decision support, not automatic strategic decisions.
- Opportunity and Quotation workflows may create intelligence records when useful learning appears before a shipment/job module exists.
- Source object links must be preserved so future shipment/job intelligence can be traced back to the originating business record.
