import os
import tempfile
from datetime import datetime, timedelta, timezone
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from telethon import TelegramClient, events


WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


async def setup(client: TelegramClient):
    @client.on(events.NewMessage(pattern=r"\.chatactivity(?:\s+(\d+))?$", outgoing=True))
    async def chatactivity_cmd(event):
        days = int(event.pattern_match.group(1)) if event.pattern_match.group(1) else 7
        if days < 1 or days > 90:
            await event.edit("период от 1 до 90 дней")
            return
        await event.edit(f"считаю активность за последние {days} дн...")
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        hours = [0] * 24
        weekdays = [0] * 7
        total = 0
        max_scan = 20000
        async for msg in client.iter_messages(event.chat_id, limit=max_scan):
            if msg.date < cutoff:
                break
            total += 1
            hours[msg.date.hour] += 1
            weekdays[msg.date.weekday()] += 1
        if total == 0:
            await event.edit("за этот период сообщений не нашёл")
            return
        peak_hour = hours.index(max(hours))
        peak_day = WEEKDAYS_RU[weekdays.index(max(weekdays))]
        chat = await event.get_chat()
        title = getattr(chat, "title", None) or getattr(chat, "first_name", None) or "чат"
        plt.style.use("dark_background")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
        fig.patch.set_facecolor("#0e1621")
        for ax in (ax1, ax2):
            ax.set_facecolor("#0e1621")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color("#2b3a4a")
            ax.spines["bottom"].set_color("#2b3a4a")
            ax.tick_params(colors="#9aa7b0")
        ax1.bar(range(24), hours, color="#7fb0ff")
        ax1.set_xticks(range(0, 24, 2))
        ax1.set_xlabel("час (UTC)", color="#9aa7b0")
        ax1.set_title("по часам", color="#e1e1e1")
        ax2.bar(range(7), weekdays, color="#2b5278")
        ax2.set_xticks(range(7))
        ax2.set_xticklabels(WEEKDAYS_RU)
        ax2.set_title("по дням недели", color="#e1e1e1")
        fig.suptitle(f"активность: {title}", color="#e1e1e1", fontsize=13)
        fig.tight_layout()
        path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                path = f.name
            fig.savefig(path, facecolor=fig.get_facecolor(), dpi=130)
            plt.close(fig)

            caption = (
                f"**активность чата за {days} дн**\n"
                f"всего сообщений: `{total}`\n"
                f"пиковый час: `{peak_hour}:00 UTC`\n"
                f"активный день: `{peak_day}`"
            )

            await client.send_file(event.chat_id, path, caption=caption, reply_to=event.id)
            await event.delete()
        except Exception as e:
            await event.edit(f"ошибка при построении графика: {e}")
        finally:
            if path and os.path.exists(path):
                os.remove(path)