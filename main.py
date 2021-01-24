import asyncio
import logging

import gui
from utils import setup_config, load_chat_history, save_messages, read_msgs, send_msgs


async def main():
    conf = setup_config()
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    save_message_queue = asyncio.Queue()

    if conf.debug:
        logging.basicConfig(level=logging.DEBUG)

    load_chat_history(conf.filepath, messages_queue)
    await asyncio.gather(gui.draw(messages_queue, sending_queue, status_updates_queue),
                         save_messages(conf.filepath, save_message_queue),
                         read_msgs(conf.host, conf.lport, messages_queue, save_message_queue),
                         send_msgs(conf.host, conf.port, conf.token, sending_queue),
                         )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
