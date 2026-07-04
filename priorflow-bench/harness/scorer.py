"""
Deterministic scoring for PriorFlow-Bench.

Total score per task = weighted blend of:
  (a) tool_trace_score  -- did the agent query the FHIR resources a
      correct trajectory requires? (fraction of required_calls resource
      types actually touched, order-insensitive)
  (b) answer_score      -- did the final answer satisfy the checklist /
      exact-match / rubric criteria for that task?

This mirrors the two things MedAgentBench actually needs to check: not
just "did the agent get the right answer" (which an agent could luck
into without looking at the chart) but "did it look at the right things
to get there."
"""

from __future__ import annotations
import re


def _resource_type_from_call(call: str) -> str | None:
    # "GET /Condition?patient=..." -> "Condition"
    m = re.search(r"/([A-Za-z]+)(\?|/|$)", call)
    return m.group(1) if m else None


def score_tool_trace(task: dict, actual_trace: list[str]) -> float:
    required_resources = set(task.get("required_fhir_resources", []))
    if not required_resources:
        return 1.0  # nothing to check
    touched = {_resource_type_from_call(c) for c in actual_trace}
    touched.discard(None)
    hit = required_resources & touched
    return len(hit) / len(required_resources)


def score_answer(task: dict, agent_output: dict) -> float:
    """
    NOTE: the 'checklist' and 'exact_match' methods below are simple,
    deterministic, keyword/structure-based stand-ins. For a real v1 you'd
    likely want a human-in-the-loop review pass on top of these (or an
    LLM-judge call for the 'llm_rubric' tasks) rather than trusting a
    keyword match alone -- flagging this explicitly rather than pretending
    naive string matching is a rigorous grader.
    """
    scoring = task["scoring"]
    method = scoring["method"]
    answer = agent_output.get("answer")

    if answer is None:
        return 0.0

    if method == "exact_match":
        return 1.0 if answer == task["reference_solution"]["answer"] else 0.0

    if method in ("checklist", "llm_rubric"):
        checklist = scoring.get("checklist", [])
        if not checklist:
            return 0.0
        answer_str = str(answer).lower()
        # naive heuristic placeholder: counts checklist items whose key
        # nouns appear in the answer. Replace with an LLM-judge call
        # (grading answer_str against each checklist item) for real use --
        # left as a clearly-marked TODO rather than dressed up as final.
        hits = 0
        for item in checklist:
            keywords = [w.lower() for w in re.findall(r"[a-zA-Z]{4,}", item)][:3]
            if any(k in answer_str for k in keywords):
                hits += 1
        return hits / len(checklist)

    raise ValueError(f"Unknown scoring method: {method}")


def score_task(task: dict, agent_output: dict, actual_trace: list[str]) -> dict:
    weight_trace = task["scoring"].get("weight_tool_trace", 0.3)
    tool_trace_score = score_tool_trace(task, actual_trace)
    answer_score = score_answer(task, agent_output)
    total = weight_trace * tool_trace_score + (1 - weight_trace) * answer_score
    return {
        "tool_trace_score": round(tool_trace_score, 3),
        "answer_score": round(answer_score, 3),
        "total_score": round(total, 3),
    }
