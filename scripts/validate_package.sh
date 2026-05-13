#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

[[ -f README.md ]] || fail "missing README.md"
[[ -f WORKFLOW.md ]] || fail "missing WORKFLOW.md"
[[ -f SKILLS_INDEX.md ]] || fail "missing SKILLS_INDEX.md"
[[ -d skills ]] || fail "missing skills/"
[[ -d references ]] || fail "missing references/"

for ref in references/a-share-data-sources.md references/evidence-schema.md references/skill-quality-rubric.md; do
  [[ -f "$ref" ]] || fail "missing $ref"
done

grep -q '## 1.0 稳定性分层' references/a-share-data-sources.md || fail "data sources must define stability tiers"
grep -q 'S1 原始/官方来源' references/a-share-data-sources.md || fail "data sources must prioritize official sources"
grep -q '09:00 定时任务价格' references/a-share-data-sources.md || fail "data sources must define 09:00 price source priority"
grep -q '## 1.0.1 数据整理不偏离原文' references/a-share-data-sources.md || fail "data sources must define non-deviation rules"
grep -q 'raw_value' references/evidence-schema.md || fail "evidence schema must preserve raw_value"
grep -q 'normalized_value' references/evidence-schema.md || fail "evidence schema must preserve normalized_value"
grep -q 'stability_tier' references/evidence-schema.md || fail "evidence schema must include stability_tier"
grep -q 'transform' references/evidence-schema.md || fail "evidence schema must include transform"

skill_count=0
while IFS= read -r skill_file; do
  skill_count=$((skill_count + 1))
  skill_dir="$(dirname "$skill_file")"
  expected_name="$(basename "$skill_dir")"

  grep -q '^---$' "$skill_file" || fail "$skill_file missing frontmatter fence"
  grep -q "^name: ${expected_name}$" "$skill_file" || fail "$skill_file name must match directory ${expected_name}"
  grep -q '^description:' "$skill_file" || fail "$skill_file missing description"

  if [[ "$expected_name" == a-share-* && "$expected_name" != "a-share-data-provider" && "$expected_name" != "a-share-evidence-pack" ]]; then
    grep -q 'references/a-share-data-sources.md' "$skill_file" || fail "$skill_file must reference data sources"
    grep -q 'references/evidence-schema.md' "$skill_file" || fail "$skill_file must reference evidence schema"
    grep -q '来源链接' "$skill_file" || fail "$skill_file must require final sources"
  fi

  grep -q "$skill_file" SKILLS_INDEX.md || fail "SKILLS_INDEX.md missing $skill_file"
  grep -q "$skill_file" MANIFEST.md || fail "MANIFEST.md missing $skill_file"
done < <(find skills -mindepth 2 -maxdepth 2 -name SKILL.md | sort)

[[ "$skill_count" -ge 9 ]] || fail "expected at least 9 skills, got $skill_count"

grep -q 'for skill_dir in "$ROOT_DIR"/skills/\*' scripts/install_lobster_assistant.sh || fail "install script must copy all skill dirs"
grep -q 'references/' scripts/install_lobster_assistant.sh || fail "install script must copy references"

echo "Package validation passed"
echo "Skills: $skill_count"
echo "References: $(find references -type f -name '*.md' | wc -l | tr -d ' ')"
