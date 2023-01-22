from minilib import Dispatcher, run
from pyrogram import enums, filters, types, errors as err
from random import choice
from utils import *

dsp = Dispatcher()


@tg.on_message(filters.chat(group_id) & filters.service, group=-1)
async def admin_group_handler(_, msg):
    global admins
    admins = [mbr.user.id async for mbr in tg.get_chat_members(msg.chat.id) if not mbr.user.is_bot]


@tg.on_message(filters.service & ~filters.private & ~filters.chat("fpg_tournament"), group=-1)
async def group_handler(_, msg):
    try:
        await msg.delete()
    except err.RPCError as rpc:
        print(f"Occurred <{rpc}>")


@tg.on_message(filters.chat("fpg_chat") & filters.new_chat_members)
async def new_chat_member(_, msg):
    welcome = await tg.send_message(
        msg.chat.id,
        f"Давайте поприветствуем нового участника нашей группы - <a href='tg://user?id={msg.from_user.id}'>{msg.from_user.first_name}</a>"
    )
    run(run_func, welcome.delete, 30)
    try:
        await tg.send_message(
            msg.from_user.id,
            f"Приветствую тебя в нашей группе, {msg.from_user.first_name}!\n👇Для начала рекомендую прочитать Правила группы👇",
            reply_markup=types.InlineKeyboardMarkup([
                [types.InlineKeyboardButton("📋Правила группы📋", url="https://telegra.ph/Pravila-gruppy-09-21-4")]
            ])
        )
    except err.RPCError as rpc:
        print(f"Occurred <{rpc}>")


# @tg.on_message(filters.chat("fpg_tournament") & ~filters.me & ~filters.service)
# async def telegram_channel_handler(_, msg):
#     if bool(msg.service):
#         return await msg.delete()

#     news = await ds.fetch_channel(news_id)
#     text, photos = '', None

#     if bool(msg.text):
#         text = msg.text.markdown
#     elif bool(msg.caption):
#         text = msg.caption.markdown
#     elif bool(msg.poll):
#         text = f"{msg.poll.question}\n" + '\n'.join(f"[{x}] {opt.text}" for x, opt in enumerate(msg.poll.options, 1))

#     text += '\n' if bool(text) else ''

#     await news.send("||@everyone||\n{0}> {1} здесь <{2}>".format(
#         text, ('Голосуй' if bool(msg.poll) else 'Больше'), msg.link
#     ))


@tg.on_message(filters.private & filters.command('start'))
async def start_private(_, msg):
    await tg.send_photo(msg.chat.id, **reply["menu"])


@tg.on_message(filters.command(['all', f'all@{me.username}']) & filters.group)
async def all_group(_, msg: types.Message):
    if (msg.from_user and msg.from_user.id in admins) or msg.sender_chat:
        chat = left.setdefault(str(msg.chat.id), [])
        await tg.send_message(
            msg.chat.id,
            "Брат, я тебя призываю\n" +
            "".join([f"<a href='tg://user?id={u.user.id}'>{choice(emojis)}</a>"
                     async for u in msg.chat.get_members() if str(u.user.id) not in chat and not u.user.is_bot])
        )

    try:
        await msg.delete()
    except err.RPCError as rpc:
        print(f"Occurred <{rpc}>")


@tg.on_message(filters.command(['leave', f'leave@{me.username}']) & filters.group)
async def leave_tag_all(_, msg):
    group = left.setdefault(str(msg.chat.id), [])
    try:
        group.append(str(msg.from_user.id))
        text = f"Теперь в этой группе я тебя не отмечу"
    except err.RPCError as rpc:
        if msg.sender_chat:
            text = f"Так как ты являешся --анонимным-- администратором, я итак не могу отметить тебя"

    run(run_func, (await msg.reply(text)).delete, msg.delete, timeout=30)


@tg.on_message(filters.command(['add', f'add@{me.username}']) & filters.group)
async def add_tag_all(_, msg):
    group = left.setdefault(str(msg.chat.id), [])
    try:
        if str(msg.from_user.id) in group:
            group.remove(str(msg.from_user.id))
            text = f"С этого момента я буду отмечать тебя в группе"
        else:
            text = f"Я итак отмечаю тебя в группе, не спамь пожалуйста"
    except err.RPCError as rpc:
        if msg.sender_chat:
            text = f"Я не могу тебя отметить в группе, т.к. ты - анонимный администратор"

    run(run_func, (await msg.reply(text)).delete, msg.delete, timeout=30)


@tg.on_message(filters.command('settings') & filters.user("python_bot_coder") & filters.private)
async def settings_menu(_, msg):
    await tg.send_photo(msg.chat.id, **reply["settings"])


@tg.on_callback_query()
async def callback_query(_, qry):
    photo, caption, markup = photos["menu"], "", []
    msg, user = qry.message, qry.from_user

    if qry.data == "tournir":
        photo, markup = photos["tournir"], []
        verified = [False, False]

        for x, chat in enumerate(["fpg_chat", "fpg_tournament"]):
            try:
                verified[x] = (await tg.get_chat_member(chat, user.id)).status in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]
            except err.RPCError as rpc:
                print(f"Occurred <{rpc}>")

        if all(verified):
            url = settings.get("Турнир", "Ссылка")
            if url:
                caption, markup = captions["tournir"], [
                    [types.InlineKeyboardButton("Регистрация", url=url)],
                    [types.InlineKeyboardButton("Правила", url="https://telegra.ph/Pravila-turnira-01-03")]
                ]
            else:
                caption = captions["no_tournir"]
        else:
            caption = captions["subscribe"]
            markup = list(filter(bool, map(lambda x: (None if x[1] else markups["subscribe"][x[0]]), enumerate(verified))))

        markup.append([types.InlineKeyboardButton("<< Назад", callback_data="menu")])
    elif qry.data == "create_post":
        pass
    elif qry.data == "rights":
        photo, caption, markup = photos["rights"], captions["rights"], markups["rights"]
        if user.id in admins:
            caption = ""
            markup = markups["rights_moder"]
    elif qry.data == "social":
        photo, markup = photos["social"], [
            [types.InlineKeyboardButton(txt, url=url)]
            for txt, url in settings.iter_group("Соц.сети")
        ]

        markup.append([types.InlineKeyboardButton("<< Назад", callback_data="info")])
    elif qry.data == 's_tournir':
        url = settings.get("Турнир", "Ссылка")
        photo, caption = photos["settings"], f"На данный момент ссылка на турнир: {url if url else 'отсутствует'}"
        
        if url:
            markup = [
                [types.InlineKeyboardButton("🖊Изменить", callback_data="e_tournir")],
                [types.InlineKeyboardButton("❌Удалить❌", callback_data="d_tournir")]
            ]
        else:
            markup = [
                [types.InlineKeyboardButton("➕Добавить", callback_data="a_tournir")]
            ]

        markup.append([types.InlineKeyboardButton("<< Назад", callback_data="settings")])
    elif qry.data in reply:
        photo, caption, markup = photos.get(qry.data, photos["menu"]), \
            captions.get(qry.data, ""), markups.get(qry.data, [])

    if isinstance(markup, list) and len(markup) > 0:
        markup = types.InlineKeyboardMarkup(markup)

    await edit_photo(
        msg, photo, caption,
        reply_markup=(markup if markup else None)
    )


if __name__ == '__main__':
    tg.run(start())
