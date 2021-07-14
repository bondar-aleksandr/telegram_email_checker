from aiogram import types
from loader import dp, imap_worker
from config import chat_ids, admins


@dp.message_handler(commands='imap_status', chat_id=chat_ids)
async def get_imap_state_tg(message: types.Message):
    msg = str()

    state = imap_worker.state
    msg += f'состояние IMAP подключения: <code>{state}</code>\n'

    suppress = imap_worker.suppress_notification
    if suppress == True:
        msg += 'уведомления: <code>ОТКЛЮЧЕНЫ</code>'
    else:
        msg += 'уведомления: <code>ВКЛЮЧЕНЫ</code>'

    await message.answer(msg)


@dp.message_handler(commands='imap_suppress', chat_id=chat_ids)
async def imap_suppress(message: types.Message):
    imap_worker.suppress_notification = True
    await message.answer('уведомления отключены!')


@dp.message_handler(commands='imap_unsuppress', chat_id=chat_ids)
async def imap_unsuppress(message: types.Message):
    imap_worker.suppress_notification = False
    await message.answer('уведомления включены!')


# @dp.message_handler(commands='imap_stop', chat_id=admins)
# async def imap_stop(message: types.Message):
#     await imap_worker.disconnect()
#     await message.answer(f'imap процесс для ящика {imap_worker.user} остановлен!')