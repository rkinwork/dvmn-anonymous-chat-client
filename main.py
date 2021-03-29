import asyncio
import logging
from contextlib import suppress

from anyio import create_task_group, run

import gui
from utils import setup_config, load_chat_history, save_messages, handle_connection, InvalidToken, register_user


async def main():
    conf = setup_config()
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    save_message_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    if conf.debug:
        logging.basicConfig(level=logging.DEBUG)

    load_chat_history(conf.filepath, messages_queue)
    if conf.register:
        nickname_queue = asyncio.Queue()
        register_queue = asyncio.Queue()
        async with create_task_group() as tg:
            await tg.spawn(gui.draw_register, register_queue, nickname_queue)
            await tg.spawn(register_user, conf.host, conf.port, status_updates_queue, nickname_queue,
                           register_queue)

        return

    try:
        async with create_task_group() as tg:
            await tg.spawn(gui.draw, messages_queue, sending_queue, status_updates_queue)
            await tg.spawn(save_messages, conf.filepath, save_message_queue)
            await tg.spawn(handle_connection, conf.host,
                           conf.port,
                           conf.lport,
                           conf.token,
                           messages_queue,
                           save_message_queue,
                           status_updates_queue,
                           watchdog_queue,
                           sending_queue)
    except InvalidToken:
        gui.show_token_error()


if __name__ == '__main__':
    with suppress(KeyboardInterrupt, gui.TkAppClosed):
        run(main)
