import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Получаем URL базы данных из переменных окружения (настройки для Docker)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/habit_db"
)

# Создаем движок подключения
engine = create_engine(DATABASE_URL, echo=True)

# Создаем фабрику сессий для работы с запросами
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция-инъецирование для FastAPI, которая будет открывать и закрывать сессию
def get_database_session():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()