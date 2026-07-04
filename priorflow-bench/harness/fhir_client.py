"""
Thin wrapper around the FHIR REST API that transparently logs every call.

This is the piece that makes tool-trace scoring possible: the scorer needs
to know exactly which FHIR resources the agent actually queried, not just
what final answer it gave. Any agent implementation (yours, a baseline
Claude tool-calling agent, a competitor's) should be routed through this
client rather than calling `requests` directly, so every submission is
scored on the same instrumentation.
"""

from __future__ import annotations
import time
import requests
from dataclasses import dataclass, field


@dataclass
class CallLogEntry:
    method: str
    path: str
    status_code: int
    duration_ms: float


class FHIRClient:
    def __init__(self, base_url: str = "http://localhost:8080/fhir"):
        self.base_url = base_url.rstrip("/")
        self.call_log: list[CallLogEntry] = field(default_factory=list)
        self.call_log = []

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        start = time.time()
        resp = requests.request(method, url, timeout=15, **kwargs)
        duration_ms = (time.time() - start) * 1000
        self.call_log.append(CallLogEntry(method=method, path=path,
                                           status_code=resp.status_code,
                                           duration_ms=duration_ms))
        resp.raise_for_status()
        return resp.json()

    # --- Convenience methods the agent/tool layer calls ---

    def get_patient(self, patient_id: str) -> dict:
        return self._request("GET", f"Patient/{patient_id}")

    def search(self, resource_type: str, **params) -> dict:
        """
        Generic FHIR search, e.g. client.search("Condition", patient="example-patient-001")
        Returns the raw FHIR Bundle.
        """
        query = "&".join(f"{k}={v}" for k, v in params.items())
        path = f"{resource_type}?{query}" if query else resource_type
        return self._request("GET", path)

    def reset_log(self):
        self.call_log = []

    def trace_as_strings(self) -> list[str]:
        """Returns call log in the same 'METHOD /path' format used in
        tasks/task_bank.json required_calls, for direct comparison."""
        return [f"{c.method} /{c.path.lstrip('/')}" for c in self.call_log]
