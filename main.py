import re

from random import choice
from games import Holdem, Omaha
from utils import *


@tg.on_message(filters.chat(group_id) & (filters.new_chat_members | filters.left_chat_member), group=-1)
async def admin_group_handler(_, msg):
	global admins
	admins = [mbr.user.id async for mbr in tg.get_chat_members(msg.chat.id) if not mbr.user.is_bot]
	update_status(admins)


@tg.on_message(filters.service & ~filters.private & ~filters.chat(channel_name), group=-1)
async def group_handler(_, msg):
	try:
		await msg.delete()
	except err.RPCError as rpc:
		print(f"<ChatError(chat_id={msg.chat.id}, title='{msg.chat.title}'): {rpc}>")


@tg.on_message(filters.chat(channel_chat_name) & filters.new_chat_members)
async def new_chat_member(_, msg):
	welcome = await tg.send_message(
		msg.chat.id,
		f"Віддаймо вітання новому учаснику нашої групи - " + msg.from_user.mention(msg.from_user.first_name)
	)
	minilib.run(run_func, welcome.delete)
	try:
		user = User.from_telegram(msg.user.id)
		await tg.send_message(
			msg.from_user.id,
			f"Вітаю тебе в нашій групі, {msg.from_user.first_name}!\n👇Для початку рекомендую ознайомитися з Правилами групи👇",
			reply_markup=types.InlineKeyboardMarkup(markups["rules"][0])
		)
	except err.RPCError as rpc:
		print(f"<ChatError(chat_id={msg.chat.id}, title='{msg.chat.title}'): {rpc}>")


@tg.on_message(filters.private & filters.command('start'))
async def start_private(_, msg):
	# if chats[str(msg.chat.id)].startswith('choose_'):
	#     pass
	# elif chats[str(msg.chat.id)].startswith('join_'):
	#     pass
	await tg.send_photo(msg.chat.id, **reply["menu"])


# @tg.on_message(filters.group & filters.command(['game', f'game@{me.username}']))
# async def game_command(_, msg):
#     pass


@tg.on_message(filters.group & filters.command(['all', f'all@{me.username}']))
async def all_group(_, msg: types.Message):
	if msg.from_user and msg.from_user.id in admins:
		chat = Chat.from_telegram(msg.chat.id).tags
		await tg.send_message(
			msg.chat.id,
			"Брате, я тебе призиваю\n" +
			"".join([m.user.mention(getattr(emoji, choice(emojis), '🫥'))
					 async for m in msg.chat.get_members() if m.user.id not in chat and not m.user.is_bot])
		)

	try:
		await msg.delete()
	except err.RPCError as rpc:
		print(f"<ChatError(chat_id={msg.chat.id}, title='{msg.chat.title}'): {rpc}>")


@tg.on_message(filters.group & filters.command(['leave', f'leave@{me.username}']))
async def leave_tag_all(_, msg):
	try:
		user = User.from_telegram(msg.from_user.id)
		if user.left_chat_tag(msg.chat.id):
			text = "Тепер я не відмічу тебе в цій групі."
		else:
			text = "Я вже і так не відмічаю тебе."
	except err.RPCError as rpc:
		text = "Щось пішло не так. Спробуй пізніше"
		print(f"<ChatError(chat_id={msg.chat.id}, title='{msg.chat.title}'): {rpc}>")

	minilib.run(run_func, (await msg.reply(text)).delete, msg.delete)


@tg.on_message(filters.group & filters.command(['add', f'add@{me.username}']))
async def add_tag_all(_, msg):
	try:
		user = User.from_telegram(msg.from_user.id)
		if user.add_chat_tag(msg.chat.id):
			text = "Відтепер я буду відмічати тебе в групі."
		else:
			text = "Я так само відмічаю тебе в групі, будь ласка, не спамуй."
	except err.RPCError as rpc:
		text = "Щось пішло не так. Спробуй пізніше"
		print(f"<ChatError(chat_id={msg.chat.id}, title='{msg.chat.title}'): {rpc}>")

	minilib.run(run_func, (await msg.reply(text)).delete, msg.delete)


@tg.on_callback_query()
async def callback_query(_, qry):
	photo, caption, markup = photos.get(qry.data, photos["menu"]), captions.get(qry.data, ""), markups.get(qry.data, [])
	msg, user = qry.message, qry.from_user

	if qry.data == 'tournir':
		verified = [False, False]

		for x, chat in enumerate([channel_chat_name, channel_name]):
			try:
				verified[x] = (await tg.get_chat_member(chat, user.id)).status not in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]
			except err.RPCError as rpc:
				print(f"<ChatError(chat_id={msg.chat.id}, title='{msg.chat.title}'): {rpc}>")

		if all(verified):
			url = settings.get("Турнир", "Ссылка")
			if url:
				markup = [
					[types.InlineKeyboardButton("Реєстрація", url=url)]
				]
			else:
				caption = captions["no_tournir"]
		else:
			caption = captions["subscribe"]
			markup = list(filter(bool, map(lambda x: (None if x[1] else markups["subscribe"][x[0]]), enumerate(verified))))

	elif qry.data == 'social':
		markup = [
			[types.InlineKeyboardButton(txt, url=url)]
			for txt, url in settings.iter_group("Соц.сети")
		] + markups["subscribe"]

		markup.append([types.InlineKeyboardButton("<< Назад", callback_data="info")])

	# elif qry.data == 'join':
		# chats[str(user.id)] = f"join_{msg.chat.id}"
		# await tg.send_message(user.id, caption, reply_markup=markup)
		# return await qry.answer(url=f"t.me/{me.username}")
	# if qry.data.startswith(("holdem", "omaha")):
	#     games[chats[str(user.id)]] = getattr(globals(), qry.data.capitalize(), Holdem)().add_players(user.id)
	#     return await msg.delete()
	# elif qry.data.endswith('join') and len(qry.data) == 5 and chats[user.id].startswith('join_') and chats[user.id][5:] in games and len(games[chats[user.id]][5:]) < 15:
	#     if qry.data == "ajoin":
	#         pass
	#     elif qry.data == "djoin":
	#         pass
	#     return

	if isinstance(markup, list):
		markup = markup.copy()

		if qry.data in ["tournir", "rules", "info", "rights"]:
			markup.append([types.InlineKeyboardButton("<< Назад", callback_data="menu")])

		if bool(markup):
			markup = types.InlineKeyboardMarkup(markup)

	await edit_photo(
		msg, photo, caption,
		reply_markup=(markup if bool(markup) else None)
	)


if __name__ == '__main__':
	tg.run(start())
