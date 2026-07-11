import io
import traceback
import contextlib
from telethon import TelegramClient, events


async def setup(client: TelegramClient):
    @client.on(events.NewMessage(pattern=r"\.eval(?: |$)([\s\S]*)", outgoing=True))
    async def eval_cmd(event):
        code = event.pattern_match.group(1)
        if not code.strip():
            await event.edit("а код где")
            return
        buf = io.StringIO()
        env = {
            "client": client,
            "event": event,
            "message": event,
            "chat": await event.get_chat(),
        }
        lines = code.strip().splitlines()
        lines[-1] = "__result__ = " + lines[-1]
        wrapped = "async def __eval__():\n" + "\n".join(f"    {line}" for line in lines) + "\n    return locals().get('__result__')"
        try:
            with contextlib.redirect_stdout(buf):
                exec(wrapped, env)
                result = await env["__eval__"]()
        except Exception:
            error = traceback.format_exc()
            await event.edit(f"**ошибка:**\n```{error[-3000:]}```")
            return
        output = buf.getvalue()
        text = "**eval:**\n"
        text += f"```{code}```\n"
        if output:
            text += f"**stdout:**\n```{output[-2000:]}```\n"
        if result is not None:
            text += f"**результат:**\n```{str(result)[-2000:]}```"
        if len(text) > 4000:
            text = text[:4000] + "\n... обрезано"
        await event.edit(text)