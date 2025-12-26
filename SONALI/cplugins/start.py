import time
import random

from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    InputMediaPhoto,
)

from youtubesearchpython.__future__ import VideosSearch

import config
from config import BANNED_USERS, OWNER_ID

from SONALI.misc import _boot_
from SONALI.plugins.sudo.sudoers import sudoers_list
from SONALI.utils.database import (
    add_served_chat_clone,
    add_served_user_clone,
    blacklisted_chats,
    get_lang,
    get_served_chats,
    get_served_users,
    get_sudoers,
    is_banned_user,
    is_on_off,
)
from SONALI.utils.decorators.language import LanguageStart
from SONALI.utils.formatters import get_readable_time
from SONALI.utils.inline import help_pannel, private_panel, start_panel

from strings import get_string


# =======================
# MEDIA
# =======================

NEXI_VID = [
    "https://telegra.ph/file/1a3c152717eb9d2e94dc2.mp4",
    "https://graph.org/file/ba7699c28dab379b518ca.mp4",
    "https://graph.org/file/83ebf52e8bbf138620de7.mp4",
    "https://graph.org/file/82fd67aa56eb1b299e08d.mp4",
    "https://graph.org/file/318eac81e3d4667edcb77.mp4",
    "https://graph.org/file/7c1aa59649fbf3ab422da.mp4",
    "https://graph.org/file/2a7f857f31b32766ac6fc.mp4",
]

YUMI_PICS = [
    "https://files.catbox.moe/xhpqtp.jpg",
    "https://files.catbox.moe/yeeu8p.jpg",
]


# =======================
# START — PRIVATE
# =======================

@Client.on_message(filters.command("start") & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    bot = await client.get_me()

    await add_served_user_clone(message.from_user.id)

    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]

        # HELP
        if name.startswith("help"):
            keyboard = help_pannel(_)
            return await message.reply_photo(
                random.choice(YUMI_PICS),
                caption=_["help_1"].format(config.SUPPORT_CHAT),
                reply_markup=keyboard,
            )

        # SUDO PANEL
        if name.startswith("sud"):
            await sudoers_list(client=client, message=message, _=_)
            return

        # YOUTUBE INFO
        if name.startswith("inf"):
            m = await message.reply_text("🔎")
            query = name.replace("info_", "", 1)
            query = f"https://www.youtube.com/watch?v={query}"

            results = VideosSearch(query, limit=1)
            data = (await results.next())["result"][0]

            title = data["title"]
            duration = data["duration"]
            views = data["viewCount"]["short"]
            thumbnail = data["thumbnails"][0]["url"].split("?")[0]
            channellink = data["channel"]["link"]
            channel = data["channel"]["name"]
            link = data["link"]
            published = data["publishedTime"]

            searched_text = _["start_6"].format(
                title,
                duration,
                views,
                published,
                channellink,
                channel,
                bot.mention,
            )

            key = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text=_["S_B_8"], url=link),
                        InlineKeyboardButton(
                            text=_["S_B_9"], url=config.SUPPORT_CHAT
                        ),
                    ],
                ]
            )

            await m.delete()
            return await client.send_photo(
                chat_id=message.chat.id,
                photo=thumbnail,
                caption=searched_text,
                reply_markup=key,
            )

    # NORMAL PRIVATE START
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_3"],
                url=f"https://t.me/{bot.username}?startgroup=true",
            )
        ],
        [
            InlineKeyboardButton(text=_["S_B_5"], user_id=OWNER_ID),
            InlineKeyboardButton(
                text=_["S_B_6"], url=config.SUPPORT_CHANNEL
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["S_B_4"], callback_data="settings_back_helper"
            ),
        ],
    ]

    await message.reply_photo(
        random.choice(YUMI_PICS),
        caption=_["c_start_2"].format(
            message.from_user.mention, bot.mention
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =======================
# START — GROUP
# =======================

@Client.on_message(filters.command("start") & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    bot = await client.get_me()

    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"],
                url=f"https://t.me/{bot.username}?startgroup=true",
            ),
            InlineKeyboardButton(
                text=_["S_B_2"], url=config.SUPPORT_CHAT
            ),
        ],
    ]

    uptime = int(time.time() - _boot_)

    await message.reply_photo(
        random.choice(NEXI_VID),
        caption=_["start_1"].format(
            bot.mention, get_readable_time(uptime)
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
    )

    await add_served_chat_clone(message.chat.id)
