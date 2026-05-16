# 龙虾投资助手配置包

关联仓库：

```text
https://github.com/Luoyuda/invest.git
```

本目录是一套面向「龙虾投资助手」的完整配置包，包含：

- 版本号：`VERSION`
- 更新记录：`CHANGELOG.md`
- 角色设定：`SOUL.md`
- 工作流程：`WORKFLOW.md`
- 用户档案：`USER_PROFILE.md`
- Skill 索引：`SKILLS_INDEX.md`
- A 股数据提供与来源核验 Skill
- A 股证据包生成与审计 Skill
- A 股核心财经要闻 Skill
- A 股个股分析 Skill
- A 股财报与公告解读 Skill
- A 股行业与赛道研究 Skill
- A 股个股候选推荐 Skill
- A 股持仓复盘 Skill
- A 股候选观察池跟踪 Skill
- 共享 reference：数据源策略、证据包 schema、板块状态账本、推荐 run schema、skill 质量评分表
- 运行态产物规范：`runtime/sector-state.latest.json`、`runtime/recommendation-runs/latest.json`、`runtime/feedback-log.jsonl`
- 三角色自我迭代体系
- 安装脚本
- 推荐 run 硬规则校验脚本
- 运行态生成脚本：行情获取、板块状态、推荐 run、反馈写入、来源审计、周度复盘
- 有边界的板块状态刷新器：运行锁、分段超时、缓存兜底、发送解耦
- 连通性检查脚本：一键验证包结构、行情、板块和新闻搜索是否可用
- 最终回答格式校验脚本：限制 Markdown 表格数量，避免触发 IM API 限制
- 多源 provider registry：新浪/腾讯快速行情交叉校验，东方财富/搜狐板块适配，adata/AKShare 可选适配
- 固定 fixtures 和 smoke test，用于验证正反例与完整本地链路
- 小龙虾读取仓库后的启动 Prompt

## 快速安装

在仓库根目录执行：

```bash
bash scripts/install_lobster_assistant.sh
```

安装目录可以显式指定，不依赖某个固定客户端目录：

```bash
LOBSTER_INSTALL_DIR=/path/to/lobster-invest bash scripts/install_lobster_assistant.sh
```

如果没有指定 `LOBSTER_INSTALL_DIR`，脚本会优先兼容 `CODEX_HOME/skills/lobster-invest`；否则安装到 `~/.lobster/skills/lobster-invest`。

每次执行安装脚本后，会在本地写入版本记录：

```text
$LOBSTER_INSTALL_DIR/VERSION
$LOBSTER_INSTALL_DIR/INSTALL_STATE.md
```

`INSTALL_STATE.md` 会记录版本号、安装时间、源仓库、源提交和安装目录。`CHANGELOG.md` 会同步到龙虾目录的 `docs/CHANGELOG.md`，用于说明本次更新内容和安装方式。

安装后，小龙虾应优先读取：

1. `SOUL.md`
2. `WORKFLOW.md`
3. `SKILLS_INDEX.md`
4. `references/a-share-data-sources.md`
5. `references/evidence-schema.md`
6. `references/sector-state.md`
7. `references/run-output-schema.md`
8. `self-improvement/SELF_IMPROVEMENT.md`
9. 用户任务对应的具体 Skill

## 核心原则

- 真实性第一，宁可少说，不编造。
- 所有高时效财经信息必须联网核验。
- 个股分析和推荐必须附来源链接。
- 关键事实必须进入证据包，最终回答必须有来源区块。
- 推荐就是推荐，不需要婉转成候选观察；但必须附来源、价格口径、风险和逻辑失效条件。
- 推荐不等于无条件买入指令、收益承诺或仓位安排。
- 不喊单，不承诺收益，不给仓位指令。
- 自我迭代采用三角色隔离：任务执行者、独立 Reviewer、评分与优化建议者。
