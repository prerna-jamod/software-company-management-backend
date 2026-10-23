
from django.urls import path

from .views import (
    register_api,
    login_api,
    send_otp,
    verify_otp,
    forgot_password_api,
    verify_reset_otp_api,
    reset_password_api,
)

urlpatterns = [
    path('send-otp/', send_otp, name='send_otp'),
    path('verify-otp/', verify_otp, name='verify_otp'),
    path('register/', register_api, name='register_api'),
    path('login/', login_api, name='login_api'),
    path('forgot-password/',forgot_password_api,name='forgot_password'),
    path('verify-reset-otp/',verify_reset_otp_api,name='verify_reset_otp'),
    path('reset-password/',reset_password_api,name='reset_password'),
]
