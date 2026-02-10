#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/vendor_sync_reference.sh [--force|--apply]"
  echo "Purpose: generate reference diff report against zjobsdev/pangu."
  echo "Default: only generate report (no code changes)."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-}"
REPORT="${ROOT_DIR}/artifacts/day7/reference_diff_report.md"

mkdir -p "${ROOT_DIR}/artifacts/day7"

if [[ -f "${REPORT}" && "${MODE}" != "--force" ]]; then
  echo "Report exists (skip): ${REPORT}"
  echo "Use --force to overwrite."
  exit 0
fi

cat > "${REPORT}" <<'MD'
# Reference Diff Report (zjobsdev/pangu)

## Summary
This report documents capability differences between this repo and zjobsdev/pangu.

## Reference Notes
See: docs/reference_pangu.md

## Gaps (must implement)
- 1/3/6/24h model selection
- 1–84h hourly scheduling
- 84–360h iterative scheduling
- paper-grade plotting bundle

## Gaps (interface only)
- region dataset adapter (plug-in interface)

## Next Steps
- Implement runner + scheduler with safe defaults
- Add paper plotting bundle with metadata
- Add region adapter skeleton and demo crop
MD

if [[ "${MODE}" == "--apply" ]]; then
  echo "NOTE: --apply is reserved; no automatic code sync is performed."
fi

echo "Wrote ${REPORT}"
