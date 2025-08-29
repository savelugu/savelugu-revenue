from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum,Avg,Count
from django.utils import timezone
from datetime import timedelta, date
from django.utils.timezone import now, timedelta
from .forms import PaymentForm, CustomLoginForm, BusinessForm,CustomUserCreationForm,BusinessOwnerForm
from .models import Payment,Attendance, RoutePoint,FraudAlert, ForecastRecord, AnalyticsSummary,RevenueRecord,Business,BusinessOwner
import json
from django.http import JsonResponse
import pandas as pd
from prophet import Prophet
from sklearn.linear_model import LinearRegression
from django.contrib.auth.forms import AuthenticationForm

import plotly.graph_objs as go
import plotly.offline as opy
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import requests
from django.conf import settings
from django.contrib import messages
import logging
logger = logging.getLogger(__name__)
def custom_login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # ✅ Role-based redirect
            if user.role == 'business':
                return redirect('submit_payment')  # your payment form view
            elif user.role in ['admin', 'collector']:
                return redirect('dashboard')  # your admin/collector dashboard
            else:
                return redirect('home')  # fallback for unknown roles
    else:
        form = CustomLoginForm()

    return render(request, 'login.html', {'form': form})
@login_required
def dashboard_view(request):
    def get_target(collector=None):
        return 2000  # static for now, dynamic later
    user = request.user
    today = now().date()
    last_week = today - timedelta(days=6)

    # base queryset for logged-in collector
    payments = Payment.objects.filter(collector=request.user)

    # optional filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    method = request.GET.get('method')

    if start_date:
        payments = payments.filter(date__date__gte=start_date)
    if end_date:
        payments = payments.filter(date__date__lte=end_date)
    if method:
        payments = payments.filter(method=method)

    # daily aggregates (last 7 days)
    daily_qs = (
        payments.filter(date__date__range=[last_week, today])
        .values('date__date')
        .annotate(total=Sum('amount'))
        .order_by('date__date')
    )
    labels = [entry['date__date'].strftime('%Y-%m-%d') for entry in daily_qs]
    data = [float(entry['total']) for entry in daily_qs]

    # collector-specific stats
    collector_total = payments.aggregate(total=Sum('amount'))['total'] or 0
    collector_avg_payment = payments.aggregate(avg=Avg('amount'))['avg'] or 0
    collector_target = get_target(request.user)
    collector_progress_pct = (collector_total / collector_target * 100) if collector_target else 0

    # today’s progress
    today_total = payments.filter(date__date=today).aggregate(total=Sum('amount'))['total'] or 0
    today_progress_pct = (today_total / collector_target * 100) if collector_target else 0

    # streak (consecutive days meeting target)
    streak = 0
    for i in range(7):
        day = today - timedelta(days=i)
        day_total = payments.filter(date__date=day).aggregate(total=Sum('amount'))['total'] or 0
        if day_total >= collector_target:
            streak += 1
        else:
            break

    # milestone badges
    milestones = []
    if collector_total >= 5000: milestones.append("GH₵5,000+")
    if collector_total >= 10000: milestones.append("GH₵10,000+")
    if collector_total >= 20000: milestones.append("GH₵20,000+")

    # peer comparison (weekly or monthly)
    period = request.GET.get('period', 'monthly')
    peer_start_date = timezone.now() - timedelta(days=30 if period == 'monthly' else 7)

    peer_qs = (
        Payment.objects.filter(date__gte=peer_start_date)
        .values('collector__username')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    peer_rank, peer_labels, peer_values = None, [], []
    for idx, peer in enumerate(peer_qs):
        peer_labels.append(peer['collector__username'])
        peer_values.append(float(peer['total']))
        if peer['collector__username'] == request.user.username:
            peer_rank = idx + 1

    top_3_peers = peer_qs[:3]

    # global analytics
    total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
    avg_daily = Payment.objects.aggregate(Avg('amount'))['amount__avg'] or 0
    top_collector = (
        Payment.objects.values('collector__username')
        .annotate(total=Sum('amount'))
        .order_by('-total')
        .first()
    )
    total_payments_count = Payment.objects.count()
    peak_day = (
        Payment.objects.values('date__date')
        .annotate(total=Sum('amount'))
        .order_by('-total')
        .first()
    )
    most_used_method = (
        Payment.objects.values('method')
        .annotate(count=Count('id'))
        .order_by('-count')
        .first()
    )
    collector_contribution_pct = (collector_total / total_revenue * 100) if total_revenue else 0

    # Example: filter payments for this collector
    total_collections = Payment.objects.filter(collector=user).aggregate(total=Sum('amount'))['total'] or 0

    # Define a target (you can make this dynamic later)
    target = 10000  

    # Create gauge chart for this user’s progress
    collector_gauge = create_gauge(
        title=f"{user.username}'s Progress",
        value=float(total_collections),
        max_value=target
    )

    context = {
        'payments': payments.order_by('-date'),
        'start_date': start_date,
        'end_date': end_date,
        'method': method,
        'labels': json.dumps(labels),
        'data': json.dumps(data),
        # peer comparison
        'collector_labels': json.dumps(peer_labels),
        'collector_amounts': json.dumps(peer_values),
        'peer_rank': peer_rank,
        'peer_total': len(peer_qs),
        'top_3_peers': top_3_peers,
        # collector analytics
        'collector_total': collector_total,
        'collector_avg_payment': collector_avg_payment,
        'collector_target': collector_target,
        'collector_progress_pct': round(collector_progress_pct, 2),
        'today_total': today_total,
        'today_progress_pct': round(today_progress_pct, 2),
        'streak': streak,
        'milestones': milestones,
        'collector_contribution_pct': round(collector_contribution_pct, 2),
        # global analytics
        'total_revenue': total_revenue,
        'avg_daily': avg_daily,
        'top_collector': top_collector,
        'total_payments_count': total_payments_count,
        'peak_day': peak_day,
        'most_used_method': most_used_method,
        'collector_gauge': collector_gauge,
    }
    return render(request, 'dashboard.html', context)




def logout_view(request):
        logout(request)
        return redirect('login')
    
from django.db.models.functions import TruncDate
import plotly.express as px
import plotly.io as pio  
  
@login_required
def collector_dashboard(request):
    user = request.user
    payments = Payment.objects.filter(collector=user)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    method = request.GET.get('method')

    if start_date:
        payments = payments.filter(date__date__gte=start_date)
    if end_date:
        payments = payments.filter(date__date__lte=end_date)
    if method:
        payments = payments.filter(method=method)

    total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
    today = now().date()
    last_week = today - timedelta(days=6)

    daily_data = (
        payments  # use filtered payments, not all Payment.objects
        .filter(date__date__range=[last_week, today])
        .values('date__date')
        .annotate(total=Sum('amount'))
        .order_by('date__date')
    )

    labels = [d['date__date'].strftime('%b %d') for d in daily_data]
    data = [float(d['total']) for d in daily_data]

    # Revenue by collector
    collector_data = (
        payments  # use filtered payments
        .values('collector__username')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    collector_labels = [c['collector__username'] for c in collector_data]
    collector_amounts = [float(c['total']) for c in collector_data]

     # === Collector Gauge Chart ===
    target = 1000  # <-- you can make this dynamic per collector
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=total_amount,
        title={'text': f"{user.username} Progress"},
        gauge={
            'axis': {'range': [0, target]},
            'bar': {'color': "green"},
            'steps': [
                {'range': [0, target * 0.5], 'color': "lightgray"},
                {'range': [target * 0.5, target], 'color': "lightgreen"}
            ],
        }
    ))
    collector_gauge = fig.to_html(full_html=False)
    
    # Daily data
    daily_qs = (
        payments.annotate(day=TruncDay("timestamp"))
        .values("day")
        .annotate(total=Sum("amount"))
        .order_by("day")
    )
    if daily_qs:
        daily_chart = px.bar(daily_qs, x="day", y="total", title="Payments Collected - Daily")
        daily_chart = daily_chart.to_html(full_html=False)
    else:
        daily_chart = None


    # Weekly data
    weekly_qs = payments.annotate(week=TruncWeek("date")).values("week").annotate(total=Sum("amount")).order_by("week")
    if weekly_qs:
        weekly_chart = px.bar(weekly_qs, x="week", y="total", title="Payments Collected - Weekly")
        weekly_chart = weekly_chart.to_html(full_html=False)
    else:
        weekly_chart = None

    # Monthly data
    monthly_qs = payments.annotate(month=TruncMonth("date")).values("month").annotate(total=Sum("amount")).order_by("month")
    if monthly_qs:
        monthly_chart = px.bar(monthly_qs, x="month", y="total", title="Payments Collected - Monthly")
        monthly_chart = monthly_chart.to_html(full_html=False)
    else:
        monthly_chart = None

    
    
    
    context = {
        'payments': payments.order_by('-date'),
        'start_date': start_date,
        'end_date': end_date,
        'method': method,
        'total_amount': total_amount,
        'labels': json.dumps(labels),
        'data': json.dumps(data),
        'collector_labels': json.dumps(collector_labels),
        'collector_amounts': json.dumps(collector_amounts),
        'collector_gauge': collector_gauge,  # <-- add gauge chart to template
        "daily_chart": daily_chart,
        "weekly_chart": weekly_chart,
        "monthly_chart": monthly_chart,
        
    }
    return render(request, 'dashboard.html', context)

