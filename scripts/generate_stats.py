#!/usr/bin/env python3
"""
Генерирует stats.svg на основе живых данных GitHub API,
подставляя значения в assets/stats.template.svg (тот же
тумано-графитовый стиль, что и весь профиль — шаблон не трогаем).

Динамически тянутся:
  - количество публичных репозиториев
  - основной язык
  - топ-2 языка по байтам кода + агрегат "Other"

Статичные поля (руками правятся тут, внизу файла):
  - FOCUS   — короткая подпись рода деятельности
  - PROFILE — доп. подпись (было "Karton111321" в исходнике)

Запуск:
  GITHUB_TOKEN=... python3 scripts/generate_stats.py
"""

import os
import sys
import json
import urllib.request
import urllib.error

# ---- настройки (можно менять руками) ----------------------------------
GH_USER = os.environ.get("GH_USER", "qweyns")
FOCUS = os.environ.get("STATS_FOCUS", "plugin dev")
PROFILE = os.environ.get("STATS_PROFILE", "Karton111321")

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "stats.template.svg")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "stats.svg")

BAR_MAX_WIDTH = 340  # ширина полной шкалы в svg, не трогать — завязано на вёрстку
# -------------------------------------------------------------------------


def gh_api(path):
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"GitHub API error on {url}: {e.code} {e.reason}", file=sys.stderr)
        print(e.read().decode("utf-8"), file=sys.stderr)
        raise


def fetch_repos(user):
    """Публичные репозитории пользователя, без форков."""
    repos = []
    page = 1
    while True:
        batch = gh_api(f"/users/{user}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(r for r in batch if not r.get("fork"))
        if len(batch) < 100:
            break
        page += 1
    return repos


def fetch_languages(user, repo_name):
    return gh_api(f"/repos/{user}/{repo_name}/languages")


def aggregate_languages(user, repos):
    totals = {}
    for r in repos:
        try:
            langs = fetch_languages(user, r["name"])
        except Exception:
            continue
        for lang, byte_count in langs.items():
            totals[lang] = totals.get(lang, 0) + byte_count
    return totals


def top_languages(totals, top_n=2):
    """Возвращает [(name, pct), ...] топ-N + остаток агрегирован в 'Other'."""
    total_bytes = sum(totals.values())
    if total_bytes == 0:
        return [("—", 0), ("—", 0)], 0
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[:top_n]
    rest_bytes = total_bytes - sum(v for _, v in top)
    top_pct = [(name, round(v / total_bytes * 100)) for name, v in top]
    other_pct = round(rest_bytes / total_bytes * 100)
    return top_pct, other_pct


def render(template, data):
    out = template
    for key, value in data.items():
        out = out.replace("{{" + key + "}}", str(value))
    if "{{" in out:
        missing = [line for line in out.splitlines() if "{{" in line]
        raise RuntimeError(f"Не заполнены плейсхолдеры в шаблоне: {missing[:3]}")
    return out


def main():
    print(f"Fetching public repos for {GH_USER}...")
    repos = fetch_repos(GH_USER)
    repo_count = len(repos)
    print(f"  -> {repo_count} public repos (excluding forks)")

    print("Aggregating languages...")
    totals = aggregate_languages(GH_USER, repos)
    (lang1, pct1), (lang2, pct2) = top_languages(totals, top_n=2)[0]
    other_pct = top_languages(totals, top_n=2)[1]
    primary_lang = lang1
    print(f"  -> {lang1}: {pct1}%, {lang2}: {pct2}%, Other: {other_pct}%")

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    data = {
        "REPOS": repo_count,
        "PRIMARY_LANG": primary_lang,
        "FOCUS": FOCUS,
        "PROFILE": PROFILE,
        "LANG1_NAME": lang1,
        "LANG1_PCT": pct1,
        "LANG1_WIDTH": round(BAR_MAX_WIDTH * pct1 / 100),
        "LANG2_NAME": lang2,
        "LANG2_PCT": pct2,
        "LANG2_WIDTH": round(BAR_MAX_WIDTH * pct2 / 100),
        "LANG3_NAME": "Other",
        "LANG3_PCT": other_pct,
        "LANG3_WIDTH": round(BAR_MAX_WIDTH * other_pct / 100),
    }

    svg = render(template, data)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Written {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
