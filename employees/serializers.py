from datetime import datetime, timedelta

from rest_framework import serializers

from .models import (
    Employees,
    EmployeePersonalInfo,
    EmployeeProfessionalInfo,
    EmployeeDocument,
    EmployeeAccountAccess,
    EmployeeAttendance,
    EmployeeLeave,
)


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocument
        fields = [
            "id",
            "document_type",
            "file",
            "uploaded_at",
        ]
        read_only_fields = ["id", "uploaded_at"]


class EmployeePersonalInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeePersonalInfo
        exclude = ["employee"]


class EmployeeProfessionalInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeProfessionalInfo
        exclude = ["employee"]


class EmployeeAccountAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeAccountAccess
        exclude = ["employee"]


# Employee profile serializer
class EmployeeSerializer(serializers.ModelSerializer):
    personal_info = EmployeePersonalInfoSerializer(read_only=True)
    professional_info = EmployeeProfessionalInfoSerializer(read_only=True)
    account_access = EmployeeAccountAccessSerializer(read_only=True)
    documents = EmployeeDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Employees
        fields = "__all__"


# Attendance serializer
class EmployeeAttendanceSerializer(serializers.ModelSerializer):

    attendance_date = serializers.DateField(
        format="%B %d, %Y"
    )

    check_in = serializers.TimeField(
        format="%I:%M %p",
        allow_null=True,
        required=False
    )

    check_out = serializers.TimeField(
        format="%I:%M %p",
        allow_null=True,
        required=False
    )

    break_duration = serializers.SerializerMethodField()
    working_hours = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeAttendance
        fields = [
            "id",
            "attendance_date",
            "check_in",
            "check_out",
            "break_duration",
            "working_hours",
            "status",
            "break_minutes",
        ]
        read_only_fields = [
            "id",
            "break_duration",
            "working_hours",
        ]

    def get_break_duration(self, obj):
        hours, minutes = divmod(obj.break_minutes, 60)
        return f"{hours:02d}:{minutes:02d} Min"

    def get_working_hours(self, obj):

        # Incomplete or absent attendance
        if (
            obj.status in ["Absent", "Leave"]
            or obj.check_in is None
            or obj.check_out is None
        ):
            return "00:00 Hrs"

        start = datetime.combine(
            obj.attendance_date,
            obj.check_in
        )

        end = datetime.combine(
            obj.attendance_date,
            obj.check_out
        )

        # Support shifts ending after midnight
        if end < start:
            end += timedelta(days=1)

        total_seconds = int(
            (end - start).total_seconds()
        )

        # Deduct break duration
        total_seconds -= obj.break_minutes * 60
        total_seconds = max(0, total_seconds)

        total_minutes = total_seconds // 60
        hours, minutes = divmod(total_minutes, 60)

        return f"{hours:02d}:{minutes:02d} Hrs"


class EmployeeLeaveSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source="employee.name", read_only=True
    )
    employee_email = serializers.EmailField(
        source="employee.email", read_only=True
    )
    designation = serializers.CharField(
        source="employee.designation", read_only=True
    )

    class Meta:
        model = EmployeeLeave
        fields = [
            "id",
            "employee",
            "employee_name",
            "employee_email",
            "designation",
            "applied_date",
            "start_date",
            "end_date",
            "days",
            "reporting_manager",
            "status",
            "reason",
        ]
        read_only_fields = [
            "id",
            "applied_date",
            "days",
        ]

    def validate(self, data):
        start_date = data.get(
            "start_date",
            getattr(self.instance, "start_date", None)
        )
        end_date = data.get(
            "end_date",
            getattr(self.instance, "end_date", None)
        )

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError({
                "end_date": "End date must be after start date."
            })

        return data
