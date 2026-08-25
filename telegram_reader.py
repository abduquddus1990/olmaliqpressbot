# -*- coding: utf-8 -*-
"""
OlmaliqpressBot - Telethon orqali Telegram kanallardan xabarlarni o'qish moduli (Tezkor va Optimallashgan).
"""
import io
import time
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import config

MAX_MEDIA_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB gacha bo'lgan medialar yuklanadi

def is_video_message(msg) -> bool:
    if msg.video:
        return True
    if msg.document:
        mime = getattr(msg.document, "mime_type", "") or ""
        if "video" in mime:
            return True
    return False

def get_media_size(msg) -> int:
    if msg.file:
        return getattr(msg.file, "size", 0) or 0
    return 0

def group_messages(messages):
    """Xabarlarni grouped_id bo'yicha albomlarga ajratish."""
    groups = []
    current = []
    current_gid = None
    
    for m in messages:
        if m.grouped_id is not None and m.grouped_id == current_gid:
            current.append(m)
        else:
            if current:
                groups.append(current)
            current = [m]
            current_gid = m.grouped_id
            
    if current:
        groups.append(current)
        
    return groups

def fetch_channel_posts(client: TelegramClient, source_info: dict, min_id: int = 0, limit: int = 10):
    channel = source_info["channel"]
    name = source_info.get("name", channel)
    
    try:
        if min_id > 0:
            raw_messages = list(client.iter_messages(channel, min_id=min_id, reverse=True, limit=limit))
        else:
            raw_messages = list(reversed(client.get_messages(channel, limit=limit)))
    except Exception as e:
        print(f"[Telethon Xatosi] @{channel} kanalidan o'qib bo'lmadi: {e}")
        return []

    if not raw_messages:
        return []

    grouped = group_messages(raw_messages)
    posts = []

    for group in grouped:
        main_text = next((m.text for m in group if m.text), "") or ""
        max_id = max(m.id for m in group)

        posts.append({
            "channel": channel,
            "source_name": name,
            "message_id": max_id,
            "all_ids": [m.id for m in group],
            "messages": group,
            "text": main_text,
        })

    return posts

def download_post_media(client: TelegramClient, post: dict) -> list[tuple[str, bytes]]:
    media_items = []
    group = post.get("messages", [])

    for m in group:
        size = get_media_size(m)
        if size > MAX_MEDIA_SIZE_BYTES:
            continue

        if m.photo:
            buf = io.BytesIO()
            try:
                client.download_media(m, file=buf)
                buf.seek(0)
                media_items.append(("photo", buf.getvalue()))
            except Exception as e:
                print(f"[Media yuklash xatosi] {post['channel']}:{m.id}: {e}")
        elif is_video_message(m):
            buf = io.BytesIO()
            try:
                client.download_media(m, file=buf)
                buf.seek(0)
                media_items.append(("video", buf.getvalue()))
            except Exception as e:
                print(f"[Video yuklash xatosi] {post['channel']}:{m.id}: {e}")

    return media_items

def get_telegram_client():
    missing = []
    if not config.TELEGRAM_API_ID:
        missing.append("TELEGRAM_API_ID")
    if not config.TELEGRAM_API_HASH:
        missing.append("TELEGRAM_API_HASH")
    if not config.TELEGRAM_SESSION:
        missing.append("TELEGRAM_SESSION")

    if missing:
        raise ValueError(
            f"Telegram API sozlamalari to'liq emas! Quyidagi Secret'lar topilmadi yoki bo'sh: {', '.join(missing)}.\n"
            f"Iltimos, GitHub Repo -> Settings -> Secrets and variables -> Actions bo'limiga ushbu kalitlarni kiriting."
        )

    return TelegramClient(
        StringSession(config.TELEGRAM_SESSION),
        config.TELEGRAM_API_ID,
        config.TELEGRAM_API_HASH,
        connection_retries=10,
        retry_delay=3,
        timeout=30
    )
