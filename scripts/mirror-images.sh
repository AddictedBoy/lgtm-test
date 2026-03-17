#!/bin/bash
# mirror-images.sh
# Run this on a machine with internet access, then transfer to air-gapped environment

set -euo pipefail

# Configuration
SOURCE_REGISTRY="${1:-docker.io}"
TARGET_REGISTRY="${2:-localhost:5000}"
IMAGES_FILE="${3:-images.txt}"

# Default images needed for LGTM stack + FluxCD + Sample Apps
DEFAULT_IMAGES=$(cat <<'EOF'
# FluxCD Components
fluxcd/flux2:v2.4.0
fluxcd/helm-controller:v0.38.3
fluxcd/source-controller:v1.4.1
fluxcd/kustomize-controller:v1.3.0
fluxcd/notification-controller:v1.4.0
fluxcd/image-automation-controller:v0.38.1
fluxcd/image-reflector-controller:v0.32.0

# Grafana Mimir
grafana/mimir:latest
grafana/mimir-continuous-test:latest

# Grafana Loki
grafana/loki:latest
grafana/promtail:latest

# Grafana Tempo
grafana/tempo:latest
grafana/tempo-query:latest

# Grafana
grafana/grafana:latest

# Grafana Agent
grafana/agent:latest
grafana/agent-operator:latest

# Sample Apps (from lgtm-stack)
python:3.11-slim
node:20-alpine
redis:7-alpine
postgres:15-alpine
openjdk:17-slim

# Kubernetes
k8s.gcr.io/kube-state-metrics/kube-state-metrics:v2.12.0
k8s.gcr.io/prometheus-adapter/prometheus-adapter:v0.12.0
EOF
)

# Parse images from file or use defaults
if [[ -f "${IMAGES_FILE}" ]]; then
  IMAGES=$(cat "${IMAGES_FILE}")
else
  IMAGES="${DEFAULT_IMAGES}"
fi

echo "=== Docker Image Mirroring Script ==="
echo "Source Registry:  ${SOURCE_REGISTRY}"
echo "Target Registry:  ${TARGET_REGISTRY}"
echo ""

# Check for skopeo
if ! command -v skopeo &> /dev/null; then
  echo "ERROR: skopeo is required but not installed."
  echo "Install: https://github.com/containers/skopeo#installing-binary-from-source"
  exit 1
fi

# Check for crane as alternative
if ! command -v skopeo &> /dev/null && ! command -v crane &> /dev/null; then
  echo "WARNING: Neither skopeo nor crane found. Using docker (slower)."
  USE_DOCKER=true
fi

# Login to target registry (if needed)
echo "Checking target registry authentication..."
if ! skopeo login "${TARGET_REGISTRY}" &> /dev/null; then
  echo "Please login to target registry:"
  echo "  skopeo login ${TARGET_REGISTRY}"
fi

# Mirror images
echo ""
echo "Mirroring images..."
for IMAGE in ${IMAGES}; do
  # Skip comments and empty lines
  [[ "${IMAGE}" =~ ^#.*$ ]] && continue
  [[ -z "${IMAGE}" ]] && continue
  
  SOURCE_IMAGE="${SOURCE_REGISTRY}/${IMAGE}"
  TARGET_IMAGE="${TARGET_REGISTRY}/${IMAGE}"
  
  echo "  ${SOURCE_IMAGE} -> ${TARGET_IMAGE}"
  
  # Use skopeo for copying
  skopeo copy \
    "docker://${SOURCE_IMAGE}" \
    "docker://${TARGET_IMAGE}" \
    --all \
    --dest-tls-verify=false \
    --preserve-digests \
    --retry-times 3
  
done

echo ""
echo "=== Mirroring Complete ==="
echo "All images mirrored to: ${TARGET_REGISTRY}"
echo ""
echo "Next steps:"
echo "1. Update HelmRelease values to use: ${TARGET_REGISTRY}/..."
echo "2. Create image pull secrets if using private registry"
