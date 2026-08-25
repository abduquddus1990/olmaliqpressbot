# -*- coding: utf-8 -*-
"""
Yangi Telegram StringSession yaratish skripti.
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import config

if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
    print("XATO: .env faylida TELEGRAM_API_ID va TELEGRAM_API_HASH ko'rsatilmagan!")
    exit(1)

print("Telegramga ulanish...")
with TelegramClient(StringSession(), config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH) as client:
    print("\n" + "="*50)
    print("SIZNING YANGI SESSION STRING:")
    print(client.session.save())
    print("="*50)
    print("Ushbu satrni .env faylidagi TELEGRAM_SESSION qatoriga nusxalang.")