import json
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .forms import BusinessForm

logger = logging.getLogger(__name__)

@login_required
@csrf_exempt   # allow fetch() JSON posts
def register_business(request):
    """
    Handles both:
    1. Normal single online registration (form POST)
    2. Offline bulk sync via JSON (localStorage queue)
    """

    # ✅ Role check
    if getattr(request.user, "role", None) not in ["collector", "admin"]:
        messages.error(request, "Access denied. Only collectors and admins can register businesses.")
        return redirect("dashboard")

    # ✅ Case 1: Bulk JSON sync from localStorage
    if request.method == "POST" and request.headers.get("Content-Type") == "application/json":
        try:
            data = json.loads(request.body.decode("utf-8"))
            businesses_data = data.get("businesses", [])
            saved_ids = []

            for entry in businesses_data:
                form = BusinessForm(entry)
                if form.is_valid():
                    business = form.save(commit=False)
                    business.registered_by = request.user
                    business.latitude = entry.get("latitude")
                    business.longitude = entry.get("longitude")
                    business.registered_at = timezone.now()
                    if hasattr(request.user, "assigned_zone"):
                        business.zone = request.user.assigned_zone
                    business.save()
                    saved_ids.append(business.id)
                    logger.info(f"✅ Offline synced business: {business.business_name}")
                else:
                    logger.warning(f"❌ Invalid business data skipped: {entry}")

            return JsonResponse({"status": "success", "saved": saved_ids})

        except Exception as e:
            logger.error(f"❌ Bulk sync failed: {str(e)}")
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    # ✅ Case 2: Normal online form submission
    if request.method == "POST":
        form = BusinessForm(request.POST)
        if form.is_valid():
            business = form.save(commit=False)
            business.registered_by = request.user

            # parse lat/lng safely
            try:
                business.latitude = float(request.POST.get("latitude", 0))
                business.longitude = float(request.POST.get("longitude", 0))
            except (TypeError, ValueError):
                business.latitude, business.longitude = None, None

            business.registered_at = timezone.now()
            if hasattr(request.user, "assigned_zone"):
                business.zone = request.user.assigned_zone
            business.save()

            logger.info(f"✅ Business registered: {business.business_name} by {request.user.username}")
            messages.success(request, f"Business '{business.business_name}' registered successfully!")

            return render(request, "core/business_success.html", {"business": business})
    else:
        form = BusinessForm()

    # ✅ Render registration page
    return render(request, "core/register_business.html", {"form": form})



