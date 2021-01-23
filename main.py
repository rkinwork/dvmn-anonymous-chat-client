import asyncio

import aiofiles

import gui
from utils import setup_config, open_connection, ATTEMPT_DELAY_SECS


async def read_msgs(host: str, port: str, message_queue: asyncio.Queue, save_message_queue: asyncio.Queue):
    while True:
        async with open_connection(host, port) as rw:
            reader, *_ = rw
            while True:
                row = await reader.readline()
                if not row:
                    break
                row = row.decode('utf8').strip()
                message_queue.put_nowait(row)
                save_message_queue.put_nowait(row)

        await asyncio.sleep(ATTEMPT_DELAY_SECS)


async def send_msgs(host: str, port: str, sending_queue: asyncio.Queue):
    while True:
        msg = await sending_queue.get()
        print(f'Пользователь написал: {msg}')


async def save_messages(filepath, queue: asyncio.Queue):
    async with aiofiles.open(filepath, 'a', buffering=1) as log_file:
        while True:
            message_to_save = await queue.get()
            await log_file.write(f'{message_to_save}\n')


def load_chat_history(filepath, queue: asyncio.Queue):  # gui blocking risk
    with open(filepath) as log_file:
        for row in log_file:
            queue.put_nowait(row.strip())


async def main():
    conf = setup_config()
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    save_message_queue = asyncio.Queue()

    load_chat_history(conf.filepath, messages_queue)
    await asyncio.gather(gui.draw(messages_queue, sending_queue, status_updates_queue),
                         save_messages(conf.filepath, save_message_queue),
                         read_msgs(conf.host, conf.port, messages_queue, save_message_queue),
                         send_msgs(conf.host, conf.port, sending_queue),
                         )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
