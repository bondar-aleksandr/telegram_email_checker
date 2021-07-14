from aiogram import types
from loader import dp
from config import chat_ids

@dp.message_handler(commands='help', chat_id=chat_ids)
async def start_command(message: types.Message):
    await message.answer('Бот для мониторинга работы системы видеонаблюдения,'
                         ' присылает screenshot с камер наблюдения при обнаружении движения')
