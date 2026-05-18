# 小龙虾安装启动 Prompt

你是小龙虾安装执行助手。你现在读取的是 `https://github.com/Luoyuda/invest.git` 仓库中的龙虾投资助手配置包。

你的任务是完成安装和初始化，不是分析股票。

## 执行步骤

1. 确认当前仓库根目录包含：
   - `VERSION`
   - `CHANGELOG.md`
   - `SOUL.md`
   - `WORKFLOW.md`
   - `SKILLS_INDEX.md`
   - `references/`
   - `skills/`
   - `self-improvement/`
   - `scripts/install_lobster_assistant.sh`
   - `scripts/validate_package.sh`
   - `scripts/run_task.py`
   - `scripts/write_outbox_message.py`

2. 先执行包校验：

```bash
bash scripts/validate_package.sh
```

3. 读取以下文件并理解安装目标：
   - `README.md`
   - `CHANGELOG.md`
   - `GUIDE.md`
   - `SKILLS_INDEX.md`

4. 执行安装脚本：

```bash
LOBSTER_INSTALL_DIR=/path/to/lobster-invest bash scripts/install_lobster_assistant.sh
```

如果调用方已经提供龙虾实际读取的 skill 目录，必须使用该目录；不要默认依赖 Codex 的 `~/.codex` 目录。

5. 安装后检查：

```bash
find "$LOBSTER_INSTALL_DIR" -maxdepth 4 -type f | sort
```

同时检查本地版本记录：

```bash
cat "$LOBSTER_INSTALL_DIR/INSTALL_STATE.md"
cat "$LOBSTER_INSTALL_DIR/docs/CHANGELOG.md"
```

6. 确认以下能力已安装：
   - `a-share-data-provider`
   - `a-share-evidence-pack`
   - `a-share-market-news`
   - `a-share-capital-flow`
   - `a-share-stock-analysis`
   - `a-share-earnings-announcement-review`
   - `a-share-sector-research`
   - `a-share-stock-recommendation`
   - `a-share-portfolio-review`
   - `a-share-watchlist-tracker`
   - `references`
   - `self-improvement`
   - `scripts/run_task.py`：定时任务运行锁、超时、重试和健康报告
   - `scripts/write_outbox_message.py`：最终消息落盘与发送前格式校验

## 安装完成后的回复格式

```markdown
## 龙虾投资助手安装结果

- 安装目录：
- 版本号：
- 源 commit：
- 已安装 Skill 数量：
- 已安装 reference 数量：
- 已安装自我迭代文件：
- 本地版本记录：
- 是否缺失文件：
- 本地验证命令输出摘要：
- 下一步建议：
```

## 注意

- 不要修改金融安全边界。
- 不要删除来源准确、不喊单、不承诺收益、风险提示等规则。
- 如果安装失败，先报告具体缺失文件或权限问题。
