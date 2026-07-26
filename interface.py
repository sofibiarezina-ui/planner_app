import app, algorithm, general
import random, os
import streamlit as st
import uuid  # Библиотека для создания уникальных ID
from datetime import datetime, timedelta, date
from calendar_view import render_mini_calendar



# Настройка заголовка вкладки в браузере
st.set_page_config(page_title="Planner TWI", layout="centered")

# актуальные данные из JSON
data = app.load_data()

#выбор пользователя
st.sidebar.title("Settings")
curr_user = st.sidebar.selectbox(
    "Who are you?",
    options=["user_1", "user_2"],
    format_func=lambda x: data["users"][x]["name"]
)
user_name = data["users"][curr_user]["name"]
st.title(f"Hallo, {user_name}!")


#две вкладки на главной странице
tab_calendar, tab_shared, tab_memes = st.tabs(
    [" My Calendar ", " General Events ", " Memes "]
)


# важные даты и выбор дат ----------------------------------------------------------------------------------------------
st.sidebar.title("Navigation")

# выбор даты
selected_date = st.sidebar.date_input(
    "Choose day",
    value=date.today()
)
selected_date_str = str(selected_date)

# «Важный день»
important_dates = data["users"][curr_user].setdefault("important_dates", [])
is_important = selected_date_str in important_dates

new_important_state = st.sidebar.checkbox("Important days", value=is_important)

# статус чекбокса изменился — обновляем JSON
if new_important_state != is_important:
    if new_important_state:
        data["users"][curr_user]["important_dates"].append(selected_date_str)
    else:
        data["users"][curr_user]["important_dates"].remove(selected_date_str)

    app.save_data(data)
    st.rerun()

st.sidebar.divider()

# 4. Отрисовка мини-календаря
calendar_html = render_mini_calendar(selected_date, data["users"][curr_user])
st.sidebar.markdown(calendar_html, unsafe_allow_html=True)




