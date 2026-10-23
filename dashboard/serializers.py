
from rest_framework import serializers
from .models import ScheduleEvent


class ScheduleEventSerializer(serializers.ModelSerializer):
    start_time = serializers.TimeField(format="%I:%M %p")
    end_time = serializers.TimeField(
        format="%I:%M %p",
        allow_null=True,
        required=False,
    )

    class Meta:
        model = ScheduleEvent
        fields = [
            "id",
            "title",
            "designation",
            "event_type",
            "date",
            "start_time",
            "end_time",
            "description",
            "location",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
