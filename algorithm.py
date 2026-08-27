import utils

def planning_algorithm(tasks: list, settings: dict, target_date: str) -> dict:
    work_start = utils.time_to_minutes(settings.get("work_start", "08:00"))
    work_end = utils.time_to_minutes(settings.get("work_end", "21:00"))

    lunch_win_start = utils.time_to_minutes(settings.get("lunch_window_start", "12:00"))
    lunch_win_end = utils.time_to_minutes(settings.get("lunch_window_end", "16:00"))
    lunch_dur = int(settings.get("lunch_duration_minutes", 60))

    # желаемое время обеда — 14:00 (если входит в окно)
    preferred_lunch_start = lunch_win_start
    if not (lunch_win_start <= preferred_lunch_start <= lunch_win_end - lunch_dur):
        preferred_lunch_start = lunch_win_start

    # жестко фиксированные задачи
    busy_blocks = []
    placed_tasks = []

    for t in tasks:
        if t.get("type") == "fixed" and t.get("start_time") and t.get("end_time"):
            busy_blocks.append({
                "start": utils.time_to_minutes(t["start_time"]),
                "end": utils.time_to_minutes(t["end_time"])
            })
            placed_tasks.append(t.copy())

    busy_blocks.sort(key=lambda x: x["start"])

    # свободные окна
    brakes = []
    current_cursor = work_start
    for block in busy_blocks:
        if block["start"] > current_cursor:
            brakes.append({"start": current_cursor, "end": block["start"]})
        current_cursor = max(current_cursor, block["end"])

    if current_cursor < work_end:
        brakes.append({"start": current_cursor, "end": work_end})

    # установка обеда (14:00)
    lunch_placed = False
    if lunch_dur > 0:
        best_lunch_start = None
        for b in brakes:
            overlap_start = max(b["start"], lunch_win_start)
            overlap_end = min(b["end"], lunch_win_end)

            if overlap_end - overlap_start >= lunch_dur:
                # 14:00 свободно — ставим на 14:00, иначе в начало свободного окна
                if overlap_start <= preferred_lunch_start and (preferred_lunch_start + lunch_dur) <= overlap_end:
                    best_lunch_start = preferred_lunch_start
                else:
                    best_lunch_start = overlap_start
                break

        if best_lunch_start is not None:
            lunch_block = {
                "id": f"lunch_reserved_block_{target_date}",
                "title": "Lunch",
                "type": "fixed",
                "date": target_date,
                "start_time": utils.minutes_to_time(best_lunch_start),
                "end_time": utils.minutes_to_time(best_lunch_start + lunch_dur),
                "duration_minutes": lunch_dur,
                "status": "scheduled"
            }
            placed_tasks.append(lunch_block)
            busy_blocks.append({"start": best_lunch_start, "end": best_lunch_start + lunch_dur})
            lunch_placed = True

    # пересчитываем окна с учётом обеда
    busy_blocks.sort(key=lambda x: x["start"])
    brakes = []
    current_cursor = work_start
    for block in busy_blocks:
        if block["start"] > current_cursor:
            brakes.append({"start": current_cursor, "end": block["start"]})
        current_cursor = max(current_cursor, block["end"])

    if current_cursor < work_end:
        brakes.append({"start": current_cursor, "end": work_end})

    # распределяем плавающие задачи
    floating_tasks = [t.copy() for t in tasks if t.get("type") == "floating"]
    floating_tasks.sort(key=lambda x: x.get("duration_minutes", 0), reverse=True)

    for brake in brakes:
        slot_start = brake["start"]
        i = 0
        while i < len(floating_tasks):
            task = floating_tasks[i]
            task_dur = task["duration_minutes"]
            remaining_dur = brake["end"] - slot_start

            if task_dur <= remaining_dur:
                floating_tasks.pop(i)
                task_start = slot_start
                task_end = slot_start + task_dur

                task["date"] = target_date
                task["start_time"] = utils.minutes_to_time(task_start)
                task["end_time"] = utils.minutes_to_time(task_end)
                task["status"] = "scheduled"

                placed_tasks.append(task)
                slot_start = task_end
            else:
                i += 1

    placed_tasks.sort(key=lambda x: utils.time_to_minutes(x["start_time"]))

    return {
        "scheduled_tasks": placed_tasks,
        "unscheduled_tasks": floating_tasks,
        "lunch_placed": lunch_placed
    }