# Контент для первой вкладки -------------------------------------------------------------------------------------------
with tab_calendar:
    #st.subheader("Your Timetable")
    #st.info("You will be able to add new tasks and use timelines")

    # Форма настроек рабочего дня и обеда
    # =========================================================================
    with st.expander("Work day settings"):
        user_settings = data["users"][curr_user].get("settings", {})

        def parse_time(time_str, default_str):
            if not time_str:
                return datetime.strptime(default_str, "%H:%M").time()
            try:
                return datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                return datetime.strptime(default_str, "%H:%M").time()


        init_work_start = parse_time(user_settings.get("work_start"), "08:00")
        init_work_end = parse_time(user_settings.get("work_end"), "18:00")
        init_lunch_start = parse_time(user_settings.get("lunch_window_start"), "13:00")
        init_lunch_end = parse_time(user_settings.get("lunch_window_end"), "16:00")
        init_lunch_dur = int(user_settings.get("lunch_duration_minutes", 60))

        with st.form(key="settings_form"):
            col_s1, col_s2 = st.columns(2)

            with col_s1:
                set_work_start = st.time_input("Work start", value=init_work_start)
                set_lunch_start = st.time_input("Lunch start", value=init_lunch_start)
                set_lunch_dur = st.number_input(
                    "Lunch duration (min):",
                    min_value=0,
                    max_value=180,
                    value=init_lunch_dur,
                    step=15,
                )

            with col_s2:
                set_work_end = st.time_input("Work end", value=init_work_end)
                set_lunch_end = st.time_input("Lunch end", value=init_lunch_end)



            save_settings = st.form_submit_button("Save settings")

            if save_settings:
                data["users"][curr_user]["settings"] = {
                    "work_start": set_work_start.strftime("%H:%M"),
                    "work_end": set_work_end.strftime("%H:%M"),
                    "lunch_window_start": set_lunch_start.strftime("%H:%M"),
                    "lunch_window_end": set_lunch_end.strftime("%H:%M"),
                    "lunch_duration_minutes": int(set_lunch_dur),
                }

                app.save_data(data)
                st.success("Settings were saved.")
                st.rerun()

    # =========================================================================

    # timeline -------------------------------------------------------------
    st.subheader(f"Timetable for {selected_date_str}")

    curr_data = app.load_data()
    user_tasks = curr_data["users"][curr_user]["tasks"]

    if not user_tasks:
        st.info("You don't have any tasks yet. Create new!")
    else:
        # ЗАДАЧИ С НАЗНАЧЕННЫМ ВРЕМЕНЕМ (и фиксированные, и распределенные плавающие)
        fixed_tasks = [
            t for t in user_tasks
            if t.get("start_time") and t.get("end_time") and (
                    t.get("date") == selected_date_str or t.get("start_date") == selected_date_str
            )
        ]
        fixed_tasks.sort(key=lambda x: x["start_time"])

        # НЕРАСПРЕДЕЛЕННЫЕ ПЛАВАЮЩИЕ ЗАДАЧИ
        floating_tasks = [
            t for t in user_tasks
            if t.get("type") == "floating" and not t.get("start_time") and (
                    t.get("start_date", t.get("date", "")) <= selected_date_str <= t.get("end_date", t.get("date", ""))
            )
        ]

        # ---------------------------------------------------------------------
        # ПРОГРЕСС-БАР ДНЯ
        # ---------------------------------------------------------------------
        tot_cnt, comp_cnt, tot_min, comp_min, pct = app.get_daily_progress(data["users"][curr_user]["tasks"], selected_date_str)

        if tot_cnt > 0:
            c_p1, c_p2 = st.columns([3, 1])
            with c_p1:
                st.progress(pct / 100.0)
            with c_p2:
                st.caption(f"**{pct}% completed** ({comp_min}/{tot_min} min)")
        # ---------------------------------------------------------------------

        st.markdown("##### Scheduled Tasks")
        if not fixed_tasks:
            st.caption("No scheduled tasks")

        for task in fixed_tasks:
            is_lunch = task.get("id", "").startswith("lunch_reserved_block")
            is_done = task.get("status") == "done"

            # Колонки: Чекбокс | Время | Название | Редактировать | Удалить
            col_check, col_time, col_content, col_edit, col_delete = st.columns([0.5, 2, 3.5, 1, 1])

            with col_check:
                # Чекбокс выполнения задачи
                check_state = st.checkbox("", value=is_done, key=f"done_chk_{task['id']}")
                if check_state != is_done:
                    task["status"] = "done" if check_state else "scheduled"
                    app.save_data(curr_data)
                    st.rerun()

            with col_time:
                st.markdown(f"**{task['start_time']} - {task['end_time']}**")

            with col_content:
                title_text = task['title']
                dur_text = f"({task['duration_minutes']} min)"

                if is_done:
                    st.success(f"~~{title_text}~~ ✅ {dur_text}")
                else:
                    st.info(f"**{title_text}** {dur_text}")

            with col_edit:
                with st.popover("Edit"):
                    with st.form(key=f"edit_form_{task['id']}"):
                        new_title = st.text_input("Title", value=task["title"])
                        new_duration = st.number_input("Duration (min):", min_value=15, max_value=480,
                                                       value=task['duration_minutes'], step=15)
                        init_time = datetime.strptime(task["start_time"], "%H:%M").time() if task[
                            "start_time"] else None
                        new_start_time = st.time_input("Start Time:", value=init_time)

                        if st.form_submit_button("Save"):
                            formatted_start = new_start_time.strftime("%H:%M") if new_start_time else None
                            has_conflict, conflict_title = app.check_fixed_task_conflict(
                                curr_data["users"][curr_user]["tasks"],
                                task.get("date", selected_date_str),
                                formatted_start,
                                int(new_duration),
                                exclude_task_id=task["id"]
                            )

                            if has_conflict:
                                    st.error(f"⚠️ Conflict! Time overlaps with «{conflict_title}».")
                            else:
                                task["title"] = new_title
                                task["duration_minutes"] = int(new_duration)
                                if new_start_time:
                                    task["start_time"] = formatted_start
                                    dt_start = datetime.combine(datetime.today(), new_start_time)
                                    dt_end = dt_start + timedelta(minutes=int(new_duration))
                                    task["end_time"] = dt_end.strftime("%H:%M")
                                app.save_data(curr_data)
                                st.rerun()

            with col_delete:
                if st.button("Delete", key=f"del_{task['id']}"):
                    curr_data["users"][curr_user]["tasks"] = [t for t in curr_data["users"][curr_user]["tasks"] if
                                                              t['id'] != task["id"]]
                    app.save_data(curr_data)
                    st.rerun()

        # ------Floating-------------------------------------------------------------------------
        st.divider()
        st.markdown("##### Floating Tasks")
        if not floating_tasks:
            st.caption("No floating tasks")

        for task in floating_tasks:
            col_time, col_content, col_edit, col_delete = st.columns([2, 4, 1, 1])

            with col_time:
                start_d = task.get("start_date", task.get("date", ""))
                end_d = task.get("end_date", task.get("date", ""))
                st.caption(f"{start_d} -> {end_d}")

            with col_content:
                st.warning(f"**{task['title']}** — *{task['duration_minutes']} min*")

            with col_edit:
                with st.popover("Edit"):
                    st.write("**Edit Floating Tasks**")
                    with st.form(key=f"edit_float_form_{task['id']}"):
                        new_title = st.text_input("Title", value=task['title'])
                        new_duration = st.number_input(
                            "Duration (min):",
                            min_value=15,
                            max_value=480,
                            value=task['duration_minutes'],
                            step=15
                        )

                        cur_start = datetime.strptime(task.get("start_date", selected_date_str), "%Y-%m-%d").date()
                        cur_end = datetime.strptime(task.get("end_date", selected_date_str), "%Y-%m-%d").date()

                        new_start_d = st.date_input("Start Date", value=cur_start)
                        new_end_d = st.date_input("End Date", value=cur_end)

                        save_edit = st.form_submit_button("Save")

                        if save_edit:
                            if new_start_d > new_end_d:
                                st.error("Start Date cannot be after Deadline")
                            else:
                                task["title"] = new_title
                                task["duration_minutes"] = int(new_duration)
                                task["start_date"] = str(new_start_d)
                                task["end_date"] = str(new_end_d)
                                task["date"] = str(new_start_d)

                                app.save_data(curr_data)
                                st.success("Updated")
                                st.rerun()

            with col_delete:
                if st.button("Delete", key=f"del_{task['id']}"):
                    curr_data["users"][curr_user]["tasks"] = [
                        t for t in curr_data["users"][curr_user]["tasks"] if t["id"] != task["id"]
                    ]

                    app.save_data(curr_data)
                    st.rerun()


        # автоматическое распределение плавающих задач --------------------------------------------------

        if st.button("Automatically schedule your day", use_container_width=True):
            all_tasks = curr_data["users"][curr_user]["tasks"]

            # удаляем старый обед за этот день
            all_tasks = [
                t for t in all_tasks
                if not (t.get("id", "").startswith("lunch_reserved_block") and t.get("date") == selected_date_str)
            ]

            # сбрасываем старое время у плавающих задач для перераспределения
            for t in all_tasks:
                if t.get("type") == "floating":
                    t["start_time"] = None
                    t["end_time"] = None
                    t["status"] = "pending"

            # фильтруем задачи на сегодня
            day_tasks = [
                t for t in all_tasks
                if (t.get("date") == selected_date_str) or (
                        t.get("type") == "floating" and
                        t.get("start_date", "") <= selected_date_str <= t.get("end_date", "")
                )
            ]

            result = algorithm.planning_algorithm(day_tasks, user_settings, selected_date_str)

            # сохраняем обновленные задачи
            scheduled_dict = {t["id"]: t for t in result["scheduled_tasks"]}

            for idx, task in enumerate(all_tasks):
                if task["id"] in scheduled_dict:
                    all_tasks[idx] = scheduled_dict[task["id"]]

            # добавляем новый обеденный блок
            for st_task in result["scheduled_tasks"]:
                if st_task["id"].startswith("lunch_reserved_block"):
                    all_tasks.append(st_task)

            curr_data["users"][curr_user]["tasks"] = all_tasks
            app.save_data(curr_data)

            if result["unscheduled_tasks"]:
                unscheduled_names = ", ".join([t["title"] for t in result["unscheduled_tasks"]])
                st.warning(f"Unscheduled floating tasks: {unscheduled_names}")
            else:
                st.success("All floating tasks and lunch were scheduled!")

            st.rerun()

    st.divider()  # horisontal line
    st.subheader("+ add new task")

    # тип задачи
    task_type = st.radio(
        "Task Type:",
        options=["fixed", "floating"],
        format_func=lambda x: "fixed time" if x == "fixed" else "floating time (range of days)",
        horizontal=True
    )

    # форма с автоматической чисткой полей после отправки -----------------------------------------
    with st.form(key="add_task_form", clear_on_submit=True):

        # название задачи
        title = st.text_input("Task Title", placeholder="enter task title")

        # длительность - шаг в 15 мин
        duration = st.number_input(
            "Duration (min):",
            min_value=15,
            max_value=480,
            value=60,
            step=15
        )


        if task_type == "fixed":
            start_time_val = st.time_input(
                "Start Time: ",
                value=None
            )
            start_date_val = selected_date
            end_date_val = selected_date
        else:
            start_time_val = None
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                start_date_val = st.date_input("Start Date", value=selected_date)

            with col_d2:
                end_date_val = st.date_input("Deadline", value=selected_date+timedelta(days=7))

        # отправка формы
        submitted = st.form_submit_button("Save the Task")

    # после нажатия кнопки сохранения ---------------------
    if submitted:
        if not title.strip():
            st.error("Please enter a title")
        elif task_type == "floating" and start_date_val > end_date_val:
            st.error("Start Date cannot be later than the Deadline")
        else:
            start_time_str = start_time_val.strftime("%H:%M") if start_time_val else None

            # Проверяем конфликты для фиксированных задач
            has_conflict = False
            conflict_title = None
            if task_type == "fixed" and start_time_str:
                has_conflict, conflict_title = app.check_fixed_task_conflict(
                    curr_data["users"][curr_user]["tasks"],
                    str(start_date_val),
                    start_time_str,
                    int(duration)
                )

            if has_conflict:
                st.error(f"⚠️ Cannot schedule task! Time slot overlaps with «{conflict_title}».")
            else:
                end_time_str = None
                if start_time_val:
                    dt_start = datetime.combine(datetime.today(), start_time_val)
                    end_time_str = (dt_start + timedelta(minutes=duration)).strftime("%H:%M")

                new_task = {
                    "id": str(uuid.uuid4())[:8],
                    "title": title,
                    "type": task_type,
                    "start_date": str(start_date_val),
                    "end_date": str(end_date_val),
                    "date": str(start_date_val),
                    "start_time": start_time_str,
                    "end_time": end_time_str,
                    "duration_minutes": int(duration),
                    "status": "scheduled" if task_type == "fixed" else "pending"
                }

                curr_data = app.load_data()
                curr_data["users"][curr_user]["tasks"].append(new_task)
                app.save_data(curr_data)
                st.success(f"Task «{title}» was successfully added!")
                st.rerun()



