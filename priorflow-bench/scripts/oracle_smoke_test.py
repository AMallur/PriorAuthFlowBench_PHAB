"""
Live-server smoke test for the PriorFlow-Bench harness -- NOT an agent
capability benchmark.

This runs an "oracle" stand-in agent that queries a live FHIR server for
each task's required resources and then submits the literal
reference_solution answer verbatim. It exists to answer one narrow
question: "does the FHIR server + FHIRClient + scorer pipeline actually
work end-to-end against live data," independent of whether any real LLM
agent is available to call.

Because the submitted answer IS the ground truth, the LLM-judge step is
replaced with a stub that marks every checklist item met by construction
-- this validates the scoring *plumbing*, not grading quality. Use
harness/controller.py with a real agent and a real ANTHROPIC_API_KEY for
an actual capability run.

Usage (from priorflow-bench/, with the FHIR server up and task-bank
patients loaded -- see scripts/load_task_bank_patients.sh):
    python scripts/oracle_smoke_test.py [fhir_base_url]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))

from fhir_client import FHIRClient  # noqa: E402
from scorer import score_task  # noqa: E402

TASK_BANK_PATH = REPO_ROOT / "tasks" / "task_bank.json"


class OracleJudgeClient:
    """Stub LLM-judge client: every checklist item is marked met, since the
    'agent answer' fed into scoring is the literal reference solution."""

    class _Messages:
        def create(self, **kwargs):
            prompt = kwargs["messages"][0]["content"]
            items = re.findall(r"^\d+\. (.+)$", prompt, re.MULTILINE)
            verdicts = [
                {"item": item, "met": True, "reason": "oracle answer satisfies by construction"}
                for item in items
            ]
            block = SimpleNamespace(type="tool_use", name="grade_checklist", input={"verdicts": verdicts})
            return SimpleNamespace(content=[block])

    def __init__(self):
        self.messages = self._Messages()


def run(fhir_base_url: str) -> list[dict]:
    tasks = json.loads(TASK_BANK_PATH.read_text())["tasks"]
    judge = OracleJudgeClient()
    results = []

    for task in tasks:
        fhir = FHIRClient(base_url=fhir_base_url)
        for rtype in task.get("required_fhir_resources", []):
            if rtype == "Patient":
                fhir.get_patient(task["patient_ref"])
            else:
                fhir.search(rtype, patient=task["patient_ref"])

        agent_output = {"answer": task["reference_solution"]["answer"]}
        trace = fhir.trace_as_strings()
        score = score_task(task, agent_output, trace, judge_client=judge)
        results.append({"task_id": task["id"], "category": task["category"], **score})
        print(f"[{task['id']}] score={score['total_score']:.2f} "
              f"(tool_trace={score['tool_trace_score']:.2f}, answer={score['answer_score']:.2f})")

    overall = sum(r["total_score"] for r in results) / len(results) if results else 0.0
    print(f"\n=== Oracle smoke-test overall score: {overall:.3f} across {len(results)} tasks ===")
    print("(A score below 1.0 means either a live FHIR query failed, or a task's")
    print(" required_fhir_resources/reference_solution no longer match the loaded chart data.)")
    return results


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/fhir"
    results = run(base_url)
    out_path = REPO_ROOT / "eval_results" / "oracle_smoke_test.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
