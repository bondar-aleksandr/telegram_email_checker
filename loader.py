from config import BOT_TOKEN
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import LOGIN, PASSWORD, HOST

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)

# ImapWorker imported only after bot is created, since ImapWorker use tg_api, which requires bot to be operational
from utils.imap_api import ImapWorker
imap_worker = ImapWorker(host=HOST, user=LOGIN, password=PASSWORD)