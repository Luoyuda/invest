# Manifest

Repository:

```text
https://github.com/Luoyuda/invest.git
```

Package:

```text
lobster-invest-assistant-kit
```

## Files

Root docs:

- `VERSION`
- `CHANGELOG.md`
- `README.md`
- `GUIDE.md`
- `SOUL.md`
- `WORKFLOW.md`
- `USER_PROFILE.md`
- `SKILLS_INDEX.md`
- `XIAOLONGXIA_INSTALL_PROMPT.md`

Skills:

- `skills/a-share-data-provider/SKILL.md`
- `skills/a-share-evidence-pack/SKILL.md`
- `skills/a-share-market-news/SKILL.md`
- `skills/a-share-stock-analysis/SKILL.md`
- `skills/a-share-earnings-announcement-review/SKILL.md`
- `skills/a-share-sector-research/SKILL.md`
- `skills/a-share-stock-recommendation/SKILL.md`
- `skills/a-share-portfolio-review/SKILL.md`
- `skills/a-share-watchlist-tracker/SKILL.md`

References:

- `references/a-share-data-sources.md`
- `references/evidence-schema.md`
- `references/sector-state.md`
- `references/run-output-schema.md`
- `references/skill-quality-rubric.md`

Runtime specs:

- `runtime/README.md`

Self improvement:

- `self-improvement/SELF_IMPROVEMENT.md`
- `self-improvement/TASK_RUNNER_PROMPT.md`
- `self-improvement/INDEPENDENT_REVIEW_PROMPT.md`
- `self-improvement/OPTIMIZATION_ADVISOR_PROMPT.md`
- `self-improvement/DAILY_SELF_CHECK_PROMPT.md`
- `self-improvement/WEEKLY_ITERATION_PROMPT.md`
- `self-improvement/SCORECARD.md`
- `self-improvement/TEST_CASES.md`
- `self-improvement/CHANGE_PROPOSAL_TEMPLATE.md`
- `self-improvement/SELF_REVIEW_SKILL.md`

Scripts:

- `scripts/fetch_a_share_data.py`
- `scripts/fetch_sector_boards.py`
- `scripts/build_sector_metrics.py`
- `scripts/generate_sector_state.py`
- `scripts/collect_catalysts.py`
- `scripts/generate_candidates.py`
- `scripts/generate_recommendation_run.py`
- `scripts/append_feedback.py`
- `scripts/audit_run_sources.py`
- `scripts/replay_recommendations.py`
- `scripts/weekly_review.py`
- `scripts/install_lobster_assistant.sh`
- `scripts/validate_package.sh`
- `scripts/validate_run.sh`
- `scripts/smoke_test.sh`
- `scripts/smoke_test_installed.sh`

Fixtures:

- `fixtures/sector-metrics.sample.json`
- `fixtures/sector-metrics.sample.csv`
- `fixtures/stocks.sample.csv`
- `fixtures/catalysts.sample.csv`
- `fixtures/candidates.valid.json`
- `fixtures/replay-prices.sample.csv`
- `fixtures/run.invalid-low-activity-high.json`
- `fixtures/run.invalid-0900-intraday.json`
- `fixtures/run.invalid-predicted-unmarked.json`
- `fixtures/run.invalid-limit-up-recommendation.json`
