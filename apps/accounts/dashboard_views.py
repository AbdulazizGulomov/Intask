# apps/accounts/dashboard_views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from config.admin_config import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_SESSION_KEY
from apps.accounts.models import User, WorkerProfile
from apps.jobs.models import Job, JobApplication

def admin_login(request):
    if request.session.get(ADMIN_SESSION_KEY):
        return redirect('admin_dashboard')
    
    error = None
    if request.method == 'POST':
        user = request.POST.get('username')
        pw = request.POST.get('password')
        if user == ADMIN_USERNAME and pw == ADMIN_PASSWORD:
            request.session[ADMIN_SESSION_KEY] = True
            return redirect('admin_dashboard')
        else:
            error = "Noto'g'ri login yoki parol"
            
    return render(request, "admin/login.html", {"error": error})

def admin_logout(request):
    if ADMIN_SESSION_KEY in request.session:
        del request.session[ADMIN_SESSION_KEY]
    return redirect('admin_login')

def admin_dashboard(request):
    if not request.session.get(ADMIN_SESSION_KEY):
        return redirect('admin_login')
    
    # Mock data for dashboard based on screenshot
    stats = {
        "total_orders": Job.objects.count(),
        "active_masters": WorkerProfile.objects.filter(is_completed=True).count(),
        "revenue": "12,450,000",
        "canceled": Job.objects.filter(is_active=False).count(),
    }
    
    new_orders = Job.objects.order_by('-created_at')[:5]
    
    return render(request, "admin/dashboard.html", {
        "stats": stats,
        "new_orders": new_orders,
    })
