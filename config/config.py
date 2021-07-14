from dotenv import load_dotenv
import os

load_dotenv()

LOGIN = os.getenv('imap_login')
PASSWORD = os.getenv('imap_password')
HOST = 'imap.ukr.net'
FROM = ['bondar.tech.home@meta.ua', 'aleksandr.bondar.1985@gmail.com']
MAIL_RETENTION_DAYS = 3
CLEANUP = True
CLEANUP_PERIOD = 30 #seconds
IMAP_SESSION_DURATION = 60 #seconds
LOG_FILE_SIZE = 5*1024*1024
LOGGING_LEVEL = 10 #20-INFO, 10- DEBUG
BOT_TOKEN = os.getenv('BOT_TOKEN')
INBOX_FOLDER = 'INBOX'
RETRY_HISTORY = 3
MAX_INTERVAL = 30
RESTART_SUPPRESS = 300

chat_ids = [
    #-1001418109829,
    785293792
]
admins = [
    785293792
]

LOG_PREFIX = {
    'search_new': '--new_message--',
    'remove_old': '==mailbox_cleanup==',
    'imap_conn': '**IMAP_connection**',
    'network': '++Network++',
    'telegram': '~~Telegram~~'
}