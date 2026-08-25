# -*- coding: utf-8 -*-
"""
OlmaliqpressBot - Barcha konfiguratsiya va sozlamalar fayli.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# ---------- ASOSIY TELEGRAM BOT SOZLAMALARI ----------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# O'zbek va Rus kanallari
TARGET_CHANNEL_UZ = os.getenv("TARGET_CHANNEL", "@olmaliqlik").strip()
TARGET_CHANNEL_RU = os.getenv("TARGET_CHANNEL_RU", "-1002262312107").strip()

TARGET_CHANNEL = TARGET_CHANNEL_UZ

# ---------- GEMINI AI SOZLAMALARI ----------
RAW_GEMINI_KEYS = os.getenv("GEMINI_API_KEY", "")
GEMINI_KEYS = [k.strip() for k in RAW_GEMINI_KEYS.split(",") if k.strip()]
DEFAULT_MODEL = os.getenv("GEMINI_MODEL") or "gemini-3.5-flash"
FALLBACK_MODELS = list(dict.fromkeys([m for m in [DEFAULT_MODEL, "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-flash-latest"] if m]))

# ---------- TELEGRAM USER (TELETHON) SOZLAMALARI ----------
_raw_api_id = os.getenv("TELEGRAM_API_ID", "0").strip()
TELEGRAM_API_ID = int(_raw_api_id) if _raw_api_id.isdigit() else 0
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "").strip()
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", "").strip()

# ---------- YANGILIK MANBALARI ----------
SOURCES = [
    {
        "channel": "olmaliqhayoti",
        "name": "Olmaliq hayoti",
        "fetch_limit": 10,
    },
    {
        "channel": "ao_agmk",
        "name": "AGMK Rasmiy",
        "fetch_limit": 10,
    },
    {
        "channel": "olmaliqshaharpressa",
        "name": "Olmaliq shahar hokimligi",
        "fetch_limit": 10,
    },
    {
        "channel": "olmaliq",
        "name": "Olmaliq",
        "fetch_limit": 10,
    },
]

# ---------- VAQT VA CHEKLOVLAR ----------
POST_INTERVAL_SECONDS = 5            # Postlar orasidagi minimal tanaffus (soniyada)
POLL_INTERVAL_SECONDS = 60           # Doimiy tsiklda kanallarni qayta tekshirish oralig'i (soniyada)
DUPLICATE_WINDOW_HOURS = 48          # Dublikat xabarlarni saqlash va tekshirish vaqti (soatda)

# Media / Xabar limitlari
PHOTO_CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096

# ---------- POST SHABLONI VA IMZOLAR (FOOTER) ----------
FOOTER_TEXT_UZ = "📍 <b>Olmaliq Yangiliklari:</b> @olmaliqlik"
FOOTER_TEXT_RU = "📍 <b>Новости Алмалыка:</b> @olmaliqrus"
FOOTER_TEXT = FOOTER_TEXT_UZ

# ---------- BLOKLANGAN KALIT SO'ZLAR (Qat'iy Reklama va Qimor filtri) ----------
BLOCKED_KEYWORDS = [
    "1xbet", "1хбет", "mostbet", "мостбет", "melbet", "мелбет",
    "fonbet", "фонбет", "parimatch", "париматч", "betwinner", "бетвиннер",
    "bet365", "olimpbet", "олимпбет", "winline", "винлайн", "leon", "леон",
    "stavka", "stavki", "ставка", "ставки", "ставок", "коэффициент",
    "koeffitsient", "koeffitsent", "prognoz", "букмекер", "bukmeker",
    "казино", "kazino", "casino", "промокод", "promokod", "фриibet", "fribet",
    "azartli o'yin", "азартные игры", "pul yutish", "aviator", "авиатор",
    "rekvizit", "karta raqami", "plastik karta", "reklama berish uchun", "hamkorlik uchun",
    "reklama narxi", "реклама учун", "aloqa uchun: @"
]

# SQLite ma'lumotlar bazasi fayli
DB_FILE = BASE_DIR / "data" / "bot_database.db"
LOG_FILE = BASE_DIR / "data" / "bot_log.txt"
