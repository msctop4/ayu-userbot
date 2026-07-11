import os
import html
import tempfile
from datetime import timezone
from telethon import TelegramClient, events

htmlpage = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{
    background: #0e1621;
    color: #e1e1e1;
    font-family: -apple-system, Segoe UI, Roboto, sans-serif;
    max-width: 720px;
    margin: 0 auto;
    padding: 20px;
}}
h1 {{
    font-size: 18px;
    color: #8ab4f8;
    border-bottom: 1px solid #2b3a4a;
    padding-bottom: 10px;
}}
.msg {{
    margin: 10px 0;
    padding: 8px 12px;
    background: #182533;
    border-radius: 10px;
    max-width: 80%;
}}
.msg.out {{
    background: #2b5278;
    margin-left: auto;
}}
.sender {{
    font-size: 13px;
    font-weight: 600;
    color: #7fb0ff;
    margin-bottom: 3px;
}}
.text {{
    font-size: 14px;
    white-space: pre-wrap;
    word-wrap: break-word;
}}
.media {{
    font-size: 13px;
    color: #9aa7b0;
    font-style: italic;
}}
.time {{
    font-size: 11px;
    color: #6b7a85;
    margin-top: 4px;
    text-align: right;
}}
</style>
</head>
<body>
<h1>{title}</h1>
{messages}
</body>
</html>
"""

MSG_TEMPLATE = """<div class="msg{out_class}">
<div class="sender">{sender}</div>
<div class="{content_class}">{content}</div>
<div class="time">{time}</div>
</div>
"""

MEDIA_LABELS = {
    "photo": "📷 фото",
    "document": "📎 файл",
    "video": "🎬 видео",
    "voice": "🎤 голосовое",
    "audio": "🎵 аудио",
    "sticker": "🖼 стикер",
    "gif": "🎞 гиф",
}


def media_label(msg):
    if msg.photo:
        return MEDIA_LABELS["photo"]
    if msg.voice:
        return MEDIA_LABELS["voice"]
    if msg.video:
        return MEDIA_LABELS["video"]
    if msg.audio:
        return MEDIA_LABELS["audio"]
    if msg.sticker:
        return MEDIA_LABELS["sticker"]
    if msg.gif:
        return MEDIA_LABELS["gif"]
    if msg.document:
        return MEDIA_LABELS["document"]
    return "📎 медиа"


async def setup(client: TelegramClient):
    @client.on(events.NewMessage(pattern=r"\.export(?:\s+(\d+))?$", outgoing=True))
    async def export_cmd(event):
        count = int(event.pattern_match.group(1)) if event.pattern_match.group(1) else 100
        if count < 1 or count > 5000:
            await event.edit("количество от 1 до 5000")
            return
        await event.edit(f"собираю последние {count} сообщений...")
        chat = await event.get_chat()
        title = getattr(chat, "title", None) or getattr(chat, "first_name", None) or "чат"
        me = await client.get_me()
        raw = []
        async for msg in client.iter_messages(event.chat_id, limit=count):
            raw.append(msg)
        raw.reverse()
        sender_cache = {}
        blocks = []
        for msg in raw:
            sender_id = msg.sender_id
            if sender_id not in sender_cache:
                try:
                    sender = await msg.get_sender()
                    name = getattr(sender, "first_name", None) or getattr(sender, "title", None) or "неизвестно"
                    last = getattr(sender, "last_name", None)
                    if last:
                        name += f" {last}"
                except Exception:
                    name = "неизвестно"
                sender_cache[sender_id] = name
            sender_name = sender_cache[sender_id]
            out_class = " out" if sender_id == me.id else ""
            local_time = msg.date.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M")
            if msg.media:
                content_class = "media"
                content = media_label(msg)
                if msg.text:
                    content += f"<br>{html.escape(msg.text)}"
            elif msg.text:
                content_class = "text"
                content = html.escape(msg.text)
            else:
                content_class = "text"
                content = "<i>пусто</i>"

            blocks.append(MSG_TEMPLATE.format(
                out_class=out_class,
                sender=html.escape(sender_name),
                content_class=content_class,
                content=content,
                time=local_time,
            ))

        page = htmlpage.format(title=html.escape(str(title)), messages="".join(blocks))

        path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
                f.write(page)
                path = f.name
            await client.send_file(
                "me",
                path,
                caption=f"экспорт чата **{title}**, сообщений: {len(raw)}",
                force_document=True,
            )
            await event.edit(f"готово, экспортировано {len(raw)} сообщений, отправил в избранное")
        except Exception as e:
            await event.edit(f"ошибка при экспорте: {e}")
        finally:
            if path and os.path.exists(path):
                os.remove(path)