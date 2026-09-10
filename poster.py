# -*- coding: utf-8 -*-
"""
OlmaliqpressBot - Telegram Bot API orqali kanalga post yuborish moduli (UZ va RU kanallarni qo'llab-quvvatlaydi).
"""
import time
import json
import requests
import config
import media_processor

BASE_URL = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"

def _post_with_retry(url: str, **kwargs) -> requests.Response | None:
    retries = 3
    for attempt in range(1, retries + 1):
        try:
            # Agar fayl buferi berilgan bo'lsa, qayta o'qish uchun boshiga o'tkazish
            for _, file_tuple in kwargs.get("files", {}).items():
                if isinstance(file_tuple, tuple) and len(file_tuple) > 1:
                    buf = file_tuple[1]
                    if hasattr(buf, "seek"):
                        buf.seek(0)

            resp = requests.post(url, **kwargs)
            if resp.status_code == 429:
                retry_after = int(resp.json().get("parameters", {}).get("retry_after", 5))
                print(f"[Telegram 429] Rate limit. {retry_after}s kutilmoqda...")
                time.sleep(retry_after + 1)
                continue

            if resp.ok:
                return resp
            else:
                print(f"[Telegram API Xatosi - {attempt}/{retries}] Status: {resp.status_code}, Response: {resp.text}")
                time.sleep(2)
        except Exception as e:
            print(f"[Telegram So'rov Xatosi - {attempt}/{retries}] {e}")
            time.sleep(2)

    return None

def send_text_post(text: str, chat_id: str | None = None) -> bool:
    target = chat_id or config.TARGET_CHANNEL_UZ
    resp = _post_with_retry(
        f"{BASE_URL}/sendMessage",
        data={
            "chat_id": target,
            "text": text[:config.TEXT_LIMIT],
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        },
        timeout=30
    )
    return resp is not None and resp.ok

def send_photo_post(photo_bytes: bytes, caption: str, chat_id: str | None = None) -> bool:
    target = chat_id or config.TARGET_CHANNEL_UZ
    cap = caption if len(caption) <= config.PHOTO_CAPTION_LIMIT else caption[:config.PHOTO_CAPTION_LIMIT - 3] + "..."
    resp = _post_with_retry(
        f"{BASE_URL}/sendPhoto",
        data={
            "chat_id": target,
            "caption": cap,
            "parse_mode": "HTML"
        },
        files={"photo": ("image.jpg", photo_bytes)},
        timeout=120
    )
    return resp is not None and resp.ok

def send_video_post(video_bytes: bytes, caption: str, chat_id: str | None = None) -> bool:
    target = chat_id or config.TARGET_CHANNEL_UZ
    cap = caption if len(caption) <= config.PHOTO_CAPTION_LIMIT else caption[:config.PHOTO_CAPTION_LIMIT - 3] + "..."
    resp = _post_with_retry(
        f"{BASE_URL}/sendVideo",
        data={
            "chat_id": target,
            "caption": cap,
            "parse_mode": "HTML",
            "supports_streaming": "true"
        },
        files={"video": ("video.mp4", video_bytes)},
        timeout=180
    )
    return resp is not None and resp.ok

import re

def html_to_rich_text(html_text: str) -> list:
    """
    HTML teglari (<b>...</b>) bo'lgan matnni Rich Message paragraph text elementlariga aylantiradi.
    """
    parts = []
    pattern = re.compile(r'<b>(.*?)</b>', re.DOTALL)
    last_idx = 0
    for match in pattern.finditer(html_text):
        start, end = match.span()
        if start > last_idx:
            plain = html_text[last_idx:start]
            if plain:
                parts.append(plain)
        bold_content = match.group(1)
        if bold_content:
            parts.append({"type": "bold", "text": bold_content})
        last_idx = end
    if last_idx < len(html_text):
        remaining = html_text[last_idx:]
        if remaining:
            parts.append(remaining)
    return parts if parts else [html_text]

def send_slideshow_post(media_items: list[tuple[str, bytes]], caption: str, chat_id: str | None = None) -> bool:
    """
    Telegram Rich Message API (sendRichMessage + InputRichBlockSlideshow) orqali
    rasmlarni haqiqiy native swipeable Slideshow / Carousel ko'rinishida jo'natadi.
    Pagination nuqtalari (● ○ ○) va silliq suriladigan slayder bilan chiqadi.
    """
    target = chat_id or config.TARGET_CHANNEL_UZ

    if not media_items:
        return send_text_post(caption, chat_id=target)

    # Albom rasmlarini bir xil karusel o'lchamiga moslashtiramiz
    normalized_media = media_processor.process_album_media(media_items)

    if len(normalized_media) == 1:
        kind, buf = normalized_media[0]
        if kind == "photo":
            return send_photo_post(buf, caption, chat_id=target)
        else:
            return send_video_post(buf, caption, chat_id=target)

    # 2 yoki undan ortiq rasmlar uchun Native Slideshow (sendRichMessage)
    slideshow_blocks = []
    files = {}

    for i, (kind, buf) in enumerate(normalized_media):
        if kind == "photo":
            attach_name = f"photo_{i}"
            slideshow_blocks.append({
                "type": "photo",
                "photo": {
                    "type": "photo",
                    "media": f"attach://{attach_name}"
                }
            })
            files[attach_name] = (f"{attach_name}.jpg", buf)

    if not slideshow_blocks:
        return send_text_post(caption, chat_id=target)

    # Matnni HTML formatdan Rich Text paragraph strukturasiga o'giramiz
    rich_text_parts = html_to_rich_text(caption)

    rich_message = {
        "blocks": [
            {
                "type": "slideshow",
                "blocks": slideshow_blocks
            },
            {
                "type": "paragraph",
                "text": rich_text_parts
            }
        ]
    }

    data = {
        "chat_id": target,
        "rich_message": json.dumps(rich_message)
    }

    resp = _post_with_retry(
        f"{BASE_URL}/sendRichMessage",
        data=data,
        files=files,
        timeout=240
    )

    if resp is not None and resp.ok:
        return True

    print("[sendRichMessage Ogohlantirish] sendRichMessage xato berdi, sendMediaGroup fallback ishlatilmoqda...")
    return _send_media_group_fallback(normalized_media, caption, target)

def _send_media_group_fallback(normalized_media: list[tuple[str, bytes]], caption: str, target: str) -> bool:
    """Zaxira jo'natish usuli"""
    media = []
    files = {}
    cap = caption if len(caption) <= config.PHOTO_CAPTION_LIMIT else caption[:config.PHOTO_CAPTION_LIMIT - 3] + "..."

    for i, (kind, buf) in enumerate(normalized_media):
        name = f"file{i}"
        entry = {
            "type": kind,
            "media": f"attach://{name}"
        }
        if i == 0 and cap:
            entry["caption"] = cap
            entry["parse_mode"] = "HTML"
            
        media.append(entry)
        files[name] = (f"{name}.mp4" if kind == "video" else f"{name}.jpg", buf)

    resp = _post_with_retry(
        f"{BASE_URL}/sendMediaGroup",
        data={
            "chat_id": target,
            "media": json.dumps(media)
        },
        files=files,
        timeout=240
    )
    return resp is not None and resp.ok

# Mavjud kodlar bilan to'liq moslik uchun alias
def send_media_group_post(media_items: list[tuple[str, bytes]], caption: str, chat_id: str | None = None) -> bool:
    return send_slideshow_post(media_items, caption, chat_id=chat_id)
