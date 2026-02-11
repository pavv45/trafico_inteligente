"""
Estado global del sistema de semáforos
Usado para compartir información entre módulos
"""

import threading

# Lock para acceso thread-safe
_state_lock = threading.Lock()

# ===== ESTADO DE LA CÁMARA =====
camera_active = False
vehicle_count = 0
vehicle_counts = [0, 0, 0, 0, 0, 0]  # Conteo por cada carril

# ===== ESTADO DEL CONTROLADOR =====
last_green = -1  # Último carril que tuvo luz verde
current_phase = "RED"  # Fase actual: GREEN, YELLOW, RED
last_phase = -1  # Última fase ejecutada (1=avenida, 2=intersecciones)
light_states = ['R', 'R', 'R', 'R', 'R', 'R']  # Estado de cada semáforo (R/Y/G)

# ===== CONTADORES PARA JUSTICIA (evitar hambruna) =====
ciclos_grupo_actual = 0  # Cuántos ciclos seguidos ha tenido el grupo actual (AVENIDA o INTERSECCION)


def update_vehicle_counts(new_counts):
    """Actualizar conteo de vehículos de forma thread-safe"""
    global vehicle_counts, vehicle_count
    
    with _state_lock:
        vehicle_counts = new_counts
        vehicle_count = sum(new_counts)


def get_vehicle_counts():
    """Obtener conteo actual de forma thread-safe"""
    with _state_lock:
        return vehicle_counts.copy()


def update_last_green(lane):
    """Actualizar último carril con luz verde"""
    global last_green
    
    with _state_lock:
        last_green = lane


def reset_state():
    """Resetear todo el estado"""
    global camera_active, vehicle_count, vehicle_counts, last_green, current_phase
    
    with _state_lock:
        camera_active = False
        vehicle_count = 0
        vehicle_counts = [0, 0, 0, 0, 0, 0]
        last_green = -1
        current_phase = "RED"


def get_full_state():
    """Obtener snapshot completo del estado"""
    with _state_lock:
        return {
            'camera_active': camera_active,
            'vehicle_count': vehicle_count,
            'vehicle_counts': vehicle_counts.copy(),
            'last_green': last_green,
            'current_phase': current_phase
        }