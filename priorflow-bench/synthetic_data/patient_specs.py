"""
Declarative clinical facts for each PriorFlow-Bench synthetic patient.

Each entry in PATIENT_BUILDERS is a function of `today` (a datetime.date)
that returns the list of FHIR resources for that patient. Dates are
expressed relative to `today` because several tasks hinge on a specific
time window (e.g. "labs within the last 30 days", "ECOG from last week",
"discharged yesterday") -- see the `days_ago`/`days_from_now` helpers.

IMPORTANT: these bundles must be regenerated close to when the benchmark
is actually run (see generate_bundles.py), or relative-date facts like
"labs 41 days old" will silently drift as real time passes. This mirrors
the same fact each task's rationale already states in words; the dates
here just make it concrete and machine-checkable.

RCM/domain review needed: the clinical content below (drug names, test
names, result phrasing) is written to make each task_bank.json task's
reference_solution verifiably true against the chart. It has not yet had
the second-reviewer pass called for in tasks/categories.md and
docs/METHODOLOGY.md -- treat it the same as the task bank itself: a
reviewed-by-1 draft, not a final clinical artifact.
"""

from __future__ import annotations

from datetime import date, timedelta

from fhir_resources import (
    condition,
    coverage,
    diagnostic_report,
    encounter,
    medication_request,
    observation,
    patient,
    procedure,
)


def _iso(d: date) -> str:
    return d.isoformat()


def days_ago(today: date, n: int) -> str:
    return _iso(today - timedelta(days=n))


def days_from_now(today: date, n: int) -> str:
    return _iso(today + timedelta(days=n))


def _pab_001(today):
    pid = "example-patient-001"
    return [
        patient(pid, "Synthetic Patient 001", "1968-03-14"),
        coverage(pid, f"{pid}-cov-1", "SyntheticPayer Commercial PPO", "ONC-INFUSION-001"),
        medication_request(
            pid, f"{pid}-medreq-1", "Pembrolizumab", status="active", intent="order",
            authored_on=days_ago(today, 0),
            note=f"Scheduled outpatient infusion center administration on {days_from_now(today, 7)}",
        ),
    ]


def _pab_002(today):
    pid = "example-patient-002"
    enc_id = f"{pid}-enc-1"
    return [
        patient(pid, "Synthetic Patient 002", "1957-11-02"),
        encounter(pid, enc_id, "IMP", "inpatient encounter",
                  period_start=days_ago(today, 2), period_end=None, status="in-progress",
                  reason_text="Neutropenic fever"),
        medication_request(
            pid, f"{pid}-medreq-1", "Chemotherapy regimen (cycle continuation)",
            status="active", intent="order", authored_on=days_ago(today, 1),
            encounter_id=enc_id,
            note="Scheduled cycle administered during the current inpatient admission",
        ),
    ]


def _pab_003(today):
    pid = "example-patient-003"
    return [
        patient(pid, "Synthetic Patient 003", "1962-06-20"),
        condition(pid, f"{pid}-cond-1", "Metastatic colorectal adenocarcinoma",
                  recorded_date=days_ago(today, 60)),
        observation(pid, f"{pid}-obs-1", "Blood pressure", effective_date=days_ago(today, 10),
                    value_text="152/88 mmHg (single reading on file)", category="vital-signs"),
        procedure(pid, f"{pid}-proc-1", "Cholecystectomy", performed_date=days_ago(today, 400)),
        # Deliberately no ECOG Observation and no second BP reading on file.
    ]


def _pab_004(today):
    pid = "example-patient-004"
    return [
        patient(pid, "Synthetic Patient 004", "1975-01-09"),
        diagnostic_report(pid, f"{pid}-dr-1", "Flow cytometry", effective_date=days_ago(today, 120),
                           conclusion="CD20 positive, consistent with CD20+ B-cell lymphoma"),
        observation(pid, f"{pid}-obs-1", "CD20 expression", effective_date=days_ago(today, 120),
                    value_text="Positive"),
    ]


def _pab_005(today):
    pid = "example-patient-005"
    return [
        patient(pid, "Synthetic Patient 005", "1959-09-30"),
        diagnostic_report(pid, f"{pid}-dr-1", "Pathology report", effective_date=days_ago(today, 90),
                           conclusion="Adenocarcinoma confirmed"),
        condition(pid, f"{pid}-cond-1", "Adenocarcinoma, subsequent line of therapy",
                  recorded_date=days_ago(today, 90)),  # no stage_text -> staging missing
        observation(pid, f"{pid}-obs-1", "Comprehensive metabolic panel",
                    effective_date=days_ago(today, 41), value_text="Within normal limits"),
        medication_request(pid, f"{pid}-medreq-1", "FOLFOX (line 1 therapy)", status="completed",
                            intent="order", authored_on=days_ago(today, 200)),
    ]