def business_success(request):
    return render(request, 'core/business_success.html')

def home(request):
    return render(request, 'core/home.html')

@login_required
def start_attendance(request):
    att = Attendance.objects.create(collector=request.user,
                                    start_lat=request.POST.get('lat'),
                                    start_lng=request.POST.get('lng'))
    return JsonResponse({'attendance_id': att.id})

@login_required
def stop_attendance(request, att_id):
    att = get_object_or_404(Attendance, id=att_id, collector=request.user)
    att.close(end_lat=request.POST.get('lat'), end_lng=request.POST.get('lng'))
    return JsonResponse({'status': 'ok'})

@login_required
def log_route_point(request):
    lat = request.POST.get('lat'); lng = request.POST.get('lng'); att_id = request.POST.get('attendance_id')
    RoutePoint.objects.create(collector=request.user, lat=lat, lng=lng, attendance_id=att_id or None)
    return JsonResponse({'ok': True})

# 1. Analytics Dashboard
def analytics_view(request):
    total_revenue = Payment.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    avg_daily = Payment.objects.aggregate(Avg('amount'))['amount__avg'] or 0
    top_collector = Payment.objects.values('collector').annotate(total=Sum('amount')).order_by('-total').first()
    highest_area = Payment.objects.values('location').annotate(total=Sum('amount')).order_by('-total').first()

    summary = {
        "total_revenue": total_revenue,
        "avg_daily_revenue": avg_daily,
        "top_collector": top_collector,
        "highest_area": highest_area
    }
    return render(request, "analytics.html", {"summary": summary})

# 2. Revenue Reports
@login_required
def revenue_reports_view(request):
    records = Payment.objects.all().order_by('-date')
    return render(request, "revenue_reports.html", {"records": records})


@login_required
def fraud_detection_view(request):
    try:
        alerts_list = FraudAlert.objects.all().order_by('-detected_on')
        
        # Optional: Paginate results (e.g., 25 alerts per page)
        paginator = Paginator(alerts_list, 25)
        page = request.GET.get('page')
        alerts = paginator.get_page(page)

        return render(request, "fraud_detection.html", {"alerts": alerts})
    
    except Exception as e:
        # Log the error or notify admin if needed
        return render(request, "fraud_detection.html", {
            "alerts": [],
            "error": "Unable to load fraud alerts at this time."
        })

@login_required
def forecasting_view(request):
    payments = Payment.objects.all().order_by('date')

    if not payments.exists():
        return render(request, "forecasting.html", {
            "plot_div": None
        })

        # Convert to DataFrame & group by date
    df = pd.DataFrame(list(payments.values('date', 'amount')))
    df['date'] = pd.to_datetime(df['date'])
    daily_df = df.groupby('date').sum().reset_index()
    daily_df.rename(columns={'date': 'ds', 'amount': 'y'}, inplace=True)

    # ❗ Remove timezone from datetime
    daily_df['ds'] = daily_df['ds'].dt.tz_localize(None)

    # Prophet model
    model = Prophet()
    model.fit(daily_df)


    # Forecast next 7 days
    future = model.make_future_dataframe(periods=7)
    forecast = model.predict(future)

    # Plotly chart
    actual_trace = go.Scatter(
        x=daily_df['ds'], y=daily_df['y'],
        mode='lines+markers', name='Actual'
    )
    forecast_trace = go.Scatter(
        x=forecast['ds'], y=forecast['yhat'],
        mode='lines', name='Forecast'
    )
    upper_trace = go.Scatter(
        x=forecast['ds'], y=forecast['yhat_upper'],
        mode='lines', name='Upper Bound',
        line=dict(dash='dot'), opacity=0.3
    )
    lower_trace = go.Scatter(
        x=forecast['ds'], y=forecast['yhat_lower'],
        mode='lines', name='Lower Bound',
        line=dict(dash='dot'), opacity=0.3
    )

    layout = go.Layout(
        title='Payment Forecast (Next 7 Days)',
        xaxis=dict(title='Date'),
        yaxis=dict(title='Amount (GH₵)'),
        hovermode='x unified'
    )

    fig = go.Figure(data=[actual_trace, forecast_trace, upper_trace, lower_trace], layout=layout)
    plot_div = opy.plot(fig, auto_open=False, output_type='div')

        # Prepare forecast table (next 7 days only)
        
    forecast_table = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(7).copy()
    forecast_table['ds'] = forecast_table['ds'].dt.strftime('%Y-%m-%d')
    forecast_table['yhat'] = forecast_table['yhat'].round(0)
    forecast_table['yhat_lower'] = forecast_table['yhat_lower'].round(2)
    forecast_table['yhat_upper'] = forecast_table['yhat_upper'].round(2)

    return render(request, "forecasting.html", {
        "plot_div": plot_div,
        "forecast_table": forecast_table.to_dict(orient='records')
    })



