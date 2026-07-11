import aiohttp
from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo
from telethon import events, TelegramClient


weatheremoji = {
    0: "☀️",
    1: "🌤",
    2: "⛅️",
    3: "☁️",
    45: "🌫",
    48: "🌫",
    51: "🌦",
    53: "🌦",
    55: "🌦",
    56: "🌧",
    57: "🌧",
    61: "🌧",
    63: "🌧",
    65: "🌧",
    66: "🌧",
    67: "🌧",
    71: "❄️",
    73: "❄️",
    75: "❄️",
    77: "❄️",
    80: "🌦",
    81: "🌦",
    82: "🌧",
    85: "🌨",
    86: "🌨",
    95: "⛈",
    96: "⛈",
    99: "⛈",
}


def emoji_for(code):
    return weatheremoji.get(code, "🌡")


async def setup(client: TelegramClient):
    @client.on(events.NewMessage(pattern=r"\.weather(?:\s+(.+))?$", outgoing=True))
    async def weather_cmd(event):
        city = event.pattern_match.group(1)
        if not city:
            await event.edit("укажи город: `.weather Москва`")
            return
        await event.edit(f"смотрю погоду в {city}...")
        try:
            async with aiohttp.ClientSession() as session:
                geo_params = {"name": city, "count": 1, "language": "ru", "format": "json"}
                async with session.get("https://geocoding-api.open-meteo.com/v1/search", params=geo_params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    geo_data = await resp.json()
                results = geo_data.get("results")
                if not results:
                    await event.edit(f"не нашёл город `{city}`")
                    return
                place = results[0]
                lat = place["latitude"]
                lon = place["longitude"]
                place_name = place.get("name", city)
                tz_name = place.get("timezone", "UTC")
                forecast_params = {
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "temperature_2m,weather_code",
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                    "timezone": "auto",
                    "forecast_days": 7,
                }
                async with session.get("https://api.open-meteo.com/v1/forecast", params=forecast_params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    weather = await resp.json()
        except Exception as e:
            await event.edit(f"ошибка: {e}")
            return
        if weather.get("error"):
            await event.edit(f"ошибка от сервиса погоды: {weather.get('reason', 'неизвестно')}")
            return
        try:
            local_now = datetime.now(ZoneInfo(tz_name))
        except Exception:
            local_now = datetime.now(dt_timezone.utc)
        hourly_times = weather["hourly"]["time"]
        hourly_temps = weather["hourly"]["temperature_2m"]
        hourly_codes = weather["hourly"]["weather_code"]
        start_idx = 0
        now_str = local_now.strftime("%Y-%m-%dT%H:00")
        for i, t in enumerate(hourly_times):
            if t >= now_str:
                start_idx = i
                break
        hourly_lines = []
        for i in range(start_idx, min(start_idx + 4, len(hourly_times))):
            hour = hourly_times[i][11:16]
            temp = hourly_temps[i]
            code = hourly_codes[i]
            hourly_lines.append(f"`{hour}` {emoji_for(code)} {temp:.1f}°")
        daily_dates = weather["daily"]["time"]
        daily_codes = weather["daily"]["weather_code"]
        daily_max = weather["daily"]["temperature_2m_max"]
        daily_min = weather["daily"]["temperature_2m_min"]
        daily_lines = []
        for i in range(len(daily_dates)):
            date_obj = datetime.strptime(daily_dates[i], "%Y-%m-%d")
            date_fmt = date_obj.strftime("%d.%m")
            code = daily_codes[i]
            daily_lines.append(f"`{date_fmt}`: {emoji_for(code)} {daily_min[i]:.0f}°..{daily_max[i]:.0f}°")
        text = (
            f"🌍 **{place_name}**\n"
            f"🕒 Местное время: `{local_now.strftime('%H:%M')}`\n\n"
            f"🌡 **Ближайшие часы:**\n"
            + "\n".join(hourly_lines) + "\n\n"
            f"📅 **На неделю:**\n"
            + "\n".join(daily_lines)
        )
        await event.edit(text)