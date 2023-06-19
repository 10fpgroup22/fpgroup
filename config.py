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
        chats = dt.get('chats', {})
        settings = Settings.load(dt.get('settings', {'_': 'Settings'}))
except (IOError, JSONDecodeError):
    print("Settings were not loaded, created new")
    settings = Settings()
    chats = {}

emojis = list(filter(lambda x: not x.startswith('_'), dir(emoji)))

captions = {
    "help_us": "Оберіть спосіб допомоги організації ACL",
    "rules": "Які правила вас заінтерисували? Обирайте зі списку нижче",
    "rights": "Ця функція недоступна. Просимо вибачення за тимчасові незручності",
    "tournir": "Беріть участь у турнірі, переможіть усіх суперників та отримайте довгоочікуваний приз\n\n"
               "P.S. Натискаючи копку 'Реєстрація', Ви погоджуєтесь з правилами нашої організації",
    "no_tournir": "На даний момент немає ніяких турнірів. Зачекайте ще трохи, скоро його буде анонсовано...",
    "info": "Знайдіть та прочитайте інформацію, що вас інтерисує. Якцо не знайдете такої,"
            "то звертайтеся до нього => [зворотній зв'язок](https://t.me/fpgfeedBot)",
    "subscribe": "Для того щоб брати участь у турнірі труба бути підписаним на:"
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
        [types.InlineKeyboardButton("Реєстрація на турнір", callback_data="tournir")],
        [types.InlineKeyboardButton("💸Привілегії💸", callback_data="rights"),
         types.InlineKeyboardButton("📋Правила📋", callback_data="rules")],
        [types.InlineKeyboardButton("ℹІнформаціяℹ", callback_data="info"),
         types.InlineKeyboardButton("Задати питання⁉️", url="https://t.me/ACL_feed_Bot")],
        [types.InlineKeyboardButton("Підтримати нас", callback_data="help_us")]
    ]),
    "help_us": [
        [types.InlineKeyboardButton("Скіни", url=settings.get("Реквизиты", "Скины"))],
        [types.InlineKeyboardButton("<< Назад", callback_data="menu")]
    ],
    "rules": [
        [types.InlineKeyboardButton("📋Правила турниру📋", url=settings.get("Правила", "Турнира"))],
        [types.InlineKeyboardButton("📋Правила групи📋", url=settings.get("Правила", "Группы"))]
    ],
    "rights": [
        [types.InlineKeyboardButton("<< Назад", callback_data="menu")]
    ],
    "info": [
        [types.InlineKeyboardButton("Ми в соц. мережах", callback_data="social")],
        [types.InlineKeyboardButton("<< Назад", callback_data="menu")]
    ],
    "subscribe": [
        [types.InlineKeyboardButton("💬Наш чат💬", url=settings.get("Соц.сети", "📨Чат"))],
        [types.InlineKeyboardButton("Телеграм канал", url="https://t.me/fpg_tournament")]
    ]
}

reply = {
    menu: {
        "photo": photos.get(menu, join(sdir, '_menu.png')),
        **{k: v for k, v in zip(["caption", "reply_markup"], [captions.get(menu, ""), markups.get(menu, None)]) if v}
    }
    for menu in ["menu", "help_us", "rules", "rights", "tournir", "no_tournir", "info", "social", "settings"]
}