def analytics_dashboard(request):
    total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
    avg_daily = Payment.objects.aggregate(Avg('amount'))['amount__avg'] or 0
    top_collector = Payment.objects.values('collector').annotate(total=Sum('amount')).order_by('-total').first()
    
    return render(request, 'analytics.html', {'total_revenue': total_revenue,'avg_daily': avg_daily,'top_collector': top_collector})

from django.http import HttpResponse
from django.core.management import call_command

def run_migrations(request):
    call_command('migrate')
    return HttpResponse("Migrations applied.")

from django.views.decorators.csrf import csrf_protect

@csrf_protect
def signup_view(request):
    if request.method == 'POST':
        form = BusinessForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'business_owner'  # or 'collector' if needed
            user.save()
            login(request, user)
            return redirect('register_business')  # or dashboard
    else:
        form = BusinessForm()
    return render(request, 'signup.html', {'form': form})




from django.shortcuts import render, redirect
from .forms import BusinessCheckForm
from django.contrib.auth import get_user_model

User = get_user_model()

def check_business_owner(request):
    if request.method == 'POST':
        form = BusinessCheckForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone_number']
            exists = User.objects.filter(phone_number=phone, role='business').exists()
            if exists:
                return redirect('login')  # Replace with your login URL name
            else:
                return redirect('signup')  # Replace with your registration URL name
    else:
        form = BusinessCheckForm()
    return render(request, 'check_business.html', {'form': form})

from django.contrib.auth.forms import AuthenticationForm
from .forms import CustomUserCreationForm, BusinessOwnerForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

@login_required
def access_view(request):
    login_form = AuthenticationForm()
    business_form = BusinessOwnerForm()

    if request.method == 'POST':
        if 'login_submit' in request.POST:
            login_form = AuthenticationForm(request, data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)

                # ✅ Redirect based on role
                if hasattr(user, 'role') and user.role == 'business':
                    return redirect('submit_payment')  # update to your URL name
                else:
                    return redirect('home')  # fallback for other roles

        elif 'signup_submit' in request.POST:
            if request.user.role not in ['admin', 'business']:
                return render(request, 'permission_denied.html')

            business_form = BusinessOwnerForm(request.POST)
            if business_form.is_valid():
                business = business_form.save(commit=False)
                business.registered_by = request.user
                business.save()
                return redirect('home')

    return render(request, 'access.html', {
        'login_form': login_form,
        'business_form': business_form,
    })




def business_owner_view(request):
    if request.method == 'POST':
        form = BusinessOwnerForm(request.POST)
        if form.is_valid():
            business_owner = form.save(commit=False)
            business_owner.user = request.user
            business_owner.save()
            return redirect('dashboard')  # or wherever you want
    else:
        form = BusinessOwnerForm()
    return render(request, 'business_owner_form.html', {'form': form})


from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.shortcuts import render, redirect

def business_owner_login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if hasattr(user, "role") and user.role == "business":
                login(request, user)
                return redirect("business_owner_dashboard")
            else:
                messages.error(request, "Access denied. You are not a Business Owner.")
        else:
            messages.error(request, "Invalid login credentials.")
    else:
        form = AuthenticationForm()

    return render(request, "business_owner_login.html", {"form": form})



from .forms import BusinessOwnerSignupForm
from .models import BusinessOwner

