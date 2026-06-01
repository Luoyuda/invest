# Runtime Artifacts

`runtime/` 用于描述运行态产物的约定。仓库只提交本说明文件，不提交真实市场状态、真实推荐结果或用户反馈数据。

运行环境应生成并维护以下文件：

```text
runtime/sector-state.latest.json
runtime/recommendation-runs/<YYYY-MM-DD>/<session-id>/<run-id>.json
runtime/recommendation-runs/latest.json
runtime/feedback-log.jsonl
runtime/market-data/latest-quotes.json
runtime/capital-flow.latest.json
runtime/market-data/sector-boards.latest.json
runtime/search-results.latest.json
runtime/source-audit.latest.json
runtime/weekly-review.latest.json
runtime/task-runs/*.latest.json
runtime/task-runs/*.last-success.json
runtime/outbox/pending/*.md
runtime/outbox/pending/*.json
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

## 2. recommendation-runs/<YYYY-MM-DD>/<session-id>/<run-id>.json

用途：保存一次推荐任务的结构化输出。最终用户回答应从该文件渲染，而不是直接绕过结构化结果。

推荐任务产物必须按日期和会话隔离，避免不同对话或定时任务互相覆盖。`runtime/recommendation-runs/latest.json` 仅是便捷指针，不作为唯一归档文件。

必须包含：

- `run_id`
- `run_session_id`
- `run_artifact_path`
- `run_time`
- `task_type`
- `sector_state_ref`
- `price_time_policy`
- `recommendations`
- `sector_anchors`
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
- `participation_role`: `recommendation`
- `execution_risk`: `low | medium`
- `trading_signals`: 开盘板、快速封板、近 5 日涨停次数、近 10 日涨幅等可参与性信号。
- `recommendation_reason`
- `key_data`
- `price_reference`
- `risks`
- `invalid_if`
- `evidence_ids`

`sector_anchors` 用于保存强但普通投资者难参与的主线锚点，例如开盘即涨停、一字板、快速封板、近 5 日多次涨停或近 10 日涨幅过大的标的。它们可以证明板块热度，但不得进入 `recommendations` 前 5。

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
-> 将开盘板、快速封板、连续板、短期涨幅过大的标的降级为 sector_anchors
-> 生成 recommendation-runs/<YYYY-MM-DD>/<session-id>/<run-id>.json
-> scripts/validate_run.sh <本次 run 文件> 校验
-> 渲染最终推荐清单
-> 失败/反馈写入 feedback-log.jsonl
```

每日快跑不负责全市场板块重算。全市场板块状态应由盘后或周度任务刷新。

## 5. 工具脚本

仓库提供以下 V1 工具：

```text
scripts/ifind_mcp.py                   # iFinD MCP/mcporter 兜底调用器；交互式 agent 优先 iFinD skill
scripts/fetch_a_share_data.py          # 通过 iFinD MCP 获取 A 股行情，不回退到免费网页源
scripts/fetch_capital_flow.py          # 通过 iFinD MCP 获取个股/市场资金流，不回退到公开网页源
scripts/fetch_sector_boards.py         # 通过 iFinD MCP 获取行业/概念板块快照，不回退到第三方 SDK
scripts/run_task.py                    # cron 通用运行器：锁、总超时、重试、健康报告、最近成功兜底
scripts/check_connectivity.py          # 一键检查包结构、行情、概念/行业板块、新闻搜索连通性
scripts/write_outbox_message.py        # 只写待发送消息产物，不直接调用 IM API；发送前校验表格数量
scripts/search_news.py                 # A 股定向新闻检索：通过 iFinD MCP 获取公告资讯，不回退到 RSS/搜索 API
scripts/build_sector_metrics.py        # 从 CSV/导出数据构建板块指标输入
scripts/refresh_sector_state.py        # 有锁、有超时、有缓存兜底地刷新板块状态
scripts/generate_sector_state.py       # 从板块指标生成 sector-state.latest.json
scripts/collect_catalysts.py           # 从公告/政策/产业 CSV 收集催化记录
scripts/generate_candidates.py         # 从股票池和板块状态生成候选输入
scripts/generate_recommendation_run.py # 从结构化候选生成按日期/会话隔离的 recommendation run
scripts/validate_run.sh                # 硬规则校验 recommendation run
scripts/audit_run_sources.py           # 检查 evidence 字段和来源链接可访问性
scripts/validate_answer_format.py      # 检查最终 Markdown 回答表格数量，避免超过 IM API 限制
scripts/append_feedback.py             # 写入 feedback-log.jsonl
scripts/replay_recommendations.py      # 用后续价格复盘推荐结果
scripts/weekly_review.py               # 汇总 run 和 feedback，生成周度复盘
scripts/smoke_test.sh                  # 本地完整链路 smoke test
scripts/smoke_test_installed.sh        # 安装目录 smoke test
```

