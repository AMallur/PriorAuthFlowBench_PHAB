#!/usr/bin/env bash
# Generates synthetic oncology patients (FHIR R4 bundles) using Synthea,
# the standard open-source synthetic patient generator used across
# health-tech research (originally MIT/MITRE). This is the same category
# of substitute MedAgentBench used a real data warehouse (STARR) for --
# except Synthea data carries zero PHI risk, which matters a lot for a
# repo you intend to publish.
#
# Requires: Java 11+, ~2GB disk.
set -euo pipefail

SYNTHEA_DIR="./synthea"
OUTPUT_DIR="../data/synthea_output"
NUM_PATIENTS=100

if [ ! -d "$SYNTHEA_DIR" ]; then
  echo "Cloning Synthea..."
  git clone https://github.com/synthetichealth/synthea.git "$SYNTHEA_DIR"
fi

cd "$SYNTHEA_DIR"

# Synthea ships disease "modules" — we bias the population toward
# oncology-relevant conditions so the resulting FHIR bundles actually
# exercise prior-auth-relevant resources: Condition (cancer diagnoses),
# MedicationRequest (chemo/infusion orders), Observation (labs used in
# medical necessity checks), and CarePlan (treatment regimens).
#
# Relevant built-in modules: breast_cancer, colorectal_cancer,
# lung_cancer (module names as shipped in src/main/resources/modules).
echo "Generating $NUM_PATIENTS synthetic patients (oncology-biased)..."
./run_synthea -p "$NUM_PATIENTS" \
  --exporter.fhir.export=true \
  --exporter.fhir.bulk_data=false \
  --exporter.baseDirectory="$OUTPUT_DIR" \
  --generate.only_alive_patients=true \
  Massachusetts

echo "Done. FHIR bundles are in $OUTPUT_DIR/fhir/"
echo ""
echo "Next: load them into the running HAPI server, e.g. per-bundle:"
echo '  for f in '"$OUTPUT_DIR"'/fhir/*.json; do'
echo '    curl -s -X POST -H "Content-Type: application/fhir+json" \'
echo '      --data @"$f" http://localhost:8080/fhir'
echo '  done'