def login_signup_view(request):
    login_form = AuthenticationForm(request, data=request.POST or None)
    signup_form = BusinessOwnerSignupForm(request.POST or None)

    if request.method == 'POST':
        if 'login_submit' in request.POST and login_form.is_valid():
            user = login_form.get_user()
            if user.role == 'business':
                login(request, user)
                return redirect('submit_payment')  # or whatever name you used in urls.py

            else:
                messages.error(request, "Access denied. Not a Business Owner.")

        elif 'signup_submit' in request.POST and signup_form.is_valid():
            user = signup_form.save(commit=False)
            user.role = 'business'
            user.save()
            login(request, user)

            BusinessOwner.objects.create(
                user=user,
                business_name=signup_form.cleaned_data['business_name'],
                phone_number=signup_form.cleaned_data['phone_number'],
                location=signup_form.cleaned_data['location'],
                latitude=signup_form.cleaned_data['latitude'],
                longitude=signup_form.cleaned_data['longitude']
            )

            return redirect('business_owner_login')

    return render(request, 'login_signup.html', {
        'login_form': login_form,
        'signup_form': signup_form
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from .models import Business, Payment
from .forms import PaymentForm
import requests


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.conf import settings
import requests

from .forms import PaymentForm
from .models import Payment  # or whatever your model is called

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Payment
from .forms import PaymentForm

@login_required
def submit_payment_view(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.collector = request.user
            payment.status = 'paid'  # ✅ Mark as paid immediately for cash
            payment.payment_method = 'cash'  # Optional: if you track method
            payment.save()

            messages.success(request, "Cash payment recorded successfully.")
            return redirect('payment_success', payment_id=payment.id)
    else:
        form = PaymentForm()

    return render(request, 'submit_payment.html', {'form': form})

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Payment

@login_required
def payment_success_view(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id, collector=request.user)
    return render(request, 'payment_success.html', {'payment': payment})


@login_required
def verify_paystack_payment(request):
    reference = request.GET.get('reference')
    if not reference:
        return render(request, 'payment_failed.html', {'error': 'Missing reference'})

    url = f'https://api.paystack.co/transaction/verify/{reference}'
    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    response = requests.get(url, headers=headers)
    res_data = response.json()

    if res_data.get('status') and res_data['data']['status'] == 'success':
        Payment.objects.filter(paystack_reference=reference).update(status='success')
        payment = Payment.objects.get(paystack_reference=reference)  # ✅ Fetch full object
        return render(request, 'payment_success.html', {'payment': payment})
    else:
        Payment.objects.filter(paystack_reference=reference).update(status='failed')
        return render(request, 'payment_failed.html', {'error': res_data.get('message')})




def logout_view(request):
    logout(request)
    return redirect('login')
@login_required
def collector_dashboard(request):
    user = request.user
    payments = Payment.objects.filter(collector=user)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    method = request.GET.get('method')

    if start_date:
        payments = payments.filter(date__date__gte=start_date)
    if end_date:
        payments = payments.filter(date__date__lte=end_date)
    if method:
        payments = payments.filter(method=method)

    total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
    today = now().date()
    last_week = today - timedelta(days=6)

    daily_data = (
        payments  # use filtered payments, not all Payment.objects
        .filter(date__date__range=[last_week, today])
        .values('date__date')
        .annotate(total=Sum('amount'))
        .order_by('date__date')
    )

    labels = [d['date__date'].strftime('%b %d') for d in daily_data]
    data = [float(d['total']) for d in daily_data]

    # Revenue by collector
    collector_data = (
        payments  # use filtered payments
        .values('collector__username')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    collector_labels = [c['collector__username'] for c in collector_data]
    collector_amounts = [float(c['total']) for c in collector_data]

    context = {
        'payments': payments.order_by('-date'),
        'start_date': start_date,
        'end_date': end_date,
        'method': method,
        'total_amount': total_amount,
        # JSON encode so JS reads it properly
        'labels': json.dumps(labels),
        'data': json.dumps(data),
        'collector_labels': json.dumps(collector_labels),
        'collector_amounts': json.dumps(collector_amounts),
    }
    return render(request, 'core/dashboard.html', context)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
import requests

from .models import Business, BusinessOwnerProfile, BusinessPayment
from .forms import BusinessPaymentForm

@login_required
def submit_payment_business_view(request):
    if request.user.role != 'business':
        messages.error(request, "Access denied.")
        return redirect('home')

    # ✅ Get the business registered by the current user
    business = Business.objects.filter(registered_by=request.user).first()
    if not business:
        messages.error(request, "No business found. Please register your business first.")
        return redirect('register_business')

    # ✅ Get or create the business owner profile
    profile, created = BusinessOwnerProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'business': business,
            'mobile_money_number': request.user.phone_number or '0000000000',
            'network': 'mtn',
            'onboarding_status': 'active'
        }
    )

    # ✅ Ensure profile is linked to business (if created earlier without one)
    if not profile.business:
        profile.business = business
        profile.save()

    if request.method == 'POST':
        form = BusinessPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.business = business
            payment.submitted_by = request.user
            payment.full_name = form.cleaned_data.get('full_name') or request.user.get_full_name() or request.user.username
            payment.latitude = request.POST.get('latitude')
            payment.longitude = request.POST.get('longitude')
            reference = request.POST.get('paystack_reference')

            if reference:
                # ✅ Verify Paystack transaction
                url = f'https://api.paystack.co/transaction/verify/{reference}'
                headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
                response = requests.get(url, headers=headers)
                res_data = response.json()

                if res_data.get('status') and res_data['data']['status'] == 'success':
                    payment.status = 'success'
                    payment.paystack_reference = reference
                    payment.receipt_id = reference
                    payment.save()
                    return render(request, 'payment_success.html', {'payment': payment})
                else:
                    payment.status = 'failed'
                    payment.paystack_reference = reference
                    payment.save()
                    return redirect('business_owner_payment_success', payment_id=payment.id)

            else:
                messages.error(request, "Missing Paystack reference.")
    else:
        form = BusinessPaymentForm()

    return render(request, 'submit_payment_business.html', {
        'form': form,
        'business': business,
        'profile': profile,
        'PAYSTACK_PUBLIC_KEY': settings.PAYSTACK_PUBLIC_KEY,
    })


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@login_required
@csrf_exempt  # Optional if you're using JS fetch
def start_paystack_payment(request):
    if request.method == 'POST':
        business = Business.objects.filter(registered_by=request.user).first()
        if not business:
            return JsonResponse({'error': 'Business not found'}, status=400)

        email = request.user.email or 'default@example.com'
        amount = int(request.POST.get('amount', 0)) * 100  # Convert to kobo
        callback_url = request.build_absolute_uri('/verify-paystack-payment/')  # You’ll create this next

        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "email": email,
            "amount": amount,
            "callback_url": callback_url,
            "channels": ["mobile_money", "card"],  # Optional: restrict to mobile money
        }

        response = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers)
        res_data = response.json()

        if res_data.get("status"):
            return JsonResponse({"authorization_url": res_data["data"]["authorization_url"]})
        else:
            return JsonResponse({"error": res_data.get("message")}, status=400)


