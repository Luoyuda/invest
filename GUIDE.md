# 龙虾投资助手完整指导文档

## 1. 项目目标

龙虾投资助手是一个面向 A 股普通投资者的信息整理、个股分析、候选观察和自我迭代助手。

它的核心目标不是喊单，而是：

- 从公开信息中筛选真正影响 A 股盘面、板块和个股涨跌的核心信息。
- 帮用户理解政策、公告、财务、估值、资金和外围市场如何影响股票。
- 生成可追溯、可解释、可复核的分析结果。
- 通过三角色自我迭代体系持续提高专业性。

## 2. 推荐仓库结构

将本目录内容放入 `https://github.com/Luoyuda/invest.git` 仓库后，建议保持如下结构：

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
├── skills/
│   ├── a-share-market-news/
│   │   └── SKILL.md
│   ├── a-share-stock-analysis/
│   │   └── SKILL.md
│   └── a-share-stock-recommendation/
│       └── SKILL.md
├── self-improvement/
│   ├── SELF_IMPROVEMENT.md
│   ├── TASK_RUNNER_PROMPT.md
│   ├── INDEPENDENT_REVIEW_PROMPT.md
│   ├── OPTIMIZATION_ADVISOR_PROMPT.md
│   ├── DAILY_SELF_CHECK_PROMPT.md
│   ├── WEEKLY_ITERATION_PROMPT.md
│   ├── SCORECARD.md
│   ├── TEST_CASES.md
│   └── CHANGE_PROPOSAL_TEMPLATE.md
└── scripts/
    └── install_lobster_assistant.sh
```

## 3. 安装方式

进入仓库根目录后执行：

```bash
bash scripts/install_lobster_assistant.sh
```

脚本会把 Skill 和配置复制到：

```text
~/.codex/skills/lobster-invest/
```

如果运行环境使用自定义 `CODEX_HOME`，脚本会安装到：

```text
$CODEX_HOME/skills/lobster-invest/
```

每次安装都会记录本地版本：

```text
$CODEX_HOME/skills/lobster-invest/VERSION
$CODEX_HOME/skills/lobster-invest/INSTALL_STATE.md
```

`INSTALL_STATE.md` 包含：

- 当前配置版本号。
- 安装时间。
- 源仓库地址。
- 当前 git commit。
- 本地安装目录。

## 4. 小龙虾启动顺序

小龙虾读取本仓库时，按以下顺序加载：

1. `README.md`：了解仓库用途。
2. `VERSION`：确认当前配置版本。
3. `SOUL.md`：加载底线规则和角色人格。
4. `WORKFLOW.md`：加载任务路由和工作流程。
5. `SKILLS_INDEX.md`：判断用户任务应该使用哪个 Skill。
6. 具体任务 Skill：
   - 财经要闻：`skills/a-share-market-news/SKILL.md`
   - 个股分析：`skills/a-share-stock-analysis/SKILL.md`
   - 个股推荐：`skills/a-share-stock-recommendation/SKILL.md`
7. 自我迭代：
   - 总机制：`self-improvement/SELF_IMPROVEMENT.md`
   - 三角色：`TASK_RUNNER_PROMPT.md`、`INDEPENDENT_REVIEW_PROMPT.md`、`OPTIMIZATION_ADVISOR_PROMPT.md`

## 5. Skill 路由

### A 股核心财经要闻

触发词：

- 今日要闻
- 近 1 日 / 近 3 日 / 近一周
- A 股利好利空
- 盘前/盘后核心消息

使用：

```text
skills/a-share-market-news/SKILL.md
```

### A 股个股分析

触发词：

- 分析某只股票
- 某股票怎么看
- 为什么涨/跌
- 公告影响
- 基本面/估值/资金面分析

使用：

```text
skills/a-share-stock-analysis/SKILL.md
```

### A 股个股候选推荐

触发词：

- 推荐几只股票
- 找潜在机会
- 筛选股票
- 给观察标的
- 生成股票候选池

使用：

```text
skills/a-share-stock-recommendation/SKILL.md
```

注意：这里的“推荐”只表示候选观察清单，不是买入指令。

## 6. 自我迭代机制

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

## 7. 冷启动迭代频率

前 14 天或仍有中高风险问题时：

- 每天轻量自检。
- 每 3 天深度迭代。
- 每周回归测试。

稳定期：

- 每 3 天轻量自检。
- 每周深度迭代。
- 每 2 周固定评测。

## 8. 金融安全边界

任何任务都必须遵守：

- 不承诺收益。
- 不喊单。
- 不给明确买入、卖出、仓位、目标价、止损价。
- 高时效信息必须联网核验。
- 来源不足时少说或不说。
- 个股相关输出必须包含风险和逻辑失效条件。
