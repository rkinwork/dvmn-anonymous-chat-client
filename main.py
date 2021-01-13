from datetime import datetime
import asyncio

import gui


async def generate_messages(messages_queue: asyncio.Queue):
    while True:
        msg = f"Ping {datetime.now().timestamp():.0f}"
        messages_queue.put_nowait(msg)
        await asyncio.sleep(1)


async def main():
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    await asyncio.gather(gui.draw(messages_queue, sending_queue, status_updates_queue),
                         generate_messages(messages_queue))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
