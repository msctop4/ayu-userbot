import importlib, os
from pathlib import Path
from telethon import TelegramClient
from src.cfg.config import api_id, api_hash, session, dir_sess

dir_sess_ = os.path.join(dir_sess, session)
dir_cogs = Path('src/cogs')
version_file = Path('__version__')
app_version = version_file.read_text(encoding='utf-8').strip() if version_file.exists() else '???'

client = TelegramClient(dir_sess_, api_id, api_hash, device_model='Ayu UserBot', app_version=app_version, system_version=' ')

async def cogs():
    loaded = 0
    for category in dir_cogs.iterdir():
        if category.name.startswith('_') or not category.is_dir():
            continue
        for file in category.glob('*.py'):
            if file.name.startswith('_'):
                continue
            module_name = f'src.cogs.{category.name}.{file.stem}'
            try:
                module = importlib.import_module(module_name)
                await module.setup(client)
                loaded += 1
                print(f'загружен {module_name}')
            except Exception as e:
                print(f'ошибка при загрузке кога {module_name} {e}')
    return loaded

async def main():
    try:
        await client.start()
        loaded = await cogs()
        print(f'загружено когов: {loaded}')
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'крит ошибка {e}')
    finally:
        await client.disconnect()
