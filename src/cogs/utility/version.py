import aiohttp, os
from telethon import events, TelegramClient

github_version = "https://raw.githubusercontent.com/msctop4/ayu-userbot/main/__version__"
local_version_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "__version__")

def local_version():
    with open(local_version_dir, "r", encoding="utf-8") as f:
        return f.read().strip()

async def git_version():
    async with aiohttp.ClientSession() as session:
        async with session.get(github_version, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.text()
    return data.strip()

async def setup(client: TelegramClient):
    @client.on(events.NewMessage(pattern=r"\.version", outgoing=True))
    async def version_cmd(event):
        current = local_version()
        try:
            latest = await git_version()
        except Exception:
            latest = "не имеется файл __version__"
        text = ("**Версии UserBot'а**\n\n"f"**Текущая:** `{current}`\n"f"**Последняя:** `{latest}`")
        await event.edit(text)