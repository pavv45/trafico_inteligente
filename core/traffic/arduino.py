import serial
import time
import threading

# ===== CONFIGURACIÓN =====
PORT = 'COM3'  # 🔥 CAMBIAR según tu puerto (COM3, COM4, /dev/ttyUSB0, etc.)
BAUD_RATE = 9600

# Variables globales
arduino = None
# Lock para acceso thread-safe
serial_lock = threading.Lock()

# ===== MAPEO FÍSICO (Software -> Hardware) =====
# Zona detección → Semáforo físico que controla esa zona
LOGICAL_TO_PHYSICAL = {
    0: 'A',  # Zona A → Semáforo A (intersección izq)
    1: 'B',  # Zona B → Semáforo B (IDA, superior izq)
    2: 'E',  # Zona C → Semáforo E (IDA, inferior izq) - mismo grupo IDA
    3: 'D',  # Zona D → Semáforo D (intersección der)
    4: 'C',  # Zona E → Semáforo C (VUELTA, superior der) - mismo grupo VUELTA
    5: 'F'   # Zona F → Semáforo F (VUELTA, inferior der)
}


def connect_arduino():
    """Conectar al Arduino de forma segura"""
    global arduino
    
    try:
        if arduino and arduino.is_open:
            return arduino
            
        arduino = serial.Serial(PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Esperar que Arduino se inicialice
        
        # Limpiar buffer
        arduino.reset_input_buffer()
        arduino.reset_output_buffer()
        
        print(f"✅ Arduino conectado en {PORT}")
        return arduino
        
    except serial.SerialException as e:
        print(f"❌ Error conectando Arduino: {e}")
        print(f"💡 Verifica que el puerto {PORT} sea correcto")
        return None


def disconnect_arduino():
    """Desconectar Arduino de forma segura"""
    global arduino
    
    with serial_lock:
        if arduino and arduino.is_open:
            arduino.close()
            print("🔌 Arduino desconectado")


def send_command(lane, color):
    """
    Enviar comando al Arduino de forma segura
    
    Args:
        lane (int): Número de carril 0-5
        color (str): 'G', 'Y', 'R'
    """
    global arduino
    
    with serial_lock:
        # Actualizar estado global SIEMPRE (para que la maqueta digital funcione)
        try:
            from . import state
            state.light_states[lane] = color
        except Exception as e:
            print(f"⚠️ Error actualizando estado digital: {e}")

        try:
            if not arduino or not arduino.is_open:
                arduino = connect_arduino()
                
            if not arduino:
                # Si no hay Arduino, solo simulamos (la maqueta ya se actualizó arriba)
                # print("⚠️ Arduino no conectado (Modo Simulación)")
                return True # Retornamos True para que el controlador siga funcionando
            
            # Convertir número de carril lógico a letra física real
            # Si no está en el mapa, usar defecto (A+lane)
            lane_char = LOGICAL_TO_PHYSICAL.get(lane, chr(ord('A') + lane))
            
            command = f"{lane_char}{color}"
            
            # Enviar comando
            arduino.write(command.encode())
            arduino.flush()
            
            # Esperar confirmación
            time.sleep(0.1)
            if arduino.in_waiting > 0:
                response = arduino.readline().decode().strip()
                print(f"📡 Arduino responde: {response}")
            
            print(f"✅ Comando enviado: Carril {lane} ({lane_char}) → {color}")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando comando: {e}")
            # Intentar reconectar
            try:
                if arduino:
                    arduino.close()
                arduino = None
            except:
                pass
            return False


def set_light(lane, color='G'):
    """
    Cambiar luz de un semáforo específico
    
    Args:
        lane (int): Número de carril 0-5
        color (str): 'G' (verde), 'Y' (amarillo), 'R' (rojo)
    """
    if lane < 0 or lane > 5:
        print(f"⚠️ Carril inválido: {lane}. Debe ser 0-5")
        return False
        
    if color not in ['G', 'Y', 'R']:
        print(f"⚠️ Color inválido: {color}. Debe ser G, Y, o R")
        return False
    
    return send_command(lane, color)


def all_red():
    """Poner TODOS los semáforos en ROJO"""
    print("🔴 Poniendo todos los semáforos en ROJO...")
    success = True
    for i in range(6):
        if not set_light(i, 'R'):
            success = False
    return success


def test_sequence():
    """Secuencia de prueba para verificar que todo funciona"""
    print("🧪 Iniciando secuencia de prueba...")
    
    # Conectar
    if not connect_arduino():
        return
    
    # Prueba: encender cada semáforo en verde uno por uno
    for i in range(6):
        print(f"\n--- Probando semáforo {i} ({chr(ord('A')+i)}) ---")
        
        all_red()
        time.sleep(0.5)
        
        set_light(i, 'G')
        time.sleep(2)
        
        set_light(i, 'Y')
        time.sleep(1)
        
        set_light(i, 'R')
        time.sleep(0.5)
    
    print("\n✅ Prueba completada")
    all_red()


# Conectar al iniciar el módulo
connect_arduino()