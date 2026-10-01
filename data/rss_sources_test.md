# 中文 RSS 源实测记录

测试时间：2026-10-01（UTC）。测试方法：对每个候选源发起 HTTP 请求（20 秒超时），
用 feedparser 解析，记录条目数、最新条目发布时间、标题中文占比。失败源重试一次。

候选池：GitHub 公开仓库 fuxiaoai/tidings-rss 的 `data/feeds.json`（718 个源，2026-08-13 版，
经该仓库 Tidings 解析器多轮验证），筛选其中中文（language=zh）科技/AI/商业类源。

入选标准：可解析（能读出条目）+ 近期有更新（48 小时内为佳）+ 中文内容为主。

## 第一批：新候选源（7 个）

| 源 | RSS 地址 | 结果 | 条目数 | 最新条目 | 中文占比 | 结论 |
|---|---|---|---|---|---|---|
| 大模型智能 | wechat2rss.bestblogs.dev/feed/bfc6440c…xml | 可用 | 10 | 10.1 小时前 | 10/10 | 当天多次更新，AI 新品/论文解读，入选 |
| InfoQ 推荐 | plink.anyfeeder.com/infoq/recommend | 可用 | 30 | 13.4 小时前 | 10/10 | 条目最多、更新稳定，权威技术推荐，入选 |
| DeepSeek | wechat2rss.bestblogs.dev/feed/1709da4f…xml | 可用 | 10 | 24.0 小时前 | 10/10 | 公司官方动态，每日更新，备选 |
| 蓝点网 | www.landiannews.com/feed | 可用 | 20 | 42.4 小时前 | 10/10 | 解析正常，更新约 2 天一篇，备选 |
| MIT 科技评论热榜 | rsshub.bestblogs.dev/mittrchina/hot | 可用 | 10 | 48.5 小时前 | 10/10 | 解析正常，约 2 天一更，备选 |
| 智谱 | wechat2rss.bestblogs.dev/feed/433d2134…xml | 可用 | 10 | 309.4 小时前（约 13 天） | 10/10 | 更新停滞，淘汰 |
| HN 每日摘要 | www.supertechfans.com/cn/index.xml | 淘汰 | 5 | 0.8 小时前 | 0/5 | 英文为主，不符合中文源要求，淘汰 |

## 第二批：复测之前已验证的源（7 个）

| 源 | RSS 地址 | 结果 | 条目数 | 最新条目 | 中文占比 | 结论 |
|---|---|---|---|---|---|---|
| 虎嗅 | rss.huxiu.com/ | 可用 | 11 | 0.4 小时前 | 10/10 | 官方源，更新极活跃，入选 |
| 钛媒体 | www.tmtpost.com/feed | 可用 | 17 | 0.7 小时前 | 10/10 | 官方源，更新极活跃，备选 |
| Solidot | www.solidot.org/index.rss | 可用 | 20 | 9.0 小时前 | 10/10 | 技术社区情报源，稳定，入选 |
| 机器之心 | wechat2rss.bestblogs.dev/feed/8d97af31…xml | 可用 | 10 | 22.0 小时前 | 10/10 | 中文 AI 媒体，公众号转 RSS 稳定，入选 |
| 掘金本周最热 | rsshub.bestblogs.dev/juejin/trending/all/weekly | 可用 | 20 | 22.4 小时前 | 10/10 | 可用，但项目已下掉掘金频道，不引入 |
| 新智元 | wechat2rss.xlab.app/feed/ede30346…xml | 可用 | 20 | 69.8 小时前 | 10/10 | 更新偏慢（近 3 天），备选 |
| 潮流周刊 | weekly.tw93.fun/rss.xml | 可用 | 12 | 74.1 小时前 | 10/10 | 周刊节奏正常，前端资讯聚合，备选 |

## 最终入选的 5 个源（替换过渡源）

过渡源（已移除）：量子位、IT之家、少数派、爱范儿、V2EX。

| 新源 | 定位 | RSS 地址 | 过滤 | 取几条 |
|---|---|---|---|---|
| 机器之心 | 中文 AI 媒体 | wechat2rss.bestblogs.dev/feed/8d97af31b0de9e48da74558af128a4673d78c9a3.xml | 否（本身即 AI 内容） | 8 |
| 虎嗅 | 科技商业 | https://rss.huxiu.com/ | AI 关键词 | 8 |
| Solidot | 技术社区情报 | https://www.solidot.org/index.rss | AI 关键词 | 8 |
| 大模型智能 | AI 新品/工具 | wechat2rss.bestblogs.dev/feed/bfc6440c1a2443fab9a6bf607137d41db5cd5c93.xml | 否（本身即 AI 内容） | 6 |
| InfoQ 推荐 | 权威技术推荐 | https://plink.anyfeeder.com/infoq/recommend | AI 关键词 | 6 |

英文源（OpenAI 官方、The Verge、TechCrunch、MIT 科技评论、Product Hunt）未动。

## 真实选题验证

2026-10-01 运行 `scripts/fetch_rss.py` 真实抓取全部 10 个源（共 53 条），随后用
`scripts/generate_briefing.py` 的候选收集逻辑（collect_candidates）验证：
候选池 40 条中，4 个新中文源的文章成功进入（机器之心 3 条、Solidot 2 条、
大模型智能 2 条、InfoQ 推荐 2 条）；虎嗅本轮 0 条——其 RSS 解析正常
（独立实测 11 条、最新 0.4 小时前），但 AI 关键词过滤把本轮的泛商业内容
全部滤掉，属过滤器按设计工作，非源质量问题。LLM 生成环节因本地无
LLM_API_KEY 未执行（CI 每日任务中会正常执行），候选抓取环节已验证通过。

附带修复：验证中发现 `collect_candidates` 的旧逻辑按源顺序取条目，
`MAX_CANDIDATES=24` 会被 GitHub(12)+HN(8)+OpenAI 占满，后面的源永远进不了
候选池（旧的 5 个过渡源同样受影响）。已改为轮询取条目（每个源每轮 1 条），
`MAX_CANDIDATES` 提高到 40，保证所有源公平参与选题。

风险提示：机器之心、大模型智能走 wechat2rss 第三方桥接（bestblogs.dev），
第三方桥接可能独立于源站故障；脚本已有单源失败不中断的降级逻辑。