@login_required
def verify_paystack_payment(request):
    reference = request.GET.get('reference')
    if not reference:
        return render(request, 'payment_failed.html', {'error': 'Missing reference'})

    url = f'https://api.paystack.co/transaction/verify/{reference}'
    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    response = requests.get(url, headers=headers)
    res_data = response.json()

    try:
        payment = BusinessOwnerPayment.objects.get(paystack_reference=reference)
    except BusinessOwnerPayment.DoesNotExist:
        return render(request, 'payment_failed.html', {'error': 'Payment record not found'})

    if res_data.get('status') and res_data['data']['status'] == 'success':
        # ✅ Mark as success
        payment.status = 'success'
        payment.save()
    else:
        # ❌ Mark as failed
        payment.status = 'failed'
        payment.save()

    # 🔑 Always redirect to the payment details page
    return redirect("business_owner_payment_details", payment_id=payment.id)



from django.shortcuts import render
from django.http import JsonResponse
from .models import Business

def business_map_view(request):
    return render(request, 'business_map.html')

def business_geojson_view(request):
    businesses = Business.objects.filter(
        latitude__gte=9.5, latitude__lte=9.8,
        longitude__gte=-0.9, longitude__lte=-0.7
    ).exclude(latitude__isnull=True, longitude__isnull=True)

    features = []
    for biz in businesses:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [biz.longitude, biz.latitude],
            },
            "properties": {
                "name": biz.name,
            }
        })

    return JsonResponse({"type": "FeatureCollection", "features": features})


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import BusinessOwner
from .forms import BusinessOwnerForm  # You'll need to create this form

@login_required
def owner_dashboard(request):
    owner = get_object_or_404(BusinessOwner, user=request.user)
    return render(request, 'business/owner_dashboard.html', {'owner': owner})

@login_required
def edit_business(request):
    owner = get_object_or_404(BusinessOwner, user=request.user)
    if request.method == 'POST':
        form = BusinessOwnerForm(request.POST, instance=owner)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = BusinessOwnerForm(instance=owner)
    return render(request, 'business/edit.html', {'form': form})

@login_required
def create_business(request):
    if request.method == 'POST':
        form = BusinessOwnerForm(request.POST)
        if form.is_valid():
            business = form.save(commit=False)
            business.user = request.user
            business.save()
            return redirect('dashboard')
    else:
        form = BusinessOwnerForm()
    return render(request, 'business/create.html', {'form': form})


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import BusinessOwnerPayment
from .forms import BusinessOwnerPaymentForm
import requests
from django.urls import reverse


@login_required
def submit_business_owner_payment_view(request):
    if request.method == 'POST':
        form = BusinessOwnerPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.submitted_by = request.user
            payment.status = 'pending'
            payment.save()

            # ✅ Redirect to payment details page instead of re-rendering form
            return redirect("business_owner_payment_details", payment_id=payment.id)

    else:
        form = BusinessOwnerPaymentForm()

    return render(request, 'submit_business_owner_payment.html', {
        'form': form,
        'PAYSTACK_PUBLIC_KEY': settings.PAYSTACK_PUBLIC_KEY,
    })




@login_required
def payment_list_view(request):
    payments = BusinessOwnerPayment.objects.filter(submitted_by=request.user).order_by('-timestamp')
    return render(request, 'payments/payment_list.html', {'payments': payments})

from django.shortcuts import render, redirect
from .forms import BusinessOwnerSignupForm

from django.shortcuts import render, redirect
from .forms import BusinessOwnerSignupForm
from .models import BusinessOwner

def business_owner_signup(request):
    if request.method == 'POST':
        form = BusinessOwnerSignupForm(request.POST)
        if form.is_valid():
            user = form.save()  # saves User + BusinessOwner

            # fetch BusinessOwner profile for displaying details
            owner = BusinessOwner.objects.get(user=user)

            return render(
                request,
                'core/business_owner_signup_success.html',
                {'owner': owner, 'user': user}
            )
    else:
        form = BusinessOwnerSignupForm()
    return render(request, 'business_owner_signup.html', {'form': form})



from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import BusinessOwnerLoginForm

class BusinessOwnerLoginView(LoginView):
    template_name = 'business_owner_login.html'
    authentication_form = BusinessOwnerLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('submit_business_owner_payment')

    


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import BusinessOwnerPayment

