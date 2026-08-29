import calendar
import utils
from datetime import date
import crud

def render_mini_calendar(db, user, selected_date: date) -> str:
    year = selected_date.year
    month = selected_date.month

    cal = calendar.monthcalendar(year, month)
    max_minutes = utils.get_max_work_minutes(user)
    important_dates = set(crud.get_important_dates(db, user.id))
    tasks = crud.get_user_tasks(db, user.id)

    html = """
    <style>
        .mini-cal { width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; }
        .mini-cal th { padding: 4px; color: #888; font-weight: 600; }
        .mini-cal td { padding: 6px 2px; position: relative; border-radius: 4px; }
        .mini-cal .selected { border: 2px solid #FF4B4B !important; font-weight: bold; }
        .mini-cal .star { position: absolute; top: 1px; right: 2px; font-size: 9px; color: #FFD700; }
    </style>
    """

    months_ru = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                 "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

    html += f"<div style='text-align: center; font-weight: bold; margin-bottom: 8px;'>"
    html += f"{months_ru[month]} {year}</div>"
    html += "<table class='mini-cal'><thead><tr>"
    for day_head in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
        html += f"<th>{day_head}</th>"
    html += "</tr></thead><tbody>"

    for week in cal:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td></td>"
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                used_min = sum(t.duration_minutes for t in tasks if t.date == date_str and t.status in ["scheduled", "done"])
                pct = min(100, int((used_min / max_minutes) * 100))

                bg_style = ""
                if pct > 0:
                    alpha = min(0.6, (pct / 100) * 0.6)
                    bg_style = f"background-color: rgba(46, 160, 67, {alpha:.2f});"

                classes = []
                if date_str == str(selected_date):
                    classes.append("selected")

                class_attr = f"class='{' '.join(classes)}'" if classes else ""
                star_icon = "<span class='star'>★</span>" if date_str in important_dates else ""

                html += f"<td {class_attr} style='{bg_style}'>{day}{star_icon}</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return html