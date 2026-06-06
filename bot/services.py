import os
import requests
from typing import Optional, List

# URL бэкенда внутри сети Docker или локально
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api")

# Локальное "in-memory" хранилище JWT-токенов пользователей для MVP.
# Ключ — telegram_id, значение — строковый access_token.
USER_TOKENS_STORAGE = {}


def register_user_in_backend(telegram_id: int) -> bool:
    """Регистрирует пользователя на бэкенде. Паролем по умолчанию делаем инвертированный ID."""
    url = f"{BACKEND_URL}/auth/register"
    payload = {
        "telegram_id": telegram_id,
        "password": f"password_{telegram_id}"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 201
    except requests.RequestException:
        return False


def authorize_user_and_get_token(telegram_id: int) -> Optional[str]:
    """Авторизует бота на бэкенде и сохраняет полученный JWT-токен."""
    url = f"{BACKEND_URL}/auth/login"
    # Стандартная форма OAuth2 ожидает данные в формате x-www-form-urlencoded
    form_data = {
        "username": str(telegram_id),
        "password": f"password_{telegram_id}"
    }
    try:
        response = requests.post(url, data=form_data, timeout=5)
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            USER_TOKENS_STORAGE[telegram_id] = access_token
            return access_token
        return None
    except requests.RequestException:
        return None


def get_headers_with_authorization(telegram_id: int) -> dict:
    """Формирует заголовки запроса с JWT-токеном авторизации."""
    token = USER_TOKENS_STORAGE.get(telegram_id)
    if not token:
        # Если токена нет в памяти, пытаемся авторизоваться заново
        token = authorize_user_and_get_token(telegram_id)
    return {"Authorization": f"Bearer {token}"} if token else {}


def get_user_habits_for_today(telegram_id: int) -> List[dict]:
    """Запрашивает список активных привычек пользователя на сегодня."""
    url = f"{BACKEND_URL}/habits/today"
    headers = get_headers_with_authorization(telegram_id)
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException:
        return []


def create_new_habit(telegram_id: int, title: str, description: Optional[str] = None) -> Optional[dict]:
    """Отправляет запрос на создание новой привычки."""
    url = f"{BACKEND_URL}/habits/"
    headers = get_headers_with_authorization(telegram_id)
    payload = {"title": title, "description": description}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        if response.status_code == 201:
            return response.json()
        return None
    except requests.RequestException:
        return None


def send_habit_execution_log(telegram_id: int, habit_id: int, is_completed: bool) -> bool:
    """Фиксирует выполнение или невыполнение конкретной привычки."""
    url = f"{BACKEND_URL}/habits/{habit_id}/log"
    headers = get_headers_with_authorization(telegram_id)
    payload = {"is_completed": is_completed}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def delete_selected_habit(telegram_id: int, habit_id: int) -> bool:
    """Удаляет привычку через API бэкенда."""
    url = f"{BACKEND_URL}/habits/{habit_id}"
    headers = get_headers_with_authorization(telegram_id)
    try:
        response = requests.delete(url, headers=headers, timeout=5)
        return response.status_code == 204
    except requests.RequestException:
        return False