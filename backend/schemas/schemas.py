from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==========================================
# СХЕМЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ (User)
# ==========================================

class UserCreateSchema(BaseModel):
    """Схема для регистрации нового пользователя через Telegram ID."""
    telegram_id: int = Field(..., description="Уникальный идентификатор пользователя в Telegram")
    password: str = Field(..., min_length=6, description="Пароль для последующего доступа к API")


class UserResponseSchema(BaseModel):
    """Схема для возврата информации о пользователе (без хеша пароля)."""
    id: int
    telegram_id: int
    created_at: datetime

    class Config:
        # Включаем режим поддержки ORM (SQLAlchemy моделей)
        from_attributes = True


# ==========================================
# СХЕМЫ ДЛЯ ЛОГОВ ВЫПОЛНЕНИЯ (HabitLog)
# ==========================================

class HabitLogCreateSchema(BaseModel):
    """Схема для фиксации выполнения привычки (выполнил / не выполнил)."""
    is_completed: bool = Field(..., description="Статус выполнения привычки на указанную дату")


class HabitLogResponseSchema(BaseModel):
    """Схема для отображения логов выполнения."""
    id: int
    habit_id: int
    log_date: datetime
    is_completed: bool

    class Config:
        from_attributes = True


# ==========================================
# СХЕМЫ ДЛЯ ПРИВЫЧЕК (Habit)
# ==========================================

class HabitCreateSchema(BaseModel):
    """Схема для создания новой ежедневной привычки."""
    title: str = Field(..., min_length=1, max_length=100, description="Название привычки")
    description: Optional[str] = Field(None, description="Подробное описание привычки")


class HabitUpdateSchema(BaseModel):
    """Схема для полного или частичного редактирования привычки."""
    title: Optional[str] = Field(None, min_length=1, max_length=100, description="Новое название привычки")
    description: Optional[str] = Field(None, description="Новое описание привычки")
    is_active: Optional[bool] = Field(None, description="Статус активности привычки")


class HabitResponseSchema(BaseModel):
    """Схема для отправки данных о привычке обратно в Telegram-бот."""
    id: int
    user_id: int
    title: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    # Сюда автоматически подтянется список логов, если мы запросим его из БД
    logs: List[HabitLogResponseSchema] = []

    class Config:
        from_attributes = True


# ==========================================
# СХЕМЫ ДЛЯ АУТЕНТИФИКАЦИИ (Токены)
# ==========================================

class TokenSchema(BaseModel):
    """Схема токена доступа, который выдается боту."""
    access_token: str
    token_type: str