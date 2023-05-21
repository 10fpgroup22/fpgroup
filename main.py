import re

from database import *
from random import choice
from utils import *


@tg.on_message(filters.chat(group_id) & (filters.new_chat_members | filters.left_chat_member), group=-1)
async def admin_group_handler(_, msg):
    global admins
    admins = [mbr.user.id async for mbr in tg.get_chat_members(msg.chat.id) if not mbr.user.is_bot]
    update_status(admins)


@tg.on_message(filters.service & ~filters.private & ~filters.chat("fpg_tournament"), group=-1)
async def group_handler(_, msg):
    try:
        await msg.delete()
    except err.RPCError as rpc:
        print(f"Occurred <{rpc}>")


@tg.on_message(filters.chat("acl_chat") & filters.new_chat_members)
async def new_chat_member(_, msg):
    welcome = await tg.send_message(
        msg.chat.id,
        f"Давайте поприветствуем нового участника нашей группы - " + msg.from_user.mention(msg.from_user.first_name)
    )
    minilib.run(run_func, welcome.delete)
    try:
        await tg.send_message(
            msg.from_user.id,
            f"Приветствую тебя в нашей группе, {msg.from_user.first_name}!\n👇Для начала рекомендую прочитать Правила группы👇",
            reply_markup=types.InlineKeyboardMarkup(markups["rules"][1])
        )
    except err.RPCError as rpc:
        print(f"<{rpc}>")


@tg.on_message(filters.private & filters.command('start'))
async def start_private(_, msg):
    await tg.send_photo(msg.chat.id, **reply["menu"])


@tg.on_message(filters.command(['all', f'all@{me.username}']) & filters.group)
async def all_group(_, msg: types.Message):
    if msg.from_user:
        member = await msg.chat.get_member(msg.from_user.id)
    elif msg.sender_chat:
        member = True

    if (msg.from_user and msg.from_user.id in admins) or msg.sender_chat \
        or (member and getattr(member, 'status', enums.ChatMemberStatus.ADMINISTRATOR) in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]):
        chat = Chat.from_telegram(msg.chat.id).get_tags()
        await tg.send_message(
            msg.chat.id,
            "Брат, я тебя призываю\n" +
            "".join([m.user.mention(getattr(emoji, choice(emojis), '🫥'))
                     async for m in msg.chat.get_members() if m.user.id not in chat and not m.user.is_bot])
        )

    try:
        await msg.delete()
    except err.RPCError as rpc:
        print(f"<{rpc}>")


@tg.on_message(filters.command(['leave', f'leave@{me.username}']) & filters.group)
async def leave_tag_all(_, msg):
    try:
        user = User.from_telegram(msg.from_user.id)
        if user.left_chat_tag(msg.chat.id):
            text = "Теперь в этой группе я тебя не отмечу"
        else:
            text = "Я итак тебя не отмечаю"
    except err.RPCError as rpc:
        if msg.sender_chat:
            text = "Так как ты являешся --анонимным-- администратором, я не могу отметить тебя"
        else:
            text = "Что-то пошло не так. Попробуй позже"

    minilib.run(run_func, (await msg.reply(text)).delete, msg.delete)


@tg.on_message(filters.command(['add', f'add@{me.username}']) & filters.group)
async def add_tag_all(_, msg):
    try:
        user = User.from_telegram_id(msg.from_user.id)
        if user.add_chat_tag(msg.chat.id):
            text = "С этого момента я буду отмечать тебя в группе"
        else:
            text = "Я итак отмечаю тебя в группе, не спамь пожалуйста"
    except err.RPCError as rpc:
        if msg.sender_chat:
            text = "Я не могу тебя отметить в группе, т.к. ты - анонимный администратор"
        else:
            text = "Что-то пошло не так. Попробуй позже"

    minilib.run(run_func, (await msg.reply(text)).delete, msg.delete)


@tg.on_callback_query()
async def callback_query(_, qry):
    photo, caption, markup = photos.get(qry.data, photos["menu"]), captions.get(qry.data, ""), markups.get(qry.data, [])
    msg, user = qry.message, qry.from_user

    if str(msg.chat.id) in chats:
        del chats[str(msg.chat.id)]

    if qry.data == "tournir":
        verified = [False, False]

        for x, chat in enumerate(["fpg_chat", "fpg_tournament"]):
            try:
                verified[x] = (await tg.get_chat_member(chat, user.id)).status not in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]
            except err.RPCError as rpc:
                print(f"<{rpc}>")

        if all(verified):
            url = settings.get("Турнир", "Ссылка")
            if url:
                markup = [
                    [types.InlineKeyboardButton("Регистрация", url=url)],
                    [types.InlineKeyboardButton("Правила", url="https://telegra.ph/Pravila-turnira-01-03")]
                ]
            else:
                caption = captions["no_tournir"]
        else:
            caption = captions["subscribe"]
            markup = list(filter(bool, map(lambda x: (None if x[1] else markups["subscribe"][x[0]]), enumerate(verified))))

        markup.append([types.InlineKeyboardButton("<< Назад", callback_data="menu")])
    elif qry.data == "social":
        markup = [
            [types.InlineKeyboardButton(txt, url=url)]
            for txt, url in settings.iter_group("Соц.сети")
        ]

        markup.append([types.InlineKeyboardButton("<< Назад", callback_data="info")])

    if bool(markup) and isinstance(markup, list):
        markup = types.InlineKeyboardMarkup(markup)

    await edit_photo(
        msg, photo, caption,
        reply_markup=(markup if bool(markup) else None)
    )


if __name__ == '__main__':
    tg.run(start())
