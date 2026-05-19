# Recommendation Run Output Schema

本文件定义 V1 推荐运行结果结构。目标是让推荐输出可审计、可自动校验，并能追溯到来源数据。

## 1. 顶层结构

```json
{
  "run_id": "2026-05-13-0900",
  "run_time": "2026-05-13T09:00:00+08:00",
  "task_type": "daily_0900_recommendation",
  "sector_state_ref": {
    "path": "runtime/sector-state.latest.json",
    "as_of": "2026-05-12",
    "valid_until": "2026-05-19",
    "status": "valid"
  },
  "price_time_policy": {
    "run_session": "pre_open",
    "allowed_price_types": ["previous_close", "latest_verifiable"],
    "disallow": ["intraday_realtime"]
  },
  "recommendations": [],
  "sector_anchors": [],
  "candidate_pool_audit": {
    "pool_size": 0,
    "sector_counts": {},
    "candidate_source_counts": {},
    "preferred_sectors": [],
    "selected_mainlines": [],
    "missing_mainlines": [],
    "missing_preferred_sectors": [],
    "warnings": []
  },
  "selection_policy": {
    "style": "short_term_mainline",
    "mainline_count": 3,
    "discovery_count": 1,
    "selected_mainlines": [],
    "max_per_sector": 2,
    "reason": "prioritize 2-3 fast and funded mainlines while reserving a small evidence-backed discovery slot for overlooked improving opportunities"
  },
  "evidence": [],
  "validation": {
    "status": "pending",
    "checked_at": null,
    "errors": [],
    "warnings": []
  }
}
```

## 2. Recommendation Item

```json
{
  "name": "股票简称",
  "code": "000001",
  "exchange": "SZSE",
  "sector": "板块/主题",
  "sector_status": "hot",
  "recommendation_type": "policy_catalyst",
  "attention_level": "high",
  "participation_role": "recommendation",
  "execution_risk": "low",
  "trading_signals": {
    "opening_limit_up": false,
    "quick_limit_up": false,
    "limit_up_count_5d": 0,
    "short_term_gain_pct": 12.3
  },
  "short_term_fit": {
    "mainline": "AI算力",
    "selection_bucket": "mainline",
    "fundamental_score": 16,
    "capital_score": 12,
    "short_term_gain_pct": 12.3,
    "style": "mainline_first_with_evidence_backed_discovery"
  },
  "exclusion_reason": [],
  "fresh_catalyst_evidence_id": "E3",
  "recommendation_reason": ["..."],
  "key_data": [
    {
      "name": "PE-TTM",
      "value": "12.3",
      "unit": "倍",
      "evidence_id": "E2"
    }
  ],
  "price_reference": {
    "price_type": "previous_close",
    "value": 10.23,
    "unit": "元",
    "data_time": "2026-05-12 15:00:00+08:00",
    "source": "东方财富",
    "evidence_id": "E1"
  },
  "risks": ["..."],
  "invalid_if": ["..."],
  "evidence_ids": ["E1", "E2", "E3"]
}
```

允许的 `sector_status`：

- `hot`
- `improving`
- `low_activity`
- `contrarian`
- `unknown`

允许的 `attention_level`：

- `high`
- `medium`
- `observe`

允许的 `participation_role`：

- `recommendation`: 可进入推荐清单的标的。
- `sector_anchor`: 只用于说明主线强度，不进入推荐前 5。

允许的 `execution_risk`：

- `low`
- `medium`
- `high`

允许的 `price_type`：

- `previous_close`
- `latest_verifiable`
- `intraday_realtime`
- `delayed_intraday`
- `external_reference`
- `predicted`
- `technical_observation`

## 3. Evidence Item

```json
{
  "id": "E1",
  "source_name": "东方财富",
  "source_type": "market_data",
  "stability_tier": "S3",
  "url": "https://...",
  "published_at": null,
  "data_time": "2026-05-12 15:00:00+08:00",
  "raw_value": "收盘价 10.23 元",
  "normalized_value": 10.23,
  "unit": "元",
  "transform": "无",
  "supports": ["price_reference.previous_close"]
}
```

## 4. 硬规则

- 最终回答只能引用 `recommendation_run` 中已有字段。
- 每个关键数字必须能追到 `evidence.id`。
- 预测值、外部目标价、真实行情价必须分开。
- `09:00` 任务不得使用 `intraday_realtime`。
- `sector_status=low_activity` 不得给 `attention_level=high`。
- `overheat_risk=high` 的板块不得直接给高关注，除非推荐项有 `fresh_catalyst_evidence_id`。
- `recommendations[]` 只能包含 `participation_role=recommendation` 的标的。
- `execution_risk=high` 的标的不得进入 `recommendations[]`。
- 开盘即涨停、一字板、快速封板、近 5 日涨停 `>=2` 或近 10 日涨幅 `>=35%` 的标的，必须放入 `sector_anchors[]`，不得进入推荐前 5。
- `candidate_pool_audit.missing_preferred_sectors` 非空时，最终回答必须说明候选池覆盖不足，不能把“没拉到数据的方向”当作已经排除。
- `selection_policy.style=short_term_mainline` 时，必须写明 `selection_policy.selected_mainlines`；若 `candidate_pool_audit.missing_mainlines` 非空，最终回答必须说明主线候选池缺口。
- 短线推荐必须包含 `short_term_fit`，用于说明标的是 `mainline` 还是 `evidence_backed_discovery`、所属方向、资金/基本面评分和短期涨幅是否已透支。
- `evidence_backed_discovery` 只是防漏网槽位，默认不超过 `selection_policy.discovery_count`；不能用来绕过低活跃、无催化、无资金验证或过度上涨限制。
- 推荐清单默认同一板块不超过 2 只，除非候选池覆盖审计能证明其它热门/改善方向确实没有合格标的。
- 不得输出无条件买入、卖出、加仓、仓位或收益承诺。

## 5. 生成工具

V1 推荐 run 可以由 `scripts/generate_recommendation_run.py` 从结构化候选文件生成。候选文件至少包含：

```json
{
  "recommendations": [],
  "evidence": []
}
```

生成后必须运行：

```bash
bash scripts/validate_run.sh runtime/recommendation-runs/latest.json
python3 scripts/audit_run_sources.py runtime/recommendation-runs/latest.json --skip-network
```

需要联网审计来源链接时，去掉 `--skip-network`。
