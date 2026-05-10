#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_BASE="${CODEX_HOME:-$HOME/.codex}"
DEST_DIR="$CODEX_BASE/skills/lobster-invest"
VERSION_FILE="$ROOT_DIR/VERSION"
VERSION="unknown"
if [[ -f "$VERSION_FILE" ]]; then
  VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
fi

GIT_COMMIT="unknown"
if command -v git >/dev/null 2>&1 && git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_COMMIT="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || printf 'unknown')"
fi

INSTALLED_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

echo "Installing Lobster Investment Assistant..."
echo "Source: $ROOT_DIR"
echo "Destination: $DEST_DIR"
echo "Version: $VERSION"
echo "Source commit: $GIT_COMMIT"

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
cp "$ROOT_DIR/VERSION" "$DEST_DIR/VERSION"

cp -R "$ROOT_DIR/skills/a-share-market-news" "$DEST_DIR/skills/"
cp -R "$ROOT_DIR/skills/a-share-stock-analysis" "$DEST_DIR/skills/"
cp -R "$ROOT_DIR/skills/a-share-stock-recommendation" "$DEST_DIR/skills/"
cp "$ROOT_DIR/self-improvement/"*.md "$DEST_DIR/self-improvement/"

cat > "$DEST_DIR/INSTALL_STATE.md" <<EOF
# 龙虾投资助手本地安装状态

- Version: $VERSION
- Installed at UTC: $INSTALLED_AT
- Source repository: https://github.com/Luoyuda/invest.git
- Source path: $ROOT_DIR
- Source commit: $GIT_COMMIT
- Install destination: $DEST_DIR

此文件由 \`scripts/install_lobster_assistant.sh\` 自动生成。用户每次拉取仓库配置并重新执行安装脚本后，本地版本记录会更新。
EOF

echo
echo "Installed files:"
find "$DEST_DIR" -maxdepth 4 -type f | sort
echo
echo "Local version record:"
echo "$DEST_DIR/INSTALL_STATE.md"
echo
echo "Done."
