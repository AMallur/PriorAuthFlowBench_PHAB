"""
Validates that the generated synthetic patient bundles actually back up
what tasks/task_bank.json claims about each chart -- this is the check
that catches "task says X, but nobody ever put X in the patient's FHIR
data" bugs, which schema validation alone can't catch.

Run from priorflow-bench/: pytest tests/test_patient_data_consistency.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "synthetic_data"))

from generate_bundles import main as generate_bundles_main  # noqa: E402

TASK_BANK_PATH = REPO_ROOT / "tasks" / "task_bank.json"
BUNDLES_DIR = REPO_ROOT / "synthetic_data" / "bundles"

# Tasks whose reference_solution depends on a resource type being ABSENT
# from the chart (not present), so the generic "every required resource
# type must appear" check would be wrong for these specific types.
EXPECTED_ABSENT_RESOURCE_CONTENT = {
    # (task_id, resource_type): substring that must NOT appear anywhere
    # in that resource type's entries for this patient.
    ("pab_003", "Observation"): "ECOG",
    ("pab_008", "Observation"): "BRAF",
    ("pab_012", "Observation"): "biosimilar",
    ("pab_018", "MedicationRequest"): "",  # no MedicationRequest at all expected
}

# Spot-check keyword assertions for the genomic biomarker category (and a
# few of the trickiest pre-existing "confirmed absence" tasks) -- these
# are the facts a domain reviewer should be able to scan against the
# reference_solution and agree are actually encoded in the chart.
MUST_CONTAIN = {
    "pab_013": ["NTRK3", "fusion"],
    "pab_014": ["NTRK1", "point mutation"],
    "pab_015": ["MLH1", "PMS2"],
    "pab_016": ["Microsatellite stable"],
    "pab_017": ["G12C"],
    "pab_018": ["G12D"],
    "pab_019": ["exon 20 insertion"],
    "pab_020": ["exon 19 deletion"],
    "pab_021": ["pathogenic variant"],
    "pab_022": ["variant of uncertain significance"],
}

MUST_NOT_CONTAIN = {
    "pab_013": ["point mutation"],
    "pab_014": ["fusion detected", "fusion positive"],  # "no fusion transcript identified" is expected text
    "pab_017": ["G12D"],
    "pab_018": ["G12C"],
    "pab_019": ["exon 19 deletion"],
    "pab_020": ["exon 20 insertion"],
    "pab_021": ["uncertain significance"],
    "pab_022": ["pathogenic variant detected"],
}


@pytest.fixture(scope="module", autouse=True)
def generated_bundles():
    generate_bundles_main()


@pytest.fixture(scope="module")
def tasks():
    return json.loads(TASK_BANK_PATH.read_text())["tasks"]


def _load_bundle(patient_ref: str) -> dict:
    path = BUNDLES_DIR / f"{patient_ref}.json"
    assert path.exists(), f"missing generated bundle for {patient_ref}"
    return json.loads(path.read_text())


def _resources_by_type(bundle: dict) -> dict[str, list[dict]]:
    by_type: dict[str, list[dict]] = {}
    for entry in bundle["entry"]:
        res = entry["resource"]
        by_type.setdefault(res["resourceType"], []).append(res)
    return by_type


def _bundle_text(bundle: dict) -> str:
    return json.dumps(bundle)


def test_every_task_has_a_bundle(tasks):
    for task in tasks:
        _load_bundle(task["patient_ref"])  # raises if missing


def test_required_resource_types_present(tasks):
    """Every FHIR resource type a task lists as required actually exists
    in that patient's bundle, unless it's a documented absence case."""
    missing = []
    for task in tasks:
        bundle = _load_bundle(task["patient_ref"])
        by_type = _resources_by_type(bundle)
        for rtype in task.get("required_fhir_resources", []):
            key = (task["id"], rtype)
            if key in EXPECTED_ABSENT_RESOURCE_CONTENT:
                continue  # deliberately absent/empty for this task
            if rtype not in by_type:
                missing.append(f"{task['id']}: expected {rtype} not found in {task['patient_ref']}")
    assert not missing, "\n" + "\n".join(missing)


def test_documented_absences_are_actually_absent(tasks):
    by_id = {t["id"]: t for t in tasks}
    failures = []
    for (task_id, rtype), forbidden in EXPECTED_ABSENT_RESOURCE_CONTENT.items():
        task = by_id[task_id]
        bundle = _load_bundle(task["patient_ref"])
        by_type = _resources_by_type(bundle)
        entries = by_type.get(rtype, [])
        if forbidden == "":
            if entries:
                failures.append(f"{task_id}: expected no {rtype} resources, found {len(entries)}")
        else:
            text = json.dumps(entries)
            if forbidden.lower() in text.lower():
                failures.append(f"{task_id}: found forbidden term '{forbidden}' in {rtype} entries")
    assert not failures, "\n" + "\n".join(failures)


def test_genomic_and_spot_check_keywords(tasks):
    by_id = {t["id"]: t for t in tasks}
    failures = []
    for task_id, keywords in MUST_CONTAIN.items():
        bundle = _load_bundle(by_id[task_id]["patient_ref"])
        text = _bundle_text(bundle).lower()
        for kw in keywords:
            if kw.lower() not in text:
                failures.append(f"{task_id}: expected keyword '{kw}' not found in chart")
    for task_id, keywords in MUST_NOT_CONTAIN.items():
        bundle = _load_bundle(by_id[task_id]["patient_ref"])
        text = _bundle_text(bundle).lower()
        for kw in keywords:
            if kw.lower() in text:
                failures.append(f"{task_id}: forbidden keyword '{kw}' found in chart")
    assert not failures, "\n" + "\n".join(failures)


def test_bundles_are_valid_fhir_transaction_shape():
    for path in BUNDLES_DIR.glob("*.json"):
        bundle = json.loads(path.read_text())
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "transaction"
        for entry in bundle["entry"]:
            assert "resource" in entry
            assert "request" in entry
            assert entry["request"]["method"] == "PUT"
            res = entry["resource"]
            assert "resourceType" in res and "id" in res
            assert entry["request"]["url"] == f"{res['resourceType']}/{res['id']}"
