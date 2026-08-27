import calendar
import utils
from datetime import date


def render_mini_calendar(selected_date: date, user_data: dict) -> str:
    # генерирует HTML-код таблицы мини-календаря с подсветкой загрузки
    year = selected_date.year
    month = selected_date.month

    cal = calendar.monthcalendar(year, month)

    settings = user_data.get("settings", {})
    max_minutes = utils.get_max_work_minutes(settings)
    important_dates = set(user_data.get("important_dates", []))
    tasks = user_data.get("tasks", [])

    # CSS-стилизация под тему Streamlit
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
                html += "<td></td>"  # дни соседних месяцев
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"

                # 1) расчет загруженности (%)
                used_min = utils.get_daily_load_minutes(tasks, date_str)
                pct = min(100, int((used_min / max_minutes) * 100))

                # 2) прозрачность фона зависит от загрузки (зеленый цвет)
                bg_style = ""
                if pct > 0:
                    alpha = min(0.6, (pct / 100) * 0.6)  # максимум 0.6 прозрачности
                    bg_style = f"background-color: rgba(46, 160, 67, {alpha:.2f});"

                # 3) классы для выбранной и важной даты
                classes = []
                if date_str == str(selected_date):
                    classes.append("selected")

                class_attr = f"class='{' '.join(classes)}'" if classes else ""
                star_icon = "<span class='star'>★</span>" if date_str in important_dates else ""

                html += f"<td {class_attr} style='{bg_style}'>{day}{star_icon}</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return html