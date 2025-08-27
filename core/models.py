from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('collector', 'Collector'),
        ('admin', 'Admin'),
        ('business', 'Business Owner'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)  # Useful for collectors too

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Business(models.Model):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, unique=True)
    location = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_businesses')
    registered_via = models.CharField(max_length=50, blank=True, null=True)  # e.g. 'field_agent'

    def __str__(self):
        return f"{self.name} - {self.phone_number}"

    class Meta:
        verbose_name_plural = "Businesses"
        ordering = ['name']


class Payment(models.Model):
    PAYMENT_METHODS = [
        ('paystack', 'Paystack'),
        ('cash', 'Cash'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    IGF_TYPES = [
        ('rates', 'Rates'),
        ('fees', 'Fees'),
        ('fines', 'Fines'),
        ('licenses', 'Licenses'),
        ('rents', 'Rents'),
        ('investment_income', 'Investment Income'),
        ('tender_docs', 'Sales of Tender Documents'),
        ('business_taxes', 'Business Taxes'),
        ('permits', 'Permits'),
    ]

    full_name = models.CharField(max_length=100)  # Name of payer (business owner or collector input)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    igf_type = models.CharField(max_length=30, choices=IGF_TYPES)
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    receipt_id = models.CharField(max_length=100, unique=True, blank=True)
    collector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'role': 'collector'}, related_name='collected_payments')
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='payments', db_index=True)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)  # Optional GPS for physical collection
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

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
  
from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings
class BusinessOwner(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='business_profile')
    business_name = models.CharField(max_length=255, verbose_name="Business Name")
    
    phone_regex = RegexValidator(
        regex=r'^\+?\d{9,15}$',
        message="Phone number must be entered in the format: '0123456789'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, verbose_name="Phone Number")
    
    location = models.CharField(max_length=255, verbose_name="Business Location")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Business Owner"
        verbose_name_plural = "Business Owners"
        ordering = ['business_name']

    def __str__(self):
        return f"{self.business_name} - {self.location}"



class BusinessOwnerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='owners')
    mobile_money_number = models.CharField(max_length=20, null=True, blank=True)
    network = models.CharField(max_length=20, choices=[
        ('mtn', 'MTN'),
        ('vodafone', 'Vodafone'),
        ('airteltigo', 'AirtelTigo'),
    ])
    onboarding_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('active', 'Active'),
    ], default='active')

    def __str__(self):
        return f"{self.user.username} → {self.business.name}"

class BusinessPayment(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('success', 'Success'), ('failed', 'Failed')])
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    receipt_id = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.CharField(max_length=50, blank=True, null=True)
    longitude = models.CharField(max_length=50, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True) 


from django.db import models
from django.conf import settings
from django.utils.crypto import get_random_string

class BusinessOwnerPayment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    IGF_TYPES = [
        ('rates', 'Rates'),
        ('fees', 'Fees'),
        ('fines', 'Fines'),
        ('licenses', 'Licenses'),
        ('rents', 'Rents'),
        ('investment_income', 'Investment Income'),
        ('tender_docs', 'Sales of Tender Documents'),
        ('business_taxes', 'Business Taxes'),
        ('permits', 'Permits'),
    ]

    full_name = models.CharField(max_length=100)  # Business owner's name
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    igf_type = models.CharField(max_length=30, choices=IGF_TYPES)
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    receipt_id = models.CharField(max_length=100, unique=True, blank=True)
    business = models.ForeignKey('core.BusinessOwner', on_delete=models.CASCADE, related_name='paystack_payments', db_index=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='submitted_payments')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.receipt_id:
            self.receipt_id = self.generate_receipt_id()
        super().save(*args, **kwargs)

    def generate_receipt_id(self):
        return f"RV-{get_random_string(8).upper()}"

    def __str__(self):
        return f"{self.business.business_name} - GH₵{self.amount} - Paystack"


    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Business Owner Payment"
        verbose_name_plural = "Business Owner Payments"


from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
IGF_TYPES = [
        ('rates', 'Rates'),
        ('fees', 'Fees'),
        ('fines', 'Fines'),
        ('licenses', 'Licenses'),
        ('rents', 'Rents'),
        ('investment_income', 'Investment Income'),
        ('tender_docs', 'Sales of Tender Documents'),
        ('business_taxes', 'Business Taxes'),
        ('permits', 'Permits'),
    ]

User = get_user_model()

class BusinessOwnerRevenueRecord(models.Model):
    date = models.DateField()
    business_owner = models.ForeignKey('BusinessOwner', on_delete=models.CASCADE, related_name='revenue_records')
    igf_type = models.CharField(max_length=30, choices=IGF_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.date} - {self.business_owner.business_name} - {self.amount} GHS"        