from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone

from .forms import PaymentForm, CustomLoginForm, BusinessForm
from .models import Payment

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
    payments = Payment.objects.filter(collector=request.user)
    return render(request, 'dashboard.html', {'payments': payments})

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

    context = {
        'payments': payments.order_by('-date'),
        'start_date': start_date,
        'end_date': end_date,
        'method': method,
        'total_amount': total_amount,
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

