# -*- coding: utf-8 -*-
"""
OlmaliqpressBot - Gemini AI Qayta Ishlash, Reklamani Saralash, Qisqartirish va Rus tiliga Tarjima Moduli.
"""
import sys
import json
import re
import html
import time
import requests
import config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SYSTEM_PROMPT_UZ = """Sen @olmaliqlik Telegram kanali uchun professional yangiliklar muharririsan.
Vazifang: Olmaliq shahri va Toshkent viloyatiga oid manbalardan kelgan xom postlarni tahlil qilish, reklamani aniqlab rad etish va haqiqiy yangilik/ma'lumotlarni o'zbek tilida (FAQAT LOTIN ALIFBOSIDA) juda ixcham, qiziqarli va aniq qilib bayon etish.

QOIDALAR:
1. REKLAMA VA SPAMNI ANIQLASH:
   - Agar post tijoriy reklama, do'kon/xizmat taklifi, pullik e'lon, qimor/stavka, obuna bo'lishga chaqiriq yoki shaxsiy tijorat xizmati haqida bo'lsa: "is_ad": true, "relevant": false qaytar.
   - Agar post shahar hayoti, AGMK, hokimlik qarorlari, ob-havo, madaniy tadbirlar, kommunal soha, sport, ta'lim, favqulodda xabarlar yoki rasmiy ma'lumotlar bo'lsa: "is_ad": false, "relevant": true qaytar.

2. JUDA QISQA VA LAKONIK TUSHUNTIRISH (SUMMARIZATION):
   - Post matni juda ixcham bo'lsin: ko'pi bilan 1-2 ta mazmunli jumla!
   - Keraksiz rasmiyatchilik, kirish so'zlari va uzun jumlalarni olib tashla.
   - Faqat eng asosiy mohiyat, muhim faktlar (raqamlar, summalar, sanalar) qolsin.

3. MAVZU KALITI (DUBLIKATLARNI ANIQLASH UCHUN):
   - Xabarning asosiy mazmunini ifodalovchi 2-3 so'zdan iborat mavzu kalitini ("mavzu_kaliti") lotin yozuvida generatsiya qil (masalan: "agmk-mukofot-puli", "ozarbayjon-prezident-tashrifi", "navoiy-otm-imtihon", "ob-havo-ogohlantirish").

4. 100% LOTIN ALIFBOSI:
   - Chiqish matnida BITTA HAM kirill harfi bo'lishi mumkin emas. Rus yoki kirillcha matn kelsa, to'liq o'zbek lotin yozuviga o'gir.
   - Joy va shaxs nomlari to'g'ri lotin yozuvida berilsin (masalan: "Олмалиқ" -> "Olmaliq", "АГМК" -> "AGMK").

5. JAVOB FORMATI:
   - Faqat toza JSON formatida javob qaytar.

OUTPUT JSON SHABLONI:
{
  "is_ad": false,
  "relevant": true,
  "sarlavha": "Qisqa, qiziqarli va aniq sarlavha (emojisiz)",
  "qisqa_mazmun": "Postning eng asosiy mohiyati 1-2 jumlada",
  "mavzu_kaliti": "asosiy-mavzu-kalit-iborasi",
  "kategoriya": "Shahar / Sanoat / Jamiyat / Kommunal / Favqulodda / Madaniyat / Sport"
}
"""

SYSTEM_PROMPT_RU = """Sen @olmaliqrus Telegram kanali uchun professional yangiliklar muharririsan va tarjimonsan.
Vazifang: @olmaliqlik kanalida chiqqan o'zbekcha yangilik postini rus tiliga (rus tili grammatikasi va jurnalistika uslubiga to'liq mos holda) aniq, ravon va professional tarzda tarjima qilish.

QOIDALAR:
1. Tarjima 100% savodli, ravon va adabiy rus tilida bo'lishi shart.
2. Sarlavha va matn qisqa, lo'nda (1-2 gap) bo'lib, barcha faktlar, raqamlar, summalar, shaxs va joy nomlari (masalan: AGMK -> АГМК, Olmaliq -> Алмалык) aniq saqlansin.
3. Chiqish formati faqat toza JSON.

OUTPUT JSON SHABLONI:
{
  "sarlavha_ru": "Заголовок новости на русском без эмодзи",
  "qisqa_mazmun_ru": "Краткое содержание новости на русском (1-2 предложения)"
}
"""

CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")

def clean_text_before_ai(text: str) -> str:
    if not text:
        return ""
    lines = text.strip().split("\n")
    cleaned_lines = []
    for line in lines:
        if re.search(r"t\.me/\S+|https?://\S+", line) and any(w in line.lower() for w in ["obuna", "kanal", "manba", "ulanish", "bizga qo'shiling", "подпишитесь", "olmaliq yangiliklari"]):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()

