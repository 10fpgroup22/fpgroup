import minilib

minilib.init()

from pyrogram import enums, filters, types, errors as err
from random import choice
from utils import *


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
        print(f"Occurred <{rpc}>")


@tg.on_message(filters.private & filters.command('start'))
async def start_private(_, msg):
    await tg.send_photo(msg.chat.id, **reply["menu"])


@tg.on_message(filters.command(['all', f'all@{me.username}']) & filters.group)
async def all_group(_, msg: types.Message):
    if (msg.from_user and msg.from_user.id in admins) or msg.sender_chat:
        chat = left.get(str(msg.chat.id), [])
        await tg.send_message(
            msg.chat.id,
            "Брат, я тебя призываю\n" +
            "".join([u.user.mention(choice(emojis))
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

    minilib.run(run_func, (await msg.reply(text)).delete, msg.delete)


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

    if len(group) == 0:
        del group

    minilib.run(run_func, (await msg.reply(text)).delete, msg.delete)


@tg.on_message(filters.command('settings') & filters.user("python_bot_coder") & filters.private)
async def settings_menu(_, msg):
    await tg.send_photo(msg.chat.id, **reply["settings"])


@tg.on_message(filters.chat("fpg_tournament") & ~filters.me & ~filters.service)
async def telegram_channel_handler(_, msg):
    kwargs = {}
    method, text = 'send_message', ''

    if bool(msg.media_group_id):
        md_group = await msg.get_media_group()
        md_group.sort(key=lambda k: k.id)
        if msg.id != md_group[-1].id:
            del kwargs, text, method, md_group
            return
        text = "\n".join(filter(bool, map(lambda m: getattr(m.caption, "markdown", ""), md_group)))
        kwargs["from_chat_id"] = msg.chat.id
        kwargs["message_id"] = msg.id
        kwargs["captions"] = f"||@everyone||\n{text}\n> Больше здесь <{msg.link}>"
        method = "copy_media_group"
        del md_group
    else:
        if bool(msg.text):
            text = msg.text
        elif bool(msg.poll):
            text = f"{msg.poll.question}\n" + '\n'.join(f"[{x}] {o.text}" for x, o in enumerate(msg.poll.options, start=1))
        elif bool(msg.media):
            text = msg.caption
            kwargs[msg.media.value] = getattr(msg, msg.media.value).file_id
            method = f"send_{msg.media.value}"

        if bool(text):
            text = f"\n{getattr(text, 'markdown', text)}"

        kwargs["caption" if bool(msg.media) and not bool(msg.poll) else "text"] = \
            f"||@everyone||{text}\n" \
            f"> {'Голосуй' if bool(msg.poll) else 'Больше'} здесь <{msg.link}>"

    ds_msg = await getattr(tg, method)(
        "python_bot_coder", **kwargs
    )
    del kwargs, text, method

    await (ds_msg if isinstance(ds_msg, types.Message) else ds_msg[0]).reply_text(
        "Так будет выглядеть сообщение(||кроме последней строчки||) в Дискорд. Хочешь отправить?",
        reply_markup=markups["discord_send_post"], quote=True
    )



@tg.on_message(filters.text & filters.private, group=1)
async def private_handler(_, msg):
    if chats.get(str(msg.chat.id), "") == "discord_send":
        del chats[str(msg.chat.id)]
        if msg.text.startswith(("t.me/fpg_tournament/", "https://t.me/fpg_tournament/")):
            chat, msg_id = msg.text.rsplit('/', 2)[1:]
            await telegram_channel_handler(tg, await tg.get_messages(chat, msg_id))


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
    elif qry.data == "discord_send":
        if user.id == 1695355296:
            chats[str(msg.chat.id)] = qry.data
        else:
            return minilib.run(run_func, (await tg.send_message(
                user.id,
                "У тебя нет доступа к этой функции"
            )).delete)
    elif qry.data.startswith("discord"):
        ds_msg = msg.reply_to_message
        if qry.data.endswith("approve"):
            news = await ds.fetch_channel(1043945356305629317)
            text = ds_msg.text
            file, files = None, None

            if bool(ds_msg.media_group_id):
                files = await asyncio.gather(*[m.download() for m in (await ds_msg.get_media_group())])
                files = list(map(lambda f: (File(f)), files))
                text = ds_msg.caption
            elif bool(ds_msg.media):
                file = File(await ds_msg.download(in_memory=True))
                text = ds_msg.caption

            await news.send(getattr(text, "markdown", text), file=file, files=files)
            rmtree(join(sdir, 'downloads'), ignore_errors=True)
            del file, files, news

        if bool(ds_msg.media_group_id):
            await asyncio.gather(*[m.delete() for m in (await ds_msg.get_media_group())])
        else:
            await ds_msg.delete()
        return await msg.delete()
    elif qry.data == "rights" and (user.id == 1695355296 or user.username == "python_bot_coder"):
        caption = ""
        markup = markups["rights_moder"]
        markup.extend(markups["rights"])
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

    await edit_photo(
        msg, photo, caption,
        reply_markup=(markup if markup else None)
    )


if __name__ == '__main__':
    tg.run(start())
