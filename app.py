import json

def load_data():
    with open("data.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data

def save_data(data):
    with open("data.json", "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def time_to_minutes(t_str: str) -> int:
    h, m = map(int, t_str.split(':'))
    return h * 60 + m

def minutes_to_time(m: int) -> str:
    h = m // 60
    mins = m % 60
    return f"{h:02d}:{mins:02d}"

def get_max_work_minutes(settings: dict) -> int:
    start = time_to_minutes(settings.get("work_start", "08:00"))
    end = time_to_minutes(settings.get("work_end", "21:00"))
    lunch = settings.get("lunch_duration_minutes", 60)

    total = end-start-lunch

    return max(1, total)

def get_daily_load_minutes(tasks: list, date_str:str) -> int:
    total = 0
    for task in tasks:
        if task.get("date") == date_str and task.get("status") in ["scheduled", "done"]:
            total += task.get("duration_minutes", 0)

    return total


def check_fixed_task_conflict(user_tasks: list, date_str: str, start_time_str: str, duration_min: int,
                              exclude_task_id: str = None):
    """
    Проверяет, не пересекается ли создаваемая/редактируемая задача
    с другими уже распланированными задачами пользователя.
    """
    if not start_time_str:
        return False, None

    req_start = time_to_minutes(start_time_str)
    req_end = req_start + duration_min

    for task in user_tasks:
        # Игнорируем задачу, которую в данный момент редактируем
        if exclude_task_id and task.get("id") == exclude_task_id:
            continue

        t_date = task.get("date") or task.get("start_date")

        # Проверяем пересечения только с задачами, у которых уже задано время
        if t_date == date_str and task.get("start_time") and task.get("end_time"):
            t_start = time_to_minutes(task["start_time"])
            t_end = time_to_minutes(task["end_time"])

            # Формула пересечения временных интервалов
            if max(req_start, t_start) < min(req_end, t_end):
                return True, task["title"]

    return False, None


def get_daily_progress(user_tasks: list, date_str: str):
    """
    Возвращает статистику выполнения задач на выбранный день:
    (всего задач, выполнено задач, всего минут, выполнено минут, процент выполнения)
    """
    day_tasks = [
        t for t in user_tasks
        if (t.get("date") == date_str or t.get("start_date") == date_str)
           and t.get("start_time")
           and not t.get("id", "").startswith("lunch_reserved_block")  # обед не считаем за рабочую задачу
    ]

    if not day_tasks:
        return 0, 0, 0, 0, 0.0

    total_count = len(day_tasks)
    completed_count = sum(1 for t in day_tasks if t.get("status") == "done")

    total_minutes = sum(t.get("duration_minutes", 0) for t in day_tasks)
    completed_minutes = sum(t.get("duration_minutes", 0) for t in day_tasks if t.get("status") == "done")

    percent = (completed_minutes / total_minutes * 100) if total_minutes > 0 else 0.0
    return total_count, completed_count, total_minutes, completed_minutes, round(percent, 1)

