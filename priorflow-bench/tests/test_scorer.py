"""
Tests for harness/scorer.py, including the LLM-judge checklist grader.

The judge tests use a fake Anthropic-compatible client (no network call,
no API key needed) so they can run in any environment -- they check that
scorer.py wires the request/response correctly, not that a real model
grades well.

Run from priorflow-bench/: pytest tests/test_scorer.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "harness"))

from scorer import llm_judge_checklist, score_answer, score_task, score_tool_trace  # noqa: E402


class FakeToolUseBlock:
    def __init__(self, name, input_):
        self.type = "tool_use"
        self.name = name
        self.input = input_


class FakeMessagesAPI:
    """Records the last request and returns a pre-programmed verdicts list."""

    def __init__(self, verdicts):
        self._verdicts = verdicts
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        block = FakeToolUseBlock("grade_checklist", {"verdicts": self._verdicts})
        return SimpleNamespace(content=[block])


class FakeAnthropicClient:
    def __init__(self, verdicts):
        self.messages = FakeMessagesAPI(verdicts)


SAMPLE_TASK = {
    "id": "pab_099",
    "reference_solution": {"answer": {"meets_criteria": False, "basis": "VUS does not qualify"}},
    "scoring": {
        "method": "checklist",
        "checklist": [
            "correctly denies criteria are met",
            "explicitly names VUS as the reason",
        ],
        "weight_tool_trace": 0.25,
    },
    "required_fhir_resources": ["DiagnosticReport", "Condition"],
}


def _verdict(item, met, reason="because"):
    return {"item": item, "met": met, "reason": reason}


def test_llm_judge_checklist_all_met_returns_full_verdicts():
    checklist = ["a", "b", "c"]
    client = FakeAnthropicClient([_verdict("a", True), _verdict("b", True), _verdict("c", False)])
    verdicts = llm_judge_checklist(checklist, {"answer": "x"}, {"answer": "y"}, client=client)
    assert len(verdicts) == 3
    assert [v["met"] for v in verdicts] == [True, True, False]
    # sanity: the prompt actually included every checklist item
    prompt = client.messages.last_call_kwargs["messages"][0]["content"]
    assert "a" in prompt and "b" in prompt and "c" in prompt
    assert client.messages.last_call_kwargs["tool_choice"] == {"type": "tool", "name": "grade_checklist"}


def test_llm_judge_checklist_empty_checklist_short_circuits_without_calling_client():
    client = FakeAnthropicClient([])
    verdicts = llm_judge_checklist([], {"answer": "x"}, {"answer": "y"}, client=client)
    assert verdicts == []
    assert client.messages.last_call_kwargs is None  # never called


def test_llm_judge_checklist_mismatched_verdict_count_raises():
    client = FakeAnthropicClient([_verdict("a", True)])  # only 1 verdict for 2 items
    with pytest.raises(ValueError):
        llm_judge_checklist(["a", "b"], {"answer": "x"}, {"answer": "y"}, client=client)


def test_score_answer_checklist_uses_judge_and_averages_verdicts():
    client = FakeAnthropicClient([_verdict("item1", True), _verdict("item2", False)])
    task = {**SAMPLE_TASK, "scoring": {**SAMPLE_TASK["scoring"], "checklist": ["item1", "item2"]}}
    score = score_answer(task, {"answer": {"meets_criteria": False}}, judge_client=client)
    assert score == pytest.approx(0.5)


def test_score_answer_no_answer_scores_zero_without_calling_judge():
    client = FakeAnthropicClient([_verdict("item1", True)])
    score = score_answer(SAMPLE_TASK, {"answer": None}, judge_client=client)
    assert score == 0.0
    assert client.messages.last_call_kwargs is None


def test_score_answer_exact_match_does_not_invoke_judge():
    client = FakeAnthropicClient([])
    task = {
        "scoring": {"method": "exact_match"},
        "reference_solution": {"answer": {"x": 1}},
    }
    assert score_answer(task, {"answer": {"x": 1}}, judge_client=client) == 1.0
    assert score_answer(task, {"answer": {"x": 2}}, judge_client=client) == 0.0
    assert client.messages.last_call_kwargs is None


def test_score_tool_trace_fraction_of_required_resources_touched():
    task = {"required_fhir_resources": ["Condition", "Observation", "MedicationRequest"]}
    trace = ["GET /Condition?patient=p1", "GET /Observation?patient=p1"]
    assert score_tool_trace(task, trace) == pytest.approx(2 / 3)


def test_score_tool_trace_no_required_resources_scores_full():
    assert score_tool_trace({"required_fhir_resources": []}, []) == 1.0


def test_score_task_blends_trace_and_answer_scores():
    client = FakeAnthropicClient([_verdict("a", True), _verdict("b", True)])
    task = {
        "required_fhir_resources": ["Condition", "Observation"],
        "reference_solution": {"answer": {"x": 1}},
        "scoring": {"method": "checklist", "checklist": ["a", "b"], "weight_tool_trace": 0.4},
    }
    trace = ["GET /Condition?patient=p1"]  # 1 of 2 required -> tool_trace_score 0.5
    result = score_task(task, {"answer": {"x": 1}}, trace, judge_client=client)
    assert result["tool_trace_score"] == 0.5
    assert result["answer_score"] == 1.0
    assert result["total_score"] == pytest.approx(0.4 * 0.5 + 0.6 * 1.0)
