import time
import threading
from .logic import select_best_phase, get_lanes_to_activate, should_system_run, get_traffic_level
from .arduino import set_light, all_red
from . import state

# ===== CONFIGURACIÓN DE TIEMPOS (REALISTAS) =====
YELLOW_TIME = 3          # Tiempo en amarillo (segundos) - Semáforo real: 3-4s
RED_CLEARANCE = 2        # Tiempo de seguridad con todos en rojo (segundos)
WAIT_INTERVAL = 5        # Segundos entre verificaciones cuando no hay tráfico

# NOTA: En semáforos reales:
# - Amarillo: 3-4 segundos (suficiente para que los carros frenen)
# - Todo rojo: 1-2 segundos (clearance de seguridad)
# - Verde mínimo: 15-20 segundos (ver logic.py)

# Control del ciclo
controller_running = False
controller_thread = None
cycle_in_progress = False  # NUEVO: indicador de ciclo activo


def execute_phase(phase, green_time):
    """
    Ejecutar UNA FASE completa del sistema
    Puede activar MÚLTIPLES semáforos en verde simultáneamente
    """
    global cycle_in_progress
    
    lanes = get_lanes_to_activate(phase)
    lanes_str = ', '.join([f"{l}({chr(ord('A')+l)})" for l in lanes])
    
    print(f"\n{'='*60}")
    print(f"🚦 EJECUTANDO FASE: {phase['name']}")
    print(f"{'='*60}")
    print(f"🟢 Carriles en VERDE: {lanes_str}")
    print(f"⏱️  Tiempo: {green_time} segundos")
    
    cycle_in_progress = True  # MARCAR QUE ESTAMOS EN CICLO
    
    # FASE 1: SEGURIDAD - Todos en ROJO
    print(f"\n🔴 Fase 1: TODOS en ROJO por {RED_CLEARANCE}s (seguridad)")
    all_red()
    time.sleep(RED_CLEARANCE)
    
    # FASE 2: VERDE - Activar semáforos de la fase
    print(f"🟢 Fase 2: Activando semáforos...")
    for lane in lanes:
        print(f"   → Carril {lane} ({chr(ord('A')+lane)}) en VERDE")
        set_light(lane, 'G')
        time.sleep(0.2)  # Pausa entre activaciones
    
    print(f"⏱️  Manteniendo verde por {green_time}s...")
    time.sleep(green_time)
    
    # FASE 3: AMARILLO
    print(f"🟡 Fase 3: Amarillo en carriles activos...")
    for lane in lanes:
        print(f"   → Carril {lane} ({chr(ord('A')+lane)}) en AMARILLO")
        set_light(lane, 'Y')
        time.sleep(0.2)
    
    time.sleep(YELLOW_TIME)
    
    # FASE 4: ROJO
    print(f"🔴 Fase 4: Rojo en carriles activos...")
    for lane in lanes:
        print(f"   → Carril {lane} ({chr(ord('A')+lane)}) en ROJO")
        set_light(lane, 'R')
        time.sleep(0.2)
    
    cycle_in_progress = False  # CICLO TERMINADO
    
    total_time = RED_CLEARANCE + green_time + YELLOW_TIME
    print(f"\n✅ FASE COMPLETADA en {total_time} segundos")
    print(f"{'='*60}\n")
    
    return phase['id'], total_time


