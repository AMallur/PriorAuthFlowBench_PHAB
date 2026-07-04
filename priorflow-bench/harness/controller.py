"""
Controller: the piece that plays the role AgentBench's controller played
for MedAgentBench. Loads the task bank, spins a fresh FHIRClient per task
(so call-trace logging doesn't bleed across tasks), invokes the agent
under test, and hands off to the scorer.

Usage:
    python controller.py --agent reference_claude --tasks ../tasks/task_bank.json
"""

from __future__ import annotations
import argparse
import json
import importlib
import time
from pathlib import Path

from fhir_client import FHIRClient
from scorer import score_task


AGENT_REGISTRY = {
    "reference_claude": ("agent_interface", "ReferenceClaudeAgent"),
    # register additional agents here, e.g.:
    # "priorflow_prod": ("priorflow_agent", "PriorFlowProductionAgent"),
}


def load_agent(name: str):
    if name not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent '{name}'. Registered: {list(AGENT_REGISTRY)}")
    module_name, class_name = AGENT_REGISTRY[name]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)()


def run(agent_name: str, tasks_path: str, fhir_base_url: str, out_path: str):
    agent = load_agent(agent_name)
    tasks = json.loads(Path(tasks_path).read_text())["tasks"]

    results = []
    for task in tasks:
        fhir = FHIRClient(base_url=fhir_base_url)
        start = time.time()
        try:
            agent_output = agent.run_task(
                instruction=task["instruction"],
                payer_context=task.get("payer_context", {}),
                fhir=fhir,
            )
            error = None
        except Exception as e:
            agent_output = {"answer": None}
            error = str(e)
        duration_s = time.time() - start

        trace = fhir.trace_as_strings()
        score = score_task(task, agent_output, trace)

        results.append({
            "task_id": task["id"],
            "category": task["category"],
            "difficulty": task["difficulty"],
            "agent_output": agent_output,
            "call_trace": trace,
            "duration_s": round(duration_s, 2),
            "error": error,
            **score,
        })
        print(f"[{task['id']}] score={score['total_score']:.2f} "
              f"(tool_trace={score['tool_trace_score']:.2f}, "
              f"answer={score['answer_score']:.2f})")

    Path(out_path).write_text(json.dumps(results, indent=2))

    overall = sum(r["total_score"] for r in results) / len(results) if results else 0.0
    print(f"\n=== Overall score: {overall:.3f} across {len(results)} tasks ===")
    by_cat: dict[str, list[float]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r["total_score"])
    for cat, scores in by_cat.items():
        print(f"  {cat}: {sum(scores)/len(scores):.3f} (n={len(scores)})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="reference_claude", choices=list(AGENT_REGISTRY))
    parser.add_argument("--tasks", default="../tasks/task_bank.json")
    parser.add_argument("--fhir-base-url", default="http://localhost:8080/fhir")
    parser.add_argument("--out", default="../eval_results/results.json")
    args = parser.parse_args()
    run(args.agent, args.tasks, args.fhir_base_url, args.out)
