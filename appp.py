import telebot
from telebot import types
import sqlite3
import re
from datetime import datetime

API_TOKEN = '7216690383:AAGPtNiQ_F2Bsa1rdC_sVT8lhic7ghjS6Fo'
ADMIN_BOT_API_TOKEN = '8191961162:AAGo_BkBhLTY7VbgMJ5DTeih5wBBq_l71mE'
ADMIN_BOT_CHAT_ID = '5338389700'

# Создание объектов бота
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
        admin_bot.send_message(ADMIN_BOT_CHAT_ID, admin_message)
    except Exception as e:
        log_event(f"Ошибка отправки уведомления администратору: {e}")

# Стартовое сообщение
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        user = get_user(message.chat.id)
        if not user:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add('Регистрация')
            bot.send_message(message.chat.id, "Добро пожаловать! Пожалуйста, зарегистрируйтесь, чтобы продолжить.", reply_markup=markup)
        else:
            send_main_menu(message)
    except Exception as e:
        log_event(f"Ошибка при отправке стартового сообщения: {e}")

# Главное меню
def send_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Отслеживание товаров', 'Аккаунт')
    markup.add('Адрес в Кыргызстане', 'Канал', 'Запрещённые товары')
    bot.send_message(message.chat.id, "Выберите нужный раздел:", reply_markup=markup)

# Проверка пользователя
def get_user(user_id):
    try:
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
    except sqlite3.Error as e:
        log_event(f"Ошибка при получении пользователя из базы данных: {e}")
    return None

# Регистрация
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
        msg = bot.send_message(message.chat.id, "Введите ваш номер телефона (только цифры):")
        bot.register_next_step_handler(msg, process_phone_step)
    except Exception as e:
        log_event(f"Ошибка на этапе ввода имени: {e}")

def process_phone_step(message):
    try:
        if message.text.lower() == 'отмена':
            bot.send_message(message.chat.id, "Регистрация отменена.", reply_markup=types.ReplyKeyboardRemove())
            return
        if not re.match(r'^\d{10,15}$', message.text):
            msg = bot.send_message(message.chat.id, "Неверный формат телефона. Попробуйте снова.")
            bot.register_next_step_handler(msg, process_phone_step)
            return

        user_data[message.chat.id]['phone'] = message.text
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
        START_CODE = 1533
        user_code = f"A{START_CODE + user_count}"
        registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('INSERT INTO users (user_id, name, phone, code, registration_date) VALUES (?, ?, ?, ?, ?)',
                       (user_id, name, phone, user_code, registration_date))
        conn.commit()

        user_data[user_id]['code'] = user_code
        user_data[user_id]['registration_date'] = registration_date

        send_admin_notification(user_data[user_id])
        bot.send_message(message.chat.id, f"Ваш уникальный код: {user_code}")

        address_message = (
            "Адрес склада в Китае:\n"
            "广东省佛山市南海区里水镇环镇南路33号1号仓315库B6961\n"
            "收货人 梅先生-B6961\n"
            "13250150777\n"
        )
        bot.send_message(message.chat.id, address_message)

        video_paths = ['instruction.mp4', 'instructions.mp4']
        for path in video_paths:
            try:
                with open(path, 'rb') as video:
                    bot.send_video(message.chat.id, video)
            except FileNotFoundError:
                bot.send_message(message.chat.id, f"Видео {path} временно недоступно.")

        bot.send_message(message.chat.id, "Регистрация завершена!")
        send_main_menu(message)
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, "Произошла ошибка при сохранении данных. Попробуйте позже.")
        log_event(f"Ошибка при регистрации пользователя: {e}")
    except Exception as e:
        log_event(f"Неизвестная ошибка при регистрации пользователя: {e}")

# Функциональность отслеживания товаров
@bot.message_handler(func=lambda message: message.text == 'Отслеживание товаров')
def track_product(message):
    try:
        msg = bot.send_message(message.chat.id, "Введите уникальный код товара для отслеживания:")
        bot.register_next_step_handler(msg, process_tracking)
    except Exception as e:
        log_event(f"Ошибка при запросе кода товара: {e}")

