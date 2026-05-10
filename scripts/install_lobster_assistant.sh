#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_BASE="${CODEX_HOME:-$HOME/.codex}"
DEST_DIR="$CODEX_BASE/skills/lobster-invest"

echo "Installing Lobster Investment Assistant..."
echo "Source: $ROOT_DIR"
echo "Destination: $DEST_DIR"

mkdir -p "$DEST_DIR/skills"
mkdir -p "$DEST_DIR/self-improvement"
mkdir -p "$DEST_DIR/docs"

cp "$ROOT_DIR/README.md" "$DEST_DIR/docs/README.md"
cp "$ROOT_DIR/GUIDE.md" "$DEST_DIR/docs/GUIDE.md"
cp "$ROOT_DIR/SOUL.md" "$DEST_DIR/docs/SOUL.md"
cp "$ROOT_DIR/WORKFLOW.md" "$DEST_DIR/docs/WORKFLOW.md"
cp "$ROOT_DIR/USER_PROFILE.md" "$DEST_DIR/docs/USER_PROFILE.md"
cp "$ROOT_DIR/SKILLS_INDEX.md" "$DEST_DIR/docs/SKILLS_INDEX.md"
cp "$ROOT_DIR/XIAOLONGXIA_INSTALL_PROMPT.md" "$DEST_DIR/docs/XIAOLONGXIA_INSTALL_PROMPT.md"

cp -R "$ROOT_DIR/skills/a-share-market-news" "$DEST_DIR/skills/"
cp -R "$ROOT_DIR/skills/a-share-stock-analysis" "$DEST_DIR/skills/"
cp -R "$ROOT_DIR/skills/a-share-stock-recommendation" "$DEST_DIR/skills/"
cp "$ROOT_DIR/self-improvement/"*.md "$DEST_DIR/self-improvement/"

echo
echo "Installed files:"
find "$DEST_DIR" -maxdepth 4 -type f | sort
echo
echo "Done."

