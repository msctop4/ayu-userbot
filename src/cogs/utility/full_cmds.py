from telethon import events, TelegramClient


async def setup(client: TelegramClient):
    @client.on(events.NewMessage(pattern=r"\.cmds", outgoing=True))
    async def cmds_cmd(event):
        handlers = client.list_event_handlers()

        count = sum(
            1 for callback, ev in handlers
            if isinstance(ev, events.NewMessage) and getattr(ev, "pattern", None))

        text = f"**всего команд:** `{count}`"

        await event.edit(text)