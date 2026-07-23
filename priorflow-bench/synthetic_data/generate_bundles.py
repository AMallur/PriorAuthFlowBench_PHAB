"""
Generate one FHIR transaction Bundle per synthetic patient referenced in
tasks/task_bank.json, from the declarative facts in patient_specs.py.

Usage:
    cd priorflow-bench/synthetic_data
    python generate_bundles.py

Writes bundles/<patient_ref>.json for every patient_ref in PATIENT_BUILDERS.
Run this shortly before loading into the FHIR server / running an eval --
several tasks encode relative-time facts (e.g. "labs 41 days old", "ECOG
from last week") that are computed from the generation date, not fixed
calendar dates, and will drift as real time passes since generation.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from fhir_resources import transaction_bundle
from patient_specs import PATIENT_BUILDERS

OUTPUT_DIR = Path(__file__).parent / "bundles"


def main():
    today = date.today()
    OUTPUT_DIR.mkdir(exist_ok=True)
    for patient_ref, build in PATIENT_BUILDERS.items():
        resources = build(today)
        bundle = transaction_bundle(resources)
        out_path = OUTPUT_DIR / f"{patient_ref}.json"
        out_path.write_text(json.dumps(bundle, indent=2))
        print(f"wrote {out_path} ({len(resources)} resources)")
    print(f"\nGenerated {len(PATIENT_BUILDERS)} patient bundles, dated relative to {today.isoformat()}.")


if __name__ == "__main__":
    main()
