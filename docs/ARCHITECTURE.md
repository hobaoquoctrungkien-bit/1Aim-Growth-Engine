# Architecture

## Application

1Aim Growth Engine is a Streamlit application backed by SQLite.

Product direction is governed by `PRODUCT_CONSTITUTION.md`, which is the highest-priority product document for future development.

Primary files:

- `app.py`: Streamlit UI and page flows.
- `database.py`: SQLite schema, migrations, business logic, scoring, CRM queries.
- `typography.py`: global typography tokens and UI scale.
- `data/growth_engine.db`: local SQLite database.
- `PRODUCT_CONSTITUTION.md`: product mission, principles, data model direction, and development guardrails.
- `PRODUCT_CONSISTENCY_REPORT.md`: current alignment report and recommended documentation/system updates.

## CRM Data Model

Core CRM tables:

- `organizations`
- `contacts`
- `leads`
- `opportunities`
- `activities`
- `relationship_occasions`
- `holiday_library`
- `outreach_campaigns`
- `outreach_messages`
- `outreach_campaign_templates`
- `processed_bounce_messages`
- `backup_history`

Customer is represented by `organizations.customer_status`. There is no separate customers table.

## Core Fields

Organizations include company identity, geography, membership, website, customer status, preferred relationship settings, and relationship dates.

Contacts include person identity, communication channels, relationship status, birthday, preferred channel/language, last contacted date, and next follow-up date.

Contacts also include `email_status` for delivery hygiene:

- Valid
- Invalid
- Bounced
- Unknown

Leads include organization/contact links, source/campaign, lead status, priority score, action score, next action, and next action date.

Opportunities include opportunity name, organization/contact links, owner, stage, trade lane, service type, potential revenue, potential profit, expected close date, next action, next action date, and notes.

Outreach campaigns store campaign metadata in `outreach_campaigns` and per-contact message records in `outreach_messages`.

`outreach_messages.delivery_status` tracks message delivery state:

- Sent
- Failed
- Bounced
- Delivered
- Replied
- Unknown

Reusable campaign templates are stored in `outreach_campaign_templates`:

- `template_name`
- `campaign_name`
- `subject_template`
- `instructions`

Opportunity pipeline stages:

- Interested
- Quote Requested
- Quoted
- Negotiation
- Won
- Lost

The existing legacy opportunity fields `title` and `status` are kept for compatibility. New pipeline UI uses `opportunity_name` and `stage`, while save logic keeps legacy fields synchronized.

## Scoring Fields

`leads.priority_score` measures strategic CRM value.

`leads.action_score` ranks who should appear first in Today's Action List.

Both scores are calculated from existing organization/contact/lead fields. They do not create new CRM objects.

Relationship health is calculated at read time for Lead Detail. It is not stored as a separate field. It combines customer status, relationship status, last contact recency, next follow-up discipline, and CRM data quality.

Missing Data Checklist is also calculated at read time from existing contact and organization fields. It is not stored as a table or field.

## Dashboard

Dashboard is an action cockpit, not a reporting screen.

Primary component:

- Today's Action List

Secondary widgets:

- Outreach queue KPIs
- Relationship funnel
- CRM data quality
- China network by city
- Overdue follow-ups
- Warm relationships
- Campaign progress
- Country pipeline

Removed duplicate dashboard widgets:

- China Priority Leads
- New Leads Needing First Touch

Those views belong in Follow-up Queue.

## Follow-up Queue

Follow-up Queue remains the broader operational list with filters and quick actions. Dashboard only shows the most important actions for today.

## Relationships Workspace

Relationship maintenance workflows are grouped under the parent menu `Relationships`.

Sub-pages:

- Follow-up Queue
- Occasion Reminders

Legacy navigation requests to those pages should route through the parent `Relationships` menu and preserve the intended sub-page.

## Leads Workspace

Lead-related workflows are grouped under the parent menu `Leads`.

Sub-pages:

- Outreach Campaigns
- Quick Capture
- Leads Import
- Leads List

Legacy navigation requests to those pages should route through the parent `Leads` menu and preserve the intended sub-page.

## Outreach Campaigns

The Outreach Campaigns page supports:

