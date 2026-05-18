# Skill 索引

## 1. 数据与证据基础层

### A 股数据提供与核验

路径：`skills/a-share-data-provider/SKILL.md`

用途：

- 确认股票代码、交易所、主体。
- 查行情、公告、财报、估值、资金、交易日历。
- 处理数据源不可用、来源冲突和降级策略。

触发词：查数据、核验来源、股票代码对不对、找公告、找财报、行情数据、资金流。

### A 股证据包生成与审计

路径：`skills/a-share-evidence-pack/SKILL.md`

用途：

- 抽取关键事实。
- 将事实绑定来源。
- 检查最终回答是否有来源链接。
- 修复“来源不足”问题。

触发词：证据包、补来源、核验链接、来源不够、references at the end。

## 2. 核心分析层

### A 股核心财经要闻

路径：`skills/a-share-market-news/SKILL.md`

用途：整理指定日期、近 1 日、近 3 日、近一周影响 A 股盘面和个股的核心财经要闻。

触发词：A 股要闻、利好利空、盘前、盘后、近 1 日、上周最后一个交易日。

### A 股资金流向分析

路径：`skills/a-share-capital-flow/SKILL.md`

用途：分析个股或方向的主力资金、同花顺实时流入/流出、超大/大/中/小单、3/5/10/20 日资金趋势。

触发词：资金流向、主力资金、净流入、净流出、超大单、大单、北向、融资融券、龙虎榜。

### A 股个股分析

路径：`skills/a-share-stock-analysis/SKILL.md`

用途：分析单只或多只 A 股，覆盖行情、基本面、财务、估值、公告、资金、风险。

触发词：分析某股票、某股票怎么看、为什么涨跌、基本面、估值、资金面。

### A 股财报与公告解读

路径：`skills/a-share-earnings-announcement-review/SKILL.md`

用途：解读年报、季报、业绩预告、回购、减持、定增、并购、重大合同、问询函、处罚、ST 风险等。

触发词：公告怎么看、财报怎么样、业绩预告、问询函、减持、回购、利好利空。

### A 股行业与赛道研究

路径：`skills/a-share-sector-research/SKILL.md`

用途：分析行业、赛道、主题、产业链、政策受益方向和代表公司。

触发词：行业怎么看、赛道研究、板块机会、产业链、机器人、半导体、创新药、高股息。

## 3. 候选池与持仓层

### A 股个股推荐

路径：`skills/a-share-stock-recommendation/SKILL.md`

用途：筛选 3-5 只 A 股推荐标的，输出推荐类型、推荐理由、风险、触发条件和失效条件。

触发词：推荐股票、找潜在机会、筛选股票、候选观察池、哪些股票值得关注。

硬边界：推荐就是推荐，不需要婉转成候选观察；不输出无来源目标价、无口径止损价、仓位比例或收益承诺。开盘板、一字板、快速封板、近 5 日多次涨停或近 10 日涨幅过大的票只能作为主线锚点，不进入推荐前 5。

### A 股持仓复盘

路径：`skills/a-share-portfolio-review/SKILL.md`

用途：复盘持仓或组合，识别行业集中度、风格暴露、逻辑变化和风险。

触发词：持仓怎么看、组合风险、亏损原因、持有逻辑、仓位结构风险。

### A 股候选观察池跟踪

路径：`skills/a-share-watchlist-tracker/SKILL.md`

用途：跟踪上次推荐或用户自选股，判断入池逻辑是否强化、削弱、失效。

触发词：跟踪候选池、观察池更新、上次推荐怎么样、哪些该移出。

## 4. 共享参考层

路径：

- `references/a-share-data-sources.md`
- `references/evidence-schema.md`
- `references/skill-quality-rubric.md`

所有高时效金融任务都应使用这些 reference。

## 5. 自我迭代体系

路径：`self-improvement/`

核心文件：

- `SELF_IMPROVEMENT.md`
- `TASK_RUNNER_PROMPT.md`
- `INDEPENDENT_REVIEW_PROMPT.md`
- `OPTIMIZATION_ADVISOR_PROMPT.md`
- `SCORECARD.md`
- `TEST_CASES.md`
