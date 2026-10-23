import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer
from .models import EmailOTP


# Helper: Send OTP email
def send_otp_email(email, otp, subject, purpose):
    return send_mail(
        subject=subject,
        message=(
            f"Your OTP is {otp}. "
            "It expires in 5 minutes. "
            "If you did not request this, please ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False
    )


# 1. Registration API
@api_view(['POST'])
def register_api(request):
    email = request.data.get('email', '').strip().lower()

    if not email:
        return Response(
            {"message": "Email is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    otp_record = EmailOTP.objects.filter(
        email__iexact=email,
        purpose='registration',
        is_verified=True
    ).order_by('-created_at').first()

    if not otp_record:
        return Response(
            {"message": "Please verify your email before registration"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(email__iexact=email).exists():
        return Response(
            {"message": "Email is already registered"},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        otp_record.delete()

        return Response({
            "message": "Registration successful",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }, status=status.HTTP_201_CREATED)

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


# 2. Login API with JWT
@api_view(['POST'])
def login_api(request):
    email = request.data.get('email', '').strip().lower()
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {"message": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user_obj = User.objects.filter(email__iexact=email).first()

    if not user_obj:
        return Response(
            {"message": "Invalid email or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    user = authenticate(
        request,
        username=user_obj.username,
        password=password
    )

    if user is None:
        return Response(
            {"message": "Invalid email or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    refresh = RefreshToken.for_user(user)

    return Response({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        },
        "tokens": {
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }
    }, status=status.HTTP_200_OK)


# 3. Registration: Send OTP
@api_view(['POST'])
def send_otp(request):
    email = request.data.get('email', '').strip().lower()

    if not email:
        return Response(
            {"message": "Email is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(email__iexact=email).exists():
        return Response(
            {"message": "Email is already registered"},
            status=status.HTTP_400_BAD_REQUEST
        )

    EmailOTP.objects.filter(
        email__iexact=email,
        purpose='registration',
        is_verified=False
    ).delete()

    otp = f"{secrets.randbelow(1000000):06d}"

    otp_record = EmailOTP.objects.create(
        email=email,
        otp_hash=make_password(otp),
        purpose='registration',
        expires_at=timezone.now() + timedelta(minutes=5)
    )

    try:
        send_otp_email(
            email,
            otp,
            "Your Email Verification OTP",
            "registration"
        )
    except Exception:
        otp_record.delete()

        return Response(
            {"message": "Unable to send OTP email"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return Response(
        {"message": "OTP sent successfully. Please check your email."},
        status=status.HTTP_200_OK
    )


# 4. Registration: Verify OTP
@api_view(['POST'])
def verify_otp(request):
    email = request.data.get('email', '').strip().lower()
    otp = request.data.get('otp', '').strip()

    if not email or not otp:
        return Response(
            {"message": "Email and OTP are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not otp.isdigit() or len(otp) != 6:
        return Response(
            {"message": "OTP must contain 6 digits"},
            status=status.HTTP_400_BAD_REQUEST
        )

    otp_record = EmailOTP.objects.filter(
        email__iexact=email,
        purpose='registration',
        is_verified=False
    ).order_by('-created_at').first()

    if not otp_record:
        return Response(
            {"message": "No active OTP found. Please request a new OTP."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if timezone.now() >= otp_record.expires_at:
        otp_record.delete()
        return Response(
            {"message": "OTP expired. Please request a new OTP."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if otp_record.attempts >= 5:
        otp_record.delete()
        return Response(
            {"message": "Too many attempts. Please request a new OTP."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    otp_record.attempts += 1
    otp_record.save(update_fields=['attempts'])

    if not check_password(otp, otp_record.otp_hash):
        return Response(
            {"message": "Invalid OTP"},
            status=status.HTTP_400_BAD_REQUEST
        )

    otp_record.is_verified = True
    otp_record.save(update_fields=['is_verified'])

    return Response(
        {"message": "Email verified successfully"},
        status=status.HTTP_200_OK
    )


# 5. Forgot Password: Send reset OTP
@api_view(['POST'])
def forgot_password_api(request):
    email = request.data.get('email', '').strip().lower()

    if not email:
        return Response(
            {"message": "Email is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Same response for registered and unregistered emails
    response_message = (
        "If the email is registered, a password reset OTP will be sent."
    )

    user = User.objects.filter(email__iexact=email).first()

    if not user:
        return Response(
            {"message": response_message},
            status=status.HTTP_200_OK
        )

    # Delete only previous unused password-reset OTPs
    EmailOTP.objects.filter(
        email__iexact=email,
        purpose='password_reset',
        is_verified=False
    ).delete()

    otp = f"{secrets.randbelow(1000000):06d}"

    otp_record = EmailOTP.objects.create(
        email=email,
        otp_hash=make_password(otp),
        purpose='password_reset',
        expires_at=timezone.now() + timedelta(minutes=5)
    )

    try:
        send_otp_email(
            email,
            otp,
            "Password Reset OTP",
            "password_reset"
        )
    except Exception:
        otp_record.delete()

        return Response(
            {"message": "Unable to send OTP email"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return Response(
        {"message": response_message},
        status=status.HTTP_200_OK
    )


# 6. Forgot Password: Verify reset OTP
@api_view(['POST'])
def verify_reset_otp_api(request):
    email = request.data.get('email', '').strip().lower()
    otp = request.data.get('otp', '').strip()

    if not email or not otp:
        return Response(
            {"message": "Email and OTP are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not otp.isdigit() or len(otp) != 6:
        return Response(
            {"message": "OTP must contain 6 digits"},
            status=status.HTTP_400_BAD_REQUEST
        )

    otp_record = EmailOTP.objects.filter(
        email__iexact=email,
        purpose='password_reset',
        is_verified=False
    ).order_by('-created_at').first()

    if not otp_record:
        return Response(
            {"message": "No active reset OTP found"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if timezone.now() >= otp_record.expires_at:
        otp_record.delete()
        return Response(
            {"message": "OTP expired. Please request a new OTP."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if otp_record.attempts >= 5:
        otp_record.delete()
        return Response(
            {"message": "Too many attempts. Please request a new OTP."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    otp_record.attempts += 1
    otp_record.save(update_fields=['attempts'])

    if not check_password(otp, otp_record.otp_hash):
        return Response(
            {"message": "Invalid OTP"},
            status=status.HTTP_400_BAD_REQUEST
        )

    otp_record.is_verified = True
    otp_record.save(update_fields=['is_verified'])

    return Response(
        {"message": "Reset OTP verified successfully"},
        status=status.HTTP_200_OK
    )


# 7. Forgot Password: Set new password
@api_view(['POST'])
def reset_password_api(request):
    email = request.data.get('email', '').strip().lower()
    new_password = request.data.get('new_password', '')
    confirm_password = request.data.get('confirm_password', '')

    if not email or not new_password or not confirm_password:
        return Response(
            {"message": "Email, new password and confirmation are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if new_password != confirm_password:
        return Response(
            {"message": "Passwords do not match"},
            status=status.HTTP_400_BAD_REQUEST
        )

    otp_record = EmailOTP.objects.filter(
        email__iexact=email,
        purpose='password_reset',
        is_verified=True
    ).order_by('-created_at').first()

    if not otp_record:
        return Response(
            {"message": "Please verify your reset OTP first"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if timezone.now() >= otp_record.expires_at:
        otp_record.delete()
        return Response(
            {"message": "OTP expired. Please start again."},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.filter(email__iexact=email).first()

    if not user:
        otp_record.delete()
        return Response(
            {"message": "Unable to reset password"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        validate_password(new_password, user=user)
    except ValidationError as error:
        return Response(
            {"message": list(error.messages)},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.set_password(new_password)
    user.save()

    # Prevent reuse of this verified OTP
    otp_record.delete()

    return Response(
        {"message": "Password reset successful. Please log in again."},
        status=status.HTTP_200_OK
    )
