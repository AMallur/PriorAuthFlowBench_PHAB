"""
Minimal FHIR R4 resource builders used to generate PriorFlow-Bench's
synthetic patient charts (see generate_bundles.py and patient_specs.py).

These are deliberately bare-bones -- just enough structure (resourceType,
status, subject, code.text, a date, a value/conclusion) for the FHIR search
queries in tasks/task_bank.json to find them and for a human reviewer to
read the clinical content directly off the JSON. This is not meant to be a
realistic full EHR export.
"""

from __future__ import annotations


def patient(pid: str, name: str, birth_date: str) -> dict:
    return {
        "resourceType": "Patient",
        "id": pid,
        "name": [{"text": name}],
        "gender": "unknown",
        "birthDate": birth_date,
    }


def condition(pid: str, res_id: str, text: str, recorded_date: str,
              clinical_status: str = "active", stage_text: str | None = None) -> dict:
    res = {
        "resourceType": "Condition",
        "id": res_id,
        "subject": {"reference": f"Patient/{pid}"},
        "code": {"text": text},
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": clinical_status,
            }]
        },
        "recordedDate": recorded_date,
    }
    if stage_text:
        res["stage"] = [{"summary": {"text": stage_text}}]
    return res


def observation(pid: str, res_id: str, text: str, effective_date: str,
                value_text: str, category: str = "laboratory",
                encounter_id: str | None = None) -> dict:
    res = {
        "resourceType": "Observation",
        "id": res_id,
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": category,
            }]
        }],
        "code": {"text": text},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": effective_date,
        "valueString": value_text,
    }
    if encounter_id:
        res["encounter"] = {"reference": f"Encounter/{encounter_id}"}
    return res


def diagnostic_report(pid: str, res_id: str, text: str, effective_date: str,
                       conclusion: str) -> dict:
    return {
        "resourceType": "DiagnosticReport",
        "id": res_id,
        "status": "final",
        "code": {"text": text},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": effective_date,
        "conclusion": conclusion,
    }


def medication_request(pid: str, res_id: str, medication_text: str,
                        status: str, intent: str, authored_on: str,
                        encounter_id: str | None = None,
                        note: str | None = None) -> dict:
    res = {
        "resourceType": "MedicationRequest",
        "id": res_id,
        "status": status,
        "intent": intent,
        "medicationCodeableConcept": {"text": medication_text},
        "subject": {"reference": f"Patient/{pid}"},
        "authoredOn": authored_on,
    }
    if encounter_id:
        res["encounter"] = {"reference": f"Encounter/{encounter_id}"}
    if note:
        res["note"] = [{"text": note}]
    return res


def coverage(pid: str, res_id: str, payer_name: str, plan_id: str) -> dict:
    return {
        "resourceType": "Coverage",
        "id": res_id,
        "status": "active",
        "beneficiary": {"reference": f"Patient/{pid}"},
        "payor": [{"display": payer_name}],
        "class": [{"type": {"text": "plan"}, "value": plan_id, "name": payer_name}],
    }


def encounter(pid: str, res_id: str, class_code: str, class_display: str,
              period_start: str, period_end: str | None, status: str,
              reason_text: str | None = None) -> dict:
    period = {"start": period_start}
    if period_end:
        period["end"] = period_end
    res = {
        "resourceType": "Encounter",
        "id": res_id,
        "status": status,
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": class_code,
            "display": class_display,
        },
        "subject": {"reference": f"Patient/{pid}"},
        "period": period,
    }
    if reason_text:
        res["reasonCode"] = [{"text": reason_text}]
    return res


def procedure(pid: str, res_id: str, text: str, performed_date: str) -> dict:
    return {
        "resourceType": "Procedure",
        "id": res_id,
        "status": "completed",
        "code": {"text": text},
        "subject": {"reference": f"Patient/{pid}"},
        "performedDateTime": performed_date,
    }


def transaction_bundle(resources: list[dict]) -> dict:
    """Wrap a list of resources into a FHIR transaction Bundle that PUTs
    each resource at its own id -- idempotent to (re)load."""
    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": r,
                "request": {"method": "PUT", "url": f"{r['resourceType']}/{r['id']}"},
            }
            for r in resources
        ],
    }
