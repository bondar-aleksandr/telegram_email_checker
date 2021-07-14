from aiogram.types import BotCommand


async def set_bot_commands(dp):
    await dp.bot.set_my_commands([
        BotCommand('start','Начать работу'),
        BotCommand('help', 'Помощь'),
        BotCommand('imap_status', 'Проверить состояние imap подключения'),
        BotCommand('imap_suppress', 'Отключить уведомления'),
        BotCommand('imap_unsuppress', 'Включить уведомления')
    ])
