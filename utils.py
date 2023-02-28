import asyncio
import inspect
import minilib

from deps import Settings
from discord import Client as DSClient, Intents, File
from json import dump, load, JSONDecodeError
from os import getenv
from os.path import abspath, dirname, join
from pyrogram import Client as TGClient, errors as err, types, enums, emoji, filters
from shutil import rmtree


tg = TGClient("main_bot", api_id=getenv("API_ID", ""), api_hash=getenv("API_HASH", ""), bot_token=getenv("TOKEN", ""),
              max_concurrent_transmissions=4)
ds = DSClient(intents=Intents.all())
sdir = abspath(dirname(__file__))
group_id = -1001558155556
news_id = 1038752367123898459

try:
    with open(join(sdir, f'{tg.name}.json'), 'r', encoding='utf-8') as fl:
        dt = load(fl)
        chats = dt.get('chats', {})
        left = dt.get('left', {})
        settings = Settings.load(dt.get('settings', {'_': 'Settings'}))
except (IOError, JSONDecodeError):
    settings = Settings()
    chats = {}
    left = {}

with tg:
    global admins
    me = tg.get_me()
    admins = [mbr.user.id for mbr in (tg.get_chat_members(group_id)) if not mbr.user.is_bot]
    print(f"@{me.username} started")

emojis = list(filter(lambda x: not x.startswith('_'), dir(emoji)))

captions = {
    "help_us": "Выберите то, чем хотите помочь",
    "rules": "Что хотите прочитать? Выбирайте из списка ниже",
    "rights": "На данный момент это функция не работает. Просим прощения за временные неудобства",
    "tournir": "Примите участие в турнире, оставьте всех противников позади и заполучите долгожданный приз\n\n"
               "P.S. Нажимая на кнопку 'Регистрация' Вы соглашаетесь правилами нашей организации",
    "no_tournir": "В данный момент не проводится турнир. Подождите ещё чуть-чуть, мы его скоро анонсируем...",
    "info": "Найдите и прочитайте интересующую вас информацию. А если не найдёте,"
            "то можете задать вопрос ему => [бот обратной связи](https://t.me/fpgfeedBot)",
    "subscribe": "Для того чтобы участвовать в турнире нужно быть подписаным на:",
    "discord_send": "Отправь пост сюда"
}

photos = {
    "menu": join(sdir, '_menu.png'),
    "rules": join(sdir, '_rules.png'),
    "rights": join(sdir, '_rights.png'),
    "tournir": join(sdir, '_tournir.png'),
    "social": join(sdir, '_social.jpg'),
    # "settings": join(sdir, '_settings.png'),
    "info": join(sdir, '_info.png')
}

markups = {
    "menu": types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("Регистрация на турнир", callback_data="tournir")],
        [types.InlineKeyboardButton("💸Привилегии💸", callback_data="rights"),
         types.InlineKeyboardButton("📋Правила📋", callback_data="rules")],
        [types.InlineKeyboardButton("ℹИнформацияℹ", callback_data="info"),
         types.InlineKeyboardButton("Задать вопросик⁉️", url="https://t.me/ACL_feed_Bot")],
        [types.InlineKeyboardButton("Поддержать нас", callback_data="help_us")]
    ]),
    "help_us": [
        [types.InlineKeyboardButton("Скины", url=settings.get("Реквизиты", "Скины"))]
        [types.InlineKeyboardButton("<< Назад", callback_data="menu")]
    ],
    "rules": [
        [types.InlineKeyboardButton("📋Правила турнира📋", url=settings.get("Правила", "Турнира"))],
        [types.InlineKeyboardButton("📋Правила группы📋", url=settings.get("Правила", "Группы"))]
    ],
    "rights": [
        [types.InlineKeyboardButton("<< Назад", callback_data="menu")]
    ],
    "info": [
        [types.InlineKeyboardButton("Мы в соц. сетях", callback_data="social")],
        [types.InlineKeyboardButton("<< Назад", callback_data="menu")]
    ],
    "subscribe": [
        [types.InlineKeyboardButton("💬Наш чат💬", url=settings.get("Соц.сети", "📨Чат"))],
        [types.InlineKeyboardButton("Телеграм канал", url="https://t.me/fpg_tournament")]
    ],
    "discord_send_post": types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("❌Нет❌", callback_data="discord_discard"),
         types.InlineKeyboardButton("✅Да✅", callback_data="discord_approve")]
    ])
}

reply = {
    menu: {
        "photo": photos.get(menu, join(sdir, '_menu.png')),
        **{k: v for k, v in zip(["caption", "reply_markup"], [captions.get(menu, ""), markups.get(menu, None)]) if v}
    }
    for menu in ["menu", "help_us", "rules", "rights", "tournir", "no_tournir", "info", "social", "settings"]
}


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
