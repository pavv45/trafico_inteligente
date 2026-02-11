"""
LÓGICA DE FASES REALISTA - Sistema de Semáforos Inteligente

GEOMETRÍA DE LA MAQUETA:
        C ↑    D ↑
          │      │
    ════════════════  A (IDA →)
    ════════════════  B (VUELTA ←)  
          │      │
        E ↓    F ↓

ANÁLISIS DE CONFLICTOS:
- A y B: CONFLICTO (opuestos en avenida, cruzan la intersección)
- C y E: CONFLICTO (misma calle vertical izquierda)
- D y F: CONFLICTO (misma calle vertical derecha)
- A y C,D,E,F: CONFLICTO (cruzan la intersección)
- B y C,D,E,F: CONFLICTO (cruzan la intersección)

COMPATIBILIDADES:
- C y D: OK (paralelos, no cruzan)
- E y F: OK (paralelos, no cruzan)
- C,D,E,F: DEPENDE (verificar que no sean opuestos)
"""

# ===== DEFINICIÓN DE FASES =====
# Cada fase define qué semáforos pueden estar en VERDE simultáneamente

# ===== FASES CON TIEMPOS PROPORCIONALES =====
# 
# DOS SUBFASES DE AVENIDA (trabajan por separado):
# - AVENIDA IDA: Semáforos B y E (pines 25-27 y 34-36) se encienden JUNTOS
# - AVENIDA VUELTA: Semáforos C y F (pines 28-30 y 37-39) se encienden JUNTOS
# 
# El tiempo en verde es PROPORCIONAL a la cantidad de vehículos en cada subfase
# 
# MAPEO FÍSICO DEL ARDUINO (según pines):
# - Pines 22,23,24 = Carril A (0) → INTERSECCIÓN IZQ
# - Pines 25,26,27 = Carril B (1) → AVENIDA IDA
# - Pines 28,29,30 = Carril C (2) → AVENIDA VUELTA
# - Pines 31,32,33 = Carril D (3) → INTERSECCIÓN DER
# - Pines 34,35,36 = Carril E (4) → AVENIDA IDA
# - Pines 37,38,39 = Carril F (5) → AVENIDA VUELTA

PHASES = [
    {
        'id': 1,
        'name': 'AVENIDA_IDA',
        'lanes': [1, 2],  # Zonas B+C = franja SUPERIOR → semáforos físicos B+E
        'description': 'Avenida superior - semáforos B y E en verde',
        'conflicts': [0, 3],
        'group': 'AVENIDA'
    },
    {
        'id': 2,
        'name': 'AVENIDA_VUELTA',
        'lanes': [4, 5],  # Zonas E+F = franja INFERIOR → semáforos físicos C+F
        'description': 'Avenida inferior - semáforos C y F en verde',
        'conflicts': [0, 3],
        'group': 'AVENIDA'
    },
    {
        'id': 3,
        'name': 'INTERSEC_A',
        'lanes': [0],  # A - Intersección izquierda
        'description': 'Intersección A en verde',
        'conflicts': [1, 2, 4, 5],  # Conflicto con avenida
        'group': 'INTERSECCION'
    },
    {
        'id': 4,
        'name': 'INTERSEC_D',
        'lanes': [3],  # D - Intersección derecha
        'description': 'Intersección D en verde',
        'conflicts': [1, 2, 4, 5],  # Conflicto con avenida
        'group': 'INTERSECCION'
    },
]

# ===== CONFIGURACIÓN DE TIEMPOS ADAPTATIVOS =====
# El tiempo en verde es MUY PROPORCIONAL a la cantidad de vehículos
# MÁS vehículos = MÁS tiempo en verde (diferencia muy notoria)

BASE_GREEN_TIME = 3       # Tiempo BASE mínimo (solo 3 segundos)
TIME_PER_VEHICLE = 5      # ¡5 segundos extra por CADA vehículo!
MAX_GREEN_TIME = 45       # Tiempo máximo en verde
MIN_GREEN_TIME = 5        # Tiempo mínimo absoluto
MIN_VEHICLES_FOR_PHASE = 1  # Mínimo de vehículos para activar una fase

