import cv2
import mediapipe as mp
import serial
import time
import os
import urllib.request
import math


# =========================================================
# CONFIGURACIÓN
# =========================================================

PUERTO_SERIAL = "COM7"
BAUD_RATE = 115200

MODEL_PATH = "hand_landmarker.task"

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/"
    "hand_landmarker.task"
)


# =========================================================
# CONEXIÓN ESP32
# =========================================================

arduino = None

try:

    arduino = serial.Serial(
        PUERTO_SERIAL,
        BAUD_RATE,
        timeout=1
    )

    time.sleep(2)

    print("======================================")
    print("ESP32 CONECTADO")
    print(f"Puerto: {PUERTO_SERIAL}")
    print("======================================")

except Exception as e:

    print("======================================")
    print("AVISO: ESP32 NO CONECTADO")
    print("El programa continuará con la cámara.")
    print("======================================")
    print(e)


# =========================================================
# DESCARGAR MODELO SI NO EXISTE
# =========================================================

if not os.path.exists(MODEL_PATH):

    print("Descargando modelo de MediaPipe...")

    try:

        urllib.request.urlretrieve(
            MODEL_URL,
            MODEL_PATH
        )

        print("Modelo descargado.")

    except Exception as e:

        print("ERROR descargando el modelo:")
        print(e)

        if arduino:
            arduino.close()

        exit()


# =========================================================
# MEDIAPIPE
# =========================================================

BaseOptions = mp.tasks.BaseOptions

HandLandmarker = mp.tasks.vision.HandLandmarker

HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions

RunningMode = mp.tasks.vision.RunningMode


options = HandLandmarkerOptions(

    base_options=BaseOptions(
        model_asset_path=MODEL_PATH
    ),

    running_mode=RunningMode.VIDEO,

    num_hands=1,

    min_hand_detection_confidence=0.65,

    min_hand_presence_confidence=0.65,

    min_tracking_confidence=0.65
)


detector = HandLandmarker.create_from_options(options)

print("MediaPipe iniciado correctamente.")


# =========================================================
# CÁMARA
# =========================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print("ERROR: No se pudo abrir la cámara.")

    detector.close()

    if arduino:
        arduino.close()

    exit()


# =========================================================
# FUNCIONES MATEMÁTICAS
# =========================================================

def distancia(p1, p2):

    return math.sqrt(
        (p1.x - p2.x) ** 2 +
        (p1.y - p2.y) ** 2 +
        (p1.z - p2.z) ** 2
    )


def angulo(a, b, c):

    """
    Calcula el ángulo ABC.
    """

    ba = (
        a.x - b.x,
        a.y - b.y,
        a.z - b.z
    )

    bc = (
        c.x - b.x,
        c.y - b.y,
        c.z - b.z
    )

    producto = (
        ba[0] * bc[0] +
        ba[1] * bc[1] +
        ba[2] * bc[2]
    )

    magnitud_ba = math.sqrt(
        ba[0] ** 2 +
        ba[1] ** 2 +
        ba[2] ** 2
    )

    magnitud_bc = math.sqrt(
        bc[0] ** 2 +
        bc[1] ** 2 +
        bc[2] ** 2
    )

    if magnitud_ba == 0 or magnitud_bc == 0:
        return 0

    coseno = producto / (
        magnitud_ba * magnitud_bc
    )

    coseno = max(-1, min(1, coseno))

    return math.degrees(
        math.acos(coseno)
    )


# =========================================================
# DETECTAR DEDOS
# =========================================================

def dedo_abierto(landmarks, mcp, pip, dip, tip):

    """
    Determina si un dedo está extendido utilizando
    los ángulos de las articulaciones.

    Esto es mucho más estable que simplemente
    comparar coordenadas Y.
    """

    angulo_pip = angulo(
        landmarks[mcp],
        landmarks[pip],
        landmarks[dip]
    )

    angulo_dip = angulo(
        landmarks[pip],
        landmarks[dip],
        landmarks[tip]
    )

    # Dedo extendido
    if angulo_pip > 155 and angulo_dip > 150:
        return True

    return False