# Контент для второй вкладки -------------------------------------------------------------------------------------------
with tab_shared:
    st.subheader("General Events & Proposals")

    curr_data = app.load_data()
    shared_events = curr_data.setdefault("shared_events", [])
    partner_user = "user_2" if curr_user == "user_1" else "user_1"
    partner_name = curr_data["users"][partner_user]["name"]

    # =========================================================================
    st.markdown("##### Existing Shared Events")

    if not shared_events:
        st.info("No shared events yet. Propose one below!")
    else:
        for event in shared_events:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 2])

                with col1:
                    st.markdown(f"### {event['title']}")
                    st.caption(f"**Date:** {event['date']} | **Time:** {event['start_time']} - {event['end_time']} "
                               f"({event['duration_minutes']} min)")

                with col2:
                    is_my_proposal = event.get("proposed_by") == curr_user
                    proposer_name = curr_data["users"].get(event.get("proposed_by", ""), {}).get("name", "Someone")

                    if event["status"] == "accepted":
                        st.success("🟢 Confirmed & Added to calendars")
                    elif event["status"] == "declined":
                        st.error("🔴 Declined")
                    else: # proposed
                        if is_my_proposal:
                            st.warning(f"⏳ Waiting for {partner_name}...")
                        else:
                            st.info(f"📩 Proposed by {proposer_name}")

                with col3:
                    # Кнопки действий
                    if event["status"] == "proposed" and not is_my_proposal:
                        c_acc, c_dec = st.columns(2)
                        with c_acc:
                            if st.button("Accept", key=f"acc_{event['id']}", type="primary"):
                                general.accept_shared_event(curr_data, event)
                                app.save_data(curr_data)
                                st.success("Accepted!")
                                st.rerun()
                        with c_dec:
                            if st.button("Decline", key=f"dec_{event['id']}"):
                                event["status"] = "declined"
                                app.save_data(curr_data)
                                st.rerun()

                    # Кнопка удаления для обеих сторон
                    if st.button("Delete Event", key=f"del_shared_{event['id']}"):
                        general.delete_shared_event(curr_data, event["id"])
                        app.save_data(curr_data)
                        st.success("Event deleted")
                        st.rerun()

    st.divider()

    # 2. ФОРМА ПРЕДЛОЖЕНИЯ НОВОЙ ВСТРЕЧИ
    # =========================================================================
    st.subheader("+ Propose New Event")

    with st.form(key="propose_event_form"):
        event_title = st.text_input("Event Title", placeholder="e.g. Cinema, Dinner, Study Session")

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            event_date = st.date_input("Date", value=selected_date)
        with col_p2:
            event_start_time = st.time_input("Start Time", value=datetime.strptime("19:00", "%H:%M").time())
        with col_p3:
            event_duration = st.number_input("Duration (min)", min_value=15, max_value=480, value=120, step=15)

        event_date_str = str(event_date)
        event_time_str = event_start_time.strftime("%H:%M")

        # ПРОВЕРКА ДОСТУПНОСТИ ОБОИХ УЧАСТНИКОВ В РЕАЛЬНОМ ВРЕМЕНИ
        my_free, my_conflict = general.check_user_availability(
            curr_data["users"][curr_user]["tasks"], event_date_str, event_time_str, int(event_duration)
        )
        partner_free, partner_conflict = general.check_user_availability(
            curr_data["users"][partner_user]["tasks"], event_date_str, event_time_str, int(event_duration)
        )

        st.markdown("**Availability Status:**")
        c_status1, c_status2 = st.columns(2)
        with c_status1:
            if my_free:
                st.caption(f"✅ **You ({user_name}):** Free")
            else:
                st.caption(f"❌ **You ({user_name}):** Busy with «{my_conflict}»")

        with c_status2:
            if partner_free:
                st.caption(f"✅ **{partner_name}:** Free")
            else:
                st.caption(f"⚠️ **{partner_name}:** Busy with «{partner_conflict}»")

        submit_proposal = st.form_submit_button("Send Proposal")

        if submit_proposal:
            if not event_title.strip():
                st.error("Please enter event title")
            else:
                dt_start = datetime.combine(datetime.today(), event_start_time)
                dt_end = dt_start + timedelta(minutes=int(event_duration))
                event_end_str = dt_end.strftime("%H:%M")

                new_event = {
                    "id": str(uuid.uuid4())[:8],
                    "title": event_title,
                    "proposed_by": curr_user,
                    "date": event_date_str,
                    "start_time": event_time_str,
                    "end_time": event_end_str,
                    "duration_minutes": int(event_duration),
                    "status": "proposed"
                }

                curr_data["shared_events"].append(new_event)
                app.save_data(curr_data)
                st.success(f"Proposal «{event_title}» sent to {partner_name}!")
                st.rerun()


