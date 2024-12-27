import telebot
from telebot import types
import sqlite3
import re
import os
from datetime import datetime
import requests

# Настройки
API_TOKEN = '7216690383:AAGPtNiQ_F2Bsa1rdC_sVT8lhic7ghjS6Fo'
ADMIN_BOT_API_TOKEN = '8126103952:AAGSX9IZcjAoHI1VVLgmztUGrfv_QJMIBvk'
ADMIN_BOT_CHAT_ID = '5338389700'

bot = telebot.TeleBot(API_TOKEN)
admin_bot = telebot.TeleBot(ADMIN_BOT_API_TOKEN)

# Настройка базы данных
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    name TEXT,
    phone TEXT,
    code TEXT,
    registration_date TEXT
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT UNIQUE,
    status TEXT
)
''')
conn.commit()

user_data = {}

# Логирование
def log_event(event):
    with open('bot_logs.txt', 'a', encoding='utf-8') as log_file:
        log_file.write(f"{datetime.now()} - {event}\n")

# Уведомление администратора
def send_admin_notification(user_data):
    try:
        admin_message = (
            f"Новый пользователь зарегистрирован:\n"
            f"Имя: {user_data['name']}\n"
            f"Телефон: {user_data['phone']}\n"
            f"Код: {user_data['code']}\n"
            f"Дата регистрации: {user_data['registration_date']}"
        )
        admin_bot_url = f"https://api.telegram.org/bot{ADMIN_BOT_API_TOKEN}/sendMessage"
        payload = {
            'chat_id': ADMIN_BOT_CHAT_ID,
            'text': admin_message
        }
        requests.post(admin_bot_url, data=payload)
    except Exception as e:
        log_event(f"Ошибка отправки уведомления администратору: {e}")

# Стартовое сообщение
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user = get_user(message.chat.id)
    if not user:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Регистрация')
        bot.send_message(message.chat.id, "Добро пожаловать! Пожалуйста, зарегистрируйтесь, чтобы продолжить.", reply_markup=markup)
    else:
        send_main_menu(message)

# Главное меню
def send_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Отслеживание товаров', 'Аккаунт')
    markup.add('Адрес в Кыргызстане', 'Канал', 'Запрещённые товары')
    bot.send_message(message.chat.id, "Выберите нужный раздел:", reply_markup=markup)

# Проверка пользователя
def get_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if user:
        return {
            'user_id': user[1],
            'name': user[2],
            'phone': user[3],
            'code': user[4],
            'registration_date': user[5]
        }
    return None

# Регистрация
@bot.message_handler(func=lambda message: message.text == 'Регистрация')
def registration(message):
    user = get_user(message.chat.id)
    if user:
        bot.send_message(message.chat.id, "Вы уже зарегистрированы!")
        send_main_menu(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Отмена')
    msg = bot.send_message(message.chat.id, "Введите ваше имя:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_name_step)

def process_name_step(message):
    if message.text.lower() == 'отмена':
        bot.send_message(message.chat.id, "Регистрация отменена.", reply_markup=types.ReplyKeyboardRemove())
        return
    user_data[message.chat.id] = {'name': message.text}
    msg = bot.send_message(message.chat.id, "Введите ваш номер телефона (только цифры):")
    bot.register_next_step_handler(msg, process_phone_step)

def process_phone_step(message):
    if message.text.lower() == 'отмена':
        bot.send_message(message.chat.id, "Регистрация отменена.", reply_markup=types.ReplyKeyboardRemove())
        return
    if not re.match(r'^\d{10,15}$', message.text):
        msg = bot.send_message(message.chat.id, "Неверный формат телефона. Попробуйте снова.")
        bot.register_next_step_handler(msg, process_phone_step)
        return

    user_data[message.chat.id]['phone'] = message.text
    complete_registration(message)

def complete_registration(message):
    user_id = message.chat.id
    name = user_data[user_id]['name']
    phone = user_data[user_id]['phone']
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    user_code = f"A1{432 + user_count}"
    registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('INSERT INTO users (user_id, name, phone, code, registration_date) VALUES (?, ?, ?, ?, ?)',
                   (user_id, name, phone, user_code, registration_date))
    conn.commit()

    user_data[user_id]['code'] = user_code
    user_data[user_id]['registration_date'] = registration_date

    send_admin_notification(user_data[user_id])

    # Уникальный код
    bot.send_message(message.chat.id, f"Ваш уникальный код: {user_code}")

    # Отправка адреса отдельными сообщениями
    address_message_part1 = (
        f"Адрес склада в Китае:\n"
    )
    bot.send_message(message.chat.id, address_message_part1)

    address_message_part2 = (
        f"广东省佛山市南海区里水镇环镇南路33号1号仓315库B6961"
        f"收货人 梅先生-B6961\n"
        f"13250150777\n"
    )
    bot.send_message(message.chat.id, address_message_part2)

    # Отправка двух видео
    video_paths = ['instruction.mp4', 'instructions.mp4']
    for path in video_paths:
        try:
            with open(path, 'rb') as video:
                bot.send_video(message.chat.id, video)
        except FileNotFoundError:
            bot.send_message(message.chat.id, f"Видео {path} временно недоступно.")

    bot.send_message(message.chat.id, "Регистрация завершена!")
    send_main_menu(message)

# Функциональность отслеживания товаров
@bot.message_handler(func=lambda message: message.text == 'Отслеживание товаров')
def track_product(message):
    msg = bot.send_message(message.chat.id, "Введите уникальный код товара для отслеживания:")
    bot.register_next_step_handler(msg, process_tracking)

def process_tracking(message):
    product_code = message.text.strip()
    cursor.execute('SELECT status FROM products WHERE product_code = ?', (product_code,))
    product = cursor.fetchone()
    if product:
        bot.send_message(message.chat.id, f"Статус вашего товара: {product[0]}")
    else:
        bot.send_message(message.chat.id, "Товар с таким кодом не найден. Пожалуйста, проверьте код и попробуйте снова.")

# Обработка кнопки "Аккаунт"
@bot.message_handler(func=lambda message: message.text == 'Аккаунт')
def account_info(message):
    user = get_user(message.chat.id)
    if user:
        bot.send_message(
            message.chat.id,
            f"Ваш аккаунт:\n"
            f"Имя: {user['name']}\n"
            f"Телефон: {user['phone']}\n"
            f"Код: {user['code']}\n"
            f"Дата регистрации: {user['registration_date']}"
        )
    else:
        bot.send_message(message.chat.id, "Вы не зарегистрированы. Пожалуйста, зарегистрируйтесь.")

# Обработка кнопки "Канал"
@bot.message_handler(func=lambda message: message.text == 'Канал')
def send_channel_links(message):
    bot.send_message(
        message.chat.id,
        "Ссылки на наши каналы:\n"
        "1. [Telegram канал](https://t.me/+N1Xktz9wb55jZjRi)\n"
        "2. [отзовы](https://web.telegram.org/k/#-2069386995)\n\n"
        "Для связи: [Личка](https://t.me/Seocargo)",
        parse_mode="Markdown"
    )
# Обработка кнопки "Адрес в Кыргызстане"
@bot.message_handler(func=lambda message: message.text == 'Адрес в Кыргызстане')
def send_address_kg(message):
    # Отправка геолокации (город Ош, пр. Абсамата Масалиева 46А)
    latitude = 40.513409  # Широта (Ош)
    longitude = 72.816244  # Долгота (Ош)
    bot.send_location(message.chat.id, latitude, longitude)
    
    # Отправка сообщения с текстовым адресом
    bot.send_message(message.chat.id, "Адрес: г. Ош, пр. Абсамата Масалиева 46А")

    # Отправка видео
    video_path = 'mds.mp4'  # Название файла с видео
    try:
        with open(video_path, 'rb') as video:
            bot.send_video(message.chat.id, video)
    except FileNotFoundError:
        bot.send_message(message.chat.id, f"Видео {video_path} временно недоступно.")

# Обработка кнопки "Запрещённые товары"
@bot.message_handler(func=lambda message: message.text == 'Запрещённые товары')
def send_prohibited_items(message):
    image_paths = [f"{i}.png" for i in range(1, 11)]  # Список из 10 картинок (1.png, 2.png, ..., 10.png)
    for path in image_paths:
        try:
            with open(path, 'rb') as image:
                bot.send_photo(message.chat.id, image)
        except FileNotFoundError:
            bot.send_message(message.chat.id, f"Картинка {path} временно недоступна.")


if __name__ == '__main__':
    bot.infinity_polling()
