#!/bin/bash
# mirror-helm-charts.sh
# Run this on a machine with internet access, then transfer to air-gapped environment

set -euo pipefail

# Configuration
REGISTRY_URL="${1:-localhost:5000}"  # Pass your internal registry as argument
CHARTS_DIR="./mirrored-charts"

# LGTM Stack Helm Charts
CHARTS=(
  "grafana/mimir-distributed"
  "grafana/loki-distributed"
  "grafana/tempo-distributed"
  "grafana/grafana"
  "grafana/tempo"
)

echo "=== Helm Chart Mirroring Script ==="
echo "Target Registry: ${REGISTRY_URL}"
echo "Charts Directory: ${CHARTS_DIR}"
echo ""

# Create charts directory
mkdir -p "${CHARTS_DIR}"

# Add Grafana charts repository
echo "Adding Grafana Helm repository..."
helm repo add grafana https://grafana.github.io/helm-charts --force-update

# Update repo
echo "Updating Helm repositories..."
helm repo update

# Pull and repackage each chart
for CHART in "${CHARTS[@]}"; do
  echo ""
  echo "Processing: ${CHART}"
  
  # Get latest version
  CHART_VERSION=$(helm search repo "${CHART}" --output json | jq -r '.[0].version')
  echo "  Latest version: ${CHART_VERSION}"
  
  # Pull chart
  helm pull "${CHART}" \
    --version "${CHART_VERSION}" \
    --untar \
    --untardir "${CHARTS_DIR}" \
    --repo https://grafana.github.io/helm-charts
  
  # Tag for internal registry
  CHART_NAME=$(echo "${CHART}" | cut -d'/' -f2)
  
  # Repackage with internal repo URL
  helm package "${CHARTS_DIR}/${CHART_NAME}" \
    --destination "${CHARTS_DIR}" \
    --app-version "${CHART_VERSION}"
  
  echo "  Packaged: ${CHART_NAME}-${CHART_VERSION}.tgz"
done

# Create index.yaml for internal repo
echo ""
echo "Creating index.yaml..."
helm repo index "${CHARTS_DIR}" --url "https://${REGISTRY_URL}/charts"

echo ""
echo "=== Mirroring Complete ==="
echo "Charts saved to: ${CHARTS_DIR}"
echo ""
echo "Next steps:"
echo "1. Transfer '${CHARTS_DIR}' to air-gapped environment"
echo "2. Push charts to internal registry:"
echo "   helm registry login ${REGISTRY_URL}"
echo "   helm push ${CHARTS_DIR}/*.tgz oci://${REGISTRY_URL}/charts"
echo "3. Update HelmRepository to use: oci://${REGISTRY_URL}/charts"
