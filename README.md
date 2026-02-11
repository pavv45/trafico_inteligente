# 🚦 Sistema de Control de Tráfico Inteligente

Sistema adaptativo de control de semáforos basado en detección de vehículos mediante visión por computadora (YOLO + OpenCV). Ajusta automáticamente los tiempos de luz verde según el volumen de tráfico detectado en tiempo real.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Django](https://img.shields.io/badge/Django-6.0.2-green)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-red)
![YOLO](https://img.shields.io/badge/YOLO-v8-orange)

## 📋 Características

- ✅ **Detección en tiempo real** de vehículos con YOLO v8
- ✅ **Control adaptativo** de 6 semáforos organizados en fases (Avenidas e Intersecciones)
- ✅ **Priorización inteligente** basada en volumen de tráfico
- ✅ **Interfaz web** con streaming de video en vivo
- ✅ **Modo automático y manual** de operación
- ✅ **Integración con Arduino** para control físico de LEDs
- ✅ **Estabilización de conteos** mediante promedio móvil

## 🎯 Funcionamiento

```
Cámara → Detección YOLO → Conteo por Zona → Cálculo de Tiempos → Arduino → Semáforos
```

**Lógica de Control:**
- Las avenidas arrancan simultáneamente en verde
- La dirección con menos tráfico termina primero
- La dirección con más tráfico continúa proporcionalmente
- Tiempo verde = 3s base + (vehículos × 5s), máximo 45s

## 🛠️ Tecnologías

| Componente | Tecnología |
|------------|------------|
| **Backend** | Django 6.0.2 + Python 3.10+ |
| **Visión por Computadora** | YOLO v8 (Ultralytics) + OpenCV |
| **Hardware** | Arduino Uno/Mega + PySerial |
| **Frontend** | HTML5 + JavaScript (AJAX) |
| **Base de Datos** | SQLite3 |

## 🚀 Instalación Rápida

### 1. Clonar repositorio
```bash
git clone https://github.com/usuario/trafico_inteligente.git
cd trafico_inteligente
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

pip install django opencv-python ultralytics numpy pyserial
```

### 3. Configurar base de datos
```bash
cd core
python manage.py migrate
```

### 4. Configurar hardware
- Programar Arduino con sketch de semáforos
- Conectar cámara USB o configurar DroidCam WiFi
- Ajustar `CAMERA_SOURCE` en `traffic/camera.py`
- Verificar puerto COM en `traffic/arduino.py`

### 5. Ejecutar servidor
```bash
python manage.py runserver
```

Abrir en navegador: **http://localhost:8000/**

## 📁 Estructura del Proyecto

```
trafico_inteligente/
├── core/
│   ├── traffic/              # App principal
│   │   ├── arduino.py       # Comunicación serial
│   │   ├── camera.py        # Detección con YOLO
│   │   ├── controller.py    # Lógica de control
│   │   ├── logic.py         # Definición de fases
│   │   ├── state.py         # Gestión de estado
│   │   ├── zones.py         # Coordenadas de detección
│   │   └── views.py         # API endpoints
│   ├── templates/           # Interfaz web
│   └── manage.py
├── yolov8n.pt              # Modelo YOLO nano
└── README.md
```

## 🎮 Uso

### Modo Automático
1. Acceder al dashboard web
2. Click en botón **AUTO**
3. El sistema detecta vehículos y controla semáforos automáticamente

### Modo Manual
1. Click en botón **MANUAL**
2. Controlar cada semáforo individualmente (Verde/Amarillo/Rojo)

### Monitoreo
- **Video en vivo**: Muestra detecciones con cajas delimitadoras
- **Conteos por zona**: Número de vehículos detectados
- **Estado de semáforos**: Colores actuales de cada luz

## 📊 Endpoints API

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/auto/` | GET | Toggle modo automático |
| `/manual/<lane>/<action>/` | GET | Control manual de semáforo |
| `/video_feed/` | GET | Stream MJPEG de video |
| `/traffic_status/` | GET | Estado del sistema (JSON) |
| `/vehicle_counts/` | GET | Conteos de vehículos (JSON) |

## ⚙️ Configuración

### Parámetros de Detección (`camera.py`)
```python
MIN_CONFIDENCE = 0.25      # Umbral de confianza YOLO
MIN_VEHICLE_SIZE = 100     # Área mínima de vehículo (px²)
STABILITY_FRAMES = 10      # Frames para estabilizar conteos
```

### Parámetros de Tiempo (`logic.py`)
```python
BASE_GREEN_TIME = 3        # Tiempo base en verde (segundos)
TIME_PER_VEHICLE = 5       # Tiempo adicional por vehículo
MAX_GREEN_TIME = 45        # Tiempo máximo en verde
YELLOW_TIME = 3            # Duración de luz amarilla
```

### Zonas de Detección (`zones.py`)
Coordenadas normalizadas (0.0 - 1.0) para 6 zonas:
- **A, D**: Intersecciones (calles verticales)
- **B, E**: Avenida IDA (horizontal superior)
- **C, F**: Avenida VUELTA (horizontal inferior)

## 🔧 Requisitos del Sistema

**Software:**
- Python 3.10 o superior
- Arduino IDE 1.8+
- 4GB RAM mínimo
- CPU con soporte AVX2 (para YOLO optimizado)

**Hardware:**
- Arduino Uno/Mega
- Cámara USB o móvil con DroidCam
- 18 LEDs (6R + 6Y + 6G) + resistencias 220Ω
- Cable USB para Arduino

## 🐛 Solución de Problemas

| Problema | Solución |
|----------|----------|
| **"Cámara tapada"** | Mejorar iluminación (brillo mínimo 25/255) |
| **Arduino no responde** | Verificar puerto COM en `arduino.py` |
| **No detecta vehículos** | Ajustar `MIN_CONFIDENCE` o calibrar zonas |
| **Puerto 8000 ocupado** | Usar `python manage.py runserver 8080` |

## 📈 Limitaciones

- Requiere iluminación mínima (no funciona de noche sin luz artificial)
- Máximo 6 zonas de detección simultáneas
- Una cámara por instancia
- Diseñado para maquetas/simulaciones (no certificado para uso vial real)
- Objetos muy pequeños (<100px²) pueden no detectarse

## 🤝 Contribuciones

Este proyecto fue desarrollado como proyecto final académico. Las contribuciones son bienvenidas:

1. Fork del proyecto
2. Crear rama (`git checkout -b feature/mejora`)
3. Commit cambios (`git commit -m 'Agregar mejora'`)
4. Push a la rama (`git push origin feature/mejora`)
5. Crear Pull Request

## 📝 Licencia

Este proyecto es de código abierto para fines educativos.

## 👨‍💻 Autor

**Sistema de Tráfico Inteligente**  
Proyecto Final - Febrero 2026

---

Para más detalles técnicos, consultar:
- **Documentación técnica completa**: Ver documento de entrega
- **Guía de instalación**: Sección 3 del documento final
- **Guía de uso**: Sección 4 del documento final
