import minilib

from pyrogram import enums, filters, types, errors as err
from random import choice
from utils import *

minilib.init()


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
    minilib.run(run_func, welcome.delete, 30)
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

    minilib.run(run_func, (await msg.reply(text)).delete, msg.delete, timeout=30)


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

    minilib.run(run_func, (await msg.reply(text)).delete, msg.delete, timeout=30)


@tg.on_message(filters.command('settings') & filters.user("python_bot_coder") & filters.private)
async def settings_menu(_, msg):
    await tg.send_photo(msg.chat.id, **reply["settings"])


@tg.on_message(filters.chat("fpg_tournament") & ~filters.me & ~filters.service)
async def telegram_channel_handler(_, msg):
    kwargs = {"reply_markup": markups["discord_send_post"]}

    if bool(msg.text):
        text = msg.text
        method = "send_message"
    elif bool(msg.media_group_id):
        text = msg.caption
        method = "send_media_group"
    elif bool(msg.poll):
        text = f"{msg.poll.question}\n" + '\n'.join(f"[{x}] {o.text}" for x, o in enumerate(msg.poll.options, start=1))

    text = f"||@everyone||{('\n' + text.markdown) if bool(text) else ''}\n" \
        f"> {'Голосуй' if bool(msg.poll) else 'Больше'} здесь {msg.link}"

    if "media" in method:
        kwargs["media"] = list(map(lambda m: (types.InputMedia(
                                                  media=m.dowload(in_memory=True, block=False),
                                                  caption=text)
                                              ),
                               await msg.get_media_group()))
    else:
        kwargs["text"] = text

    await getattr(tg, method)(
        1695355296, **kwargs
    )


@tg.on_message(filters.text & filters.private)
async def private_handler(_, msg):
    if chats.get(str(msg.chat.id), "") == "discord_send":
        del chats[str(msg.chat.id)]


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
                print(f"Occurred <{rpc}>")

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
    elif qry.data.startswith("discord"):
        if qry.data.endswith("approve"):
            news = await ds.fetch_channel(news_id)
            files = None

            if msg.media_group_id:
                files = list(map(lambda m: (File(m.download(in_memory=True, block=False))),
                             await msg.get_media_group()))

            await news.send(msg.text, files=files)
        return await msg.delete()
    elif qry.data == "rights" and user.id in admins:
        caption = ""
        markup = markups["rights_moder"]
    elif qry.data == "discord_send":
        chats[str(msg.chat.id)] = qry.data
    elif qry.data == "social":
        markup = [
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
    elif qry.data.endswith("_tournir"):
        if qry.data.startswith("d"):
            settings.set("Турнир", "Ссылка", "")
            qry.data = "s_tournir"
            return await callback_query(tg, qry)

        chats[str(msg.chat.id)] = qry.data
        caption = "Введите ссылку на турнир"
        markup = [[types.InlineKeyboardButton("<< Отмена", callback_data="s_tournir")]]

    if isinstance(markup, list) and len(markup) > 0:
        markup = types.InlineKeyboardMarkup(markup)

    await edit_media(
        msg, photo, caption,
        reply_markup=(markup if markup else None)
    )


if __name__ == '__main__':
    tg.minilib.run(start())
