# -*- coding: utf-8 -*-
"""
OlmaliqpressBot - JSON asosidagi holat saqlash va aqlli dublikatlarni aniqlash moduli (bot_state.json).
Git va GitHub Actions uchun 100% xavfsiz va to'qnashuvlarsiz (no binary merge conflicts).
"""
import os
import re
import json
import time
from pathlib import Path
import config

STOPWORDS = {
    "haqida", "uchun", "bilan", "bolgan", "boshlandi", "bolib", "otdi",
    "yangi", "shahar", "shahrida", "viloyat", "viloyatida", "respublika",
    "toshkent", "olmaliq", "ham", "esa", "kuni", "dagi", "boyicha",
    "otkazildi", "otkaziladi", "amalga", "oshirildi", "malum", "qilindi",
    "xabar", "berildi", "togrisida", "muhokama", "tomonidan", "boladi",
    "elon", "qilingan", "etildi", "etiladi", "orasida", "keltirilgan",
    "boyicha", "orqali", "kabi", "kora", "asosan", "tegishli", "qilish", "qilishga",
    "bugun", "kuni", "kunlik", "yil", "yilgi", "bo‘yicha", "to‘g‘risida", "o‘zbekiston",
    "davomida", "sababli", "holda", "qayta", "yana", "tartibida"
}

# O'zbek tili affikslari (uzunidan qisqasiga qarab saralangan)
SUFFIXES = [
    "larining", "laridan", "lariga", "larini", "larida", "larga", "larni", "larda", "larim", "lari", "lar",
    "sining", "sidan", "siga", "sini", "sida",
    "ining", "idan", "iga", "ini", "ida",
    "ning", "dan", "dagi", "ga", "ka", "qa", "ni", "da",
    "tirilmoqda", "tirilgan", "tirilishi", "tiriladi", "tirish",
    "ilmoqda", "ayotgan", "yotgan", "ilgan", "ilishi", "moqda", "yapti", "ishdi", "iladi",
    "dilar", "gan", "kan", "qan", "gani", "gach", "guncha",
    "shgan", "ishdi", "adi", "ydi", "di", "ish", "ishi",
    "likka", "ligini", "ligida", "ligi", "lik",
    "imiz", "ingiz", "si", "i"
]
SUFFIXES.sort(key=len, reverse=True)

STATE_FILE = getattr(config, "STATE_FILE", config.BASE_DIR / "data" / "bot_state.json")

_state = {
    "channel_pointers": {},
    "processed_messages": {},  # "channel:id" -> timestamp
    "posted_articles": []      # list of {title, summary, norm_title, topic_key, stems, posted_at}
}
_state_loaded = False

def stem_word(w: str) -> str:
    """O'zbekcha so'zning o'zagini ajratish."""
    w = w.lower().strip()
    w = re.sub(r"[\'`ʻʼ’]", "", w)
    w = re.sub(r"[^a-z0-9]", "", w)
    if len(w) <= 3:
        return w
    changed = True
    while changed and len(w) > 3:
        changed = False
        for s in SUFFIXES:
            if w.endswith(s) and len(w) - len(s) >= 3:
                w = w[:-len(s)]
                changed = True
                break
    return w

def extract_stems(text: str) -> set[str]:
    """Matndan mazmunli so'z o'zaklarini ajratish."""
    if not text:
        return set()
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    words = [w for w in clean.split() if len(w) > 2 and w not in STOPWORDS]
    stems = {stem_word(w) for w in words}
    return {s for s in stems if len(s) > 2 and s not in STOPWORDS}

def _normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[^\w\s]", "", text.lower()).strip()

def get_recurring_category(text: str) -> str | None:
    """Kunlik takrorlanadigan xabarlar toifasi (namoz, ob-havo, valyuta)."""
    t = text.lower()
    if any(k in t for k in ["namoz", "bomdod", "peshin", "asr", "shom", "xufton"]):
        return "namoz"
    if any(k in t for k in ["ob-havo", "ob havo", "obhavo", "harorat", "yogingarchilik"]):
        return "ob-havo"
    if any(k in t for k in ["valyuta kursi", "valyuta kurslari", "dollarning kursi"]):
        return "valyuta"
    return None

def load_state():
    global _state, _state_loaded
    if _state_loaded:
        return

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _state["channel_pointers"] = data.get("channel_pointers", {})
                _state["processed_messages"] = data.get("processed_messages", {})
                _state["posted_articles"] = data.get("posted_articles", [])
                _state_loaded = True
                return
        except Exception as e:
            print(f"[Storage Xatosi] bot_state.json o'qishda xatolik: {e}")

    # Agar bot_state.json bo'lmasa, mavjud SQLite bazasidan yuklashga urinamiz
    _import_from_sqlite_if_exists()
    _state_loaded = True

def _import_from_sqlite_if_exists():
    global _state
    db_file = getattr(config, "DB_FILE", config.BASE_DIR / "data" / "bot_database.db")
    if not db_file.exists():
        return
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # channel_state
        cur.execute("SELECT channel, last_id FROM channel_state")
        for r in cur.fetchall():
            _state["channel_pointers"][r["channel"]] = r["last_id"]

        # processed_messages
        cur.execute("SELECT channel, message_id, created_at FROM processed_messages")
        for r in cur.fetchall():
            _state["processed_messages"][f"{r['channel']}:{r['message_id']}"] = r["created_at"]

        # posted_articles
        cur.execute("SELECT title, norm_title, topic_key, posted_at FROM posted_articles ORDER BY id DESC LIMIT 200")
        for r in reversed(cur.fetchall()):
            stems = list(extract_stems(r["title"]))
            _state["posted_articles"].append({
                "title": r["title"],
                "summary": "",
                "norm_title": r["norm_title"],
                "topic_key": r["topic_key"],
                "stems": stems,
                "posted_at": r["posted_at"]
            })
        conn.close()
        save_state()
        print("[Storage] Eski SQLite bazasidagi ma'lumotlar bot_state.json ga muvaffaqiyatli ko'chirildi.")
    except Exception as e:
        print(f"[Storage Ogohlantirish] SQLite import muvaffaqiyatsiz bo'ldi: {e}")

