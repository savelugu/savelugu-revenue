from django.urls import path
from . import views
from .views import run_migrations

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
    
    path('attendance/start/', views.start_attendance, name='attendance_start'),
    path('attendance/stop/<int:att_id>/', views.stop_attendance, name='attendance_stop'),
    path('attendance/point/', views.log_route_point, name='attendance_point'),
    
    
    path('revenue-reports/', views.revenue_reports_view, name='revenue_reports'),
    path('fraud-detection/', views.fraud_detection_view, name='fraud_detection'),
    path('forecasting/', views.forecasting_view, name='forecasting'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    
    path('run-migrations/', run_migrations),
]