def has_blocked_words(text: str) -> bool:
    text_lower = text.lower()
    for kw in config.BLOCKED_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False

def extract_json(raw_response: str) -> dict | None:
    if not raw_response:
        return None
    cleaned = re.sub(r"```(?:json)?", "", raw_response).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", raw_response)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return None

def call_gemini(text: str, system_prompt: str, extra_prompt: str = "") -> dict | None:
    keys = config.GEMINI_KEYS if config.GEMINI_KEYS else [""]
    models = config.FALLBACK_MODELS
    prompt = f"{text}\n\n{extra_prompt}".strip() if extra_prompt else text

    for attempt in range(len(keys) * len(models)):
        key = keys[attempt % len(keys)]
        model = models[(attempt // len(keys)) % len(models)]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.3
            }
        }

        try:
            resp = requests.post(url, params={"key": key}, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates") or []
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts") or []
                    if parts:
                        text_res = parts[0].get("text", "").strip()
                        parsed = extract_json(text_res)
                        if parsed:
                            return parsed
            elif resp.status_code == 429:
                time.sleep(1)
            else:
                time.sleep(1)
        except Exception as e:
            time.sleep(1)

    return None

def safe_html_escape(text: str) -> str:
    return html.escape(text, quote=False)

def process_and_summarize(raw_text: str) -> dict | None:
    if not raw_text or not raw_text.strip():
        return None
    if has_blocked_words(raw_text):
        return None

    cleaned_text = clean_text_before_ai(raw_text)
    if len(cleaned_text) < 10:
        cleaned_text = raw_text.strip()
    if len(cleaned_text) < 10:
        return None

    data = call_gemini(cleaned_text, system_prompt=SYSTEM_PROMPT_UZ)
    if not data or data.get("is_ad", False) or not data.get("relevant", True):
        return None

    has_cyrillic = any(
        CYRILLIC_RE.search(str(data.get(f, ""))) for f in ("sarlavha", "qisqa_mazmun")
    )
    if has_cyrillic:
        retry_data = call_gemini(
            cleaned_text,
            system_prompt=SYSTEM_PROMPT_UZ,
            extra_prompt="DIQQAT: Matnni FAQAT o'zbek lotin alifbosida yoz. Bitta ham kirillcha harf bo'lmasin!"
        )
        if retry_data and not retry_data.get("is_ad", False) and retry_data.get("relevant", True):
            data = retry_data

    sarlavha = (data.get("sarlavha") or "Olmaliq yangiliklari").strip()
    qisqa_mazmun = (data.get("qisqa_mazmun") or cleaned_text).strip()
    mavzu_kaliti = (data.get("mavzu_kaliti") or sarlavha).strip().lower()

    # Toza va qulay standart post dizayni
    post_html = (
        f"<b>⚡️ {safe_html_escape(sarlavha)}</b>\n\n"
        f"{safe_html_escape(qisqa_mazmun)}\n\n"
        f"{config.FOOTER_TEXT_UZ}"
    )

    return {
        "sarlavha": sarlavha,
        "qisqa_mazmun": qisqa_mazmun,
        "mavzu_kaliti": mavzu_kaliti,
        "kategoriya": data.get("kategoriya", "Yangiliklar"),
        "telegram_post": post_html
    }

def translate_to_russian(text_uz: str, title_uz: str = "") -> dict | None:
    if not text_uz or not text_uz.strip():
        return None

    input_text = f"Sarlavha: {title_uz}\nMatn: {text_uz}" if title_uz else text_uz
    cleaned = clean_text_before_ai(input_text)
    if len(cleaned) < 10:
        cleaned = input_text.strip()

    data = call_gemini(cleaned, system_prompt=SYSTEM_PROMPT_RU)
    if not data:
        return None

    sarlavha_ru = (data.get("sarlavha_ru") or "Новости Алмалыка").strip()
    qisqa_mazmun_ru = (data.get("qisqa_mazmun_ru") or "").strip()

    if not qisqa_mazmun_ru:
        return None

    # Toza va qulay standart post dizayni (Ruscha)
    post_html_ru = (
        f"<b>⚡️ {safe_html_escape(sarlavha_ru)}</b>\n\n"
        f"{safe_html_escape(qisqa_mazmun_ru)}\n\n"
        f"{config.FOOTER_TEXT_RU}"
    )

    return {
        "sarlavha_ru": sarlavha_ru,
        "qisqa_mazmun_ru": qisqa_mazmun_ru,
        "telegram_post_ru": post_html_ru
    }
