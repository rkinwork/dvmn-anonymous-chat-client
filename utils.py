import sys
import contextlib

import asyncio
import configargparse
from aiofiles.os import wrap as aiowrap

DEFAULT_LOG_DESCRIPTOR = aiowrap(sys.stdout.write)
LOG_DTTM_TMPL = '%d-%m-%y %H:%M:%S'
ATTEMPT_DELAY_SECS = 3
ATTEMPTS_BEFORE_DELAY = 2
DEFAULT_SERVER_HOST = 'minechat.dvmn.org'
DEFAULT_LISTEN_SERVER_PORT = 5000
DEFAULT_SEND_SERVER_PORT = 5050
DEFAULT_HISTORY_FILE = 'minechat.history'


def setup_config():
    p = configargparse.ArgParser(default_config_files=['conf.ini'])
    p.add_argument('-u', '--host', help='host of the chat server', env_var='DVMN_HOST', default=DEFAULT_SERVER_HOST)
    p.add_argument('-p', '--port', help='port of the chat server', env_var='DVMN_SEND_PORT',
                   default=DEFAULT_SEND_SERVER_PORT)
    p.add_argument('-d', '--debug', help='switch on debug mode', env_var='DVMN_DEBUG', action='store_true')
    group = p.add_mutually_exclusive_group()
    group.add_argument('-t', '--token', help='authorization token', env_var='DVMN_AUTH_TOKEN')
    group.add_argument('-n', '--nickname', help='name of the new user')
    return p.parse_args()


def decode_message(message):
    return message.decode('utf-8').strip()


async def dummy_message_writer(msg):
    await asyncio.sleep(0)


@contextlib.asynccontextmanager
async def open_connection(server, port, message_writer=None):
    attempt = 0
    connected = False
    reader, writer = None, None
    message_writer = message_writer or dummy_message_writer
    while True:
        try:
            reader, writer = await asyncio.open_connection(server, port)
            await message_writer("Соединение установлено")
            connected = True
            yield reader, writer
            break

        except asyncio.CancelledError:
            raise

        except (ConnectionRefusedError, ConnectionResetError):
            if connected:
                await message_writer("Соединение было разорвано")
                break
            if attempt >= ATTEMPTS_BEFORE_DELAY:
                await message_writer(f"Нет соединения. Повторная попытка через {ATTEMPT_DELAY_SECS} сек.")
                await asyncio.sleep(ATTEMPT_DELAY_SECS)
                continue
            attempt += 1
            await message_writer(f"Нет соединения. Повторная попытка.")

        finally:
            if all((reader, writer)):
                writer.close()
                await writer.wait_closed()
            await message_writer("Соединение закрыто")
