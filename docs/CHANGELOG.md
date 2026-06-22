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

- Added Outreach Campaign Engine V2 foundation.
- Added audience filtering by country, membership, lead status, and relationship status.
- Added rule-based personalized message generation using contact and organization fields.
- Added review/edit screen before sending.
- Added SMTP settings in Admin.
- Added Send Test Email action in Admin for SMTP verification.
- Added `outreach_campaigns` and `outreach_messages` tables.
- Added CRM updates after successful campaign send: lead contacted, next action follow-up, next action date +7 days.
- Added campaign metrics for sent, opened, replied, and qualified.
- Added Git backup automation script `scripts/git_backup.py`.
- Added Windows wrapper `backup_git.bat`.
- Added Git backup troubleshooting guide `docs/GIT_BACKUP.md`.
- Added Git Health Monitor in Admin with repository details, status, errors, suggested fixes, and Backup Now action.
- Added Opportunity Pipeline V1 with Opportunities menu, list, detail, create from Lead Detail, stage buttons, opportunity dashboard KPIs, and revenue KPIs.
