# -*- coding: utf-8 -*-
"""
OlmaliqpressBot - Telegram kanallardan xabarlarni o'qish moduli.
Session (StringSession) talab qilmaydigan, AuthKeyDuplicatedError xatolaridan 100% xoli,
doimiy barqaror Web Reader mexanizmi asosida ishlaydi.
"""
import re
import datetime
import requests
from bs4 import BeautifulSoup
import config

MAX_MEDIA_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB gacha bo'lgan medialar yuklanadi

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "uz,ru;q=0.9,en;q=0.8",
}

class DummyClient:
    """
    main.py dagi `with client:` konteksti bilan to'liq moslikni ta'minlaydigan
    xavfsiz obyekt. Hech qanday Telethon sessiyasi talab qilmaydi va hech qachon uzilib qolmaydi.
    """
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def is_connected(self):
        return True

    def connect(self):
        pass

    def disconnect(self):
        pass

def _extract_bg_url(style: str) -> str:
    if not style:
        return ""
    match = re.search(r"background-image\s*:\s*url\(['\"]?(.*?)['\"]?\)", style)
    return match.group(1).strip() if match else ""

def fetch_channel_posts(client, source_info: dict, min_id: int = 0, limit: int = 20) -> list[dict]:
    """
    Telegram ommaviy kanalining web-sahifasidan (https://t.me/s/<channel>)
    eng so'nggi postlarni o'qiydi.
    """
    channel = source_info["channel"].lstrip("@").strip()
    name = source_info.get("name", channel)
    url = f"https://t.me/s/{channel}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"[WebReader Xatosi] @{channel} sahifasi ochilmadi (status={resp.status_code})")
            return []
    except Exception as e:
        print(f"[WebReader Ulanish Xatosi] @{channel}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    widgets = soup.find_all("div", class_="tgme_widget_message")
    if not widgets:
        return []

    posts = []
    for w in widgets:
        data_post = w.get("data-post", "")
        if not data_post or "/" not in data_post:
            continue
        try:
            msg_id = int(data_post.split("/")[-1])
        except ValueError:
            continue

        if min_id > 0 and msg_id <= min_id:
            continue

        # Matnni ajratib olish
        text_el = w.find("div", class_="tgme_widget_message_text")
        if text_el:
            # <br> teglarini yangi qatorga almashtiramiz
            for br in text_el.find_all("br"):
                br.replace_with("\n")
            main_text = text_el.get_text()
        else:
            main_text = ""

        # Vaqtni ajratib olish (a.tgme_widget_message_date time)
        post_date = None
        time_el = w.select_one("a.tgme_widget_message_date time")
        if not time_el:
            # Zaxira qidiruv: datetime atributiga ega har qanday time tegi
            for t_candidate in w.find_all("time"):
                if t_candidate.get("datetime"):
                    time_el = t_candidate
                    break

        if time_el and time_el.get("datetime"):
            dt_str = time_el.get("datetime")
            try:
                post_date = datetime.datetime.fromisoformat(dt_str)
                if post_date.tzinfo is None:
                    post_date = post_date.replace(tzinfo=datetime.timezone.utc)
            except Exception:
                post_date = None

        # Rasmlar (bitta rasm yoki albomdagi barcha rasmlar)
        photo_urls = []
        for pw in w.find_all("a", class_="tgme_widget_message_photo_wrap"):
            bg_url = _extract_bg_url(pw.get("style", ""))
            if bg_url and bg_url not in photo_urls:
                photo_urls.append(bg_url)

        # Videolar (agar to'g'ridan-to'g'ri mp4 link bo'lsa)
        video_urls = []
        for v in w.find_all("video"):
            src = (v.get("src") or "").strip()
            if src and src.startswith("http") and src not in video_urls:
                video_urls.append(src)

        # Video muqovasi (thumbnail) yoki Link preview rasmi (agar postda katta video bo'lsa)
        thumb_urls = []
        for thumb_el in w.find_all("i", class_=["tgme_widget_message_video_thumb", "link_preview_image"]):
            bg_url = _extract_bg_url(thumb_el.get("style", ""))
            if bg_url and bg_url not in thumb_urls and bg_url not in photo_urls:
                thumb_urls.append(bg_url)

        posts.append({
            "channel": source_info["channel"],
            "source_name": name,
            "message_id": msg_id,
            "all_ids": [msg_id],
            "text": main_text,
            "date": post_date,
            "photo_urls": photo_urls,
            "video_urls": video_urls,
            "thumb_urls": thumb_urls,
        })

    if limit and len(posts) > limit:
        posts = posts[-limit:]

    return posts

def download_post_media(client, post: dict) -> list[tuple[str, bytes]]:
    """
    Post ichidagi rasmlar yoki videolarni yuklab oladi.
    """
    media_items: list[tuple[str, bytes]] = []

    # 1. Asosiy rasmlar (yoki albom)
    for p_url in post.get("photo_urls", []):
        try:
            r = requests.get(p_url, headers=HEADERS, timeout=25)
            if r.status_code == 200 and r.content and len(r.content) <= MAX_MEDIA_SIZE_BYTES:
                media_items.append(("photo", r.content))
        except Exception as e:
            print(f"[Media yuklash xatosi - photo] {post.get('channel')}:{post.get('message_id')}: {e}")

    # 2. Videolar (agar rasm bo'lmasa yoki qo'shimcha video bo'lsa)
    if not media_items:
        for v_url in post.get("video_urls", []):
            try:
                r = requests.get(v_url, headers=HEADERS, timeout=45, stream=True)
                if r.status_code == 200:
                    content_length = int(r.headers.get("Content-Length", 0) or 0)
                    if content_length > MAX_MEDIA_SIZE_BYTES:
                        r.close()
                        continue
                    data = r.content
                    if data and len(data) <= MAX_MEDIA_SIZE_BYTES:
                        media_items.append(("video", data))
            except Exception as e:
                print(f"[Media yuklash xatosi - video] {post.get('channel')}:{post.get('message_id')}: {e}")

    # 3. Agar katta hajmli video tufayli video yuklanmagan bo'lsa, uning sifatli muqova rasmini (thumbnail) olamiz
    if not media_items:
        for t_url in post.get("thumb_urls", []):
            try:
                r = requests.get(t_url, headers=HEADERS, timeout=20)
                if r.status_code == 200 and r.content and len(r.content) <= MAX_MEDIA_SIZE_BYTES:
                    media_items.append(("photo", r.content))
                    break
            except Exception as e:
                print(f"[Media yuklash xatosi - thumb] {post.get('channel')}:{post.get('message_id')}: {e}")

    return media_items

def get_telegram_client():
    """
    Session talab qilmaydigan doimiy faol mijoz obyektini qaytaradi.
    """
    return DummyClient()
