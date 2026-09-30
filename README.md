# ✋💡 Control de iluminación por gestos de la mano — MediaPipe + ESP32

Sistema que reconoce gestos de la mano en tiempo real con **MediaPipe Gesture Recognizer** y, según el gesto detectado, controla la intensidad de tres LEDs y dos secuencias de luces conectados a una **ESP32** programada en **MicroPython**.

> Universidad Militar Nueva Granada — Microcontroladores
> Autor: **Bryan Andrey Martínez Montaño**

---

## 🎥 Video de funcionamiento

[![Video de funcionamiento](https://img.youtube.com/vi/gBYAK_kNrNs/0.jpg)](https://youtu.be/gBYAK_kNrNs)

👉 https://youtu.be/gBYAK_kNrNs

---

## 📋 Descripción del reto

A partir de la librería MediaPipe y su demo de [Gesture Recognizer](https://google-ai-edge.github.io/mediapipe-samples-web/#/vision/gesture_recognizer), se desarrolló un sistema de control de iluminación con el siguiente comportamiento:

| Gesto | Categoría MediaPipe | LED | Acción |
|---|---|---|---|
| ✊ Puño cerrado | `Closed_Fist` | 🟡 Amarillo | 30 % de intensidad |
| ✌️ Victoria | `Victory` | 🔵 Azul | 70 % de intensidad |
| 🖐️ Mano abierta | `Open_Palm` | 🔴 Rojo | 100 % de intensidad |
| 👎 Pulgar abajo | `Thumb_Down` | Todos | **1.ª interrupción** → Secuencia de luces (Modo 1) |
| 👍 Pulgar arriba | `Thumb_Up` | Todos | **2.ª interrupción** → Secuencia de luces (Modo 2) |

---

## 🧠 ¿Cómo funciona?

```
┌──────────────┐    frames    ┌─────────────────────┐   gesto (texto)   ┌──────────────┐    PWM    ┌───────┐
│   Cámara     │ ───────────► │ Python + MediaPipe  │ ────────────────► │ ESP32        │ ────────► │ LEDs  │
│   (webcam)   │              │ (PC)                │   Serial USB      │ (MicroPython)│           │       │
└──────────────┘              └─────────────────────┘                   └──────────────┘           └───────┘
```

1. **Captura:** OpenCV toma los frames de la cámara del PC.
2. **Detección de la mano:** MediaPipe ubica los **21 puntos (landmarks)** de la mano (0 = `WRIST` … 20 = `PINKY_TIP`).
3. **Clasificación del gesto:** el modelo `gesture_recognizer.task` devuelve la categoría del gesto (`Closed_Fist`, `Victory`, `Open_Palm`, `Thumb_Down`, `Thumb_Up`) con su nivel de confianza.
4. **Filtrado:** el gesto solo se envía si supera un umbral de confianza y si es distinto del último enviado. Así no se satura el puerto serial.
5. **Envío:** el nombre del gesto se manda a la ESP32 por el puerto serial.
6. **Control en la ESP32:** MicroPython lee el comando y:
   - ajusta el **ciclo útil del PWM** del LED correspondiente (30 %, 70 % o 100 %), o
   - activa una **bandera de interrupción** que ejecuta la secuencia de luces del Modo 1 o del Modo 2.

### Cálculo del PWM (resolución de 16 bits en MicroPython)

`duty_u16 = porcentaje × 65535`

| Intensidad | Cálculo | `duty_u16` |
|---|---|---|
| 30 % | 0.30 × 65535 | 19660 |
| 70 % | 0.70 × 65535 | 45875 |
| 100 % | 1.00 × 65535 | 65535 |

---

## 🔌 Hardware

| Componente | Cantidad |
|---|---|
| ESP32 DevKit | 1 |
| LED amarillo, azul y rojo | 1 c/u |
| Resistencias de 220 Ω | 3 |
| Protoboard y jumpers | — |
| Cable USB (datos) | 1 |
| Webcam (integrada o USB) | 1 |

### Conexiones

| LED | GPIO ESP32 |
|---|---|
| 🟡 Amarillo | GPIO `25` |
| 🔵 Azul | GPIO `26` |
| 🔴 Rojo | GPIO `27` |

Cada LED va en serie con su resistencia de 220 Ω hacia **GND**.

---

## 📁 Estructura del repositorio

```
├── pc/
│   ├── gestos.py                 # Detección con MediaPipe + envío serial
│   └── gesture_recognizer.task   # Modelo de MediaPipe
├── esp32/
│   └── main.py                   # Control de LEDs (MicroPython)
├── requirements.txt
└── README.md
```

---

## ⚙️ Instalación y uso

### 1. Entorno en el PC (Windows)

```bash
python -m venv venv
venv\Scripts\activate
pip install mediapipe opencv-python pyserial
```

Descarga el modelo y guárdalo en la carpeta `pc/`:
https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task

### 2. ESP32

1. Flashea el firmware de **MicroPython** en la ESP32.
2. En **Visual Studio Code** (extensión Pymakr o MicroPico), o con Thonny, sube `esp32/main.py` a la placa.
3. Cierra la terminal REPL para liberar el puerto COM.

### 3. Ejecutar

1. En `gestos.py`, cambia el puerto (`COM3`, `COM5`, …) al que usa tu ESP32.
2. Ejecuta:
   ```bash
   python pc/gestos.py
   ```
3. Haz los gestos frente a la cámara. Presiona `q` para salir.

---

## 🧪 Resultados

- Los cinco gestos se reconocieron correctamente con buena iluminación y la mano de frente a la cámara.
- El cambio de intensidad del PWM se aprecia claramente entre 30 %, 70 % y 100 %.
- Los gestos 👎 y 👍 interrumpen el estado actual y ejecutan sus secuencias (Modo 1 y Modo 2).

### Dificultades y soluciones

- **Mucho tráfico en el puerto serial:** se envía el gesto solo cuando cambia.
- **Falsos positivos:** se usa un umbral mínimo de confianza.
- **Puerto ocupado:** hay que cerrar el REPL del IDE antes de correr el script del PC.

---

## 📚 Referencias

- MediaPipe Gesture Recognizer — https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer
- Demo web — https://google-ai-edge.github.io/mediapipe-samples-web/#/vision/gesture_recognizer
- Documentación de MicroPython para ESP32 (PWM) — https://docs.micropython.org/en/latest/esp32/quickref.html#pwm-pulse-width-modulation
