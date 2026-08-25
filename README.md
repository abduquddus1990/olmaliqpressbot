# OlmaliqpressBot (@olmaliqlik kanali uchun avtomatlashtirilgan yangiliklar boti)

Ushbu bot ko'rsatilgan Telegram kanallaridan yangiliklarni avtomatik qabul qilib, reklamalarni saralab olib tashlaydi va **Google Gemini AI** orqali postlarni o'zbek lotin alifbosida ixcham, qiziqarli va professional qilib tayyorlab, `@olmaliqlik` kanaliga uzatadi.

---

## 📂 Loyiha tuzilishi

- `.env` — Maxfiy kalitlar (Bot Token, Telegram API ID/Hash, Session, Gemini API kalit).
- `config.py` — Barcha konfiguratsiya va manba kanallar ro'yxati.
- `telegram_reader.py` — Telethon yordamida ko'p kanallarni va ulardagi rasmlar/videolarni xavfsiz yuklovchi modul.
- `processor.py` — Gemini AI orqali reklamani filtrlash, matnni lotinlashtirish va qisqa xulosaga keltirish moduli.
- `poster.py` — Telegram Bot API orqali kanalga matn, rasm, video va albomlarni chiroyli formatda joylovchi modul.
- `storage.py` — SQLite ma'lumotlar bazasi orqali dublikatlarni oldini olish moduli.
- `main.py` — Barcha modullarni birlashtiruvchi asosiy boshqaruvchi.
- `run_bot.bat` — 24/7 rejimda ishga tushirish uchun 1-klikli fayl.
- `test_bot.bat` — Barcha manbalardan 1 tadan post olib test qilish fayli.

---

## 🚀 Ishga tushirish rejimlari

### 1. Test rejimi (Har bir kanaldan bittadan post olib kanalga joylash):
```bash
python main.py --test
```
yoki `test_bot.bat` faylini ikki marta bosing.

### 2. Doimiy 24/7 monitoring rejimi:
```bash
python main.py --loop
```
yoki `run_bot.bat` faylini ikki marta bosing.

### 3. Hozirgi eski postlarni o'tkazib yuborish (faqat yangilarini kutish):
```bash
python main.py --catchup
```

---

## ➕ Yangi manba qo'shish

Yangi kanal qo'shish uchun `config.py` faylidagi `SOURCES` massiviga yangi kanal qo'shing:

```python
SOURCES = [
    {"channel": "olmaliqhayoti", "name": "Olmaliq hayoti", "fetch_limit": 10},
    {"channel": "ao_agmk", "name": "AGMK Rasmiy", "fetch_limit": 10},
    {"channel": "olmaliqshaharpressa", "name": "Olmaliq shahar hokimligi", "fetch_limit": 10},
    {"channel": "olmaliq", "name": "Olmaliq", "fetch_limit": 10},
    {"channel": "yangi_kanal_username", "name": "Yangi Kanal Nomi", "fetch_limit": 10},
]
```
