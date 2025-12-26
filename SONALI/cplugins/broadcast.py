import asyncio
import random
from typing import Dict, List, Union

from pyrogram import Client, filters
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import FloodWait

from SONALI import app, userbot
from SONALI.misc import SUDOERS
from SONALI.utils.database import (
    get_client,
    get_served_chats_clone,
    get_served_users_clone,
)
from SONALI.utils.decorators.language import language
from SONALI.utils.formatters import alpha_to_int
from SONALI.core.mongo import mongodb, pymongodb
from config import adminlist


# =======================
# DATABASE COLLECTIONS
# =======================

authdb = mongodb.adminauth
authuserdb = mongodb.authuser
autoenddb = mongodb.autoend
assdb = mongodb.assistants
blacklist_chatdb = mongodb.blacklistChat
blockeddb = mongodb.blockedusers
chatsdbc = mongodb.chatsc
channeldb = mongodb.cplaymode
clonebotdb = pymongodb.clonebotdb
countdb = mongodb.upcount
gbansdb = mongodb.gban
langdb = mongodb.language
onoffdb = mongodb.onoffper
playmodedb = mongodb.playmode
playtypedb = mongodb.playtypedb
skipdb = mongodb.skipmode
sudoersdb = mongodb.sudoers
usersdbc = mongodb.tgusersdbc
privatedb = mongodb.privatechats
suggdb = mongodb.suggestion
cleandb = mongodb.cleanmode
queriesdb = mongodb.queries
userdb = mongodb.userstats
videodb = mongodb.vipvideocalls


# =======================
# MEMORY CACHES (FAST)
# =======================

active = []
activevideo = []
assistantdict = {}
autoend = {}
count = {}
channelconnect = {}
langm = {}
loop = {}
maintenance = []
nonadmin = {}
pause = {}
playmode = {}
playtype = {}
skipmode = {}
privatechats = {}
cleanmode = []
suggestion = {}
mute = {}
audio = {}
video = {}


# =======================
# ACTIVE CHAT HANDLERS
# =======================

async def get_active_chats_clone() -> list:
    return active


async def is_active_chat_clone(chat_id: int) -> bool:
    return chat_id in active


async def add_active_chat_clone(chat_id: int):
    if chat_id not in active:
        active.append(chat_id)


async def remove_active_chat_clone(chat_id: int):
    if chat_id in active:
        active.remove(chat_id)


# =======================
# AUTH USERS (CLONE SAFE)
# =======================

async def _get_authusers(chat_id: int) -> Dict[str, int]:
    data = await authuserdb.find_one({"chat_id": chat_id})
    return {} if not data else data["notes"]


async def get_authuser_names_clone(chat_id: int) -> List[str]:
    return list(await _get_authusers(chat_id))


async def get_authuser_clone(chat_id: int, name: str) -> Union[bool, dict]:
    notes = await _get_authusers(chat_id)
    return notes.get(name, False)


async def save_authuser_clone(chat_id: int, name: str, note: dict):
    notes = await _get_authusers(chat_id)
    notes[name] = note
    await authuserdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"notes": notes}},
        upsert=True,
    )


async def delete_authuser_clone(chat_id: int, name: str) -> bool:
    notes = await _get_authusers(chat_id)
    if name not in notes:
        return False
    del notes[name]
    await authuserdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"notes": notes}},
        upsert=True,
    )
    return True


# =======================
# BROADCAST
# =======================

IS_BROADCASTING = False


@Client.on_message(filters.command(["broadcast", "gcast"]) & SUDOERS)
@language
async def broadcast_message(client, message, _):
    global IS_BROADCASTING

    if message.reply_to_message:
        msg_id = message.reply_to_message.id
        chat_id = message.chat.id
    else:
        if len(message.command) < 2:
            return await message.reply_text(_["broad_2"])
        query = message.text.split(None, 1)[1]
        for flag in ["-pin", "-pinloud", "-nobot", "-assistant", "-user"]:
            query = query.replace(flag, "")
        if not query.strip():
            return await message.reply_text(_["broad_8"])

    IS_BROADCASTING = True
    await message.reply_text(_["broad_1"])

    # BOT BROADCAST
    if "-nobot" not in message.text:
        sent, pin = 0, 0
        chats = [int(c["chat_id"]) for c in await get_served_chats_clone()]

        for cid in chats:
            try:
                m = (
                    await client.forward_messages(cid, chat_id, msg_id)
                    if message.reply_to_message
                    else await client.send_message(cid, query)
                )
                if "-pin" in message.text:
                    await m.pin(disable_notification=True)
                    pin += 1
                elif "-pinloud" in message.text:
                    await m.pin(disable_notification=False)
                    pin += 1
                sent += 1
                await asyncio.sleep(0.2)
            except FloodWait as fw:
                if fw.value <= 200:
                    await asyncio.sleep(fw.value)
            except:
                continue

        await message.reply_text(_["broad_3"].format(sent, pin))

    # USER BROADCAST
    if "-user" in message.text:
        sent = 0
        users = [int(u["user_id"]) for u in await get_served_users_clone()]
        for uid in users:
            try:
                (
                    await client.forward_messages(uid, chat_id, msg_id)
                    if message.reply_to_message
                    else await client.send_message(uid, query)
                )
                sent += 1
                await asyncio.sleep(0.2)
            except FloodWait as fw:
                if fw.value <= 200:
                    await asyncio.sleep(fw.value)
            except:
                continue

        await message.reply_text(_["broad_4"].format(sent))

    # ASSISTANT BROADCAST
    if "-assistant" in message.text:
        from SONALI.core.userbot import assistants

        aw = await message.reply_text(_["broad_5"])
        text = _["broad_6"]

        for num in assistants:
            sent = 0
            cli = await get_client(num)
            async for dialog in cli.get_dialogs():
                try:
                    (
                        await cli.forward_messages(dialog.chat.id, chat_id, msg_id)
                        if message.reply_to_message
                        else await cli.send_message(dialog.chat.id, query)
                    )
                    sent += 1
                    await asyncio.sleep(3)
                except FloodWait as fw:
                    if fw.value <= 200:
                        await asyncio.sleep(fw.value)
                except:
                    continue
            text += _["broad_7"].format(num, sent)

        await aw.edit_text(text)

    IS_BROADCASTING = False


# =======================
# AUTO ADMIN CLEANER
# =======================

async def auto_clean():
    while True:
        await asyncio.sleep(10)
        try:
            for chat_id in await get_active_chats_clone():
                if chat_id not in adminlist:
                    adminlist[chat_id] = []

                async for member in app.get_chat_members(
                    chat_id,
                    filter=ChatMembersFilter.ADMINISTRATORS,
                ):
                    if member.privileges and member.privileges.can_manage_video_chats:
                        adminlist[chat_id].append(member.user.id)

                for user in await get_authuser_names_clone(chat_id):
                    adminlist[chat_id].append(await alpha_to_int(user))
        except:
            continue


asyncio.create_task(auto_clean())
