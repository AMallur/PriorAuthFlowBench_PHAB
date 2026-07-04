# PriorFlow-Bench: A Realistic Virtual Payer/EHR Environment to Benchmark Oncology Prior Authorization Agents

**Status:** v0.1 scaffold — pre-registration draft
**Author:** Ashy (solo founder, PriorFlow) — domain background: oncology RCM / infusion billing
**Inspired by methodology in:** Jiang et al., *MedAgentBench: A Realistic Virtual EHR Environment to Benchmark Medical LLM Agents*, NEJM AI (Stanford ML Group)

---

## 1. What this is

PriorFlow-Bench is a benchmark — not a product demo — for evaluating whether an LLM agent can correctly perform the judgment-heavy parts of oncology infusion prior authorization: reading a chart, determining whether prior auth is required, checking payer-specific medical necessity criteria, identifying missing documentation, and drafting a defensible clinical justification.

It follows the same three-layer structure MedAgentBench uses:

| Layer | MedAgentBench | PriorFlow-Bench |
|---|---|---|
| **Environment** | Dockerized FHIR server, 100 synthetic patients from STARR | Dockerized FHIR server, synthetic oncology patients from Synthea |
| **Tasks** | 300 physician-written instructions | 30+ RCM/billing-expert-written prior-auth tasks (seeded here, expand over time) |
| **Harness** | AgentBench controller + task workers | Custom lightweight controller + task workers (`harness/`) |

The reason this structure matters: a benchmark is only credible if (a) the environment is realistic enough that passing means something, (b) the tasks were written by someone with real domain judgment (this is where your RCM background *is* the moat — same role physicians played for MedAgentBench), and (c) scoring is deterministic/reproducible, not vibes-based.

## 2. Repo layout

```
priorflow-bench/
├── README.md                  # this file
├── docker-compose.yml         # HAPI FHIR JPA server (the "virtual EHR")
├── requirements.txt
├── scripts/
│   └── generate_synthetic_patients.sh   # Synthea invocation w/ oncology modules
├── tasks/
│   ├── schema.json             # JSON Schema all tasks must validate against
│   ├── task_bank.json           # the actual task set (12 seed tasks, 4 categories)
│   └── categories.md            # task taxonomy + how to write new tasks
├── harness/
│   ├── fhir_client.py           # thin FHIR REST wrapper that LOGS every call
│   ├── agent_interface.py       # abstract Agent + a reference Claude-based agent
│   ├── controller.py            # runs task set against an agent, saves transcripts
│   └── scorer.py                # deterministic scoring: tool-call match + checklist
├── docs/
│   └── METHODOLOGY.md           # paper-style write-up: data, task design, limitations
└── eval_results/                # output transcripts + score reports land here
```

## 3. Quickstart

```bash
# 1. Stand up the virtual EHR
docker compose up -d

# 2. Generate synthetic oncology patients (requires Java + Synthea jar, see scripts/)
bash scripts/generate_synthetic_patients.sh

# 3. Load patients into the FHIR server (script prints the upload command)

# 4. Run the eval
pip install -r requirements.txt
python harness/controller.py --agent reference_claude_agent --tasks tasks/task_bank.json
```

## 4. Why this is worth doing (beyond an internal eval)

An internal "does my agent work" test is worth something to you. A published, versioned, reproducible benchmark repo is worth something to everyone evaluating whether *any* prior-auth agent — yours or a competitor's — actually works. That's the leverage MedAgentBench has: it's cited by everyone building medical agents afterward, because it's the yardstick. Same play here, scoped to oncology infusion prior auth, is a credibility asset for PriorFlow outreach and a genuine (small, honest) research contribution if written up and posted (e.g., arXiv preprint doesn't require institutional affiliation).

## 5. What's honest about the scope right now

- 12 seed tasks, not 300. MedAgentBench had a research team + physicians; you're one person. Task count should grow slowly and only with real domain rigor, not padded for volume.
- Synthea data, not a real data warehouse. This is the correct and only responsible substitute without an IRB/DUA — do not attempt to source real PHI for this.
- No inter-rater reliability step yet (MedAgentBench likely had multiple physicians cross-check tasks). Solo, note this explicitly as a limitation rather than skip mentioning it.
