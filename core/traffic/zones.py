"""
Zonas de detección de vehículos configuradas para tu maqueta

MAPEO FÍSICO DEL ARDUINO:
- A (carril 0): INTERSECCIÓN izquierda (pines 22,23,24)
- B (carril 1): AVENIDA (pines 25,26,27)
- C (carril 2): AVENIDA (pines 28,29,30)
- D (carril 3): INTERSECCIÓN derecha (pines 31,32,33)
- E (carril 4): AVENIDA (pines 34,35,36)
- F (carril 5): AVENIDA (pines 37,38,39)

RESUMEN:
- AVENIDA (4 semáforos): B, C, E, F
- INTERSECCIONES (2 semáforos): A, D

Coordenadas normalizadas (0-1):
- 0,0 = esquina superior izquierda
- 1,1 = esquina inferior derecha
"""

# ===== ZONAS DE DETECCIÓN =====
# Ajustar según la posición de la cámara

ZONES = [
    # === INTERSECCIONES (calles verticales) ===
    
    # A - Intersección izquierda (calle vertical, NO la casa)
    (0.22, 0.05, 0.48, 0.32),
    
    # === AVENIDA IDA ===
    
    # B - Avenida IDA (franja horizontal superior - lado izquierdo)
    (0.00, 0.30, 0.50, 0.48),
    
    # C - Avenida IDA (franja horizontal superior - lado derecho)
    (0.50, 0.28, 1.00, 0.46),
    
    # === INTERSECCIONES ===
    

    # D - Intersección derecha (calle vertical derecha)
    (0.58, 0.60, 0.82, 0.98),

    
    # === AVENIDA VUELTA ===
    
    # E - Avenida VUELTA (franja horizontal inferior - lado izquierdo)
    (0.00, 0.48, 0.50, 0.62),
    
    # F - Avenida VUELTA (franja horizontal inferior - lado derecho)
    (0.50, 0.46, 1.00, 0.60),
]

# Nombres descriptivos
ZONE_NAMES = [
    "A - Intersección Izq",
    "B - Avenida",
    "C - Avenida", 
    "D - Intersección Der",
    "E - Avenida",
    "F - Avenida"
]

# Colores para visualización (BGR para OpenCV)
ZONE_COLORS = [
    (0, 0, 255),    # A - ROJO (intersección)
    (255, 0, 0),    # B - AZUL (avenida)
    (255, 0, 0),    # C - AZUL (avenida)
    (0, 0, 255),    # D - ROJO (intersección)
    (255, 0, 0),    # E - AZUL (avenida)
    (255, 0, 0),    # F - AZUL (avenida)
]


# ===== FUNCIONES AUXILIARES =====

def get_zone_center(zone_index):
    """Obtener el centro de una zona"""
    if 0 <= zone_index < len(ZONES):
        x1, y1, x2, y2 = ZONES[zone_index]
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        return (cx, cy)
    return None


def is_point_in_zone(x, y, zone_index, frame_width, frame_height):
    """
    Verificar si un punto está dentro de una zona
    
    Args:
        x, y: Coordenadas del punto en píxeles
        zone_index: Índice de la zona (0-5)
        frame_width, frame_height: Dimensiones del frame
    """
    if 0 <= zone_index < len(ZONES):
        x1, y1, x2, y2 = ZONES[zone_index]
        
        # Convertir coordenadas normalizadas a píxeles
        px1 = int(x1 * frame_width)
        py1 = int(y1 * frame_height)
        px2 = int(x2 * frame_width)
        py2 = int(y2 * frame_height)
        
        return px1 <= x <= px2 and py1 <= y <= py2
    
    return False


# ===== GUÍA DE AJUSTE =====
"""
🎯 CÓMO AJUSTAR LAS ZONAS PARA QUE COINCIDAN EXACTAMENTE:

1. Ejecuta el servidor y abre: http://localhost:8000/traffic/video_feed/

2. Verás rectángulos de colores sobre el video (las zonas)

3. Ajusta los números en ZONES hasta que los rectángulos cubran tus calles:

   FORMATO: (x1, y1, x2, y2)
   
   x1, x2 = posición horizontal (0 = izquierda, 1 = derecha)
   y1, y2 = posición vertical (0 = arriba, 1 = abajo)

4. TIPS:
   - Avenida horizontal debe tener x1 bajo y x2 alto (para que sea larga)
   - Calles verticales deben tener y1 bajo y y2 alto (para que sean altas)
   - Evita que las zonas se superpongan

5. EJEMPLO DE AJUSTE:
   Si la zona A (avenida ida) aparece muy arriba:
   - Aumenta y1 y y2: (0.05, 0.40, 0.95, 0.52)
   
   Si la zona C (lateral izquierda) está muy a la derecha:
   - Disminuye x1 y x2: (0.03, 0.05, 0.20, 0.34)

📏 REFERENCIA VISUAL DE COORDENADAS:

    (0,0) ────────────────── (1,0)
      │                        │
      │    TU MAQUETA AQUÍ     │
      │                        │
    (0,1) ────────────────── (1,1)

AVENIDA (horizontal larga):
- x debe ir de ~0.05 a ~0.95 (casi todo el ancho)
- y debe ser estrecha, ej: 0.35 a 0.47

LATERALES (verticales cortas):
- x debe ser estrecha, ej: 0.08 a 0.25
- y debe ser larga, ej: 0.05 a 0.34
"""