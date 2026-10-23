
from django.db import models


class ScheduleEvent(models.Model):

    EVENT_TYPES = [
        ("Interview", "Interview"),
        ("Meeting", "Meeting"),
        ("Review", "Review"),
        ("Other", "Other"),
    ]

    title = models.CharField(max_length=200)
    designation = models.CharField(max_length=100)
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPES,
        default="Other",
    )

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)

    description = models.TextField(blank=True, default="")
    location = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.title} - {self.date}"
