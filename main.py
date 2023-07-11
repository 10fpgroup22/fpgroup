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
	if str(msg.chat.id) in chats and chats[str(msg.chat.id)].startswith(('choose_', 'join_')):
		action, _ = chats[str(msg.chat.id)].split('_')
		return await tg.send_message(msg.chat.id, **reply[action].replace(caption="text"))
	await tg.send_photo(msg.chat.id, **reply["menu"])


@tg.on_message(filters.group & filters.command(['game', f'game@{me.username}']))
async def game_command(_, msg):
	if in_dev:
		dev = await msg.reply("Ця функція ще не розроблена, спробуйте пізніше")
		return

	chats[str(msg.from_user.id)] = f"choose_{msg.chat.id}"
	mention = msg.from_user.mention(msg.from_user.first_name)
	status = await msg.reply(**reply["choose_status"].format(mention).replace(caption="text"))
	for _ in range(300):
		await asyncio.sleep(1)
		if str(msg.chat.id) in games:
			break
	else:
		await status.edit(f"На жаль, {mention} не встиг обрати гру за 5 хвилин, тому її було скасовано")
		await info.delete()
		return minilib.run(run_func, msg.delete, status.delete)

	if games[str(msg.chat.id)] == "cancel":
		del games[str(msg.chat.id)]
		await status.edit(f"{mention} скасував гру")
		return minilib.run(run_func, msg.delete, status.delete)


@tg.on_message(filters.group & filters.command(['all', f'all@{me.username}']))
async def all_group(_, msg: types.Message):
	try:
		group_admin = (await tg.get_chat_member(msg.chat.id, msg.from_user.id)).status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
	except:
		group_admin = False

	if msg.from_user and (msg.from_user.id in admins or group_admin):
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

	elif qry.data == "choose":
		if str(user.id) in chats and str(msg.chat.id) == chats[str(user.id)].split('_')[1]:
			await qry.answer(url=f"t.me/{me.username}?start=1")
		else:
			await qry.answer("На жаль, обирати гру маєш не ти", show_alert=True)
		return

	elif qry.data in ["holdem", "omaha", "cancel"] and str(user.id) in chats and chats[str(user.id)].startswith('choose_'):
		_, chat_id = chats[str(user.id)].split('_')
		if qry.data == "cancel":
			games[chat_id] = "cancel"
		else:
			games.setdefault(chat_id, getattr(globals(), qry.data.capitalize(), Holdem)()).add_player(user.id)
		del chats[str(user.id)]

	elif qry.data == 'join':
		chats[str(user.id)] = f"join_{msg.chat.id}"
		return await qry.answer(url=f"t.me/{me.username}?start=1")
	
	elif qry.data.endswith('join') and str(user.id) in chats and chats[str(user.id)].startswith('join_'):
		_, chat_id = chats[str(user.id)].split('_')

		if chat_id in games:
			if qry.data == "ajoin" and games[chat_id].add_player(user_id):
				await qry.answer("Ви успішно приєднались до гри", show_alert=True)
			elif qry.data == "djoin" and user_id in games[chat_id]:
				games[chat_id].remove_player(user_id)
				await qry.answer("Ви від'єднались від гри", show_alert=True)
			chats[str(user.id)] = f"game_{chat_id}"
		elif chat_id not in games or qry.data == "djoin":
			del chats[str(user.id)]

	if qry.data in ["ajoin", "djoin", "holdem", "omaha", "cancel"]:
		return await msg.delete()
	elif qry.data in ["g_poker"]:
		return await msg.edit(caption, reply_markup=markup)

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
