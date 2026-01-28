import random
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings

# OTP validity: 5 minutes
OTP_EXPIRY = 300
# Max allowed attempts
MAX_ATTEMPTS = 3

def generate_otp(email):
    """Generate a random 6-digit OTP and store in cache"""
    otp = str(random.randint(100000, 999999))
    cache.set(f"otp_{email}", otp, timeout=OTP_EXPIRY)
    cache.set(f"otp_attempts_{email}", 0, timeout=OTP_EXPIRY)
    return otp

def get_stored_otp(email):
    """Retrieve stored OTP for given email"""
    return cache.get(f"otp_{email}")

def increment_attempts(email):
    """Increment failed attempts counter"""
    attempts = cache.get(f"otp_attempts_{email}", 0) + 1
    cache.set(f"otp_attempts_{email}", attempts, timeout=OTP_EXPIRY)
    return attempts

def attempts_left(email):
    """Return how many attempts are left"""
    attempts = cache.get(f"otp_attempts_{email}", 0)
    return max(0, MAX_ATTEMPTS - attempts)

def delete_otp(email):
    """Remove OTP and attempts from cache"""
    cache.delete(f"otp_{email}")
    cache.delete(f"otp_attempts_{email}")

def send_otp_email(email, otp, purpose="login"):
    """Send OTP email"""
    subject = f"Your OTP for {purpose.capitalize()}"
    message = f"Hello,\n\nYour OTP for {purpose} is: {otp}\n\nThis OTP will expire in 5 minutes."
    from_email = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, [email])
