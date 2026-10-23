
from django.db import models


class EmailOTP(models.Model):

    OTP_PURPOSE_CHOICES = [
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
    ]

    email = models.EmailField(db_index=True)

    otp_hash = models.CharField(max_length=128)

    purpose = models.CharField(
        max_length=20,
        choices=OTP_PURPOSE_CHOICES,
        default='registration'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField()

    is_verified = models.BooleanField(default=False)

    attempts = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"{self.email} - {self.purpose}"
