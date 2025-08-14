from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum,Avg,Count
from django.utils import timezone
from datetime import timedelta, date
from django.utils.timezone import now, timedelta
from .forms import PaymentForm, CustomLoginForm, BusinessForm
from .models import Payment,Attendance, RoutePoint,FraudAlert, ForecastRecord, AnalyticsSummary,RevenueRecord
import json
from django.http import JsonResponse
import pandas as pd
from prophet import Prophet
from sklearn.linear_model import LinearRegression

import plotly.graph_objs as go
import plotly.offline as opy
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
def custom_login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomLoginForm()
    return render(request, 'login.html', {'form': form})
@login_required
def dashboard_view(request):
    # Static target function — future-proofed
    def get_target(collector=None):
        return 2000  # static for now, dynamic later if needed

    # base queryset for the logged-in collector
    payments = Payment.objects.filter(collector=request.user)

    # filters from GET (optional)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    method = request.GET.get('method')
    if start_date:
        payments = payments.filter(date__date__gte=start_date)
    if end_date:
        payments = payments.filter(date__date__lte=end_date)
    if method:
        payments = payments.filter(method=method)

    # daily aggregates for the last 7 days (use filtered payments)
    today = now().date()
    last_week = today - timedelta(days=6)

    daily_qs = (
        payments
        .filter(date__date__range=[last_week, today])
        .values('date__date')
        .annotate(total=Sum('amount'))
        .order_by('date__date')
    )

    labels = [entry['date__date'].strftime('%Y-%m-%d') for entry in daily_qs]
    data = [float(entry['total']) for entry in daily_qs]

    # revenue by collector (from filtered payments)
    collector_qs = (
        payments
        .values('collector__username')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    collector_labels = [c['collector__username'] or 'Unknown' for c in collector_qs]
    collector_amounts = [float(c['total']) for c in collector_qs]

    # 🔍 GLOBAL ANALYTICS (from all payments)
    total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
    avg_daily = Payment.objects.aggregate(Avg('amount'))['amount__avg'] or 0
    top_collector = (
        Payment.objects
        .values('collector__username')
        .annotate(total=Sum('amount'))
        .order_by('-total')
        .first()
    )

    # Total number of payments
    total_payments_count = Payment.objects.count()

    # Average payment amount for the logged-in collector
    collector_avg_payment = payments.aggregate(avg=Avg('amount'))['avg'] or 0

    # Peak collection day (globally)
    peak_day = (
        Payment.objects
        .values('date__date')
        .annotate(total=Sum('amount'))
        .order_by('-total')
        .first()
    )

    # Most used payment method
    most_used_method = (
        Payment.objects
        .values('method')
        .annotate(count=Count('id'))
        .order_by('-count')
        .first()
    )

    # Collector's contribution to total revenue
    collector_total = payments.aggregate(total=Sum('amount'))['total'] or 0
    collector_contribution_pct = (collector_total / total_revenue * 100) if total_revenue else 0

    # Collector target and progress
    collector_target = get_target(request.user)
    collector_progress_pct = (collector_total / collector_target * 100) if collector_target else 0
    
    

    # DEBUG prints
    print("DEBUG dashboard_view labels:", labels)
    print("DEBUG dashboard_view data:", data)
    print("DEBUG collectors:", collector_labels, collector_amounts)
    print("DEBUG total_revenue:", total_revenue)
    print("DEBUG avg_daily:", avg_daily)
    print("DEBUG top_collector:", top_collector)
    print("DEBUG collector_target:", collector_target)
    print("DEBUG collector_progress_pct:", collector_progress_pct)
 # Collector analytics
    collector_total = payments.aggregate(total=Sum('amount'))['total'] or 0
    collector_target = get_target(request.user)
    collector_progress_pct = (collector_total / collector_target * 100) if collector_target else 0
    collector_avg_payment = payments.aggregate(avg=Avg('amount'))['avg'] or 0

    # Daily Target Tracker
    today_total = payments.filter(date__date=today).aggregate(total=Sum('amount'))['total'] or 0
    today_progress_pct = (today_total / collector_target * 100) if collector_target else 0

    # Streak Counter 🔥
    streak = 0
    for i in range(7):
        day = today - timedelta(days=i)
        day_total = payments.filter(date__date=day).aggregate(total=Sum('amount'))['total'] or 0
        if day_total >= collector_target:
            streak += 1
        else:
            break

    # Milestone Badges
    milestones = []
    if collector_total >= 5000:
        milestones.append("GH₵5,000+")
    if collector_total >= 10000:
        milestones.append("GH₵10,000+")
    if collector_total >= 20000:
        milestones.append("GH₵20,000+")

    

    period = request.GET.get('period', 'monthly')
    start_date = timezone.now() - timedelta(days=30 if period == 'monthly' else 7)

    # Peer Comparison (Global)
    peer_qs = Payment.objects.filter(date__gte=start_date) \
    .values('collector__username') \
    .annotate(total=Sum('amount')) \
    .order_by('-total')

    peer_rank = None
    top_3_peers = peer_qs[:3]
    peer_labels = []
    peer_values = []

    for idx, peer in enumerate(peer_qs):
        peer_labels.append(peer['collector__username'])
        peer_values.append(float(peer['total']))
        if peer['collector__username'] == request.user.username:
            peer_rank = idx + 1

    peer_total = len(peer_qs)



    # Global analytics
    total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
    avg_daily = Payment.objects.aggregate(Avg('amount'))['amount__avg'] or 0
    top_collector = Payment.objects.values('collector__username').annotate(total=Sum('amount')).order_by('-total').first()
    total_payments_count = Payment.objects.count()
    peak_day = Payment.objects.values('date__date').annotate(total=Sum('amount')).order_by('-total').first()
    most_used_method = Payment.objects.values('method').annotate(count=Count('id')).order_by('-count').first()
    collector_contribution_pct = (collector_total / total_revenue * 100) if total_revenue else 0

    context = {
        'payments': payments.order_by('-date'),
        'start_date': start_date,
        'end_date': end_date,
        'method': method,
        'labels': json.dumps(labels),
        'data': json.dumps(data),
        'collector_labels': json.dumps([c['collector__username'] for c in peer_qs]),
        'collector_amounts': json.dumps([float(c['total']) for c in peer_qs]),
        # Analytics
        'total_revenue': total_revenue,
        'avg_daily': avg_daily,
        'top_collector': top_collector,
        'total_payments_count': total_payments_count,
        'collector_avg_payment': collector_avg_payment,
        'peak_day': peak_day,
        'most_used_method': most_used_method,
        'collector_contribution_pct': round(collector_contribution_pct, 2),
        'collector_target': collector_target,
        'collector_total': collector_total,
        'collector_progress_pct': round(collector_progress_pct, 2),
        # Motivation Features
        'today_total': today_total,
        'today_progress_pct': round(today_progress_pct, 2),
        'streak': streak,
        'milestones': milestones,
        'peer_rank': peer_rank,
        'peer_total': len(peer_qs),
        'peer_rank': peer_rank,
        'peer_total': peer_total,
        'top_3_peers': top_3_peers,
        'peer_labels': json.dumps(peer_labels),
        'peer_values': json.dumps(peer_values),
    }
    return render(request, 'dashboard.html', context)


@login_required
def submit_payment_view(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.collector = request.user
            payment.save()
            return render(request, 'payment_success.html', {'payment': payment})
    else:
        form = PaymentForm()
    return render(request, 'submit_payment.html', {'form': form})

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

@login_required
def register_business(request):
    if request.method == 'POST':
        form = BusinessForm(request.POST)
        if form.is_valid():
            business = form.save(commit=False)
            business.registered_by = request.user
            business.save()
            return redirect('business_success')
    else:
        form = BusinessForm()

    return render(request, 'core/register_business.html', {'form': form})

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




