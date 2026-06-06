from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.db.session import get_database_session
from backend.core.dependencies import get_current_authenticated_user
from backend.db.models import UserModel
from backend.schemas.schemas import (
    HabitCreateSchema, HabitUpdateSchema, HabitResponseSchema, HabitLogResponseSchema, HabitLogCreateSchema
)
from backend.crud.habit import (
    create_user_habit, get_active_habits_for_today, update_user_habit, delete_user_habit, log_habit_execution
)

habits_router = APIRouter(prefix="/habits", tags=["Управление привычками"])


@habits_router.post("/", response_model=HabitResponseSchema, status_code=status.HTTP_201_CREATED)
def create_habit(
        habit_data: HabitCreateSchema,
        database_session: Session = Depends(get_database_session),
        current_user: UserModel = Depends(get_current_authenticated_user)
):
    """Создает новую ежедневную привычку для авторизованного пользователя."""
    return create_user_habit(database_session, habit_data=habit_data, user_id=current_user.id)


@habits_router.get("/today", response_model=List[HabitResponseSchema])
def get_today_habits(
        database_session: Session = Depends(get_database_session),
        current_user: UserModel = Depends(get_current_authenticated_user)
):
    """
    Возвращает список привычек на сегодня.
    Автоматически переносит невыполненные и скрывает те, что закреплены (выполнены 21 раз).
    """
    return get_active_habits_for_today(database_session, user_id=current_user.id)


@habits_router.put("/{habit_id}", response_model=HabitResponseSchema)
def update_habit(
        habit_id: int,
        habit_data: HabitUpdateSchema,
        database_session: Session = Depends(get_database_session),
        current_user: UserModel = Depends(get_current_authenticated_user)
):
    """Редактирует параметры привычки (название, описание или статус активности)."""
    updated_habit = update_user_habit(database_session, habit_id=habit_id, habit_data=habit_data)
    if not updated_habit or updated_habit.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Привычка не найдена или у вас нет прав на её изменение."
        )
    return updated_habit


@habits_router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_habit(
        habit_id: int,
        database_session: Session = Depends(get_database_session),
        current_user: UserModel = Depends(get_current_authenticated_user)
):
    """Полностью удаляет привычку."""
    # Сначала проверяем принадлежность привычки пользователю
    from backend.db.models import HabitModel
    habit = database_session.query(HabitModel).filter(HabitModel.id == habit_id).first()
    if not habit or habit.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Привычка не найдена или у вас нет прав на её удаление."
        )

    delete_user_habit(database_session, habit_id=habit_id)
    return


@habits_router.post("/{habit_id}/log", response_model=HabitLogResponseSchema)
def track_habit_execution(
        habit_id: int,
        log_data: HabitLogCreateSchema,
        database_session: Session = Depends(get_database_session),
        current_user: UserModel = Depends(get_current_authenticated_user)
):
    """Фиксирует выполнение привычки на сегодняшний день: выполнил (True) / не выполнил (False)."""
    from backend.db.models import HabitModel
    habit = database_session.query(HabitModel).filter(HabitModel.id == habit_id).first()
    if not habit or habit.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Привычка не найдена."
        )

    return log_habit_execution(database_session, habit_id=habit_id, is_completed=log_data.is_completed)