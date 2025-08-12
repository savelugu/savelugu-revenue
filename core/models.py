from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = (
        ('collector', 'Collector'),
        ('admin', 'Admin'),
        ('business', 'Business'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Business(models.Model):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, unique=True)
    location = models.CharField(max_length=100)  # still keep a text address if you want
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)  # e.g. 9.0580
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True) # e.g. -0.8595
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.phone_number}"

    class Meta:
        verbose_name_plural = "Businesses"
        ordering = ['name']

class Payment(models.Model):
    PAYMENT_METHODS = (
        ('mobile_money', 'Mobile Money'),
        ('cash', 'Cash'),
    )

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='mobile_money')
    collector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    receipt_id = models.CharField(max_length=100, unique=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.receipt_id:
            self.receipt_id = self.generate_receipt_id()
        super().save(*args, **kwargs)

    def generate_receipt_id(self):
        return f"RV-{get_random_string(8).upper()}"

    def __str__(self):
        return f"{self.business.name} - GH₵{self.amount} - {self.get_method_display()}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

class Attendance(models.Model):
    collector = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    start_lat = models.FloatField(null=True, blank=True)
    start_lng = models.FloatField(null=True, blank=True)
    end_lat = models.FloatField(null=True, blank=True)
    end_lng = models.FloatField(null=True, blank=True)

    def close(self, end_lat=None, end_lng=None):
        import django.utils.timezone as tz
        self.end_time = tz.now()
        if end_lat: self.end_lat = end_lat
        if end_lng: self.end_lng = end_lng
        self.save()

class RoutePoint(models.Model):
    collector = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    lat = models.FloatField()
    lng = models.FloatField()
    attendance = models.ForeignKey(Attendance, on_delete=models.SET_NULL, null=True, blank=True)

class CollectorMetricsCache(models.Model):
    collector = models.OneToOneField(User, on_delete=models.CASCADE)
    total_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    number_of_collections = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

class FraudAlert(models.Model):
    transaction_id = models.CharField(max_length=50)
    reason = models.TextField()
    detected_on = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ])

    def __str__(self):
        return f"Alert: {self.transaction_id} ({self.severity})"

class ForecastRecord(models.Model):
    forecast_date = models.DateField()
    predicted_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    confidence_interval = models.CharField(max_length=50)  # e.g., "±5%"

    def __str__(self):
        return f"Forecast {self.forecast_date} - {self.predicted_revenue}"    
    
class AnalyticsSummary(models.Model):
    generated_on = models.DateTimeField(auto_now_add=True)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    avg_daily_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    top_collector = models.CharField(max_length=100)
    highest_area = models.CharField(max_length=100)

    def __str__(self):
        return f"Analytics {self.generated_on}"  

class RevenueRecord(models.Model):
    date = models.DateField()
    collector = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.date} - {self.collector} - {self.amount}"      