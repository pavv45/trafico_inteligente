import cv2
import numpy as np
from ultralytics import YOLO
from .zones import ZONES, ZONE_NAMES, ZONE_COLORS
from . import state

# Cargar modelo YOLO
model = YOLO("yolov8n.pt")

# Clases de vehículos en COCO dataset
VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck

# ===== CONFIGURACIÓN DE DETECCIÓN =====
MIN_CONFIDENCE = 0.25       # Bajo para capturar detecciones intermitentes
MIN_VEHICLE_SIZE = 100      # Muy bajo para detectar carritos pequeños desde lejos
MAX_VEHICLE_SIZE = 100000   # Máximo grande por si la cámara está cerca
MIN_BRIGHTNESS = 1          # 🔥 MODIFICADO: Muy bajo para permitir funcionamiento en oscuridad (maqueta)

# ===== SISTEMA DE ESTABILIZACIÓN =====
STABILITY_FRAMES = 10
UPDATE_INTERVAL = 5

# Buffers para estabilización
detection_history = []
stable_counts = [0] * 6
frame_counter = 0


def is_image_valid(frame):
    """Verificar si la imagen tiene suficiente luz"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    avg_brightness = np.mean(gray)
    
    if avg_brightness < MIN_BRIGHTNESS:
        return False, avg_brightness
    
    return True, avg_brightness


def is_valid_vehicle(box, frame_width, frame_height):
    """Verificar si la detección es un vehículo válido"""
    confidence = float(box.conf[0])
    if confidence < MIN_CONFIDENCE:
        return False
    
    x1, y1, x2, y2 = map(int, box.xyxy[0])
    width = x2 - x1
    height = y2 - y1
    area = width * height
    
    if area < MIN_VEHICLE_SIZE or area > MAX_VEHICLE_SIZE:
        return False
    
    aspect_ratio = width / height if height > 0 else 0
    if aspect_ratio < 0.2 or aspect_ratio > 6.0:
        return False
    
    return True


def stabilize_counts(new_counts):
    """Estabilizar conteos - si detecta aunque sea 1 vez, lo mantiene"""
    global detection_history, stable_counts
    
    detection_history.append(new_counts)
    
    if len(detection_history) > STABILITY_FRAMES:
        detection_history.pop(0)
    
    if len(detection_history) >= 2:
        averaged_counts = []
        for zone_idx in range(6):
            zone_detections = [frame[zone_idx] for frame in detection_history]
            
            # Contar frames donde se detectó algo
            frames_with_detection = sum(1 for d in zone_detections if d > 0)
            
            # Si se detectó en al menos 1 de los últimos 10 frames, mantener
            if frames_with_detection >= 1:
                # Usar el máximo de los últimos 5 frames
                recent = zone_detections[-min(5, len(zone_detections)):]
                stable_value = max(recent)
            else:
                stable_value = 0
            
            averaged_counts.append(stable_value)
        
        stable_counts = averaged_counts
    
    return stable_counts


def generate_frames():
    """Generador de frames con detección YOLO + estabilización"""
    global frame_counter, stable_counts
    
    # ===== FUENTE DE CÁMARA =====
    # Opción 1: Webcam normal
    # CAMERA_SOURCE = 0
    #
    # Opción 2: DroidCam por WiFi
    CAMERA_SOURCE = "http://192.168.100.138:4747/video"
    #
    # Opción 3: DroidCam como webcam virtual
    # CAMERA_SOURCE = 1
    
    print(f"📷 Conectando a: {CAMERA_SOURCE}")
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    
    if not cap.isOpened():
        print(f"❌ No se puede conectar a: {CAMERA_SOURCE}")
        print("   💡 Verifica que DroidCam esté abierto en el celular")
        print("   💡 Verifica que la IP sea correcta")
        print("   💡 Asegúrate de estar en la misma red WiFi")
        state.camera_active = False
        return
    
    # Resolución de captura
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    state.camera_active = True
    print(f"✅ Cámara conectada: {actual_w}x{actual_h}")
    print(f"📊 Configuración:")
    print(f"   - Confianza mínima: {MIN_CONFIDENCE}")
    print(f"   - YOLO imgsz: 1280 (alta resolución para objetos pequeños)")
    print(f"   - Estabilización: {STABILITY_FRAMES} frames")
    
    last_warning = 0
    
    try:
        while True:
            success, frame = cap.read()
            if not success:
                print("⚠️ Error leyendo frame")
                state.camera_active = False
                break
            
            h, w, _ = frame.shape
            current_detections = [0] * 6
            
            # Verificar brillo
            is_valid, brightness = is_image_valid(frame)
            
            if not is_valid:
                # Imagen muy oscura
                if frame_counter - last_warning > 30:
                    print(f"⚠️  Cámara tapada (brillo: {brightness:.1f}/255)")
                    last_warning = frame_counter
                
                # Forzar conteos a cero
                detection_history.clear()
                stable_counts = [0] * 6
                state.update_vehicle_counts([0] * 6)
                
                # Mostrar advertencia
                cv2.rectangle(frame, (0, 0), (w, 100), (0, 0, 0), -1)
                cv2.putText(frame, "CAMARA TAPADA O SIN LUZ", (w//2 - 200, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                cv2.putText(frame, f"Brillo: {brightness:.1f}/255 (min: {MIN_BRIGHTNESS})",
                           (w//2 - 200, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            else:
                # Detectar cada 3 frames para no sobrecargar
                if frame_counter % 3 == 0:
                    # imgsz=1280 para detectar objetos PEQUEÑOS desde lejos
                    results = model(frame, stream=True, verbose=False, conf=MIN_CONFIDENCE, imgsz=1280)
                    
                    for r in results:
                        for box in r.boxes:
                            cls = int(box.cls[0])
                            
                            if cls not in VEHICLE_CLASSES:
                                continue
                            
                            if not is_valid_vehicle(box, w, h):
                                continue
                            
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            cx = (x1 + x2) // 2
                            cy = (y1 + y2) // 2
                            confidence = float(box.conf[0])
                            
                            # Detectar en qué zona cae
                            vehicle_in_zone = False
                            for i, (zx1, zy1, zx2, zy2) in enumerate(ZONES):
                                zone_x1 = int(zx1 * w)
                                zone_y1 = int(zy1 * h)
                                zone_x2 = int(zx2 * w)
                                zone_y2 = int(zy2 * h)
                                
                                if zone_x1 <= cx <= zone_x2 and zone_y1 <= cy <= zone_y2:
                                    current_detections[i] += 1
                                    vehicle_in_zone = True
                                    
                                    label = f"{ZONE_NAMES[i][0]} {confidence:.2f}"
                                    cv2.putText(frame, label, (x1, y1 - 10),
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, ZONE_COLORS[i], 2)
                                    break
                            
                            # Dibujar caja
                            color = (0, 255, 0) if vehicle_in_zone else (0, 165, 255)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                            cv2.putText(frame, f"car {confidence:.0%}", (x1, y2 + 15),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                    
                    # Estabilizar (solo en frames donde corrió YOLO)
                    stabilize_counts(current_detections)
                    
                    if frame_counter % 30 == 0 and sum(stable_counts) > 0:
                        print(f"📊 Conteos estabilizados: {stable_counts}")
                
                # Actualizar estado cada UPDATE_INTERVAL frames
                if frame_counter % UPDATE_INTERVAL == 0:
                    state.update_vehicle_counts(stable_counts.copy())
            
            # Dibujar zonas
            for i, (zx1, zy1, zx2, zy2) in enumerate(ZONES):
                x1 = int(zx1 * w)
                y1 = int(zy1 * h)
                x2 = int(zx2 * w)
                y2 = int(zy2 * h)
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), ZONE_COLORS[i], 2)
                
                label = f"{ZONE_NAMES[i]}: {stable_counts[i]}"
                (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(frame, (x1, y1), (x1 + text_w + 10, y1 + text_h + 10), ZONE_COLORS[i], -1)
                cv2.putText(frame, label, (x1 + 5, y1 + text_h + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            
            # Info general
            total = sum(stable_counts)
            status_text = f"Vehiculos: {total} | Brillo: {brightness:.0f}/255"
            if not is_valid:
                status_text += " | TAPADA"
            
            status_color = (0, 255, 0) if is_valid else (0, 0, 255)
            
            cv2.rectangle(frame, (0, h - 40), (w, h), (0, 0, 0), -1)
            cv2.putText(frame, status_text, (10, h - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
            
            # Indicador de estabilidad
            stability_pct = min(100, (len(detection_history) / STABILITY_FRAMES) * 100)
            stability_text = f"Estabilidad: {stability_pct:.0f}%"
            cv2.putText(frame, stability_text, (w - 200, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            
            # Codificar frame
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
            )
            
            frame_counter += 1
    
    except Exception as e:
        print(f"❌ Error en generate_frames: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cap.release()
        state.camera_active = False
        print("🔌 Cámara desconectada")


def test_camera():
    """Función de prueba para calibrar detección"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ No se puede abrir la cámara")
        return
    
    print("✅ Cámara OK. Presiona 'q' para cerrar")
    
    test_history = []
    test_stable = [0] * 6
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        h, w, _ = frame.shape
        is_valid, brightness = is_image_valid(frame)
        
        current = [0] * 6
        
        if is_valid:
            results = model(frame, verbose=False, conf=MIN_CONFIDENCE)
            
            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    if cls not in VEHICLE_CLASSES:
                        continue
                    
                    if not is_valid_vehicle(box, w, h):
                        continue
                    
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    
                    for i, (zx1, zy1, zx2, zy2) in enumerate(ZONES):
                        zone_x1 = int(zx1 * w)
                        zone_y1 = int(zy1 * h)
                        zone_x2 = int(zx2 * w)
                        zone_y2 = int(zy2 * h)
                        
                        if zone_x1 <= cx <= zone_x2 and zone_y1 <= cy <= zone_y2:
                            current[i] += 1
                            break
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            test_history.append(current)
            if len(test_history) > STABILITY_FRAMES:
                test_history.pop(0)
            
            if len(test_history) >= 3:
                for i in range(6):
                    avg = sum([f[i] for f in test_history]) / len(test_history)
                    test_stable[i] = round(avg) if avg >= 0.4 else 0
        
        cv2.putText(frame, f"Instantaneo: {current}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(frame, f"ESTABLE: {test_stable}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"Brillo: {brightness:.0f}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow('Test Estabilizacion', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


def get_camera_status():
    """Obtener estado actual de la cámara"""
    return {
        'active': state.camera_active,
        'vehicle_count': state.vehicle_count,
        'counts_per_lane': state.vehicle_counts,
        'stable': len(detection_history) >= STABILITY_FRAMES
    }