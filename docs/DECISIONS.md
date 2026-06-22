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

Date: 2026-06-22

Decision:
Git backup must use an application-level lock and stale Git lock cleanup.

Reason:
Windows intermittently leaves `index.lock` or `packed-refs.lock` when multiple Git processes touch the repo. A higher-level lock prevents concurrent backup execution, while stale lock cleanup avoids unnecessary manual repair.

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
