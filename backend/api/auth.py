from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.db.session import get_database_session
from backend.schemas.schemas import UserCreateSchema, UserResponseSchema, TokenSchema
from backend.crud.user import get_user_by_telegram_id, create_new_user, verify_password
from backend.core.security import create_access_token

auth_router = APIRouter(prefix="/auth", tags=["Аутентификация"])


@auth_router.post("/register", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
def register_telegram_user(user_data: UserCreateSchema, database_session: Session = Depends(get_database_session)):
    """Регистрирует нового пользователя Telegram в системе бэкенда."""
    existing_user = get_user_by_telegram_id(database_session, telegram_id=user_data.telegram_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким Telegram ID уже зарегистрирован в системе."
        )
    return create_new_user(database_session, user_data=user_data)


@auth_router.post("/login", response_model=TokenSchema)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    database_session: Session = Depends(get_database_session)
):
    """
    Принимает Telegram ID (в поле username) и пароль.
    Возвращает JWT-токен для последующего доступа к CRUD-методам привычек.
    """
    # Поле username из стандартной формы OAuth2 используется под наш Telegram ID
    try:
        telegram_id = int(form_data.username)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя пользователя (username) должно быть валидным числовым Telegram ID."
        )

    user = get_user_by_telegram_id(database_session, telegram_id=telegram_id)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный Telegram ID или пароль.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Зашиваем Telegram ID в поле 'sub' токена
    access_token = create_access_token(data={"sub": str(user.telegram_id)})
    return {"access_token": access_token, "token_type": "bearer"}