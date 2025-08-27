from django.contrib import admin
from .models import User, Business, Payment,BusinessOwner,BusinessOwnerPayment
from django.contrib.auth.admin import UserAdmin

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'role', 'phone_number')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'phone_number')

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = ['username', 'email', 'role', 'is_staff']
    list_filter = ('role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')
    ordering = ('username',)
    readonly_fields = ('last_login', 'date_joined')

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password', 'role', 'phone_number')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'phone_number', 'is_staff', 'is_superuser'),
        }),
    )



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