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
import json
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


_JUDGE_TOOL = {
    "name": "grade_checklist",
    "description": "Record a pass/fail verdict for each checklist item against the agent's answer.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item": {"type": "string", "description": "The exact checklist item text being graded."},
                        "met": {"type": "boolean"},
                        "reason": {"type": "string", "description": "One sentence: why met/not met."},
                    },
                    "required": ["item", "met", "reason"],
                },
            }
        },
        "required": ["verdicts"],
    },
}

_JUDGE_SYSTEM_PROMPT = (
    "You are grading a prior-authorization agent's answer against a checklist of "
    "required elements, using the reference (ground-truth) solution as the source "
    "of truth for what's clinically/administratively correct. For each checklist "
    "item, decide whether the agent's answer clearly and correctly satisfies it. "
    "Be strict: do not give credit for vague or hedged language that happens to "
    "contain the right keywords, and do not give credit for a claim that "
    "contradicts the reference solution. Call grade_checklist with one verdict "
    "per checklist item, in the same order given."
)


def llm_judge_checklist(
    checklist: list[str],
    agent_answer,
    reference_solution: dict,
    client=None,
    model: str = "claude-sonnet-4-6",
) -> list[dict]:
    """
    Grades agent_answer against each checklist item with an LLM judge and
    returns a list of {"item", "met", "reason"} dicts, one per checklist
    item. `client` is an anthropic.Anthropic-compatible object (injectable
    for testing); if omitted, a default client is constructed, which
    requires ANTHROPIC_API_KEY to be set in the environment.
    """
    if not checklist:
        return []

    if client is None:
        import anthropic
        client = anthropic.Anthropic()

    user_prompt = (
        f"Reference (ground-truth) solution:\n{json.dumps(reference_solution, indent=2)}\n\n"
        f"Agent's answer:\n{json.dumps(agent_answer, indent=2)}\n\n"
        "Checklist items to grade (grade every one, in order):\n"
        + "\n".join(f"{i + 1}. {item}" for i, item in enumerate(checklist))
    )

    resp = client.messages.create(
        model=model,
        max_tokens=1536,
        system=_JUDGE_SYSTEM_PROMPT,
        tools=[_JUDGE_TOOL],
        tool_choice={"type": "tool", "name": "grade_checklist"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "grade_checklist":
            verdicts = block.input.get("verdicts", [])
            if len(verdicts) != len(checklist):
                raise ValueError(
                    f"LLM judge returned {len(verdicts)} verdicts for {len(checklist)} checklist items"
                )
            return verdicts

    raise RuntimeError("LLM judge did not return a grade_checklist tool call")


def score_answer(task: dict, agent_output: dict, judge_client=None) -> float:
    """
    'exact_match' is graded deterministically (structural equality against
    the reference answer). 'checklist' and 'llm_rubric' are graded by an
    LLM judge scoring each checklist item against the reference solution --
    replacing the previous keyword-match placeholder, which could be
    satisfied by an answer that merely repeated checklist nouns without
    actually getting the determination right.
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
        verdicts = llm_judge_checklist(
            checklist, answer, task["reference_solution"], client=judge_client
        )
        if not verdicts:
            return 0.0
        met = sum(1 for v in verdicts if v.get("met"))
        return met / len(checklist)

    raise ValueError(f"Unknown scoring method: {method}")


def score_task(task: dict, agent_output: dict, actual_trace: list[str], judge_client=None) -> dict:
    weight_trace = task["scoring"].get("weight_tool_trace", 0.3)
    tool_trace_score = score_tool_trace(task, actual_trace)
    answer_score = score_answer(task, agent_output, judge_client=judge_client)
    total = weight_trace * tool_trace_score + (1 - weight_trace) * answer_score
    return {
        "tool_trace_score": round(tool_trace_score, 3),
        "answer_score": round(answer_score, 3),
        "total_score": round(total, 3),
    }