def traffic_controller():
    """
    Ejecutar UN CICLO INTELIGENTE del controlador
    
    IMPORTANTE: CONGELA los conteos al inicio para evitar cambios durante el ciclo
    
    NUEVA LÓGICA AVENIDAS:
    - Si el grupo ganador es AVENIDA, ejecuta AMBAS subfases (IDA y VUELTA)
    - Cada subfase tiene su propio tiempo proporcional a sus vehículos
    """
    from .logic import PHASES, calculate_phase_priority
    
    # 🔒 CONGELAR conteos al inicio del ciclo
    frozen_counts = getattr(state, "vehicle_counts", [0] * 6).copy()
    last_phase = getattr(state, "last_phase", -1)
    
    print(f"\n🔒 CONTEOS CONGELADOS PARA ESTE CICLO: {frozen_counts}")
    
    # Verificar si hay vehículos
    if not should_system_run(frozen_counts):
        print(f"\n⏸️  SISTEMA EN ESPERA - Sin vehículos detectados")
        all_red()
        return None, 0
    
    # Seleccionar mejor fase CON LOS CONTEOS CONGELADOS
    phase, green_time = select_best_phase(frozen_counts, last_phase)
    
    if phase is None or green_time == 0:
        print(f"\n⏸️  NO se ejecutó ciclo - Sin vehículos suficientes")
        all_red()
        return None, 0
    
    # Verificar si la fase seleccionada es del grupo AVENIDA o INTERSECCION
    from .logic import PHASES, calculate_phase_priority, MIN_GREEN_TIME
    
    group_name = phase.get('group')
    
    if group_name == 'AVENIDA':
        # ============================================
        # AVENIDA: ARRANQUE SIMULTÁNEO, APAGADO ESCALONADO
        # ============================================
        print(f"\n🚗 GRUPO AVENIDA - ARRANQUE SIMULTÁNEO")
        
        fase_a = None  # IDA
        fase_b = None  # VUELTA
        for p in PHASES:
            if p['name'] == 'AVENIDA_IDA':
                fase_a = p
            elif p['name'] == 'AVENIDA_VUELTA':
                fase_b = p
        
        veh_a, tiempo_a = calculate_phase_priority(frozen_counts, fase_a)
        veh_b, tiempo_b = calculate_phase_priority(frozen_counts, fase_b)
        
        label_a = "SUPERIOR (B+C → sem B+E)"
        label_b = "INFERIOR (E+F → sem C+F)"
        
    elif group_name == 'INTERSECCION':
        # ============================================
        # INTERSECCIONES: ARRANQUE SIMULTÁNEO, APAGADO ESCALONADO
        # ============================================
        print(f"\n🏙️ GRUPO INTERSECCIONES - ARRANQUE SIMULTÁNEO")
        
        fase_a = None  # INTERSEC_A
        fase_b = None  # INTERSEC_D
        for p in PHASES:
            if p['name'] == 'INTERSEC_A':
                fase_a = p
            elif p['name'] == 'INTERSEC_D':
                fase_b = p
        
        veh_a, tiempo_a = calculate_phase_priority(frozen_counts, fase_a)
        veh_b, tiempo_b = calculate_phase_priority(frozen_counts, fase_b)
        
        label_a = "INTERSEC_A (A)"
        label_b = "INTERSEC_D (D)"
    
    else:
        # Fase desconocida, ejecutar normalmente
        phase_id, cycle_time = execute_phase(phase, green_time)
        state.last_phase = phase_id
        return phase_id, cycle_time
    
    # ============================================
    # LÓGICA COMÚN: ARRANQUE SIMULTÁNEO + APAGADO ESCALONADO
    # Si una subfase tiene 0 carros, NO se enciende
    # ============================================
    
    print(f"   🔵 {label_a}: {veh_a} carros → {tiempo_a}s verde")
    print(f"   🔵 {label_b}: {veh_b} carros → {tiempo_b}s verde")
    
    cycle_in_progress = True
    
    # PASO 1: SEGURIDAD - Todos en ROJO
    print(f"\n🔴 PASO 1: Todos en ROJO por {RED_CLEARANCE}s (seguridad)")
    all_red()
    time.sleep(RED_CLEARANCE)
    
    # ============================================
    # ARRANQUE SIMULTÁNEO + APAGADO ESCALONADO
    # Los 4 semáforos de avenida arrancan en VERDE al mismo tiempo
    # El que tiene MENOS carros se apaga primero
    # ============================================
    
    # Caso 1: AMBAS tienen vehículos → arranque simultáneo
    if veh_a > 0 and veh_b > 0:
        # Determinar cuál tiene más y cuál menos tiempo
        if tiempo_a >= tiempo_b:
            fase_larga, fase_corta = fase_a, fase_b
            tiempo_largo, tiempo_corto = tiempo_a, tiempo_b
            label_larga, label_corta = label_a, label_b
        else:
            fase_larga, fase_corta = fase_b, fase_a
            tiempo_largo, tiempo_corto = tiempo_b, tiempo_a
            label_larga, label_corta = label_b, label_a
        
        # PASO 2: TODOS en VERDE al mismo tiempo
        print(f"\n🟢 PASO 2: TODOS en VERDE")
        all_lanes = fase_a['lanes'] + fase_b['lanes']
        for lane in all_lanes:
            print(f"   → Carril {lane} ({chr(ord('A')+lane)}) en VERDE")
            set_light(lane, 'G')
            time.sleep(0.2)
        
        # PASO 3: Esperar el tiempo de la subfase CORTA (ambas en verde)
        print(f"\n⏱️  PASO 3: Todos en verde por {tiempo_corto}s...")
        time.sleep(tiempo_corto)
        
        # PASO 4: La de MENOS carros se apaga (la otra sigue en verde)
        tiempo_restante = tiempo_largo - tiempo_corto
        
        if tiempo_restante > 0:
            print(f"\n🟡 PASO 4: {label_corta} se apaga (menos carros)")
            for lane in fase_corta['lanes']:
                set_light(lane, 'Y')
                time.sleep(0.2)
            time.sleep(YELLOW_TIME)
            
            for lane in fase_corta['lanes']:
                set_light(lane, 'R')
                time.sleep(0.2)
            
            # PASO 5: La larga sigue en verde el tiempo restante
            print(f"\n🟢 PASO 5: {label_larga} sigue VERDE por {tiempo_restante}s más...")
            time.sleep(tiempo_restante)
        
        # PASO 6: La de MÁS carros también se apaga
        print(f"\n🟡 PASO 6: {label_larga} se apaga")
        for lane in fase_larga['lanes']:
            set_light(lane, 'Y')
            time.sleep(0.2)
        time.sleep(YELLOW_TIME)
        
        for lane in fase_larga['lanes']:
            set_light(lane, 'R')
            time.sleep(0.2)
        
        total_time = RED_CLEARANCE + tiempo_largo + YELLOW_TIME
        if tiempo_restante > 0:
            total_time += YELLOW_TIME
    
    # Caso 2: SOLO una tiene vehículos → solo encender esa
    elif veh_a > 0:
        print(f"\n🟢 Solo {label_a} tiene carros")
        for lane in fase_a['lanes']:
            set_light(lane, 'G')
            time.sleep(0.2)
        
        time.sleep(tiempo_a)
        
        for lane in fase_a['lanes']:
            set_light(lane, 'Y')
            time.sleep(0.2)
        time.sleep(YELLOW_TIME)
        for lane in fase_a['lanes']:
            set_light(lane, 'R')
            time.sleep(0.2)
        
        total_time = RED_CLEARANCE + tiempo_a + YELLOW_TIME
    
    elif veh_b > 0:
        print(f"\n🟢 Solo {label_b} tiene carros")
        for lane in fase_b['lanes']:
            set_light(lane, 'G')
            time.sleep(0.2)
        
        time.sleep(tiempo_b)
        
        for lane in fase_b['lanes']:
            set_light(lane, 'Y')
            time.sleep(0.2)
        time.sleep(YELLOW_TIME)
        for lane in fase_b['lanes']:
            set_light(lane, 'R')
            time.sleep(0.2)
        
        total_time = RED_CLEARANCE + tiempo_b + YELLOW_TIME
    
    else:
        # Ninguna tiene carros (no debería llegar aquí)
        cycle_in_progress = False
        return None, 0
    
    cycle_in_progress = False
    
    print(f"\n✅ CICLO {group_name} COMPLETO en {total_time}s")
    print(f"   {label_a}: {veh_a} carros ({tiempo_a}s) | {label_b}: {veh_b} carros ({tiempo_b}s)")
    
    # Guardar datos en la base de datos
    try:
        from .models import TrafficCycle
        TrafficCycle.objects.create(
            phase=phase['name'],
            zone_a_count=frozen_counts[0],
            zone_b_count=frozen_counts[1],
            zone_c_count=frozen_counts[2],
            zone_d_count=frozen_counts[3],
            zone_e_count=frozen_counts[4],
            zone_f_count=frozen_counts[5],
            green_time=max(tiempo_a, tiempo_b),
            total_vehicles=sum(frozen_counts)
        )
        print(f"💾 Datos guardados en BD")
    except Exception as e:
        print(f"⚠️  Error guardando datos: {e}")
    
    state.last_phase = phase['id']
    return phase['id'], total_time


