import os
import json

from django.db import transaction
from django.db.models import Q

from django.utils import timezone
from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import (
    Employees,
    EmployeePersonalInfo,
    EmployeeProfessionalInfo,
    EmployeeDocument,
    EmployeeAccountAccess,
    EmployeeAttendance,
    EmployeeLeave,
    Holiday,
    Notification,
)

from .serializers import (
    EmployeeSerializer,
    EmployeePersonalInfoSerializer,
    EmployeeProfessionalInfoSerializer,
    EmployeeAccountAccessSerializer,
    EmployeeAttendanceSerializer,
     EmployeeLeaveSerializer,
)


# --------------------------------------------------
# FILE VALIDATION
# --------------------------------------------------

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_IMAGE_SIZE = 2 * 1024 * 1024


def validate_upload(uploaded_file, allowed_extensions, max_size):
    extension = os.path.splitext(uploaded_file.name)[1].lower()

    if extension not in allowed_extensions:
        return "Unsupported file extension."

    if uploaded_file.size == 0:
        return "Uploaded file is empty."

    if uploaded_file.size > max_size:
        return "File size exceeds the allowed limit."

    return None


# --------------------------------------------------
# PAGINATION
# --------------------------------------------------

class EmployeePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def get_paginated_employees(request, employees):
    paginator = EmployeePagination()
    page = paginator.paginate_queryset(employees, request)

    serializer = EmployeeSerializer(
        page,
        many=True,
        context={"request": request},
    )

    return paginator.get_paginated_response(serializer.data)


# --------------------------------------------------
# CREATE EMPLOYEE / GET ALL EMPLOYEES
# --------------------------------------------------

