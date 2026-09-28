# -*- coding: utf-8 -*-
"""
Telegram QR Kod orqali yangi StringSession yaratish skripti.
"""
import sys
import qrcode
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import config

if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
    print("XATO: .env faylida TELEGRAM_API_ID va TELEGRAM_API_HASH ko'rsatilmagan!")
    sys.exit(1)

client = TelegramClient(StringSession(), config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
client.connect()

if not client.is_user_authorized():
    print("QR-kod yaratilmoqda...")
    qr_login = client.qr_login()
    
    # Terminalda QR chiqarish
    qr = qrcode.QRCode()
    qr.add_data(qr_login.url)
    qr.print_ascii(invert=True)
    
    print("\n" + "="*50)
    print("TELEFONINGIZDA TELEGRAMNI OCHING:")
    print("Sozlamalar (Settings) -> Qurilmalar (Devices) -> Qurilmani ulash (Link Desktop Device)")
    print("va ekrandagi QR-kodni kamerangiz bilan skaner qiling!")
    print("="*50 + "\n")
    
    try:
        user = qr_login.wait(timeout=60)
        print(f"Muvaffaqiyatli ulandi: {user.first_name}")
    except Exception as e:
        print(f"Xatolik yoki vaqt tugadi: {e}")
        client.disconnect()
        sys.exit(1)

print("\n" + "="*50)
print("SIZNING YANGI SESSION STRING:")
print(client.session.save())
print("="*50)
print("Ushbu satrni .env va GitHub Secrets'ga nusxalang.")
client.disconnect()
