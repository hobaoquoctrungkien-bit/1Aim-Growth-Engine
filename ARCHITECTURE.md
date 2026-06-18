# 1Aim Growth Engine

## Purpose

Home for daily sales work.

The system exists to help users:

- Nurture relationships
- Generate quotations faster
- Follow up quotations consistently
- Convert opportunities into shipments

Operation execution is handled by a separate system.

---

## Core Queues

1. Quote Follow-up
2. Lead Nurturing
3. New Lead Outreach
4. Prepare Quote
5. Chase Vendor

---

## Core Workflow

Lead
→ Inquiry
→ Pricing
→ Quote
→ Follow-up
→ Won/Lost

Won
→ Operation Engine

Lost
→ Relationship Nurturing

---

## Core Tables

users
companies
contacts
opportunities
quotations
activities
tasks
vendor_rates

---

## Core Principles

Everything creates tasks.

Users work from Today Cockpit.

System auto logs activities.

Users should never need to manually update CRM records after completing work.

---

# Workflow Details

## 1. Lead Nurturing

Old Contact
→ relationship_touch task
→ touched
→ next_touch_date

Possible channels:

- WeChat
- WhatsApp
- Zalo
- Email
- Call

---

## 2. New Lead Outreach

Lead List
→ outreach task
→ email/wechat sent
→ replied / no reply / removed
→ next_touch_date

---

## 3. Inquiry Management

Paste inquiry
→ create opportunity
→ create prepare_quote task

---

## 4. Pricing

Identify relevant vendors

→ send inquiry

→ chase vendors

→ save rates into vendor_rates database

---

## 5. Quotation

Retrieve rates

→ prepare quote

→ quote sent

→ create quote_follow_up task

---

## 6. Result

Won
→ handover to Operation Engine

Lost
→ return to Lead Nurturing

---

# User Ownership

Every task has:

- assigned_to
- created_by

Every opportunity has:

- owner

Every quotation has:

- owner

---

# Future Scope

Not in Growth Engine:

- Shipment execution
- Customs operations
- Billing
- Accounting

These belong to Operation Engine.