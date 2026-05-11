# 证据包 Schema

所有高时效金融任务都必须生成证据包。用户最终答案可以只展示“来源链接”，但内部执行和自审必须保留结构化证据。

## 1. Evidence Item

```yaml
- id: E1
  source_name: 巨潮资讯
  source_type: announcement
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
- 观点必须通过 `depends_on` 连接到事实。
- 无法核验的信息只能写成“未查到可靠来源支持”。
- 如果最终答案无法附来源区块，任务视为未完成。
