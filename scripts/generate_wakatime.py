#!/usr/bin/env python3
"""
Генерирует wakatime.svg (карточка "сколько кодил за неделю") из WakaTime API,
подставляя значения в assets/wakatime.template.svg.

Требует переменную окружения WAKATIME_API_KEY — берётся с
https://wakatime.com/settings/api-key (Secrets → Actions в репозитории,
НЕ вписывать ключ в код).

Запуск:
  WAKATIME_API_KEY=... python3 scripts/generate_wakatime.py
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "wakatime.template.svg")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "wakatime.svg")
BAR_MAX_WIDTH = 326


def wakatime_api(path):
    api_key = os.environ.get("WAKATIME_API_KEY")
    if not api_key:
        print("WAKATIME_API_KEY is not set", file=sys.stderr)
        sys.exit(1)
    url = f"https://wakatime.com/api/v1/users/current{path}"
    token = base64.b64encode(api_key.encode()).decode()
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"WakaTime API error: {e.code} {e.reason}", file=sys.stderr)
        print(e.read().decode("utf-8"), file=sys.stderr)
        raise


def top_languages(languages, top_n=2):
    ranked = sorted(languages, key=lambda l: l.get("total_seconds", 0), reverse=True)
    total = sum(l.get("total_seconds", 0) for l in ranked) or 1
    top = ranked[:top_n]
    rest = total - sum(l.get("total_seconds", 0) for l in top)
    top_pct = [(l["name"], round(l["total_seconds"] / total * 100)) for l in top]
    other_pct = round(rest / total * 100)
    while len(top_pct) < top_n:
        top_pct.append(("—", 0))
    return top_pct, other_pct


def render(template, data):
    out = template
    for key, value in data.items():
        out = out.replace("{{" + key + "}}", str(value))
    if "{{" in out:
        missing = [line for line in out.splitlines() if "{{" in line]
        raise RuntimeError(f"Не заполнены плейсхолдеры: {missing[:3]}")
    return out


def main():
    print("Fetching WakaTime stats (last 7 days)...")
    stats = wakatime_api("/stats/last_7_days")
    data_block = stats.get("data", {})

    total_time = data_block.get("human_readable_total", "0 mins")
    languages = data_block.get("languages", [])

    top_pct, other_pct = top_languages(languages, top_n=2)
    (lang1, pct1), (lang2, pct2) = top_pct

    print(f"  -> {total_time} total, {lang1} {pct1}%, {lang2} {pct2}%, Other {other_pct}%")

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    render_data = {
        "TOTAL_TIME": total_time,
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

    svg = render(template, render_data)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Written {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
