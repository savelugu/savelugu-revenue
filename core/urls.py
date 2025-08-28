from django.urls import path
from . import views
from .views import run_migrations,business_owner_view,start_paystack_payment, verify_paystack_payment,BusinessOwnerLoginView
from .views import login_signup_view,submit_payment_business_view,submit_business_owner_payment_view,payment_list_view,business_owner_revenue_reports_view
from django.contrib.auth import views as auth_views
from core.views import BusinessOwnerLoginView


urlpatterns = [
    path('', views.home, name='home'),

    # Auth
    path('login/', views.custom_login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('access/', views.access_view, name='access'),
    path('business-login/', views.business_owner_login_view, name='business_login'),
    #path('login-signup/', views.login_signup_view, name='login_signup'),
    path('business-owner-login/', login_signup_view, name='business_owner_login'),
    path('auth/', login_signup_view, name='login_signup'),

    # Dashboard(s)
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('collector-dashboard/', views.collector_dashboard, name='collector_dashboard'),

    # Payments
    path('submit-payment/', views.submit_payment_view, name='submit_payment'),
    path('payment-success/<int:payment_id>/', views.payment_success_view, name='payment_success'),

    path('sub-payment/', submit_payment_business_view, name='submit_payment_business'),
    path('start-paystack-payment/', start_paystack_payment, name='start_paystack_payment'),  # ✅ This is the missing one
    path('verify-paystack-payment/', verify_paystack_payment, name='verify_paystack_payment'),
    


    # Business registration (frontend)
    path('register-business/', views.register_business, name='register_business'),
    path('business-success/', views.business_success, name='business_success'),
    path('register-owner/', business_owner_view, name='register_owner'),
    
    path('attendance/start/', views.start_attendance, name='attendance_start'),
    path('attendance/stop/<int:att_id>/', views.stop_attendance, name='attendance_stop'),
    path('attendance/point/', views.log_route_point, name='attendance_point'),
    
    
    path('revenue-reports/', views.revenue_reports_view, name='revenue_reports'),
    path('fraud-detection/', views.fraud_detection_view, name='fraud_detection'),
    path('forecasting/', views.forecasting_view, name='forecasting'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    
    path('run-migrations/', run_migrations),
    
    path('map/', views.business_map_view, name='business_map'),
    path('map/data/', views.business_geojson_view, name='business_geojson'),
    
    path('owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('edit/', views.edit_business, name='edit_business'),
    path('create/', views.create_business, name='create_business'),
    
    path('payments/submit/', submit_business_owner_payment_view, name='submit_business_owner_payment'),
    path('payments/', payment_list_view, name='payment_list'),  # Optional
    path('business-owner/payment-success/<int:payment_id>/', views.business_owner_payment_success_view, name='business_owner_payment_success'),
    

    
    path('business-owner/signup/', views.business_owner_signup, name='business_owner_signup'),
    path('auth/business-owner/', login_signup_view, name='auth_business_owner'),
    
    path('business-owner/login/', BusinessOwnerLoginView.as_view(), name='business_owner_login'),
    path("business-owner-dashboard/", views.business_owner_dashboard, name="business_owner_dashboard"),
    path('business-owner/revenue-reports/', business_owner_revenue_reports_view, name='business_owner_revenue_reports'),
    path("business-owner/payment-details/<int:payment_id>/",views.business_owner_payment_details,name="business_owner_payment_details"),

    # Password reset flow
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    
    # Password reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name="registration/password_reset.html"), 
         name='password_reset'),

    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"), 
         name='password_reset_done'),

    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name="registration/password_reset_confirm.html"), 
         name='password_reset_confirm'),

    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"), 
         name='password_reset_complete'),

    
]
    
    



