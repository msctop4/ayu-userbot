import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument,
    DocumentAttributeSticker, DocumentAttributeAnimated,
    DocumentAttributeAudio, DocumentAttributeVideo,
)

stop_words = {
    'это', 'что', 'как', 'так', 'и', 'в', 'на', 'с', 'я', 'ты', 'он', 'она',
    'они', 'мы', 'вы', 'не', 'да', 'но', 'а', 'же', 'то', 'был', 'было',
    'быть', 'для', 'по', 'из', 'к', 'у', 'о', 'за', 'от', 'до', 'при',
    'или', 'если', 'когда', 'там', 'тут', 'его', 'её', 'их', 'мой', 'твой',
    'наш', 'ваш', 'бы', 'ну', 'вот', 'ещё', 'уже', 'тоже',
}

weekdays = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
emoji_re = re.compile('[\U0001F300-\U0001FAFF\u2600-\u27BF]')


def media_kind(msg):
    if not msg.media:
        return None
    if isinstance(msg.media, MessageMediaPhoto):
        return 'фото'
    if isinstance(msg.media, MessageMediaDocument):
        doc = msg.media.document
        if doc is None:
            return 'файл'
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeSticker):
                return 'стикеры'
            if isinstance(attr, DocumentAttributeAnimated):
                return 'гифки'
            if isinstance(attr, DocumentAttributeAudio):
                return 'голосовые' if attr.voice else 'аудио'
            if isinstance(attr, DocumentAttributeVideo):
                return 'видео'
        return 'файлы'
    return 'другое'


async def setup(client: TelegramClient):
    @client.on(events.NewMessage(pattern=r'\.wrapped(?:\s+(\S+))?$', outgoing=True))
    async def wrapped_cmd(event):
        arg = event.pattern_match.group(1)
        year_mode = None
        end_date = None
        if not arg:
            days = 30
        elif arg.lower() in ('год', 'year', 'y'):
            days = 365
        elif re.match(r'^(19|20)\d{2}$', arg):
            year_mode = int(arg)
            start = datetime(year_mode, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(year_mode + 1, 1, 1, tzinfo=timezone.utc)
            days = (end_date - start).days
        elif ',' in arg or '.' in arg:
            days = float(arg.replace(',', '.')) * 365
        else:
            days = int(arg)
        if year_mode:
            cutoff = datetime(year_mode, 1, 1, tzinfo=timezone.utc)
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        chat = await event.get_input_chat()
        label = f'{year_mode} год' if year_mode else f'{round(days)} дней'
        await event.edit(f'копаюсь в истории за {label}, это может занять время...')
        senders = Counter()
        chars = Counter()
        hours = Counter()
        weekday_count = Counter()
        words = Counter()
        emoji_count = Counter()
        media = Counter()
        active_days = set()
        questions = 0
        shouts = 0
        longest = ('', 0)
        total = 0
        first_date = None
        last_date = None
        async for msg in client.iter_messages(chat, limit=None, offset_date=end_date):
            if msg.date < cutoff:
                break
            total += 1
            local = msg.date.astimezone()
            senders[msg.sender_id] += 1
            hours[local.hour] += 1
            weekday_count[local.weekday()] += 1
            active_days.add(local.date())
            if first_date is None or msg.date < first_date:
                first_date = msg.date
            if last_date is None or msg.date > last_date:
                last_date = msg.date
            kind = media_kind(msg)
            if kind:
                media[kind] += 1
            text = msg.raw_text or ''
            chars[msg.sender_id] += len(text)
            if text:
                if text.strip().endswith('?'):
                    questions += 1
                letters = [c for c in text if c.isalpha()]
                if letters and len(letters) > 5 and sum(1 for c in letters if c.isupper()) / len(letters) > 0.7:
                    shouts += 1
                if len(text) > longest[1]:
                    longest = (text, len(text))
                for w in re.findall(r'[а-яa-zё]{3,}', text.lower()):
                    if w not in stop_words:
                        words[w] += 1
                for e in emoji_re.findall(text):
                    emoji_count[e] += 1
        if total == 0:
            await event.edit('за этот период тут пусто')
            return
        span_days = max((last_date - first_date).days, 1)
        top_hour = hours.most_common(1)[0]
        top_day = weekday_count.most_common(1)[0]
        top_words = words.most_common(5)
        top_emoji = emoji_count.most_common(3)
        lines = [
            f'**wrapped за {label}**',
            f'сообщений: {total}',
            f'активных дней: {len(active_days)} из {span_days}',
        ]
        if event.is_private:
            me = await client.get_me()
            for uid, cnt in senders.most_common():
                name = 'я' if uid == me.id else 'собеседник'
                pct = round(cnt / total * 100)
                avg_len = round(chars[uid] / cnt)
                lines.append(f'{name}: {cnt} ({pct}%), в среднем {avg_len} символов')
        else:
            lines.append('топ по активности:')
            for uid, cnt in senders.most_common(5):
                try:
                    user = await client.get_entity(uid)
                    name = getattr(user, 'first_name', None) or str(uid)
                except Exception:
                    name = str(uid)
                pct = round(cnt / total * 100)
                lines.append(f'{name}: {cnt} ({pct}%)')
        lines.append(f'пик активности: {top_hour[0]}:00 ({top_hour[1]} сообщений)')
        lines.append(f'болтливее всего по {weekdays[top_day[0]]}')
        if media:
            lines.append('медиа: ' + ', '.join(f'{k} — {v}' for k, v in media.most_common()))
        if top_words:
            lines.append('часто мелькает: ' + ', '.join(w for w, _ in top_words))
        if top_emoji:
            lines.append('любимые эмодзи: ' + ' '.join(e for e, _ in top_emoji))
        lines.append(f'вопросов задано: {questions}')
        lines.append(f'сообщений КАПСОМ: {shouts}')
        if longest[0]:
            preview = longest[0][:80].replace('\n', ' ')
            lines.append(f'самое длинное сообщение ({longest[1]} симв.): "{preview}..."')
        await event.edit('\n'.join(lines))