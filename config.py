from deps import Settings
from json import dump, load, JSONDecodeError
from os.path import abspath, dirname, join
from pyrogram import types, emoji
from utils import tg

sdir = abspath(dirname(__file__))
group_id = -722067196

try:
    with open(join(sdir, f'{tg.name}.json'), 'r', encoding='utf-8') as fl:
        dt = load(fl)
        chats = data.get('chats', {})
        settings = Settings.load(dt.get('settings', {'_': 'Settings'}))
except (IOError, JSONDecodeError):
    print("Settings were not loaded, created new")
    settings = Settings()
    chats = {}

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
        [types.InlineKeyboardButton("Скины", url=settings.get("Реквизиты", "Скины"))],
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