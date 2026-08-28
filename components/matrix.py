from datetime import datetime, time, date
import streamlit as st
from sqlalchemy.orm import Session
import crud


# =========================================================================================================
# Модальное окно планирования задач -----------------------------------------------------------------------
# =========================================================================================================

@st.dialog("Plan the task")
def schedule_task_dialog(db: Session, task_id: int, task_title: str, user_id: int):
    st.write(f"Task: **{task_title}**")

    # Ввод параметров времени
    selected_date = st.date_input("Date", value=date.today())
    selected_time = st.time_input("Start time", value=time(9, 0))
    duration = st.number_input("Duration (min)", min_value=15, max_value=480, value=60, step=15)


    new_start = datetime.combine(selected_date, selected_time)

    # кнопка проверки и сохранения
    if st.button("Save in timetable", type="primary"):
        if new_start:
            # поиск конфликтов
            conflicts = crud.check_time_conflicts(db, user_id, new_start, duration)

            if conflicts:
                st.warning(f"⚠️ Conflicts were found ({len(conflicts)})")
                # названия конфликтующих задач
                for c in conflicts:
                    st.caption(f"• {c.title} ({c.start_time.strftime('%H:%M')} - {c.end_time.strftime('%H:%M')})")

                st.write("When saving, old tasks will be automatically trimmed in time.")
                if st.button("Trim and save"):
                    crud.schedule_task_with_trim(db, task_id, new_start, duration)
                    st.success("Task was successfully saved!")
                    st.rerun()
            else:
                # конфликтов нет — просто сохраняем
                crud.schedule_task_with_trim(db, task_id, new_start, duration)
                st.success("Task was planned!")
                st.rerun()


# ==========================================================================================================
# Основной интерфейс матрицы -------------------------------------------------------------------------------
# ==========================================================================================================

def render_matrix_ui(db: Session, user_id: int):
    st.title("Eisenhower Matrix")

    # форма быстрого создания задачи
    with st.form("new_task_form", clear_on_submit=True):
        col_title, col_quad = st.columns([2, 1])
        with col_title:
            title = st.text_input("New task's title", placeholder="Example: Cooking")
        with col_quad:
            quadrant = st.selectbox(
                "Quadrant",
                options=["DO", "PLAN", "DELEGATE", "ELIMINATE"],
                format_func=lambda x: {
                    "DO": "Do (Urgent and Important)",
                    "PLAN": "Plan (Important, Not Urgent)",
                    "DELEGATE": "Delegate (Urgent, Not Important)",
                    "ELIMINATE": "Routine (Not Important, Not Urgent)"
                }[x]
            )
        submit = st.form_submit_button("Add to matrix")
        if submit and title:
            crud.create_task(db, user_id, title, quadrant)
            st.rerun()

    # загружаем незапланированные задачи текущего пользователя
    all_tasks = crud.get_matrix_tasks(db, user_id)

    do_tasks = [
        t for t in all_tasks
        if t.quadrant == "DO"
    ]
    plan_tasks = [
        t for t in all_tasks
        if t.quadrant == "PLAN"
    ]
    delegate_tasks = [
        t for t in all_tasks
        if t.quadrant == "DELEGATE"
    ]
    eliminate_tasks = [
        t for t in all_tasks
        if t.quadrant == "ELIMINATE"
    ]

    # отрисовка 4 квадрантов сеткой 2x2
    col_left, col_right = st.columns(2)

    with col_left:
        # квадрант 1: DO
        with st.container(border=True):
            st.subheader("DO")
            _render_task_list(db, do_tasks, user_id)

        # квадрант 3: DELEGATE
        with st.container(border=True):
            st.subheader("DELEGATE")
            _render_task_list(db, delegate_tasks, user_id)

    with col_right:
        # квадрант 2: PLAN
        with st.container(border=True):
            st.subheader("PLAN")
            _render_task_list(db, plan_tasks, user_id)

        # квадрант 4: ELIMINATE
        with st.container(border=True):
            st.subheader("ELIMINATE")
            _render_task_list(db, eliminate_tasks, user_id)


def _render_task_list(db: Session, tasks: list, user_id: int):
    # вспомогательная функция отрисовки списка карточек внутри квадранта
    if not tasks:
        st.caption("No tasks")
        return

    for task in tasks:
        col_name, col_btn = st.columns([3, 1])
        with col_name:
            st.write(task.title)
        with col_btn:
            # При нажатии открываем диалоговое окно
            if st.button("📅", key=f"sched_{task.id}", help="Move to calendar"):
                schedule_task_dialog(db, task.id, task.title, user_id)