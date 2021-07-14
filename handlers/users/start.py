from aiogram import types
from loader import dp
from config import chat_ids

@dp.message_handler(commands='start', chat_id=chat_ids)
async def start_command(message: types.Message):
    await message.answer('Для запуска действий не требуется')
