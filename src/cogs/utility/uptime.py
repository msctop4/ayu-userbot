from telethon import TelegramClient, events
from datetime import datetime

start = datetime.now()

async def setup(client: TelegramClient):

    @client.on(events.NewMessage(pattern=r'\.uptime$', outgoing=True))
    async def uptime_cmd(event):
        delta = datetime.now() - start
        secs = int(delta.total_seconds())
        d = secs // 86400
        secs -= d * 86400
        h = secs // 3600
        secs -= h * 3600
        m = secs // 60
        s = secs - m * 60
        parts = []
        if d:
            parts.append(f"{d}д") # дни
        if h:
            parts.append(f"{h}ч") # часы
        if m:
            parts.append(f"{m}м") # минуты
        parts.append(f"{s}с") # секунды

        await event.edit("uptime " + " ".join(parts))