# =========================================================
# DETECTAR PULGAR
# =========================================================

def pulgar_arriba(landmarks):

    wrist = landmarks[0]
    thumb_mcp = landmarks[2]
    thumb_tip = landmarks[4]

    # El pulgar está bastante por encima
    # de su base y de la muñeca.

    return (
        thumb_tip.y < thumb_mcp.y - 0.08
        and
        thumb_tip.y < wrist.y - 0.05
    )


def pulgar_abajo(landmarks):

    wrist = landmarks[0]
    thumb_mcp = landmarks[2]
    thumb_tip = landmarks[4]

    return (
        thumb_tip.y > thumb_mcp.y + 0.08
        and
        thumb_tip.y > wrist.y + 0.05
    )


# =========================================================
# IDENTIFICAR GESTO
# =========================================================

def identificar_gesto(landmarks):

    # =====================================================
    # DETECTAR LOS 4 DEDOS PRINCIPALES
    # =====================================================

    indice = dedo_abierto(
        landmarks,
        5, 6, 7, 8
    )

    medio = dedo_abierto(
        landmarks,
        9, 10, 11, 12
    )

    anular = dedo_abierto(
        landmarks,
        13, 14, 15, 16
    )

    menique = dedo_abierto(
        landmarks,
        17, 18, 19, 20
    )


    dedos = [
        indice,
        medio,
        anular,
        menique
    ]


    cantidad = sum(dedos)


    # =====================================================
    # ✊ PUÑO CERRADO
    # =====================================================

    # IMPORTANTE:
    #
    # Para el puño NO dependemos del pulgar.
    #
    # Si los cuatro dedos principales están cerrados,
    # consideramos que es puño.
    #
    # Esto hace que el gesto sea mucho más estable.

    if cantidad == 0:

        return "PUÑO"


    # =====================================================
    # ✌️ DOS DEDOS
    # =====================================================

    if (
        indice
        and
        medio
        and
        not anular
        and
        not menique
    ):

        return "DOS"


    # =====================================================
    # 🖐️ MANO ABIERTA
    # =====================================================

    if cantidad == 4:

        return "ABIERTA"


    # =====================================================
    # 👍 PULGAR ARRIBA
    # =====================================================

    if cantidad == 0 and pulgar_arriba(landmarks):

        return "PULGAR_ARRIBA"


    # =====================================================
    # 👎 PULGAR ABAJO
    # =====================================================

    if cantidad == 0 and pulgar_abajo(landmarks):

        return "PULGAR_ABAJO"


    # =====================================================
    # NINGÚN GESTO
    # =====================================================

    return "NINGUNO"


# =========================================================
# DIBUJAR MANO
# =========================================================

CONNECTIONS = [

    # Pulgar
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),

    # Índice
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),

    # Medio
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),

    # Anular
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),

    # Meñique
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),

    # Palma
    (0, 17)
]


def dibujar_mano(img, landmarks):

    altura, ancho, _ = img.shape

    puntos = []

    for landmark in landmarks:

        x = int(
            landmark.x * ancho
        )

        y = int(
            landmark.y * altura
        )

        puntos.append(
            (x, y)
        )

        cv2.circle(
            img,
            (x, y),
            5,
            (0, 255, 0),
            -1
        )


    for inicio, fin in CONNECTIONS:

        cv2.line(
            img,
            puntos[inicio],
            puntos[fin],
            (255, 0, 0),
            2
        )


# =========================================================
# ENVIAR COMANDO
# =========================================================

def enviar_comando(comando):

    if arduino:

        try:

            arduino.write(
                comando.encode()
            )

            print(
                f"COMANDO ENVIADO: {comando}"
            )

        except Exception as e:

            print(
                "Error enviando comando:"
            )

            print(e)

    else:

        print(
            f"COMANDO: {comando} "
            "(ESP32 desconectado)"
        )


# =========================================================
# VARIABLES
# =========================================================

gesto_anterior = "NINGUNO"

