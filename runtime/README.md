# Runtime Artifacts

`runtime/` 用于描述运行态产物的约定。仓库只提交本说明文件，不提交真实市场状态、真实推荐结果或用户反馈数据。

运行环境应生成并维护以下文件：

```text
runtime/sector-state.latest.json
runtime/recommendation-runs/latest.json
runtime/feedback-log.jsonl
runtime/market-data/latest-quotes.json
runtime/source-audit.latest.json
runtime/weekly-review.latest.json
```

## 1. sector-state.latest.json

用途：保存最近一周左右沉淀的 A 股板块状态，供每日推荐快跑读取。

必须包含：

- `as_of`: 状态对应日期。
- `valid_until`: 状态有效期；过期后不得作为高关注推荐依据。
- `generated_at`: 生成时间。
- `generated_by`: 生成任务，如 `daily_update`、`after_close_update`、`weekly_refresh`。
- `benchmark`: 对照指数，如 `沪深300`、`中证全指`。
- `sectors`: 板块状态数组。

每个 `sector` 至少包含：

- `name`
- `status`: `hot | improving | low_activity | contrarian | unknown`
- `confidence`: `high | medium | low`
- `evidence_window`: 如 `5d`、`20d`
- `policy_industry_catalyst`
- `relative_strength`
- `turnover_heat`
- `breadth`
- `capital_flow`
- `overheat_risk`: `high | medium | low`
- `crowding_signals`
- `upgrade_triggers`
- `downgrade_triggers`
- `source_refs`

## 2. recommendation-runs/latest.json

用途：保存一次推荐任务的结构化输出。最终用户回答应从该文件渲染，而不是直接绕过结构化结果。

必须包含：

- `run_id`
- `run_time`
- `task_type`
- `sector_state_ref`
- `price_time_policy`
- `recommendations`
- `evidence`
- `validation`

每只推荐股票至少包含：

- `name`
- `code`
- `exchange`
- `sector`
- `sector_status`
- `recommendation_type`
- `attention_level`: `high | medium | observe`
- `recommendation_reason`
- `key_data`
- `price_reference`
- `risks`
- `invalid_if`
- `evidence_ids`

## 3. feedback-log.jsonl

用途：记录用户反馈、自动校验失败和后续复盘发现的问题。

每行是一个 JSON 对象，至少包含：

- `timestamp`
- `run_id`
- `feedback_type`
- `failure_type`
- `summary`
- `affected_stock`
- `affected_sector`
- `action_needed`

## 4. 主链路

每日 09:00 推荐只走短链路：

```text
读取 sector-state.latest.json
-> 检查 valid_until
-> 刷新上一交易日收盘价
-> 检查重大催化/重大负面
-> 生成 recommendation-runs/latest.json
-> scripts/validate_run.sh 校验
-> 渲染最终推荐清单
-> 失败/反馈写入 feedback-log.jsonl
```

每日快跑不负责全市场板块重算。全市场板块状态应由盘后或周度任务刷新。

## 5. 工具脚本

仓库提供以下 V1 工具：

```text
scripts/fetch_a_share_data.py          # 轻量获取 A 股行情，写入 market-data
scripts/build_sector_metrics.py        # 从 CSV/导出数据构建板块指标输入
scripts/generate_sector_state.py       # 从板块指标生成 sector-state.latest.json
scripts/collect_catalysts.py           # 从公告/政策/产业 CSV 收集催化记录
scripts/generate_candidates.py         # 从股票池和板块状态生成候选输入
scripts/generate_recommendation_run.py # 从结构化候选生成 recommendation-runs/latest.json
scripts/validate_run.sh                # 硬规则校验 recommendation run
scripts/audit_run_sources.py           # 检查 evidence 字段和来源链接可访问性
scripts/append_feedback.py             # 写入 feedback-log.jsonl
scripts/replay_recommendations.py      # 用后续价格复盘推荐结果
scripts/weekly_review.py               # 汇总 run 和 feedback，生成周度复盘
scripts/smoke_test.sh                  # 本地完整链路 smoke test
scripts/smoke_test_installed.sh        # 安装目录 smoke test
```

这些脚本不替代专业判断。它们负责把运行态产物结构化、可校验、可复盘。
