from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from .camera import generate_frames
from .models import TrafficCycle, TrafficStats
from . import state

from .logic import decide_green, get_traffic_level
from .arduino import set_light, all_red, test_sequence
from .controller import (
    traffic_controller, 
    start_auto_cycle, 
    stop_auto_cycle,
    emergency_stop,
    get_controller_status
)


# =========================
# MAPA DE INTERSECCIONES
# =========================
def intersections_map(request):
    """Vista principal con mapa de intersecciones"""
    intersections = [
        {'id': 0, 'name': 'A - Avenida Ida', 'status': 'red'},
        {'id': 1, 'name': 'B - Avenida Vuelta', 'status': 'red'},
        {'id': 2, 'name': 'C - Lateral 1', 'status': 'red'},
        {'id': 3, 'name': 'D - Lateral 2', 'status': 'red'},
        {'id': 4, 'name': 'E - Lateral 3', 'status': 'red'},
        {'id': 5, 'name': 'F - Lateral 4', 'status': 'red'},
    ]
    return render(request, 'traffic/intersections.html', {
        'intersections': intersections
    })


# =========================
# DETALLE DE INTERSECCIÓN
# =========================
def intersection_detail(request, id):
    """Vista de detalle de una intersección específica"""
    lane_names = ['A - Avenida Ida', 'B - Avenida Vuelta', 
                  'C - Lateral 1', 'D - Lateral 2', 
                  'E - Lateral 3', 'F - Lateral 4']
    
    counts = getattr(state, 'vehicle_counts', [0] * 6)
    
    return render(request, 'traffic/intersection_detail.html', {
        'intersection': {
            'id': id,
            'name': lane_names[id] if 0 <= id < 6 else 'Desconocida',
            'vehicles': counts[id] if 0 <= id < 6 else 0
        }
    })


