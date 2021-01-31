import contextlib
import json
import logging
import re
from enum import Enum

import asyncio
import configargparse
import aiofiles
import async_timeout
from anyio import create_task_group, ExceptionGroup, get_cancelled_exc_class, open_cancel_scope

import gui

LOG_DTTM_TMPL = '%d-%m-%y %H:%M:%S'
ATTEMPT_DELAY_SECS = 3
ATTEMPTS_BEFORE_DELAY = 2
DEFAULT_SERVER_HOST = 'minechat.dvmn.org'
DEFAULT_LISTEN_SERVER_PORT = 5000
DEFAULT_SEND_SERVER_PORT = 5050
DEFAULT_HISTORY_FILE = 'minechat.history'
ESCAPE_MESSAGE_PATTERN = re.compile('\n+')
WATCHDOG_TEMPLATE = 'Connection is alive. {msg}'
WATCHDOG_TIMEOUT_SEC = 1

watchdog_logger = logging.getLogger('watchdog_logger')
watchdog_logger.propagate = False
watchdog_logger.handlers.clear()
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(created)d] %(message)s'))
watchdog_logger.addHandler(handler)


class InvalidToken(Exception):
    pass


class WatchDogStates(Enum):
    AUTHORIZED = 'authorization done'
    NEW_MESSAGE = 'new message in chat'
    SEND_MESSAGE = 'message sent'

    def __str__(self):
        return str(self.value)


def setup_config():
    p = configargparse.ArgParser(default_config_files=['conf.ini'])
    p.add_argument('-u', '--host', help='host of the chat server', env_var='DVMN_HOST', default=DEFAULT_SERVER_HOST)
    p.add_argument('-p', '--port', help='transmit port of the chat server', env_var='DVMN_SEND_PORT',
                   default=DEFAULT_SEND_SERVER_PORT)
    p.add_argument('-l', '--lport', help='listen port of the chat server', env_var='DVMN_PORT',
                   default=DEFAULT_LISTEN_SERVER_PORT)
    p.add_argument('-d', '--debug', help='switch on debug mode', env_var='DVMN_DEBUG', action='store_true')
    p.add_argument('-f', '--filepath', help='path to the file where to store chat history',
                   env_var='DVMN_CHAT_PATH', default=DEFAULT_HISTORY_FILE)
    group = p.add_mutually_exclusive_group()
    group.add_argument('-t', '--token', help='authorization token', env_var='DVMN_AUTH_TOKEN')
    group.add_argument('-n', '--nickname', help='name of the new user')

    return p.parse_args()


async def authorise(token, reader, writer, status_updates_queue: asyncio.Queue):
    logging.debug(decode_message(await reader.readline()))
    writer.write(f"{token}\n".encode())
    response = json.loads(await reader.readline())
    if not response:
        logging.error("Unknown token. Check it, or register new user")
        return False
    logging.debug(response)
    nickname = response.get('nickname')
    if nickname:
        status_updates_queue.put_nowait(gui.NicknameReceived(response.get('nickname')))
    logging.debug(f"Выполнена авторизация. Пользователь {nickname}.")

    return True


def decode_message(message):
    return message.decode('utf-8').strip()


def reconnect(func):
    async def wrapper(*args, **kwargs):
        while True:
            try:
                await func(*args, **kwargs)
            except ConnectionError as e:
                watchdog_logger.error(f'Get connection error: {e}')
                continue

    return wrapper


@reconnect
async def handle_connection(host: str, send_port: str, receive_port: str, token: str,
                            messages_queue: asyncio.Queue,
                            save_message_queue: asyncio.Queue,
                            status_updates_queue: asyncio.Queue,
                            watchdog_queue: asyncio.Queue,
                            sending_queue: asyncio.Queue):

    # todo как здесь отлавливать Cancel? или это будет решено позже по задаче, где всё обернём в группы?
    async with create_task_group() as tg:
        await tg.spawn(read_msgs, host, receive_port, messages_queue, save_message_queue, status_updates_queue,
                       watchdog_queue)
        await tg.spawn(send_msgs, host, send_port, token, sending_queue, status_updates_queue, watchdog_queue)
        await tg.spawn(watch_for_connection, watchdog_queue)


