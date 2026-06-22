# Changelog

## 2026-06-21

- Added CRM development rules documentation.
- Documented core CRM model, dashboard philosophy, follow-up philosophy, and documentation policy.
- Added `action_score` for Today's Action List ranking.
- Updated Today's Action List inclusion logic to include scheduled follow-ups, high-value relationship maintenance, customer/qualified organization maintenance, and new lead first touch.
- Added action reason labels: Due Today, Overdue, Active Relationship Maintenance, Customer Maintenance, New Lead First Touch.
- Kept Dashboard simplified by not re-adding China Priority Leads or New Leads Needing First Touch.
- Added a "Why" popover to Today's Action List showing action reason, due date, overdue days, and action score components.
- Added Relationship Health indicator on Lead Detail with explainable score components.
- Added Relationship Health to Dashboard Today's Action List.
- Added Missing Data Checklist to Lead Detail for contact and organization cleanup.

## 2026-06-22

- Added `PRODUCT_CONSTITUTION.md` as the highest-priority product source of truth.
- Added `PRODUCT_CONSISTENCY_REPORT.md` comparing the constitution against architecture, CRM rules, `.codex-rules.md`, and current implementation.
- Updated architecture documentation to reference the Product Constitution and consistency report.
- Added Outreach Campaign Engine V2 foundation.
- Added audience filtering by country, membership, lead status, and relationship status.
- Added rule-based personalized message generation using contact and organization fields.
- Added review/edit screen before sending.
- Added SMTP settings in Admin.
- Added Send Test Email action in Admin for SMTP verification.
- Added SMTP encryption dropdown with SSL, TLS, and None.
- Added SMTP Test Connection action that verifies connection, encryption, and authentication without sending email.
- Improved SMTP error messages for connection, timeout, authentication, TLS, and credential failures.
- Added `outreach_campaigns` and `outreach_messages` tables.
- Added recipient include/exclude checkboxes to Outreach Campaign review.
- Added global campaign subject templates with contact and organization tokens.
- Added rule-based Campaign Instructions and Regenerate Campaign action.
- Added Preview First 5 and Generate Full Campaign workflow.
- Added final Campaign Summary before sending.
- Added reusable outreach campaign templates.
- Added centralized Email Signature settings in Admin and automatic signature append for generated outreach messages.
- Added `outreach_campaign_templates` table.
- Added Outreach Campaign Review V2 with short subject template presets and expanded subject variables.
- Added Campaign Instruction Presets for Friendly OLO Intro, China Agent Outreach, WCA Introduction, Follow-up No Reply, Holiday Greeting, and Custom.
- Added Apply Edit To All Drafts find/replace workflow.
- Added Send Preview To Myself with `[PREVIEW]` subject prefix and no CRM state updates.
- Added rule-based campaign quality checks for quality, spam risk, and personalization.
- Added required final review approval checkbox.
- Changed successful outreach activity logging to `Email Sent` with campaign, subject, recipient, and timestamp details.
- Added campaign result summary with sent, failed, skipped, failed-recipient view, and Follow-up Queue shortcut.
- Added Email Bounce Handling V1 with `contacts.email_status`, `outreach_messages.delivery_status`, and `processed_bounce_messages`.
- Added Admin Email Bounce Processing via IMAP using saved SMTP credentials.
- Added hard/soft bounce parsing, bounced recipient extraction, contact status updates, bounce activities, and processed message tracking.
- Added campaign exclusion for contacts marked `Bounced` or `Invalid`.
- Added manual Lead Detail actions to mark email Valid, Invalid, or Bounced.
- Added Admin Invalid / Bounced Email Cleanup view with status/search filters, corrected email save, status actions, and Open Lead shortcut.
- Collapsed Admin modules by default so each maintenance area opens only when clicked.
- Added CRM updates after successful campaign send: lead contacted, next action follow-up, next action date +7 days.
- Added campaign metrics for sent, opened, replied, and qualified.
- Added Git backup automation script `scripts/git_backup.py`.
- Added Windows wrapper `backup_git.bat`.
- Added Git backup troubleshooting guide `docs/GIT_BACKUP.md`.
- Added Git Health Monitor in Admin with repository details, status, errors, suggested fixes, and Backup Now action.
- Added application-level Git backup lock to prevent concurrent backup execution.
- Added stale cleanup for `.git/index.lock` and `.git/packed-refs.lock` older than 5 minutes.
- Added `backup_history` table and Admin history view.
- Added Auto Backup Every setting with Off, 30 min, 1 hour, and 4 hours options.
- Added Dashboard Last Successful Backup widget.
- Added Opportunity Pipeline V1 with Opportunities menu, list, detail, create from Lead Detail, stage buttons, opportunity dashboard KPIs, and revenue KPIs.
