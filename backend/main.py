import uvicorn
from fastapi import FastAPI
from backend.api.auth import auth_router
from backend.api.habits import habits_router

app = FastAPI(
    title="Habit Tracker API",
    description="Бэкенд-сервис для управления привычками через Telegram-бота на архитектуре MVP",
    version="1.0.0"
)
app.include_router(auth_router, prefix="/api")
app.include_router(habits_router, prefix="/api")


@app.get("/", tags=["Корневой эндпоинт"])
def read_root_status():
    """Возвращает статус работоспособности сервиса."""
    return {"status": "running", "service": "habit_tracker_backend"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
