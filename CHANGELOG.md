# Changelog

## 2026-05-13

### 数据源与 Provider Registry

- 将 `scripts/fetch_a_share_data.py` 从单次轻量行情抓取升级为多 provider registry。
- 新增 `scripts/search_news.py`，默认使用 A 股财经站点定向 RSS 免费源；Brave/Tavily 仅作为可选 API key provider，支持单 provider 超时、总超时预算和失败降级。
- 默认 provider 为 `eastmoney,tencent`：
  - `eastmoney`：东方财富公开网页行情接口，按 S3 主源处理。
  - `tencent`：腾讯公开网页行情接口，按 S4 兜底和交叉校验处理。
- 行情输出新增：
  - `provider_results`：每个 provider 的成功/失败、错误信息和原始 quote。
  - `quality.status`：`passed | conflict | single_source | failed`。
  - `quality.warnings`：单源降级、价格差异过大等风险提示。
- 新增 `scripts/fetch_sector_boards.py`：
  - `--provider eastmoney`：抓取东方财富行业/概念板块快照。
  - `--provider akshare_ths`：本地安装 AKShare 后，通过 AKShare 获取同花顺行业/概念板块快照。
- 明确规则：东方财富公开接口可作为免费 S3 主源，但不是官方长期稳定 API；同花顺免费公开侧不直接硬编码为稳定源，只通过 AKShare 可选接入或正式授权源接入。

### 推荐链路影响

- 09:00 定时推荐仍应优先使用上一交易日收盘价或最近可核验价。
- 若东方财富不可用但腾讯可用，行情结果会标记为 `single_source`，推荐确定性必须降级。
- 若板块 provider 失败，脚本会记录错误并输出空板块列表，不编造板块热度。
- 关键推荐结论不得只依赖单一网页 provider；必须结合运行态板块账本、行情交叉校验、催化来源和风险降级。
- 推荐生成新增候选池覆盖审计：当热门/景气改善方向没有候选股数据时，必须提示覆盖不足，避免“先拉到数据的股票”天然占优。

### 安装到龙虾

在仓库根目录执行：

```bash
git pull
bash scripts/validate_package.sh
bash scripts/install_lobster_assistant.sh
```

安装目录不依赖 Codex。推荐显式指定龙虾实际读取的 skill 目录：

```bash
export LOBSTER_INSTALL_DIR=/path/to/lobster-invest
bash scripts/install_lobster_assistant.sh
```

也可以直接把目录作为参数传入：

```bash
bash scripts/install_lobster_assistant.sh /path/to/lobster-invest
```

安装后检查：

```bash
cat "$LOBSTER_INSTALL_DIR/INSTALL_STATE.md"
ls "$LOBSTER_INSTALL_DIR/docs"
cat "$LOBSTER_INSTALL_DIR/docs/CHANGELOG.md"
```

需要同花顺板块能力时，龙虾运行环境还需要安装 AKShare：

```bash
python3 -m pip install -U akshare
python3 scripts/fetch_sector_boards.py --provider akshare_ths --kind concept
```

如果不安装 AKShare，`akshare_ths` provider 会明确报错降级，不影响东方财富和腾讯 provider。
