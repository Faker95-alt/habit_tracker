from sqlalchemy.orm import Session
from backend.db.models import UserModel
from backend.schemas.schemas import UserCreateSchema
from passlib.context import CryptContext

# Настройка контекста для безопасного хеширования паролей (алгоритм bcrypt)
password_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


def calculate_password_hash(password: str) -> str:
    """Хеширует пароль пользователя для безопасного хранения в базе данных."""
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет соответствие введенного пароля сохраненному хешу."""
    return password_context.verify(plain_password, hashed_password)


def get_user_by_telegram_id(database_session: Session, telegram_id: int) -> UserModel:
    """Находит пользователя в базе данных по его уникальному Telegram ID."""
    return database_session.query(UserModel).filter(UserModel.telegram_id == telegram_id).first()


def create_new_user(database_session: Session, user_data: UserCreateSchema) -> UserModel:
    """Создает нового пользователя с хешированным паролем."""
    hashed_password = calculate_password_hash(user_data.password)
    new_user = UserModel(
        telegram_id=user_data.telegram_id,
        hashed_password=hashed_password
    )
    database_session.add(new_user)
    database_session.commit()
    database_session.refresh(new_user)
    return new_user