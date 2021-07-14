import socket
import time
import collections
from aiogram import executor
from utils import set_bot_commands
from handlers import dp
from loader import imap_worker
import asyncio
import aiogram
import aiohttp
import sys
import signal
from config import LOG_FILE_SIZE, LOG_PREFIX, LOGGING_LEVEL, RETRY_HISTORY, MAX_INTERVAL, RESTART_SUPPRESS
import logging
from logging.handlers import RotatingFileHandler

from utils.imap_api import DisconnectError, ImapError, ConnectivityError
from utils.tg_api import tg_send_message


if sys.platform == 'win32':
    signals = None
else:
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)


rotating_file_handler = RotatingFileHandler(
    filename='./log/app.log',
    mode='a',
    maxBytes=LOG_FILE_SIZE,
    backupCount=2,
    encoding='utf-8'
)
rotating_file_handler.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)


logging.basicConfig(format=u'%(filename)s [LINE:%(lineno)d] #%(levelname)-8s [%(asctime)s]  %(message)s',
                    level=LOGGING_LEVEL, handlers = [rotating_file_handler, stream_handler])


async def on_startup(dp):
    await tg_send_message('Бот запущен!')
    await set_bot_commands(dp)


async def shutdown(loop, s:signal = None):
    if s:
        logging.info(f'Received exit signal {s.name}')
    logging.info(f'{LOG_PREFIX["imap_conn"]} closing imap connection...')
    try:
        await imap_worker.disconnect()
    except DisconnectError:
        pass
    logging.info('Canceling tasks...')
    tasks = [t for t in asyncio.all_tasks() if t is not
             asyncio.current_task()]
    [task.cancel() for task in tasks]
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.exceptions.CancelledError:
        pass

    logging.info(f'{len(tasks)} tasks canceled!')
    logging.info('Shut down!')
    loop.stop()


def exception_handler(loop: asyncio.AbstractEventLoop, context: dict):
    exc: Exception
    exc = context.get('exception', context['message'])
    logging.error(f'Caught exception: {exc}')
    if isinstance(exc, (socket.gaierror, aiohttp.ClientError, aiogram.exceptions.NetworkError)):
        logging.error('No network connection!')
        loop.create_task(shutdown(loop=loop))
    elif isinstance(exc, aiogram.exceptions.TerminatedByOtherGetUpdates) :
        logging.error('Another bot instance is running somewhere!')
        loop.create_task(shutdown(loop=loop))


async def supervisor(func, retry_history=RETRY_HISTORY, max_interval=MAX_INTERVAL):
    start_times = collections.deque([float('-inf')], maxlen=retry_history)
    while True:
        start_times.append(time.monotonic())
        try:
            return await func()
        except ConnectivityError as e:
            if min(start_times) > time.monotonic() - max_interval:
                logging.error(f'suppressed restart for {RESTART_SUPPRESS} sec for function {func}')
                await asyncio.sleep(RESTART_SUPPRESS)
            else:
                logging.error(f'{func} restarted due to {e}')
                await tg_send_message(text=f'imap процесс перезапущен по причине: <code>{e}</code>')
        except ImapError:
            await shutdown(loop=loop)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    #loop.set_debug(enabled=True)
    loop.set_exception_handler(exception_handler)
    if signals:
        for s in signals:
            loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown(loop=loop, s=s)))
    loop.create_task(supervisor(imap_worker.run))
    # loop.run_forever()
    executor.start_polling(dp, on_startup=on_startup)
