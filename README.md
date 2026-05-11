# 龙虾投资助手配置包

关联仓库：

```text
https://github.com/Luoyuda/invest.git
```

本目录是一套面向「龙虾投资助手」的完整配置包，包含：

- 版本号：`VERSION`
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
- 共享 reference：数据源策略、证据包 schema、skill 质量评分表
- 三角色自我迭代体系
- 安装脚本
- 小龙虾读取仓库后的启动 Prompt

## 快速安装

在仓库根目录执行：

```bash
bash scripts/install_lobster_assistant.sh
```

默认安装到：

```text
~/.codex/skills/lobster-invest/
```

每次执行安装脚本后，会在本地写入版本记录：

```text
~/.codex/skills/lobster-invest/VERSION
~/.codex/skills/lobster-invest/INSTALL_STATE.md
```

`INSTALL_STATE.md` 会记录版本号、安装时间、源仓库、源提交和安装目录。

安装后，小龙虾应优先读取：

1. `SOUL.md`
2. `WORKFLOW.md`
3. `SKILLS_INDEX.md`
4. `references/a-share-data-sources.md`
5. `references/evidence-schema.md`
6. `self-improvement/SELF_IMPROVEMENT.md`
7. 用户任务对应的具体 Skill

## 核心原则

- 真实性第一，宁可少说，不编造。
- 所有高时效财经信息必须联网核验。
- 个股分析和推荐必须附来源链接。
- 关键事实必须进入证据包，最终回答必须有来源区块。
- 推荐只表示候选观察清单，不是买入指令。
- 不喊单，不承诺收益，不给仓位指令。
- 自我迭代采用三角色隔离：任务执行者、独立 Reviewer、评分与优化建议者。
