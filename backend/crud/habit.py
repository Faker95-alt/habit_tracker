from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.models import HabitModel, HabitLogModel
from backend.schemas.schemas import HabitCreateSchema, HabitUpdateSchema


def create_user_habit(database_session: Session, habit_data: HabitCreateSchema, user_id: int) -> HabitModel:
    """Создает новую привычку для конкретного пользователя."""
    new_habit = HabitModel(
        user_id=user_id,
        title=habit_data.title,
        description=habit_data.description
    )
    database_session.add(new_habit)
    database_session.commit()
    database_session.refresh(new_habit)
    return new_habit


def get_active_habits_for_today(database_session: Session, user_id: int, target_days_count: int = 21) -> List[
    HabitModel]:
    """
    Возвращает список активных привычек пользователя на текущий день.
    Реализует механизм переноса: привычка переносится, если она выполнена менее 21 раза.
    """
    # Подзапрос: считаем количество успешных выполнений для каждой привычки
    completed_logs_count_subquery = (
        database_session.query(
            HabitLogModel.habit_id,
            func.count(HabitLogModel.id).label("total_completed")
        )
        .filter(HabitLogModel.is_completed == True)
        .group_by(HabitLogModel.habit_id)
        .subquery()
    )

    # Основной запрос: выбираем активные привычки, у которых успешных логов меньше target_days_count (21)
    # Используем outerjoin, чтобы учесть привычки, у которых еще вообще нет логов (total_completed IS NULL)
    query = (
        database_session.query(HabitModel)
        .outerjoin(completed_logs_count_subquery, HabitModel.id == completed_logs_count_subquery.c.habit_id)
        .filter(
            HabitModel.user_id == user_id,
            HabitModel.is_active == True,
            func.coalesce(completed_logs_count_subquery.c.total_completed, 0) < target_days_count
        )
    )

    return query.all()


def update_user_habit(database_session: Session, habit_id: int, habit_data: HabitUpdateSchema) -> HabitModel:
    """Полностью или частично редактирует параметры привычки."""
    habit = database_session.query(HabitModel).filter(HabitModel.id == habit_id).first()
    if not habit:
        return None

    # Динамически обновляем только те поля, которые были переданы
    if habit_data.title is not None:
        habit.title = habit_data.title
    if habit_data.description is not None:
        habit.description = habit_data.description
    if habit_data.is_active is not None:
        habit.is_active = habit_data.is_active

    database_session.commit()
    database_session.refresh(habit)
    return habit


def delete_user_habit(database_session: Session, habit_id: int) -> bool:
    """Удаляет привычку из базы данных."""
    habit = database_session.query(HabitModel).filter(HabitModel.id == habit_id).first()
    if not habit:
        return False
    database_session.delete(habit)
    database_session.commit()
    return True


def log_habit_execution(database_session: Session, habit_id: int, is_completed: bool) -> HabitLogModel:
    """
    Фиксирует выполнение или невыполнение привычки на текущую дату.
    Если на сегодня отметка уже существует — обновляет её.
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)

    # Проверяем, была ли уже отметка на сегодня
    existing_log = (
        database_session.query(HabitLogModel)
        .filter(
            HabitLogModel.habit_id == habit_id,
            HabitLogModel.log_date >= today_start,
            HabitLogModel.log_date <= today_end
        )
        .first()
    )

    if existing_log:
        existing_log.is_completed = is_completed
        new_log = existing_log
    else:
        new_log = HabitLogModel(
            habit_id=habit_id,
            is_completed=is_completed,
            log_date=datetime.utcnow()
        )
        database_session.add(new_log)

    database_session.commit()
    database_session.refresh(new_log)
    return new_log