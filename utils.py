import asyncio

from deps import Settings
from discord import Client as DSClient, Intents
from json import dump, load, JSONDecodeError
from os import environ
from os.path import abspath, dirname, join
from pyrogram import Client as TGClient, errors as err, types, enums
from queue import Queue
from typing import Any


def getenv(env: str, default: Any = None):
    return environ.get(env, default)


tg = TGClient("main_bot", api_id=getenv("API_ID", ""), api_hash=getenv("API_HASH", ""), bot_token=getenv("TOKEN", ""))
ds = DSClient(intents=Intents.all())
sdir = abspath(dirname(__file__))
events = Queue()
group_id = -1001558155556
news_id = 1038752367123898459

try:
    with open(join(sdir, f'{tg.name}.json'), 'r', encoding='utf-8') as fl:
        dt = load(fl)
        chats = dt.get('chats', {})
        settings = Settings.load(dt.get("settings", {"_": "Settings"}))
        left = dt.get('left', {})
except (IOError, JSONDecodeError):
    with open(join(sdir, f'{tg.name}.json'), 'w', encoding='utf-8') as fl:
        settings = Settings()
        chats = {}
        left = {}
        dump({"settings": settings, "chats": chats, "left": left}, fl, default=lambda o: getattr(o, '__dict__', None), ensure_ascii=False, indent=4)

with tg:
    global admins
    me = tg.get_me()
    admins = [mbr.user.id for mbr in (tg.get_chat_members(group_id)) if not mbr.user.is_bot]
    print(f"@{me.username} started")

emojis = ["👊🏽", "🐾", "😎", "🧑🏻‍🦳", "🏃🏼", "🤑", "🖋", "🚣🏼‍♀", "🦶🏾", "👨🏻‍🏫", "🧝🏾‍♂️", "🪶", "💓", "👋🏼",
          "🤹🏻", "🛠", "💁🏻‍♀️", "🚏", "🧑🏿‍🦼", "🧝🏼‍♀️", "🧘🏿‍♂", "👩🏿‍🚀", "🏓", "📪", "🧙🏽‍♂️", "✈️", "☝️", "😮",
          "🍓", "🤽🏾", "🦸🏻", "🧍‍♂️", "👨🏿‍🎨", "👩‍💼", "🫅🏽", "👩🏽‍🦽", "🤡", "🚢", "☁️"]

captions = {
    "help_us": "Выберите то, чем хотите помочь",
    "rules": "Что хотите прочитать? Выбирайте из списка ниже",
    "rights": "На данный момент это функция не работает. Просим прощения за временные неудобства",
    "tournir": "Примите участие в турнире, оставьте всех противников позади и заполучите долгожданный приз\n\n"
               "P.S. Нажимая на кнопку 'Регистрация' Вы соглашаетесь с нашими правилами",
    "no_tournir": "В данный момент не проводится турнир. Подождите ещё чуть-чуть, мы его скоро анонсируем...",
    "info": "Найдите и прочитайте интересующую вас информацию. А если не найдёте, то можете задать вопрос ему => <a href='https://t.me/fpgfeedBot'>бот обратной связи</a>",
    "subscribe": "Для того чтобы участвовать в турнире нужно быть подписаным на:"
}

photos = {
    "menu": join(sdir, '_menu.png'),
    "rules": join(sdir, '_rules.png'),
    "rights": join(sdir, '_rights.png'),
    "tournir": join(sdir, '_tournir.png'),
    "social": join(sdir, '_social.jpg'),
    "settings": join(sdir, '_settings.png'),
    "info": join(sdir, '_info.png')
}

markups = {
    "menu": types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("Регистрация на турнир", callback_data="tournir")],
        [types.InlineKeyboardButton("💸Привилегии💸", callback_data="rights"),
         types.InlineKeyboardButton("📋Правила📋", callback_data="rules")],
        [types.InlineKeyboardButton("ℹИнформацияℹ", callback_data="info"),
         types.InlineKeyboardButton("Задать вопросик⁉️", url="https://t.me/fpgfeedBot")],
        [types.InlineKeyboardButton("Поддержать нас", callback_data="help_us")]
    ]),
    "help_us": types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("Скины", url="https://steamcommunity.com/tradeoffer/new/?partner=310787303&token=8dNiyxlC")],
        [types.InlineKeyboardButton("<< Главное меню", callback_data="menu")]
    ]),
    "rules": types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("Правила турнира", url="https://telegra.ph/Pravila-turnira-01-03")],
        [types.InlineKeyboardButton("Правила группы", url="https://telegra.ph/Pravila-gruppy-09-21-4")],
        [types.InlineKeyboardButton("<< Главное меню", callback_data="menu")]
    ]),
    "rights": types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("<< Назад", callback_data="menu")]
    ]),
    "rights_moder": types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("➕Создать пост", callback_data="create_post")],
        [types.InlineKeyboardButton("<< Назад", callback_data="menu")]
    ]),
    "info": types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("Мы в соц. сетях", callback_data="social")],
        [types.InlineKeyboardButton("<< Назад", callback_data="menu")]
    ]),
    "subscribe": [
        [types.InlineKeyboardButton("💬Наш чат💬", url=settings.get("Соц.сети", "📨Чат"))],
        [types.InlineKeyboardButton("Телеграм канал", url="https://t.me/fpg_tournament")]
    ],
    "settings": types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("Турнир", callback_data="s_tournir")]
    ]),
    "create_post": types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("Изменить текст📝", callback_data="post_text")],
        [types.InlineKeyboardButton("Добавить кнопку➕", callback_data="post_add_button")]
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


async def run_func(func, timeout=30):
    await asyncio.sleep(timeout)
    try:
        await func()
    except BaseException as e:
        print("Something went wrong:", e)


def dispatch(event: str, *args, **kwargs):
    events.put({"event": event, "args": args, "kwargs": kwargs})


async def start():
    from bot_web import run
    await run(block=False)
    asyncio.create_task(ds.start(getenv("DISCORD")))
    await tg.start()

    while True:
        try:
            event = events.get(block=False)
            if event:
                event, args, kwargs = event["event"], event["args"], event["kwargs"]
                dsp.dispatch(event, *args, **kwargs)
        except BaseException as e:
            pass
        await asyncio.sleep(.1)
        with open(join(sdir, f"{tg.name}.json"), 'w', encoding="utf-8") as file:
            dump({"settings": settings, "chats": chats, "left": left}, file, default=lambda o: getattr(o, '__dict__', None), ensure_ascii=False, indent=4)

    await tg.stop()