def process_tracking(message):
    try:
        product_code = message.text.strip()
        cursor.execute('SELECT status FROM products WHERE product_code = ?', (product_code,))
        product = cursor.fetchone()
        if product:
            bot.send_message(message.chat.id, f"Статус вашего товара: {product[0]}")
        else:
            bot.send_message(message.chat.id, "Товар с таким кодом не найден. Пожалуйста, проверьте код и попробуйте снова.")
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, "Произошла ошибка при обработке запроса. Попробуйте позже.")
        log_event(f"Ошибка при отслеживании товара: {e}")
    except Exception as e:
        log_event(f"Неизвестная ошибка при отслеживании товара: {e}")

# Обработка кнопки "Аккаунт"
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
            parse_mode="Markdown"
        )
    except Exception as e:
        log_event(f"Ошибка при отправке ссылок на каналы: {e}")

@bot.message_handler(func=lambda message: message.text == 'Адрес в Кыргызстане')
def send_address_kg(message):
    try:
        bot.send_message(message.chat.id, "Адрес: г. Ош, пр. Масалиева 44")

        google_maps_url = "https://maps.app.goo.gl/TDL61Viw1Rjjd9197"
        bot.send_message(
            message.chat.id,
            f"Посмотреть карту: [Google Maps]({google_maps_url})",
            parse_mode="Markdown"
        )

        video_path = 'mds.mp4'
        try:
            with open(video_path, 'rb') as video:
                bot.send_video(message.chat.id, video)
        except FileNotFoundError:
            bot.send_message(message.chat.id, f"Видео {video_path} временно недоступно.")
    except Exception as e:
        log_event(f"Ошибка при отправке адреса в Кыргызстане: {e}")

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

@bot.message_handler(commands=['send'])
def send_message_from_admin(message):
    try:
        parts = message.text.split(' ', 2)

        if len(parts) < 3:
            bot.send_message(message.chat.id, "❌ Неверный формат команды.\nИспользуйте:\n/send <user_code> <сообщение>")
            log_event(f"Неверный формат команды от администратора {message.chat.id}: {message.text}")
            return

        user_code = parts[1].strip()
        admin_message = parts[2].strip()

        try:
            cursor.execute('SELECT user_id FROM users WHERE code = ?', (user_code,))
            user = cursor.fetchone()

            if not user:
                bot.send_message(message.chat.id, f"❌ Пользователь с кодом {user_code} не найден.")
                log_event(f"Пользователь с кодом {user_code} не найден. Сообщение от администратора не отправлено.")
                return

            user_id = user[0]

            try:
                bot.send_message(user_id, f"📩 Сообщение от администратора:\n\n{admin_message}")
                bot.send_message(message.chat.id, f"✅ Сообщение успешно отправлено пользователю с кодом {user_code}.")
                log_event(f"Сообщение отправлено пользователю {user_id} с кодом {user_code}: {admin_message}")
            except telebot.apihelper.ApiTelegramException as e:
                bot.send_message(
                    message.chat.id,
                    f"❌ Ошибка: не удалось отправить сообщение пользователю с кодом {user_code}. Пользователь мог заблокировать бота или недоступен."
                )
                log_event(f"Ошибка Telegram API при отправке пользователю {user_id} с кодом {user_code}: {e}")
            except Exception as e:
                bot.send_message(
                    message.chat.id,
                    f"❌ Произошла неизвестная ошибка при отправке сообщения пользователю с кодом {user_code}."
                )
                log_event(f"Неизвестная ошибка при отправке пользователю {user_id} с кодом {user_code}: {e}")

        except sqlite3.Error as e:
            bot.send_message(message.chat.id, "❌ Произошла ошибка при обработке команды. Попробуйте позже.")
            log_event(f"Ошибка базы данных при обработке команды /send: {e}")

    except Exception as e:
        bot.send_message(message.chat.id, "❌ Произошла ошибка при обработке команды.")
        log_event(f"Ошибка при обработке команды /send от администратора {message.chat.id}: {e}")

if __name__ == '__main__':
    try:
        bot.infinity_polling()
    except Exception as e:
        log_event(f"Критическая ошибка бота: {e}")
