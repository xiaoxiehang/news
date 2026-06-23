# Skill: 新闻数据抓取与处理

## 用途

处理本项目的新闻数据抓取、聚合和验证工作。

## 何时使用

- 需要新增/修改数据源抓取脚本时
- 需要调试数据抓取失败问题时
- 需要验证数据格式是否正确时
- 需要运行完整的数据更新流程时

## 数据源清单

| 数据源 | 脚本文件 | 主 API | 备用 API | 输出文件 |
|--------|---------|--------|---------|---------|
| GitHub Trending | `scripts/fetch_github.py` | GitHub Search API | - | `data/github.json` |
| Hacker News | `scripts/fetch_hackernews.py` | Firebase API | Algolia API | `data/hackernews.json` |
| 掘金 | `scripts/fetch_juejin.py` | 掘金推荐 API | - | `data/juejin.json` |
| 名言 + 天气 | `scripts/fetch_misc.py` | Quotable + Open-Meteo | AdviceSlip + 本地兜底 | `data/misc.json` |
| 综合新闻聚合 | `scripts/generate_news.py` | 聚合以上数据 | - | `data/news_data.json` |

## 标准操作流程

### 1. 运行所有抓取脚本

```bash
# 依次运行所有抓取脚本
python3 scripts/fetch_github.py
python3 scripts/fetch_hackernews.py
python3 scripts/fetch_juejin.py
python3 scripts/fetch_misc.py
python3 scripts/generate_news.py
```

### 2. 调试某个数据源失败

1. 单独运行该脚本，查看输出
2. 检查 API 是否可达：`curl -I "API_URL"`
3. 检查是否有备用 API 已配置
4. 如果备用 API 也失败，考虑添加新的备用源

### 3. 新增数据源

1. 在 `scripts/` 下创建 `fetch_{source}.py`
2. 遵循[输出路径规范](AGENTS.md#输出路径)
3. 遵循[错误处理模式](AGENTS.md#错误处理模式)
4. 在 `.github/workflows/daily-update.yml` 中添加对应步骤
5. 如需在首页展示，更新 `scripts/generate_news.py`

## 数据格式规范

### github.json
```json
{
  "updated_at": "2026-06-23 15:00:00",
  "categories": {
    "hot": {
      "name": "Hot",
      "desc": "描述",
      "repos": [
        {
          "name": "...",
          "full_name": "...",
          "description": "...",
          "html_url": "...",
          "stars": 123,
          "language": "Python",
          "topics": ["..."]
        }
      ]
    }
  }
}
```

### hackernews.json
```json
{
  "updated_at": "2026-06-23 15:00:00",
  "stories": [
    {
      "id": 12345,
      "title": "...",
      "url": "...",
      "score": 100,
      "by": "author",
      "time": "2026-06-23 10:00",
      "descendants": 50,
      "hn_url": "https://news.ycombinator.com/item?id=12345"
    }
  ]
}
```

### juejin.json
```json
{
  "updated_at": "2026-06-23 15:00:00",
  "articles": [
    {
      "id": "...",
      "title": "...",
      "url": "...",
      "digest": "...",
      "views": 1000,
      "likes": 100,
      "author": "...",
      "category": "前端"
    }
  ]
}
```

### news_data.json（首页用）
```json
{
  "date": "2026-06-23",
  "date_str": "2026年06月23日",
  "count": 25,
  "news": [
    {
      "title": "...",
      "summary": "...",
      "link": "...",
      "source": "Hacker News",
      "category": "科技",
      "published": "2026-06-23"
    }
  ]
}
```

## 常见问题排查

### 问题：SSL 证书错误
- 原因：API 证书过期或网络环境问题
- 解决：添加备用 API，或对非关键 API 使用 `verify=False`

### 问题：Rate Limited
- 原因：API 调用频率过高
- 解决：添加重试等待逻辑（如 GitHub 脚本中的 60s 等待）

### 问题：前端数据不更新
- 原因 1：缓存问题 → 检查 URL 后是否有时间戳参数
- 原因 2：脚本输出路径错误 → 确认输出到 `data/` 目录
- 原因 3：GitHub Actions 失败 → 检查 Actions 运行日志

### 问题：news_data.json 数据为空
- 原因：上游数据源都失败了
- 解决：
  1. 检查各独立数据源是否正常
  2. 确认 `generate_news.py` 在所有 fetch 脚本之后运行
  3. 增加更多备用数据源
