import telebot
from telebot import types
import sqlite3
import re
from datetime import datetime
import requests


API_TOKEN = '8168304863:AAE2pTAg5_Cs_wHMy-GUKKyyddT1Ia_wbbE'
ADMIN_BOT_API_TOKEN = '8191961162:AAGo_BkBhLTY7VbgMJ5DTeih5wBBq_l71mE'
ADMIN_BOT_CHAT_ID = '5338389700'
API_URL = "https://south-cargo-osh.prolabagency.com/api/v1/clients/"

bot = telebot.TeleBot(API_TOKEN)
admin_bot = telebot.TeleBot(ADMIN_BOT_API_TOKEN)

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
conn.commit()

user_data = {}

def log_event(event):
    with open('bot_logs.txt', 'a', encoding='utf-8') as log_file:
        log_file.write(f"{datetime.now()} - {event}\n")

def send_admin_notification(user_data):
    try:
        admin_message = (
            f"Новый пользователь зарегистрирован:\n"
            f"Имя: {user_data['name']}\n"
            f"Телефон: {user_data['phone']}\n"
            f"Код: {user_data['code']}\n"
            f"Дата регистрации: {user_data['registration_date']}"
        )
        admin_bot.send_message(ADMIN_BOT_CHAT_ID, admin_message)
    except Exception as e:
        log_event(f"Ошибка отправки уведомления администратору: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = get_user(message.chat.id)
    if not user:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Регистрация')
        bot.send_message(message.chat.id, "Добро пожаловать! Зарегистрируйтесь, чтобы продолжить.", reply_markup=markup)
    else:
        send_main_menu(message)

def send_data_to_api(user_data):
    try:
        response = requests.post(API_URL, json=user_data)
        if response.status_code == 200:
            log_event("Данные успешно отправлены на сайт")
        else:
            log_event(f"Ошибка отправки данных на сайт: {response.status_code} - {response.text}")
    except Exception as e:
        log_event(f"Ошибка соединения с API сайта: {e}")


    test_data = {
                f"Имя: {user_data['name']}\n"
                f"Телефон: {user_data['phone']}\n"
                f"Код: {user_data['code']}\n"
                f"Дата регистрации: {user_data['registration_date']}"
    }

    response = requests.post(API_URL, json=test_data)
    print(response.status_code, response.text)

def send_data_to_api(user_data):
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(API_URL, json=user_data, headers=headers)
        
        if response.status_code == 200:
            log_event("✅ Данные успешно отправлены на сайт")
        else:
            log_event(f"⚠ Ошибка отправки данных: {response.status_code} - {response.text}")
    except Exception as e:
        log_event(f"❌ Ошибка соединения с API сайта: {e}")


def send_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Аккаунт', 'Запрещённые товары','Канал',)
    bot.send_message(message.chat.id, "Выберите нужный раздел:", reply_markup=markup)

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

@bot.message_handler(func=lambda message: message.text == 'Регистрация')
def registration(message):
    try:
        user = get_user(message.chat.id)
        if user:
            bot.send_message(message.chat.id, "Вы уже зарегистрированы!")
            send_main_menu(message)
            return

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Отмена')
        msg = bot.send_message(message.chat.id, "Введите ваше имя:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_name_step)
    except Exception as e:
        log_event(f"Ошибка в процессе регистрации: {e}")

def process_name_step(message):
    try:
        if message.text.lower() == 'отмена':
            bot.send_message(message.chat.id, "Регистрация отменена.", reply_markup=types.ReplyKeyboardRemove())
            return
        user_data[message.chat.id] = {'name': message.text}
        msg = bot.send_message(message.chat.id, "Введите ваш номер телефона (пример: +996559708005):")
        bot.register_next_step_handler(msg, process_phone_step)
    except Exception as e:
        log_event(f"Ошибка на этапе ввода имени: {e}")

def process_phone_step(message):
    try:
        if message.text.lower() == 'отмена':
            bot.send_message(message.chat.id, "Регистрация отменена.", reply_markup=types.ReplyKeyboardRemove())
            return
        
        phone = message.text.strip()
        if not re.match(r'^\+\d{10,15}$', phone):
            msg = bot.send_message(message.chat.id, "Неверный формат номера. Введите снова (пример: +996559708005):")
            bot.register_next_step_handler(msg, process_phone_step)
            return

        user_data[message.chat.id]['phone'] = phone
        complete_registration(message)
    except Exception as e:
        log_event(f"Ошибка на этапе ввода телефона: {e}")

def complete_registration(message):
    try:
        user_id = message.chat.id
        name = user_data[user_id]['name']
        phone = user_data[user_id]['phone']

        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        START_CODE = 3000
        user_code = f"A{START_CODE + user_count}"
        registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('INSERT INTO users (user_id, name, phone, code, registration_date) VALUES (?, ?, ?, ?, ?)',
                       (user_id, name, phone, user_code, registration_date))
        conn.commit()

        user_data[user_id]['code'] = user_code
        user_data[user_id]['registration_date'] = registration_date

        send_admin_notification(user_data[user_id])

        # Отправка пользователю всех регистрационных данных
        bot.send_message(message.chat.id, f"✅ *Регистрация завершена!*\n\n"
                                          f"📌 *Ваши данные:*\n"
                                          f"🔹 *Имя:* {name}\n"
                                          f"📞 *Телефон:* {phone}\n"
                                          f"🆔 *Уникальный код:* {user_code}\n"
                                          f"📅 *Дата регистрации:* {registration_date}",
                         parse_mode="Markdown")

        address_message = (
            "📦 *Адрес склада в Китае:*\n"
            "广东省佛山市南海区里水镇环镇南路33号1号仓315库B6961\n"
            "收货人 梅先生-B6961\n"
            "13250150777"
        )
        bot.send_message(message.chat.id, address_message, parse_mode="Markdown")

        video_paths = ['instruction.mp4', 'instructions.mp4']
        for path in video_paths:
            try:
                with open(path, 'rb') as video:
                    bot.send_video(message.chat.id, video)
            except FileNotFoundError:
                bot.send_message(message.chat.id, f"⚠ Видео {path} временно недоступно.")

        bot.send_message(message.chat.id, "🎉 Теперь вы можете пользоваться нашим сервисом!")
        send_main_menu(message)
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, "❌ Произошла ошибка при сохранении данных. Попробуйте позже.")
        log_event(f"Ошибка при регистрации пользователя: {e}")
    except Exception as e:
        log_event(f"Неизвестная ошибка при регистрации пользователя: {e}")

@bot.message_handler(func=lambda message: message.text == 'Аккаунт')
def account_info(message):
    try:
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
    except Exception as e:
        log_event(f"Ошибка при получении информации об аккаунте: {e}")

# Обработка кнопки "Канал"
@bot.message_handler(func=lambda message: message.text == 'Канал')
def send_channel_links(message):
    try:
        bot.send_message(
            message.chat.id,
            "Ссылки на наши каналы:\n"
            "1. [Telegram канал](https://t.me/+N1Xktz9wb55jZjRi)\n"
            "2. [Отзывы](https://web.telegram.org/k/#-2069386995)\n\n"
            "Для связи: [Личка](https://t.me/Seocargo)",
            "Для связи: [Личка](https://wa.me/message/ADWEXABNRF74I1)",
            parse_mode="Markdown"
        )
    except Exception as e:
        log_event(f"Ошибка при отправке ссылок на каналы: {e}")


# Обработка кнопки "Запрещённые товары"
@bot.message_handler(func=lambda message: message.text == 'Запрещённые товары')
def send_prohibited_items(message):
    try:
        image_paths = [f"{i}.png" for i in range(1, 11)]
        for path in image_paths:
            try:
                with open(path, 'rb') as image:
                    bot.send_photo(message.chat.id, image)
            except FileNotFoundError:
                bot.send_message(message.chat.id, f"Картинка {path} временно недоступна.")
    except Exception as e:
        log_event(f"Ошибка при отправке запрещённых товаров: {e}")


if __name__ == '__main__':
    try:
        bot.infinity_polling()
    except Exception as e:
        log_event(f"Критическая ошибка бота: {e}")