def save_state():
    global _state
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Eski ma'lumotlarni tozalash (hajmi oshib ketmasligi uchun)
    now = time.time()
    cutoff_time = now - (14 * 86400)  # 14 kundan eski o'qilgan ID larni tozalash

    # Faqat 14 kun ichidagi ID lar yoki eng so'nggi 5000 tasini qoldiramiz
    if len(_state["processed_messages"]) > 5000:
        cleaned_proc = {
            k: v for k, v in _state["processed_messages"].items()
            if isinstance(v, (int, float)) and v >= cutoff_time
        }
        _state["processed_messages"] = cleaned_proc

    # Maqolalardan so'nggi 200 tasini saqlab qolamiz
    if len(_state["posted_articles"]) > 200:
        _state["posted_articles"] = _state["posted_articles"][-200:]

    tmp_file = STATE_FILE.with_suffix(".tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(_state, f, ensure_ascii=False, indent=2)
        tmp_file.replace(STATE_FILE)
    except Exception as e:
        print(f"[Storage Xatosi] bot_state.json saqlashda xatolik: {e}")

# Modul yuklanganda bazani ochish
load_state()

def is_message_processed(channel: str, message_id: int) -> bool:
    load_state()
    key = f"{channel}:{message_id}"
    return key in _state["processed_messages"]

def mark_message_processed(channel: str, message_id: int, status: str = "posted"):
    load_state()
    key = f"{channel}:{message_id}"
    _state["processed_messages"][key] = time.time()
    save_state()

def is_duplicate_news(title: str, summary: str = "", topic_key: str = "", window_hours: int = 72) -> bool:
    """
    Turli manba kanallaridagi bir xil mazmundagi xabarlarni 100% aniqlik bilan tutib qoladi.
    - Kunlik postlar (namoz, ob-havo) 18 soat ichida faqat 1 marta chiqishi mumkin.
    - O'zbek tili affikslarini tozalab, o'zaklar o'xshashligini (Jaccard, overlap) tekshiradi.
    - Sarlavha va qisqa mazmun (summary) bo'yicha qat'iy tekshiradi.
    """
    if not title:
        return False
    load_state()

    norm_new = _normalize_text(title)
    norm_topic = _normalize_text(topic_key)
    stems_new = extract_stems(title)
    rec_cat_new = get_recurring_category(title + " " + summary)

    now = time.time()
    min_time = now - (window_hours * 3600)
    recurring_min_time = now - (18 * 3600)  # Kunlik xabarlar uchun 18 soat

    for art in reversed(_state["posted_articles"]):
        posted_at = art.get("posted_at", 0)
        old_title = art.get("title", "")
        old_summary = art.get("summary", "")
        old_norm = art.get("norm_title", _normalize_text(old_title))
        old_topic = _normalize_text(art.get("topic_key", ""))

        # 1. Kunlik takrorlanuvchi postlar (Namoz, Ob-havo, Valyuta): 18 soat ichida faqat 1 marta!
        if rec_cat_new and posted_at >= recurring_min_time:
            rec_cat_old = get_recurring_category(old_title + " " + old_summary)
            if rec_cat_old and rec_cat_new == rec_cat_old:
                return True

        # Qolgan barcha xabarlar 72 soatlik (window_hours) oyna ichida tekshiriladi
        if posted_at < min_time:
            continue

        # 2. To'liq sarlavha mosligi
        if norm_new == old_norm:
            return True

        # 3. Mavzu kaliti (topic_key) mosligi
        if norm_topic and old_topic and len(norm_topic) >= 5 and norm_topic == old_topic:
            return True

        # 4. Sarlavha o'zaklari (Stems) tahlili
        stems_old = set(art.get("stems", [])) or extract_stems(old_title)
        common_stems = stems_new.intersection(stems_old)

        if len(common_stems) >= 3:
            return True

        min_len = min(len(stems_new), len(stems_old)) if stems_new and stems_old else 1
        overlap = len(common_stems) / min_len if min_len > 0 else 0
        if len(common_stems) >= 2 and overlap >= 0.50:
            return True

        union_len = len(stems_new.union(stems_old))
        jaccard = len(common_stems) / union_len if union_len > 0 else 0
        if jaccard >= 0.35:
            return True

        # 5. Qisqa mazmun (Summary) o'zaklari tahlili
        if summary and old_summary:
            sum_stems_new = extract_stems(summary)
            sum_stems_old = extract_stems(old_summary)
            common_sum = sum_stems_new.intersection(sum_stems_old)
            if len(common_sum) >= 4:
                return True

    return False

def mark_news_posted(title: str, summary: str = "", topic_key: str = ""):
    if not title:
        return
    load_state()
    norm_title = _normalize_text(title)
    stems = list(extract_stems(title))

    _state["posted_articles"].append({
        "title": title,
        "summary": summary,
        "norm_title": norm_title,
        "topic_key": topic_key,
        "stems": stems,
        "posted_at": time.time()
    })
    save_state()

def get_last_id(channel: str) -> int:
    load_state()
    return _state["channel_pointers"].get(channel, 0)

def set_last_id(channel: str, last_id: int):
    load_state()
    current = _state["channel_pointers"].get(channel, 0)
    _state["channel_pointers"][channel] = max(current, last_id)
    save_state()
