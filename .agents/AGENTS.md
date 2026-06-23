# Agent 工作规范

## 项目概述

这是一个每日新闻聚合静态网站项目，通过 Python 脚本从多个数据源抓取新闻，前端直接读取 JSON 文件展示。

## 核心原则

1. **数据一致性优先**：所有数据文件统一存放在 `data/` 目录，前端从 `data/` 读取
2. **多源容错**：每个数据源至少有 1 个备用 API，主源失败时自动切换
3. **相对路径**：脚本使用相对路径（基于脚本位置），不硬编码绝对路径
4. **静默降级**：API 失败时不报错退出，使用备用源或本地兜底数据
5. **幂等设计**：脚本可以重复运行，不会产生副作用

## 目录结构约定

```
/workspace/
├── data/              # 数据文件（所有 JSON 输出目标）
├── scripts/           # Python 抓取脚本
│   ├── fetch_*.py    # 各数据源抓取脚本
│   ├── generate_*.py # 数据聚合/生成脚本
│   └── *.js          # 前端组件脚本
├── .github/workflows/ # CI 工作流
└── .agents/           # Agent 规范和 Skill
```

## 数据抓取脚本规范

### 命名规范
- 数据源抓取脚本：`fetch_{source}.py`
- 数据聚合脚本：`generate_{purpose}.py`

### 输出路径
```python
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.abspath(os.path.join(script_dir, '..', 'data'))
os.makedirs(data_dir, exist_ok=True)
```

### 错误处理模式
```python
def fetch_data():
    sources = [
        ('Primary', fetch_primary),
        ('Fallback', fetch_fallback),
    ]
    for name, fetcher in sources:
        try:
            result = fetcher()
            if result:
                print(f"  ✅ {name}: success")
                return result
        except Exception as e:
            print(f"  ⚠️ {name} failed: {e}")
    print(f"  ❌ All sources failed")
    return []  # 或默认值
```

### 输出格式
所有 JSON 文件必须包含 `updated_at` 字段：
```json
{
  "updated_at": "2026-06-23 15:00:00",
  "...": "..."
}
```

## 前端开发规范

### 数据加载
- 使用 `data/{file}.json?t=` + 时间戳 避免缓存
- 必须有加载失败的降级处理（空状态 / 本地兜底数据）

### 组件复用
- 公共 JS 组件放在 `scripts/` 目录
- header 统一使用 `header-info.js`
- footer 统一使用 `footer.js`

## CI/CD 规范

### 工作流步骤顺序
1. Checkout
2. Setup Python
3. Install dependencies
4. Fetch GitHub
5. Fetch Hacker News
6. Fetch Juejin
7. Fetch Misc
8. Generate aggregated data（如 news_data.json）
9. Commit & push

### 时间安排
- 每日 UTC 00:00（北京时间 08:00）运行
- 支持手动触发 `workflow_dispatch`

## 修改 Checklist

修改数据抓取相关代码时，检查以下项：

- [ ] 输出路径是否指向 `data/` 目录
- [ ] 是否有备用数据源
- [ ] 失败时是否有降级处理
- [ ] JSON 格式是否与前端期望一致
- [ ] GitHub Actions 是否需要同步更新

修改前端代码时，检查以下项：

- [ ] 是否使用相对路径引用 data/
- [ ] 数据加载失败是否有友好提示
- [ ] 响应式布局是否正常
