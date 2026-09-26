import asyncio, re, os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, MessageNotModifiedError, MessageIdInvalidError

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION = os.environ["SESSION"]
FINISH_TEXT = "00:00 время вышло"

TIMER_RE = re.compile(r"^\s*(\d{1,3}):([0-5]\d)\s*$")
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
tasks = {}

def fmt(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

async def countdown(chat, chat_id, msg_id, total):
    print(f"[таймер] старт {fmt(total)} | чат {chat_id}", flush=True)
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    for left in range(total - 1, -1, -1):
        target = t0 + (total - left) * 60
        await asyncio.sleep(max(0, target - loop.time()))
        text = fmt(left) if left else FINISH_TEXT
        try:
            await client.edit_message(chat, msg_id, text)
        except MessageNotModifiedError:
            pass
        except MessageIdInvalidError:
            print("[таймер] сообщение удалено, стоп", flush=True)
            break
        except FloodWaitError as e:
            print(f"[таймер] флуд-лимит {e.seconds} сек", flush=True)
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print("[таймер] ОШИБКА:", type(e).__name__, e, flush=True)
    print("[таймер] закончил", flush=True)
    tasks.pop(chat_id, None)

@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    text = event.raw_text.strip()
    try:
        if text == ".stop":
            t = tasks.pop(event.chat_id, None)
            if t: t.cancel()
            await event.delete()
            return
        m = TIMER_RE.match(text)
        if not m:
            return
        total = int(m.group(1)) * 60 + int(m.group(2))
        if total == 0:
            return
        chat = await event.get_input_chat()
        old = tasks.pop(event.chat_id, None)
        if old: old.cancel()
        tasks[event.chat_id] = asyncio.create_task(countdown(chat, event.chat_id, event.id, total))
    except Exception as e:
        print("[бот] ОШИБКА:", type(e).__name__, e, flush=True)

async def main():
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("SESSION невалидная, сгенерируй заново")
    await client.get_dialogs()
    me = await client.get_me()
    print(f"юзербот запущен как {me.first_name}", flush=True)
    await client.run_until_disconnected()

asyncio.run(main())
