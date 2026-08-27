from datetime import datetime, timedelta
from typing import Optional, Any
from sqlalchemy.orm import Session
from database import User, Task


# авторизация -------------------------------------------------------

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, username: str, email: str, password_hash: str) -> User:
    user = User(username=username, email=email, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# задачи в матрице -----------------------------------------------------

def create_task(db: Session, user_id: int, title: str, quadrant: str) -> Task:
    task = Task(
        user_id=user_id,
        title=title,
        quadrant=quadrant,
        is_scheduled=False
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_matrix_tasks(db: Session, user_id: int) -> list[type[Task]]:
    return db.query(Task).filter(Task.user_id == user_id, Task.is_scheduled == False).all()


# планирование и конфликты -----------------------------------------------

def get_weekly_tasks(db: Session, user_id: int, start_week: datetime, end_week: datetime) -> list[type[Task]]:
    return db.query(Task).filter(
        Task.user_id == user_id,
        Task.is_scheduled.is_(True),
        Task.start_time >= start_week,
        Task.start_time <= end_week
    ).all()


def check_time_conflicts(db: Session, user_id: int, new_start: datetime, duration_min: int) -> list[type[Task]]:
    new_end = new_start + timedelta(minutes=duration_min)
    return db.query(Task).filter(
        Task.user_id == user_id,
        Task.is_scheduled.is_(True),
        Task.start_time < new_end,
        Task.end_time > new_start
    ).all()


def schedule_task_with_trim(db: Session, task_id: int, new_start: datetime, duration_min: int) -> type[Task] | None:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return None

    new_end = new_start + timedelta(minutes=duration_min)
    conflicts = check_time_conflicts(db, task.user_id, new_start, duration_min)

    for old_task in conflicts:
        if old_task.id == task_id:
            continue

        if old_task.start_time < new_start:
            # обрезка старой задачи до начала новой
            old_task.end_time = new_start
            old_task.duration_min = int((new_start - old_task.start_time).total_seconds() // 60)
        else:
            # если старая задача полностью накладывается — возвращаем её в матрицу
            old_task.is_scheduled = False
            old_task.start_time = None
            old_task.end_time = None
            old_task.duration_min = None

    # привязка нового времени
    task.start_time = new_start
    task.end_time = new_end
    task.duration_min = duration_min
    task.is_scheduled = True

    db.commit()
    db.refresh(task)
    return task