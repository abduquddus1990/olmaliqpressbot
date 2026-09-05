# -*- coding: utf-8 -*-
"""
OlmaliqpressBot - Rasmlarni Instagram / Telegram Karusel formatiga avtomatik moslashtirish moduli.
"""
import io
from PIL import Image, ImageFilter, ImageOps

def normalize_image_for_carousel(image_bytes: bytes, target_size: tuple[int, int] = (1080, 1350)) -> bytes:
    """
    Bitta rasmni berilgan standart o'lchamga (masalan 4:5 vertikal 1080x1350)
    chiroyli xiralashtirilgan fon (blurred background) bilan moslashtiradi.
    """
    try:
        im = Image.open(io.BytesIO(image_bytes))
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        
        tw, th = target_size
        
        curr_ratio = round(im.width / im.height, 2)
        target_ratio = round(tw / th, 2)
        if curr_ratio == target_ratio and im.width >= 600:
            return image_bytes

        # Fon: rasmni kattalashtirib, xiralashtiramiz (blurred background)
        bg = im.copy().resize((tw, th), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
        
        # Asosiy rasm: proporsiyani saqlagan holda sig'diramiz
        im_fitted = ImageOps.contain(im, (tw, th), Image.Resampling.LANCZOS)
        
        # O'rtasiga joylashtiramiz
        paste_x = (tw - im_fitted.width) // 2
        paste_y = (th - im_fitted.height) // 2
        bg.paste(im_fitted, (paste_x, paste_y))
        
        out_buf = io.BytesIO()
        bg.save(out_buf, format="JPEG", quality=93)
        return out_buf.getvalue()
    except Exception as e:
        print(f"[MediaProcessor Xato] {e}")
        return image_bytes

def process_album_media(media_items: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    """
    Agar postda bir nechta rasm (albom/karusel) bo'lsa, ularning barchasini
    bir xil standart o'lchamga keltiradi.
    """
    if not media_items or len(media_items) <= 1:
        return media_items

    processed = []
    for kind, b in media_items:
        if kind == "photo":
            norm_b = normalize_image_for_carousel(b)
            processed.append((kind, norm_b))
        else:
            processed.append((kind, b))
            
    return processed
