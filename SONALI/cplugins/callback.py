import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from pyrogram.enums import ChatMemberStatus

import config
from config import BANNED_USERS, adminlist, votemode, confirmer

from SONALI import app, YouTube
from SONALI.core.call import SONALI_CALL
from SONALI.misc import SUDOERS, db

from SONALI.utils.database import (
    get_assistant,
    get_upvote_count,
    is_active_chat,
    is_music_playing,
    is_nonadmin_chat,
    music_on,
    music_off,
    mute_on,
    mute_off,
    is_muted,
    set_loop,
)
from SONALI.utils.decorators.language import languageCB
from SONALI.utils.formatters import seconds_to_min
from SONALI.utils.inline import (
    close_markup,
    stream_markup,
    stream_markup2,
    panel_markup_1,
    panel_markup_2,
    panel_markup_3,
    panel_markup_4,
    panel_markup_5,
    queue_markup,
)
from SONALI.utils.stream.autoclear import auto_clean
from SONALI.utils.thumbnails import gen_thumb


# ===================== ASSISTANT UNBAN ===================== #

@Client.on_callback_query(filters.regex("^unban_assistant$"))
async def unban_assistant(client, cb: CallbackQuery):
    chat_id = cb.message.chat.id
    assistant = await get_assistant(chat_id)

    try:
        await client.unban_chat_member(chat_id, assistant.id)
        await cb.answer("Assistant unbanned successfully ✅", show_alert=True)
    except:
        await cb.answer(
            "I need BAN permissions to unban my assistant ❌",
            show_alert=True,
        )


# ===================== PANEL NAVIGATION ===================== #

@Client.on_callback_query(filters.regex("^PanelMarkup") & ~BANNED_USERS)
@languageCB
async def panel_nav(client, cb: CallbackQuery, _):
    await cb.answer()
    videoid, chat_id = cb.data.split(None, 1)[1].split("|")
    chat_id = cb.message.chat.id

    buttons = panel_markup_1(_, videoid, chat_id)
    await cb.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_callback_query(filters.regex("^Pages") & ~BANNED_USERS)
@languageCB
async def panel_pages(client, cb: CallbackQuery, _):
    await cb.answer()
    state, page, videoid, chat = cb.data.split(None, 1)[1].split("|")
    chat_id = int(chat)
    page = int(page)

    playing = db.get(chat_id)
    if not playing:
        return

    if state == "Forw":
        buttons = [
            panel_markup_5,
            panel_markup_1,
            panel_markup_2,
        ][page](_, videoid, chat_id)

    else:
        if page == 0:
            buttons = panel_markup_3(_, videoid, chat_id)
        elif page == 1:
            buttons = panel_markup_1(_, videoid, chat_id)
        elif page == 2:
            buttons = panel_markup_5(_, videoid, chat_id)
        else:
            buttons = panel_markup_4(
                _,
                playing[0]["vidid"],
                chat_id,
                seconds_to_min(playing[0]["played"]),
                playing[0]["dur"],
            )

    await cb.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ===================== ADMIN CONTROLS ===================== #

upvoters = {}

@Client.on_callback_query(filters.regex("^ADMIN") & ~BANNED_USERS)
@languageCB
async def admin_controls(client, cb: CallbackQuery, _):
    await cb.answer()
    command, chat = cb.data.split(None, 1)[1].split("|")

    if "_" in chat:
        chat_id, counter = chat.split("_")
        chat_id = int(chat_id)
    else:
        chat_id = int(chat)
        counter = None

    if not await is_active_chat(chat_id):
        return await cb.answer(_["general_5"], show_alert=True)

    mention = cb.from_user.mention

    # ---- Permission Check ---- #
    if command not in ["UpVote"] and cb.from_user.id not in SUDOERS:
        if not await is_nonadmin_chat(chat_id):
            admins = adminlist.get(chat_id, [])
            if cb.from_user.id not in admins:
                return await cb.answer(_["admin_14"], show_alert=True)

    # ================= VOTE SKIP ================= #
    if command == "UpVote":
        upvoters.setdefault(chat_id, {}).setdefault(cb.message.id, [])
        votemode.setdefault(chat_id, {}).setdefault(cb.message.id, 0)

        if cb.from_user.id in upvoters[chat_id][cb.message.id]:
            upvoters[chat_id][cb.message.id].remove(cb.from_user.id)
            votemode[chat_id][cb.message.id] -= 1
        else:
            upvoters[chat_id][cb.message.id].append(cb.from_user.id)
            votemode[chat_id][cb.message.id] += 1

        required = await get_upvote_count(chat_id)
        current = votemode[chat_id][cb.message.id]

        if current >= required:
            await cb.edit_message_text(_["admin_37"].format(required))
            return

        button = InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"👍 {current}", callback_data=cb.data)]]
        )
        return await cb.edit_message_reply_markup(reply_markup=button)

    # ================= PLAYBACK ================= #

    if command == "Pause":
        if not await is_music_playing(chat_id):
            return await cb.answer(_["admin_1"], show_alert=True)

        await music_off(chat_id)
        await SONALI_CALL.pause_stream(chat_id)
        return await cb.message.reply_text(_["admin_2"].format(mention))

    if command == "Resume":
        await music_on(chat_id)
        await SONALI_CALL.resume_stream(chat_id)
        return await cb.message.reply_text(_["admin_4"].format(mention))

    if command in ["Stop", "End"]:
        await SONALI_CALL.stop_stream(chat_id)
        await set_loop(chat_id, 0)
        return await cb.message.reply_text(
            _["admin_5"].format(mention),
            reply_markup=close_markup(_),
        )

    if command == "Mute":
        if await is_muted(chat_id):
            return await cb.answer(_["admin_45"], show_alert=True)
        await mute_on(chat_id)
        await SONALI_CALL.mute_stream(chat_id)
        return await cb.message.reply_text(_["admin_46"].format(mention))

    if command == "Unmute":
        if not await is_muted(chat_id):
            return await cb.answer(_["admin_47"], show_alert=True)
        await mute_off(chat_id)
        await SONALI_CALL.unmute_stream(chat_id)
        return await cb.message.reply_text(_["admin_48"].format(mention))

    if command == "Loop":
        await set_loop(chat_id, 3)
        return await cb.message.reply_text(_["admin_41"].format(mention, 3))

    if command == "Shuffle":
        queue = db.get(chat_id)
        if not queue or len(queue) < 2:
            return await cb.answer(_["admin_42"], show_alert=True)

        first = queue.pop(0)
        random.shuffle(queue)
        queue.insert(0, first)
        return await cb.message.reply_text(_["admin_44"].format(mention))
