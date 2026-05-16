# 证据包 Schema

所有高时效金融任务都必须生成证据包。用户最终答案可以只展示“来源链接”，但内部执行和自审必须保留结构化证据。

## 1. Evidence Item

```yaml
- id: E1
  source_name: 巨潮资讯
  source_type: announcement
  stability_tier: S1
  publisher: 上市公司或监管主体
  published_at: YYYY-MM-DD
  data_time: YYYY-MM-DD HH:mm TZ 或报告期
  url: https://...
  accessed_at: YYYY-MM-DD HH:mm TZ
  supports:
    - fact_id: F1
      fact: 公司披露 2026 年一季报营收...
      used_in: 核心事实/财务
  reliability: primary | official | mainstream | market-data | secondary
  limitations: 该来源不包含...
```

## 2. Fact Item

```yaml
- id: F1
  statement: 可被核验的一句话事实
  evidence_ids: [E1, E2]
  source_field: 来源页面/接口字段名或原文位置
  raw_value: 来源原始值或原文摘要
  normalized_value: 整理后的值
  unit: 元/亿元/%/万股/报告期等
  transform: 单位换算、复权口径、币种换算或“无”
  confidence: high | medium | low
  freshness: realtime | latest-trading-day | latest-report | stale
  notes: 口径、单位、限制
```

## 3. Inference Item

```yaml
- id: I1
  conclusion: 基于事实推导出的观点
  depends_on: [F1, F2]
  logic_chain: 政策补贴 -> 订单预期 -> 利润弹性 -> 估值修复
  confidence: high | medium | low
  invalid_if:
    - 订单未兑现
    - 毛利率继续下滑
```

## 4. 输出时的来源区块

最终回答末尾必须有“来源链接”或“参考来源”区块，每条来源包含：

1. 来源名称。
2. 发布日期或数据时间。
3. 链接。
4. 支撑的信息点。

示例：

```markdown
### 来源链接
1. 巨潮资讯，2026-04-28，https://...；支撑信息：公司 2026 年一季报营收、归母净利润。
2. 东方财富，数据时间 2026-05-11 15:00，https://...；支撑信息：收盘价、成交额、市盈率。
```

## 5. 证据质量规则

- 关键事实没有 `evidence_ids` 时，不得进入正文。
- 一条来源不能支撑它没有明确提供的信息。
- 关键事实必须保留 `raw_value` 和 `normalized_value`；无法保留原始值时，必须说明原因。
- `normalized_value` 不得改变 `raw_value` 的语义；只允许做单位、币种、复权、日期格式等可解释换算。
- 涉及金额、股数、比例、估值、价格时，必须填写 `unit` 和 `transform`。
- 来源之间数值冲突时，不得静默合并；必须生成冲突说明并选择更高稳定性来源。
- 观点必须通过 `depends_on` 连接到事实。
- 无法核验的信息只能写成“未查到可靠来源支持”。
- 如果最终答案无法附来源区块，任务视为未完成。

## 5.1 IM 输出格式限制

最终回答默认最多 5 个 Markdown 表格。超过 5 个表格容易触发 IM API 限制，必须改写：

- 优先保留 1-3 个核心汇总表。
- 其余明细改为编号列表、分段小标题或合并到同一张表。
- 来源链接区块使用编号列表，不使用表格。
- 发送前运行 `python3 scripts/validate_answer_format.py /path/to/final-answer.md --max-tables 5`。

## 6. 数据一致性检查

最终回答生成前必须检查：

1. 正文每个关键数字都能在 Fact Item 中找到。
2. Fact Item 的 `normalized_value` 能追溯到 Evidence Item 的 `raw_value`。
3. 价格、估值、财务字段没有丢失单位、报告期、数据时间。
4. 预测值、外部目标价、真实行情价三者没有混写。
5. 结论没有超出 `supports` 和 `depends_on` 能支撑的范围。
