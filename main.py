import asyncio

import gui
from utils import setup_config, open_connection, ATTEMPT_DELAY_SECS


async def read_rows_from_server(rows_reader, message_queue):
    while True:
        row = await rows_reader.readline()
        if not row:
            break
        message_queue.put_nowait(f"{row.decode('utf8').strip()}")


async def read_msgs(host: str, port: str, message_queue: asyncio.Queue):
    while True:
        async with open_connection(host, port) as rw:
            reader, *_ = rw
            while True:
                await read_rows_from_server(reader, message_queue)

        await asyncio.sleep(ATTEMPT_DELAY_SECS)


async def main():
    conf = setup_config()
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    await asyncio.gather(gui.draw(messages_queue, sending_queue, status_updates_queue),
                         read_msgs(conf.host, conf.port, messages_queue)
                         )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
