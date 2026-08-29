from sqlalchemy.orm import Session
from database import User, Task, ImportantDate, SharedEvent, Meme
from datetime import datetime, timedelta
from typing import Optional
import secrets


# Авторизация и профиль --------------------------------------------------------

def get_all_other_users(db: Session, current_user_id: int) -> list[User]:
    return db.query(User).filter(User.id != current_user_id).all()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, username: str, email: str, password_hash: str) -> User:
    user = User(username=username, email=email, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user_settings(db: Session, user_id: int, settings: dict):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.work_start = settings["work_start"]
        user.work_end = settings["work_end"]
        user.lunch_window_start = settings["lunch_window_start"]
        user.lunch_window_end = settings["lunch_window_end"]
        user.lunch_duration_minutes = settings["lunch_duration_minutes"]
        db.commit()

# Задачи (Матрица и Расписание) -----------------------------------------------

def create_task(db: Session, user_id: int, **kwargs) -> Task:
    task = Task(user_id=user_id, **kwargs)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def get_user_tasks(db: Session, user_id: int) -> list[Task]:
    return db.query(Task).filter(Task.user_id == user_id).all()

def get_matrix_tasks(db: Session, user_id: int) -> list[Task]:
    return db.query(Task).filter(Task.user_id == user_id, Task.is_scheduled == False).all()

def get_scheduled_tasks_by_date(db: Session, user_id: int, date_str: str) -> list[Task]:
    return db.query(Task).filter(
        Task.user_id == user_id,
        Task.is_scheduled == True,
        Task.date == date_str
    ).all()

def update_task(db: Session, task_id: int, **kwargs):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        for key, value in kwargs.items():
            setattr(task, key, value)
        db.commit()
        db.refresh(task)
    return task

def delete_task(db: Session, task_id: int):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()

# Важные даты ------------------------------------------------------------------

def toggle_important_date(db: Session, user_id: int, date_str: str):
    item = db.query(ImportantDate).filter_by(user_id=user_id, date=date_str).first()
    if item:
        db.delete(item)
    else:
        db.add(ImportantDate(user_id=user_id, date=date_str))
    db.commit()

def get_important_dates(db: Session, user_id: int) -> list[str]:
    return [d.date for d in db.query(ImportantDate).filter_by(user_id=user_id).all()]

# Совместные события ------------------------------------------------------------

def get_shared_events_for_user(db: Session, user_id: int) -> list[SharedEvent]:
    return db.query(SharedEvent).filter(
        (SharedEvent.proposed_by_id == user_id) | (SharedEvent.receiver_id == user_id)
    ).all()

def create_shared_event(db: Session, **kwargs) -> SharedEvent:
    event = SharedEvent(**kwargs)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

def accept_shared_event(db: Session, event_id: int):
    event = db.query(SharedEvent).filter_by(id=event_id).first()
    if event:
        event.status = "accepted"
        # Добавляем задачу и отправителю, и получателю
        for u_id in [event.proposed_by_id, event.receiver_id]:
            # Проверка от повторного добавления
            exists = db.query(Task).filter_by(user_id=u_id, shared_event_id=event.id).first()
            if not exists:
                crud_create_task_obj = Task(
                    user_id=u_id,
                    title=f"🤝 {event.title}",
                    type="fixed",
                    date=event.date,
                    start_date=event.date,
                    end_date=event.date,
                    start_time=event.start_time,
                    end_time=event.end_time,
                    duration_minutes=event.duration_minutes,
                    is_scheduled=True,
                    status="scheduled",
                    shared_event_id=event.id
                )
                db.add(crud_create_task_obj)
        db.commit()

def update_shared_event_status(db: Session, event_id: int, status: str):
    event = db.query(SharedEvent).filter_by(id=event_id).first()
    if event:
        event.status = status
        db.commit()

def delete_shared_event(db: Session, event_id: int):
    db.query(Task).filter(Task.shared_event_id == event_id).delete()
    db.query(SharedEvent).filter_by(id=event_id).delete()
    db.commit()

# Мемы ------------------------------------------------------------------------

def create_meme(db: Session, sender_id: int, path: str, url: str, caption: str, date_str: str) -> Meme:
    meme = Meme(sender_id=sender_id, path=path, url=url, caption=caption, date=date_str)
    db.add(meme)
    db.commit()
    db.refresh(meme)
    return meme

def get_all_memes(db: Session) -> list[Meme]:
    return db.query(Meme).all()

def delete_meme(db: Session, meme_id: int):
    meme = db.query(Meme).filter_by(id=meme_id).first()
    if meme:
        db.delete(meme)
        db.commit()


# Управление сессиями ---------------------------------------------------------

def create_user_session(db: Session, user_id: int, days_valid: int = 14) -> str:
    token = secrets.token_hex(32)
    expiry = datetime.utcnow() + timedelta(days=days_valid)
    user = db.query(User).filter_by(id=user_id).first()
    if user:
        user.session_token = token
        user.token_expiry = expiry
        db.commit()
        return token
    return None

def get_user_by_session_token(db: Session, token: str) -> Optional[User]:
    if not token:
        return None
    user = db.query(User).filter_by(session_token=token).first()
    if user and user.token_expiry and user.token_expiry > datetime.utcnow():
        return user
    return None

def logout_user_session(db: Session, user_id: int):
    user = db.query(User).filter_by(id=user_id).first()
    if user:
        user.session_token = None
        user.token_expiry = None
        db.commit()