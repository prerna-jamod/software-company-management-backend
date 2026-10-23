
from django.urls import path

from .views import calendar_events

from .views import (
    dashboard_summary,
    attendance_overview,
    today_attendance,
    my_schedule,
)

urlpatterns = [
    path("summary/", dashboard_summary, name="dashboard-summary"),
    path(
        "attendance-overview/",
        attendance_overview,
        name="attendance-overview",
    ),
    path(
        "today-attendance/",
        today_attendance,
        name="today-attendance",
    ),
path(
    "calendar-events/",
    calendar_events,
    name="calendar-events",
),

path(
    "my-schedule/",
    my_schedule,
    name="my-schedule",
),
]
