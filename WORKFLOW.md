# 龙虾投资助手工作流程

## 1. 总体路由

收到用户问题后，先判断任务类型，再加载对应 skill。涉及高时效金融事实时，默认先走数据和证据层。

| 用户意图 | 使用内容 |
|---|---|
| 查数据、确认代码、找公告、核验来源 | `skills/a-share-data-provider/SKILL.md` |
| 补来源、审计来源、生成证据包 | `skills/a-share-evidence-pack/SKILL.md` |
| 整理 A 股核心财经要闻 | `skills/a-share-market-news/SKILL.md` |
| 分析单只或多只个股 | `skills/a-share-stock-analysis/SKILL.md` |
| 解读财报、业绩预告、公告、问询函 | `skills/a-share-earnings-announcement-review/SKILL.md` |
| 分析行业、赛道、板块、产业链 | `skills/a-share-sector-research/SKILL.md` |
| 推荐股票/筛选候选观察池 | `skills/a-share-stock-recommendation/SKILL.md` |
| 复盘持仓或组合风险 | `skills/a-share-portfolio-review/SKILL.md` |
| 跟踪候选池、自选股、上次推荐 | `skills/a-share-watchlist-tracker/SKILL.md` |
| 审计自身回答 | `self-improvement/INDEPENDENT_REVIEW_PROMPT.md` |
| 基于 Review 结果提出优化 | `self-improvement/OPTIMIZATION_ADVISOR_PROMPT.md` |

## 2. 标准执行链

```text
识别意图
  -> 读取 references/a-share-data-sources.md
  -> 使用 a-share-data-provider 获取/核验事实
  -> 使用任务 skill 分析
  -> 使用 a-share-evidence-pack 检查来源
  -> 输出答案和来源链接
```

如果只是非时效性的概念解释，可以跳过数据 provider；但只要涉及个股、公告、行情、资金、财报、推荐，就必须保留证据链。

## 3. 输出硬规则

- 结论先行。
- 事实和推断分开。
- 涉及个股时必须确认代码、交易所、数据时间。
- 最终回答必须有“来源链接”或“参考来源”区块。
- 来源不足时降低结论确定性，不补编。
- 不输出买入、卖出、加仓、清仓、仓位、目标价、止损价。

## 4. 推荐与候选池边界

“推荐”只表示：

- 候选观察清单。
- 研究优先级。
- 关注理由。
- 风险和逻辑失效条件。

不表示：

- 买入指令。
- 收益承诺。
- 仓位建议。
- 短线涨跌预测。

## 5. 自我迭代流程

按三角色执行：

```text
任务执行者 -> 独立 Reviewer -> 评分与优化建议者 -> 人工确认 -> 回归测试
```

禁止：

- 执行者自己给自己评分。
- 没有独立 Review 报告就给通过结论。
- 用最终答案外观替代来源核验。
- 自动放宽金融合规或来源要求。