def _pab_006(today):
    pid = "example-patient-006"
    return [
        patient(pid, "Synthetic Patient 006", "1970-04-18"),
        diagnostic_report(pid, f"{pid}-dr-1", "Pathology report", effective_date=days_ago(today, 20),
                           conclusion="Adenocarcinoma confirmed"),
        condition(pid, f"{pid}-cond-1", "Adenocarcinoma, first-line therapy",
                  recorded_date=days_ago(today, 20), stage_text="Stage IV"),
        observation(pid, f"{pid}-obs-1", "Comprehensive metabolic panel",
                    effective_date=days_ago(today, 10), value_text="Within normal limits"),
    ]


def _pab_007(today):
    pid = "example-patient-007"
    return [
        patient(pid, "Synthetic Patient 007", "1966-12-05"),
        condition(pid, f"{pid}-cond-1", "Metastatic colorectal cancer", recorded_date=days_ago(today, 30)),
        observation(pid, f"{pid}-obs-1", "BRAF mutation analysis", effective_date=days_ago(today, 25),
                    value_text="Positive - BRAF V600E detected"),
        medication_request(pid, f"{pid}-medreq-1", "FOLFOXIRI", status="draft", intent="proposal",
                            authored_on=days_ago(today, 0), note="Proposed first-line therapy"),
    ]


def _pab_008(today):
    pid = "example-patient-008"
    return [
        patient(pid, "Synthetic Patient 008", "1964-02-27"),
        condition(pid, f"{pid}-cond-1", "Metastatic colorectal cancer", recorded_date=days_ago(today, 30)),
        medication_request(pid, f"{pid}-medreq-1", "FOLFOXIRI", status="draft", intent="proposal",
                            authored_on=days_ago(today, 0), note="Proposed first-line therapy"),
        # Deliberately no BRAF Observation and no prior FOLFOX/FOLFIRI MedicationRequest.
    ]


def _pab_009(today):
    pid = "example-patient-009"
    enc_id = f"{pid}-enc-1"
    return [
        patient(pid, "Synthetic Patient 009", "1955-07-11"),
        condition(pid, f"{pid}-cond-1", "Metastatic colorectal cancer", recorded_date=days_ago(today, 100)),
        encounter(pid, enc_id, "AMB", "ambulatory encounter",
                  period_start=days_ago(today, 7), period_end=days_ago(today, 7), status="finished",
                  reason_text="Oncology follow-up visit"),
        observation(pid, f"{pid}-obs-1", "ECOG Performance Status", effective_date=days_ago(today, 7),
                    value_text="1", category="survey", encounter_id=enc_id),
    ]


def _pab_010(today):
    pid = "example-patient-010"
    return [
        patient(pid, "Synthetic Patient 010", "1971-10-08"),
        coverage(pid, f"{pid}-cov-1", "SyntheticPayer Commercial PPO", "FORM-ONC-2026"),
        condition(pid, f"{pid}-cond-1", "HER2-low metastatic breast cancer", recorded_date=days_ago(today, 50)),
    ]


def _pab_011(today):
    pid = "example-patient-011"
    imp_enc = f"{pid}-enc-1"
    amb_enc = f"{pid}-enc-2"
    return [
        patient(pid, "Synthetic Patient 011", "1960-05-22"),
        encounter(pid, imp_enc, "IMP", "inpatient encounter",
                  period_start=days_ago(today, 3), period_end=days_ago(today, 1), status="finished",
                  reason_text="Chemotherapy administration, inpatient stay"),
        encounter(pid, amb_enc, "AMB", "ambulatory encounter",
                  period_start=days_from_now(today, 1), period_end=days_from_now(today, 1),
                  status="planned", reason_text="Scheduled outpatient infusion follow-up"),
        medication_request(pid, f"{pid}-medreq-1", "Chemotherapy regimen (started inpatient)",
                            status="completed", intent="order", authored_on=days_ago(today, 2),
                            encounter_id=imp_enc),
        medication_request(pid, f"{pid}-medreq-2", "Chemotherapy regimen (outpatient continuation)",
                            status="active", intent="order", authored_on=days_ago(today, 0),
                            encounter_id=amb_enc, note="Same regimen continued in outpatient setting"),
    ]


