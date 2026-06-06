import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt

# Ключ для шифрования токенов (в продакшене должен браться из переменных окружения)
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY_FOR_HABIT_TRACKER_DEVELOMPENT_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # Токен будет жить 7 дней, чтобы боту не пришлось часто переавторизовываться


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Генерирует безопасный JWT-токен доступа для Telegram-бота.
    В полезную нагрузку (payload) зашивается идентификатор пользователя.
    """
    data_to_encode = data.copy()

    if expires_delta:
        expire_time = datetime.utcnow() + expires_delta
    else:
        expire_time = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Добавляем время истечения токена в payload
    data_to_encode.update({"exp": expire_time})

    # Кодируем JWT-токен
    jwt_token = jwt.encode(data_to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return jwt_token


def decode_access_token(token: str) -> Optional[dict]:
    """
    Декодирует JWT-токен и проверяет его валидность.
    Возвращает словарь с данными, если токен корректен, или None, если он просрочен/изменен.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None