from deps import Settings
from json import dump, load, JSONDecodeError
from os.path import abspath, dirname, join
from pyrogram import types, emoji
from utils import tg

sdir = abspath(dirname(__file__))
channel_name = "ACL_esports"
channel_chat_name = "acl_chat"
feedback_bot_username = "ACL_feed_Bot"
group_id = -722067196

try:
	with open(join(sdir, f'../{tg.name}.json'), 'r', encoding='utf-8') as fl:
		dt = load(fl)
		chats, games = dt.get('chats', {}), dt.get('games', {})
		settings = Settings.load(dt.get('settings', {'_': 'Settings'}))
except (IOError, JSONDecodeError):
	print("Settings were not loaded, created new")
	settings = Settings()
	chats, games = {}, {}

emojis = list(filter(lambda x: not x.startswith('_'), dir(emoji)))

captions = {
	"help_us": "Оберіть спосіб допомоги організації ACL",
	"rules": "Які правила вас заінтерисували? Обирайте зі списку нижче",
	"rights": "Ця функція недоступна. Просимо вибачення за тимчасові незручності",
	"tournir": "Беріть участь у турнірі, переможіть усіх суперників та отримайте довгоочікуваний приз\n\n"
			   "P.S. Натискаючи копку 'Реєстрація', Ви погоджуєтесь з правилами нашої організації",
	"no_tournir": "На даний момент немає ніяких турнірів. Зачекайте ще трохи, скоро його буде анонсовано...",
	"info": "Знайдіть та прочитайте інформацію, що вас інтерисує. Якцо не знайдете такої,"
		   f"то звертайтеся до нього => [зворотній зв'язок](https://t.me/{feedback_bot_username})",
	"subscribe": "Для того щоб брати участь у турнірі треба бути підписаним на:",
	"join": "Підтвердіть участь у грі натисканням кнопки 'Підтвердити'"
}

photos = {
	fname: join(sdir, f'_{fname}.png')
	for fname in ["menu", "rules", "rights", "tournir", "social", "info"]
}

markups = {
	"menu": types.InlineKeyboardMarkup([
		[types.InlineKeyboardButton("Реєстрація на турнір", callback_data="tournir")],
		[types.InlineKeyboardButton("💸Привілегії💸", callback_data="rights"),
		 types.InlineKeyboardButton("📋Правила📋", callback_data="rules")],
		[types.InlineKeyboardButton("ℹІнформаціяℹ", callback_data="info"),
		 types.InlineKeyboardButton("Задати питання⁉️", url=f"https://t.me/{feedback_bot_username}")],
		[types.InlineKeyboardButton("Підтримати нас", callback_data="help_us")]
	]),
	"help_us": [
		[types.InlineKeyboardButton("Скіни", url=settings.get("Реквизиты", "Скины"))],
		[types.InlineKeyboardButton("<< Назад", callback_data="menu")]
	],
	"rules": [
		[types.InlineKeyboardButton("📋Правила групи📋", url=settings.get("Правила", "Группы"))],
		# [types.InlineKeyboardButton("📋Правила ігор📋", callback_data="games_rules")]
	],
	"info": [[types.InlineKeyboardButton("Ми в соц. мережах", callback_data="social")]],
	"subscribe": [
		[types.InlineKeyboardButton("💬Наш чат💬", url=f"https://t.me/{channel_chat_name}")],
		[types.InlineKeyboardButton("Телеграм канал", url=f"https://t.me/{channel_name}")]
	],
	"games": [
		[types.InlineKeyboardButton("Покер", callback_data="g_poker")],
		[types.InlineKeyboardButton("Скасувати", callback_data="cancel")]
	],
	"g_poker": [
		[types.InlineKeyboardButton("Холдем", callback_data="holdem"),
		 types.InlineKeyboardButton("Омаха", callback_data="omaha")],
		[types.InlineKeyboardButton("<< Назад", callback_data="games")]
	],
	"join": [
		[types.InlineKeyboardButton("Підтвердити", callback_data="ajoin"),
		 types.InlineKeyboardButton("Відхилити", callback_data="djoin")]
	]
}

reply = {
	menu: {
		k: v
		for k, v in zip(
			["photo", "caption", "reply_markup"],
			[photos.get(menu, None), captions.get(menu, ""), markups.get(menu, None)]
		) if v
	}
	for menu in set([*markups.keys(), *captions.keys(), *photos.keys()])
}