def _pab_012(today):
    pid = "example-patient-012"
    return [
        patient(pid, "Synthetic Patient 012", "1969-08-16"),
        condition(pid, f"{pid}-cond-1", "Metastatic colorectal cancer", recorded_date=days_ago(today, 60)),
        medication_request(pid, f"{pid}-medreq-1", "Bevacizumab (brand)", status="draft",
                            intent="order", authored_on=days_ago(today, 0)),
        # Deliberately no Observation documenting intolerance/contraindication to the biosimilar.
    ]


def _pab_013(today):
    pid = "example-patient-013"
    return [
        patient(pid, "Synthetic Patient 013", "1980-01-25"),
        condition(pid, f"{pid}-cond-1", "Metastatic sarcoma, refractory to standard therapy",
                  recorded_date=days_ago(today, 300)),
        diagnostic_report(pid, f"{pid}-dr-1", "NGS solid tumor panel", effective_date=days_ago(today, 15),
                           conclusion="NTRK3 gene fusion (ETV6-NTRK3) detected. No acquired TRK-domain "
                                      "resistance mutation identified."),
        observation(pid, f"{pid}-obs-1", "NTRK fusion status", effective_date=days_ago(today, 15),
                    value_text="NTRK3 fusion positive"),
    ]


def _pab_014(today):
    pid = "example-patient-014"
    return [
        patient(pid, "Synthetic Patient 014", "1977-03-19"),
        condition(pid, f"{pid}-cond-1", "Solid tumor, advanced", recorded_date=days_ago(today, 150)),
        diagnostic_report(pid, f"{pid}-dr-1", "NGS solid tumor panel", effective_date=days_ago(today, 10),
                           conclusion="NTRK1 missense point mutation detected. No fusion transcript identified."),
        observation(pid, f"{pid}-obs-1", "NTRK1 variant", effective_date=days_ago(today, 10),
                    value_text="Point mutation (not a fusion)"),
    ]


def _pab_015(today):
    pid = "example-patient-015"
    return [
        patient(pid, "Synthetic Patient 015", "1963-09-02"),
        condition(pid, f"{pid}-cond-1", "Metastatic endometrial cancer", recorded_date=days_ago(today, 200)),
        diagnostic_report(pid, f"{pid}-dr-1", "Mismatch repair IHC panel", effective_date=days_ago(today, 20),
                           conclusion="Loss of MLH1 and PMS2 nuclear expression (dMMR)"),
        medication_request(pid, f"{pid}-medreq-1", "Carboplatin/Paclitaxel (line 1 therapy)",
                            status="completed", intent="order", authored_on=days_ago(today, 180),
                            note="Disease progressed on this regimen"),
    ]


def _pab_016(today):
    pid = "example-patient-016"
    return [
        patient(pid, "Synthetic Patient 016", "1958-12-11"),
        condition(pid, f"{pid}-cond-1", "Metastatic solid tumor", recorded_date=days_ago(today, 200)),
        diagnostic_report(pid, f"{pid}-dr-1", "Microsatellite instability PCR panel",
                           effective_date=days_ago(today, 20), conclusion="Microsatellite stable (MSS)"),
        medication_request(pid, f"{pid}-medreq-1", "Prior line chemotherapy", status="completed",
                            intent="order", authored_on=days_ago(today, 180)),
    ]


def _pab_017(today):
    pid = "example-patient-017"
    return [
        patient(pid, "Synthetic Patient 017", "1961-04-07"),
        condition(pid, f"{pid}-cond-1", "Metastatic non-small cell lung cancer", recorded_date=days_ago(today, 150)),
        observation(pid, f"{pid}-obs-1", "KRAS mutation analysis (FDA-approved companion diagnostic)",
                    effective_date=days_ago(today, 30), value_text="KRAS p.G12C detected"),
        medication_request(pid, f"{pid}-medreq-1", "Carboplatin/Pemetrexed (line 1 therapy)",
                            status="completed", intent="order", authored_on=days_ago(today, 120)),
    ]


def _pab_018(today):
    pid = "example-patient-018"
    return [
        patient(pid, "Synthetic Patient 018", "1968-11-23"),
        condition(pid, f"{pid}-cond-1", "Metastatic non-small cell lung cancer, newly diagnosed",
                  recorded_date=days_ago(today, 20)),
        observation(pid, f"{pid}-obs-1", "KRAS mutation analysis (FDA-approved companion diagnostic)",
                    effective_date=days_ago(today, 15), value_text="KRAS p.G12D detected"),
        # Deliberately no prior systemic-therapy MedicationRequest -- treatment-naive.
    ]


