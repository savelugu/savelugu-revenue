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
    location = models.CharField(max_length=100)
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

