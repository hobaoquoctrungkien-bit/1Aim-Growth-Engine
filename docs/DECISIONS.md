# Decisions

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
SMTP configuration must be testable before campaign approval.

Reason:
Campaign sending should not be attempted blindly. A test email reduces the risk of failed or misconfigured outreach runs.

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
