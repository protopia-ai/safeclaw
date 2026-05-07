#!/bin/bash
set -euo pipefail

OPENCLAW_DIR=/home/openclaw/.openclaw
mkdir -p "${OPENCLAW_DIR}"

# The operator writes the openclaw.json ConfigMap content to the PVC before this
# container starts. Expand ${VAR} placeholders using Secret-injected env vars so
# that secrets never need to be hardcoded in the ConfigMap.
if [ -f "${OPENCLAW_DIR}/openclaw.json" ]; then
  tmp=$(mktemp)
  envsubst < "${OPENCLAW_DIR}/openclaw.json" > "$tmp"
  mv "$tmp" "${OPENCLAW_DIR}/openclaw.json"
fi

# Seed all example data into the workspace on first boot.
# Source data is baked into the image at /opt/safeclaw-examples/ via Dockerfile COPY.
WORKSPACE="${OPENCLAW_DIR}/workspace-safeclaw"
if [ ! -d "${WORKSPACE}/investment-portfolio" ]; then
  mkdir -p "${WORKSPACE}/investment-portfolio" \
            "${WORKSPACE}/email-monitor" \
            "${WORKSPACE}/pii-scanner" \
            "${WORKSPACE}/financial-data"
  cp -r /opt/safeclaw-examples/2-investment-portfolio/. "${WORKSPACE}/investment-portfolio/"
  cp -r /opt/safeclaw-examples/3-email-monitor/.        "${WORKSPACE}/email-monitor/"
  cp -r /opt/safeclaw-examples/4-pii-scanner/.          "${WORKSPACE}/pii-scanner/"
  mkdir -p "${WORKSPACE}/pii-scanner/data-guardian-pii-scanner/no-pii" \
            "${WORKSPACE}/pii-scanner/data-guardian-pii-scanner/yes-pii"
  cp -r /opt/safeclaw-examples/1-financial-data/.       "${WORKSPACE}/financial-data/"
fi

# Register plugins in openclaw's plugin registry.
# The operator npm-installs plugins (spec.plugins) but doesn't update openclaw's
# registry, running `openclaw plugins install` does both, making them available
# on gateway startup without needing a separate manual step.
openclaw plugins install @openclaw/brave-plugin 2>/dev/null || true

exec "$@"