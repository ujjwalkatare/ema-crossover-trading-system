from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


# Custom user manager
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and return a user with an email and password.
        """
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # Hash password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)



from django.db import models

class MonitoringSession(models.Model):
    is_active = models.BooleanField(default=False)
    start_time = models.DateTimeField(auto_now_add=True)
    timeframe = models.CharField(max_length=50)

    def __str__(self):
        return f"Session started at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} ({self.timeframe})"

class MonitoredStock(models.Model):
    session = models.ForeignKey(MonitoringSession, related_name='stocks', on_delete=models.CASCADE)
    ticker = models.CharField(max_length=20)
    timeframe = models.CharField(max_length=50)  # Add this field
    last_trend = models.CharField(max_length=100, blank=True, null=True)
    last_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.ticker

class SignalEvent(models.Model):
    session = models.ForeignKey(MonitoringSession, related_name='signals', on_delete=models.CASCADE)
    ticker = models.CharField(max_length=20)
    signal_type = models.CharField(max_length=100) # e.g., "BULLISH CROSSOVER 🔼"
    description = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticker} - {self.signal_type} at {self.timestamp.strftime('%H:%M')}"