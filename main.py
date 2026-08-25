# -*- coding: utf-8 -*-
"""
OlmaliqpressBot - Asosiy boshqaruvchi skript (O'zbek @olmaliqlik va Rus @olmaliqrus kanallari bilan).
"""
import sys
import time
import argparse
from pathlib import Path

# Windows konsolida UTF-8 ni to'g'ri chiqarish
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import config
import storage
import processor
import poster
from telegram_reader import get_telegram_client, fetch_channel_posts, download_post_media

def log(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(config.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def post_to_both_channels(media_items: list, uz_result: dict) -> bool:
    """
    O'zbekcha postni @olmaliqlik kanaliga, uning ruscha tarjimasini esa @olmaliqrus kanaliga joylaydi.
    """
    # 1. @olmaliqlik (UZ) kanaliga joylash
    uz_caption = uz_result["telegram_post"]
    log(f"[UZ Posting] {config.TARGET_CHANNEL_UZ} kanaliga yuborilmoqda...")
    uz_ok = poster.send_media_group_post(media_items, uz_caption, chat_id=config.TARGET_CHANNEL_UZ)

    if not uz_ok:
        log(f"[UZ Error] {config.TARGET_CHANNEL_UZ} kanaliga yuborib bo'lmadi.")
        return False

    log(f"[UZ Success] ✅ {config.TARGET_CHANNEL_UZ} kanaliga post joylandi.")

    # 2. Rus tiliga tarjima qilish
    time.sleep(2)
    log("[RU Translation] Rus tiliga tarjima qilinmoqda...")
    ru_result = processor.translate_to_russian(uz_result["qisqa_mazmun"], uz_result["sarlavha"])

    if not ru_result:
        log("[RU Warning] Rus tiliga tarjima qilib bo'lmadi. Faqat UZ kanalga chiqdi.")
        return True

    # 3. @olmaliqrus (RU) kanaliga joylash
    ru_caption = ru_result["telegram_post_ru"]
    log(f"[RU Posting] {config.TARGET_CHANNEL_RU} kanaliga yuborilmoqda: '{ru_result['sarlavha_ru']}'...")
    ru_ok = poster.send_media_group_post(media_items, ru_caption, chat_id=config.TARGET_CHANNEL_RU)

    if ru_ok:
        log(f"[RU Success] ✅ {config.TARGET_CHANNEL_RU} kanaliga ruscha post joylandi.")
    else:
        log(f"[RU Error] ❌ {config.TARGET_CHANNEL_RU} kanaliga yuborishda xatolik yuz berdi.")

    return True

def run_test_mode(client):
    """
    Test rejimi: 4 ta kanaldan so'nggi rasmli yangilik postlarini olib,
    AI orqali qisqartirib @olmaliqlik va @olmaliqrus kanallariga postlaydi.
    """
    log("=== TEST REJIMI ISHGA TUSHDI ===")
    log(f"Maqsadli kanallar: UZ: {config.TARGET_CHANNEL_UZ} | RU: {config.TARGET_CHANNEL_RU}")
    log(f"Manbalar soni: {len(config.SOURCES)}")

    for source in config.SOURCES:
        ch = source["channel"]
        name = source.get("name", ch)
        log(f"\n---> Manba: @{ch} ({name}) tekshirilmoqda...")

        posts = fetch_channel_posts(client, source, min_id=0, limit=15)
        if not posts:
            log(f"[@{ch}] Xabar topilmadi yoki yuklab bo'lmadi.")
            continue

        selected_post = None
        for p in reversed(posts):
            if not p["text"] or len(p["text"].strip()) < 15:
                continue
            selected_post = p
            break

        if not selected_post:
            log(f"[@{ch}] Mos matnli post topilmadi.")
            continue

        post = selected_post
        raw_text = post["text"]
        log(f"[@{ch}] Tanlangan matn ({len(raw_text)} belgi):\n{raw_text[:120]}...")

        # 1. Faqat rasmli postlar
        media_items = download_post_media(client, post)
        if not media_items:
            log(f"[@{ch}] ⚠️ Postda rasm/video yo'q. Qoidaga ko'ra rasmsiz postlar chiqarilmaydi.")
            continue

        # 2. AI orqali tahlil va qisqartirish
        log(f"[@{ch}] Gemini AI orqali tahlil qilinmoqda...")
        result = processor.process_and_summarize(raw_text)

        if not result:
            log(f"[@{ch}] Xabar reklama deb topildi yoki AI tomonidan rad etildi.")
            continue

        # 3. Kanallararo dublikat tekshiruvi
        if storage.is_duplicate_news(result["sarlavha"], result.get("mavzu_kaliti", "")):
            log(f"[@{ch}] ⚠️ Mazmunan o'xshash xabar avvalroq chiqarilgan: '{result['sarlavha']}'. O'tkazib yuborildi.")
            continue

        log(f"[@{ch}] AI Sarlavha (UZ): {result['sarlavha']}")
        log(f"[@{ch}] AI Qisqa mazmun (1-2 jumla): {result['qisqa_mazmun']}")

        success = post_to_both_channels(media_items, result)

        if success:
            for mid in post["all_ids"]:
                storage.mark_message_processed(ch, mid, "test_posted")
            storage.mark_news_posted(result["sarlavha"], result.get("mavzu_kaliti", ""))
            storage.set_last_id(ch, post["message_id"])

        time.sleep(config.POST_INTERVAL_SECONDS)

    log("\n=== TEST YAKUNLANDI ===")

def run_translate_olmaliqlik_to_rus(client, count: int = 4):
    """
    @olmaliqlik kanalida chiqqan so'nggi 4 ta postni olib,
    rus tiliga tarjima qilib @olmaliqrus kanaliga joylaydi.
    """
    log(f"=== @olmaliqlik KANALIDAGI SO'NGGI {count} TA POSTNI @olmaliqrus GA TARJIMA QILISH ===")
    source_info = {"channel": "olmaliqlik", "name": "Olmaliqlik UZ Kanali"}

    posts = fetch_channel_posts(client, source_info, min_id=0, limit=15)
    if not posts:
        log("[Xato] @olmaliqlik kanalidan postlar olinmadi.")
        return

    # Faqat matnli postlarni ajratib olamiz
    valid_posts = [p for p in posts if p["text"] and len(p["text"].strip()) > 10]
    log(f"[@olmaliqlik] {len(valid_posts)} ta post topildi. So'nggi {count} tasi tanlanmoqda...")

    target_posts = valid_posts[-count:]
    posted_count = 0

    for idx, post in enumerate(target_posts, 1):
        log(f"\n--- Post {idx}/{len(target_posts)} (ID: {post['message_id']}) ---")
        raw_text = post["text"]
        log(f"Asl matn ({len(raw_text)} belgi):\n{raw_text[:120]}...")

        # Medialarni yuklash
        media_items = download_post_media(client, post)
        log(f"Media elementlar soni: {len(media_items)}")

        # Rus tiliga tarjima qilish
        log("Gemini AI orqali rus tiliga tarjima qilinmoqda...")
        ru_res = processor.translate_to_russian(raw_text)

        if not ru_res:
            log("❌ Tarjima qilib bo'lmadi. Keyingi postga o'tilmoqda.")
            continue

        log(f"Sarlavha (RU): {ru_res['sarlavha_ru']}")
        log(f"Qisqa mazmun (RU): {ru_res['qisqa_mazmun_ru']}")

        ru_caption = ru_res["telegram_post_ru"]
        log(f"{config.TARGET_CHANNEL_RU} kanaliga yuborilmoqda...")

        success = poster.send_media_group_post(media_items, ru_caption, chat_id=config.TARGET_CHANNEL_RU)

        if success:
            posted_count += 1
            log(f"✅ {idx}-post {config.TARGET_CHANNEL_RU} kanaliga muvaffaqiyatli joylandi!")
        else:
            log(f"❌ {idx}-postni yuborishda xatolik yuz berdi.")

        time.sleep(config.POST_INTERVAL_SECONDS)

    log(f"\n=== YAKUNLANDI: Jami {posted_count} ta post @olmaliqrus kanaliga chiqarildi ===")

def run_catchup_mode(client):
    """Barcha kanallardagi hozirgi mavjud postlarni 'ko'rilgan' deb belgilaydi."""
    log("=== CATCHUP REJIMI: Hozirgi barcha postlar bazaga kiritilmoqda ===")
    for source in config.SOURCES:
        ch = source["channel"]
        posts = fetch_channel_posts(client, source, min_id=0, limit=20)
        for p in posts:
            for mid in p["all_ids"]:
                storage.mark_message_processed(ch, mid, "caught_up")
            storage.set_last_id(ch, p["message_id"])
        log(f"[@{ch}] {len(posts)} ta post 'o'qilgan' deb belgilandi.")
    log("=== CATCHUP YAKUNLANDI. Endi faqat yangi kelgan postlar chiqariladi ===")

def run_cycle(client):
    """Doimiy yangi postlarni tekshirish davri (UZ va RU kanallarga bir vaqtda joylaydi)."""
    total_posted = 0

    for source in config.SOURCES:
        ch = source["channel"]
        last_id = storage.get_last_id(ch)

        posts = fetch_channel_posts(client, source, min_id=last_id, limit=10)

        for post in posts:
            msg_id = post["message_id"]

            if storage.is_message_processed(ch, msg_id):
                continue

            raw_text = post["text"]
            if not raw_text.strip():
                for mid in post["all_ids"]:
                    storage.mark_message_processed(ch, mid, "no_text")
                storage.set_last_id(ch, msg_id)
                continue

            # 1. Faqat rasmli postlar
            media_items = download_post_media(client, post)
            if not media_items:
                log(f"[@{ch}] Postda media yo'q (faqat rasmli xabarlar qabul qilinadi). O'tkazib yuborildi.")
                for mid in post["all_ids"]:
                    storage.mark_message_processed(ch, mid, "no_media_skipped")
                storage.set_last_id(ch, msg_id)
                continue

            # 2. AI orqali tahlil va qisqartirish
            result = processor.process_and_summarize(raw_text)

            if not result:
                for mid in post["all_ids"]:
                    storage.mark_message_processed(ch, mid, "filtered_ad")
                storage.set_last_id(ch, msg_id)
                continue

            # 3. Kanallararo dublikat tekshiruvi
            if storage.is_duplicate_news(result["sarlavha"], result.get("mavzu_kaliti", "")):
                log(f"[@{ch}] ⚠️ Mazmunan o'xshash xabar avvalroq chiqarilgan: '{result['sarlavha']}'. O'tkazib yuborildi.")
                for mid in post["all_ids"]:
                    storage.mark_message_processed(ch, mid, "duplicate_topic")
                storage.set_last_id(ch, msg_id)
                continue

            # 4. Ikkala kanalga postlash (UZ va RU)
            log(f"[@{ch}] Yangi post chiqarilmoqda: '{result['sarlavha']}' (media: {len(media_items)})")
            success = post_to_both_channels(media_items, result)

            if success:
                total_posted += 1
                for mid in post["all_ids"]:
                    storage.mark_message_processed(ch, mid, "posted")
                storage.mark_news_posted(result["sarlavha"], result.get("mavzu_kaliti", ""))
                storage.set_last_id(ch, msg_id)
                time.sleep(config.POST_INTERVAL_SECONDS)
            else:
                log(f"[@{ch}] ❌ Post yuborishda xatolik!")
                break

    return total_posted

def main():
    parser = argparse.ArgumentParser(description="Olmaliqpress Telegram News Bot")
    parser.add_argument("--test", "-t", action="store_true", help="Manbalardan post olib UZ va RU kanallariga test qilish")
    parser.add_argument("--test-ru", "-tru", action="store_true", help="@olmaliqlik kanalidagi so'nggi 4 ta postni tarjima qilib @olmaliqrus ga joylash")
    parser.add_argument("--catchup", "-c", action="store_true", help="Eski postlarni tashlab yuborish")
    parser.add_argument("--loop", "-l", action="store_true", help="24/7 uzluksiz fonda ishlash")
    args = parser.parse_args()

    log("Bot yuklanmoqda...")
    client = get_telegram_client()

    with client:
        if args.test_ru:
            run_translate_olmaliqlik_to_rus(client, count=4)
            return

        if args.test:
            run_test_mode(client)
            return

        if args.catchup:
            run_catchup_mode(client)
            return

        if args.loop:
            log(f"=== OlmaliqpressBot 24/7 monitoring rejimida ishga tushdi ===")
            log(f"Kanallar: UZ: {config.TARGET_CHANNEL_UZ} | RU: {config.TARGET_CHANNEL_RU}")
            log(f"Tekshirish oralig'i: har {config.POLL_INTERVAL_SECONDS} soniyada.")
            try:
                while True:
                    posted = run_cycle(client)
                    if posted > 0:
                        log(f"Jami {posted} ta yangi post ikkala kanalga joylandi.")
                    time.sleep(config.POLL_INTERVAL_SECONDS)
            except KeyboardInterrupt:
                log("Bot to'xtatildi.")
        else:
            log("Bir martalik tekshiruv boshlandi...")
            posted = run_cycle(client)
            log(f"Yakunlandi. {posted} ta post joylandi.")

if __name__ == "__main__":
    main()
