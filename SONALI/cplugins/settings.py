from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.errors import MessageNotModified
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from SONALI import app
from SONALI.utils.database import (
    add_nonadmin_chat,
    get_authuser,
    get_authuser_names,
    get_playmode,
    get_playtype,
    get_upvote_count,
    is_nonadmin_chat,
    is_skipmode,
    remove_nonadmin_chat,
    set_playmode,
    set_playtype,
    set_upvotes,
    skip_off,
    skip_on,
)
from SONALI.utils.decorators.admins import ActualAdminCB
from SONALI.utils.decorators.language import language, languageCB
from SONALI.utils.inline.settings import (
    auth_users_markup,
    playmode_users_markup,
    setting_markup,
    vote_mode_markup,
)
from SONALI.utils.inline.start import private_panel
from config import BANNED_USERS, OWNER_ID


# =======================
# SETTINGS COMMAND
# =======================

@Client.on_message(
    filters.command(["settings", "setting"]) & filters.group & ~BANNED_USERS
)
@language
async def settings_mar(client, message: Message, _):
    cname = (await client.get_me()).mention
    buttons = setting_markup(_)
    await message.reply_text(
        _["setting_1"].format(cname, message.chat.id, message.chat.title),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =======================
# SETTINGS CALLBACK
# =======================

@Client.on_callback_query(filters.regex("settings_helper") & ~BANNED_USERS)
@languageCB
async def settings_cb(client, callback_query: CallbackQuery, _):
    cname = (await client.get_me()).mention
    try:
        await callback_query.answer(_["set_cb_5"])
    except:
        pass

    buttons = setting_markup(_)
    await callback_query.edit_message_text(
        _["setting_1"].format(
            cname,
            callback_query.message.chat.id,
            callback_query.message.chat.title,
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@Client.on_callback_query(filters.regex("settingsback_helper") & ~BANNED_USERS)
@languageCB
async def settings_back_markup(client, callback_query: CallbackQuery, _):
    cname = (await client.get_me()).mention
    try:
        await callback_query.answer()
    except:
        pass

    if callback_query.message.chat.type == ChatType.PRIVATE:
        buttons = private_panel(_)
        await callback_query.edit_message_text(
            _["start_2"].format(callback_query.from_user.mention, cname),
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        buttons = setting_markup(_)
        await callback_query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )


# =======================
# NON-ADMIN CALLBACK ANSWERS
# =======================

@Client.on_callback_query(
    filters.regex(
        r"^(SEARCHANSWER|PLAYMODEANSWER|PLAYTYPEANSWER|AUTHANSWER|ANSWERVOMODE|VOTEANSWER|PM|AU|VM)$"
    )
    & ~BANNED_USERS
)
@languageCB
async def without_admin_rights(client, callback_query: CallbackQuery, _):
    command = callback_query.matches[0].group(1)

    if command == "SEARCHANSWER":
        return await callback_query.answer(_["setting_2"], show_alert=True)

    if command == "PLAYMODEANSWER":
        return await callback_query.answer(_["setting_5"], show_alert=True)

    if command == "PLAYTYPEANSWER":
        return await callback_query.answer(_["setting_6"], show_alert=True)

    if command == "AUTHANSWER":
        return await callback_query.answer(_["setting_3"], show_alert=True)

    if command == "VOTEANSWER":
        return await callback_query.answer(_["setting_8"], show_alert=True)

    if command == "ANSWERVOMODE":
        current = await get_upvote_count(callback_query.message.chat.id)
        return await callback_query.answer(
            _["setting_9"].format(current),
            show_alert=True,
        )

    if command == "PM":
        await callback_query.answer(_["set_cb_2"], show_alert=True)
        playmode = await get_playmode(callback_query.message.chat.id)
        is_non_admin = await is_nonadmin_chat(callback_query.message.chat.id)
        playtype = await get_playtype(callback_query.message.chat.id)

        buttons = playmode_users_markup(
            _,
            Direct=(playmode == "Direct"),
            Group=not is_non_admin,
            Playtype=(playtype != "Everyone"),
        )

    elif command == "AU":
        await callback_query.answer(_["set_cb_1"], show_alert=True)
        is_non_admin = await is_nonadmin_chat(callback_query.message.chat.id)
        buttons = auth_users_markup(_, not is_non_admin)

    elif command == "VM":
        mode = await is_skipmode(callback_query.message.chat.id)
        current = await get_upvote_count(callback_query.message.chat.id)
        buttons = vote_mode_markup(_, current, mode)

    try:
        await callback_query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except MessageNotModified:
        pass


# =======================
# ADMIN: VOTE COUNT CHANGE
# =======================

@Client.on_callback_query(filters.regex("FERRARIUDTI") & ~BANNED_USERS)
@ActualAdminCB
async def addition(client, callback_query: CallbackQuery, _):
    mode = callback_query.data.split(None, 1)[1]

    if not await is_skipmode(callback_query.message.chat.id):
        return await callback_query.answer(_["setting_10"], show_alert=True)

    current = await get_upvote_count(callback_query.message.chat.id)

    if mode == "M":
        final = max(2, current - 2)
        if final == 0:
            return await callback_query.answer(_["setting_11"], show_alert=True)
    else:
        final = min(15, current + 2)
        if final == 17:
            return await callback_query.answer(_["setting_12"], show_alert=True)

    await set_upvotes(callback_query.message.chat.id, final)
    buttons = vote_mode_markup(_, final, True)

    try:
        await callback_query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except MessageNotModified:
        pass


# =======================
# ADMIN: PLAY MODE / TYPE
# =======================

@Client.on_callback_query(
    filters.regex(r"^(MODECHANGE|CHANNELMODECHANGE|PLAYTYPECHANGE)$")
    & ~BANNED_USERS
)
@ActualAdminCB
async def playmode_ans(client, callback_query: CallbackQuery, _):
    command = callback_query.matches[0].group(1)

    if command == "CHANNELMODECHANGE":
        if await is_nonadmin_chat(callback_query.message.chat.id):
            await remove_nonadmin_chat(callback_query.message.chat.id)
        else:
            await add_nonadmin_chat(callback_query.message.chat.id)

    elif command == "MODECHANGE":
        playmode = await get_playmode(callback_query.message.chat.id)
        await set_playmode(
            callback_query.message.chat.id,
            "Inline" if playmode == "Direct" else "Direct",
        )

    elif command == "PLAYTYPECHANGE":
        playtype = await get_playtype(callback_query.message.chat.id)
        await set_playtype(
            callback_query.message.chat.id,
            "Admin" if playtype == "Everyone" else "Everyone",
        )

    playmode = await get_playmode(callback_query.message.chat.id)
    playtype = await get_playtype(callback_query.message.chat.id)
    is_non_admin = await is_nonadmin_chat(callback_query.message.chat.id)

    buttons = playmode_users_markup(
        _,
        Direct=(playmode == "Direct"),
        Group=not is_non_admin,
        Playtype=(playtype != "Everyone"),
    )

    try:
        await callback_query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except MessageNotModified:
        pass


# =======================
# ADMIN: AUTH USERS
# =======================

@Client.on_callback_query(filters.regex(r"^(AUTH|AUTHLIST)$") & ~BANNED_USERS)
@ActualAdminCB
async def authusers_mar(client, callback_query: CallbackQuery, _):
    command = callback_query.matches[0].group(1)

    if command == "AUTHLIST":
        auth_users = await get_authuser_names(callback_query.message.chat.id)
        if not auth_users:
            return await callback_query.answer(_["setting_4"], show_alert=True)

        msg = _["auth_7"].format(callback_query.message.chat.title)
        count = 0

        for user_id in auth_users:
            data = await get_authuser(callback_query.message.chat.id, user_id)
            try:
                user = await client.get_users(data["auth_user_id"])
                count += 1
                msg += (
                    f"{count}➤ {user.first_name}"
                    f"[<code>{data['auth_user_id']}</code>]\n"
                    f"   {_['auth_8']} {data['admin_name']}"
                    f"[<code>{data['admin_id']}</code>]\n\n"
                )
            except:
                continue

        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=_["BACK_BUTTON"], callback_data="AU"
                    ),
                    InlineKeyboardButton(
                        text=_["CLOSE_BUTTON"], callback_data="close"
                    ),
                ]
            ]
        )
        return await callback_query.edit_message_text(msg, reply_markup=buttons)

    if await is_nonadmin_chat(callback_query.message.chat.id):
        await remove_nonadmin_chat(callback_query.message.chat.id)
        buttons = auth_users_markup(_, True)
    else:
        await add_nonadmin_chat(callback_query.message.chat.id)
        buttons = auth_users_markup(_)

    await callback_query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# =======================
# ADMIN: VOTE MODE TOGGLE
# =======================

@Client.on_callback_query(filters.regex("VOMODECHANGE") & ~BANNED_USERS)
@ActualAdminCB
async def vote_change(client, callback_query: CallbackQuery, _):
    if await is_skipmode(callback_query.message.chat.id):
        await skip_off(callback_query.message.chat.id)
        mod = None
    else:
        await skip_on(callback_query.message.chat.id)
        mod = True

    current = await get_upvote_count(callback_query.message.chat.id)
    buttons = vote_mode_markup(_, current, mod)

    try:
        await callback_query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except MessageNotModified:
        pass
