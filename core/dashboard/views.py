from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Sum, Count, Avg
from traffic.models import TrafficCycle

@login_required
def home(request):
    """Dashboard principal con estadísticas reales del sistema"""
    
    # Obtener datos del día actual
    today_start = now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_cycles = TrafficCycle.objects.filter(timestamp__gte=today_start)
    
    # Últimas 24 horas
    last_24h = now() - timedelta(hours=24)
    cycles_24h = TrafficCycle.objects.filter(timestamp__gte=last_24h)
    
    # KPIs
    total_vehicles_today = today_cycles.aggregate(Sum('total_vehicles'))['total_vehicles__sum'] or 0
    cycles_count_today = today_cycles.count()
    avg_green_time = today_cycles.aggregate(Avg('green_time'))['green_time__avg'] or 0
    
    # Flujo vehicular por hora (últimas 24 horas)
    hourly_data = []
    for i in range(24):
        hour_start = last_24h + timedelta(hours=i)
        hour_end = hour_start + timedelta(hours=1)
        vehicles = TrafficCycle.objects.filter(
            timestamp__gte=hour_start,
            timestamp__lt=hour_end
        ).aggregate(Sum('total_vehicles'))['total_vehicles__sum'] or 0
        hourly_data.append(vehicles)
    
    # Total de ciclos ejecutados (histórico)
    total_cycles_all_time = TrafficCycle.objects.count()
    
    context = {
        'total_vehicles_today': total_vehicles_today,
        'cycles_count_today': cycles_count_today,
        'total_cycles_all_time': total_cycles_all_time,
        'avg_green_time': round(avg_green_time, 1),
        'hourly_data': hourly_data,
    }
    
    return render(request, 'dashboard/dashboard.html', context)