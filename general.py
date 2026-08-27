import utils

def check_user_availability(user_tasks: list, date_str: str, start_time_str: str, duration_min: int):
    req_start = utils.time_to_minutes(start_time_str)
    req_end = req_start + duration_min

    for task in user_tasks:
        t_date = task.get("date") or task.get("start_date")
        if t_date == date_str and task.get("start_time") and task.get("end_time"):
            t_start = utils.time_to_minutes(task["start_time"])
            t_end = utils.time_to_minutes(task["end_time"])

            # пересечение отрезков
            if max(req_start, t_start) < min(req_end, t_end):
                return False, task["title"]

    return True, None

def accept_shared_event(data: dict, event: dict):
    event["status"] = "accepted"

    for u_key in ["user_1", "user_2"]:
        user_tasks = data["users"][u_key]["tasks"]
        # не добавлено ли событие ранее
        if not any(t.get("shared_event_id") == event["id"] for t in user_tasks):
            user_tasks.append({
                "id": f"shared_task_{event['id']}_{u_key}",
                "shared_event_id": event["id"],
                "title": f"🤝 {event['title']}",
                "type": "fixed",
                "date": event["date"],
                "start_date": event["date"],
                "end_date": event["date"],
                "start_time": event["start_time"],
                "end_time": event["end_time"],
                "duration_minutes": event["duration_minutes"],
                "status": "scheduled"
            })

def delete_shared_event(data: dict, event_id: str):
    data["shared_events"] = [e for e in data.get("shared_events", []) if e["id"] != event_id]

    for u_key in ["user_1", "user_2"]:
        data["users"][u_key]["tasks"] = [
            t for t in data["users"][u_key]["tasks"]
            if t.get("shared_event_id") != event_id
        ]