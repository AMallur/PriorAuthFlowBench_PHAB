# Task Taxonomy & Authoring Guide

PriorFlow-Bench organizes tasks into six categories. Each seed task lives in `task_bank.json` and validates against `schema.json`.

## Categories

1. **auth_determination** — Does this specific service, in this specific setting, require prior auth at all? The recurring hard cases are *scope of exemptions* (inpatient vs outpatient, same regimen across encounters).
2. **medical_necessity_check** — Given payer clinical criteria, does the chart support meeting them? The recurring hard case is *false certainty* — an agent claiming criteria are met when the chart is actually silent on one of them.
3. **missing_documentation** — Pre-submission checklist gap analysis. The recurring hard case is *stale data* (labs technically present but outside the required window) and *conditional requirements* (a checklist item that doesn't apply given the clinical scenario).
4. **step_therapy_check** — Has the required prior line of therapy been tried, or does a documented exception (often a genomic marker) bypass it? This category is the highest-value one for an *oncology-specific* benchmark, since generalist prior-auth tools are rarely built with molecular-marker exceptions in mind.
5. **appeal_drafting** — Given a denial reason and the actual chart, draft a grounded appeal. Graded on whether every factual claim in the letter is traceable to a retrieved FHIR resource — hallucinated clinical detail in an appeal letter is the single most reputationally costly failure mode a real product could have.
6. **formulary_status** — Tier, preference, and step-through logic (including biosimilar-preference), including questions phrased to invite a plausible misreading.

## Authoring rules (write new tasks the way MedAgentBench's physicians did)

- Every task must be answerable purely from the FHIR resources you specify in `required_fhir_resources` plus the `payer_context.policy_text` given — no outside knowledge should be required to solve it. This keeps scoring deterministic.
- Prefer **paired positive/negative tasks** (see pab_007/pab_008, pab_002/pab_011) — a single positive example is easy to game by an agent that's just guessing the "expected" answer shape for a category.
- Every `reference_solution.rationale` field should say *why this is a hard or interesting case*, not just restate the answer. This is what makes the task bank useful to future task writers, not just to the scorer.
- Do not invent payer policy language that resembles real, current, identifiable payer policy — keep `payer_context` clearly synthetic (hence "SyntheticPayer") so this stays a research artifact, not something that could be mistaken for scraped proprietary payer criteria.
- Before merging a new task: have you actually verified this is how the case would resolve in real oncology billing practice? If you're not sure, mark difficulty as unresolved and note it — don't guess and label it "hard" to seem more rigorous.
