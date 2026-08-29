from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    session_token = Column(String(255), nullable=True, index=True)
    token_expiry = Column(DateTime, nullable=True)

    # настройки рабочего дня
    work_start = Column(String(5), default="08:00")
    work_end = Column(String(5), default="18:00")
    lunch_window_start = Column(String(5), default="13:00")
    lunch_window_end = Column(String(5), default="16:00")
    lunch_duration_minutes = Column(Integer, default=60)

    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    important_dates = relationship("ImportantDate", back_populates="user", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(String(20), default="fixed")  # 'fixed' или 'floating'
    quadrant = Column(String(50), nullable=True)  # 'DO', 'PLAN', 'DELEGATE', 'ELIMINATE'
    is_scheduled = Column(Boolean, default=False)

    date = Column(String(10), nullable=True)  # YYYY-MM-DD
    start_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    end_date = Column(String(10), nullable=True)  # YYYY-MM-DD

    start_time = Column(String(5), nullable=True)  # HH:MM
    end_time = Column(String(5), nullable=True)  # HH:MM
    duration_minutes = Column(Integer, default=60)
    status = Column(String(20), default="pending")  # 'pending', 'scheduled', 'done'
    shared_event_id = Column(Integer, nullable=True)

    user = relationship("User", back_populates="tasks")


class ImportantDate(Base):
    __tablename__ = "important_dates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD

    user = relationship("User", back_populates="important_dates")


class SharedEvent(Base):
    __tablename__ = "shared_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    proposed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String(10), nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    status = Column(String(20), default="proposed")  # 'proposed', 'accepted', 'declined'


class Meme(Base):
    __tablename__ = "memes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    path = Column(String(500), nullable=True)
    url = Column(String(500), nullable=True)
    caption = Column(String(255), nullable=True)
    date = Column(String(10), nullable=False)


DATABASE_URL = "sqlite:///planner.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)