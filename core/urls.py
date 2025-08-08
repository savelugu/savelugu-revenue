from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # Auth
    path('login/', views.custom_login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard(s)
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('collector-dashboard/', views.collector_dashboard, name='collector_dashboard'),

    # Payments
    path('submit-payment/', views.submit_payment_view, name='submit_payment'),
    # note: submit_payment_view renders payment_success.html on POST

    # Business registration (frontend)
    path('register-business/', views.register_business, name='register_business'),
    path('business-success/', views.business_success, name='business_success'),
]


