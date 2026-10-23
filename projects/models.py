
from django.db import models
from employees.models import Employees


class Projects(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=50)

    # Existing field retained for compatibility
    employee_name = models.CharField(max_length=100)

    # Link project with an employee
    employee = models.ForeignKey(
        Employees,
        on_delete=models.CASCADE,
        related_name="projects",
        null=True,
        blank=True
    )

    start_date = models.DateField(null=True, blank=True)
    finish_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name
