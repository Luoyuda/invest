#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

[[ -f README.md ]] || fail "missing README.md"
[[ -f CHANGELOG.md ]] || fail "missing CHANGELOG.md"
[[ -f WORKFLOW.md ]] || fail "missing WORKFLOW.md"
[[ -f SKILLS_INDEX.md ]] || fail "missing SKILLS_INDEX.md"
[[ -d skills ]] || fail "missing skills/"
[[ -d references ]] || fail "missing references/"
[[ -f runtime/README.md ]] || fail "missing runtime/README.md"
[[ -f scripts/validate_run.sh ]] || fail "missing scripts/validate_run.sh"
[[ -x scripts/smoke_test.sh ]] || fail "missing executable scripts/smoke_test.sh"
[[ -x scripts/smoke_test_installed.sh ]] || fail "missing executable scripts/smoke_test_installed.sh"
for script in \
  scripts/fetch_a_share_data.py \
  scripts/fetch_sector_boards.py \
  scripts/check_connectivity.py \
  scripts/validate_answer_format.py \
  scripts/search_news.py \
  scripts/build_sector_metrics.py \
  scripts/refresh_sector_state.py \
  scripts/generate_sector_state.py \
  scripts/collect_catalysts.py \
  scripts/generate_candidates.py \
  scripts/generate_recommendation_run.py \
  scripts/append_feedback.py \
  scripts/audit_run_sources.py \
  scripts/replay_recommendations.py \
  scripts/weekly_review.py; do
  [[ -f "$script" ]] || fail "missing $script"
  [[ -x "$script" ]] || fail "$script must be executable"
done

for ref in references/a-share-data-sources.md references/evidence-schema.md references/sector-state.md references/run-output-schema.md references/skill-quality-rubric.md; do
  [[ -f "$ref" ]] || fail "missing $ref"
done

