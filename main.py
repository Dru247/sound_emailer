import datetime
import logging
import os
import sqlite3 as sq
import telebot

from dotenv import load_dotenv
from telebot import types


load_dotenv()

db = "sound.db"

logging.basicConfig(
    level=logging.INFO,
    filename="logs.log",
    filemode="a",
    format="%(asctime)s %(levelname)s %(message)s")

bot = telebot.TeleBot(
    token=os.getenv("TELEGRAM_TOKEN"),
    parse_mode=None)

keyboard_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
commands = [
    "Get songs",
    "Add song",
    "Get list",
    "Get song",
    "Change"
]
list_keys = list()
for key in commands:
    list_keys.append(types.KeyboardButton(key))
keyboard_main.row(*list_keys)


def get_songs(message):
    msg = bot.send_message(chat_id=message.chat.id, text="era")
    bot.register_next_step_handler(message=msg, callback=select_songs)


def select_songs(message):
    try:
        age = int(message.text)
        era_start = datetime.datetime.now().year - age + int(os.getenv("ERA_START"))
        era_end = era_start + int(os.getenv("ERA_DURATION"))
        if age >= 50:
            era_end += 4
        with sq.connect(db) as con:
            cur = con.cursor()
            cur.execute(f"""
                SELECT id, name, year, grade, data FROM songs
                WHERE year BETWEEN {era_start} AND {era_end}
               ORDER BY grade
            """)
            results = cur.fetchall()
        for song in results:
            file_name = f"{song[0]}-{song[1]}-{song[2]}-{song[3]}.mp3"
            with open(file_name, 'wb') as new_file:
                new_file.write(song[4])
            with open(file_name, "rb") as audio:
                bot.send_audio(message.chat.id, audio)
            os.remove(file_name)
    except Exception:
        logging.critical(msg="func select_songs - error", exc_info=True)


def add_song(message):
    msg = bot.send_message(chat_id=message.chat.id, text='load_song > caption "name;year;grade"')
    bot.register_next_step_handler(message=msg, callback=load_song)


def load_song(message):
    try:
        file_id = message.audio.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        f_name, f_year, f_grade = message.json["caption"].strip().split(";")
        with sq.connect(db) as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO songs (name, year, grade, data) VALUES (?, ?, ?, ?)",
                (f_name, f_year, f_grade, sq.Binary(downloaded_file))
            )
    except Exception:
        logging.critical(msg="func load_song - error", exc_info=True)


def get_list(message):
    try:
        with sq.connect(db) as con:
            cur = con.cursor()
            cur.execute("SELECT id, name, year, grade FROM songs ORDER BY name")
            result = cur.fetchall()
        msg_text = str()
        for song in result:
            msg_text += f'{song[0]}: "{song[1]}" | {song[2]} г. | {song[3]} оц.\n'
        bot.send_message(chat_id=message.chat.id, text=msg_text)
    except Exception:
        logging.critical(msg="func get_list - error", exc_info=True)


def get_song(message):
    try:
        msg = bot.send_message(chat_id=message.chat.id, text="id")
        bot.register_next_step_handler(message=msg, callback=select_song)
    except Exception:
        logging.critical(msg="func get_song - error", exc_info=True)


def select_song(message):
    try:
        with sq.connect(db) as con:
            cur = con.cursor()
            cur.execute(f"""
                SELECT id, name, year, grade, data FROM songs
                WHERE id = {message.text}
            """)
            song = cur.fetchone()
        file_name = f"{song[0]}-{song[1]}-{song[2]}-{song[3]}.mp3"
        with open(file_name, 'wb') as new_file:
            new_file.write(song[4])
        with open(file_name, "rb") as audio:
            bot.send_audio(message.chat.id, audio)
        os.remove(file_name)
    except Exception:
        logging.critical(msg="func get_song - error", exc_info=True)


def change_song(message):
    try:
        msg = bot.send_message(chat_id=message.chat.id, text="id")
        bot.register_next_step_handler(message=msg, callback=change_request)
    except Exception:
        logging.critical(msg="func change_song - error", exc_info=True)


def change_request(message):
    try:
        key_1 = types.InlineKeyboardButton(
            text="Name",
            callback_data=f"change;name {message.text}")
        key_2 = types.InlineKeyboardButton(
            text="Year",
            callback_data=f"change;year {message.text}")
        key_3 = types.InlineKeyboardButton(
            text="Grade",
            callback_data=f"change;grade {message.text}")
        key_4 = types.InlineKeyboardButton(
            text="Del",
            callback_data=f"change;del {message.text}")
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(key_1, key_2, key_3, key_4)
        bot.send_message(
            chat_id=message.chat.id,
            text="Что меняем?",
            reply_markup=keyboard)
    except Exception:
        logging.critical(msg="func change_request - error", exc_info=True)


def change_request_text(message, call_data):
    try:
        call_data = call_data.split()
        id_song = call_data[1]
        column = call_data[0].split(";")[1]
        if column == "del":
            with sq.connect(db) as con:
                cur = con.cursor()
                cur.execute(f"DELETE FROM songs WHERE id = {id_song}")
                bot.send_message(chat_id=message.chat.id, text="Success")
        else:
            msg = bot.send_message(chat_id=message.chat.id, text="Введи текст")
            bot.register_next_step_handler(message=msg, callback=change_select, data=(id_song, column))
    except Exception:
        logging.critical(msg="func change_request_text - error", exc_info=True)


def change_select(message, data):
    try:
        select_text = f"UPDATE songs SET {data[1]} = '{message.text}' WHERE id = {data[0]}"
        logging.info(msg=select_text)
        with sq.connect(db) as con:
            cur = con.cursor()
            cur.execute(select_text)
        bot.send_message(chat_id=message.chat.id, text="Success")
    except Exception:
        logging.critical(msg="func change_select - error", exc_info=True)


@bot.message_handler(commands=['start', 'help'])
def help_message(message):
    bot.send_message(
        message.chat.id,
        text="Hi! Catch the keyboard!",
        reply_markup=keyboard_main)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if "change" in call.data:
        change_request_text(call.message, call.data)


@bot.message_handler(content_types=['text'])
def take_text(message):
    if message.text.lower() == commands[0].lower():
        get_songs(message)
    elif message.text.lower() == commands[1].lower():
        add_song(message)
    elif message.text.lower() == commands[2].lower():
        get_list(message)
    elif message.text.lower() == commands[3].lower():
        get_song(message)
    elif message.text.lower() == commands[4].lower():
        change_song(message)
    else:
        logging.warning(
            f"func take_text: not understand question: {message.text}")
        bot.send_message(message.chat.id, "I don't understand")


if __name__ == "__main__":
    bot.infinity_polling()