async def read_msgs(host: str,
                    port: str,
                    message_queue: asyncio.Queue,
                    save_message_queue: asyncio.Queue,
                    status_updates_queue: asyncio.Queue,
                    watchdog_queue: asyncio.Queue,
                    ):
    while True:
        async with open_connection(host, port, status_updates_queue, gui.ReadConnectionStateChanged) as rw:
            reader, *_ = rw
            while True:
                row = await reader.readline()
                if not row:
                    break
                row = row.decode('utf8').strip()
                message_queue.put_nowait(row)
                save_message_queue.put_nowait(row)
                watchdog_queue.put_nowait(WatchDogStates.NEW_MESSAGE)

        await asyncio.sleep(ATTEMPT_DELAY_SECS)


async def send_msgs(host: str,
                    port: str,
                    token: str,
                    sending_queue: asyncio.Queue,
                    status_updates_queue: asyncio.Queue,
                    watchdog_queue: asyncio.Queue,
                    ):
    async with open_connection(host, port, status_updates_queue, gui.SendingConnectionStateChanged) as rw:
        reader, writer = rw
        if await authorise(token, reader, writer, status_updates_queue):
            auth_response = decode_message(await reader.readline())
            logging.debug(auth_response)
            watchdog_queue.put_nowait(WatchDogStates.AUTHORIZED)
        else:
            logging.error('Problems with authorization. Check your token')
            raise InvalidToken('Problems with authorization. Check your token')

        while True:
            message = await sending_queue.get()
            message = ESCAPE_MESSAGE_PATTERN.sub('\n', message)  # remove new lines
            writer.write(f"{message}\n\n".encode())
            logging.debug(message)
            logging.debug(decode_message(await reader.readline()))
            watchdog_queue.put_nowait(WatchDogStates.SEND_MESSAGE)


async def watch_for_connection(wathchdog_queue: asyncio.Queue):
    while True:
        try:
            async with async_timeout.timeout(WATCHDOG_TIMEOUT_SEC) as cm:
                state = await wathchdog_queue.get()
                message = WATCHDOG_TEMPLATE.format(msg=str(state).capitalize())
        except (asyncio.exceptions.TimeoutError,) as e:
            if cm.expired:
                message = f'{WATCHDOG_TIMEOUT_SEC}s timeout is elapsed'
                watchdog_logger.info(message)
                raise ConnectionError(message)
            else:
                raise e

        watchdog_logger.info(message)


async def save_messages(filepath, queue: asyncio.Queue):
    async with aiofiles.open(filepath, 'a', buffering=1) as log_file:
        while True:
            message_to_save = await queue.get()
            await log_file.write(f'{message_to_save}\n')


def load_chat_history(filepath, queue: asyncio.Queue):  # gui blocking risk
    with open(filepath) as log_file:
        for row in log_file:
            queue.put_nowait(row.strip())


@contextlib.asynccontextmanager
async def open_connection(server: str, port: str, status_updates_queue: asyncio.Queue, state_enum):
    attempt = 0
    connected = False
    reader, writer = None, None
    status_updates_queue.put_nowait(state_enum.INITIATED)
    while True:
        try:
            reader, writer = await asyncio.open_connection(server, port)
            status_updates_queue.put_nowait(state_enum.ESTABLISHED)
            # TODO расширить enum что бы не дублировать сообщения
            logging.debug("Соединение установлено")
            connected = True
            yield reader, writer
            break

        except asyncio.CancelledError:
            raise

        except (ConnectionRefusedError, ConnectionResetError):
            if connected:
                status_updates_queue.put_nowait(state_enum.CLOSED)
                logging.debug("Соединение было разорвано")
                break
            if attempt >= ATTEMPTS_BEFORE_DELAY:
                logging.debug(f"Нет соединения. Повторная попытка через {ATTEMPT_DELAY_SECS} сек.")
                await asyncio.sleep(ATTEMPT_DELAY_SECS)
                continue
            attempt += 1
            logging.debug(f"Нет соединения. Повторная попытка.")

        finally:
            if all((reader, writer)):
                writer.close()
                await writer.wait_closed()
            status_updates_queue.put_nowait(state_enum.CLOSED)
            logging.debug("Соединение закрыто")
