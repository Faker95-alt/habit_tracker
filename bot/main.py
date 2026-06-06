import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.services import (
    register_user_in_backend, authorize_user_and_get_token,
    get_user_habits_for_today, create_new_habit,
    send_habit_execution_log, delete_selected_habit
)

# Инициализация бота
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8949113905:AAFiQZNRZp4YxFe-b4ATqCIkr_98iTIK204")
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Генерирует красивое главное меню в виде Inline-кнопок."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    button_list_habits = InlineKeyboardButton("📋 Мои привычки на сегодня", callback_data="menu_list")
    button_add_habit = InlineKeyboardButton("➕ Добавить новую привычку", callback_data="menu_add")

    keyboard.add(button_list_habits, button_add_habit)
    return keyboard


@bot.message_handler(commands=['start', 'menu'])
def handle_start_or_menu_command(message):
    """Отрисовывает главное интерактивное меню пользователя."""
    telegram_id = message.from_user.id

    # Запускаем фоновую регистрацию/авторизацию
    register_user_in_backend(telegram_id)
    access_token = authorize_user_and_get_token(telegram_id)

    if not access_token:
        bot.send_message(message.chat.id, "❌ Ошибка авторизации на сервере. Попробуйте позже: /start")
        return

    welcome_text = (
        "✨ *Добро пожаловать в Habit Tracker!*\n\n"
        "Я помогу тебе закрепить полезные действия. Каждая привычка переносится "
        "изо дня в день автоматически, пока ты не выполнишь её *21 раз*.\n\n"
        "Управляй трекером прямо через интерактивное меню ниже 👇"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")


def show_today_habits(chat_id: int, telegram_id: int):
    """Вспомогательная функция для красивого вывода привычек."""
    habits = get_user_habits_for_today(telegram_id)

    if not habits:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("⬅️ В главное меню", callback_data="menu_back"))
        bot.send_message(chat_id, "🎉 На сегодня у тебя нет активных привычек! Время добавить что-то новое.",
                         reply_markup=keyboard)
        return

    bot.send_message(chat_id, "📊 *Твои цели на сегодня:*", parse_mode="Markdown")

    for habit in habits:
        # Считаем количество успешных выполнений
        completed_count = sum(1 for log in habit.get('logs', []) if log.get('is_completed'))

        # Проверяем, отмечал ли пользователь привычку конкретно сегодня
        # (берём самый свежий лог)
        logs = habit.get('logs', [])
        today_status = "⏳ Еще не отмечена"
        if logs:
            # Сортируем логи по дате, чтобы взять последний
            latest_log = sorted(logs, key=lambda x: x['log_date'])[-1]
            # Проверяем, совпадает ли дата (упрощенно для MVP по наличию лога)
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

        # Интерактивные кнопки управления карточкой
        keyboard = InlineKeyboardMarkup()
        button_complete = InlineKeyboardButton("✅ Выполнил", callback_data=f"complete_{habit['id']}")
        button_fail = InlineKeyboardButton("❌ Пропустил", callback_data=f"fail_{habit['id']}")
        button_delete = InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{habit['id']}")

        keyboard.row(button_complete, button_fail)
        keyboard.row(button_delete)

        bot.send_message(chat_id, card_text, reply_markup=keyboard, parse_mode="Markdown")

    # Добавляем кнопку возврата в самом конце списка карточек
    back_keyboard = InlineKeyboardMarkup()
    back_keyboard.add(InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="menu_back"))
    bot.send_message(chat_id, "📍 Управление списком:", reply_markup=back_keyboard)


@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    """Единый диспетчер обработки всех нажатий Inline-кнопок."""
    telegram_id = call.from_user.id
    chat_id = call.message.chat.id

    # 1. Навигация по главному меню
    if call.data == "menu_list":
        bot.answer_callback_query(call.id)
        bot.delete_message(chat_id, call.message.message_id)
        show_today_habits(chat_id, telegram_id)

    elif call.data == "menu_add":
        bot.answer_callback_query(call.id)
        bot.delete_message(chat_id, call.message.message_id)
        sent_message = bot.send_message(chat_id, "✍️ Введи *название* новой привычки (например: 'Зарядка'):",
                                        parse_mode="Markdown")
        bot.register_next_step_handler(sent_message, process_title_step)

    elif call.data == "menu_back":
        bot.answer_callback_query(call.id)
        bot.delete_message(chat_id, call.message.message_id)
        bot.send_message(chat_id, "📋 Главное меню:", reply_markup=get_main_menu_keyboard())

    # 2. Управление карточками привычек
    else:
        action, habit_id_string = call.data.split("_")
        habit_id = int(habit_id_string)

        if action == "complete":
            if send_habit_execution_log(telegram_id, habit_id, is_completed=True):
                bot.answer_callback_query(call.id, "Засчитано! Отличный день! 💪")
                # Обновляем сообщение, убирая кнопки, чтобы избежать повторных нажатий
                bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

        elif action == "fail":
            if send_habit_execution_log(telegram_id, habit_id, is_completed=False):
                bot.answer_callback_query(call.id, "Статус обновлен. Завтра получится лучше! ⏳")
                bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

        elif action == "delete":
            if delete_selected_habit(telegram_id, habit_id):
                bot.answer_callback_query(call.id, "Привычка полностью удалена.")
                bot.delete_message(chat_id, call.message.message_id)


# Шаги создания новой привычки через Next Step Handler
def process_title_step(message):
    habit_title = message.text.strip()
    if not habit_title:
        bot.send_message(message.chat.id, "⚠️ Название не может быть пустым. Возврат в меню.",
                         reply_markup=get_main_menu_keyboard())
        return

    sent_message = bot.send_message(message.chat.id, f"📝 Теперь введи краткое *описание* для «{habit_title}»:",
                                    parse_mode="Markdown")
    bot.register_next_step_handler(sent_message, process_description_step, habit_title)


def process_description_step(message, habit_title):
    habit_description = message.text.strip()
    telegram_id = message.from_user.id

    created = create_new_habit(telegram_id, title=habit_title, description=habit_description)
    if created:
        bot.send_message(
            message.chat.id,
            f"🎉 Привычка *{habit_title}* успешно создана!",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "❌ Не удалось сохранить изменения на бэкенде.",
                         reply_markup=get_main_menu_keyboard())


if __name__ == "__main__":
    print("Telegram-бот с красивым Inline-меню успешно запущен...")
    bot.infinity_polling()