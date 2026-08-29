import streamlit as st
import uuid, os, random
from datetime import datetime, timedelta, date

from database import SessionLocal, init_db, User, Task, SharedEvent, Meme
import crud, auth, utils, algorithm
from calendar_view import render_mini_calendar

st.set_page_config(page_title="Planner TWI", layout="wide")
init_db()

def check_availability(user_tasks, date_str, start_time_str, duration_min):
    if not start_time_str:
        return True, None
    req_start = utils.time_to_minutes(start_time_str)
    req_end = req_start + duration_min

    for t in user_tasks:
        t_date = t.date or t.start_date
        if t_date == date_str and t.start_time and t.end_time:
            t_start = utils.time_to_minutes(t.start_time)
            t_end = utils.time_to_minutes(t.end_time)
            if max(req_start, t_start) < min(req_end, t_end):
                return False, t.title
    return True, None

def main():
    db = SessionLocal()

    try:
        is_logged_in = auth.render_auth_ui(db)
        if not is_logged_in:
            st.info("Please log in or register to use the planner.")
            return

        user_id = st.session_state.user_id
        current_user = db.query(User).filter_by(id=user_id).first()

        st.title(f"Hallo, {current_user.username}!")

        # --------------------------------------------------------------------------------------------------
        # Навигация и Мини-календарь в боковой панели
        # --------------------------------------------------------------------------------------------------
        st.sidebar.title("Navigation")
        selected_date = st.sidebar.date_input("Choose day", value=date.today())
        selected_date_str = str(selected_date)

        important_dates = crud.get_important_dates(db, user_id)
        is_important = selected_date_str in important_dates
        new_important_state = st.sidebar.checkbox("Important day", value=is_important)

        if new_important_state != is_important:
            crud.toggle_important_date(db, user_id, selected_date_str)
            st.rerun()

        st.sidebar.divider()
        calendar_html = render_mini_calendar(db, current_user, selected_date)
        st.sidebar.markdown(calendar_html, unsafe_allow_html=True)

        # --------------------------------------------------------------------------------------------------
        # Вкладки
        # --------------------------------------------------------------------------------------------------
        tab_calendar, tab_matrix, tab_weekly, tab_shared, tab_memes = st.tabs([
            " My Calendar ", " Eisenhower Matrix ", " Weekly Schedule ", " General Events ", " Memes "
        ])

        # ==================================================================================================
        # Вкладка 1: My Calendar
        # ==================================================================================================
        with tab_calendar:
            with st.expander("Work day settings"):
                def parse_time(time_str, default_str):
                    try:
                        return datetime.strptime(time_str, "%H:%M").time()
                    except (ValueError, TypeError):
                        return datetime.strptime(default_str, "%H:%M").time()

                init_work_start = parse_time(current_user.work_start, "08:00")
                init_work_end = parse_time(current_user.work_end, "18:00")
                init_lunch_start = parse_time(current_user.lunch_window_start, "13:00")
                init_lunch_end = parse_time(current_user.lunch_window_end, "16:00")
                init_lunch_dur = int(current_user.lunch_duration_minutes or 60)

                with st.form(key="settings_form"):
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        set_work_start = st.time_input("Work start", value=init_work_start)
                        set_lunch_start = st.time_input("Lunch start", value=init_lunch_start)
                        set_lunch_dur = st.number_input("Lunch duration (min):", min_value=0, max_value=180, value=init_lunch_dur, step=15)
                    with col_s2:
                        set_work_end = st.time_input("Work end", value=init_work_end)
                        set_lunch_end = st.time_input("Lunch end", value=init_lunch_end)

                    if st.form_submit_button("Save settings"):
                        crud.update_user_settings(db, user_id, {
                            "work_start": set_work_start.strftime("%H:%M"),
                            "work_end": set_work_end.strftime("%H:%M"),
                            "lunch_window_start": set_lunch_start.strftime("%H:%M"),
                            "lunch_window_end": set_lunch_end.strftime("%H:%M"),
                            "lunch_duration_minutes": int(set_lunch_dur)
                        })
                        st.success("Settings saved.")
                        st.rerun()

            st.subheader(f"Timetable for {selected_date_str}")
            user_tasks = crud.get_user_tasks(db, user_id)

            fixed_tasks = [
                t for t in user_tasks
                if t.start_time and t.end_time and (t.date == selected_date_str or t.start_date == selected_date_str)
            ]
            fixed_tasks.sort(key=lambda x: x.start_time)

            floating_tasks = [
                t for t in user_tasks
                if t.type == "floating" and not t.start_time and (
                    (t.start_date or t.date or "") <= selected_date_str <= (t.end_date or t.date or "")
                )
            ]

            tot_cnt, comp_cnt, tot_min, comp_min, pct = utils.get_daily_progress(user_tasks, selected_date_str)
            if tot_cnt > 0:
                c_p1, c_p2 = st.columns([3, 1])
                with c_p1: st.progress(pct / 100.0)
                with c_p2: st.caption(f"**{pct}% completed** ({comp_min}/{tot_min} min)")

            st.markdown("##### Scheduled Tasks")
            if not fixed_tasks: st.caption("No scheduled tasks")

            for task in fixed_tasks:
                is_done = task.status == "done"
                col_check, col_time, col_content, col_edit, col_delete = st.columns([0.5, 2, 4, 1, 1])

                with col_check:
                    check_state = st.checkbox("", value=is_done, key=f"done_chk_{task.id}")
                    if check_state != is_done:
                        crud.update_task(db, task.id, status="done" if check_state else "scheduled")
                        st.rerun()
                with col_time:
                    st.markdown(f"**{task.start_time} - {task.end_time}**")
                with col_content:
                    t_title = task.title
                    dur = f"({task.duration_minutes} min)"
                    if is_done: st.success(f"~~{t_title}~~ ✅ {dur}")
                    else: st.info(f"**{t_title}** {dur}")
                with col_edit:
                    with st.popover("Edit"):
                        with st.form(key=f"edit_form_{task.id}"):
                            new_title = st.text_input("Title", value=task.title)
                            new_dur = st.number_input("Duration (min):", min_value=15, max_value=480, value=task.duration_minutes, step=15)
                            init_t = datetime.strptime(task.start_time, "%H:%M").time() if task.start_time else None
                            new_st = st.time_input("Start Time:", value=init_t)

                            if st.form_submit_button("Save"):
                                fmt_st = new_st.strftime("%H:%M") if new_st else None
                                conflict, c_title = utils.check_fixed_task_conflict(
                                    user_tasks, task.date or selected_date_str, fmt_st, int(new_dur), exclude_task_id=task.id
                                )
                                if conflict:
                                    st.error(f"⚠️ Conflict with «{c_title}».")
                                else:
                                    fmt_end = None
                                    if new_st:
                                        dt_s = datetime.combine(datetime.today(), new_st)
                                        fmt_end = (dt_s + timedelta(minutes=int(new_dur))).strftime("%H:%M")
                                    crud.update_task(db, task.id, title=new_title, duration_minutes=int(new_dur), start_time=fmt_st, end_time=fmt_end)
                                    st.rerun()
                with col_delete:
                    if st.button("Delete", key=f"del_{task.id}"):
                        crud.delete_task(db, task.id)
                        st.rerun()

            st.divider()
            st.markdown("##### Floating Tasks")
            if not floating_tasks: st.caption("No floating tasks")

            for task in floating_tasks:
                col_time, col_content, col_edit, col_delete = st.columns([2, 4, 1, 1])
                with col_time:
                    st.caption(f"{task.start_date or task.date} -> {task.end_date or task.date}")
                with col_content:
                    st.warning(f"**{task.title}** — *{task.duration_minutes} min*")
                with col_edit:
                    with st.popover("Edit"):
                        with st.form(key=f"edit_fl_{task.id}"):
                            n_title = st.text_input("Title", value=task.title)
                            n_dur = st.number_input("Duration (min):", min_value=15, max_value=480, value=task.duration_minutes, step=15)
                            cur_s = datetime.strptime(task.start_date or selected_date_str, "%Y-%m-%d").date()
                            cur_e = datetime.strptime(task.end_date or selected_date_str, "%Y-%m-%d").date()
                            n_s_d = st.date_input("Start Date", value=cur_s)
                            n_e_d = st.date_input("End Date", value=cur_e)

                            if st.form_submit_button("Save"):
                                if n_s_d > n_e_d:
                                    st.error("Start Date cannot be after Deadline")
                                else:
                                    crud.update_task(db, task.id, title=n_title, duration_minutes=int(n_dur), start_date=str(n_s_d), end_date=str(n_e_d), date=str(n_s_d))
                                    st.rerun()
                with col_delete:
                    if st.button("Delete", key=f"del_fl_{task.id}"):
                        crud.delete_task(db, task.id)
                        st.rerun()

            # Автоматическое расписание с отчетом
            st.divider()
            if st.button("Automatically schedule your day", use_container_width=True):
                for t in user_tasks:
                    if t.title == "Lunch" and t.date == selected_date_str:
                        crud.delete_task(db, t.id)

                settings_dict = {
                    "work_start": current_user.work_start,
                    "work_end": current_user.work_end,
                    "lunch_window_start": current_user.lunch_window_start,
                    "lunch_window_end": current_user.lunch_window_end,
                    "lunch_duration_minutes": current_user.lunch_duration_minutes
                }

                day_tasks = [
                    {
                        "id": t.id, "title": t.title, "type": t.type,
                        "start_time": t.start_time, "end_time": t.end_time,
                        "duration_minutes": t.duration_minutes, "status": t.status,
                        "date": t.date, "start_date": t.start_date, "end_date": t.end_date
                    }
                    for t in user_tasks
                    if (t.date == selected_date_str) or (
                        t.type == "floating" and (t.start_date or "") <= selected_date_str <= (t.end_date or "")
                    )
                ]

                result = algorithm.planning_algorithm(day_tasks, settings_dict, selected_date_str)

                for st_task in result["scheduled_tasks"]:
                    if str(st_task["id"]).startswith("lunch_reserved_block"):
                        crud.create_task(
                            db, user_id, title="Lunch", type="fixed", date=selected_date_str,
                            start_time=st_task["start_time"], end_time=st_task["end_time"],
                            duration_minutes=st_task["duration_minutes"], is_scheduled=True, status="scheduled"
                        )
                    else:
                        crud.update_task(
                            db, st_task["id"], date=selected_date_str,
                            start_time=st_task["start_time"], end_time=st_task["end_time"],
                            is_scheduled=True, status="scheduled"
                        )

                if result.get("unscheduled_tasks"):
                    unscheduled_names = ", ".join([t["title"] for t in result["unscheduled_tasks"]])
                    st.warning(f"Unscheduled floating tasks due to lack of time: {unscheduled_names}")
                else:
                    st.success("All tasks and lunch were successfully scheduled!")
                st.rerun()

            # Добавление задачи
            st.divider()
            st.subheader("+ Add New Task")
            task_type = st.radio("Task Type:", options=["fixed", "floating"], format_func=lambda x: "fixed time" if x == "fixed" else "floating time", horizontal=True)

            with st.form(key="add_task_form", clear_on_submit=True):
                title = st.text_input("Task Title")
                duration = st.number_input("Duration (min):", min_value=15, max_value=480, value=60, step=15)

                if task_type == "fixed":
                    start_time_val = st.time_input("Start Time:", value=None)
                    start_date_val, end_date_val = selected_date, selected_date
                else:
                    start_time_val = None
                    col_d1, col_d2 = st.columns(2)
                    with col_d1: start_date_val = st.date_input("Start Date", value=selected_date)
                    with col_d2: end_date_val = st.date_input("Deadline", value=selected_date + timedelta(days=7))

                if st.form_submit_button("Save Task"):
                    if not title.strip(): st.error("Please enter a title")
                    elif task_type == "floating" and start_date_val > end_date_val: st.error("Start Date cannot be after Deadline")
                    else:
                        start_time_str = start_time_val.strftime("%H:%M") if start_time_val else None
                        has_conflict, conflict_title = utils.check_fixed_task_conflict(user_tasks, str(start_date_val), start_time_str, int(duration))

                        if has_conflict:
                            st.error(f"⚠️ Conflict with «{conflict_title}».")
                        else:
                            end_time_str = None
                            if start_time_val:
                                dt_start = datetime.combine(datetime.today(), start_time_val)
                                end_time_str = (dt_start + timedelta(minutes=duration)).strftime("%H:%M")

                            crud.create_task(
                                db, user_id, title=title, type=task_type,
                                start_date=str(start_date_val), end_date=str(end_date_val), date=str(start_date_val),
                                start_time=start_time_str, end_time=end_time_str, duration_minutes=int(duration),
                                is_scheduled=(task_type == "fixed"), status="scheduled" if task_type == "fixed" else "pending"
                            )
                            st.success(f"Task «{title}» added!")
                            st.rerun()

        # ==================================================================================================
        # Вкладка 2: Eisenhower Matrix (С возможностью планирования)
        # ==================================================================================================
        with tab_matrix:
            st.subheader("Eisenhower Matrix")
            with st.expander("+ Add task to Matrix", expanded=True):
                with st.form("matrix_add_form", clear_on_submit=True):
                    m_title = st.text_input("Task Title")
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        m_quadrant = st.selectbox("Quadrant", ["DO", "PLAN", "DELEGATE", "ELIMINATE"])
                        m_dur = st.number_input("Duration (min)", min_value=15, max_value=480, value=60, step=15)
                    with col_m2:
                        m_start_d = st.date_input("Start Date", value=selected_date)
                        m_end_d = st.date_input("Deadline", value=selected_date + timedelta(days=7))

                    if st.form_submit_button("Add to Matrix"):
                        if m_title.strip():
                            crud.create_task(
                                db, user_id, title=m_title, quadrant=m_quadrant, type="floating",
                                duration_minutes=int(m_dur), start_date=str(m_start_d), end_date=str(m_end_d),
                                date=str(m_start_d), is_scheduled=False, status="pending"
                            )
                            st.rerun()

            m_tasks = crud.get_matrix_tasks(db, user_id)
            m_cols = st.columns(2)
            q_map = [
                ("DO", "🔴 Urgent & Important", m_cols[0]),
                ("PLAN", "🔵 Not Urgent & Important", m_cols[1]),
                ("DELEGATE", "🟡 Urgent & Unimportant", m_cols[0]),
                ("ELIMINATE", "⚪ Not Urgent & Unimportant", m_cols[1])
            ]

            for q_code, q_label, col in q_map:
                with col:
                    st.markdown(f"### {q_label}")
                    quad_tasks = [x for x in m_tasks if x.quadrant == q_code]
                    if not quad_tasks:
                        st.caption("No tasks in this quadrant")
                    for t in quad_tasks:
                        with st.container(border=True):
                            st.write(f"**{t.title}** ({t.duration_minutes} min)")
                            st.caption(f"Range: {t.start_date or t.date} -> {t.end_date or t.date}")
                            if t.is_scheduled or t.start_time:
                                st.success("🗓️ Scheduled in Calendar")
                            else:
                                c_m_act1, c_m_act2 = st.columns(2)
                                with c_m_act1:
                                    with st.popover("🗓️ Plan Time"):
                                        with st.form(key=f"plan_mat_form_{t.id}"):
                                            plan_date = st.date_input("Date", value=selected_date)
                                            plan_time = st.time_input("Start Time",
                                                                      value=datetime.strptime("09:00", "%H:%M").time())

                                            if st.form_submit_button("Schedule"):
                                                start_str = plan_time.strftime("%H:%M")
                                                dt_start = datetime.combine(datetime.today(), plan_time)
                                                end_str = (dt_start + timedelta(minutes=t.duration_minutes)).strftime(
                                                    "%H:%M")

                                                # Проверяем конфликты
                                                all_user_tasks = crud.get_user_tasks(db, user_id)
                                                has_conflict, c_title = utils.check_fixed_task_conflict(
                                                    all_user_tasks, str(plan_date), start_str, t.duration_minutes,
                                                    exclude_task_id=t.id
                                                )
                                                if has_conflict:
                                                    st.error(f"Conflict with «{c_title}»")
                                                else:
                                                    crud.update_task(
                                                        db, t.id,
                                                        date=str(plan_date),
                                                        start_date=str(plan_date),
                                                        start_time=start_str,
                                                        end_time=end_str,
                                                        type="fixed",
                                                        is_scheduled=True,
                                                        status="scheduled"
                                                    )
                                                    st.success("Task scheduled on calendar!")
                                                    st.rerun()
                                with c_m_act2:
                                    if st.button("Delete", key=f"del_mat_{t.id}"):
                                        crud.delete_task(db, t.id)
                                        st.rerun()



        # ==================================================================================================
        # Вкладка 3: Weekly Schedule (Переработанный сетчатый интерфейс)
        # ==================================================================================================
        with tab_weekly:
            st.subheader("Weekly Schedule")
            start_of_week = selected_date - timedelta(days=selected_date.weekday())
            w_cols = st.columns(7)
            days_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

            for idx, d_name in enumerate(days_names):
                curr_d = start_of_week + timedelta(days=idx)
                curr_d_str = str(curr_d)
                is_today = curr_d == date.today()

                with w_cols[idx]:
                    header_bg = "🟢 " if is_today else ""
                    st.markdown(f"### {header_bg}{d_name}")
                    st.caption(f"`{curr_d_str}`")

                    with st.container(border=True):
                        w_tasks = crud.get_scheduled_tasks_by_date(db, user_id, curr_d_str)
                        if not w_tasks:
                            st.caption("No tasks")
                        else:
                            for wt in sorted(w_tasks, key=lambda x: x.start_time or "00:00"):
                                status_icon = "✅" if wt.status == "done" else "⏳"
                                st.markdown(f"**{wt.start_time} - {wt.end_time}**")
                                st.markdown(f"{status_icon} *{wt.title}*")
                                st.divider()

        # ==================================================================================================
        # Вкладка 4: General Events (Выбор адресата и проверка доступности)
        # ==================================================================================================
        with tab_shared:
            st.subheader("General Events & Proposals")
            shared_events = crud.get_shared_events_for_user(db, user_id)
            other_users = crud.get_all_other_users(db, user_id)

            st.markdown("##### Existing Shared Events")
            if not shared_events:
                st.info("No shared events yet.")
            else:
                for event in shared_events:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 2, 2])
                        proposer = db.query(User).filter_by(id=event.proposed_by_id).first()
                        receiver = db.query(User).filter_by(id=event.receiver_id).first()
                        proposer_name = proposer.username if proposer else "Someone"
                        receiver_name = receiver.username if receiver else "Someone"

                        with c1:
                            st.markdown(f"### {event.title}")
                            st.caption(f"**From:** {proposer_name} | **To:** {receiver_name}")
                            st.caption(f"**Date:** {event.date} | **Time:** {event.start_time} - {event.end_time} ({event.duration_minutes} min)")
                        with c2:
                            is_my_prop = event.proposed_by_id == user_id
                            if event.status == "accepted": st.success("🟢 Confirmed & Added to calendars")
                            elif event.status == "declined": st.error("🔴 Declined")
                            else: st.warning("⏳ Waiting..." if is_my_prop else f"📩 Proposed by {proposer_name}")
                        with c3:
                            if event.status == "proposed" and not is_my_prop:
                                c_acc, c_dec = st.columns(2)
                                with c_acc:
                                    if st.button("Accept", key=f"acc_ev_{event.id}", type="primary"):
                                        crud.accept_shared_event(db, event.id)
                                        st.rerun()
                                with c_dec:
                                    if st.button("Decline", key=f"dec_ev_{event.id}"):
                                        crud.update_shared_event_status(db, event.id, "declined")
                                        st.rerun()
                            if st.button("Delete Event", key=f"del_ev_{event.id}"):
                                crud.delete_shared_event(db, event.id)
                                st.rerun()

            st.divider()
            st.subheader("+ Propose New Event")
            if not other_users:
                st.warning("No other registered users found to invite.")
            else:
                with st.form(key="propose_event_form"):
                    selected_partner = st.selectbox("Select Partner", options=other_users, format_func=lambda u: u.username)
                    event_title = st.text_input("Event Title", placeholder="e.g. Cinema, Meeting, Dinner")

                    col_p1, col_p2, col_p3 = st.columns(3)
                    with col_p1: event_date = st.date_input("Date", value=selected_date)
                    with col_p2: event_start_time = st.time_input("Start Time", value=datetime.strptime("19:00", "%H:%M").time())
                    with col_p3: event_duration = st.number_input("Duration (min)", min_value=15, max_value=480, value=120, step=15)

                    event_date_str = str(event_date)
                    event_time_str = event_start_time.strftime("%H:%M")

                    # Проверка доступности обеих сторон
                    my_free, my_conflict = check_availability(user_tasks, event_date_str, event_time_str, int(event_duration))
                    partner_tasks = crud.get_user_tasks(db, selected_partner.id)
                    partner_free, partner_conflict = check_availability(partner_tasks, event_date_str, event_time_str, int(event_duration))

                    st.markdown("**Availability Status:**")
                    c_st1, c_st2 = st.columns(2)
                    with c_st1:
                        if my_free: st.caption(f"✅ **You ({current_user.username}):** Free")
                        else: st.caption(f"❌ **You ({current_user.username}):** Busy with «{my_conflict}»")
                    with c_st2:
                        if partner_free: st.caption(f"✅ **{selected_partner.username}:** Free")
                        else: st.caption(f"⚠️ **{selected_partner.username}:** Busy with «{partner_conflict}»")

                    if st.form_submit_button("Send Proposal"):
                        if not event_title.strip():
                            st.error("Please enter event title")
                        else:
                            dt_start = datetime.combine(datetime.today(), event_start_time)
                            event_end_str = (dt_start + timedelta(minutes=int(event_duration))).strftime("%H:%M")
                            crud.create_shared_event(
                                db, title=event_title, proposed_by_id=user_id, receiver_id=selected_partner.id,
                                date=event_date_str, start_time=event_time_str, end_time=event_end_str, duration_minutes=int(event_duration)
                            )
                            st.success(f"Proposal sent to {selected_partner.username}!")
                            st.rerun()

        # ==================================================================================================
        # Вкладка 5: Memes (С выбором случайного мема и указанием автора)
        # ==================================================================================================
        with tab_memes:
            st.subheader("Meme Zone — Personal Anti-Burnout Library")
            os.makedirs("memes_uploads", exist_ok=True)
            memes_list = crud.get_all_memes(db)

            st.markdown("##### 🎲 Random Meme")
            if st.button("Get Random Meme"):
                if memes_list:
                    st.session_state["selected_random_meme_id"] = random.choice(memes_list).id
                else:
                    st.warning("Library is empty!")

            if "selected_random_meme_id" in st.session_state:
                rand_m = db.query(Meme).filter_by(id=st.session_state["selected_random_meme_id"]).first()
                if rand_m:
                    sender = db.query(User).filter_by(id=rand_m.sender_id).first()
                    sender_name = sender.username if sender else "Someone"
                    with st.container(border=True):
                        st.image(rand_m.path or rand_m.url, caption=f"«{rand_m.caption}» — Uploaded by {sender_name}")

            if "selected_random_meme" in st.session_state:
                rand_m = st.session_state["selected_random_meme"]
                sender = db.query(User).filter_by(id=rand_m.sender_id).first()
                sender_name = sender.username if sender else "Someone"
                with st.container(border=True):
                    st.image(rand_m.path or rand_m.url, caption=f"«{rand_m.caption}» — Uploaded by {sender_name}")

            st.divider()
            st.subheader("+ Add Meme to Library")
            with st.form(key="upload_meme_form", clear_on_submit=True):
                uploaded_file = st.file_uploader("Upload Image File", type=["png", "jpg", "jpeg", "gif"])
                meme_url = st.text_input("OR Direct Image URL")
                meme_caption = st.text_input("Caption")

                if st.form_submit_button("Upload"):
                    saved_path = None
                    if uploaded_file:
                        saved_path = f"memes_uploads/{uuid.uuid4()[:8]}.{uploaded_file.name.split('.')[-1]}"
                        with open(saved_path, "wb") as f: f.write(uploaded_file.getbuffer())

                    if not saved_path and not meme_url.strip():
                        st.error("Please upload a file or specify a URL")
                    else:
                        crud.create_meme(db, sender_id=user_id, path=saved_path, url=meme_url.strip(), caption=meme_caption.strip(), date_str=str(date.today()))
                        st.success("Meme added!")
                        st.rerun()

            st.divider()
            st.markdown(f"##### Collection ({len(memes_list)} memes)")
            m_cols = st.columns(2)
            for idx, m in enumerate(reversed(memes_list)):
                sender = db.query(User).filter_by(id=m.sender_id).first()
                sender_name = sender.username if sender else "Someone"
                with m_cols[idx % 2]:
                    with st.container(border=True):
                        st.image(m.path or m.url)
                        if m.caption: st.write(f"**«{m.caption}»**")
                        st.caption(f"Added by **{sender_name}** on {m.date}")
                        if st.button("Delete", key=f"del_meme_{m.id}"):
                            crud.delete_meme(db, m.id)
                            st.rerun()

    finally:
        db.close()

if __name__ == "__main__":
    main()