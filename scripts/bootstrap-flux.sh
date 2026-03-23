#!/bin/bash
# bootstrap-flux.sh
# Run this on a machine with internet access before transferring to air-gapped environment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== FluxCD Bootstrap for Air-Gapped Environment ==="
echo ""

# Step 1: Mirror Helm charts
echo "Step 1: Mirroring Helm charts..."
chmod +x "${SCRIPT_DIR}/mirror-helm-charts.sh"
"${SCRIPT_DIR}/mirror-helm-charts.sh" "$@"

# Step 2: Mirror Docker images
echo ""
echo "Step 2: Mirroring Docker images..."
chmod +x "${SCRIPT_DIR}/mirror-images.sh"
"${SCRIPT_DIR}/mirror-images.sh" "$@"

# Step 3: Export Flux manifests
echo ""
echo "Step 3: Exporting Flux manifests..."
flux export --all > "${SCRIPT_DIR}/../flux-config/gotk-components.yaml"

# Step 4: Create image pull secrets
echo ""
echo "Step 4: Generating image pull secrets template..."
cat > "${SCRIPT_DIR}/../clusters/air-gapped/flux-system/image-credentials.yaml" <<'EOF'
---
apiVersion: v1
kind: Secret
metadata:
  name: image-credentials
  namespace: flux-system
type: kubernetes.io/dockerconfigjson
data:
  # Run: kubectl create secret docker-registry image-credentials \
  #   --docker-server=<your-registry> \
  #   --docker-username=<user> \
  #   --docker-password=<token> \
  #   --namespace=flux-system
  .dockerconfigjson: c3R5bGU9ImF1dGgiCk0EAAAAP
EOF

echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "Next steps:"
echo "1. Transfer 'lgtm-test' folder to air-gapped environment"
echo "2. Push to your internal GitLab"
echo "3. Run: flux bootstrap gitlab --path=clusters/air-gapped"
