#!/usr/bin/env bash
# Loads the hand-crafted synthetic patient bundles that back the seed
# tasks in tasks/task_bank.json (as opposed to the bulk Synthea population
# from generate_synthetic_patients.sh, which is a separate, larger,
# unlabeled patient pool not tied to specific task_bank.json entries).
#
# These bundles are generated fresh by synthetic_data/generate_bundles.py
# because several tasks encode relative-time facts (e.g. "labs 41 days
# old") computed from the generation date -- regenerate close to when you
# actually run an eval.
#
# Usage:
#   bash scripts/load_task_bank_patients.sh [fhir_base_url]
set -euo pipefail

FHIR_BASE_URL="${1:-http://localhost:8080/fhir}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNTHETIC_DATA_DIR="$SCRIPT_DIR/../synthetic_data"
BUNDLES_DIR="$SYNTHETIC_DATA_DIR/bundles"

echo "Regenerating patient bundles (dates are relative to today)..."
(cd "$SYNTHETIC_DATA_DIR" && python3 generate_bundles.py)

echo ""
echo "Loading bundles into $FHIR_BASE_URL ..."
for f in "$BUNDLES_DIR"/*.json; do
  patient_ref="$(basename "$f" .json)"
  status=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/fhir+json" \
    --data @"$f" "$FHIR_BASE_URL")
  if [[ "$status" == 2* ]]; then
    echo "  OK   $patient_ref ($status)"
  else
    echo "  FAIL $patient_ref ($status)" >&2
  fi
done

echo ""
echo "Done. Verify with, e.g.:"
echo "  curl -s '$FHIR_BASE_URL/Patient/example-patient-013'"
