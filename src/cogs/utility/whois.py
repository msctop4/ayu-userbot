import asyncio
import ipaddress
from telethon import TelegramClient, events
from ipwhois import IPWhois

def _is_ip(s: str) -> bool:
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False

def _clean_query(raw: str) -> str:
    q = raw.strip().lower()
    q = q.replace('https://', '').replace('http://', '')
    q = q.split('/')[0]
    return q

def _whois_domain(query: str) -> str:
    import whois
    w = whois.whois(query)
    def first(val):
        if isinstance(val, list):
            return val[0] if val else None
        return val
    lines = [f'домен: {first(w.domain_name) or query}']
    if w.registrar:
        lines.append(f'регистратор: {w.registrar}')
    if w.creation_date:
        lines.append(f'создан: {first(w.creation_date)}')
    if w.expiration_date:
        lines.append(f'истекает: {first(w.expiration_date)}')
    if w.updated_date:
        lines.append(f'обновлён: {first(w.updated_date)}')
    if w.name_servers:
        ns = w.name_servers
        ns = ', '.join(sorted(ns)) if isinstance(ns, (list, set)) else ns
        lines.append(f'nameservers: {ns}')
    if w.status:
        lines.append(f'статус: {first(w.status)}')
    if getattr(w, 'org', None):
        lines.append(f'организация: {w.org}')
    if getattr(w, 'country', None):
        lines.append(f'страна: {w.country}')
    return '\n'.join(lines)


def _whois_ip(query: str) -> str:
    res = IPWhois(query).lookup_rdap(depth=1)
    lines = [f'ip: {query}']
    if res.get('asn'):
        lines.append(f"asn: {res['asn']}")
    if res.get('asn_description'):
        lines.append(f"провайдер: {res['asn_description']}")
    network = res.get('network') or {}
    if network.get('name'):
        lines.append(f"сеть: {network['name']}")
    if network.get('cidr'):
        lines.append(f"диапазон: {network['cidr']}")
    country = network.get('country') or res.get('asn_country_code')
    if country:
        lines.append(f'страна: {country}')
    entities = res.get('entities')
    if entities:
        lines.append(f"entities: {', '.join(entities)}")
    return '\n'.join(lines)


async def setup(client: TelegramClient):
    @client.on(events.NewMessage(pattern=r'\.whois(?:\s+(\S+))?$', outgoing=True))
    async def whois_cmd(event):
        raw = event.pattern_match.group(1)
        if not raw:
            await event.edit('дай домен или ip: `.whois <домен/ip>`')
            return
        query = _clean_query(raw)
        await event.edit('смотрю...')
        loop = asyncio.get_event_loop()
        try:
            if _is_ip(query):
                text = await loop.run_in_executor(None, _whois_ip, query)
            else:
                text = await loop.run_in_executor(None, _whois_domain, query)
        except ImportError as e:
            missing = 'ipwhois' if 'ipwhois' in str(e) else 'python-whois'
            await event.edit(f'нужен пакет: `pip install {missing}`')
            return
        except Exception as e:
            await event.edit(f'ошибка: {str(e)[:200]}')
            return
        if not text.strip():
            await event.edit('пусто, ничего не нашёл')
            return
        await event.edit(f'**whois {query}**\n{text}')