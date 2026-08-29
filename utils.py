def time_to_minutes(t_str: str) -> int:
    h, m = map(int, t_str.split(':'))
    return h * 60 + m

def minutes_to_time(m: int) -> str:
    h = m // 60
    mins = m % 60
    return f"{h:02d}:{mins:02d}"

def get_max_work_minutes(user) -> int:
    start = time_to_minutes(user.work_start or "08:00")
    end = time_to_minutes(user.work_end or "18:00")
    lunch = user.lunch_duration_minutes or 60
    return max(1, end - start - lunch)

def check_fixed_task_conflict(user_tasks: list, date_str: str, start_time_str: str,
                              duration_min: int, exclude_task_id: int = None):
    if not start_time_str:
        return False, None

    req_start = time_to_minutes(start_time_str)
    req_end = req_start + duration_min

    for task in user_tasks:
        if exclude_task_id and task.id == exclude_task_id:
            continue

        t_date = task.date or task.start_date
        if t_date == date_str and task.start_time and task.end_time:
            t_start = time_to_minutes(task.start_time)
            t_end = time_to_minutes(task.end_time)

            if max(req_start, t_start) < min(req_end, t_end):
                return True, task.title

    return False, None

def get_daily_progress(user_tasks: list, date_str: str):
    day_tasks = [
        t for t in user_tasks
        if (t.date == date_str or t.start_date == date_str)
           and t.start_time
           and not (t.title == "Lunch")
    ]

    if not day_tasks:
        return 0, 0, 0, 0, 0.0

    total_count = len(day_tasks)
    completed_count = sum(1 for t in day_tasks if t.status == "done")
    total_minutes = sum(t.duration_minutes or 0 for t in day_tasks)
    completed_minutes = sum(t.duration_minutes or 0 for t in day_tasks if t.status == "done")

    percent = (completed_minutes / total_minutes * 100) if total_minutes > 0 else 0.0
    return total_count, completed_count, total_minutes, completed_minutes, round(percent, 1)