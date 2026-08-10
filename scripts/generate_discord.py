#!/usr/bin/env python3
"""
Генерирует discord.svg (карточка статуса Discord) из публичного Lanyard API,
подставляя значения в assets/discord.template.svg.

Важно: Lanyard видит твой статус только если ты состоишь на сервере
discord.gg/lanyard (это требование самого Lanyard, не наше). Без этого
API просто не отдаёт presence.

Требует переменную окружения DISCORD_USER_ID — свой Discord ID
(Settings → Advanced → Developer Mode, потом ПКМ по себе → Copy User ID).
Это не секрет, просто числовой ID, можно хранить открыто в workflow.

Запуск:
  DISCORD_USER_ID=... python3 scripts/generate_discord.py
"""

import os
import sys
import json
import urllib.request
import urllib.error

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "discord.template.svg")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "discord.svg")

# монохромная палитра статусов — вместо ярких discord-цветов, чтобы не выбиваться из стиля
STATUS_COLOR = {
    "online": "#E4EAEF",
    "idle": "#93A8B5",
    "dnd": "#6B8791",
    "offline": "#3D4F5A",
}
STATUS_TEXT = {
    "online": "online",
    "idle": "away",
    "dnd": "do not disturb",
    "offline": "offline",
}


def lanyard_api(user_id):
    url = f"https://api.lanyard.rest/v1/users/{user_id}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Lanyard API error: {e.code} {e.reason}", file=sys.stderr)
        print(e.read().decode("utf-8"), file=sys.stderr)
        raise


def render(template, data):
    out = template
    for key, value in data.items():
        out = out.replace("{{" + key + "}}", str(value))
    if "{{" in out:
        missing = [line for line in out.splitlines() if "{{" in line]
        raise RuntimeError(f"Не заполнены плейсхолдеры: {missing[:3]}")
    return out


def main():
    user_id = os.environ.get("DISCORD_USER_ID")
    if not user_id:
        print("DISCORD_USER_ID is not set", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching Lanyard presence for {user_id}...")
    result = lanyard_api(user_id)
    if not result.get("success"):
        print("Lanyard did not return data — are you a member of discord.gg/lanyard?", file=sys.stderr)
        sys.exit(1)

    d = result["data"]
    discord_status = d.get("discord_status", "offline")
    discord_user = d.get("discord_user", {})

    # avatar url
    user_id_val = discord_user.get("id", user_id)
    avatar_hash = discord_user.get("avatar")
    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id_val}/{avatar_hash}.{ext}?size=128"
    else:
        avatar_url = "https://cdn.discordapp.com/embed/avatars/1.png"

    # activity text: приоритет — игра/кастомный статус, иначе просто статус
    activity_text = None
    activities = d.get("activities", [])
    for act in activities:
        if act.get("type") == 0:  # Playing
            activity_text = f"playing {act.get('name', '')}"
            break
        if act.get("type") == 4 and act.get("state"):  # Custom status
            activity_text = act["state"]
            break
    if not activity_text:
        activity_text = "just chilling"

    render_data = {
        "AVATAR_URL": avatar_url,
        "STATUS_COLOR": STATUS_COLOR.get(discord_status, "#3D4F5A"),
        "STATUS_TEXT": STATUS_TEXT.get(discord_status, "offline"),
        "ACTIVITY_TEXT": activity_text,
    }

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    svg = render(template, render_data)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Written {OUTPUT_PATH} — status: {discord_status}, activity: {activity_text}")


if __name__ == "__main__":
    main()
