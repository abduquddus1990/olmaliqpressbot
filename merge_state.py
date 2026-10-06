# -*- coding: utf-8 -*-
"""
OlmaliqpressBot - bot_state.json faylini git to'qnashuvlarida (merge conflict) xavfsiz birlashtiruvchi skript.
"""
import sys
import json
import re
from pathlib import Path

STATE_FILE = Path("data/bot_state.json")

def parse_conflicted_json(content: str) -> list[dict]:
    """Git conflict markers bo'lgan matndan ikkala tomonning JSON obyektlarini ajratib oladi."""
    parts = []
    # Agar conflict marker bo'lmasa, to'g'ridan-to'g'ri o'qiymiz
    if "<<<<<<<" not in content:
        try:
            return [json.loads(content)]
        except Exception:
            return []

    # Conflict markerlar orasidagi qismlarni ajratish
    pattern = re.compile(r'<<<<<<<[^\n]*\n([\s\S]*?)=======\n([\s\S]*?)>>>>>>>[^\n]*', re.MULTILINE)
    matches = list(pattern.finditer(content))
    if matches:
        for m in matches:
            side_a, side_b = m.group(1), m.group(2)
            for side in (side_a, side_b):
                try:
                    obj = json.loads(side.strip())
                    parts.append(obj)
                except Exception:
                    pass
    return parts

def merge_states():
    if not STATE_FILE.exists():
        print("bot_state.json topilmadi.")
        return

    content = STATE_FILE.read_text(encoding="utf-8")
    objects = parse_conflicted_json(content)

    if not objects:
        # Fayl buzilgan bo'lsa, zaxiradan yoki bo'sh obyekt yaratamiz
        print("bot_state.json parse qilinmadi, default tuzilma yaratilmoqda.")
        merged = {"channel_pointers": {}, "processed_messages": {}, "posted_articles": []}
    elif len(objects) == 1:
        merged = objects[0]
    else:
        merged = {"channel_pointers": {}, "processed_messages": {}, "posted_articles": []}
        for obj in objects:
            # channel_pointers: max id
            for ch, ptr in obj.get("channel_pointers", {}).items():
                merged["channel_pointers"][ch] = max(merged["channel_pointers"].get(ch, 0), ptr)

            # processed_messages: birlashtirish
            for k, v in obj.get("processed_messages", {}).items():
                merged["processed_messages"][k] = max(merged["processed_messages"].get(k, 0), v)

            # posted_articles: unikal sarlavhalar bo'yicha birlashtirish
            seen_titles = {a.get("norm_title", "") for a in merged["posted_articles"] if a.get("norm_title")}
            for art in obj.get("posted_articles", []):
                norm = art.get("norm_title", "")
                if norm and norm not in seen_titles:
                    seen_titles.add(norm)
                    merged["posted_articles"].append(art)

    # Saralash va cheklash
    if len(merged["posted_articles"]) > 200:
        merged["posted_articles"] = merged["posted_articles"][-200:]

    STATE_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print("bot_state.json muvaffaqiyatli birlashtirildi.")

if __name__ == "__main__":
    merge_states()
