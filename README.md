# LGTM-NPD: FluxCD Configuration for GitHub

This repository contains FluxCD manifests to deploy the LGTM (Loki, Grafana, Tempo, Mimir) stack and sample applications.

## Repository Structure

```
lgtm-npd/
├── clusters/
│   └── air-gapped/
│       ├── flux-system/          # Flux system components
│       ├── repositories.yaml    # GitRepository & HelmRepository
│       └── *.yaml               # Kustomizations
├── apps/                         # Sample applications
├── infrastructure/               # LGTM HelmRelease
├── flux-config/                 # Flux components
├── scripts/                      # Mirroring scripts
└── .github/workflows/           # GitHub Actions
```

## Quick Start

### 1. Install Flux

```bash
brew install fluxcd/tap/flux
```

### 2. Bootstrap to GitHub

```bash
flux bootstrap github \
  --owner=<your-github-org> \
  --repository=lgtm-npd \
  --branch=main \
  --path=clusters/air-gapped \
  --personal
```

This will:
- Create a deploy key for read-only access
- Store the private key as a Kubernetes secret
- Apply the initial Flux manifests

### 3. Verify Installation

```bash
flux get all --all-namespaces
```

You should see:
- GitRepository: `lgtm-npd`
- HelmRepository: `grafana-charts`
- Kustomizations: `clusters`, `apps`, `infrastructure`

## Bootstrap Output

After running `flux bootstrap`, you'll see something like:

```
► installing components in flux-system namespace
◎ waiting for components to be installed
✔ installed components
✔ configured service account for GitHub
✔ generated deploy key (GitHub deploy key)
✔ pushing flux-system manifests
✔ cloning <org>/lgtm-npd branch
✔ reconciling flux-system manifests
✔ committed flux-system manifests to <org>/lgtm-npd/main
✔ pushed flux-system manifests to <org>/lgtm-npd/main
◎ waiting for kustomization/flux-system to be reconciled
✔ kustomization/flux-system reconciled
```

## GitHub Actions (Optional)

The `.github/workflows/flux-sync.yaml` workflow provides additional sync capabilities:

- Triggers on push to `main`
- Reconciles Flux components automatically
- Requires `KUBECONFIG` secret configured in GitHub repo

To enable:
1. Add your kubeconfig as a GitHub secret: `Settings > Secrets > KUBECONFIG`
2. Enable the workflow on push

## Manual Apply (Without Bootstrap)

If you prefer manual installation:

```bash
# 1. Install Flux
kubectl apply -f https://github.com/fluxcd/flux2/releases/latest/download/install.yaml

# 2. Create GitHub token secret
kubectl create secret generic flux-system \
  --from-literal=token=<your-github-token> \
  --namespace=flux-system

# 3. Apply manifests
kubectl apply -f clusters/air-gapped/repositories.yaml
kubectl apply -f clusters/air-gapped/kustomization.yaml
```

## Configuration

### Update GitHub Org/Repo

Edit these files to match your GitHub details:

- `clusters/air-gapped/repositories.yaml` - Change `<org>` to your GitHub org
- `clusters/air-gapped/flux-system/gotk-sync.yaml` - Change `<org>` to your GitHub org

### Update Helm Charts for Air-Gapped

See `scripts/mirror-helm-charts.sh` to mirror charts to your internal registry.

## Troubleshooting

```bash
# Check Flux status
flux logs --level=debug

# Check GitRepository sync
flux get sources git

# Force reconciliation
flux reconcile source git lgtm-npd
flux reconcile kustomization apps --with-source
```

## FluxCD Resources

| Resource | File |
|----------|------|
| GitRepository | `clusters/air-gapped/repositories.yaml` |
| HelmRepository | `clusters/air-gapped/repositories.yaml` |
| HelmRelease | `infrastructure/helmrelease-lgtm.yaml` |
| Kustomization | `clusters/air-gapped/*.yaml` |
