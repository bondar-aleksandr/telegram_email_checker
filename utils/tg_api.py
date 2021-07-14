import asyncio
from typing import Dict
import aiogram.utils.exceptions
from loader import bot
from config import chat_ids, LOG_PREFIX
import logging


async def tg_send_message(text: str = None, attributes: Dict = None):
    msg = str()
    if attributes:
        for key, val in attributes.items():
            msg += f'<b>{key}</b>: <code>{val}</code>\n'
    if text:
        msg += text
    for chat in chat_ids:
        while True:
            try:
                await bot.send_message(chat_id=chat, text=msg)
                break
            except aiogram.exceptions.CantParseEntities:
                break
            except aiogram.exceptions.RetryAfter:
                logging.warning(f'{LOG_PREFIX["search_new"]} Telegram rate limit exceeded, retrying...')
                await asyncio.sleep(15)


async def tg_send_media(media: bytearray):
    for chat in chat_ids:
        while True:
            try:
                await bot.send_photo(photo=media, chat_id=chat)
                logging.info(f'{LOG_PREFIX["search_new"]} Successfully sent via Telegram!')
                break
            except aiogram.utils.exceptions.RetryAfter:
                logging.warning(f'{LOG_PREFIX["search_new"]} Telegram rate limit exceeded, retrying...')
                await asyncio.sleep(15)