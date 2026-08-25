# -*- coding: utf-8 -*-
"""
OlmaliqpressBot - Ma'lumotlar bazasi va dublikatlarni qat'iy nazorat qilish moduli (SQLite).
"""
import sqlite3
import re
import time
import hashlib
from pathlib import Path
import config

def get_connection():
    config.DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
                channel TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                created_at REAL NOT NULL,
                status TEXT DEFAULT 'posted',
                PRIMARY KEY (channel, message_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posted_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                norm_title TEXT NOT NULL,
                topic_key TEXT NOT NULL,
                posted_at REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_state (
                channel TEXT PRIMARY KEY,
                last_id INTEGER NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        conn.commit()

init_db()

def _normalize_text(text: str) -> str:
    """Matnni solishtirish uchun tozalash."""
    if not text:
        return ""
    # Faqat harflar va raqamlarni qoldiramiz
    cleaned = re.sub(r"[^\w\s]", "", text.lower()).strip()
    return cleaned

def is_message_processed(channel: str, message_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM processed_messages WHERE channel = ? AND message_id = ?",
            (channel, message_id)
        )
        return cursor.fetchone() is not None

def mark_message_processed(channel: str, message_id: int, status: str = "posted"):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO processed_messages (channel, message_id, created_at, status) VALUES (?, ?, ?, ?)",
            (channel, message_id, time.time(), status)
        )
        conn.commit()

def _jaccard_similarity(set1: set, set2: set) -> float:
    if not set1 or not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0

def is_duplicate_news(title: str, topic_key: str = "", window_hours: int = config.DUPLICATE_WINDOW_HOURS) -> bool:
    """
    4 ta kanaldagi bir xil mazmunda chiqqan xabarlarni aniqlaydi.
    1. Topic key (mavzu kaliti) o'xshashligi.
    2. Sarlavhadagi so'zlar o'xshashligi (50%+ umumiy so'zlar bo'lsa).
    3. Aniq tenglik.
    """
    if not title:
        return False

    norm_new = _normalize_text(title)
    norm_topic = _normalize_text(topic_key)
    
    words_new = set(w for w in norm_new.split() if len(w) > 2)
    min_time = time.time() - (window_hours * 3600)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title, norm_title, topic_key FROM posted_articles WHERE posted_at >= ?",
            (min_time,)
        )
        rows = cursor.fetchall()

        for row in rows:
            old_norm = row["norm_title"]
            old_topic = _normalize_text(row["topic_key"])

            # 1. Aniq moslik
            if norm_new == old_norm:
                return True

            # 2. Mavzu kaliti bo'yicha moslik (agar ikkalasida ham mavjud bo'lsa)
            if norm_topic and old_topic and len(norm_topic) > 4 and len(old_topic) > 4:
                if norm_topic == old_topic or norm_topic in old_topic or old_topic in norm_topic:
                    return True

            # 3. So'zlar to'plami bo'yicha o'xshashlik (Jaccard similarity >= 0.50)
            words_old = set(w for w in old_norm.split() if len(w) > 2)
            sim = _jaccard_similarity(words_new, words_old)
            if sim >= 0.50:
                return True

            # 4. Agar 3 ta yoki undan ko'p asosiy so'zlar bir xil bo'lsa
            common_words = words_new.intersection(words_old)
            if len(common_words) >= 3 and len(words_new) <= 6:
                return True

    return False

def mark_news_posted(title: str, topic_key: str = ""):
    if not title:
        return
    norm_title = _normalize_text(title)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO posted_articles (title, norm_title, topic_key, posted_at) VALUES (?, ?, ?, ?)",
            (title, norm_title, topic_key, time.time())
        )
        conn.commit()

def get_last_id(channel: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT last_id FROM channel_state WHERE channel = ?", (channel,))
        row = cursor.fetchone()
        return row["last_id"] if row else 0

def set_last_id(channel: str, last_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO channel_state (channel, last_id, updated_at) VALUES (?, ?, ?)",
            (channel, last_id, time.time())
        )
        conn.commit()
