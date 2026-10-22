#!/usr/bin/env python3
"""夜间质检 2b：实时榜点评回填抓取。
按 api/trending.js 各 tab 的同一查询抓 GitHub Search API，
过滤后输出缺失点评的仓库列表（供人工撰写点评后写入）。
"""
import json, time, urllib.parse, urllib.request
from datetime import date, timedelta

SITE = "/home/hatch/workspace/xiaojj-pro/site"
TOKEN = open("/home/hatch/.config/github/push-token").read().strip()

CATEGORIES = [
    ("ai", "ai", ['"machine learning" OR "deep learning" OR LLM stars:>1000']),
    ("ai-apps", "ai-apps", ["ai agent OR llm app OR chatbot stars:>500"]),
    ("frontend-mobile", "frontend-mobile", ["react OR vue OR flutter OR react-native OR nextjs stars:>2000"]),
    ("backend-infra", "backend-infra", ["kubernetes OR docker OR postgres OR redis OR microservice stars:>2000"]),
    ("devtools", "devtools", ["cli OR developer tool OR productivity OR automation stars:>1000"]),
    ("game", "game", ["game engine OR godot OR gamedev stars:>1000"]),
    ("healthcare", "healthcare", ["topic:healthcare stars:>50"]),
    ("fintech", "fintech", ["topic:fintech stars:>50"]),
    ("education", "education", ["topic:education stars:>100"]),
    ("research", "research", ["topic:science stars:>50"]),
    ("media", "media", ["topic:video stars:>100", "topic:audio stars:>100",
                        "topic:music stars:>100", "topic:podcast stars:>100",
                        "topic:video-player stars:>100", "topic:iptv stars:>100"]),
]

# 从 api/trending.js 抄的过滤表（只过滤不搬运）
EXCLUDE = {"stashapp/stash", "Igglybuff/awesome-piracy", "MDX-Tom/gpt-instruct"}
OVERRIDES = {
    "apache/iggy": "backend-infra", "travisjeffery/jocko": "backend-infra",
    "memgraph/memgraph": "backend-infra", "Cysharp/MagicOnion": "backend-infra",
    "apache/streampark": "backend-infra", "lakesoul-io/LakeSoul": "backend-infra",
    "apache/incubator-heron": "backend-infra", "fastly/pushpin": "backend-infra",
    "piskvorky/smart_open": "backend-infra", "adaltas/node-csv": "backend-infra",
    "iusztinpaul/hands-on-llms": "ai", "TanStack/ai": "ai-apps",
    "OpenMOSS/MOSS-TTS": "ai", "hashicorp/packer": "backend-infra",
    "prometheus/node_exporter": "backend-infra", "rathena/rathena": "game",
    "noob-hackers/infect": "devtools", "flink-china/flink-training-course": "education",
    "Dujltqzv/Some-Many-Books": "education", "huggingface/transformers": "ai",
    "bytedance/deer-flow": "ai-apps", "ahmedkhaleel2004/gitdiagram": "devtools",
    "ctjhoa/rust-learning": "education", "gztchan/awesome-design": "education",
    "mahmoud/awesome-python-applications": "devtools", "zatosource/zato": "backend-infra",
    "you-dont-need/You-Dont-Need-JavaScript": "frontend-mobile",
    "Kaustubh-Natuskar/moreThanFAANGM": "education", "996icu/996.ICU": "education",
    "GitHubDaily/GitHubDaily": "education", "shap/shap": "ai",
    "YyzHarry/imbalanced-regression": "ai", "pliang279/MultiBench": "ai",
    "pliang279/awesome-multimodal-ml": "ai", "frappe/erpnext": "backend-infra",
    "coollabsio/coolify": "backend-infra", "team-spotube/spotube": "media",
    "redis/redis": "backend-infra",
}


def search(query, per_page):
    url = ("https://api.github.com/search/repositories?q=" + urllib.parse.quote(query) +
           "&sort=stars&order=desc&per_page=" + str(per_page))
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "xiaojj-pro-trending/1.0",
        "Authorization": "Bearer " + TOKEN,
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    items = []
    for it in data.get("items", []):
        items.append({
            "name": it.get("name"), "full_name": it.get("full_name"),
            "owner": (it.get("owner") or {}).get("login"),
            "description": (it.get("description") or "")[:200],
            "language": it.get("language"),
            "stars": it.get("stargazers_count") or 0,
            "topics": (it.get("topics") or [])[:5],
        })
    return items


def tab_repos(tab_id, queries, take):
    seen, merged = set(), []
    for q in queries:
        time.sleep(2.2)  # 认证搜索 30次/分钟，按 27次/分钟打
        try:
            items = search(q, 80 if tab_id not in ("rising", "leaderboard") else take)
        except Exception as e:
            print("  [ERR]", tab_id, q[:40], e)
            continue
        for r in items:
            if r["full_name"] not in seen:
                seen.add(r["full_name"])
                merged.append(r)
    merged.sort(key=lambda x: -(x["stars"] or 0))
    merged = merged[:take]
    out = []
    for r in merged:
        fn = r["full_name"]
        if fn in EXCLUDE:
            continue
        t = OVERRIDES.get(fn)
        if t and t != tab_id:
            continue
        out.append(r)
    return out


today = date(2026, 10, 22)
d120 = str(today - timedelta(days=120))
d1 = str(today - timedelta(days=1))

results = {}
results["rising"] = tab_repos("rising", [f"created:>{d120} stars:>100"], 30)
results["leaderboard"] = tab_repos("leaderboard", [f"stars:>100 pushed:>{d1}"], 20)
for tab_id, _, queries in CATEGORIES:
    results[tab_id] = tab_repos(tab_id, queries, 80)

total = sum(len(v) for v in results.values())
print("tabs:", {k: len(v) for k, v in results.items()}, "total:", total)

ins = json.load(open(SITE + "/data/github_insights.json"))["insights"]
missing = []
for tab_id, repos in results.items():
    for r in repos:
        if r["full_name"] not in ins:
            missing.append((tab_id, r))
print("missing insights:", len(missing))
json.dump(missing, open(SITE + "/scripts/nightly_backfill_missing.json", "w"),
          ensure_ascii=False, indent=1)
for tab_id, r in missing:
    print(f"[{tab_id}] {r['full_name']} | {r['description'][:90]} | {r['language']} | stars={r['stars']}")
