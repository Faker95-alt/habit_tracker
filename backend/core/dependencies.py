from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.db.session import get_database_session
from backend.core.security import decode_access_token
from backend.crud.user import get_user_by_telegram_id
from backend.db.models import UserModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def get_current_authenticated_user(
        token: str = Depends(oauth2_scheme),
        database_session: Session = Depends(get_database_session)
) -> UserModel:
    """
    Зависимость для проверки авторизации. Извлекает пользователя из БД по токену.
    Если токен невалидный — сразу выбрасывает HTTP 401 Unauthorized.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось валидировать учетные данные. Токен недействителен или просрочен.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    telegram_id: int = payload.get("sub")
    if telegram_id is None:
        raise credentials_exception

    user = get_user_by_telegram_id(database_session, telegram_id=int(telegram_id))
    if user is None:
        raise credentials_exception

    return user