@login_required
def business_owner_payment_success_view(request, payment_id):
    payment = get_object_or_404(BusinessOwnerPayment, id=payment_id)

    # Restrict access to the user who submitted it
    if payment.submitted_by != request.user:
        messages.error(request, "Access denied.")
        return redirect('home')

    # Optional: verify Paystack reference from query string
    reference = request.GET.get('reference')
    if reference and reference == payment.paystack_reference:
        payment.status = 'completed'
        payment.save()
        messages.success(request, "Mobile payment recorded successfully.")
    elif reference:
        messages.warning(request, "Reference mismatch. Payment may not be verified.")

    return render(request, 'business_owner_payment_success.html', {'payment': payment})






from django.contrib import messages
from django.shortcuts import redirect

def business_owner_success_signup(request):
    if request.method == 'POST':
        form = BusinessOwnerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully! 🎉')
            return redirect('business_owner_login')  # or wherever you want
    else:
        form = BusinessOwnerForm()
    return render(request, 'signup.html', {'form': form})


from django.shortcuts import render
from datetime import datetime
import random

def home(request):
    quotes = [
        "Over 1,200 businesses registered in Savelugu 🚀",
        "Digital revenue collection boosted transparency by 40% 📊",
        "Collectors cover more than 25 zones across the municipality 🌍",
        "Revenue mobilization supports infrastructure growth 💼",
        "Smart payments reduce fraud and delays ⏱️"
    ]
    random_quote = random.choice(quotes)

    return render(request, "core/home.html", {   # ✅ include "core/"
        "year": datetime.now().year,
        "quotes": quotes,
        "random_quote": random_quote,
    })


from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.http import HttpResponseForbidden
from .models import BusinessOwner, BusinessOwnerPayment, User

@login_required
def business_owner_dashboard(request):
    if request.user.role == 'business':
        # Show the logged-in business user's profile
        try:
            business_owner = request.user.business_profile
        except BusinessOwner.DoesNotExist:
            business_owner = None

        if business_owner:
            payments = BusinessOwnerPayment.objects.filter(business=business_owner)
            total_amount = payments.filter(status="success").aggregate(total=Sum("amount"))["total"] or 0
            total_payments = payments.count()
            pending_count = payments.filter(status="pending").count()
            success_count = payments.filter(status="success").count()
            failed_count = payments.filter(status="failed").count()
        else:
            payments = []
            total_amount = total_payments = pending_count = success_count = failed_count = 0

        context = {
            "business_owner": business_owner,
            "payments": payments[:5],  # latest 5 payments
            "total_amount": total_amount,
            "total_payments": total_payments,
            "pending_count": pending_count,
            "success_count": success_count,
            "failed_count": failed_count,
        }
        return render(request, "business_owner_dashboard.html", context)

    elif request.user.role == 'admin':
        # Admin sees all business owners and their payments
        all_businesses = BusinessOwner.objects.all()
        businesses_data = []
        for bo in all_businesses:
            payments = BusinessOwnerPayment.objects.filter(business=bo)
            businesses_data.append({
                "business_owner": bo,
                "payments": payments[:5],
                "total_amount": payments.filter(status="success").aggregate(total=Sum("amount"))["total"] or 0,
                "total_payments": payments.count(),
                "pending_count": payments.filter(status="pending").count(),
                "success_count": payments.filter(status="success").count(),
                "failed_count": payments.filter(status="failed").count(),
            })
        context = {"businesses_data": businesses_data}
        return render(request, "business_owner_dashboard.html", context)

    else:
        # Collectors or other roles cannot access
        return HttpResponseForbidden("You are not allowed to view this page.")



from django.shortcuts import render
from django.db.models import Sum
from .models import BusinessOwnerPayment
import plotly.graph_objs as go
import plotly.offline as opy

def create_gauge(title, value, max_value):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=float(value),  # convert Decimal to float
        title={'text': title, 'font': {'size': 18, 'color': 'white'}},
        number={'font': {'color': 'white'}},
        gauge={
            'axis': {'range': [0, max_value], 'tickcolor': 'white'},
            'bgcolor': "rgba(0,0,0,0)",
            'bar': {'color': "#006CFF"},
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, max_value * 0.5], 'color': "#2c2f33"},
                {'range': [max_value * 0.5, max_value * 0.75], 'color': "#3b3f44"},
                {'range': [max_value * 0.75, max_value], 'color': "#4c8eda"}
            ],
            'threshold': {
                'line': {'color': "#FFD700", 'width': 4},
                'thickness': 0.75,
                'value': float(value)
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor="#005d03",
        font={'color': 'white'}
    )
    return opy.plot(fig, auto_open=False, output_type='div')


from django.db.models import Sum

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
import plotly.graph_objects as go
import plotly.offline as opy
import plotly.express as px
import pandas as pd
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from .models import BusinessOwnerPayment