def smart_auto_cycle():
    """
    Ciclo automático INTELIGENTE con sistema de FASES
    
    NUEVA LÓGICA:
    - Congela conteos al inicio de cada ciclo
    - No se interrumpe aunque los conteos cambien
    - Espera a que termine el ciclo completo antes de tomar nuevas decisiones
    """
    global controller_running, cycle_in_progress
    controller_running = True
    
    print("\n" + "="*60)
    print("🚀 SISTEMA INTELIGENTE DE FASES - INICIADO")
    print("="*60)
    print("📡 Modo: Automático continuo")
    print("🎯 Objetivo: Reducir congestión vehicular")
    print("⚙️  Lógica: Fases realistas + Tiempos adaptativos")
    print("🔒 Estabilidad: Conteos congelados por ciclo")
    print("="*60 + "\n")
    
    all_red()
    
    while controller_running:
        try:
            # Obtener conteo actual
            counts = getattr(state, "vehicle_counts", [0] * 6)
            
            # Verificar si hay vehículos
            if should_system_run(counts):
                # HAY TRÁFICO: Ejecutar ciclo inteligente
                # Los conteos se congelarán DENTRO de traffic_controller()
                phase_id, cycle_time = traffic_controller()
                
                # Pausa breve antes del siguiente ciclo
                if controller_running:
                    print(f"⏸️  Pausa de 2s antes del siguiente análisis...\n")
                    time.sleep(2)
            else:
                # SIN TRÁFICO: Esperar
                print(f"⏸️  Sin tráfico - Verificando en {WAIT_INTERVAL}s...")
                all_red()
                time.sleep(WAIT_INTERVAL)
        
        except Exception as e:
            print(f"❌ Error en ciclo automático: {e}")
            import traceback
            traceback.print_exc()
            cycle_in_progress = False
            all_red()
            time.sleep(5)
    
    print("\n⏹️  SISTEMA INTELIGENTE DETENIDO")
    cycle_in_progress = False
    all_red()


