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
- 不得输出无条件买入、卖出、加仓、仓位或收益承诺。