@login_required
def business_owner_revenue_reports_view(request):
    records = BusinessOwnerPayment.objects.all().order_by('-timestamp')
    total_revenue = records.aggregate(Sum('amount'))['amount__sum'] or 0

    # 📊 IGF Type Bar Chart
    igf_data = records.values('igf_type').annotate(total=Sum('amount'))
    df = pd.DataFrame(igf_data)
    df['IGF Type'] = df['igf_type'].str.title()
    df['Total Revenue'] = df['total']
    df = df.sort_values('Total Revenue', ascending=False)

    fig = px.bar(
        df,
        x="Total Revenue",
        y="IGF Type",
        orientation='h',
        color="IGF Type",
        labels={"Total Revenue": "GHS"},
        color_discrete_sequence=px.colors.qualitative.Set2
    )

    fig.update_traces(
        text=[f"GHS {int(val):,}" for val in df["Total Revenue"]],
        textposition='outside',
        marker_line_color="black",
        marker_line_width=0.5
    )

    fig.update_layout(
        title='Total Revenue per IGF Type',
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="black"),
        xaxis=dict(title="Total Revenue (GHS)", color="black", gridcolor="gray"),
        yaxis=dict(title="", color="black", categoryorder='total ascending'),
        height=400,
        margin=dict(l=70, r=50, t=40, b=40),
        legend=dict(title="IGF Type", font=dict(color="black")),
    )
    igf_chart = opy.plot(fig, auto_open=False, output_type='div')

    # 🥧 Pie: Top 10 Businesses
    business_data = (
        records.values('business__business_name')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:10]
    )

    labels = [b['business__business_name'] for b in business_data]
    values = [b['total'] for b in business_data]

    fig = go.Figure([go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        textinfo='label+percent',
        hoverinfo='label+value',
        marker=dict(colors=px.colors.sequential.Plasma),
        textfont=dict(size=14),
    )])

    fig.update_traces(
        textposition='inside',
        insidetextorientation='radial',
        marker_line_color="white",
        marker_line_width=1
    )

    fig.update_layout(
        title='Top 10 Businesses by Revenue',
        title_x=0.5,
        template='plotly_white',
        height=400,
        width=600,
        margin=dict(t=60, b=20, l=20, r=20),
        showlegend=True
    )
    pie_chart = opy.plot(fig, auto_open=False, output_type='div')

    # 📈 Line chart (Monthly, Weekly, Daily)
    monthly_data = records.annotate(month=TruncMonth('timestamp')).values('month').annotate(total=Sum('amount')).order_by('month')
    weekly_data = records.annotate(week=TruncWeek('timestamp')).values('week').annotate(total=Sum('amount')).order_by('week')
    daily_data = records.annotate(day=TruncDay('timestamp')).values('day').annotate(total=Sum('amount')).order_by('day')

    months = [m['month'].strftime('%b %Y') for m in monthly_data]
    month_totals = [m['total'] for m in monthly_data]

    weeks = [w['week'].strftime('%d %b') for w in weekly_data]
    week_totals = [w['total'] for w in weekly_data]

    days = [d['day'].strftime('%d %b') for d in daily_data]
    day_totals = [d['total'] for d in daily_data]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=months, y=month_totals, mode='lines+markers',
                             name='Monthly', line=dict(color='royalblue', width=3)))
    fig.add_trace(go.Scatter(x=weeks, y=week_totals, mode='lines+markers',
                             name='Weekly', line=dict(color='green', width=2)))
    fig.add_trace(go.Scatter(x=days, y=day_totals, mode='lines+markers',
                             name='Daily', line=dict(color='firebrick', width=1)))

    fig.update_layout(
        title=dict(text='📊 Revenue Trends: Monthly, Weekly, Daily', x=0.5, font=dict(size=20)),
        xaxis_title='Date',
        yaxis_title='Revenue (GHS)',
        template='plotly_white',
        height=400,
        width=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=80, l=60, r=30)
    )
    line_chart = opy.plot(fig, auto_open=False, output_type='div')

    # Aggregate payments by business owner
    top4 = BusinessOwnerPayment.objects.values('business__business_name') \
        .annotate(total=Sum('amount')) \
        .order_by('-total')[:4]

    # Find the maximum revenue for scaling the gauges
    max_value = max(float(b['total']) for b in top4) if top4 else 1

    # Create gauge charts for each business
    gauge_charts = [
        create_gauge(b['business__business_name'], b['total'], max_value)
        for b in top4
    ]


    context = {
        'records': records,
        'total_revenue': total_revenue,
        'igf_chart': igf_chart,
        'pie_chart': pie_chart,
        'line_chart': line_chart,
        'gauge_charts': gauge_charts,
        'top4': top4
        
    }
    return render(request, "business_owner_revenue_reports.html", context)



from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import BusinessOwnerPayment

@login_required
def business_owner_payment_details(request, payment_id):
    payment = get_object_or_404(BusinessOwnerPayment, id=payment_id)
    return render(request, "core/business_owner_payment_details.html", {"payment": payment})


# views.py
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings

def contact_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message_content = request.POST.get("message")

        if name and email and message_content:
            subject = f"New Contact Message from {name}"
            body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message_content}"

            try:
                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,         # From email (your Gmail)
                    [settings.EMAIL_RECIPIENT],          # Recipient email from .env
                    fail_silently=False
                )
                messages.success(request, "✅ Your message has been sent successfully!")
                return redirect("contact")  # Or any page you want to redirect to
            except Exception as e:
                messages.error(request, f"⚠️ An error occurred while sending your message: {e}")
                return redirect("contact")
        else:
            messages.warning(request, "⚠️ Please fill in all fields before submitting.")
            return redirect("contact")

    return render(request, "contact.html")

