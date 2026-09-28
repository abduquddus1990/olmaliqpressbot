# -*- coding: utf-8 -*-
"""
Telegram QR Kod orqali yangi StringSession yaratish skripti (2FA Parol qo'llab-quvvatlaydi).
"""
import sys
import asyncio
import qrcode
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import config

if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
    print("XATO: .env faylida TELEGRAM_API_ID va TELEGRAM_API_HASH ko'rsatilmagan!")
    sys.exit(1)

async def main():
    client = TelegramClient(StringSession(), config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("\nQR-kod yaratilmoqda...\n")
        qr_login = await client.qr_login()
        
        # Terminalda QR chiqarish
        qr = qrcode.QRCode()
        qr.add_data(qr_login.url)
        qr.print_ascii(invert=True)
        
        print("\n" + "="*50)
        print("TELEFONINGIZDA TELEGRAMNI OCHING:")
        print("Sozlamalar (Настройки) -> Qurilmalar (Устройства) -> Qurilmani ulash (Подключить устройство)")
        print("va ekrandagi QR-kodni kamerangiz bilan skaner qiling!")
        print("="*50 + "\n")
        
        try:
            user = await qr_login.wait(timeout=120)
        except SessionPasswordNeededError:
            print("\n🔐 Telegramingizda 2 bosqichli himoya (2FA Parol) yoqilgan.")
            pwd = input("Iltimos, Telegram bulutli parolingizni kiriting: ")
            user = await client.sign_in(password=pwd)
        except Exception as e:
            # Ba'zan umumiy Exception ichida "Two-steps verification" deb keladi
            if "Two-steps verification" in str(e) or "password is required" in str(e):
                print("\n🔐 Telegramingizda 2 bosqichli himoya (2FA Parol) yoqilgan.")
                pwd = input("Iltimos, Telegram bulutli parolingizni kiriting: ")
                user = await client.sign_in(password=pwd)
            else:
                print(f"\n❌ Xatolik yoki vaqt tugadi: {e}")
                await client.disconnect()
                return

        name = getattr(user, "first_name", "Telegram User")
        print(f"\n✅ Muvaffaqiyatli ulandi: {name}")

    session_string = client.session.save()
    print("\n" + "="*60)
    print("SIZNING YANGI SESSION STRING:")
    print(session_string)
    print("="*60 + "\n")
    print("Ushbu satrni .env va GitHub Secrets'ga nusxalang.\n")
    
    # .env fayliga avtomatik saqlash
    try:
        env_file = config.BASE_DIR / ".env"
        if env_file.exists():
            content = env_file.read_text(encoding="utf-8")
            import re
            if "TELEGRAM_SESSION=" in content:
                content = re.sub(r'TELEGRAM_SESSION=.*', f'TELEGRAM_SESSION={session_string}', content)
            else:
                content += f"\nTELEGRAM_SESSION={session_string}\n"
            env_file.write_text(content, encoding="utf-8")
            print("✅ .env faylidagi TELEGRAM_SESSION avtomatik yangilandi!")
    except Exception as e:
        pass

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
