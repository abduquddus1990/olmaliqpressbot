# -*- coding: utf-8 -*-
"""
OlmaliqpressBot - Telegram kanaldan va mavjud bazadan bot_state.json ni to'liq sinxronlash va boshlang'ich ma'lumotlar bilan to'ldirish skripti.
"""
import sys
import re
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import config
import storage
from telegram_reader import get_telegram_client

def main():
    print("=== SEEDING BOT STATE FROM TELEGRAM AND DATABASE ===")
    storage.load_state()

    client = get_telegram_client()
    with client:
        # 1. Fetch from @olmaliqlik
        print("1. @olmaliqlik kanalidan so'nggi postlar o'qilmoqda...")
        target = client.get_entity(config.TARGET_CHANNEL_UZ)
        target_msgs = client.get_messages(target, limit=60)
        added_target = 0
        for m in reversed(target_msgs):
            if not m.text:
                continue
            lines = [l.strip() for l in m.text.split("\n") if l.strip()]
            raw_title = lines[0] if lines else ""
            title = re.sub(r"[*_`⚡️📍#]", "", raw_title).strip()
            summary = lines[1] if len(lines) > 1 else ""
            summary = re.sub(r"[*_`⚡️📍#]", "", summary).strip()

            norm = storage._normalize_text(title)
            existing = any(a.get("norm_title") == norm for a in storage._state["posted_articles"])
            if not existing and title:
                stems = list(storage.extract_stems(title))
                storage._state["posted_articles"].append({
                    "title": title,
                    "summary": summary,
                    "norm_title": norm,
                    "topic_key": "",
                    "stems": stems,
                    "posted_at": m.date.timestamp()
                })
                added_target += 1
        print(f"   @olmaliqlik kanalidan {added_target} ta post bazaga qo'shildi.")

        # 2. Fetch top messages from sources and record IDs
        print("2. Manbalar bo'yicha oxirgi ID lar aniqlanmoqda...")
        for src in config.SOURCES:
            ch = src["channel"]
            name = src["name"]
            msgs = client.get_messages(ch, limit=30)
            if msgs:
                max_id = max(m.id for m in msgs)
                storage.set_last_id(ch, max_id)
                for m in msgs:
                    key = f"{ch}:{m.id}"
                    if key not in storage._state["processed_messages"]:
                        storage._state["processed_messages"][key] = m.date.timestamp()
                print(f"   @{ch} ({name}): max_id={max_id}, {len(msgs)} ta xabar holati belgilandi.")

        storage.save_state()
        print("=== SEEDING MUVAFFAQIYATLI YAKUNLANDI ===")
        total_art = len(storage._state["posted_articles"])
        total_msg = len(storage._state["processed_messages"])
        print(f"Jami saqlangan maqolalar: {total_art}")
        print(f"Jami belgilangan xabarlar: {total_msg}")

if __name__ == "__main__":
    main()
