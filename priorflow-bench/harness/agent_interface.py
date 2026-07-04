"""
Agent interface for PriorFlow-Bench.

Any agent under evaluation — your production PriorFlow agent, a baseline
Claude tool-calling agent, or a competitor's system — implements `Agent`
below. This mirrors how AgentBench decouples "the environment/tasks" from
"the thing being evaluated," which is what let MedAgentBench benchmark
multiple different LLMs against the same task set.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
import json
import os

from fhir_client import FHIRClient


class Agent(ABC):
    @abstractmethod
    def run_task(self, instruction: str, payer_context: dict, fhir: FHIRClient) -> dict:
        """
        Given a task instruction and payer context, use `fhir` to gather
        whatever evidence is needed, then return a structured answer dict.
        The FHIRClient passed in is fresh (empty call log) for this task,
        so fhir.trace_as_strings() after this call reflects only this task's
        queries.
        """
        raise NotImplementedError


class ReferenceClaudeAgent(Agent):
    """
    A minimal, honest reference implementation: gives Claude a small tool
    belt of FHIR search calls and lets it decide what to query. This is
    intentionally NOT PriorFlow's actual production agent — it's a baseline
    so the benchmark can report a credible "here's what a generic tool-
    calling agent scores" number alongside your product's number, exactly
    the way MedAgentBench reports multiple baseline LLMs rather than only
    the authors' preferred model.
    """

    TOOLS = [
        {
            "name": "fhir_search",
            "description": "Search FHIR resources. Use resource_type (e.g. 'Condition', 'Observation', 'MedicationRequest', 'DiagnosticReport', 'Coverage', 'Encounter', 'Procedure') and params (dict of query params, typically at least {'patient': <id>}).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "resource_type": {"type": "string"},
                    "params": {"type": "object"}
                },
                "required": ["resource_type", "params"]
            }
        },
        {
            "name": "submit_answer",
            "description": "Submit your final structured answer once you have gathered sufficient evidence.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "object"}
                },
                "required": ["answer"]
            }
        }
    ]

    def __init__(self, model: str = "claude-sonnet-4-6", max_turns: int = 8):
        self.model = model
        self.max_turns = max_turns

    def run_task(self, instruction: str, payer_context: dict, fhir: FHIRClient) -> dict:
        import anthropic
        client = anthropic.Anthropic()

        system = (
            "You are a prior-authorization review agent for oncology infusion "
            "therapy. You will be given an instruction and the relevant payer "
            "policy text. Use the fhir_search tool to gather exactly the "
            "evidence needed from the patient's chart, then call submit_answer "
            "with a structured JSON answer. Do not claim a criterion is met "
            "unless you have directly observed evidence for it in a FHIR "
            "resource you queried. If evidence is missing or ambiguous, say so "
            "explicitly rather than guessing."
        )
        user_msg = (
            f"Payer policy context: {json.dumps(payer_context)}\n\n"
            f"Task: {instruction}\n\n"
            f"Patient FHIR id: (use the patient param already scoped for this task)"
        )

        messages = [{"role": "user", "content": user_msg}]

        for _ in range(self.max_turns):
            resp = client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system,
                tools=self.TOOLS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": resp.content})

            tool_use_blocks = [b for b in resp.content if b.type == "tool_use"]
            if not tool_use_blocks:
                # Model didn't call a tool and didn't submit -- treat as
                # a failed/incomplete task rather than guessing at intent.
                return {"answer": None, "error": "agent_did_not_submit_answer"}

            tool_results = []
            submitted = None
            for block in tool_use_blocks:
                if block.name == "submit_answer":
                    submitted = block.input.get("answer")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "answer recorded"
                    })
                elif block.name == "fhir_search":
                    try:
                        result = fhir.search(block.input["resource_type"], **block.input.get("params", {}))
                        content = json.dumps(result)[:4000]  # keep transcript bounded
                    except Exception as e:
                        content = f"ERROR: {e}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": content
                    })

            if submitted is not None:
                return {"answer": submitted}

            messages.append({"role": "user", "content": tool_results})

        return {"answer": None, "error": "max_turns_exceeded"}