def _pab_019(today):
    pid = "example-patient-019"
    return [
        patient(pid, "Synthetic Patient 019", "1972-06-30"),
        condition(pid, f"{pid}-cond-1", "Metastatic non-small cell lung cancer, newly diagnosed",
                  recorded_date=days_ago(today, 10)),
        diagnostic_report(pid, f"{pid}-dr-1", "EGFR molecular panel", effective_date=days_ago(today, 10),
                           conclusion="EGFR exon 20 insertion mutation detected"),
        medication_request(pid, f"{pid}-medreq-1", "Osimertinib", status="draft", intent="proposal",
                            authored_on=days_ago(today, 0), note="Proposed first-line therapy"),
    ]


def _pab_020(today):
    pid = "example-patient-020"
    return [
        patient(pid, "Synthetic Patient 020", "1974-02-14"),
        condition(pid, f"{pid}-cond-1", "Metastatic non-small cell lung cancer, newly diagnosed",
                  recorded_date=days_ago(today, 10)),
        diagnostic_report(pid, f"{pid}-dr-1", "EGFR molecular panel", effective_date=days_ago(today, 10),
                           conclusion="EGFR exon 19 deletion detected"),
        medication_request(pid, f"{pid}-medreq-1", "Osimertinib", status="draft", intent="proposal",
                            authored_on=days_ago(today, 0), note="Proposed first-line therapy"),
    ]


def _pab_021(today):
    pid = "example-patient-021"
    return [
        patient(pid, "Synthetic Patient 021", "1965-10-17"),
        condition(pid, f"{pid}-cond-1", "Advanced epithelial ovarian cancer, newly diagnosed",
                  recorded_date=days_ago(today, 200)),
        diagnostic_report(pid, f"{pid}-dr-1", "Germline BRCA1/2 genetic testing",
                           effective_date=days_ago(today, 400),
                           conclusion="BRCA1 pathogenic variant detected (c.68_69delAG)"),
        medication_request(pid, f"{pid}-medreq-1", "Carboplatin/Paclitaxel (line 1 therapy)",
                            status="completed", intent="order", authored_on=days_ago(today, 100)),
        observation(pid, f"{pid}-obs-1", "Response assessment", effective_date=days_ago(today, 20),
                    value_text="Complete response (CR)", category="imaging"),
    ]


def _pab_022(today):
    pid = "example-patient-022"
    return [
        patient(pid, "Synthetic Patient 022", "1967-01-05"),
        condition(pid, f"{pid}-cond-1", "Advanced epithelial ovarian cancer, newly diagnosed",
                  recorded_date=days_ago(today, 200)),
        diagnostic_report(pid, f"{pid}-dr-1", "Germline BRCA1/2 genetic testing",
                           effective_date=days_ago(today, 400),
                           conclusion="BRCA1 variant of uncertain significance (VUS) identified (c.123A>T)"),
        medication_request(pid, f"{pid}-medreq-1", "Carboplatin/Paclitaxel (line 1 therapy)",
                            status="completed", intent="order", authored_on=days_ago(today, 100)),
        observation(pid, f"{pid}-obs-1", "Response assessment", effective_date=days_ago(today, 20),
                    value_text="Complete response (CR)", category="imaging"),
    ]


PATIENT_BUILDERS = {
    "example-patient-001": _pab_001,
    "example-patient-002": _pab_002,
    "example-patient-003": _pab_003,
    "example-patient-004": _pab_004,
    "example-patient-005": _pab_005,
    "example-patient-006": _pab_006,
    "example-patient-007": _pab_007,
    "example-patient-008": _pab_008,
    "example-patient-009": _pab_009,
    "example-patient-010": _pab_010,
    "example-patient-011": _pab_011,
    "example-patient-012": _pab_012,
    "example-patient-013": _pab_013,
    "example-patient-014": _pab_014,
    "example-patient-015": _pab_015,
    "example-patient-016": _pab_016,
    "example-patient-017": _pab_017,
    "example-patient-018": _pab_018,
    "example-patient-019": _pab_019,
    "example-patient-020": _pab_020,
    "example-patient-021": _pab_021,
    "example-patient-022": _pab_022,
}
