# Methodology

This follows the structure of the MedAgentBench methodology (Jiang et al., NEJM AI) as closely as is honest to do solo, and explicitly marks where the two diverge.

## 1. Motivation

Existing agent benchmarks for healthcare (MedAgentBench included) evaluate general clinical EHR interaction — retrieving labs, placing orders, checking vitals. None evaluate the specific reasoning pattern required for **payer-facing prior authorization**: reading a chart against externally-imposed, often non-obvious criteria (step therapy exceptions, setting-dependent exemptions, documentation staleness windows) and producing a decision or artifact (an auth determination or an appeal letter) that must be defensible if audited. This is a distinct skill from general EHR question-answering, and it's the skill oncology RCM analysts are actually hired for.

## 2. Environment construction

- **Server:** HAPI FHIR JPA server (R4), the standard open-source reference implementation, run via the included `docker-compose.yml`.
- **Patient population:** synthetic patients generated via Synthea, biased toward oncology modules (breast, colorectal, lung cancer) to ensure the resulting Condition/MedicationRequest/Observation resources are prior-auth-relevant.
- **Divergence from MedAgentBench:** MedAgentBench drew 100 patients from Stanford's real (de-identified) STARR warehouse via institutional data access. We do not have that access, and would not seek it for a project at this stage even if we could — Synthea data carries no PHI risk, which is the correct tradeoff for a benchmark intended to be published openly. The tradeoff is that synthetic charts are less messy/realistic than real ones; this should be stated as a limitation, not hidden.

## 3. Task design

- **Author:** currently one person (RCM/oncology billing background, ContractorCloud/PriorFlow founder), analogous to the domain-expert role physicians played for MedAgentBench.
- **Divergence:** MedAgentBench tasks were written/reviewed by multiple physicians, giving some inter-rater validation on task correctness. A solo-authored task bank has no such check. Until a second domain reviewer is brought in, tasks should be labeled `reviewed_by: 1` in metadata and the limitation stated plainly in any public write-up.
- **Design principle used:** paired positive/negative tasks per hard case (see `tasks/categories.md`), to reduce the chance an agent scores well by pattern-matching category → expected answer shape rather than actually reasoning from the chart.

## 4. Harness

- Custom lightweight controller (`harness/controller.py`) rather than reusing AgentBench, because AgentBench's abstractions are built around a broader set of environments (web browsing, OS interaction, etc.) that add complexity not needed here. This is a reasonable engineering simplification, not a corner cut on rigor.
- Scoring blends (a) tool-call trace match — did the agent query the FHIR resources a correct trajectory requires — and (b) final-answer correctness, so an agent can't score well by guessing without looking at the chart.

## 5. Known limitations (state these explicitly, don't bury them)

1. Solo-authored task bank — no inter-rater task validation yet.
2. Synthetic patient data — less noisy/realistic than a real clinical warehouse.
3. Payer policy text is illustrative/synthetic, not sourced from verified current real payer policy documents — do not cite specific numeric thresholds in this repo as representing any real payer's actual current criteria.
4. Answer scoring for `checklist`/`llm_rubric` tasks currently uses a naive keyword-match placeholder in `scorer.py` — needs either a human grading pass or a proper LLM-judge implementation before results are reported as final.
5. Small task count (12 seed tasks vs. MedAgentBench's 300) — treat any score on this version as a smoke test of the harness, not a claim about agent capability at large.

## 6. Suggested next steps toward a defensible v1

1. Get a second RCM/oncology billing professional (or a contracted oncologist) to independently review and score-check each task's reference solution.
2. Replace the keyword-match scorer with an LLM-judge call, itself validated against a human-graded sample.
3. Expand to 50-100 tasks once the above two are in place, maintaining the paired positive/negative discipline.
4. Run the reference Claude agent and your production PriorFlow agent side by side, publish both scores — a benchmark that only ever reports the author's own product's score is not credible as a benchmark.
5. Consider a short arXiv writeup once task count and review are solid — arXiv doesn't require institutional affiliation, and a well-executed niche benchmark is a legitimate research contribution and credibility asset independent of PriorFlow's commercial success.
