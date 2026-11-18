#!/usr/bin/env bash
# md2docx.sh — markdown in, .docx out, with Vietnamese office typography applied.
#
#   ./md2docx.sh input.md output.docx [--toc] [--pdf]
#   cat input.md | ./md2docx.sh - output.docx
#
# Prints one short line on success. Exit 1 with a one-line reason on failure.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REF="$SKILL_DIR/assets/reference-vn.docx"

# Per-run scratch dir: concurrent invocations must not share an error file, and
# the stdin copy has to be cleaned up on every exit path.
RUNDIR="$(mktemp -d "${TMPDIR:-/tmp}/md2docx.XXXXXX")"
trap 'rm -rf "$RUNDIR"' EXIT
ERR="$RUNDIR/pandoc.err"

MD=""
OUT=""
TOC=""
WANT_PDF=0

[[ -x "$(command -v pandoc)" ]] || { echo "FAIL: pandoc not installed" >&2; exit 1; }
[[ $# -ge 2 ]] || { echo "FAIL: usage: md2docx.sh input.md output.docx [--toc] [--pdf]" >&2; exit 1; }

MD="$1"; OUT="$2"; shift 2
while [[ $# -gt 0 ]]; do
  case "$1" in
    --toc) TOC="--toc" ;;
    --pdf) WANT_PDF=1 ;;
    *) echo "FAIL: unknown flag $1" >&2; exit 1 ;;
  esac
  shift
done

if [[ "$MD" == "-" ]]; then
  MD="$RUNDIR/input.md"; cat > "$MD"
fi
[[ -f "$MD" ]] || { echo "FAIL: input not found: $MD" >&2; exit 1; }

ARGS=(--from markdown+pipe_tables+task_lists+yaml_metadata_block
      --to docx --standalone --shift-heading-level-by=0
      --wrap=none
      --resource-path="$(dirname "$MD"):$SKILL_DIR/assets")
[[ -f "$REF" ]] && ARGS+=(--reference-doc="$REF")
[[ -n "$TOC" ]] && ARGS+=(--toc --toc-depth=2)

mkdir -p "$(dirname "$OUT")"
if ! pandoc "${ARGS[@]}" "$MD" -o "$OUT" 2>"$ERR"; then
  echo "FAIL: pandoc: $(tr -d '\n' < "$ERR" | cut -c1-300)" >&2
  exit 1
fi
[[ -s "$OUT" ]] || { echo "FAIL: empty output" >&2; exit 1; }

SIZE=$(wc -c < "$OUT" | tr -d ' ')
echo "ok: $OUT (${SIZE}B, $(basename "$REF" .docx))"

if [[ $WANT_PDF -eq 1 ]]; then
  if command -v soffice >/dev/null 2>&1; then
    soffice --headless --convert-to pdf --outdir "$(dirname "$OUT")" "$OUT" >/dev/null 2>&1 \
      && echo "ok: ${OUT%.docx}.pdf" \
      || echo "warn: pdf conversion failed (docx is still valid)" >&2
  else
    echo "warn: --pdf requested but soffice not installed; skipped" >&2
  fi
fi
