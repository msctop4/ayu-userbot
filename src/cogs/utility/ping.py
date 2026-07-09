import time
from telethon import events, TelegramClient


async def setup(client: TelegramClient):
    @client.on(events.NewMessage(pattern=r"\.ping", outgoing=True))
    async def ping_cmd(event):
        start = time.perf_counter()
        await client.get_me()
        tg_ms = (time.perf_counter() - start) * 1000

        text = (f"**ping:** `{round(tg_ms)} мс`")

        await event.edit(text)