这些脚本不替代专业判断。它们负责把运行态产物结构化、可校验、可复盘。

连通性检查：

```bash
python3 scripts/check_connectivity.py \
  --output runtime/connectivity-check.latest.json \
  --text-output runtime/connectivity-check.latest.txt
```

检查项包括包结构、iFinD MCP 配置、默认行情源、概念板块、行业板块和新闻搜索。任一必需项失败时命令返回非 0。

资金流检查：

```bash
python3 scripts/fetch_capital_flow.py 300308 --provider ifind --days 20 --output runtime/capital-flow.latest.json
```

交互式 agent 优先使用 iFinD skill；CLI/定时任务使用 iFinD MCP。iFinD 不可用时必须失败并记录缺失，不得回退到东方财富、同花顺公开网页或第三方 SDK。

大盘资金方向：

```bash
python3 scripts/fetch_capital_flow.py \
  --scope market \
  --provider ifind \
  --limit 50 \
  --output runtime/capital-flow.latest.json
```

该模式通过 iFinD MCP 查询行业/概念资金方向。若 iFinD 返回内容没有明确全市场总额，不得写成“大盘净流入/净流出 X 亿”。

cron 任务建议统一套一层运行器，避免任务超时后拖垮后续流程：

```bash
python3 scripts/run_task.py \
  --name "sector-refresh-1600" \
  --timeout-sec 90 \
  --retries 1 \
  --allow-stale-success \
  --stale-success-max-age-hours 24 \
  -- python3 scripts/refresh_sector_state.py \
    --fetch-timeout-sec 30 \
    --generate-timeout-sec 15
```

运行器会生成：

- `runtime/task-runs/<name>.latest.json`：最近一次运行健康报告。
- `runtime/task-runs/<name>.latest.txt`：给 IM 或人工看的简版摘要。
- `runtime/task-runs/<name>.last-success.json`：最近成功记录；外部源临时失败时可作为降级依据。

定时任务推荐的稳定性边界：

- 09:00 推荐快跑：`timeout-sec` 建议 120-180 秒；不做全市场板块重算。
- 盘中/盘后板块刷新：`timeout-sec` 建议 90-120 秒；外部源失败时保留最近成功状态。
- 消息发送：作为独立任务处理，发送失败只标记 delivery 失败，不把数据刷新或推荐生成判为失败。

最终回答格式检查：

```bash
python3 scripts/validate_answer_format.py /path/to/final-answer.md --max-tables 5
```

发送 IM 前应执行该检查。超过 5 个 Markdown/HTML 表格时命令返回非 0，必须改写为列表或合并表格后再发送。

若运行环境支持发送前落盘，优先写入 outbox，再由独立发送器投递：

```bash
python3 scripts/write_outbox_message.py \
  --task "09:00-a-share-recommendation" \
  --input runtime/final-answer.md \
  --outbox-dir runtime/outbox/pending \
  --max-tables 5
```

这样可以把“内容生成成功”和“IM API 投递成功”拆开。IM 短暂不可用时，待发送内容仍保留在 `runtime/outbox/pending/`，不会丢失本次分析结果。

板块状态刷新建议使用有边界的刷新器，而不是在 cron 中串行调用多个外部源：

```bash
python3 scripts/refresh_sector_state.py \
  --fetch-timeout-sec 45 \
  --generate-timeout-sec 20 \
  --health-output runtime/sector-refresh.latest.json \
  --summary-output runtime/sector-refresh.latest.txt
```

该脚本内置：

- `runtime/locks/sector-refresh.lock` 运行锁，避免上一次未结束时重复触发。
- 概念/行业板块分段超时，单个源卡住不会拖到 500s。
- 成功快照先写临时文件，只有有数据才替换最新缓存。
- 外部源失败时使用 `runtime/market-data/sector-boards.{kind}.latest.json` 缓存。
- 刷新结果与消息发送解耦，消息发送失败不应回滚 `sector-state.latest.json`。