# =========================
# VIDEO STREAM (CÁMARA)
# =========================
def video_feed(request):
    """Stream de video en tiempo real desde la cámara"""
    return StreamingHttpResponse(
        generate_frames(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


# =========================
# ESTADO GENERAL (UI)
# =========================
def traffic_status(request):
    """
    Endpoint que devuelve el estado actual del tráfico
    Usado para actualizar el dashboard en tiempo real
    """
    counts = getattr(state, "vehicle_counts", [0] * 6)
    total = sum(counts)
    traffic_level = get_traffic_level(counts)
    
    # Determinar color del estado
    if traffic_level == 'high':
        status = "red"
    elif traffic_level == 'medium':
        status = "yellow"
    else:
        status = "green"
    
    controller_status = get_controller_status()
    
    return JsonResponse({
        "vehicles": total,
        "status": status,
        "traffic_level": traffic_level,
        "counts": counts,
        "lane_names": ['A', 'B', 'C', 'D', 'E', 'F'],
        "lights": getattr(state, "light_states", ['R'] * 6),  # Estado actual de cada semáforo
        "controller_running": controller_status['running'],
        "last_phase": controller_status.get('last_phase', -1)
    })


# =========================
# CICLO ÚNICO (MANUAL)
# =========================
@csrf_exempt
def auto_control(request):
    """
    Ejecutar UN SOLO CICLO del controlador
    Útil para control manual o testing
    """
    try:
        result = traffic_controller()
        
        # traffic_controller devuelve (phase_id, cycle_time) o (None, 0)
        if result is None or result[0] is None:
            return JsonResponse({
                "status": "success",
                "message": "Sin vehículos detectados - Sistema en espera",
                "counts": state.vehicle_counts
            })
        
        phase_id, cycle_time = result
        
        return JsonResponse({
            "status": "success",
            "phase_id": phase_id,
            "cycle_time": cycle_time,
            "counts": state.vehicle_counts,
            "message": f"Ciclo completado. Fase {phase_id} ejecutada por {cycle_time}s"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


# =========================
# CICLO AUTOMÁTICO
# =========================
@csrf_exempt
def start_automatic(request):
    """Iniciar ciclo automático continuo"""
    try:
        start_auto_cycle()
        
        return JsonResponse({
            "status": "success",
            "message": "Ciclo automático iniciado"
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


@csrf_exempt
def stop_automatic(request):
    """Detener ciclo automático"""
    try:
        stop_auto_cycle()
        
        return JsonResponse({
            "status": "success",
            "message": "Ciclo automático detenido"
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


# =========================
# CONTROL MANUAL
# =========================
@csrf_exempt
def manual_control(request, lane, color):
    """
    Control manual directo de un semáforo
    
    Args:
        lane (int): Carril 0-5
        color (str): 'green', 'yellow', 'red'
    """
    try:
        # Convertir nombre de color a letra
        color_map = {
            'green': 'G',
            'yellow': 'Y',
            'red': 'R'
        }
        
        color_code = color_map.get(color.lower())
        
        if not color_code:
            return JsonResponse({
                "status": "error",
                "message": f"Color inválido: {color}"
            }, status=400)
        
        if lane < 0 or lane > 5:
            return JsonResponse({
                "status": "error",
                "message": f"Carril inválido: {lane}"
            }, status=400)
        
        success = set_light(lane, color_code)
        
        if success:
            return JsonResponse({
                "status": "success",
                "lane": lane,
                "color": color,
                "message": f"Semáforo {lane} ({chr(ord('A')+lane)}) cambiado a {color}"
            })
        else:
            return JsonResponse({
                "status": "error",
                "message": "Error comunicando con Arduino"
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


# =========================
# TEST BÁSICO (COMPATIBILIDAD)
# =========================
@csrf_exempt
def test_green(request, lane):
    """Test simple: poner un carril en verde"""
    return manual_control(request, lane, 'green')


# =========================
# EMERGENCIA
# =========================
@csrf_exempt
def emergency(request):
    """Parada de emergencia: todos en rojo"""
    try:
        emergency_stop()
        
        return JsonResponse({
            "status": "success",
            "message": "Parada de emergencia ejecutada. Todos los semáforos en ROJO."
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


# =========================
# TEST DE HARDWARE
# =========================
@csrf_exempt
def hardware_test(request):
    """Ejecutar secuencia de prueba del hardware"""
    try:
        # Ejecutar en thread para no bloquear
        import threading
        thread = threading.Thread(target=test_sequence, daemon=True)
        thread.start()
        
        return JsonResponse({
            "status": "success",
            "message": "Secuencia de prueba iniciada. Revisa la consola y los semáforos."
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


# =========================
# GUARDAR DATOS (HISTORIAL)
# =========================
@csrf_exempt
def save_traffic_data(request, intersection_id=None):
    """Guardar registro de tráfico en la base de datos"""
    try:
        if intersection_id is None:
            intersection_id = 1
            
        TrafficRecord.objects.create(
            intersection_id=intersection_id,
            vehicle_count=sum(state.vehicle_counts),
            timestamp=now()
        )
        
        return JsonResponse({
            "status": "success",
            "message": "Datos guardados correctamente"
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


# =========================
# ESTADO DEL CONTROLADOR
# =========================
def controller_status(request):
    """Obtener estado completo del controlador"""
    status = get_controller_status()
    
    return JsonResponse({
        "status": "success",
        "data": status
    })


def emergency_stop_view(request):
    """Detener inmediatamente el sistema automático"""
    emergency_stop()
    return JsonResponse({
        'success': True,
        'message': 'Sistema detenido'
    })


# =========================
# REPORTES Y ESTADÍSTICAS
# =========================
def reports_view(request):
    """Vista de reportes con estadísticas del sistema"""
    from datetime import timedelta
    from django.db.models import Count, Avg, Sum
    from django.utils.timezone import now
    
    # Obtener parámetros de filtro
    days = int(request.GET.get('days', 7))  # Últimos 7 días por defecto
    end_date = now()
    start_date = end_date - timedelta(days=days)
    
    # Ciclos en el periodo
    cycles = TrafficCycle.objects.filter(
        timestamp__gte=start_date,
        timestamp__lte=end_date
    )
    
    # Estadísticas generales
    total_cycles = cycles.count()
    total_vehicles = cycles.aggregate(Sum('total_vehicles'))['total_vehicles__sum'] or 0
    avg_green = cycles.aggregate(Avg('green_time'))['green_time__avg'] or 0
    
    # Por fase
    phase_stats = cycles.values('phase').annotate(
        count=Count('id'),
        total_veh=Sum('total_vehicles'),
        avg_time=Avg('green_time')
    ).order_by('-count')
    
    # Vehículos por zona
    zone_stats = {
        'A': cycles.aggregate(Sum('zone_a_count'))['zone_a_count__sum'] or 0,
        'B': cycles.aggregate(Sum('zone_b_count'))['zone_b_count__sum'] or 0,
        'C': cycles.aggregate(Sum('zone_c_count'))['zone_c_count__sum'] or 0,
        'D': cycles.aggregate(Sum('zone_d_count'))['zone_d_count__sum'] or 0,
        'E': cycles.aggregate(Sum('zone_e_count'))['zone_e_count__sum'] or 0,
        'F': cycles.aggregate(Sum('zone_f_count'))['zone_f_count__sum'] or 0,
    }
    
    # Ciclos por día (para gráfica)
    from django.db.models.functions import TruncDate
    daily_cycles = cycles.annotate(
        date=TruncDate('timestamp')
    ).values('date').annotate(
        count=Count('id'),
        vehicles=Sum('total_vehicles')
    ).order_by('date')
    
    # Últimos 10 ciclos
    recent_cycles = cycles[:10]
    
    context = {
        'days_filter': days,
        'total_cycles': total_cycles,
        'total_vehicles': total_vehicles,
        'avg_green_time': round(avg_green, 1),
        'phase_stats': phase_stats,
        'zone_stats': zone_stats,
        'daily_cycles': list(daily_cycles),
        'recent_cycles': recent_cycles,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'traffic/reports.html', context)


# =========================
# CONFIGURACIÓN
# =========================
def settings_view(request):
    """Vista de configuración del sistema"""
    saved = False
    
    if request.method == 'POST':
        # Aquí se guardaría la configuración en un archivo o DB
        # Por ahora solo mostramos el mensaje de éxito
        saved = True
    
    return render(request, 'traffic/settings.html', {'saved': saved})


# =========================
# GESTIÓN DE USUARIOS
# =========================
from django.contrib.auth.models import User
from django.shortcuts import redirect

def users_view(request):
    """Vista de gestión de usuarios"""
    message = None
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password == password2:
            try:
                User.objects.create_user(username=username, email=email, password=password)
                message = f"Usuario {username} creado exitosamente"
            except Exception as e:
                message = f"Error: {str(e)}"
        else:
            message = "Las contraseñas no coinciden"
    
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'traffic/users.html', {'users': users, 'message': message})


def delete_user_view(request, user_id):
    """Eliminar un usuario"""
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            if not user.is_superuser or User.objects.filter(is_superuser=True).count() > 1:
                user.delete()
        except User.DoesNotExist:
            pass
    
    return redirect('users')
