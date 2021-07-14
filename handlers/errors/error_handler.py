import logging

from loader import dp
from aiogram.types import Update

@dp.errors_handler()
async def error_handler(update: Update, exception):
    await update.get_current().message.answer(f'Exception occurred:\n{exception}')
    logging.exception(exception)
    return True