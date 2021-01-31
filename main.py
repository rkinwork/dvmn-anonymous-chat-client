import asyncio
import logging

import gui
from utils import setup_config, load_chat_history, save_messages, handle_connection, InvalidToken


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
    coros_to_gather = [gui.draw(messages_queue, sending_queue, status_updates_queue),
                       save_messages(conf.filepath, save_message_queue),
                       handle_connection(host=conf.host,
                                         send_port=conf.port,
                                         receive_port=conf.lport,
                                         token=conf.token,
                                         messages_queue=messages_queue,
                                         save_message_queue=save_message_queue,
                                         status_updates_queue=status_updates_queue,
                                         watchdog_queue=watchdog_queue,
                                         sending_queue=sending_queue
                                         )
                       ]
    tasks_to_gather = [asyncio.create_task(coro) for coro in coros_to_gather]
    try:
        await asyncio.gather(*tasks_to_gather)
    except InvalidToken:
        gui.show_token_error()
    except gui.TkAppClosed:
        pass
    finally:
        [task.cancel() for task in tasks_to_gather]


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
