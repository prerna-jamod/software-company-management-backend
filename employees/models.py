
from django.db import models


# 1. Common Employee Table
class Employees(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=100)

    salary = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    joining_date = models.DateField(null=True, blank=True)

    employee_id = models.CharField(
        max_length=30, unique=True, null=True, blank=True
    )
    employee_type = models.CharField(max_length=30, blank=True)

    ROLE_CHOICES = [
        ("Employee", "Employee"),
        ("HR", "HR"),
        ("Team Leader", "Team Leader"),
        ("Admin", "Admin"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="Employee"
    )
 
    status = models.CharField(max_length=30, default="Permanent")

    profile_image = models.ImageField(
        upload_to="profile_images/",
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name


# 2. Personal Information Table
class EmployeePersonalInfo(models.Model):
    employee = models.OneToOneField(
        Employees,
        on_delete=models.CASCADE,
        related_name="personal_info"
    )

    mobile_number = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    marital_status = models.CharField(max_length=30, blank=True)
    gender = models.CharField(max_length=30, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return f"Personal Info - {self.employee.name}"


# 3. Professional Information Table
class EmployeeProfessionalInfo(models.Model):
    employee = models.OneToOneField(
        Employees,
        on_delete=models.CASCADE,
        related_name="professional_info"
    )

    username = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )
    working_days = models.JSONField(default=list, blank=True)
    office_location = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"Professional Info - {self.employee.name}"


# 4. Employee Documents Table
class EmployeeDocument(models.Model):
    DOCUMENT_CHOICES = [
        ("appointment_letter", "Appointment Letter"),
        ("salary_slip", "Salary Slip"),
        ("relieving_letter", "Relieving Letter"),
        ("experience_letter", "Experience Letter"),
    ]

    employee = models.ForeignKey(
        Employees,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_CHOICES
    )

    file = models.FileField(upload_to="employee_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.name} - {self.document_type}"


# 5. Account Access Table
class EmployeeAccountAccess(models.Model):
    employee = models.OneToOneField(
        Employees,
        on_delete=models.CASCADE,
        related_name="account_access"
    )

    email = models.EmailField(blank=True)
    slack_id = models.CharField(max_length=150, blank=True)
    skype_id = models.CharField(max_length=150, blank=True)
    github_id = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"Account Access - {self.employee.name}"


# 6. NEW: Employee Attendance Table
class EmployeeAttendance(models.Model):

    ATTENDANCE_STATUS = [
        ("On Time", "On Time"),
        ("Late", "Late"),
        ("Absent", "Absent"),
        ("Leave", "Leave"),
    ]

    employee = models.ForeignKey(
        Employees,
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )

    attendance_date = models.DateField()

    check_in = models.TimeField(
        null=True,
        blank=True
    )

    check_out = models.TimeField(
        null=True,
        blank=True
    )

    # Break duration in minutes
    break_minutes = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_STATUS,
        default="On Time"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-attendance_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "attendance_date"],
                name="unique_employee_attendance_per_day"
            )
        ]

    def __str__(self):
        return (
            f"{self.employee.name} - "
            f"{self.attendance_date} - {self.status}"
        )


# 7. Employees Leaves Detail


class EmployeeLeave(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    employee = models.ForeignKey(
        Employees,
        on_delete=models.CASCADE,
        related_name="leaves"
    )

    applied_date = models.DateField(auto_now_add=True)
    start_date = models.DateField()
    end_date = models.DateField()

    days = models.PositiveIntegerField(default=0)

    reporting_manager = models.CharField(max_length=100)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    reason = models.TextField(blank=True, default="")

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.days = max(
                0, (self.end_date - self.start_date).days
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.name} - {self.status}"


# 8. Holiday Management Table
class Holiday(models.Model):
    holiday_name = models.CharField(max_length=150)
    date = models.DateField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]

    @property
    def day(self):
        return self.date.strftime("%A")

    def __str__(self):
        return f"{self.holiday_name} - {self.date}"



class Notification(models.Model):
    CATEGORY_CHOICES = [
        ("Leaves", "Leaves"),
        ("Attendance", "Attendance"),
        ("Jobs", "Jobs"),
        ("Candidates", "Candidates"),
        ("Feedback", "Feedback"),
        ("Security", "Security"),
        ("General", "General"),
    ]

    recipient = models.ForeignKey(
        Employees,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True
    )
    sender_name = models.CharField(max_length=150, blank=True, default="")
    title = models.CharField(max_length=200)
    message = models.TextField()
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="General"
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