- Audience filtering by country, membership, lead status, and relationship status
- Preview First 5 before full campaign generation
- Rule-based message draft generation
- Campaign Instructions for rule-based regeneration
- Global campaign subject templates with contact and organization tokens
- Default short subject templates
- Campaign instruction presets
- Global find/replace across current drafts
- Send Preview To Myself without CRM state updates
- Rule-based quality checks for message review
- Include/exclude recipient checkboxes
- Per-message review and editing before send
- Campaign summary and required approval checkbox before final send
- Manual approval via `Final Approve & Send`
- Campaign result display after send with sent, failed, skipped, failed-recipient view, and Follow-up Queue navigation
- Reusable campaign templates
- Central email signature appended to generated messages
- SMTP delivery using settings stored in `app_settings`
- SMTP test email from Admin using the same saved settings
- SMTP connection test from Admin without sending email
- CRM updates after successful send
- Campaign metrics

SMTP settings and email signature settings are stored in `app_settings`.

Email signature setting keys:

- `signature_name`
- `signature_title`
- `signature_company`
- `signature_phone`
- `signature_email`
- `signature_website`
- `signature_wechat`
- `signature_whatsapp`
- `signature_html`

SMTP encryption modes:

- SSL: `smtplib.SMTP_SSL(host, port)`
- TLS: `smtplib.SMTP(host, port)` followed by `starttls()`
- None: `smtplib.SMTP(host, port)`

## Email Bounce Processing

Admin includes Email Bounce Processing.

V1 reads bounce messages by IMAP using:

- Host: `mail.1aimlogistics.com`
- Port: `993`
- Encryption: SSL
- Username/password: saved SMTP username and password

Bounce processing:

- Searches bounce-like subjects.
- Parses bounced recipient emails from `Final-Recipient`, `Original-Recipient`, `RCPT TO`, `Recipient`, or visible email addresses.
- Classifies hard and soft bounces with rule-based text checks.
- Updates hard-bounced contacts to `email_status = Bounced`.
- Logs bounce activities.
- Updates matching outreach message delivery status.
- Stores processed messages in `processed_bounce_messages`.
- Does not delete mailbox messages in V1.

Admin also includes Invalid / Bounced Email Cleanup.

The cleanup view queries contacts with `email_status IN ('Bounced', 'Invalid')`, shows company and lead context, and supports:

- saving a corrected email as Valid
- marking email Valid, Invalid, or Bounced
- opening the related Lead Detail page

## Admin UX

Admin modules are displayed as collapsed sections by default so operational settings do not overwhelm the page.

Current Admin modules:

- Database Backup Status
- Git Status
- System Settings
- Email Sending
- Email Bounce Processing
- Invalid / Bounced Email Cleanup
- Email Signature
- CRM Activation

## Git Health Monitor

Admin includes a Git Status section for local backup visibility.

It displays:

- Repository path
- Current branch
- Remote URL
- Last commit hash
- Last commit time
- Last push time
- Sync status
- Error and suggested fix when Git reports a problem
- Remaining uncommitted files when the working tree is dirty

The Backup Now button runs `scripts/git_backup.py` and displays the script output inside the Admin page.

After Backup Now completes, Admin reruns Git Health and refreshes the Git Status section from current repository state.

The Refresh Git Status button manually reruns Git status, latest commit, and remote sync checks.

Git backup history is stored in `backup_history`.

Auto backup uses `app_settings`:

- `git_auto_backup_every`
- `git_last_auto_backup_at`
- `git_backup_running`

The Git backup script creates an application-level lock file and cleans stale Git lock files older than 5 minutes:

- `.git/index.lock`
- `.git/packed-refs.lock`

Git Health ignores transient runtime lock files:

- `data/git_backup_running.lock`
- `*.lock`

## Opportunities

The Opportunities page contains:

- Opportunity dashboard KPIs
- Revenue KPIs
- Opportunity list
- Opportunity detail
- Stage change actions
- Create opportunity workflow

Lead Detail can create an opportunity directly from the current lead context.

## Documentation Policy

Product direction follows `PRODUCT_CONSTITUTION.md` first.

Business logic changes update `docs/CRM_RULES.md`.

Data structure changes update `docs/ARCHITECTURE.md`.

Significant decisions update `docs/DECISIONS.md`.

Completed features append to `docs/CHANGELOG.md`.
