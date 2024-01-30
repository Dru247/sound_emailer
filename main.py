import datetime
import logging
import os
import sqlite3 as sq
import telebot

from dotenv import load_dotenv


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

keyboard_main = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
commands = ["Get songs",
            "Add song"
            ]
list_keys = list()
for key in commands:
    list_keys.append(telebot.types.KeyboardButton(key))
keyboard_main.row(*list_keys)


def get_songs(message):
    msg = bot.send_message(chat_id=message.chat.id, text="era")
    bot.register_next_step_handler(message=msg, callback=select_songs)


def select_songs(message):
    try:
        era_start = datetime.datetime.now().year - int(message.text) + int(os.getenv("ERA_START"))
        era_end = era_start + int(os.getenv("ERA_DURATION"))
        with sq.connect(db) as con:
            cur = con.cursor()
            cur.execute(f"""
                SELECT name, year, data FROM songs
                WHERE year BETWEEN {era_start} AND {era_end}
               ORDER BY grade
            """)
            results = cur.fetchall()
            for song in results:
                file_name = f"{song[0]}-{song[1]}.mp3"
                with open(file_name, 'wb') as new_file:
                    new_file.write(song[2])
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


@bot.message_handler(commands=['start', 'help'])
def help_message(message):
    bot.send_message(
        message.chat.id,
        text="Hi! Catch the keyboard!",
        reply_markup=keyboard_main)


@bot.message_handler(content_types=['text'])
def take_text(message):
    if message.text.lower() == commands[0].lower():
        get_songs(message)
    elif message.text.lower() == commands[1].lower():
        add_song(message)
    else:
        logging.warning(
            f"func take_text: not understand question: {message.text}")
        bot.send_message(message.chat.id, "I don't understand")


if __name__ == "__main__":
    bot.infinity_polling()