timestamp_ms = 0


# =========================================================
# FILTRO DE ESTABILIDAD
# =========================================================

historial_gestos = []

NUM_MUESTRAS = 5


# =========================================================
# PROGRAMA PRINCIPAL
# =========================================================

while True:

    # =====================================================
    # CÁMARA
    # =====================================================

    success, img = cap.read()

    if not success:

        print("Error leyendo cámara.")

        continue


    # =====================================================
    # ESPEJO
    # =====================================================

    img = cv2.flip(
        img,
        1
    )


    # =====================================================
    # RGB
    # =====================================================

    img_rgb = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2RGB
    )


    # =====================================================
    # MEDIAPIPE IMAGE
    # =====================================================

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=img_rgb
    )


    timestamp_ms += 33


    # =====================================================
    # DETECCIÓN
    # =====================================================

    try:

        results = detector.detect_for_video(
            mp_image,
            timestamp_ms
        )

    except Exception as e:

        print("Error MediaPipe:")
        print(e)

        continue


    gesto_actual = "NINGUNO"


    # =====================================================
    # MANO DETECTADA
    # =====================================================

    if results.hand_landmarks:

        landmarks = results.hand_landmarks[0]


        # Dibujar
        dibujar_mano(
            img,
            landmarks
        )


        # Detectar
        gesto_actual = identificar_gesto(
            landmarks
        )


        # =================================================
        # FILTRO
        # =================================================

        historial_gestos.append(
            gesto_actual
        )


        if len(historial_gestos) > NUM_MUESTRAS:

            historial_gestos.pop(0)


        # Contar cuál aparece más
        if len(historial_gestos) >= 3:

            gesto_filtrado = max(
                set(historial_gestos),
                key=historial_gestos.count
            )

        else:

            gesto_filtrado = gesto_actual


    else:

        historial_gestos.clear()

        gesto_filtrado = "NINGUNO"


    # =====================================================
    # MOSTRAR GESTO
    # =====================================================

    cv2.putText(
        img,
        f"Gesto: {gesto_filtrado}",
        (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        3
    )


    # =====================================================
    # INFORMACIÓN DEL SISTEMA
    # =====================================================

    cv2.putText(
        img,
        "PUÑO = MODO 1",
        (20, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.putText(
        img,
        "DOS = 70% | ABIERTA = 100%",
        (20, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.putText(
        img,
        "PULGAR = MODO 2",
        (20, 150),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )


    # =====================================================
    # ENVIAR COMANDO
    # =====================================================

    if gesto_filtrado != gesto_anterior:

        # -----------------------------------------------
        # ✊ PRIMERA INTERRUPCIÓN
        # -----------------------------------------------

        if gesto_filtrado == "PUÑO":

            enviar_comando("1")


        # -----------------------------------------------
        # ✌️ 70%
        # -----------------------------------------------

        elif gesto_filtrado == "DOS":

            enviar_comando("2")


        # -----------------------------------------------
        # 🖐️ 100%
        # -----------------------------------------------

        elif gesto_filtrado == "ABIERTA":

            enviar_comando("3")


        # -----------------------------------------------
        # 👍 SEGUNDA INTERRUPCIÓN
        # -----------------------------------------------

        elif gesto_filtrado == "PULGAR_ARRIBA":

            enviar_comando("4")


        # -----------------------------------------------
        # 👎 SEGUNDA INTERRUPCIÓN
        # -----------------------------------------------

        elif gesto_filtrado == "PULGAR_ABAJO":

            enviar_comando("5")


        gesto_anterior = gesto_filtrado


    # =====================================================
    # MOSTRAR
    # =====================================================

    cv2.imshow(
        "Control de Luces - ESP32",
        img
    )


    # =====================================================
    # ESC
    # =====================================================

    if cv2.waitKey(1) & 0xFF == 27:

        break


# =========================================================
# CERRAR
# =========================================================

cap.release()

cv2.destroyAllWindows()

detector.close()

if arduino:

    arduino.close()

print("Programa terminado.")