# EJEMPLO DE CÓMO FUNCIONA AHORA:
# - 1 vehículo  → 3 + 5  =  8 segundos en verde
# - 2 vehículos → 3 + 10 = 13 segundos en verde
# - 3 vehículos → 3 + 15 = 18 segundos en verde
# - 4 vehículos → 3 + 20 = 23 segundos en verde
# - 8 vehículos → 3 + 40 = 43 segundos en verde
# 
# ¡La diferencia entre 1 y 4 vehículos es de 15 segundos!


def calculate_phase_priority(counts, phase):
    """
    Calcular prioridad de una fase según vehículos esperando
    
    Args:
        counts: Lista de 6 enteros con conteo de vehículos
        phase: Diccionario con definición de fase
        
    Returns:
        tuple: (total_vehicles, green_time)
    """
    # Contar vehículos en los carriles de esta fase
    total_vehicles = sum(counts[lane] for lane in phase['lanes'])
    
    # Calcular tiempo en verde PROPORCIONAL a los vehículos
    if total_vehicles == 0:
        green_time = 0
    else:
        # FÓRMULA: tiempo_base + (vehículos × tiempo_por_vehiculo)
        green_time = BASE_GREEN_TIME + (total_vehicles * TIME_PER_VEHICLE)
        green_time = min(green_time, MAX_GREEN_TIME)
        print(f"   ⏱️ CÁLCULO TIEMPO: {BASE_GREEN_TIME}s base + ({total_vehicles} carros × {TIME_PER_VEHICLE}s) = {green_time}s verde")
    
    return total_vehicles, green_time


def select_best_phase(counts, last_phase_id=-1):
    """
    Seleccionar la mejor fase según tráfico actual
    
    LÓGICA DE 4 FASES INDEPENDIENTES:
    - Cada fase tiene su tiempo proporcional a SUS vehículos
    - Se selecciona la fase con MÁS vehículos
    - Las fases del mismo grupo (AVENIDA o INTERSECCION) pueden ejecutarse consecutivamente
    
    Args:
        counts: Lista de 6 enteros con conteo de vehículos [A, B, C, D, E, F]
        last_phase_id: ID de la última fase ejecutada (1-4)
        
    Returns:
        tuple: (phase_dict, green_time) o (None, 0)
    """
    total_vehicles = sum(counts)
    
    if total_vehicles == 0:
        print("⏸️  NO hay vehículos - Sistema en espera")
        return None, 0
    
    # Calcular prioridad de cada una de las 4 fases
    phase_scores = []
    
    print(f"\n📊 ANÁLISIS DE TRÁFICO POR FASE:")
    print(f"   Conteo por carril: A={counts[0]}, B={counts[1]}, C={counts[2]}, D={counts[3]}, E={counts[4]}, F={counts[5]}")
    
    for phase in PHASES:
        vehicles, green_time = calculate_phase_priority(counts, phase)
        phase_scores.append({
            'phase': phase,
            'vehicles': vehicles,
            'green_time': green_time,
            'group': phase.get('group', 'UNKNOWN')
        })
        lanes_str = ', '.join([chr(ord('A')+l) for l in phase['lanes']])
        print(f"   → {phase['name']} ({lanes_str}): {vehicles} vehículos → {green_time}s verde")
    
    # Filtrar fases que tienen al menos 1 vehículo
    active_phases = [p for p in phase_scores if p['vehicles'] > 0]
    
    if not active_phases:
        print("⏸️  Ninguna fase tiene vehículos")
        return None, 0
    
    # Ordenar por cantidad de vehículos (mayor primero)
    active_phases.sort(key=lambda x: x['vehicles'], reverse=True)
    
    # Obtener la última fase y su grupo
    last_group = None
    for phase in PHASES:
        if phase['id'] == last_phase_id:
            last_group = phase.get('group', None)
            break
    
    from . import state as state_module
    ciclos_grupo_actual = getattr(state_module, 'ciclos_grupo_actual', 0)
    MAX_CICLOS_GRUPO = 3  # Máximo de ciclos seguidos para un grupo antes de cambiar
    
    # REGLA DE SELECCIÓN:
    # 1. Priorizar la fase con más vehículos
    # 2. PERO si el grupo actual lleva muchos ciclos, cambiar al otro grupo
    # 3. Dentro del mismo grupo, las fases pueden ejecutarse consecutivamente
    
    selected = None
    
    # Verificar si hay que cambiar de grupo por justicia
    best_phase = active_phases[0]
    best_group = best_phase['group']
    
    if last_group and ciclos_grupo_actual >= MAX_CICLOS_GRUPO:
        # Buscar una fase del OTRO grupo que tenga vehículos
        other_group_phases = [p for p in active_phases if p['group'] != last_group]
        if other_group_phases:
            selected = other_group_phases[0]
            print(f"\n⚖️ JUSTICIA: Grupo {last_group} tuvo {ciclos_grupo_actual} ciclos → Cambiando a {selected['group']}")
            state_module.ciclos_grupo_actual = 1
        else:
            # No hay fases activas del otro grupo, continuar con el actual
            selected = best_phase
            state_module.ciclos_grupo_actual = ciclos_grupo_actual + 1
    else:
        # Seleccionar la fase con más vehículos
        selected = best_phase
        
        # Actualizar contador de grupo
        if best_group == last_group:
            state_module.ciclos_grupo_actual = ciclos_grupo_actual + 1
        else:
            state_module.ciclos_grupo_actual = 1
    
    # Obtener datos de la fase seleccionada
    phase = selected['phase']
    green_time = selected['green_time']
    
    # Garantizar tiempo mínimo
    if green_time < MIN_GREEN_TIME:
        green_time = MIN_GREEN_TIME
    
    lanes_str = ', '.join([chr(ord('A')+l) for l in phase['lanes']])
    
    print(f"\n✅ FASE SELECCIONADA: {phase['name']}")
    print(f"   Grupo: {phase.get('group', 'N/A')}")
    print(f"   Carriles en verde: {lanes_str}")
    print(f"   Vehículos: {selected['vehicles']}")
    print(f"   Tiempo verde: {green_time}s")
    
    # Guardar última fase
    state_module.last_phase = phase['id']
    
    return phase, green_time


