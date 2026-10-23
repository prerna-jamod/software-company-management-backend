from django.utils import timezone
from django.db.models import Q

from rest_framework.decorators import api_view
from rest_framework.response import Response

from employees.models import Employees, EmployeeAttendance
from projects.models import Projects


from datetime import date

from rest_framework import status

from .models import ScheduleEvent
from .serializers import ScheduleEventSerializer




@api_view(["GET"])
def dashboard_summary(request):
    today = timezone.localdate()

    # Total employees
    total_employees = Employees.objects.count()

    # Today's attendance
    today_attendance = EmployeeAttendance.objects.filter(
        attendance_date=today
    )

    total_attendance = today_attendance.count()

    present_count = today_attendance.filter(
        status__in=["On Time", "Late"]
    ).count()

    late_count = today_attendance.filter(
        status="Late"
    ).count()

    attendance_percentage = round(
        (present_count / total_employees) * 100, 2
    ) if total_employees else 0

    # Total projects
    total_projects = Projects.objects.count()

    return Response({
        "date": str(today),
        "total_employees": total_employees,
        "total_applicants": None,
        "total_projects": total_projects,
        "attendance": {
            "total_records": total_attendance,
            "present": present_count,
            "late": late_count,
            "attendance_percentage": attendance_percentage
        },
        "message": (
            "Applicant count will be added after "
            "connecting the applicant model."
        )
    })
    
    
from datetime import timedelta

@api_view(["GET"])
def attendance_overview(request):
    today = timezone.localdate()

    period = request.query_params.get("period", "week")

    if period != "week":
        return Response(
            {"error": "Currently only period=week is supported."},
            status=400,
        )

    week_start = today - timedelta(days=today.weekday())
    total_employees = Employees.objects.count()

    attendance_data = []

    for day_offset in range(7):
        current_date = week_start + timedelta(days=day_offset)

        records = EmployeeAttendance.objects.filter(
            attendance_date=current_date
        )

        present_count = records.filter(
            status__in=["On Time", "Late"]
        ).count()

        percentage = round(
            (present_count / total_employees) * 100, 2
        ) if total_employees else 0

        attendance_data.append({
            "date": str(current_date),
            "day": current_date.strftime("%a"),
            "total_employees": total_employees,
            "present": present_count,
            "percentage": percentage,
        })

    return Response({
        "period": "week",
        "week_start": str(week_start),
        "week_end": str(week_start + timedelta(days=6)),
        "attendance_overview": attendance_data,
    })

    
    
@api_view(["GET"])
def today_attendance(request):
    today = timezone.localdate()

    attendance_records = (
        EmployeeAttendance.objects
        .filter(attendance_date=today)
        .select_related("employee")
        .order_by("check_in", "id")
    )

    attendance_data = []

    for record in attendance_records:
        employee = record.employee

        attendance_data.append({
            "attendance_id": record.id,
            "employee_id": employee.id,
            "employee_name": employee.name,
            "designation": employee.designation,
            "employee_type": employee.employee_type,
            "check_in": (
                record.check_in.strftime("%I:%M %p")
                if record.check_in else None
            ),
            "status": record.status,
            "attendance_date": str(record.attendance_date),
        })

    return Response({
        "date": str(today),
        "total_records": len(attendance_data),
        "attendance": attendance_data,
    })



from employees.models import Holiday, EmployeeLeave


@api_view(["GET"])
def calendar_events(request):
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    holidays = Holiday.objects.all()
    leaves = EmployeeLeave.objects.select_related("employee").all()

    # Optional date-range filtering
    if start_date:
        holidays = holidays.filter(date__gte=start_date)
        leaves = leaves.filter(end_date__gte=start_date)

    if end_date:
        holidays = holidays.filter(date__lte=end_date)
        leaves = leaves.filter(start_date__lte=end_date)

    events = []

    for holiday in holidays:
        events.append({
            "id": f"holiday-{holiday.id}",
            "type": "Holiday",
            "title": holiday.holiday_name,
            "date": str(holiday.date),
            "day": holiday.date.strftime("%A"),
        })

    for leave in leaves:
        events.append({
            "id": f"leave-{leave.id}",
            "type": "Leave",
            "title": f"{leave.employee.name} - Leave",
            "employee_id": leave.employee_id,
            "employee_name": leave.employee.name,
            "start_date": str(leave.start_date),
            "end_date": str(leave.end_date),
            "status": leave.status,
            "reason": leave.reason,
        })

    events.sort(
        key=lambda event: event.get("date", event.get("start_date", ""))
    )

    return Response({
        "total_events": len(events),
        "events": events,
    })

@api_view(["GET", "POST"])
def my_schedule(request):

    # POST: Create a schedule event
    if request.method == "POST":
        serializer = ScheduleEventSerializer(data=request.data)

        if serializer.is_valid():
            event = serializer.save()

            return Response(
                {
                    "message": "Schedule event created successfully.",
                    "event": ScheduleEventSerializer(event).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    # GET: Fetch schedule events
    events = ScheduleEvent.objects.all()

    selected_date = request.query_params.get("date")
    month = request.query_params.get("month")
    year = request.query_params.get("year")

    # Fetch events for one selected date
    if selected_date:
        try:
            parsed_date = date.fromisoformat(selected_date)
        except ValueError:
            return Response(
                {"error": "Use date format YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        events = events.filter(date=parsed_date)

    # Fetch events for a selected month and year
    elif month or year:
        if not month or not year:
            return Response(
                {"error": "Both month and year are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            month_number = int(month)
            year_number = int(year)

            if not 1 <= month_number <= 12:
                raise ValueError

            if not 1 <= year_number <= 9999:
                raise ValueError

        except ValueError:
            return Response(
                {"error": "Provide a valid month (1-12) and year."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        events = events.filter(
            date__year=year_number,
            date__month=month_number,
        )

    events = events.order_by("date", "start_time")
    data = ScheduleEventSerializer(events, many=True).data

    return Response(
        {
            "total_events": len(data),
            "events": data,
        },
        status=status.HTTP_200_OK,
    )
