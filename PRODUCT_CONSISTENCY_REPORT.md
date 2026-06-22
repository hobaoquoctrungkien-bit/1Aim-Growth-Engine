# Product Consistency Report

Date: 2026-06-22

Reviewed sources:

- `PRODUCT_CONSTITUTION.md`
- `docs/ARCHITECTURE.md`
- `.codex-rules.md`
- `docs/CRM_RULES.md`
- Current app/database structure

## Summary

The current 1Aim Growth Engine mostly aligns with the new Product Constitution.

Strong alignments:

- Customer is an Organization status, not a separate table.
- Dashboard is action-oriented.
- Follow-up Queue protects against forgotten leads.
- Outreach requires human approval before real sending.
- Backup, restore, and Git safety systems exist.
- Quick Capture and OCR/namecard import support data entry automation.
- Occasion Reminders support long-term relationship maintenance.

Main conflicts:

- Opportunity stage names are not fully aligned.
- `.codex-rules.md` requires automatic commit/push after every completed feature, which may conflict with local Git lock and permission realities.
- Product Constitution allows AI-assisted outreach, while current CRM rules describe Outreach V1/V2 as rule-based and no external AI.
- Shipment Management is in the target data model but not implemented yet.

## Conflict 1: Opportunity Stage Names

Product Constitution target stages:

- Interested
- Qualified
- Quoted
- Negotiation
- Won
- Lost

Current `docs/ARCHITECTURE.md` stages:

- Interested
- Quote Requested
- Quoted
- Negotiation
- Won
- Lost

Impact:

The constitution treats `Qualified` as the second opportunity stage, while the current app uses `Quote Requested`. This can cause future dashboard, reporting, and pipeline logic to diverge.

Recommendation:

Choose one of these approaches:

1. Migrate Opportunity Pipeline stage `Quote Requested` to `Qualified`.
2. Keep `Quote Requested` as an implementation-specific sub-stage but document it as compatible with constitution stage `Qualified`.
3. Expand the constitution to include both `Qualified` and `Quote Requested` if Kien wants both business meanings.

Recommended option:

Use `Qualified` as the canonical stage and treat quote request as a quotation workflow trigger.

## Conflict 2: Outreach AI Principle vs Rule-Based Current State

Product Constitution:

- AI assists outreach.
- Human approves outreach.

Current rules:

- Outreach V1/V2 does not use external AI.
- Campaign Instructions tune a rule-based generator only.

Impact:

This is not a direct conflict if interpreted as roadmap direction. However, future developers might incorrectly add automatic AI sending or AI qualification.

Recommendation:

Update CRM rules to state:

- Current implementation is rule-based.
- Future AI may assist drafting and personalization.
- AI must never bypass human final approval.

## Conflict 3: `.codex-rules.md` Git Requirement

`.codex-rules.md` currently says every completed feature must:

1. Run `git add .`
2. Run `git commit`
3. Run `git push origin main`
4. Verify push succeeded

Observed system reality:

- Git lock and permission issues have occurred on Windows.
- The app now includes `scripts/git_backup.py`, `backup_git.bat`, Git Health Monitor, backup history, and lock cleanup.
- Some environments cannot write `.git` directly from the agent sandbox.

Impact:

The rule is correct in spirit but can be impossible in restricted environments. It may also conflict with the instruction to never claim Git updated unless push succeeded.

Recommendation:

Replace `.codex-rules.md` with a safer rule:

```text
After every completed feature:

1. Attempt Git backup using scripts/git_backup.py or backup_git.bat.
2. Verify commit and push succeeded.
3. Return commit hash, branch, and push status.
4. If Git cannot run due to lock, permission, auth, or sandbox limits, report the exact blocker and do not claim Git updated.
5. Never claim Git updated unless push succeeded.
```

## Conflict 4: Shipment Layer Not Implemented

Product Constitution target chain:

```text
Organization -> Contact -> Lead -> Opportunity -> Quotation -> Shipment
```

Current implementation:

- Quotations exist in the database.
- Shipment/job management is not implemented.

Impact:

No immediate bug. This is a roadmap gap.

Recommendation:

Keep Shipment Management as Layer 5. Do not create partial shipment objects until Opportunity and Quotation flows are stable.

## Conflict 5: Lead Meaning

Product Constitution:

- Lead represents relationship stage and outreach context.

Existing CRM Rules:

- Lead = sales opportunity or outreach record connected to a contact and organization.

Impact:

The word "opportunity" inside Lead definition can blur Lead vs Opportunity separation.

Recommendation:

Update CRM wording to:

```text
Lead = outreach/prospecting record connected to a Contact and Organization.
Opportunity = qualified revenue potential.
```

This preserves the current data model while making the business boundary cleaner.

## Recommended Documentation Updates

Update `docs/ARCHITECTURE.md`:

- Add Product Constitution as the highest-priority product document.
- Clarify Opportunity stage alignment with `Qualified`.
- Mention Shipment Management as future Layer 5, not currently implemented.

Update `docs/CRM_RULES.md`:

- Clarify Lead vs Opportunity boundary.
- Clarify AI roadmap: rule-based now, AI assist later, human final approval always.

Update `.codex-rules.md`:

- Replace strict unconditional commit/push with Git backup attempt and verified push reporting.
- Include blocked-state reporting for permission/sandbox/Git lock failures.

Update `docs/DECISIONS.md`:

- Record Product Constitution as highest-priority product document.
- Record canonical Opportunity stage decision after Kien approves stage alignment.

## Consistency Score

Overall consistency: High

Risk areas:

- Medium: Opportunity stage naming
- Medium: Git rule feasibility
- Low: AI wording
- Low: Shipment roadmap gap
- Low: Lead wording ambiguity

## Next Recommended Action

Ask Kien to approve the Opportunity stage decision:

- Option A: Replace `Quote Requested` with `Qualified`.
- Option B: Keep `Quote Requested` and update the constitution.
- Option C: Use both stages: Interested, Qualified, Quote Requested, Quoted, Negotiation, Won, Lost.