def start_auto_cycle():
    """Iniciar ciclo automático inteligente"""
    global controller_running, controller_thread
    
    if controller_running:
        print("⚠️ El sistema ya está corriendo")
        return False
    
    controller_thread = threading.Thread(target=smart_auto_cycle, daemon=True)
    controller_thread.start()
    
    print("✅ Sistema automático iniciado")
    return True


def stop_auto_cycle():
    """Detener el ciclo automático"""
    global controller_running
    
    if not controller_running:
        print("⚠️ El sistema no está corriendo")
        return False
    
    print("\n⏳ Deteniendo sistema...")
    controller_running = False
    
    # Esperar que termine el ciclo actual
    if controller_thread:
        print("⏳ Esperando que termine el ciclo actual...")
        controller_thread.join(timeout=40)
    
    all_red()
    print("✅ Sistema detenido. Todos en ROJO")
    
    return True


def emergency_stop():
    """Parada de emergencia"""
    global controller_running, cycle_in_progress
    
    print("\n🚨 PARADA DE EMERGENCIA")
    controller_running = False
    cycle_in_progress = False
    all_red()
    print("✅ Todos los semáforos en ROJO")


def get_controller_status():
    """Obtener estado actual del controlador"""
    counts = getattr(state, 'vehicle_counts', [0] * 6)
    
    return {
        'running': controller_running,
        'cycle_in_progress': cycle_in_progress,
        'last_phase': getattr(state, 'last_phase', -1),
        'vehicle_counts': counts,
        'total_vehicles': sum(counts),
        'traffic_level': get_traffic_level(counts),
        'has_traffic': should_system_run(counts)
    }


def manual_phase(phase_id, custom_time=None):
    """
    Ejecutar una fase específica manualmente
    """
    from .logic import PHASES, calculate_phase_priority
    
    phase = next((p for p in PHASES if p['id'] == phase_id), None)
    
    if not phase:
        print(f"⚠️ Fase inválida: {phase_id}")
        return False
    
    counts = getattr(state, "vehicle_counts", [0] * 6)
    
    if custom_time:
        green_time = custom_time
    else:
        _, green_time = calculate_phase_priority(counts, phase)
        if green_time == 0:
            green_time = 5
    
    print(f"\n🎮 CICLO MANUAL: Fase {phase_id} - {phase['name']}")
    
    execute_phase(phase, green_time)
    
    print(f"✅ Ciclo manual completado")
    return True


def test_phase_system():
    """Probar el sistema de fases con diferentes escenarios"""
    print("\n🧪 PRUEBA DEL SISTEMA DE FASES\n")
    
    scenarios = [
        ([0, 0, 0, 0, 0, 0], "Sin tráfico"),
        ([5, 0, 0, 0, 0, 0], "Solo avenida IDA"),
        ([0, 5, 0, 0, 0, 0], "Solo avenida VUELTA"),
        ([0, 0, 3, 3, 0, 0], "Laterales superiores (C y D)"),
        ([0, 0, 0, 0, 3, 3], "Laterales inferiores (E y F)"),
        ([3, 2, 1, 1, 1, 1], "Tráfico mixto"),
    ]
    
    for counts, description in scenarios:
        print(f"\n{'='*60}")
        print(f"📋 Escenario: {description}")
        
        state.vehicle_counts = counts
        phase_id, time_used = traffic_controller()
        
        time.sleep(2)
    
    print("\n✅ Prueba completada")