# =====================================================================================================================
# Контент для третьей вкладки: Memes
# =====================================================================================================================
with tab_memes:
    st.subheader(" Meme Zone — Personal Anti-Burnout Library")

    # Создаем папку для хранения загруженных картинок, если ее еще нет
    os.makedirs("memes_uploads", exist_ok=True)

    curr_data = app.load_data()
    memes_list = curr_data.setdefault("memes", [])
    partner_user = "user_2" if curr_user == "user_1" else "user_1"
    partner_name = curr_data["users"][partner_user]["name"]

    # 1. СЛУЧАЙНЫЙ МЕМ ИЗ ВАШЕЙ БИБЛИОТЕКИ
    # =========================================================================
    st.markdown("##### 🎲 Random Meme from Your Collection")

    col_rand_btn, col_rand_info = st.columns([2, 3])
    with col_rand_btn:
        if st.button("Get Random Meme", use_container_width=True):
            if memes_list:
                st.session_state["selected_random_meme"] = random.choice(memes_list)
            else:
                st.warning("Library is empty! Upload some memes below")

    if "selected_random_meme" in st.session_state and st.session_state["selected_random_meme"] in memes_list:
        rand_meme = st.session_state["selected_random_meme"]
        proposer = curr_data["users"].get(rand_meme.get("sender"), {}).get("name", "Someone")

        img_source = rand_meme.get("path") or rand_meme.get("url")
        if img_source:
            with st.container(border=True):
                st.image(img_source, caption=f"«{rand_meme.get('caption', '')}» — Uploaded by {proposer}",
                         use_container_width=True)

    st.divider()

    # 2. ФОРМА ЗАГРУЗКИ НОВОГО МЕМА (Файлом или Ссылкой)
    # =========================================================================
    st.subheader("+ Add Meme to Library")

    with st.form(key="upload_meme_form", clear_on_submit=True):
        uploaded_file = st.file_uploader("Upload Image File (PNG, JPG, GIF)", type=["png", "jpg", "jpeg", "gif"])
        meme_url = st.text_input("OR Direct Image URL", placeholder="https://example.com/meme.jpg")
        meme_caption = st.text_input("Caption / Inside Joke", placeholder="e.g. When the code works on the first try")

        submit_meme = st.form_submit_button("Upload to Collection")

        if submit_meme:
            if not uploaded_file and not meme_url.strip():
                st.error("Please upload an image file or enter an image URL.")
            else:
                saved_path = None

                # Если загружен файл — сохраняем его локально в папку memes_uploads
                if uploaded_file:
                    file_ext = uploaded_file.name.split(".")[-1]
                    file_id = str(uuid.uuid4())[:8]
                    saved_path = f"memes_uploads/{file_id}.{file_ext}"
                    with open(saved_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                new_meme = {
                    "id": str(uuid.uuid4())[:8],
                    "sender": curr_user,
                    "path": saved_path,
                    "url": meme_url.strip() if not saved_path else None,
                    "caption": meme_caption.strip(),
                    "date": str(date.today())
                }

                curr_data["memes"].append(new_meme)
                app.save_data(curr_data)
                st.success("New meme added to the library!")
                st.rerun()

    st.divider()

    # 3. ЛЕНТА / БИБЛИОТЕКА ВСЕХ МЕМОВ
    # =========================================================================
    st.markdown(f"##### Shared Library ({len(memes_list)} memes)")

    if not memes_list:
        st.info("No memes in the collection yet. Be the first to upload one!")
    else:
        # Отображаем мемы сеткой по 2 в ряд
        cols = st.columns(2)
        for idx, meme in enumerate(reversed(memes_list)):
            with cols[idx % 2]:
                with st.container(border=True):
                    img_src = meme.get("path") or meme.get("url")
                    sender_name = curr_data["users"].get(meme.get("sender"), {}).get("name", "Someone")
                    is_me = meme.get("sender") == curr_user

                    if img_src:
                        st.image(img_src, use_container_width=True)

                    if meme.get("caption"):
                        st.markdown(f"**«{meme['caption']}»**")

                    st.caption(f"Added by **{sender_name}** on {meme.get('date', '')}")

                    if st.button("Delete", key=f"del_m_{meme['id']}_{idx}"):
                        # Если был файл на диске — удаляем его
                        if meme.get("path") and os.path.exists(meme["path"]):
                            try:
                                os.remove(meme["path"])
                            except Exception:
                                pass

                        curr_data["memes"] = [m for m in curr_data["memes"] if m["id"] != meme["id"]]
                        app.save_data(curr_data)
                        st.success("Meme removed")
                        st.rerun()