@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser])
def employee_list(request):

    if request.method == "GET":
        employees = Employees.objects.all().order_by("-id")
        return get_paginated_employees(request, employees)

    data = request.data
    profile_image = request.FILES.get("profile_image")

    # Profile image is mandatory when creating an employee
    if not profile_image:
        return Response(
            {"error": "Profile image is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    error = validate_upload(
        profile_image,
        ALLOWED_IMAGE_EXTENSIONS,
        MAX_IMAGE_SIZE,
    )

    if error:
        return Response(
            {"error": f"Profile image: {error}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    name = data.get("name", "").strip()

    if not name:
        name = f"{first_name} {last_name}".strip()

    email = data.get("email", "").strip().lower()

    if not name or not email:
        return Response(
            {"error": "Employee name and email are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    common_data = {
        "name": name,
        "email": email,
        "employee_id": data.get("employee_id") or None,
        "employee_type": data.get("employee_type", "").strip(),
        "department": data.get("department", "").strip(),
        "designation": data.get("designation", "").strip(),
        "joining_date": data.get("joining_date") or None,
        "salary": data.get("salary") or 0,
        "status": data.get("status", "Permanent").strip(),
        "profile_image": profile_image,
    }

    personal_data = {
        "mobile_number": data.get("mobile_number", "").strip(),
        "date_of_birth": data.get("date_of_birth") or None,
        "marital_status": data.get("marital_status", "").strip(),
        "gender": data.get("gender", "").strip(),
        "nationality": data.get("nationality", "").strip(),
        "address": data.get("address", "").strip(),
        "city": data.get("city", "").strip(),
        "state": data.get("state", "").strip(),
        "zip_code": data.get("zip_code", "").strip(),
    }

    working_days_input = data.get("working_days", "[]")

    try:
        working_days = json.loads(working_days_input)

        if not isinstance(working_days, list):
            return Response(
                {"error": "working_days must be a JSON list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except (TypeError, json.JSONDecodeError):
        working_days = [
            day.strip()
            for day in working_days_input.split(",")
            if day.strip()
        ]

    professional_data = {
        "username": data.get("username") or None,
        "working_days": working_days,
        "office_location": data.get("office_location", "").strip(),
    }

    account_data = {
        "email": data.get("account_email", email).strip().lower(),
        "slack_id": data.get("slack_id", "").strip(),
        "skype_id": data.get("skype_id", "").strip(),
        "github_id": data.get("github_id", "").strip(),
    }

    document_fields = [
        ("appointment_letter", "appointment_letter"),
        ("salary_slips", "salary_slip"),
        ("relieving_letter", "relieving_letter"),
        ("experience_letter", "experience_letter"),
    ]

    files_to_save = []

    for form_key, document_type in document_fields:
        if form_key == "salary_slips":
            uploaded_files = request.FILES.getlist(form_key)
        else:
            uploaded_file = request.FILES.get(form_key)
            uploaded_files = [uploaded_file] if uploaded_file else []

        for uploaded_file in uploaded_files:
            error = validate_upload(
                uploaded_file,
                ALLOWED_EXTENSIONS,
                MAX_FILE_SIZE,
            )

            if error:
                return Response(
                    {"error": f"{uploaded_file.name}: {error}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            files_to_save.append((document_type, uploaded_file))

    try:
        with transaction.atomic():

            employee_serializer = EmployeeSerializer(data=common_data)
            employee_serializer.is_valid(raise_exception=True)
            employee = employee_serializer.save()

            personal_serializer = EmployeePersonalInfoSerializer(
                data=personal_data
            )
            personal_serializer.is_valid(raise_exception=True)

            EmployeePersonalInfo.objects.create(
                employee=employee,
                **personal_serializer.validated_data,
            )

            professional_serializer = EmployeeProfessionalInfoSerializer(
                data=professional_data
            )
            professional_serializer.is_valid(raise_exception=True)

            EmployeeProfessionalInfo.objects.create(
                employee=employee,
                **professional_serializer.validated_data,
            )

            account_serializer = EmployeeAccountAccessSerializer(
                data=account_data
            )
            account_serializer.is_valid(raise_exception=True)

            EmployeeAccountAccess.objects.create(
                employee=employee,
                **account_serializer.validated_data,
            )

            for document_type, uploaded_file in files_to_save:
                EmployeeDocument.objects.create(
                    employee=employee,
                    document_type=document_type,
                    file=uploaded_file,
                )

    except Exception:
        return Response(
            {
                "error": (
                    "Employee could not be created. "
                    "Check required fields, duplicate email/ID, "
                    "username and submitted data."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        EmployeeSerializer(
            employee,
            context={"request": request},
        ).data,
        status=status.HTTP_201_CREATED,
    )


# --------------------------------------------------
# FILTER EMPLOYEES
# --------------------------------------------------

@api_view(["GET"])
def employee_filter(request):
    employees = Employees.objects.all()

    department = request.query_params.get("department", "").strip()
    employee_type = request.query_params.get("type", "").strip()
    search = request.query_params.get("search", "").strip()

    if department:
        employees = employees.filter(department__iexact=department)

    if employee_type:
        normalized_type = employee_type.lower().replace("-", " ").strip()

        if normalized_type == "office":
            employees = employees.filter(employee_type__iexact="Office")

        elif normalized_type in ["work from home", "remote", "wfh"]:
            employees = employees.filter(
                Q(employee_type__iexact="Work from Home")
                | Q(employee_type__iexact="Remote")
                | Q(employee_type__iexact="WFH")
            )

        else:
            return Response(
                {"error": "Use type=Office or type=Work from Home."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if search:
        employees = employees.filter(
            Q(name__icontains=search)
            | Q(employee_id__icontains=search)
            | Q(email__icontains=search)
        )

    response = get_paginated_employees(
        request,
        employees.order_by("-id"),
    )

    response.data["filters"] = {
        "department": department or None,
        "type": employee_type or None,
        "search": search or None,
    }

    return response


# --------------------------------------------------
# OFFICE EMPLOYEES
# --------------------------------------------------

@api_view(["GET"])
def office_employees(request):
    employees = Employees.objects.filter(
        employee_type__iexact="Office"
    ).order_by("-id")

    return get_paginated_employees(request, employees)


# --------------------------------------------------
# REMOTE EMPLOYEES
# --------------------------------------------------

@api_view(["GET"])
def remote_employees(request):
    employees = Employees.objects.filter(
        Q(employee_type__iexact="Work from Home")
        | Q(employee_type__iexact="Remote")
        | Q(employee_type__iexact="WFH")
    ).order_by("-id")

    return get_paginated_employees(request, employees)


# --------------------------------------------------
# GET / UPDATE / DELETE ONE EMPLOYEE
# --------------------------------------------------

@api_view(["GET", "PUT", "PATCH", "DELETE"])
@parser_classes([MultiPartParser, FormParser])
def employee_detail(request, employee_id):

    employee = get_object_or_404(Employees, id=employee_id)

    if request.method == "GET":
        serializer = EmployeeSerializer(
            employee,
            context={"request": request},
        )
        return Response(serializer.data)

    if request.method in ["PUT", "PATCH"]:

        new_image = request.FILES.get("profile_image")

        if new_image:
            error = validate_upload(
                new_image,
                ALLOWED_IMAGE_EXTENSIONS,
                MAX_IMAGE_SIZE,
            )

            if error:
                return Response(
                    {"error": f"Profile image: {error}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        document_fields = [
            "appointment_letter",
            "salary_slips",
            "relieving_letter",
            "experience_letter",
        ]

        for field_name in document_fields:
            if field_name == "salary_slips":
                uploaded_files = request.FILES.getlist(field_name)
            else:
                uploaded_file = request.FILES.get(field_name)
                uploaded_files = [uploaded_file] if uploaded_file else []

            for uploaded_file in uploaded_files:
                error = validate_upload(
                    uploaded_file,
                    ALLOWED_EXTENSIONS,
                    MAX_FILE_SIZE,
                )

                if error:
                    return Response(
                        {"error": f"{uploaded_file.name}: {error}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        serializer = EmployeeSerializer(
            employee,
            data=request.data,
            partial=(request.method == "PATCH"),
            context={"request": request},
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    employee.delete()

    return Response(
        {"message": "Employee deleted successfully."},
        status=status.HTTP_200_OK,
    )


# --------------------------------------------------
# NEW: EMPLOYEE ATTENDANCE API
# GET: View records
# POST: Create a record
# --------------------------------------------------

@api_view(["GET", "POST"])
def employee_attendance(request, employee_id):

    employee = get_object_or_404(Employees, id=employee_id)

    if request.method == "GET":
        records = EmployeeAttendance.objects.filter(
            employee=employee
        ).order_by("-attendance_date")

        serializer = EmployeeAttendanceSerializer(
            records,
            many=True,
        )

        return Response({
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "email": employee.email,
            },
            "count": records.count(),
            "attendance": serializer.data,
        })

    serializer = EmployeeAttendanceSerializer(data=request.data)

    if serializer.is_valid():
        try:
            serializer.save(employee=employee)

        except Exception:
            return Response(
                {
                    "error": (
                        "Attendance could not be saved. "
                        "A record for this employee and date may "
                        "already exist."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Attendance saved successfully.",
                "attendance": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )


# --------------------------------------------------
# EMPLOYEE LEAVE LIST / CREATE
# Automatically notifies all HR employees on leave application
# --------------------------------------------------

@api_view(["GET", "POST"])
def employee_leave_list(request, employee_id):
    employee = get_object_or_404(Employees, id=employee_id)

    # GET: List employee leaves
    if request.method == "GET":
        leaves = EmployeeLeave.objects.filter(
            employee=employee
        ).order_by("-applied_date", "-id")

        leave_status = request.query_params.get(
            "status", ""
        ).strip()

        if leave_status:
            allowed_statuses = [
                "Pending", "Approved", "Rejected"
            ]

            if leave_status not in allowed_statuses:
                return Response(
                    {
                        "error": (
                            "Invalid status. Use Pending, "
                            "Approved, or Rejected."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            leaves = leaves.filter(status=leave_status)

        serializer = EmployeeLeaveSerializer(
            leaves,
            many=True,
        )

        return Response(
            {
                "employee_id": employee.id,
                "employee_name": employee.name,
                "count": leaves.count(),
                "leaves": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    # POST: Apply for leave
    serializer = EmployeeLeaveSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        leave = serializer.save(employee=employee)

        # Notify HR, Team Leader and Admin
        recipients = Employees.objects.filter(
            role__in=["HR", "Team Leader", "Admin"]
        ).exclude(id=employee.id)

        notifications = [
            Notification(
                recipient=recipient,
                sender_name=employee.name,
                title="Leave Request",
                message=(
                    f"{employee.name} has applied for leave."
                ),
                category="Leaves",
            )
            for recipient in recipients
        ]

        if notifications:
            Notification.objects.bulk_create(notifications)

    return Response(
        {
            "message": "Leave request created successfully.",
            "leave": EmployeeLeaveSerializer(leave).data,
            "notifications_created": len(notifications),
        },
        status=status.HTTP_201_CREATED,
    )

# --------------------------------------------------
# GET / APPROVE / REJECT / DELETE LEAVE
# Automatically notifies employee when leave is approved/rejected
# --------------------------------------------------

@api_view(["GET", "PATCH", "DELETE"])
def employee_leave_detail(request, leave_id):
    leave = get_object_or_404(EmployeeLeave, id=leave_id)

    if request.method == "GET":
        return Response(
            EmployeeLeaveSerializer(leave).data,
            status=status.HTTP_200_OK,
        )

    if request.method == "PATCH":
        new_status = request.data.get("status")

        if new_status not in ["Approved", "Rejected"]:
            return Response(
                {"error": "Status must be Approved or Rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if leave.status != "Pending":
            return Response(
                {
                    "error": (
                        "Only Pending leave requests can "
                        "be approved or rejected."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee = leave.employee

        with transaction.atomic():
            leave.status = new_status
            leave.save(update_fields=["status"])

            action = new_status.lower()

            Notification.objects.create(
                recipient=employee,
                sender_name="HR Team",
                title=f"Leave {new_status}",
                message=(
                    f"Your leave request has been {action}."
                ),
                category="Leaves",
            )

        return Response(
            {
                "message": f"Leave request {action} successfully.",
                "leave": EmployeeLeaveSerializer(leave).data,
            },
            status=status.HTTP_200_OK,
        )

    leave.delete()

    return Response(
        {"message": "Leave deleted successfully."},
        status=status.HTTP_200_OK,
    )


# --------------------------------------------------
# HOLIDAY LIST / ADD NEW HOLIDAY API
# GET: List, search, upcoming and past holidays
# POST: Add a new holiday
# --------------------------------------------------

@api_view(["GET", "POST"])
def holiday_list(request):

    # GET: Retrieve holidays
    if request.method == "GET":
        holidays = Holiday.objects.all().order_by("date")

        # Search by holiday name
        search = request.query_params.get("search", "").strip()

        if search:
            holidays = holidays.filter(
                holiday_name__icontains=search
            )

        # Filter: all, upcoming or past
        holiday_type = request.query_params.get(
            "type", "all"
        ).strip().lower()

        today = timezone.localdate()

        if holiday_type == "upcoming":
            holidays = holidays.filter(date__gte=today)

        elif holiday_type == "past":
            holidays = holidays.filter(date__lt=today)

        elif holiday_type != "all":
            return Response(
                {
                    "error": (
                        "Invalid type. Use all, upcoming, or past."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        holiday_data = [
            {
                "id": holiday.id,
                "holiday_name": holiday.holiday_name,
                "date": holiday.date.isoformat(),
                "day": holiday.day,
            }
            for holiday in holidays
        ]

        return Response(
            {
                "count": len(holiday_data),
                "type": holiday_type,
                "search": search or None,
                "holidays": holiday_data,
            },
            status=status.HTTP_200_OK,
        )

    # POST: Create a new holiday
    holiday_name = request.data.get(
        "holiday_name", ""
    ).strip()

    date_input = request.data.get("date", "").strip()

    if not holiday_name:
        return Response(
            {"error": "Holiday name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not date_input:
        return Response(
            {"error": "Holiday date is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    holiday_date = parse_date(date_input)

    if holiday_date is None:
        return Response(
            {
                "error": (
                    "Invalid date format. Use YYYY-MM-DD."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if Holiday.objects.filter(date=holiday_date).exists():
        return Response(
            {
                "error": (
                    "A holiday already exists for this date."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    holiday = Holiday.objects.create(
        holiday_name=holiday_name,
        date=holiday_date,
    )

    return Response(
        {
            "message": "Holiday added successfully.",
            "holiday": {
                "id": holiday.id,
                "holiday_name": holiday.holiday_name,
                "date": holiday.date.isoformat(),
                "day": holiday.day,
            },
        },
        status=status.HTTP_201_CREATED,
    )



# --------------------------------------------------
# NOTIFICATION LIST / CREATE API
# GET: List, search, filter, pagination
# POST: Create notification
# --------------------------------------------------

class NotificationPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def notification_to_dict(notification):
    return {
        "id": notification.id,
        "recipient": notification.recipient_id,
        "sender_name": notification.sender_name,
        "title": notification.title,
        "message": notification.message,
        "category": notification.category,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
    }


@api_view(["GET", "POST"])
def notification_list(request):

    # GET: List notifications
    if request.method == "GET":
        notifications = Notification.objects.select_related(
            "recipient"
        ).all()

        # Optional employee-specific notifications
        recipient_id = request.query_params.get("recipient_id", "").strip()

        if recipient_id:
            if not recipient_id.isdigit():
                return Response(
                    {"error": "recipient_id must be a valid integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            notifications = notifications.filter(
                recipient_id=int(recipient_id)
            )

        # Search title, message, sender or category
        search = request.query_params.get("search", "").strip()

        if search:
            notifications = notifications.filter(
                Q(title__icontains=search)
                | Q(message__icontains=search)
                | Q(sender_name__icontains=search)
                | Q(category__icontains=search)
            )

        # Filter by category
        category = request.query_params.get("category", "").strip()

        if category:
            valid_categories = dict(
                Notification.CATEGORY_CHOICES
            )

            matched_category = next(
                (
                    key for key in valid_categories
                    if key.lower() == category.lower()
                ),
                None,
            )

            if not matched_category:
                return Response(
                    {
                        "error": "Invalid category.",
                        "allowed_categories": list(valid_categories.keys()),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            notifications = notifications.filter(
                category=matched_category
            )

        # Filter unread / read notifications
        unread = request.query_params.get("unread", "").lower()

        if unread in ["true", "1", "yes"]:
            notifications = notifications.filter(is_read=False)

        elif unread in ["false", "0", "no"]:
            notifications = notifications.filter(is_read=True)

        elif unread:
            return Response(
                {"error": "Use unread=true or unread=false."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Paginate results
        paginator = NotificationPagination()
        page = paginator.paginate_queryset(
            notifications.order_by("-created_at", "-id"),
            request,
        )

        data = [
            notification_to_dict(item)
            for item in page
        ]

        response = paginator.get_paginated_response(data)

        response.data["unread_count"] = notifications.filter(
            is_read=False
        ).count()

        response.data["filters"] = {
            "recipient_id": recipient_id or None,
            "search": search or None,
            "category": category or None,
            "unread": unread or None,
        }

        return response

    # POST: Create a notification
    data = request.data

    title = data.get("title", "").strip()
    message = data.get("message", "").strip()
    sender_name = data.get("sender_name", "").strip()
    category = data.get("category", "General").strip()

    if not title or not message:
        return Response(
            {"error": "Title and message are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    valid_categories = dict(Notification.CATEGORY_CHOICES)

    matched_category = next(
        (
            key for key in valid_categories
            if key.lower() == category.lower()
        ),
        None,
    )

    if not matched_category:
        return Response(
            {
                "error": "Invalid category.",
                "allowed_categories": list(valid_categories.keys()),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    recipient = None
    recipient_id = data.get("recipient_id")

    if recipient_id not in [None, ""]:
        if not str(recipient_id).isdigit():
            return Response(
                {"error": "recipient_id must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recipient = get_object_or_404(
            Employees,
            id=int(recipient_id),
        )

    notification = Notification.objects.create(
        recipient=recipient,
        sender_name=sender_name,
        title=title,
        message=message,
        category=matched_category,
    )

    return Response(
        {
            "message": "Notification created successfully.",
            "notification": notification_to_dict(notification),
        },
        status=status.HTTP_201_CREATED,
    )


# --------------------------------------------------
# GET / MARK ONE NOTIFICATION AS READ
# --------------------------------------------------

@api_view(["GET", "PATCH"])
def notification_detail(request, notification_id):

    notification = get_object_or_404(
        Notification,
        id=notification_id,
    )

    if request.method == "GET":
        return Response(
            notification_to_dict(notification),
            status=status.HTTP_200_OK,
        )

    notification.is_read = True
    notification.save(update_fields=["is_read"])

    return Response(
        {
            "message": "Notification marked as read.",
            "notification": notification_to_dict(notification),
        },
        status=status.HTTP_200_OK,
    )
