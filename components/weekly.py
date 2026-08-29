from datetime import datetime, timedelta, date
import streamlit as st
from streamlit_calendar import calendar
from sqlalchemy.orm import Session
import crud

def render_weekly_ui(db: Session, user_id: int):
    st.title("Weekly schedule")

    # границы текущей недели (понедельник - воскресенье)
    today = date.today()
    start_week = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    end_week = start_week + timedelta(days=7)

    # запланированные задачи из БД
    tasks = crud.get_weekly_tasks(db, user_id, start_week, end_week)

    calendar_events = [
        {
            "title": t.title,
            "start": t.start_time.isoformat(),
            "end": t.end_time.isoformat()
        }
        for t in tasks
    ]

    # конфигурация FullCalendar
    calendar_options = {
        "initialView": "timeGridWeek",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "timeGridWeek,timeGridDay",
        },
        "slotMinTime": "07:00:00",
        "slotMaxTime": "23:00:00",
        "allDaySlot": False,
    }

    # отрисовка календаря
    calendar(events=calendar_events, options=calendar_options, key="weekly_calendar")

    st.divider()

    # индикатор загруженности на день
    st.subheader("Today's workload")

    today_tasks = [t for t in tasks if t.start_time and t.start_time.date() == today]

    total_minutes = sum(t.duration_min for t in today_tasks)

    max_daily_minutes = 480  # 8 часов рабочего времени
    progress = min(total_minutes / max_daily_minutes, 1.0) if max_daily_minutes > 0 else 0.0

    col_bar, col_text = st.columns([3, 1])
    with col_bar:
        st.progress(progress)
    with col_text:
        st.caption(f"**{total_minutes}** / {max_daily_minutes} мин ({int(progress * 100)}%)")