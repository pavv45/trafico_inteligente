from django.urls import path
from . import views

urlpatterns = [
    # ===== PÁGINAS WEB =====
    path('intersections/', views.intersections_map, name='intersections'),
    path('intersections/<int:id>/', views.intersection_detail, name='intersection_detail'),
    
    # ===== VIDEO Y ESTADO =====
    path('video_feed/', views.video_feed, name='video_feed'),
    path('traffic_status/', views.traffic_status, name='traffic_status'),
    path('controller_status/', views.controller_status, name='controller_status'),
    
    # Reportes
    path('reports/', views.reports_view, name='reports'),
    
    # Configuración y Usuarios
    path('settings/', views.settings_view, name='settings'),
    path('users/', views.users_view, name='users'),
    path('users/delete/<int:user_id>/', views.delete_user_view, name='delete_user'),
    
    # ===== CONTROL AUTOMÁTICO =====
    path('auto/', views.auto_control, name='auto_control'),  # Un solo ciclo
    path('auto/start/', views.start_automatic, name='start_automatic'),  # Iniciar ciclo continuo
    path('auto/stop/', views.stop_automatic, name='stop_automatic'),  # Detener ciclo
    
    # ===== CONTROL MANUAL =====
    path('manual/<int:lane>/<str:color>/', views.manual_control, name='manual_control'),
    path('test/<int:lane>/', views.test_green, name='test_green'),  # Compatibilidad
    
    # ===== EMERGENCIA Y PRUEBAS =====
    path('emergency/', views.emergency, name='emergency'),
    path('hardware_test/', views.hardware_test, name='hardware_test'),
    
    # ===== DATOS =====
    path('save_data/', views.save_traffic_data, name='save_traffic_data'),
    path('save_data/<int:intersection_id>/', views.save_traffic_data, name='save_traffic_data_id'),
]