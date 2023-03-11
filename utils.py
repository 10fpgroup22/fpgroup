import asyncio
import minilib

from discord import Client as DSClient, Intents, File
from os import getenv
from pyrogram import Client as TGClient, errors as err, enums, filters


tg = TGClient("main_bot", api_id=getenv("API_ID", ""), api_hash=getenv("API_HASH", ""), bot_token=getenv("TOKEN", ""), max_concurrent_transmissions=4)
ds = DSClient(intents=Intents.all())

from config import *

with tg:
    global admins
    me = tg.get_me()
    admins = [mbr.user.id for mbr in (tg.get_chat_members(group_id)) if not mbr.user.is_bot]
    print(f"@{me.username} started")


async def edit_photo(msg, photo="", caption="", reply_markup=None):
    try:
        return await msg.edit_media(types.InputMediaPhoto(media=photo, caption=caption), reply_markup=reply_markup)
    except err.RPCError as e:
        print("Something where occurred:", e)
        return msg


async def run_func(*funcs, timeout=30):
    await asyncio.sleep(timeout)
    result = []
    try:
        for func in funcs:
            result.append(await func())
    except BaseException as e:
        print("Something went wrong:", e)

    return result


async def start():
    from server import run
    app = await run()
    app['discord'], app['telegram'] = ds, tg
    asyncio.create_task(ds.start(getenv("DISCORD")))
    await tg.start()

    while True:
        await asyncio.sleep(.1)
        with open(join(sdir, f"{tg.name}.json"), 'w', encoding="utf-8") as file:
            dump({"settings": settings, "chats": chats, "left": left},
                 file, default=lambda o: getattr(o, '__dict__', None), ensure_ascii=False, indent=4)

    await tg.stop()
