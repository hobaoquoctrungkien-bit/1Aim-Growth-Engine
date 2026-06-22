# Architecture

## Application

1Aim Growth Engine is a Streamlit application backed by SQLite.

Primary files:

- `app.py`: Streamlit UI and page flows.
- `database.py`: SQLite schema, migrations, business logic, scoring, CRM queries.
- `typography.py`: global typography tokens and UI scale.
- `data/growth_engine.db`: local SQLite database.

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

Customer is represented by `organizations.customer_status`. There is no separate customers table.

## Core Fields

Organizations include company identity, geography, membership, website, customer status, preferred relationship settings, and relationship dates.

Contacts include person identity, communication channels, relationship status, birthday, preferred channel/language, last contacted date, and next follow-up date.

Leads include organization/contact links, source/campaign, lead status, priority score, action score, next action, and next action date.

Opportunities include opportunity name, organization/contact links, owner, stage, trade lane, service type, potential revenue, potential profit, expected close date, next action, next action date, and notes.

Outreach campaigns store campaign metadata in `outreach_campaigns` and per-contact message records in `outreach_messages`.

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

## Outreach Campaigns

The Outreach Campaigns page supports:

- Audience filtering by country, membership, lead status, and relationship status
- Rule-based message draft generation
- Per-message review and editing before send
- Manual approval via `Approve & Send`
- SMTP delivery using settings stored in `app_settings`
- SMTP test email from Admin using the same saved settings
- CRM updates after successful send
- Campaign metrics

SMTP settings are stored in `app_settings`.

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

The Backup Now button runs `scripts/git_backup.py` and displays the script output inside the Admin page.

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

Business logic changes update `docs/CRM_RULES.md`.

Data structure changes update `docs/ARCHITECTURE.md`.

Significant decisions update `docs/DECISIONS.md`.

Completed features append to `docs/CHANGELOG.md`.
