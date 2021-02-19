import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from enum import Enum
import asyncio

from anyio import create_task_group, sleep


class TkAppClosed(Exception):
    pass


class ReadConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class SendingConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class NicknameReceived:
    def __init__(self, nickname):
        self.nickname = nickname


def process_new_message(input_field, sending_queue):
    text = input_field.get()
    sending_queue.put_nowait(text)
    input_field.delete(0, tk.END)


async def update_tk(root_frame, interval=1 / 120):
    while True:
        try:
            root_frame.update()
        except tk.TclError:
            # if application has been destroyed/closed
            raise TkAppClosed()
        await sleep(interval)


async def update_conversation_history(panel, messages_queue):
    while True:
        msg = await messages_queue.get()

        panel['state'] = 'normal'
        if panel.index('end-1c') != '1.0':
            panel.insert('end', '\n')
        panel.insert('end', msg)
        # TODO сделать промотку умной, чтобы не мешала просматривать историю сообщений
        # ScrolledText.frame
        # ScrolledText.vbar
        panel.yview(tk.END)
        panel['state'] = 'disabled'


async def update_status_panel(status_labels, status_updates_queue):
    nickname_label, read_label, write_label = status_labels

    read_label['text'] = f'Чтение: нет соединения'
    write_label['text'] = f'Отправка: нет соединения'
    nickname_label['text'] = f'Имя пользователя: неизвестно'

    while True:
        msg = await status_updates_queue.get()
        if isinstance(msg, ReadConnectionStateChanged):
            read_label['text'] = f'Чтение: {msg}'

        if isinstance(msg, SendingConnectionStateChanged):
            write_label['text'] = f'Отправка: {msg}'

        if isinstance(msg, NicknameReceived):
            nickname_label['text'] = f'Имя пользователя: {msg.nickname}'


def create_status_panel(root_frame):
    status_frame = tk.Frame(root_frame)
    status_frame.pack(side="bottom", fill=tk.X)

    connections_frame = tk.Frame(status_frame)
    connections_frame.pack(side="left")

    nickname_label = tk.Label(connections_frame, height=1, fg='grey', font='arial 10', anchor='w')
    nickname_label.pack(side="top", fill=tk.X)

    status_read_label = tk.Label(connections_frame, height=1, fg='grey', font='arial 10', anchor='w')
    status_read_label.pack(side="top", fill=tk.X)

    status_write_label = tk.Label(connections_frame, height=1, fg='grey', font='arial 10', anchor='w')
    status_write_label.pack(side="top", fill=tk.X)

    return (nickname_label, status_read_label, status_write_label)


async def draw(messages_queue, sending_queue, status_updates_queue):
    root = tk.Tk()

    root.title('Чат Майнкрафтера')

    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    status_labels = create_status_panel(root_frame)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side="bottom", fill=tk.X)

    input_field = tk.Entry(input_frame)
    input_field.pack(side="left", fill=tk.X, expand=True)

    input_field.bind("<Return>", lambda event: process_new_message(input_field, sending_queue))

    send_button = tk.Button(input_frame)
    send_button["text"] = "Отправить"
    send_button["command"] = lambda: process_new_message(input_field, sending_queue)
    send_button.pack(side="left")

    conversation_panel = ScrolledText(root_frame, wrap='none')
    conversation_panel.pack(side="top", fill="both", expand=True)

    async with create_task_group() as tg:
        await tg.spawn(update_tk, root_frame)
        await tg.spawn(update_conversation_history, conversation_panel, messages_queue)
        await tg.spawn(update_status_panel, status_labels, status_updates_queue)


def show_token_error():
    messagebox.showinfo("Неверный токен", "Проверьте токен, сервер его не узнал.")


def register_user(root, input_field, nickname_queue):
    nick_name = input_field.get()
    nick_name = nick_name.strip()
    if len(nick_name) == 0:
        messagebox.showerror("Ошибка", "Пустой никнейм, по пробуйте ещё раз")
        root.destroy()
    nickname_queue.put_nowait(nick_name)


async def check_register(root, register_queue: asyncio.Queue):
    res = await register_queue.get()
    if not res:
        messagebox.showerror("Ошибка", "Проблема с регистрацией, по пробуйте ещё раз")
        root.destroy()
        return

    messagebox.showinfo("Успех", f"Ваш токен сохранён в файл {res}")
    root.destroy()


async def draw_register(register_queue: asyncio.Queue, nickname_queue: asyncio.Queue):
    root = tk.Tk()

    root.title('Регистрация пользователя')

    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(fill=tk.X)

    label = tk.Label(input_frame)
    label["text"] = "Введите желаемый никнейм"
    label["height"] = "3"
    label.pack(side="top", fill=tk.Y)

    input_field = tk.Entry(input_frame)
    input_field.pack(side="left", fill=tk.X, expand=True)

    send_button = tk.Button(input_frame)
    send_button["text"] = "Отправить"
    send_button["command"] = lambda: register_user(root, input_field, nickname_queue)
    send_button.pack(side="left")

    async with create_task_group() as tg:
        await tg.spawn(check_register, root, register_queue)
        await tg.spawn(update_tk, root_frame)
