import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove
from bot.services import (
    register_user_in_backend, authorize_user_and_get_token,
    get_user_habits_for_today, create_new_habit,
    send_habit_execution_log, delete_selected_habit
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8949113905:AAFiQZNRZp4YxFe-b4ATqCIkr_98iTIK204")
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Генерирует красивое постоянное нижнее меню (Reply Keyboard)."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    button_list = KeyboardButton("📋 Мои привычки")
    button_add = KeyboardButton("➕ Добавить привычку")

    keyboard.add(button_list, button_add)
    return keyboard


@bot.message_handler(commands=['start', 'menu'])
def handle_start_or_menu_command(message):
    """Регистрирует пользователя и выводит постоянное нижнее меню."""
    telegram_id = message.from_user.id
    bot.send_message(message.chat.id, "⚡ Инициализация профиля...")
    register_user_in_backend(telegram_id)
    access_token = authorize_user_and_get_token(telegram_id)

    if not access_token:
        bot.send_message(message.chat.id, "❌ Ошибка авторизации на сервере. Попробуйте позже: /start")
        return

    welcome_text = (
        "✨ *Добро пожаловать в Habit Tracker!*\n\n"
        "Я помогу тебе закрепить полезные действия. Каждая привычка переносится "
        "изо дня в день автоматически, пока ты не выполнишь её *21 раз*.\n\n"
        "Используй меню внизу экрана для управления своими привычками 👇"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_reply_keyboard(), parse_mode="Markdown")


@bot.message_handler(func=lambda message: message.text in ["📋 Мои привычки", "➕ Добавить привычку"])
def handle_reply_menu_clicks(message):
    """Обрабатывает клики по текстовым кнопкам нижнего меню."""
    telegram_id = message.from_user.id

    if message.text == "📋 Мои привычки":
        show_today_habits(message.chat.id, telegram_id)

    elif message.text == "➕ Добавить привычку":
        sent_message = bot.send_message(
            message.chat.id,
            "✍️ Введи *название* новой привычки (например: 'Зарядка'):",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(sent_message, process_title_step)


def show_today_habits(chat_id: int, telegram_id: int):
    """Выводит список привычек на сегодня с Inline-кнопками под каждой карточкой."""
    habits = get_user_habits_for_today(telegram_id)

    if not habits:
        bot.send_message(
            chat_id,
            "🎉 На сегодня у тебя нет активных привычек! Нажми «➕ Добавить привычку» внизу, чтобы начать.",
            reply_markup=get_main_reply_keyboard()
        )
        return

    bot.send_message(chat_id, "📊 *Твои цели на сегодня:*", parse_mode="Markdown")

    for habit in habits:
        completed_count = sum(1 for log in habit.get('logs', []) if log.get('is_completed'))

        logs = habit.get('logs', [])
        today_status = "⏳ Еще не отмечена"
        if logs:
            latest_log = sorted(logs, key=lambda x: x['log_date'])[-1]
            if latest_log.get('is_completed'):
                today_status = "✅ Выполнена!"
            else:
                today_status = "❌ Пропущена"

        card_text = (
            f"🎯 *{habit['title']}*\n"
            f"📝 Описание: _{habit['description'] or 'Отсутствует'}_\n"
            f"📈 Прогресс: *{completed_count} из 21 дня*\n"
            f"⚡ Статус сегодня: {today_status}"
        )
        keyboard = InlineKeyboardMarkup()
        button_complete = InlineKeyboardButton("✅ Выполнил", callback_data=f"complete_{habit['id']}")
        button_fail = InlineKeyboardButton("❌ Пропустил", callback_data=f"fail_{habit['id']}")
        button_delete = InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{habit['id']}")

        keyboard.row(button_complete, button_fail)
        keyboard.row(button_delete)

        bot.send_message(chat_id, card_text, reply_markup=keyboard, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: True)
def handle_inline_callbacks(call):
    """Обрабатывает действия внутри карточек привычек (Выполнил/Пропустил/Удалить)."""
    telegram_id = call.from_user.id
    chat_id = call.message.chat.id

    action, habit_id_string = call.data.split("_")
    habit_id = int(habit_id_string)

    if action == "complete":
        if send_habit_execution_log(telegram_id, habit_id, is_completed=True):
            bot.answer_callback_query(call.id, "Засчитано! Отличный день! 💪")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

    elif action == "fail":
        if send_habit_execution_log(telegram_id, habit_id, is_completed=False):
            bot.answer_callback_query(call.id, "Статус обновлен. Завтра всё получится! ⏳")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

    elif action == "delete":
        if delete_selected_habit(telegram_id, habit_id):
            bot.answer_callback_query(call.id, "Привычка удалена.")
            bot.delete_message(chat_id, call.message.message_id)


def process_title_step(message):
    habit_title = message.text.strip() if message.text else ""
    if not habit_title:
        bot.send_message(message.chat.id, "⚠️ Название не может быть пустым.", reply_markup=get_main_reply_keyboard())
        return

    sent_message = bot.send_message(message.chat.id, f"📝 Теперь введи краткое *описание* для «{habit_title}»:",
                                    parse_mode="Markdown")
    bot.register_next_step_handler(sent_message, process_description_step, habit_title)


def process_description_step(message, habit_title):
    habit_description = message.text.strip() if message.text else ""
    telegram_id = message.from_user.id

    created = create_new_habit(telegram_id, title=habit_title, description=habit_description)
    if created:
        bot.send_message(
            message.chat.id,
            f"🎉 Привычка *{habit_title}* успешно создана!",
            reply_markup=get_main_reply_keyboard(),
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "❌ Не удалось сохранить изменения на бэкенде.",
                         reply_markup=get_main_reply_keyboard())


if __name__ == "__main__":
    print("Telegram-бот с постоянным нижним меню запущен...")
    bot.infinity_polling()
