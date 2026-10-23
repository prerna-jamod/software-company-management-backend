
from django.urls import path
from . import views
from projects.views import employee_projects

urlpatterns = [
    # Create employee / Get all employees
    path(
        "",
        views.employee_list,
        name="employee-list",
    ),

    # Filter employees
    path(
        "filter/",
        views.employee_filter,
        name="employee-filter",
    ),

    # Office employees
    path(
        "filter/office/",
        views.office_employees,
        name="office-employees",
    ),

    # Remote / Work From Home employees
    path(
        "filter/remote/",
        views.remote_employees,
        name="remote-employees",
    ),

    # Employee attendance
    path(
        "<int:employee_id>/attendance/",
        views.employee_attendance,
        name="employee-attendance",
    ),

    # Employee projects
    path(
        "<int:employee_id>/projects/",
        employee_projects,
        name="employee-projects",
    ),

    # Get / Update / Delete a specific employee
    path(
        "<int:employee_id>/",
        views.employee_detail,
        name="employee-detail",
    ),
    
    path(
    "<int:employee_id>/leaves/",
    views.employee_leave_list,
    name="employee_leave_list",
),
path(
    "leaves/<int:leave_id>/",
    views.employee_leave_detail,
    name="employee_leave_detail",
),
# Holiday list / Add new holiday
path(
    "holidays/",
    views.holiday_list,
    name="holiday-list",
),
path(
    "notifications/",
    views.notification_list,
    name="notification_list",
),
path(
    "notifications/<int:notification_id>/",
    views.notification_detail,
    name="notification_detail",
),
]
