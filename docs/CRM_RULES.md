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
2. Generate rule-based personalized drafts using contact and organization fields.
3. Review and edit each message.
4. Approve and send manually.
5. Update CRM follow-up state after successful send.

Campaign sending rules:

- Do not use AI generation for V1/V2.
- Do not send without explicit `Approve & Send`.
- Do not send if SMTP settings are missing.
- SMTP settings should be verified with a test email before sending a real campaign.
- After a successful send, set `lead_status = Contacted`.
- After a successful send, set `next_action = Follow-up`.
- After a successful send, set `next_action_date = today + 7 days`.
- Log an activity for each sent message.

Campaign metrics:

- Sent
- Opened
- Replied
- Qualified
