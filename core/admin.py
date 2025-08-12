from django.contrib import admin
from .models import User, Business, Payment
from django.contrib.auth.admin import UserAdmin

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'role', 'is_staff']

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'location', 'latitude', 'longitude']
    search_fields = ['name', 'phone_number']
    list_filter = ['location']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['business', 'amount', 'method', 'location', 'timestamp']
    list_filter = ['method', 'location']
    search_fields = ['business__name']


