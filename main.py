import re

from random import choice
from utils import *

LINK_RE = re.compile(r"(https://)?t.me/(c/)?(?P<username>[0-9]+|[a-z0-9_]+)/(?P<message>[0-9]+)")


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
        print(f"<{rpc}>")


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
            "".join([u.user.mention(getattr(emoji, choice(emojis), '🫥'))
                     async for u in msg.chat.get_members() if str(u.user.id) not in chat and not u.user.is_bot])
        )

    try:
        await msg.delete()
    except err.RPCError as rpc:
        print(f"<{rpc}>")


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


@tg.on_edited_message(filters.chat(["test_fpg_channel", "fpg_tournament"]) & ~filters.me & ~filters.service)
async def edited_channel_handler(_, msg):
    news = 1043945356305629317 if msg.chat.username == "test_fpg_channel" else news_id
    news = await ds.fetch_channel(news)
    text = msg.text
    file, files = [], []
    edited = False
    async for dsm in news.history(after=msg.date, limit=10):
        if msg.link in dsm.content:
            if bool(msg.media_group_id):
                md_group = await msg.get_media_group()
                files = await asyncio.gather(*[m.download() for m in (md_group)])
                files = list(map(lambda f: (File(f)), files))
                text = "\n".join(filter(bool, map(lambda cap: getattr(cap.caption, "markdown", cap.caption), md_group)))
            elif bool(msg.poll):
                text = f"{msg.poll.question}\n" + '\n'.join(f"[{x}] {o.text}" for x, o in enumerate(msg.poll.options, start=1))
            elif bool(msg.media):
                files = [File(await msg.download())]
                text = msg.caption

            if bool(text):
                text = f"\n{getattr(text, 'markdown', text)}"

            await dsm.edit(content=f"||@everyone||{text}\n> {'Голосуй' if bool(msg.poll) else 'Больше'} здесь {msg.link}",
                           attachments=files, suppress=True)
            edited = True
            break

    if not edited:
        await channel_handler(tg, msg)

    rmtree(join(sdir, 'downloads'), ignore_errors=True)
    del edited, file, files, news, text


@tg.on_message(filters.chat(["fpg_tournament", "test_fpg_channel"]) & ~filters.me & ~filters.service)
async def channel_handler(_, msg):
    kwargs = {}
    method, text = 'send_message', ''

    if bool(msg.media_group_id):
        md_group = await msg.get_media_group()
        md_group.sort(key=lambda k: k.id)
        if msg.id != md_group[-1].id:
            del kwargs, text, method, md_group
            return
        text = "\n".join(filter(bool, map(lambda m: getattr(m.caption, "markdown", ""), md_group)))
        if bool(text):
            text = f"\n{text}"
        kwargs["from_chat_id"] = msg.chat.id
        kwargs["message_id"] = msg.id
        kwargs["captions"] = f"||@everyone||{text}\n> Больше здесь <{msg.link}>"
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
        else:
            text = ''

        kwargs["caption" if bool(msg.media) and not bool(msg.poll) else "text"] = \
            f"||@everyone||{text}\n" \
            f"> {'Голосуй' if bool(msg.poll) else 'Больше'} здесь {msg.link}"

    ds_msg = await getattr(tg, method)(
        ("python_bot_coder" if msg.chat.username == "test_fpg_channel" else 1695355296), **kwargs
    )
    del kwargs, text, method

    await (ds_msg if isinstance(ds_msg, types.Message) else ds_msg[0]).reply_text(
        "Так будет выглядеть сообщение(||кроме последней строчки||) в Дискорд. Хочешь отправить?",
        reply_markup=markups["discord_send_post"], quote=True
    )


@tg.on_callback_query()
async def callback_query(_, qry):
    rmtree(join(sdir, 'downloads'), ignore_errors=True)
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
    elif qry.data.startswith("discord"):
        ds_msg = msg.reply_to_message
        await msg.delete()
        if qry.data.endswith("approve"):
            news = 1043945356305629317 if user.username == "python_bot_coder" else news_id
            news = await ds.fetch_channel(news)
            text = ds_msg.text
            file, files = None, None

            if bool(ds_msg.media_group_id):
                files = await asyncio.gather(*[m.download() for m in (await ds_msg.get_media_group())])
                files = list(map(lambda f: (File(f)), files))
                text = ds_msg.caption
            elif bool(ds_msg.media):
                file = File(await ds_msg.download())
                text = ds_msg.caption

            await news.send(getattr(text, "markdown", text), file=file, files=files,
                            suppress_embeds=True)
            del file, files, news

        if bool(ds_msg.media_group_id):
            await asyncio.gather(*[m.delete() for m in (await ds_msg.get_media_group())])
        else:
            await ds_msg.delete()
        return
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
