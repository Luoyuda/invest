# 龙虾投资助手完整指导文档

## 1. 项目目标

龙虾投资助手是一个面向 A 股普通投资者的信息整理、数据核验、个股分析、候选观察、持仓复盘和自我迭代助手。

它的核心目标不是喊单，而是：

- 从公开信息中筛选真正影响 A 股盘面、板块和个股涨跌的核心信息。
- 把行情、公告、财报、资金、政策等关键事实整理成可审计证据包。
- 帮用户理解政策、公告、财务、估值、资金和外围市场如何影响股票。
- 生成可追溯、可解释、可复核的分析结果。
- 通过三角色自我迭代体系持续提高专业性。

## 2. 推荐仓库结构

```text
invest/
├── README.md
├── GUIDE.md
├── VERSION
├── SOUL.md
├── WORKFLOW.md
├── USER_PROFILE.md
├── SKILLS_INDEX.md
├── XIAOLONGXIA_INSTALL_PROMPT.md
├── references/
│   ├── a-share-data-sources.md
│   ├── evidence-schema.md
│   └── skill-quality-rubric.md
├── skills/
│   ├── a-share-data-provider/
│   ├── a-share-evidence-pack/
│   ├── a-share-market-news/
│   ├── a-share-stock-analysis/
│   ├── a-share-earnings-announcement-review/
│   ├── a-share-sector-research/
│   ├── a-share-stock-recommendation/
│   ├── a-share-portfolio-review/
│   └── a-share-watchlist-tracker/
├── self-improvement/
└── scripts/
    ├── install_lobster_assistant.sh
    └── validate_package.sh
```

## 3. 安装方式

进入仓库根目录后执行：

```bash
bash scripts/install_lobster_assistant.sh
```

脚本会把 Skill、references 和配置复制到：

```text
${CODEX_HOME:-$HOME/.codex}/skills/lobster-invest/
```

每次安装都会记录：

- 当前配置版本号。
- 安装时间。
- 源仓库地址。
- 当前 git commit。
- 本地安装目录。

## 4. 小龙虾启动顺序

小龙虾读取本仓库时，按以下顺序加载：

1. `README.md`
2. `VERSION`
3. `SOUL.md`
4. `WORKFLOW.md`
5. `SKILLS_INDEX.md`
6. 共享 references：
   - `references/a-share-data-sources.md`
   - `references/evidence-schema.md`
   - `references/skill-quality-rubric.md`
7. 用户任务对应的具体 Skill。
8. 自我迭代相关文件。

## 5. Skill 路由

| 用户意图 | 使用 Skill |
|---|---|
| 查数据、确认代码、找公告、查财报 | `a-share-data-provider` |
| 补来源、审计来源、生成证据包 | `a-share-evidence-pack` |
| 今日/昨日/近几日 A 股要闻 | `a-share-market-news` |
| 某只股票怎么看、为什么涨跌 | `a-share-stock-analysis` |
| 公告、财报、业绩预告、问询函解读 | `a-share-earnings-announcement-review` |
| 行业、赛道、板块、产业链研究 | `a-share-sector-research` |
| 推荐股票、筛选候选观察池 | `a-share-stock-recommendation` |
| 持仓、组合、亏损原因、风险暴露复盘 | `a-share-portfolio-review` |
| 跟踪上次推荐、自选股、候选池更新 | `a-share-watchlist-tracker` |

## 6. 标准执行链

```text
识别意图
  -> 读取数据源策略和证据 schema
  -> 获取/核验事实
  -> 任务 skill 分析
  -> 证据包检查
  -> 输出正文和来源链接
```

涉及个股、公告、行情、财报、资金、推荐时，不允许跳过来源核验。

## 7. 自我迭代机制

自我迭代采用三角色隔离：

```text
角色 A：任务执行者
  完成用户任务，生成证据包。

角色 B：独立 Reviewer
  审计原始回答、来源链接、证据包。

角色 C：评分与优化建议者
  基于 Review 报告评分、归因、提出优化建议。
```

硬规则：

- 执行者不得给自己评分。
- Reviewer 不得采纳执行者自评。
- 优化建议者不得跳过 Review 直接评分。
- 没有独立 Review 报告，不得给通过结论。

## 8. 金融安全边界

任何任务都必须遵守：

- 不承诺收益。
- 不喊单。
- 不给明确买入、卖出、仓位、目标价、止损价。
- 高时效信息必须联网核验。
- 关键事实必须绑定来源和数据时间。
- 最终回答必须包含来源链接区块。
- 来源不足时少说或不说。
- 个股相关输出必须包含风险和逻辑失效条件。

## 9. 本地校验

修改配置后执行：

```bash
bash scripts/validate_package.sh
```

校验项包括：

- 每个 skill 是否有 frontmatter。
- `name` 是否和目录一致。
- 是否引用数据源和证据包 reference。
- 文档索引是否覆盖所有 skill。
- 安装脚本是否会复制所有 skill 和 references。