grep -q '## 1.0 稳定性分层' references/a-share-data-sources.md || fail "data sources must define stability tiers"
grep -q 'S1 原始/官方来源' references/a-share-data-sources.md || fail "data sources must prioritize official sources"
grep -q '09:00 定时任务价格' references/a-share-data-sources.md || fail "data sources must define 09:00 price source priority"
grep -q '本仓库 Provider Registry' references/a-share-data-sources.md || fail "data sources must define provider registry"
grep -q 'sina' references/a-share-data-sources.md || fail "data sources must document Sina quote provider"
grep -q 'adata' references/a-share-data-sources.md || fail "data sources must document optional adata provider"
grep -q 'sohu' references/a-share-data-sources.md || fail "data sources must document Sohu board fallback provider"
grep -q 'akshare_ths' references/a-share-data-sources.md || fail "data sources must document optional Tonghuashun provider"
grep -q '## 1.0.1 数据整理不偏离原文' references/a-share-data-sources.md || fail "data sources must define non-deviation rules"
grep -q 'raw_value' references/evidence-schema.md || fail "evidence schema must preserve raw_value"
grep -q 'normalized_value' references/evidence-schema.md || fail "evidence schema must preserve normalized_value"
grep -q 'stability_tier' references/evidence-schema.md || fail "evidence schema must include stability_tier"
grep -q 'transform' references/evidence-schema.md || fail "evidence schema must include transform"
grep -q '板块热度/行业强弱' references/a-share-data-sources.md || fail "data sources must define sector heat data sources"
grep -q '## 1.1.1 板块热度与行业强弱口径' references/a-share-data-sources.md || fail "data sources must define sector heat methodology"
grep -q 'A 股板块状态账本' references/sector-state.md || fail "sector state ledger must exist"
grep -q '热门方向' references/sector-state.md || fail "sector state ledger must define hot sectors"
grep -q '低活跃方向' references/sector-state.md || fail "sector state ledger must define low-activity sectors"
grep -q 'valid_until' references/sector-state.md || fail "sector state ledger must define validity window"
grep -q 'overheat_risk' references/sector-state.md || fail "sector state ledger must define overheat_risk"
grep -q 'recommendation_run' references/run-output-schema.md || fail "run output schema must define recommendation_run"
grep -q 'runtime/sector-state.latest.json' runtime/README.md || fail "runtime README must define sector-state artifact"
grep -q 'runtime/recommendation-runs/latest.json' runtime/README.md || fail "runtime README must define recommendation run artifact"
grep -q 'runtime/feedback-log.jsonl' runtime/README.md || fail "runtime README must define feedback log artifact"
grep -q 'runtime/market-data/sector-boards.latest.json' runtime/README.md || fail "runtime README must define sector board artifact"
grep -q 'runtime/search-results.latest.json' runtime/README.md || fail "runtime README must define search results artifact"
grep -q 'generate_sector_state.py' runtime/README.md || fail "runtime README must list sector state generator"
grep -q 'fetch_sector_boards.py' runtime/README.md || fail "runtime README must list sector board fetcher"
grep -q 'refresh_sector_state.py' runtime/README.md || fail "runtime README must list bounded sector refresh"
grep -q 'search_news.py' runtime/README.md || fail "runtime README must list search news script"
grep -q 'A 股定向新闻检索' runtime/README.md || fail "runtime README must define A-share focused search"
grep -q 'build_sector_metrics.py' runtime/README.md || fail "runtime README must list sector metrics builder"
grep -q 'generate_candidates.py' runtime/README.md || fail "runtime README must list candidate generator"
grep -q 'replay_recommendations.py' runtime/README.md || fail "runtime README must list replay script"
grep -q 'generate_recommendation_run.py' runtime/README.md || fail "runtime README must list recommendation generator"
grep -q 'weekly_review.py' runtime/README.md || fail "runtime README must list weekly review"
grep -q '行业/政策/产业催化 | 35%' skills/a-share-stock-recommendation/SKILL.md || fail "stock recommendation must prioritize policy and industry catalysts"
grep -q '先做板块筛选，再做个股筛选' skills/a-share-stock-recommendation/SKILL.md || fail "stock recommendation must use top-down sector filtering"
grep -q 'references/sector-state.md' skills/a-share-stock-recommendation/SKILL.md || fail "stock recommendation must read sector state ledger"
grep -q 'references/run-output-schema.md' skills/a-share-stock-recommendation/SKILL.md || fail "stock recommendation must read run output schema"
grep -q 'runtime/sector-state.latest.json' skills/a-share-stock-recommendation/SKILL.md || fail "stock recommendation must read runtime sector state"
grep -q 'runtime/recommendation-runs/latest.json' skills/a-share-stock-recommendation/SKILL.md || fail "stock recommendation must generate recommendation run"
grep -q '候选池覆盖' skills/a-share-stock-recommendation/SKILL.md || fail "stock recommendation must audit candidate pool coverage"
grep -q 'references/sector-state.md' skills/a-share-sector-research/SKILL.md || fail "sector research must read sector state ledger"
grep -q '板块热度评分' skills/a-share-sector-research/SKILL.md || fail "sector research must score sector heat"
grep -q 'feedback-log.jsonl' self-improvement/SELF_IMPROVEMENT.md || fail "self improvement must consume feedback log"
grep -q 'sector_state_stale' self-improvement/SELF_IMPROVEMENT.md || fail "self improvement must define failure taxonomy"
grep -q '默认推荐偏好' USER_PROFILE.md || fail "user profile must define recommendation preference"

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
grep -q 'LOBSTER_INSTALL_DIR' scripts/install_lobster_assistant.sh || fail "install script must support LOBSTER_INSTALL_DIR"
grep -q 'references/' scripts/install_lobster_assistant.sh || fail "install script must copy references"
grep -q 'runtime/README.md' scripts/install_lobster_assistant.sh || fail "install script must copy runtime README"
grep -q '\*.py' scripts/install_lobster_assistant.sh || fail "install script must copy python scripts"
grep -q 'fixtures/' scripts/install_lobster_assistant.sh || fail "install script must copy fixtures"
grep -q 'CHANGELOG.md' scripts/install_lobster_assistant.sh || fail "install script must copy changelog"
grep -q 'Run validation passed' scripts/validate_run.sh || fail "validate_run.sh must implement run validation"
grep -q 'max_tables' scripts/validate_answer_format.py || fail "validate_answer_format.py must enforce table limit"
grep -q 'fetch-timeout-sec' scripts/refresh_sector_state.py || fail "refresh_sector_state.py must expose fetch timeout"
grep -q 'cached_board_snapshot' scripts/refresh_sector_state.py || fail "refresh_sector_state.py must support cache fallback"
grep -q '最多 5 个 Markdown 表格' skills/a-share-stock-recommendation/SKILL.md || fail "stock recommendation must define IM table limit"
grep -q '最多 5 个 Markdown 表格' references/evidence-schema.md || fail "evidence schema must define IM table limit"

for fixture in \
  fixtures/sector-metrics.sample.json \
  fixtures/sector-metrics.sample.csv \
  fixtures/stocks.sample.csv \
  fixtures/catalysts.sample.csv \
  fixtures/candidates.valid.json \
  fixtures/replay-prices.sample.csv \
  fixtures/run.invalid-low-activity-high.json \
  fixtures/run.invalid-0900-intraday.json \
  fixtures/run.invalid-predicted-unmarked.json \
  fixtures/run.invalid-limit-up-recommendation.json; do
  [[ -f "$fixture" ]] || fail "missing $fixture"
done

echo "Package validation passed"
echo "Skills: $skill_count"
echo "References: $(find references -type f -name '*.md' | wc -l | tr -d ' ')"
