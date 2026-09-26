import asyncio, re
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, MessageNotModifiedError, MessageIdInvalidError

API_ID = 39878737           # свой
API_HASH = "e64fc211a8642b165ff2031a78da4b58"  # свой
FINISH_TEXT = "00:00 ВРЕМЯ ВЫШЛО!"

TIMER_RE = re.compile(r"^\s*(\d{1,3}):([0-5]\d)\s*$")
client = TelegramClient("userbot", API_ID, API_HASH)
tasks = {}  # chat_id -> task

def fmt(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

async def countdown(chat, chat_id, msg_id, total):
    print(f"[таймер] старт {fmt(total)} | чат {chat_id} | сообщение {msg_id}")
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    for left in range(total - 1, -1, -1):
        target = t0 + (total - left) * 60
        await asyncio.sleep(max(0, target - loop.time()))
        text = fmt(left) if left else FINISH_TEXT
        try:
            await client.edit_message(chat, msg_id, text)
            print("[таймер] →", text)
        except MessageNotModifiedError:
            pass
        except MessageIdInvalidError:
            print("[таймер] сообщение удалено, стоп")
            break
        except FloodWaitError as e:
            print(f"[таймер] флуд-лимит, жду {e.seconds} сек")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print("[таймер] ОШИБКА:", type(e).__name__, e)
    print("[таймер] закончил")
    tasks.pop(chat_id, None)

@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    text = event.raw_text.strip()
    print("[бот] поймал:", repr(text), "| чат:", event.chat_id)
    try:
        if text == ".stop":
            t = tasks.pop(event.chat_id, None)
            if t:
                t.cancel()
                print("[бот] таймер остановлен")
            await event.delete()
            return
        m = TIMER_RE.match(text)
        if not m:
            return
        total = int(m.group(1)) * 60 + int(m.group(2))
        if total == 0:
            return
        chat = await event.get_input_chat()  # <-- фикс ошибки "Could not find the input entity"
        old = tasks.pop(event.chat_id, None)
        if old:
            old.cancel()
        tasks[event.chat_id] = asyncio.create_task(countdown(chat, event.chat_id, event.id, total))
    except Exception as e:
        print("[бот] ОШИБКА:", type(e).__name__, e)

async def main():
    await client.start()
    await client.get_dialogs()  # подгружаем чаты в кэш
    me = await client.get_me()
    print(f"юзербот запущен как {me.first_name}. Жду сообщений...")
    await client.run_until_disconnected()

asyncio.run(main())