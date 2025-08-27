from django.contrib import admin
from .models import User, Business, Payment,BusinessOwner,BusinessOwnerPayment
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
    list_display = ['business', 'amount', 'method', 'timestamp']
    list_filter = ['method', 'business']
    search_fields = ['business__name']


@admin.register(BusinessOwner)
class BusinessOwnerAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number','business_name','location']
    search_fields = ['user__username', 'location']

# Business Owner admin


# Business Owner Payment admin
@admin.register(BusinessOwnerPayment)
class BusinessOwnerPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'receipt_id', 'full_name', 'business', 'amount', 'status',
        'igf_type', 'timestamp', 'submitted_by'
    )
    list_filter = ('status', 'igf_type', 'timestamp')
    search_fields = ('receipt_id', 'full_name', 'business__name', 'submitted_by__username')
    readonly_fields = ('receipt_id', 'timestamp', 'paystack_reference')