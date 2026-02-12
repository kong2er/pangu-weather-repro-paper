#!/usr/bin/env bash
set -euo pipefail

# dry-run: bash scripts/cleanup_check.sh
# apply:   bash scripts/cleanup_check.sh --apply

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

source configs/default.env

OUT="${OUTPUT_ROOT:-/root/autodl-tmp/pangu-weather-repro/outputs}"

echo "[INFO] OUT=$OUT"
echo "[INFO] Exclude: $OUT/day4_rollout_30h/*"
echo "[INFO] Size filter: +50M"
echo

if [[ $APPLY -eq 0 ]]; then
  echo "[DRY-RUN] Duplicate file groups:"
  find "$OUT" -type f \
    ! -path "$OUT/day4_rollout_30h/*" \
    -size +50M -print0 \
  | xargs -0 sha256sum \
  | sort \
  | awk '
  {h=$1; f=$2; c[h]++; files[h]=files[h] ORS f}
  END{
    for (k in c) if (c[k]>1){
      print "=== DUP HASH:",k,"COUNT:",c[k];
      print files[k];
      print ""
    }
  }'
  exit 0
fi

echo "[APPLY] Deleting duplicates (keep the first file per hash):"
find "$OUT" -type f \
  ! -path "$OUT/day4_rollout_30h/*" \
  -size +50M -print0 \
| xargs -0 sha256sum \
| sort \
| awk '
{
  h=$1; f=$2;
  if (++seen[h] > 1) print f;
}' \
| while IFS= read -r f; do rm -f "$f"; echo "[DEL] $f"; done

echo
echo "[DONE] Re-run dry-run to confirm: bash scripts/cleanup_check.sh"
