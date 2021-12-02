import aioimaplib
import asyncio
from typing import List, Union, Tuple, NamedTuple
from email import message_from_bytes
from email.utils import parsedate_to_datetime
from email.header import decode_header
from email.message import Message
import logging
from config import FROM, MAIL_RETENTION_DAYS, CLEANUP_PERIOD, IMAP_SESSION_DURATION, \
    LOG_PREFIX, INBOX_FOLDER, CLEANUP, MESSAGE_PL_MAINTYPE
from utils.tg_api import tg_send_media, tg_send_message
from utils import normalize_header
import datetime
from collections import namedtuple
from pytz import timezone


seq_date = namedtuple('seq_date','seq date')
seq_msg = namedtuple('seq_msg', 'seq msg')


class ImapError(Exception):
    pass


class ConnectivityError(Exception):
    pass


class CredentialsError(ImapError):
    pass


class MailboxError(ImapError):
    pass


class ServerError(ImapError):
    pass


class ConnError(ConnectivityError):
    pass


class DisconnectError(ConnectivityError):
    pass


class ImapWorker:
    def __init__(self, host:str, user:str, password:str):
        self.host = host
        self.user = user
        self.password = password
        self.suppress_notification = False

    def __repr__(self):
        return f'ImapWorker({self.user})'

    async def _connect(self):
        # connection check
        self.connection = aioimaplib.IMAP4_SSL(host=self.host, timeout=5)
        try:
            await self.connection.wait_hello_from_server()
            logging.info(f'{LOG_PREFIX["imap_conn"]} SSL connection to IMAP server established!')
            # credentials check
            logging.info(f'{LOG_PREFIX["imap_conn"]} logging in...')
            await self.connection.login(self.user, self.password)

        except asyncio.exceptions.TimeoutError:
            logging.error(f'{LOG_PREFIX["imap_conn"]} unable to connection to IMAP server {self.host}!')
            raise ConnError('No connectivity to Imap server!')

        if self.connection.get_state() == 'AUTH':
            logging.info(f'{LOG_PREFIX["imap_conn"]} login success!')
        else:
            logging.error(f'{LOG_PREFIX["imap_conn"]} wrong credentials specified for mailbox {self.user}!')
            raise CredentialsError('Wrong imap credentials specified!')

        # mailbox selection
        await self.connection.select(INBOX_FOLDER)
        if self.connection.get_state() == 'SELECTED':
            logging.info(f'{LOG_PREFIX["imap_conn"]} moved to SELECTED state!')
        else:
            logging.error(f'{LOG_PREFIX["imap_conn"]} no folder {INBOX_FOLDER} for {self.user}!')
            raise MailboxError('Wrong mailbox name specified!')


    async def disconnect(self):
        try:
            if self.connection.has_pending_idle():
                self.connection.idle_done()
            await self.connection.close()
            await self.connection.logout()
            logging.info(f'{LOG_PREFIX["imap_conn"]} connection to IMAP server terminated gracefully!')
        except asyncio.exceptions.TimeoutError:
            logging.error(f'{LOG_PREFIX["imap_conn"]} can\'t close IMAP connection gracefully, timeout occurred!')
            raise DisconnectError('Timeout during imap disconnect commands!')
        except aioimaplib.Abort:
            logging.info(f'{LOG_PREFIX["imap_conn"]} can\'t disconnect session in state {self.connection.get_state()}!')

    @property
    def state(self) -> str:
        if self.connection.get_state():
            return self.connection.get_state()
        else:
            return 'UNKNOWN'


    async def _get_new_messages(self):
        for sender in FROM:
            rule = f'UNSEEN FROM {sender}'
            logging.info(f'{LOG_PREFIX["search_new"]} searching new messages from {sender}')
            seq_list, amount = await self._search_messages(lookup_rule=rule)
            logging.info(f'{LOG_PREFIX["search_new"]} {amount} unprocessed messages found from {sender}!')
            if amount > 0:
                seq_msg_list = await self._fetch_message_body(seq_list)
                await self._process_new_message(seq_msg_list)


    async def _remove_old_messages(self):
        for sender in FROM:
            rule = f'SEEN FROM {sender}'
            logging.info(f'{LOG_PREFIX["remove_old"]} is starting for {sender}...')
            seq_list, amount = await self._search_messages(lookup_rule=rule)
            logging.info(f'{LOG_PREFIX["remove_old"]} {amount} old messages found from {sender}!')
            if amount > 0:
                seq_dates_list = await self._fetch_dates(seq_list)
                await self._process_old_message(seq_dates_list, sender=sender)


    async def _search_messages(self, lookup_rule: str) -> Union[Tuple[List, int], None]:
        response = await self.connection.search(lookup_rule)
        if response.result == 'OK':
            msg_nums_str = response.lines[0].decode()
            msg_nums_list = msg_nums_str.split()
            amount = len(msg_nums_list)
            return msg_nums_list, amount
        else:
            logging.warning(f'{LOG_PREFIX["search_new"]} error during search operation: '
                            f'{lookup_rule}, server returned status: {response.result}!')
            raise ServerError('Error during search operation!')


    async def _fetch_message_body(self, seq_list: List[str]) -> Union[List[NamedTuple], None]:
        result = list()
        for seq in seq_list:
            response = await self.connection.fetch(message_set=seq, message_parts='(RFC822)')
            if response.result == 'OK':
                msg = message_from_bytes(response.lines[1])
                element = seq_msg(seq=seq, msg=msg)
                result.append(element)
            else:
                logging.warning(f'{LOG_PREFIX["search_new"]} error during fetching message {seq} body,'
                                f'server returned status: {response.result} !')
                raise ServerError('Error during fetch operation!')
        return result


    async def _fetch_dates(self, seq_list: List[str]) -> List[NamedTuple]:
        result = list()
        for seq in seq_list:
            response = await self.connection.fetch(message_set=seq, message_parts='(BODY[HEADER])')
            if response.result == 'OK':
                msg_header = message_from_bytes(response[1][1])
                msg_date_str = msg_header['Date']
                msg_date = parsedate_to_datetime(msg_date_str)
                element = seq_date(seq=seq, date=msg_date)
                result.append(element)
            else:
                logging.warning(f'{LOG_PREFIX["remove_old"]} error during fetching message {seq} header,'
                                f'server returned status: {response.result} !')
                raise ServerError('Error during fetch operation!')
        return result


    async def _process_new_message(self, seq_msg_list: List[NamedTuple]) -> None:
        for element in seq_msg_list:
            if not self.suppress_notification:
                element: seq_msg

                # getting attributes
                # attributes = dict()
                # attributes['from'] = normalize_header(element.msg['Return-path'])
                # attributes['date'] = element.msg['Date']
                # subject = decode_header(element.msg['Subject'])[0][0]
                # if isinstance(subject, bytes):
                    # for cases, when subject is base64 encoded
                    # subject = subject.decode()
                # attributes['subject'] = subject
                # await tg_send_message(attributes=attributes)

                for part in element.msg.walk():
                    part: Message
                    if part.get_content_maintype() == 'text':
                        text = part.get_payload()
                        if part['Content-Transfer-Encoding'] == 'base64':
                            text = part.get_payload(decode=True).decode()
                        await tg_send_message(text=text)

                    if part.get_content_maintype() == MESSAGE_PL_MAINTYPE:
                        pl = part.get_payload(decode=True)
                        await tg_send_media(pl)
            # mark message as Seen
            await self.connection.store(element.seq, '+FLAGS', '\\Seen')
            logging.info(f'{LOG_PREFIX["search_new"]} processing complete!')


    async def _process_old_message(self, seq_dates_list: List[NamedTuple], sender: str) -> None:
        current_date = datetime.datetime.today().replace(tzinfo=timezone('EET'))
        deleted_count = 0
        for element in seq_dates_list:
            element: seq_date
            delta = current_date - element.date
            if delta.days > MAIL_RETENTION_DAYS:
                await self.connection.store(element.seq, '+FLAGS', '\\Deleted')
                deleted_count += 1
        await self.connection.expunge()
        logging.info(f'{LOG_PREFIX["remove_old"]} {deleted_count} messages deleted from {sender}!')


    async def run(self):

        def check_exception(exc):
            for ex in exc:
                if isinstance(ex, asyncio.exceptions.TimeoutError):
                    raise ConnError('Timeout occurred!')
                elif isinstance(ex,aioimaplib.Abort):
                    raise ServerError('unexpected tagged response with pending sync command')
                elif isinstance(ex, ServerError):
                    raise ex

        while True:
            await self._connect()

            session_est_time = datetime.datetime.now()

            # In order not to run cleanup on each loop iteration
            last_cleanup_run = datetime.datetime.now()

            # imap idle loop
            while True:
                # break idle loop if IMAP session duration exceeded IMAP_SESSION_DURATION
                session_loop_now = datetime.datetime.now()
                session_delta = session_loop_now - session_est_time
                if session_delta.seconds > IMAP_SESSION_DURATION:
                    break

                result = await asyncio.gather(self._get_new_messages(), return_exceptions=True)
                check_exception(result)

                # In order not to run cleanup on each loop iteration
                idle_loop_now = datetime.datetime.now()
                idle_delta = idle_loop_now - last_cleanup_run
                if idle_delta.seconds > CLEANUP_PERIOD and CLEANUP:
                    result = await asyncio.gather(self._remove_old_messages(), return_exceptions=True)
                    check_exception(result)
                    last_cleanup_run = datetime.datetime.now()

                # handle connection interruption
                try:
                    logging.info(f'{LOG_PREFIX["imap_conn"]} staring idle mode for {self.user}')
                    idle_task = await self.connection.idle_start(timeout=60)
                    await self.connection.wait_server_push()
                    self.connection.idle_done()
                    await asyncio.wait_for(idle_task, timeout=5)
                    logging.info(f'{LOG_PREFIX["imap_conn"]} ending idle mode for user {self.user}')

                except asyncio.exceptions.TimeoutError:
                    logging.error(f'{LOG_PREFIX["imap_conn"]} connection to IMAP server lost!')
                    raise ConnError('connection to IMAP server lost!')

                except aioimaplib.Abort as e:
                    logging.error(f'{LOG_PREFIX["imap_conn"]} server error: {e}')
                    raise ServerError(f'Server error: {e}')

            # Close IMAP session gracefully to avoid session timeout
            await self.disconnect()