def get_lanes_to_activate(phase):
    """
    Obtener lista de carriles que deben ponerse en verde
    
    Args:
        phase: Diccionario con definición de fase
        
    Returns:
        list: Números de carriles (0-5)
    """
    return phase['lanes'] if phase else []


def get_traffic_level(counts):
    """
    Determinar nivel de congestión general
    
    Returns:
        str: 'none', 'low', 'medium', 'high', 'critical'
    """
    total = sum(counts) if counts else 0
    
    if total == 0:
        return 'none'
    elif total <= 3:
        return 'low'
    elif total <= 8:
        return 'medium'
    elif total <= 15:
        return 'high'
    else:
        return 'critical'


def should_system_run(counts):
    """
    Determinar si el sistema debe estar activo
    
    Returns:
        bool: True si hay vehículos
    """
    return sum(counts) > 0


# ===== FUNCIÓN DE DEBUG =====
def simulate_phase_selection(counts, last_phase=-1):
    """
    Simular selección de fase para testing
    """
    print("\n" + "="*60)
    print("🧪 SIMULACIÓN DE SELECCIÓN DE FASE")
    print("="*60)
    
    phase, time = select_best_phase(counts, last_phase)
    
    if phase is None:
        print("\n⏸️  Resultado: Sin fase activa (sin vehículos)")
    else:
        lanes = get_lanes_to_activate(phase)
        lanes_str = ', '.join([f"{l}({chr(ord('A')+l)})" for l in lanes])
        print(f"\n✅ Resultado: Fase {phase['id']} - {phase['name']}")
        print(f"   Carriles: {lanes_str}")
        print(f"   Tiempo: {time}s")
    
    print("="*60 + "\n")
    
    return phase, time


# ===== COMPATIBILIDAD CON CÓDIGO ANTERIOR =====
def decide_green(counts, last_green=-1):
    """
    Función de compatibilidad con el código anterior
    Ahora usa el sistema de fases
    
    Returns:
        tuple: (phase_dict, green_time) en lugar de (lane, time)
    """
    return select_best_phase(counts, last_green)


def calculate_green_time(vehicle_count):
    """
    Calcular tiempo en verde (función de compatibilidad)
    """
    if vehicle_count == 0:
        return 0
    
    green_time = BASE_GREEN_TIME + (vehicle_count * TIME_PER_VEHICLE)
    return min(int(green_time), MAX_GREEN_TIME)